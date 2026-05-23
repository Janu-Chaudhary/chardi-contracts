"""Texas TxSmartBuy ingestion orchestration entry point."""

from __future__ import annotations

import asyncio
import json
import traceback

from backend.core import db
from backend.workers.texas.mapper import SOURCE_PORTAL, map_texas_row
from backend.workers.texas.scraper import fetch_texas_dataframe


async def run_texas_ingestion() -> dict[str, object]:
    """Fetch CSV via Playwright, map rows, and upsert into opportunities."""
    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={"mode": "playwright_csv_export"},
    )

    status = "FAILED"
    records_upserted = 0
    error_msg: str | None = None

    try:
        print(f"Run {run_id}: Fetching Texas TxSmartBuy data...")
        df = await fetch_texas_dataframe()

        if df.empty:
            raise ValueError("DataFrame returned empty from TxSmartBuy portal.")

        records = df.to_dict("records")
        mapped_tuples = [map_texas_row(row) for row in records]

        print(f"Run {run_id}: Upserting {len(mapped_tuples)} records...")
        records_upserted = await db.upsert_opportunities(mapped_tuples)
        status = "SUCCESS"

    except Exception as exc:
        error_msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(f"[ERROR] Texas run failed: {error_msg}")
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

    print(f"Run {run_id} complete with status: {status}")
    return {
        "run_id": run_id,
        "status": status,
        "records_upserted": records_upserted,
        "error": error_msg,
    }


async def _async_main() -> None:
    await db.create_pool()
    try:
        result = await run_texas_ingestion()
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(_async_main())
