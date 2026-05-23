"""
Montgomery County MD Contracts ingestion entry point.

Usage:
  python -m backend.workers.montgomery_county.main
"""

from __future__ import annotations

import asyncio
import json
import traceback

import aiohttp

from backend.core import db, settings
from backend.workers.montgomery_county.fetcher import fetch_montgomery_records
from backend.workers.montgomery_county.mapper import SOURCE_PORTAL, map_montgomery_row

PORTAL_LABEL = "Montgomery County MD — Contracts"


async def run_montgomery_ingestion() -> dict[str, object]:
    run_id = await db.insert_scrape_run(SOURCE_PORTAL, metadata={"portal": PORTAL_LABEL})
    status = "FAILED"
    records_upserted = 0
    error_msg: str | None = None

    try:
        print(f"Run {run_id}: Starting Montgomery County ingestion...")
        async with aiohttp.ClientSession(headers={"User-Agent": settings.USER_AGENT}) as session:
            raw_records = await fetch_montgomery_records(session)

        if not raw_records:
            status = "SUCCESS"
        else:
            mapped = [map_montgomery_row(r) for r in raw_records]
            print(f"Run {run_id}: Upserting {len(mapped)} records...")
            records_upserted = await db.upsert_opportunities(mapped)
            status = "SUCCESS"

    except Exception as exc:
        error_msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(f"[ERROR] Montgomery County run failed: {error_msg}")
        await db.log_scrape_error(run_id, SOURCE_PORTAL, error_msg,
                                  raw_payload={"traceback": traceback.format_exc()})

    await db.finalize_scrape_run(run_id, status, records_upserted,
                                 metadata={"upserted": records_upserted, "error": error_msg})
    print(f"Run {run_id} complete: {status} — {records_upserted} records")
    return {"run_id": run_id, "status": status, "records_upserted": records_upserted}


async def _async_main() -> None:
    await db.create_pool()
    try:
        result = await run_montgomery_ingestion()
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.close_pool()


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
