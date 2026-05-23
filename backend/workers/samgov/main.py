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
    INTER_DAY_DELAY,
    QuotaExhaustedError,
    SamGovFetcher,
    create_session,
    iter_date_windows,
)

SOURCE_PORTAL = mapper.SOURCE_PORTAL


async def run_samgov_ingestion(days: int) -> dict[str, Any]:
    """
    Run SAM.gov ingestion for the last `days` calendar days (inclusive of today).

    Processes day windows sequentially to maximise quota usage — same approach
    as the backfill script. Stops gracefully on quota exhaustion and records
    the run as PARTIAL_SUCCESS so the next scheduled run can continue.
    """
    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={"days": days, "mode": "sequential_date_window"},
    )

    windows = iter_date_windows(date.today(), days)
    task_count = len(windows)
    records_scraped = 0
    errors: list[str] = []
    window_results: list[dict[str, Any]] = []
    quota_hit = False

    session = await create_session()
    try:
        fetcher = SamGovFetcher(session)

        for i, (posted_from, posted_to) in enumerate(windows, 1):
            print(f"  [{i}/{task_count}] {posted_from} … ", end="", flush=True)
            try:
                notices = await fetcher.fetch_notices_for_range(posted_from, posted_to)
                tuples = [mapper.map_notice_to_tuple(item) for item in notices]
                written = await db.upsert_opportunities(tuples)
                records_scraped += written
                result = {
                    "posted_from": posted_from,
                    "posted_to": posted_to,
                    "fetched": len(notices),
                    "upserted": written,
                }
                window_results.append(result)
                print(f"fetched={len(notices)}  upserted={written}")

            except QuotaExhaustedError as exc:
                # Daily quota gone — stop cleanly, remaining days will be
                # picked up on the next scheduled run (upsert is idempotent)
                quota_hit = True
                msg = str(exc)
                print(f"\n  ⛔  Quota exhausted: {msg[:120]}")
                errors.append(msg)
                await db.log_scrape_error(
                    run_id, SOURCE_PORTAL, msg,
                    raw_payload={"posted_from": posted_from, "posted_to": posted_to},
                )
                window_results.append({
                    "posted_from": posted_from,
                    "posted_to": posted_to,
                    "error": "quota_exhausted",
                })
                break

            except Exception as exc:
                msg = "".join(
                    traceback.format_exception_only(type(exc), exc)
                ).strip()
                errors.append(msg)
                print(f"ERROR — {msg}")
                await db.log_scrape_error(
                    run_id, SOURCE_PORTAL, msg,
                    raw_payload={
                        "posted_from": posted_from,
                        "posted_to": posted_to,
                        "traceback": traceback.format_exc(),
                    },
                )
                window_results.append({
                    "posted_from": posted_from,
                    "posted_to": posted_to,
                    "error": msg,
                })

            # Polite delay between days (skip after last window)
            if i < task_count and not quota_hit:
                await asyncio.sleep(INTER_DAY_DELAY)

    finally:
        await session.close()

    # Determine final status
    non_quota_errors = [e for e in errors if "quota" not in e.lower()]
    if quota_hit and records_scraped == 0 and not non_quota_errors:
        final_status = "FAILED"
    elif errors:
        final_status = "PARTIAL_SUCCESS"
    else:
        final_status = "SUCCESS"

    metadata = {
        "days": days,
        "task_count": task_count,
        "days_processed": len([w for w in window_results if "error" not in w]),
        "error_count": len(errors),
        "quota_hit": quota_hit,
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
        "quota_hit": quota_hit,
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
