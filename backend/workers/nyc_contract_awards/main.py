"""
NYC Contract Awards ingestion entry point.

Usage:
  python -m backend.workers.nyc_contract_awards.main              # daily (default)
  python -m backend.workers.nyc_contract_awards.main --mode daily
  python -m backend.workers.nyc_contract_awards.main --mode initial

Modes:
  daily   — Socrata JSON API (1 000 records/page, aiohttp, paginated)
  initial — Full CSV export (~35 MB, stdlib only, one-time backfill)

Both modes filter to 2026 start_date records before upserting.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import traceback

import aiohttp

from backend.core import db, settings
from backend.workers.nyc_contract_awards.fetcher import fetch_daily_json, fetch_initial_csv
from backend.workers.nyc_contract_awards.mapper import SOURCE_PORTAL, map_nyc_row

PORTAL_LABEL = "NYC Open Data — Recent Contract Awards"


async def run_nyc_ingestion(mode: str = "daily") -> dict[str, object]:
    """
    Fetch NYC contract award records, map them, and upsert into opportunities.

    Args:
        mode: "daily" (JSON API) or "initial" (full CSV export)

    Returns:
        dict with run_id, status, records_upserted, error
    """
    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={"mode": mode, "portal": PORTAL_LABEL},
    )

    status = "FAILED"
    records_upserted = 0
    error_msg: str | None = None

    try:
        print(f"Run {run_id}: Starting NYC ingestion (mode={mode})...")

        if mode == "initial":
            # Sync CSV download — run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            raw_records = await loop.run_in_executor(None, fetch_initial_csv)
        else:
            # Daily JSON API via aiohttp
            async with aiohttp.ClientSession(
                headers={"User-Agent": settings.USER_AGENT}
            ) as session:
                raw_records = await fetch_daily_json(session)

        if not raw_records:
            print(f"Run {run_id}: No 2026 records found — nothing to upsert.")
            status = "SUCCESS"
        else:
            mapped_tuples = [map_nyc_row(r) for r in raw_records]
            print(f"Run {run_id}: Upserting {len(mapped_tuples)} records...")
            records_upserted = await db.upsert_opportunities(mapped_tuples)
            status = "SUCCESS"

    except Exception as exc:
        error_msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(f"[ERROR] NYC run failed: {error_msg}")
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
        result = await run_nyc_ingestion(mode)
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NYC Contract Awards ingestion worker"
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "initial"],
        default="daily",
        help="daily = Socrata JSON API (default); initial = full CSV export",
    )
    args = parser.parse_args()
    asyncio.run(_async_main(args.mode))


if __name__ == "__main__":
    main()
