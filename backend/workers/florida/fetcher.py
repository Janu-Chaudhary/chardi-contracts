"""
Florida DMS State Contracts async fetcher.

List API: https://dms-media.ccplatform.net/api/search_contracts
  - Returns ALL contracts in a single call (pagination is UI-only)
  - No authentication required
  - ~2 seconds for 147 contracts

Detail pages: https://www.dms.myflorida.com/...
  - HTML pages with embedded __NEXT_DATA__ JSON
  - Contains description, benefits, commodity codes
  - Archive URLs (/archive/) often return HTTP 500 — skipped
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import aiohttp

from backend.core import settings

LIST_API_URL = "https://dms-media.ccplatform.net/api/search_contracts"
LIST_PARAMS = {
    "q": "",
    "page": "1",
    "type": "22065,4578,4110,4576,4577",
    "options": "includeExpired",
    "filterOptionsValue": "none",
}

MAX_DETAIL_CONCURRENCY = 8
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Archive URLs reliably return HTTP 500 from the server — skip them
SKIP_URL_PATTERN = re.compile(r"/archive/", re.IGNORECASE)

# Extract __NEXT_DATA__ JSON from HTML detail pages
NEXT_DATA_RE = re.compile(
    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.DOTALL,
)


async def fetch_contract_list(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """
    Fetch all Florida DMS contracts in a single API call.
    Returns the raw resultsObjects list.
    """
    async with session.get(
        LIST_API_URL,
        params=LIST_PARAMS,
        timeout=aiohttp.ClientTimeout(total=30),
        headers={"Accept": "application/json", "User-Agent": settings.USER_AGENT},
    ) as resp:
        resp.raise_for_status()
        data = await resp.json(content_type=None)

    contracts = data.get("resultsObjects") or []
    total = data.get("totalCount", len(contracts))
    print(f"[Florida] Fetched {len(contracts)} contracts (totalCount={total})")
    return contracts


async def _fetch_detail_page(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    url: str,
) -> dict[str, Any] | None:
    """
    Fetch one detail page and extract __NEXT_DATA__ JSON.
    Returns parsed pageData dict or None on failure.
    """
    if SKIP_URL_PATTERN.search(url):
        return None  # Archive URLs reliably 500

    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            async with semaphore:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": settings.USER_AGENT},
                    allow_redirects=True,
                ) as resp:
                    if resp.status in RETRYABLE_STATUS:
                        last_exc = aiohttp.ClientResponseError(
                            request_info=resp.request_info,
                            history=resp.history,
                            status=resp.status,
                        )
                        await asyncio.sleep(2 ** attempt)
                        continue
                    if resp.status >= 400:
                        return None  # 404 etc — skip silently
                    html = await resp.text(errors="replace")

            match = NEXT_DATA_RE.search(html)
            if not match:
                return None

            next_data = json.loads(match.group(1))
            page_data = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("pageData", {})
            )
            return page_data if page_data else None

        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as exc:
            last_exc = exc
            await asyncio.sleep(2 ** attempt)

    return None  # All retries exhausted


async def fetch_all_details(
    session: aiohttp.ClientSession,
    contracts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Fetch detail pages for all contracts concurrently.
    Returns dict mapping detail_url → pageData.
    """
    semaphore = asyncio.Semaphore(MAX_DETAIL_CONCURRENCY)
    urls = [
        c.get("link", {}).get("url", "")
        for c in contracts
        if c.get("link", {}).get("url")
    ]

    skipped = sum(1 for u in urls if SKIP_URL_PATTERN.search(u))
    fetchable = [u for u in urls if not SKIP_URL_PATTERN.search(u)]
    print(f"[Florida] Fetching {len(fetchable)} detail pages ({skipped} archive URLs skipped)...")

    tasks = [
        _fetch_detail_page(session, semaphore, url)
        for url in fetchable
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    detail_map: dict[str, dict[str, Any]] = {}
    errors = 0
    for url, result in zip(fetchable, results):
        if isinstance(result, BaseException) or result is None:
            errors += 1
        else:
            detail_map[url] = result

    print(f"[Florida] Details: {len(detail_map)} OK, {errors} failed/empty")
    return detail_map


def _strip_html(html_text: str | None) -> str | None:
    """Strip HTML tags from a string."""
    if not html_text:
        return None
    clean = re.sub(r"<[^>]+>", " ", html_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or None


def merge_contract_with_detail(
    contract: dict[str, Any],
    detail_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Merge list record with detail page data."""
    url = contract.get("link", {}).get("url", "")
    detail = detail_map.get(url, {})

    merged = dict(contract)

    if detail:
        # Extract description
        desc_html = (
            detail.get("description", {}).get("html5")
            or detail.get("description", {}).get("value")
            or ""
        )
        merged["description"] = _strip_html(desc_html)

        # Extract benefits
        benefits_html = (
            detail.get("benefits", {}).get("html5")
            or detail.get("benefits", {}).get("value")
            or ""
        )
        merged["benefits"] = _strip_html(benefits_html)

        # Extract category from detail (more specific than list)
        if detail.get("newCategory"):
            merged["detail_category"] = detail["newCategory"]

        # Commodity codes
        commodity = detail.get("commodityCodes") or detail.get("commodity_codes") or []
        merged["commodity_codes"] = commodity

    return merged
