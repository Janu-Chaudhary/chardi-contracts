"""
SAM.gov Historical Backfill — April 14 to May 14, 2026
=======================================================

Run once to backfill historical SAM.gov data using a dedicated API key.

Features:
- Sequential day-by-day processing (no concurrency) to stay under rate limits
- Graceful quota-exhaustion handling: saves progress and exits cleanly
- Resume support: skips days already in the DB (checks by posted_date)
- Detailed console progress logging

Usage:
    .venv/bin/python -m backend.workers.samgov.backfill_historical

    # Or override date range:
    .venv/bin/python -m backend.workers.samgov.backfill_historical \
        --start 2026-04-14 --end 2026-05-14
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import traceback
from datetime import date, timedelta
from typing import Any

import aiohttp
import asyncpg

from backend.core import db, settings
from backend.workers.samgov.mapper import map_notice_to_tuple, SOURCE_PORTAL

# ── Config ────────────────────────────────────────────────────────────────────

BACKFILL_API_KEY = "SAM-34e9bd8c-e76c-4ecc-9dd5-294731a5935e"
DEFAULT_START = date(2026, 4, 14)
DEFAULT_END = date(2026, 5, 14)

PAGE_LIMIT = 1000
MAX_RETRIES = 6
# Sequential — no semaphore needed, but keep a small delay between pages
INTER_PAGE_DELAY = 1.0   # seconds between paginated requests
INTER_DAY_DELAY = 2.0    # seconds between days


# ── Date helpers ──────────────────────────────────────────────────────────────

def fmt(d: date) -> str:
    """Format date as MM/dd/yyyy for SAM.gov API."""
    return d.strftime("%m/%d/%Y")


def date_range(start: date, end: date) -> list[date]:
    """Return list of dates from start to end inclusive, oldest first."""
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


# ── Already-ingested check ────────────────────────────────────────────────────

async def get_ingested_dates(pool: asyncpg.Pool, start: date, end: date) -> set[date]:
    """
    Return the set of posted_dates already present in the DB for SAM.gov
    within the backfill window. Used to skip days we already have.
    """
    rows = await pool.fetch(
        """
        SELECT DISTINCT posted_date::date AS d
        FROM opportunities
        WHERE source_portal = $1
          AND posted_date::date BETWEEN $2 AND $3
        """,
        SOURCE_PORTAL,
        start,
        end,
    )
    return {row["d"] for row in rows}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def backoff_sleep(attempt: int) -> None:
    base = min(2 ** attempt, 60)
    jitter = random.uniform(0.5, 2.0)
    delay = base + jitter
    print(f"    ↳ backoff sleep {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
    await asyncio.sleep(delay)


async def fetch_page(
    session: aiohttp.ClientSession,
    posted_from: str,
    posted_to: str,
    offset: int,
) -> dict[str, Any] | None:
    """
    Fetch one page from SAM.gov.

    Returns:
        dict  — parsed JSON on success
        None  — quota exhausted (caller should stop the whole run)

    Raises:
        RuntimeError — after MAX_RETRIES on persistent errors
    """
    params = {
        "api_key": BACKFILL_API_KEY,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "limit": PAGE_LIMIT,
        "offset": offset,
    }
    timeout = aiohttp.ClientTimeout(total=90, connect=15, sock_read=60)
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(
                settings.SAM_GOV_BASE_URL,
                params=params,
                timeout=timeout,
                headers={
                    "User-Agent": settings.USER_AGENT,
                    "Accept": "application/json",
                },
            ) as resp:
                if resp.status == 429:
                    body = await resp.text()
                    if "nextAccessTime" in body:
                        # Daily quota exhausted — signal caller to stop
                        print(f"\n  ⛔  Daily quota exhausted. API response: {body[:300]}")
                        return None
                    # Temporary rate limit — back off and retry
                    print(f"    ↳ 429 rate limit (no quota marker), retrying…")
                    last_error = aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=429,
                        message=body,
                    )
                    await backoff_sleep(attempt)
                    continue

                if resp.status in {500, 502, 503, 504}:
                    body = await resp.text()
                    last_error = aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=resp.status,
                        message=body,
                    )
                    await backoff_sleep(attempt)
                    continue

                resp.raise_for_status()
                return await resp.json()

        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_error = exc
            await backoff_sleep(attempt)

    raise RuntimeError(
        f"SAM.gov request failed after {MAX_RETRIES} attempts "
        f"({posted_from} offset={offset})"
    ) from last_error


async def fetch_all_pages_for_day(
    session: aiohttp.ClientSession,
    day: date,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Fetch all paginated results for a single day.

    Returns:
        (notices, quota_hit)
        quota_hit=True means the daily limit was reached mid-fetch.
    """
    label = fmt(day)
    offset = 0
    notices: list[dict[str, Any]] = []
    total_records: int | None = None

    while True:
        payload = await fetch_page(session, label, label, offset)

        if payload is None:
            # Quota exhausted — return whatever we collected so far
            return notices, True

        batch = payload.get("opportunitiesData") or []
        if not isinstance(batch, list):
            batch = []

        notices.extend(batch)

        if total_records is None:
            total_records = int(payload.get("totalRecords") or 0)

        offset += PAGE_LIMIT

        if offset >= total_records or not batch:
            break

        # Small delay between pages to be polite
        await asyncio.sleep(INTER_PAGE_DELAY)

    return notices, False


