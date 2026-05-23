"""
Oregon OregonBuys Purchases and Contracts fetcher.
Source: data.oregon.gov Socrata API — dataset qyug-f2km

No date filter — full history required for award enrichment corpus.
All records are AWARDED status, used to build "who has won similar" feature.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import aiohttp

from backend.core import settings

API_URL = "https://data.oregon.gov/resource/qyug-f2km.json"
PAGE_LIMIT = 1000
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


async def _fetch_page(session: aiohttp.ClientSession, offset: int) -> list[dict[str, Any]]:
    """Fetch one page — no date filter, full history for award corpus."""
    params = {
        "$limit": PAGE_LIMIT,
        "$offset": offset,
        "$order": "sent_date DESC",
    }
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(
                API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT_SECONDS),
                headers={"User-Agent": settings.USER_AGENT, "Accept": "application/json"},
            ) as resp:
                if resp.status in RETRYABLE_STATUS:
                    await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 1.5))
                    continue
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_exc = exc
            await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 1.5))
    raise RuntimeError(f"Oregon API failed after {MAX_RETRIES} attempts") from last_exc


async def fetch_oregon_records(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Paginate full Oregon award history — all records, no date filter."""
    all_records: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = await _fetch_page(session, offset)
        all_records.extend(page)
        print(f"[Oregon] offset={offset}: {len(page)} records (total so far: {len(all_records)})")
        if len(page) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT
    print(f"[Oregon] Full history: {len(all_records)} records")
    return all_records
