"""New York State Contract Reporter (nyscr.ny.gov) ingestion entry point."""

from __future__ import annotations

import asyncio
import json
import traceback

from backend.core import db
from backend.workers.newyork.mapper import SOURCE_PORTAL, map_newyork_event
from backend.workers.newyork.scraper import fetch_newyork_events


async def run_newyork_ingestion() -> dict[str, object]:
    """Download NYSCR PDF, parse records, map, and upsert into opportunities."""
    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={"mode": "pdf_download_parse"},
    )

    status = "FAILED"
    records_upserted = 0
    error_msg: str | None = None

    try:
        print(f"Run {run_id}: Downloading New York NYSCR PDF...")
        events = await fetch_newyork_events()

        if not events:
            raise ValueError("No events parsed from NYSCR PDF.")

        print(f"Run {run_id}: Parsed {len(events)} records. Mapping and upserting...")
        mapped_tuples = [map_newyork_event(e) for e in events]
        records_upserted = await db.upsert_opportunities(mapped_tuples)
        status = "SUCCESS"

    except Exception as exc:
        error_msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(f"[ERROR] New York run failed: {error_msg}")
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
        metadata={"upserted": records_upserted, "error": error_msg},
    )

    print(f"Run {run_id} complete: {status} ({records_upserted} records)")
    return {
        "run_id": run_id,
        "status": status,
        "records_upserted": records_upserted,
        "error": error_msg,
    }


async def _async_main() -> None:
    await db.create_pool()
    try:
        result = await run_newyork_ingestion()
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(_async_main())
