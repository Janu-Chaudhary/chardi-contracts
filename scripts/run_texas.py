"""Run Texas TxSmartBuy ingestion — convenience script."""

import asyncio
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core import db
from backend.workers.texas.main import run_texas_ingestion
import json


async def main() -> None:
    await db.create_pool()
    try:
        result = await run_texas_ingestion()
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