# ── Main backfill logic ───────────────────────────────────────────────────────

async def run_backfill(start: date, end: date) -> None:
    pool = await db.create_pool()

    print(f"\n{'='*60}")
    print(f"  SAM.gov Historical Backfill")
    print(f"  Range : {start} → {end}")
    print(f"  API   : {BACKFILL_API_KEY[:12]}…")
    print(f"{'='*60}\n")

    # Check which days are already in the DB
    ingested = await get_ingested_dates(pool, start, end)
    all_days = date_range(start, end)
    pending_days = [d for d in all_days if d not in ingested]

    print(f"  Total days in range : {len(all_days)}")
    print(f"  Already in DB       : {len(ingested)}")
    print(f"  Days to fetch       : {len(pending_days)}\n")

    if not pending_days:
        print("  ✅  Nothing to do — all days already ingested.")
        await db.close_pool()
        return

    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={
            "mode": "historical_backfill",
            "start": str(start),
            "end": str(end),
            "pending_days": len(pending_days),
        },
    )

    total_upserted = 0
    days_done = 0
    quota_hit = False

    session = aiohttp.ClientSession(
        headers={"User-Agent": settings.USER_AGENT},
    )

    try:
        for day in pending_days:
            print(f"  [{days_done + 1}/{len(pending_days)}] Fetching {day} …", end=" ", flush=True)

            try:
                notices, quota_hit = await fetch_all_pages_for_day(session, day)
            except Exception as exc:
                msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
                print(f"ERROR — {msg}")
                await db.log_scrape_error(
                    run_id, SOURCE_PORTAL, msg,
                    raw_payload={"day": str(day), "traceback": traceback.format_exc()},
                )
                if quota_hit:
                    break
                continue

            if notices:
                tuples = [map_notice_to_tuple(n) for n in notices]
                written = await db.upsert_opportunities(tuples)
                total_upserted += written
                print(f"fetched={len(notices)}  upserted={written}")
            else:
                print("fetched=0  (no records for this day)")

            days_done += 1

            if quota_hit:
                print(f"\n  ⛔  Quota hit after {days_done} days. Stopping gracefully.")
                break

            # Polite delay between days
            await asyncio.sleep(INTER_DAY_DELAY)

    finally:
        await session.close()

    # Finalize scrape run
    if quota_hit and days_done == 0:
        final_status = "FAILED"
    elif quota_hit:
        final_status = "PARTIAL_SUCCESS"
    else:
        final_status = "SUCCESS"

    remaining = len(pending_days) - days_done
    await db.finalize_scrape_run(
        run_id,
        final_status,
        total_upserted,
        metadata={
            "mode": "historical_backfill",
            "start": str(start),
            "end": str(end),
            "days_attempted": days_done,
            "days_remaining": remaining,
            "total_upserted": total_upserted,
            "quota_hit": quota_hit,
        },
    )

    print(f"\n{'='*60}")
    print(f"  Status          : {final_status}")
    print(f"  Days processed  : {days_done} / {len(pending_days)}")
    print(f"  Records upserted: {total_upserted}")
    if quota_hit and remaining > 0:
        print(f"  Days remaining  : {remaining}  (re-run to continue)")
    print(f"{'='*60}\n")

    await db.close_pool()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill SAM.gov historical data (Apr 14 → May 14, 2026)"
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=DEFAULT_START,
        help="Start date inclusive (YYYY-MM-DD), default: 2026-04-14",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=DEFAULT_END,
        help="End date inclusive (YYYY-MM-DD), default: 2026-05-14",
    )
    args = parser.parse_args()

    if args.start > args.end:
        raise SystemExit("--start must be before or equal to --end")

    asyncio.run(run_backfill(args.start, args.end))


if __name__ == "__main__":
    main()
