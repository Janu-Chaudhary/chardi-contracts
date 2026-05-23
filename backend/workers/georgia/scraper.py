"""
Georgia Team Georgia Marketplace (TGM) contract scraper.

Portal: https://solutions.sciquest.com/apps/Router/ContractSearch
Login: tgmguest / tgmguest (public guest account)

v2 reliability fixes:
  - Direct URL navigation instead of fragile dashboard link click
  - Retry wrapper (3 attempts, 15s backoff)
  - Fixed strict mode violation in _set_200_per_page (nth() iteration)
  - Fallback selector for date filter dropdown
  - Increased timeouts throughout
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from playwright.async_api import Page, async_playwright

LOGIN_URL = "https://solutions.sciquest.com/apps/Router/Login?OrgName=Georgia"
SEARCH_URL = "https://solutions.sciquest.com/apps/Router/ContractSearch?DocTypeId=2000"

USERNAME = "tgmguest"
PASSWORD = "tgmguest"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

LAUNCH_ARGS = [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 15


async def _login(page: Page) -> None:
    print("[Georgia] Navigating to login page...")
    await page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
    await page.fill("input[name='Login_User']", USERNAME)
    await page.fill("input[name='Login_Password']", PASSWORD)
    await page.press("input[name='Login_Password']", "Enter")
    await page.wait_for_url("**/ShoppingDashboard**", timeout=30000)
    print(f"[Georgia] Logged in — title: {await page.title()!r}")


async def _navigate_to_search(page: Page) -> None:
    """Navigate directly to contract search URL — avoids fragile dashboard link."""
    print("[Georgia] Navigating directly to contract search URL...")
    await page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(2000)
    print(f"[Georgia] Contract search loaded — title: {await page.title()!r}")


async def _apply_last_30_days_filter(page: Page) -> None:
    """Apply Created Date → Last 30 Days filter with fallback selectors."""
    print("[Georgia] Applying Last 30 Days filter...")

    add_filter = page.locator("text=Add Filter").first
    await add_filter.wait_for(state="visible", timeout=30000)
    await add_filter.click()
    await page.wait_for_timeout(1500)

    created_date = page.locator("text=Created Date").first
    await created_date.wait_for(state="visible", timeout=20000)
    await created_date.click()
    await page.wait_for_timeout(2000)

    dropdown_selector = "#ESSearchInput_CreateDateWITHIN_OPTION_VALUE"
    try:
        await page.wait_for_selector(dropdown_selector, timeout=15000)
        await page.select_option(dropdown_selector, value="LAST_30_DAYS")
    except Exception:
        print("[Georgia] Primary dropdown selector failed, trying fallback...")
        selects = page.locator("select")
        count = await selects.count()
        for i in range(count):
            try:
                options = await selects.nth(i).inner_html()
                if "LAST_30_DAYS" in options or "Last 30" in options:
                    await selects.nth(i).select_option(value="LAST_30_DAYS")
                    print(f"[Georgia] Used fallback select #{i}")
                    break
            except Exception:
                continue

    await page.wait_for_timeout(500)

    search_btn = page.locator(
        "button:has-text('Search'), input[value='Search'], button[type='submit']"
    ).first
    if await search_btn.count() > 0:
        await search_btn.click()
        await page.wait_for_load_state("networkidle", timeout=30000)
    else:
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle", timeout=30000)

    await page.wait_for_timeout(2000)
    print("[Georgia] Filter applied")


async def _set_200_per_page(page: Page) -> None:
    """Set results per page to 200 — uses nth() to avoid strict mode violation."""
    try:
        selects = page.locator("select")
        count = await selects.count()
        for i in range(count):
            try:
                options_text = await selects.nth(i).inner_text()
                if "200" in options_text:
                    await selects.nth(i).select_option(label="200 Per Page")
                    await page.wait_for_load_state("networkidle", timeout=20000)
                    print("[Georgia] Set 200 per page")
                    return
            except Exception:
                continue
        print("[Georgia] Could not find per-page selector (continuing with default)")
    except Exception as e:
        print(f"[Georgia] Could not set per-page (continuing): {e}")


async def _scrape_page(page: Page) -> list[dict[str, Any]]:
    rows = []
    await page.wait_for_selector("th", timeout=20000)
    await page.wait_for_timeout(1000)

    headers = page.locator("th")
    header_count = await headers.count()
    col_names = []
    for i in range(header_count):
        text = (await headers.nth(i).inner_text()).strip()
        col_names.append(text)

    all_rows = page.locator("tr")
    row_count = await all_rows.count()

    for i in range(row_count):
        cells = all_rows.nth(i).locator("td")
        cell_count = await cells.count()
        if cell_count < 3:
            continue

        row: dict[str, Any] = {}
        for j in range(min(cell_count, len(col_names))):
            text = (await cells.nth(j).inner_text()).strip()
            if col_names[j]:
                row[col_names[j]] = text

        link = all_rows.nth(i).locator("a").first
        if await link.count() > 0:
            href = await link.get_attribute("href")
            if href and "Contract" in href:
                row["_detail_url"] = (
                    href if href.startswith("http")
                    else f"https://solutions.sciquest.com{href}"
                )

        if row.get("Contract Number") or row.get("Contract Name"):
            rows.append(row)

    return rows


async def _get_total_pages(page: Page) -> int:
    try:
        page_text = await page.inner_text("body")
        match = re.search(r"Page\s+\d+\s+of\s+(\d+)", page_text)
        if match:
            return int(match.group(1))
        pagination = page.locator("[class*='pagination'], [class*='pager']")
        if await pagination.count() > 0:
            text = await pagination.inner_text()
            match = re.search(r"of\s+(\d+)", text)
            if match:
                return int(match.group(1))
    except Exception:
        pass
    return 1


async def _go_to_next_page(page: Page, current: int) -> bool:
    try:
        next_btn = page.locator(
            "a:has-text('Next'), button:has-text('Next'), [title='Next']"
        ).first
        if await next_btn.count() > 0:
            is_disabled = await next_btn.get_attribute("disabled")
            if is_disabled:
                return False
            await next_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            return True

        next_page_btn = page.locator(f"a:has-text('{current + 1}')").first
        if await next_page_btn.count() > 0:
            await next_page_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            return True
    except Exception as e:
        print(f"[Georgia] Pagination error: {e}")
    return False


async def _scrape_once() -> list[dict[str, Any]]:
    all_contracts: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=LAUNCH_ARGS)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = await context.new_page()

        try:
            await _login(page)
            await _navigate_to_search(page)
            await _apply_last_30_days_filter(page)
            await _set_200_per_page(page)

            total_pages = await _get_total_pages(page)
            print(f"[Georgia] Total pages: {total_pages}")

            current_page = 1
            while True:
                print(f"[Georgia] Scraping page {current_page}/{total_pages}...")
                rows = await _scrape_page(page)
                all_contracts.extend(rows)
                print(f"[Georgia] Page {current_page}: {len(rows)} rows (total: {len(all_contracts)})")

                if current_page >= total_pages:
                    break

                has_next = await _go_to_next_page(page, current_page)
                if not has_next:
                    break

                current_page += 1
                await asyncio.sleep(1)

        finally:
            await browser.close()

    return all_contracts


async def fetch_georgia_contracts() -> list[dict[str, Any]]:
    """Fetch Georgia TGM contracts with retry wrapper (3 attempts, 15s backoff)."""
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[Georgia] Attempt {attempt}/{MAX_RETRIES}...")
            result = await _scrape_once()
            print(f"[Georgia] Success on attempt {attempt} — {len(result)} contracts")
            return result
        except Exception as exc:
            last_exc = exc
            print(f"[Georgia] Attempt {attempt} failed: {exc}")
            if attempt < MAX_RETRIES:
                print(f"[Georgia] Retrying in {RETRY_BACKOFF_SECONDS}s...")
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

    raise RuntimeError(
        f"Georgia scraper failed after {MAX_RETRIES} attempts"
    ) from last_exc
