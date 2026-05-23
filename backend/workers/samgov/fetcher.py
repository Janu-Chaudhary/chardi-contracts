"""Async SAM.gov opportunities API client with retries and pagination."""

from __future__ import annotations

import asyncio
import random
from datetime import date, timedelta
from typing import Any

import aiohttp

from backend.core import settings

PAGE_LIMIT = 1000
MAX_RETRIES = 5
CONCURRENCY_LIMIT = 3  # Reduced from 5 to 3 for better rate limit handling
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def format_sam_date(d: date) -> str:
    """Format a date for SAM.gov postedFrom/postedTo (MM/dd/yyyy)."""
    return d.strftime("%m/%d/%Y")


def iter_date_windows(end: date, days: int) -> list[tuple[str, str]]:
    """
    Build per-day (postedFrom, postedTo) pairs for the last `days` days inclusive.

    Structured for future partitioning by day or ptype without changing callers.
    """
    windows: list[tuple[str, str]] = []
    for offset in range(days):
        day = end - timedelta(days=offset)
        label = format_sam_date(day)
        windows.append((label, label))
    return windows


class SamGovFetcher:
    """Concurrent SAM.gov search client with semaphore-limited requests."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        self._timeout = aiohttp.ClientTimeout(
            total=60,
            connect=15,
            sock_read=settings.REQUEST_TIMEOUT_SECONDS,
        )

    def _build_params(
        self,
        posted_from: str,
        posted_to: str,
        offset: int,
        ptype: str | None = None,
    ) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "api_key": settings.SAM_GOV_API_KEY,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": PAGE_LIMIT,
            "offset": offset,
        }
        if ptype:
            params["ptype"] = ptype
        return params

    async def _backoff_sleep(self, attempt: int, status: int | None = None) -> None:
        """
        Exponential backoff with jitter.
        
        Formula: (2 ** attempt) + random.uniform(0.1, 1.5)
        Max base delay capped at 60 seconds.
        """
        base = min(2**attempt, 60)
        jitter = random.uniform(0.1, 1.5)
        delay = base + jitter
        await asyncio.sleep(delay)

    async def fetch_page(
        self,
        posted_from: str,
        posted_to: str,
        offset: int = 0,
        ptype: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch one SAM.gov search page.

        Retries up to MAX_RETRIES on 429/5xx or transport errors.
        CRITICAL: Backoff sleeps occur OUTSIDE the concurrency semaphore to release the slot.
        
        Daily Quota Handling:
        - 429 with 'nextAccessTime' in response → Fatal error (daily quota exhausted)
        - 429 without 'nextAccessTime' → Retry with backoff (temporary rate limit)
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            should_retry = False
            retry_status = None
            
            try:
                async with self._semaphore:
                    async with self._session.get(
                        settings.SAM_GOV_BASE_URL,
                        params=self._build_params(posted_from, posted_to, offset, ptype),
                        timeout=self._timeout,
                        headers={
                            "User-Agent": settings.USER_AGENT,
                            "Accept": "application/json",
                        },
                    ) as response:
                        if response.status in RETRYABLE_STATUS:
                            response_text = await response.text()
                            
                            # Check for daily quota exhaustion (429 with nextAccessTime)
                            if response.status == 429 and "nextAccessTime" in response_text:
                                raise RuntimeError(
                                    f"SAM.gov daily quota exhausted. API locked until reset time. "
                                    f"Response: {response_text}"
                                )
                            
                            # Temporary rate limit or server error - retry with backoff
                            should_retry = True
                            retry_status = response.status
                            last_error = aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=response_text,
                            )
                        else:
                            response.raise_for_status()
                            return await response.json()
                
                # Backoff sleep OUTSIDE semaphore if we need to retry
                if should_retry:
                    await self._backoff_sleep(attempt, retry_status)
                    continue
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                # Backoff sleep OUTSIDE semaphore for transport errors
                await self._backoff_sleep(attempt)

        raise RuntimeError(
            f"SAM.gov request failed after {MAX_RETRIES} attempts "
            f"({posted_from}..{posted_to} offset={offset})"
        ) from last_error

    async def collect_paginated_notices(
        self,
        posted_from: str,
        posted_to: str,
        ptype: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all pages for a date window and return notice dicts."""
        offset = 0
        notices: list[dict[str, Any]] = []
        total_records: int | None = None

        while True:
            payload = await self.fetch_page(posted_from, posted_to, offset, ptype)
            batch = payload.get("opportunitiesData") or []
            if not isinstance(batch, list):
                batch = []

            notices.extend(batch)

            if total_records is None:
                total_records = int(payload.get("totalRecords") or 0)

            offset += PAGE_LIMIT
            if offset >= total_records or not batch:
                break

        return notices

    async def fetch_notices_for_range(
        self,
        posted_from: str,
        posted_to: str,
        ptype: str | None = None,
    ) -> list[dict[str, Any]]:
        """Public helper for one postedFrom/postedTo window."""
        return await self.collect_paginated_notices(posted_from, posted_to, ptype)


async def create_session() -> aiohttp.ClientSession:
    """Build a shared aiohttp session for a worker run."""
    return aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60, connect=15),
        headers={"User-Agent": settings.USER_AGENT},
    )
