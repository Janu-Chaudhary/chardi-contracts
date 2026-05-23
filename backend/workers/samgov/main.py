"""SAM.gov ingestion orchestration entry point."""

from __future__ import annotations

import argparse
import asyncio
import json
import traceback
from datetime import date
from typing import Any

from backend.core import db
from backend.workers.samgov import mapper
from backend.workers.samgov.fetcher import (
    SamGovFetcher,
    create_session,
    iter_date_windows,
)

SOURCE_PORTAL = mapper.SOURCE_PORTAL


async def _process_day_window(
    fetcher: SamGovFetcher,
    posted_from: str,
    posted_to: str,
) -> dict[str, Any]:
    """Fetch, map, and upsert notices for one day window."""
    notices = await fetcher.fetch_notices_for_range(posted_from, posted_to)
    tuples = [mapper.map_notice_to_tuple(item) for item in notices]
    written = await db.upsert_opportunities(tuples)
    return {
        "posted_from": posted_from,
        "posted_to": posted_to,
        "fetched": len(notices),
        "upserted": written,
    }


async def run_samgov_ingestion(days: int) -> dict[str, Any]:
    """
    Run SAM.gov ingestion for the last `days` calendar days (inclusive of today).

    Creates scrape_runs observability rows, processes day windows concurrently,
    and records per-window failures in scrape_errors.
    """
    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={"days": days, "mode": "date_window_partition"},
    )

    windows = iter_date_windows(date.today(), days)
    task_count = len(windows)
    records_scraped = 0
    errors: list[str] = []
    window_results: list[dict[str, Any]] = []

    session = await create_session()
    try:
        fetcher = SamGovFetcher(session)
        tasks = [
            _process_day_window(fetcher, posted_from, posted_to)
            for posted_from, posted_to in windows
        ]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        for window, outcome in zip(windows, outcomes):
            posted_from, posted_to = window
            if isinstance(outcome, BaseException):
                message = "".join(
                    traceback.format_exception_only(type(outcome), outcome)
                ).strip()
                errors.append(message)
                await db.log_scrape_error(
                    run_id,
                    SOURCE_PORTAL,
                    message,
                    raw_payload={
                        "posted_from": posted_from,
                        "posted_to": posted_to,
                        "traceback": "".join(
                            traceback.format_exception(
                                type(outcome), outcome, outcome.__traceback__
                            )
                        ),
                    },
                )
                window_results.append(
                    {
                        "posted_from": posted_from,
                        "posted_to": posted_to,
                        "error": message,
                    }
                )
            else:
                records_scraped += int(outcome.get("upserted", 0))
                window_results.append(outcome)
    finally:
        await session.close()

    if errors and len(errors) == task_count:
        final_status = "FAILED"
    elif errors:
        final_status = "PARTIAL_SUCCESS"
    else:
        final_status = "SUCCESS"

    metadata = {
        "days": days,
        "task_count": task_count,
        "error_count": len(errors),
        "records_scraped": records_scraped,
        "windows": window_results,
    }

    await db.finalize_scrape_run(
        run_id,
        final_status,
        records_scraped,
        metadata=metadata,
    )

    return {
        "run_id": run_id,
        "status": final_status,
        "records_scraped": records_scraped,
        "errors": errors,
        "metadata": metadata,
    }


async def _async_main(days: int) -> None:
    pool = await db.create_pool()
    try:
        result = await run_samgov_ingestion(days)
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description="SAM.gov federal ingestion worker")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of calendar days to ingest (default: 30)",
    )
    args = parser.parse_args()
    if args.days < 1:
        raise SystemExit("--days must be at least 1")
    asyncio.run(_async_main(args.days))


if __name__ == "__main__":
    main()
