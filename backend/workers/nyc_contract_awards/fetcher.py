"""
NYC Contract Awards fetcher.

Two modes:
  - daily:   Socrata JSON API  https://data.cityofnewyork.us/resource/qyyg-4tf5.json
             Uses aiohttp, paginates with $limit/$offset (1 000 records/page).
  - initial: Full CSV export   https://data.cityofnewyork.us/api/views/qyyg-4tf5/rows.csv
             Uses stdlib only (urllib.request + csv.DictReader), streams the ~35 MB file.

Both modes return only records whose start_date falls in calendar year 2026.
"""

from __future__ import annotations

import asyncio
import csv
import io
import random
import urllib.request
from datetime import datetime
from typing import Any

import aiohttp

from backend.core import settings

# ── Endpoints ────────────────────────────────────────────────────────────────
DAILY_API_URL = "https://data.cityofnewyork.us/resource/qyyg-4tf5.json"
CSV_EXPORT_URL = (
    "https://data.cityofnewyork.us/api/views/qyyg-4tf5/rows.csv?accessType=DOWNLOAD"
)

# ── Pagination / retry config ─────────────────────────────────────────────────
PAGE_LIMIT = 1000
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
FILTER_YEAR = 2026


# ── Shared date parser ────────────────────────────────────────────────────────

def _parse_date(val: str | None) -> datetime | None:
    """Parse ISO 8601 or date-only strings to datetime. Returns None on failure."""
    if not val:
        return None
    text = str(val).strip()
    if not text:
        return None
    # Try full ISO with time component first
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    # Try date-only
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt)
        except ValueError:
            continue
    return None


def _filter_2026(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only records whose start_date falls in 2026."""
    result = []
    for r in records:
        dt = _parse_date(r.get("start_date") or r.get("Start Date") or "")
        if dt and dt.year == FILTER_YEAR:
            result.append(r)
    return result


# ── Daily mode (aiohttp + JSON API) ──────────────────────────────────────────

async def _fetch_page(
    session: aiohttp.ClientSession,
    offset: int,
) -> list[dict[str, Any]]:
    """Fetch one page from the Socrata JSON API with retry/backoff.

    Uses SoQL server-side filter for 2026 start_date so we only download
    relevant records instead of paginating through all 52k rows.
    """
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
                headers={
                    "User-Agent": settings.USER_AGENT,
                    "Accept": "application/json",
                },
            ) as resp:
                if resp.status in RETRYABLE_STATUS:
                    last_exc = aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=resp.status,
                    )
                    delay = (2 ** attempt) + random.uniform(0.1, 1.5)
                    await asyncio.sleep(delay)
                    continue
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_exc = exc
            delay = (2 ** attempt) + random.uniform(0.1, 1.5)
            await asyncio.sleep(delay)

    raise RuntimeError(
        f"NYC API request failed after {MAX_RETRIES} attempts (offset={offset})"
    ) from last_exc


async def fetch_daily_json(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """
    Paginate the Socrata JSON API and return all 2026 contract award records.

    Stops when a page returns fewer than PAGE_LIMIT records.
    """
    all_records: list[dict[str, Any]] = []
    offset = 0

    while True:
        page = await _fetch_page(session, offset)
        all_records.extend(page)
        print(f"[NYC] Fetched page offset={offset}: {len(page)} records")
        if len(page) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT

    filtered = _filter_2026(all_records)
    print(f"[NYC] Total fetched: {len(all_records)}, after 2026 filter: {len(filtered)}")
    return filtered


# ── Initial load mode (stdlib CSV) ───────────────────────────────────────────

def fetch_initial_csv() -> list[dict[str, Any]]:
    """
    Download the full NYC contract awards CSV (~35 MB) using stdlib only.

    Streams the response through csv.DictReader — does not load the whole
    file into memory at once. Returns only 2026 records.
    """
    req = urllib.request.Request(
        CSV_EXPORT_URL,
        headers={"User-Agent": settings.USER_AGENT},
    )
    print(f"[NYC] Downloading full CSV from {CSV_EXPORT_URL} ...")

    with urllib.request.urlopen(req, timeout=600) as resp:
        if resp.status != 200:
            raise RuntimeError(f"CSV download failed: HTTP {resp.status}")

        wrapper = io.TextIOWrapper(resp, encoding="utf-8", errors="replace")
        reader = csv.DictReader(wrapper)
        all_records = list(reader)

    print(f"[NYC] CSV rows read: {len(all_records)}")
    filtered = _filter_2026(all_records)
    print(f"[NYC] After 2026 filter: {len(filtered)}")
    return filtered
