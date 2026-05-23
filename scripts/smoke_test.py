#!/usr/bin/env python3
"""Quick Neon connectivity and ingestion observability check."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core import db


async def main() -> None:
    pool = await db.create_pool()
    try:
        total = await pool.fetchval("SELECT COUNT(*) FROM opportunities")
        print(f"opportunities_total: {total}")

        runs = await pool.fetch(
            """
            SELECT id, source_portal, start_time, end_time, records_scraped, status
            FROM scrape_runs
            ORDER BY id DESC
            LIMIT 5
            """
        )
        print("\nlatest_scrape_runs:")
        for row in runs:
            print(dict(row))

        errors = await pool.fetch(
            """
            SELECT id, run_id, source_portal, error_message, created_at
            FROM scrape_errors
            ORDER BY id DESC
            LIMIT 5
            """
        )
        print("\nlatest_scrape_errors:")
        for row in errors:
            print(dict(row))
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
