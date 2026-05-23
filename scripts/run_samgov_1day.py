#!/usr/bin/env python3
"""Run SAM.gov ingestion for the last 1 calendar day."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core import db
from backend.workers.samgov.main import run_samgov_ingestion


async def main() -> None:
    await db.create_pool()
    try:
        result = await run_samgov_ingestion(days=1)
        print(result)
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
