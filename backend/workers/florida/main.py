"""Florida DMS State Contracts ingestion entry point."""

from __future__ import annotations

import asyncio
import json
import traceback

import aiohttp

from backend.core import db, settings
from backend.workers.florida.fetcher import (
    fetch_all_details,
    fetch_contract_list,
    merge_contract_with_detail,
)
from backend.workers.florida.mapper import SOURCE_PORTAL, map_florida_contract


async def run_florida_ingestion() -> dict[str, object]:
    """
    Fetch Florida DMS contracts via REST API, enrich with detail pages,
    map to tuples, and upsert into opportunities.
    """
    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={"mode": "rest_api_with_detail_pages", "portal": "Florida DMS"},
    )

    status = "FAILED"
    records_upserted = 0
    error_msg: str | None = None

    try:
        print(f"Run {run_id}: Fetching Florida DMS contracts...")

        async with aiohttp.ClientSession(
            headers={"User-Agent": settings.USER_AGENT}
        ) as session:
            # Step 1: Fetch all contracts from the list API (single call)
            contracts = await fetch_contract_list(session)

            if not contracts:
                raise ValueError("No contracts returned from Florida DMS API.")

            # Step 2: Fetch detail pages concurrently for descriptions
            detail_map = await fetch_all_details(session, contracts)

        # Step 3: Merge list + detail data
        merged = [
            merge_contract_with_detail(c, detail_map)
            for c in contracts
        ]

        # Step 4: Map to upsert tuples
        mapped_tuples = [map_florida_contract(r) for r in merged]
        print(f"Run {run_id}: Upserting {len(mapped_tuples)} records...")
        records_upserted = await db.upsert_opportunities(mapped_tuples)
        status = "SUCCESS"

    except Exception as exc:
        error_msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        print(f"[ERROR] Florida run failed: {error_msg}")
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

    print(f"Run {run_id} complete: {status} — {records_upserted} records")
    return {
        "run_id": run_id,
        "status": status,
        "records_upserted": records_upserted,
        "error": error_msg,
    }


async def _async_main() -> None:
    await db.create_pool()
    try:
        result = await run_florida_ingestion()
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(_async_main())
