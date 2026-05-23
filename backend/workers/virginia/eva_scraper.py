"""
Virginia eVA Non-IT public search portal scraper.

Portal: https://mvendor.cgieva.com/Vendor/public/PublicSearch.jsp
Approach:
  1. Load portal with retries (handles 403 / timeout / React hydration)
  2. Apply UI filters: Contracts only, start_date = last 30 days
  3. Fetch all matching docs from the Solr API using the browser session
  4. Return list of raw Solr doc dicts

Adapted from /home/janu-chaudhary/AAA/portal_browser.py (working Cursor script).
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import quote

from playwright.async_api import Page, Playwright, Response

PORTAL_URL = "https://mvendor.cgieva.com/Vendor/public/PublicSearch.jsp"
SEARCH_BUTTON = "#topNavSrchBtn"
DATE_INPUT = ".react-datepicker__input-container input, .react-datepicker-wrapper input"
PARENT_FQ = (
    "%7B!parent%20which%3Dtype_s%3A(%22PO%22%2C%22Supplier%22%2C%22Contract%22)%7D"
)
LAST_MONTH_DAYS = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
LAUNCH_ARGS = [
    "--headless=new",
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]
WEBDRIVER_PATCH = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
)

MAX_RETRIES = 5
RETRY_BACKOFF_SEC = 2.0
GOTO_TIMEOUT_MS = 90_000
HYDRATE_TIMEOUT_MS = 45_000
MIN_HTML_BYTES = 25_000
SOLR_ROWS_PER_PAGE = 50
SOLR_REQUEST_TIMEOUT_MS = 120_000


class EvaPortalError(RuntimeError):
    """Portal blocked, timed out, or failed to hydrate."""


# ── Date helpers ──────────────────────────────────────────────────────────────

def get_last_month_range(*, days: int = LAST_MONTH_DAYS) -> dict[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return {
        "from_display": start.strftime("%m/%d/%Y"),
        "to_display": end.strftime("%m/%d/%Y"),
        "from_iso": start.strftime("%Y-%m-%dT00:00:00.000Z"),
        "to_iso": end.strftime("%Y-%m-%dT23:59:59.999Z"),
    }


# ── Solr URL builder ──────────────────────────────────────────────────────────

def contracts_last_month_solr_url(
    *,
    rows: int = SOLR_ROWS_PER_PAGE,
    cursor_mark: str = "*",
    date_range: dict[str, str] | None = None,
) -> str:
    dates = date_range or get_last_month_range()
    fq_date = quote(
        f"start_date:[{dates['from_iso']} TO {dates['to_iso']}]",
        safe="",
    )
    return (
        "https://mvendor.cgieva.com/search/solrConnect.jsp?select?"
        "q=type_s%3A(%22Contract%22)"
        "&fq=type_s%3A(%22Contract%22)"
        f"&fq={fq_date}"
        f"&fq={PARENT_FQ}"
        "&sort=score%20desc,id%20desc"
        "&wt=json&facet=off"
        f"&rows={rows}"
        f"&cursorMark={quote(cursor_mark, safe='')}"
    )


# ── Portal hydration checks ───────────────────────────────────────────────────

def _page_blocked(html: str) -> bool:
    return "403 Forbidden" in html or len(html) < 1000


def _portal_hydrated(html: str) -> bool:
    if _page_blocked(html):
        return False
    if len(html) < MIN_HTML_BYTES:
        return False
    return (
        "react-datepicker" in html
        or "eVA Search Portal" in html
        or "topNavSrchBtn" in html
    )


# ── Browser helpers ───────────────────────────────────────────────────────────

async def _open_portal_page(playwright: Playwright) -> tuple[object, Page]:
    browser = await playwright.chromium.launch(headless=True, args=LAUNCH_ARGS)
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
        },
    )
    page = await context.new_page()
    await page.add_init_script(WEBDRIVER_PATCH)
    return browser, page


async def _goto_portal(page: Page) -> None:
    last_error: Exception | None = None
    for wait_until in ("domcontentloaded", "load", "commit"):
        try:
            response = await page.goto(
                PORTAL_URL, wait_until=wait_until, timeout=GOTO_TIMEOUT_MS
            )
            if response and response.status >= 400:
                raise EvaPortalError(f"HTTP {response.status} loading portal")
            return
        except Exception as exc:
            last_error = exc
            if _portal_hydrated(await page.content()):
                return
    raise EvaPortalError(f"Navigation failed: {last_error}") from last_error


async def _wait_for_hydration(page: Page) -> str:
    try:
        await page.wait_for_selector(
            SEARCH_BUTTON, state="visible", timeout=HYDRATE_TIMEOUT_MS
        )
    except Exception:
        pass

    loop = asyncio.get_running_loop()
    deadline = loop.time() + HYDRATE_TIMEOUT_MS / 1000
    while loop.time() < deadline:
        html = await page.content()
        if _portal_hydrated(html):
            return html
        await page.wait_for_timeout(750)

    html = await page.content()
    if _portal_hydrated(html):
        return html
    raise EvaPortalError(f"Portal UI did not hydrate ({len(html)} bytes)")


async def _load_portal_with_retry(playwright: Playwright) -> tuple[object, Page]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[eVA] Portal load attempt {attempt}/{MAX_RETRIES}...")
        browser, page = await _open_portal_page(playwright)
        try:
            await _goto_portal(page)
            await _wait_for_hydration(page)
            print(f"[eVA] Portal ready (title={await page.title()!r})")
            return browser, page
        except Exception as exc:
            last_error = exc
            await browser.close()
            print(f"[eVA] Attempt {attempt} failed: {exc}")
            if attempt < MAX_RETRIES:
                delay = RETRY_BACKOFF_SEC * (2 ** (attempt - 1)) + random.uniform(0, 1)
                await asyncio.sleep(delay)

    raise EvaPortalError(f"All {MAX_RETRIES} attempts failed") from last_error


# ── UI filter application ─────────────────────────────────────────────────────

async def _apply_filters(page: Page) -> dict[str, str]:
    """Apply Contracts + last-30-days date filter in the portal UI."""
    dates = get_last_month_range()

    # Wait for facet sidebar
    await page.wait_for_function(
        "() => document.body.innerText.includes('Purchase Orders')"
        " && document.body.innerText.includes('Contracts')",
        timeout=60_000,
    )

    # Click Contracts facet
    clicked = await page.evaluate(
        """() => {
            for (const el of document.querySelectorAll('div, li, span, a')) {
                const t = el.innerText?.trim() || '';
                if (/^Contracts\\n\\d+$/.test(t) && el.offsetParent) {
                    el.click();
                    return true;
                }
            }
            return false;
        }"""
    )
    if not clicked:
        raise EvaPortalError("Could not click Contracts facet")

    await page.wait_for_timeout(1500)
    await page.get_by_text("Advanced Filters", exact=True).click()
    await page.wait_for_timeout(500)
    await page.get_by_text("Date (PO & Contract)", exact=False).click()
    await page.wait_for_timeout(500)

    date_inputs = page.locator(DATE_INPUT)
    if await date_inputs.count() < 2:
        raise EvaPortalError("Date filter inputs not found")

    await date_inputs.nth(0).fill(dates["from_display"])
    await date_inputs.nth(1).fill(dates["to_display"])
    await page.get_by_role("button", name="Go").click()
    await page.wait_for_timeout(3000)
    return dates


# ── Solr pagination ───────────────────────────────────────────────────────────

async def _fetch_solr_batch(page: Page, url: str) -> dict:
    headers = {"Accept": "application/json", "Referer": PORTAL_URL}
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            response = await page.context.request.get(
                url, headers=headers, timeout=SOLR_REQUEST_TIMEOUT_MS
            )
            if response.status >= 400:
                raise EvaPortalError(f"Solr HTTP {response.status}")
            text = await response.text()
            if text.lstrip().startswith("{"):
                return json.loads(text)
            raise EvaPortalError(f"Unexpected Solr body: {text[:200]}")
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                await asyncio.sleep(2)
    raise EvaPortalError(f"Solr request failed: {last_exc}") from last_exc


async def _fetch_all_solr_pages(
    page: Page,
    date_range: dict[str, str],
) -> list[dict]:
    all_docs: list[dict] = []
    cursor = "*"
    num_found = 0
    target: int | None = None

    while True:
        if target is not None and len(all_docs) >= target:
            break
        url = contracts_last_month_solr_url(
            rows=SOLR_ROWS_PER_PAGE,
            cursor_mark=cursor,
            date_range=date_range,
        )
        payload = await _fetch_solr_batch(page, url)
        batch = payload.get("response", {}).get("docs", [])
        num_found = payload.get("response", {}).get("numFound", num_found)

        if not batch:
            break

        all_docs.extend(batch)
        if target is None and num_found:
            target = num_found
            print(f"[eVA] {num_found} contracts found, fetching all...")

        if target is not None and len(all_docs) >= target:
            break

        next_cursor = payload.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return all_docs[:target] if target else all_docs


# ── Public entry point ────────────────────────────────────────────────────────

async def fetch_eva_contracts() -> list[dict]:
    """
    Load the eVA portal, apply Contracts + last-30-days filter,
    fetch all matching docs from Solr, and return raw doc dicts.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser, page = await _load_portal_with_retry(playwright)
        try:
            date_range = await _apply_filters(page)
            docs = await _fetch_all_solr_pages(page, date_range)
            print(f"[eVA] Fetched {len(docs)} contract docs")
            return docs
        finally:
            await browser.close()
