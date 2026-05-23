"""
Chicago Contracts fetcher.

Daily mode: Socrata JSON API
  https://data.cityofchicago.org/resource/rsxa-ify5.json
  Uses aiohttp, SoQL server-side 2026 filter, paginates with $limit/$offset.

Returns only records whose start_date falls in calendar year 2026.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Any

import aiohttp

from backend.core import settings

DAILY_API_URL = "https://data.cityofchicago.org/resource/rsxa-ify5.json"
PAGE_LIMIT = 1000
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
FILTER_YEAR = 2026


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    text = str(val).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt)
        except ValueError:
            continue
    return None


def _filter_2026(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if (dt := _parse_date(r.get("start_date"))) and dt.year == FILTER_YEAR]


async def _fetch_page(session: aiohttp.ClientSession, offset: int) -> list[dict[str, Any]]:
    """Fetch one page with retry/backoff. Uses SoQL 2026 filter server-side."""
    params = {
        "$limit": PAGE_LIMIT,
        "$offset": offset,
        "$order": "start_date DESC",
        "$where": "start_date >= '2026-01-01T00:00:00.000' AND start_date <= '2026-12-31T23:59:59.999'",
    }
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(
                DAILY_API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT_SECONDS),
                headers={"User-Agent": settings.USER_AGENT, "Accept": "application/json"},
            ) as resp:
                if resp.status in RETRYABLE_STATUS:
                    last_exc = aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=resp.status,
                    )
                    await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 1.5))
                    continue
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_exc = exc
            await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 1.5))

    raise RuntimeError(
        f"Chicago API request failed after {MAX_RETRIES} attempts (offset={offset})"
    ) from last_exc


async def fetch_daily_json(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Paginate the Socrata JSON API and return all 2026 Chicago contract records."""
    all_records: list[dict[str, Any]] = []
    offset = 0

    while True:
        page = await _fetch_page(session, offset)
        all_records.extend(page)
        print(f"[Chicago] Fetched page offset={offset}: {len(page)} records")
        if len(page) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT

    # Server-side filter already limits to 2026, but apply local filter as safety net
    filtered = _filter_2026(all_records)
    print(f"[Chicago] Total fetched: {len(all_records)}, after 2026 filter: {len(filtered)}")
    return filtered
