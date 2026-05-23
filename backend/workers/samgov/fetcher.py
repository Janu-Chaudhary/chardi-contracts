"""Async SAM.gov opportunities API client with retries and pagination."""

from __future__ import annotations

import asyncio
import random
from datetime import date, timedelta
from typing import Any

import aiohttp

from backend.core import settings

PAGE_LIMIT = 1000
MAX_RETRIES = 6
INTER_PAGE_DELAY = 1.0   # seconds between paginated requests within a day
INTER_DAY_DELAY = 2.0    # seconds between day windows
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class QuotaExhaustedError(RuntimeError):
    """Raised when SAM.gov daily API quota is exhausted (429 + nextAccessTime)."""


def format_sam_date(d: date) -> str:
    """Format a date for SAM.gov postedFrom/postedTo (MM/dd/yyyy)."""
    return d.strftime("%m/%d/%Y")


def iter_date_windows(end: date, days: int) -> list[tuple[str, str]]:
    """
    Build per-day (postedFrom, postedTo) pairs for the last `days` days inclusive.
    """
    windows: list[tuple[str, str]] = []
    for offset in range(days):
        day = end - timedelta(days=offset)
        label = format_sam_date(day)
        windows.append((label, label))
    return windows


class SamGovFetcher:
    """Sequential SAM.gov search client — one day at a time to maximise quota usage."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._timeout = aiohttp.ClientTimeout(
            total=90,
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

    async def _backoff_sleep(self, attempt: int) -> None:
        """Exponential backoff with jitter. Max base delay capped at 60s."""
        base = min(2 ** attempt, 60)
        jitter = random.uniform(0.5, 2.0)
        await asyncio.sleep(base + jitter)

    async def fetch_page(
        self,
        posted_from: str,
        posted_to: str,
        offset: int = 0,
        ptype: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch one SAM.gov search page with retries.

        Raises:
            QuotaExhaustedError — daily quota hit (429 + nextAccessTime).
                                  Caller should stop the entire run.
            RuntimeError        — persistent failure after MAX_RETRIES.
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.get(
                    settings.SAM_GOV_BASE_URL,
                    params=self._build_params(posted_from, posted_to, offset, ptype),
                    timeout=self._timeout,
                    headers={
                        "User-Agent": settings.USER_AGENT,
                        "Accept": "application/json",
                    },
                ) as response:
                    if response.status == 429:
                        body = await response.text()
                        if "nextAccessTime" in body:
                            raise QuotaExhaustedError(
                                f"SAM.gov daily quota exhausted. "
                                f"Response: {body[:300]}"
                            )
                        # Temporary rate limit — back off and retry
                        last_error = aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=429,
                            message=body,
                        )
                        await self._backoff_sleep(attempt)
                        continue

                    if response.status in {500, 502, 503, 504}:
                        body = await response.text()
                        last_error = aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=body,
                        )
                        await self._backoff_sleep(attempt)
                        continue

                    response.raise_for_status()
                    return await response.json()

            except QuotaExhaustedError:
                raise  # propagate immediately — no retry

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
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
        """
        Fetch all pages for a date window sequentially.

        Raises QuotaExhaustedError if quota is hit mid-pagination.
        """
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

            # Polite delay between pages
            await asyncio.sleep(INTER_PAGE_DELAY)

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
        timeout=aiohttp.ClientTimeout(total=90, connect=15),
        headers={"User-Agent": settings.USER_AGENT},
    )
