"""
Virginia procurement ingestion entry point.

Runs two sources in sequence:
  1. eVA Non-IT portal (mvendor.cgieva.com) — Contracts, last 30 days, Solr API
  2. VITA IT portal (vita.cobblestonesystems.com) — all statewide IT contracts

Both upsert into the shared opportunities table.
"""

from __future__ import annotations

import asyncio
import json
import traceback

from backend.core import db
from backend.workers.virginia.eva_mapper import SOURCE_PORTAL as EVA_PORTAL, map_eva_contract
from backend.workers.virginia.eva_scraper import fetch_eva_contracts
from backend.workers.virginia.vita_mapper import SOURCE_PORTAL as VITA_PORTAL, map_vita_contract
from backend.workers.virginia.vita_scraper import fetch_vita_contracts


async def _run_source(
    source_portal: str,
    fetch_fn,
    map_fn,
    mode: str,
) -> dict[str, object]:
    """Generic runner: fetch → map → upsert for one Virginia source."""
    run_id = await db.insert_scrape_run(source_portal, metadata={"mode": mode})
    status = "FAILED"
    records_upserted = 0
    error_msg: str | None = None

    try:
        print(f"Run {run_id} [{source_portal}]: Fetching...")
        records = await fetch_fn()

        if not records:
            raise ValueError(f"No records returned from {source_portal}")

        mapped = [map_fn(r) for r in records]
        print(f"Run {run_id} [{source_portal}]: Upserting {len(mapped)} records...")
        records_upserted = await db.upsert_opportunities(mapped)
        status = "SUCCESS"

    except Exception as exc:
        error_msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(f"[ERROR] {source_portal} failed: {error_msg}")
        await db.log_scrape_error(
            run_id,
            source_portal,
            error_msg,
            raw_payload={"traceback": traceback.format_exc()},
        )

    await db.finalize_scrape_run(
        run_id,
        status,
        records_upserted,
        metadata={"upserted": records_upserted, "error": error_msg},
    )
    print(f"Run {run_id} [{source_portal}] complete: {status} ({records_upserted} records)")
    return {
        "run_id": run_id,
        "source": source_portal,
        "status": status,
        "records_upserted": records_upserted,
        "error": error_msg,
    }


async def run_virginia_ingestion() -> dict[str, object]:
    """Run both Virginia sources and return combined results."""
    eva_result = await _run_source(
        EVA_PORTAL,
        fetch_eva_contracts,
        map_eva_contract,
        mode="solr_api_last_30_days",
    )

    vita_result = await _run_source(
        VITA_PORTAL,
        fetch_vita_contracts,
        map_vita_contract,
        mode="cobblestone_grid_all",
    )

    total = (eva_result.get("records_upserted") or 0) + (vita_result.get("records_upserted") or 0)
    print(f"\nVirginia ingestion complete: {total} total records upserted")

    return {
        "eva": eva_result,
        "vita": vita_result,
        "total_upserted": total,
    }


async def _async_main() -> None:
    await db.create_pool()
    try:
        result = await run_virginia_ingestion()
        print(json.dumps(result, indent=2, default=str))
        # Exit 0 even if eVA failed — VITA success is enough
        # eVA failure is logged to scrape_errors for observability
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(_async_main())
