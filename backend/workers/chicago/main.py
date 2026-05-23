"""
Chicago Contracts ingestion entry point.

Usage:
  python -m backend.workers.chicago.main              # daily (default)
  python -m backend.workers.chicago.main --mode daily

Fetches 2026 contract records from Chicago Data Portal Socrata API,
maps them to the opportunities schema, and upserts into the DB.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import traceback

import aiohttp

from backend.core import db, settings
from backend.workers.chicago.fetcher import fetch_daily_json
from backend.workers.chicago.mapper import SOURCE_PORTAL, map_chicago_row

PORTAL_LABEL = "Chicago Data Portal — Contracts"


async def run_chicago_ingestion(mode: str = "daily") -> dict[str, object]:
    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={"mode": mode, "portal": PORTAL_LABEL},
    )

    status = "FAILED"
    records_upserted = 0
    error_msg: str | None = None

    try:
        print(f"Run {run_id}: Starting Chicago ingestion (mode={mode})...")

        async with aiohttp.ClientSession(
            headers={"User-Agent": settings.USER_AGENT}
        ) as session:
            raw_records = await fetch_daily_json(session)

        if not raw_records:
            print(f"Run {run_id}: No 2026 records found — nothing to upsert.")
            status = "SUCCESS"
        else:
            mapped_tuples = [map_chicago_row(r) for r in raw_records]
            print(f"Run {run_id}: Upserting {len(mapped_tuples)} records...")
            records_upserted = await db.upsert_opportunities(mapped_tuples)
            status = "SUCCESS"

    except Exception as exc:
        error_msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(f"[ERROR] Chicago run failed: {error_msg}")
        await db.log_scrape_error(
            run_id,
            SOURCE_PORTAL,
            error_msg,
            raw_payload={"traceback": traceback.format_exc()},
        )

    await db.finalize_scrape_run(
        run_id,
        status,
        records_upserted,
        metadata={"mode": mode, "upserted": records_upserted, "error": error_msg},
    )

    print(f"Run {run_id} complete: {status} — {records_upserted} records")
    return {
        "run_id": run_id,
        "status": status,
        "records_upserted": records_upserted,
        "error": error_msg,
    }


async def _async_main(mode: str) -> None:
    await db.create_pool()
    try:
        result = await run_chicago_ingestion(mode)
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description="Chicago Contracts ingestion worker")
    parser.add_argument(
        "--mode",
        choices=["daily"],
        default="daily",
        help="daily = Socrata JSON API (default)",
    )
    args = parser.parse_args()
    asyncio.run(_async_main(args.mode))


if __name__ == "__main__":
    main()
