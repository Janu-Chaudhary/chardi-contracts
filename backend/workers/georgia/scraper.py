"""
Georgia Team Georgia Marketplace (TGM) contract scraper.

Portal: https://solutions.sciquest.com/apps/Router/ContractSearch
Login: tgmguest / tgmguest (public guest account)
Approach:
  1. Login with guest credentials
  2. Navigate to Contract Search with DocTypeId=2000
  3. Add filter: Created Date → Within → Last 30 Days
  4. Set 200 results per page
  5. Paginate through all pages, scraping each row
  6. Return list of raw contract dicts
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


async def _login(page: Page) -> None:
    """Login with guest credentials using Enter key to submit."""
    print("[Georgia] Navigating to login page...")
    await page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
    await page.fill("input[name='Login_User']", USERNAME)
    await page.fill("input[name='Login_Password']", PASSWORD)
    await page.press("input[name='Login_Password']", "Enter")
    # Wait for redirect to dashboard
    await page.wait_for_url("**/ShoppingDashboard**", timeout=20000)
    print(f"[Georgia] Logged in — title: {await page.title()!r}")


async def _navigate_to_search(page: Page) -> None:
    """Navigate to contract search by clicking the dashboard link."""
    print("[Georgia] Navigating to contract search...")
    # Click the 'here' link in the Advanced Contract Search section
    here_link = page.locator("a:has-text('here')").first
    await here_link.wait_for(state="visible", timeout=10000)
    await here_link.click()
    await page.wait_for_load_state("networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    print(f"[Georgia] Contract search loaded — title: {await page.title()!r}")


async def _apply_last_30_days_filter(page: Page) -> None:
    """Add Created Date → Within → Last 30 Days filter using exact element IDs."""
    print("[Georgia] Applying Last 30 Days filter...")

    # Click "Add Filter" dropdown
    add_filter = page.locator("text=Add Filter").first
    await add_filter.wait_for(state="visible", timeout=15000)
    await add_filter.click()
    await page.wait_for_timeout(1000)

    # Look for "Created Date" option in the dropdown
    created_date = page.locator("text=Created Date").first
    await created_date.wait_for(state="visible", timeout=10000)
    await created_date.click()
    await page.wait_for_timeout(1500)

    # Select "Last 30 days" from the Created Date within-value dropdown
    await page.wait_for_selector("#ESSearchInput_CreateDateWITHIN_OPTION_VALUE", timeout=10000)
    await page.select_option(
        "#ESSearchInput_CreateDateWITHIN_OPTION_VALUE",
        value="LAST_30_DAYS"
    )
    await page.wait_for_timeout(500)

    # Click Search/Apply button
    search_btn = page.locator("button:has-text('Search'), input[value='Search'], button[type='submit']").first
    if await search_btn.count() > 0:
        await search_btn.click()
        await page.wait_for_load_state("networkidle", timeout=30000)
    else:
        # Try pressing Enter
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle", timeout=30000)

    await page.wait_for_timeout(2000)
    print("[Georgia] Filter applied")


async def _set_200_per_page(page: Page) -> None:
    """Set results per page to 200."""
    try:
        per_page = page.locator("select").filter(has_text="200")
        if await per_page.count() > 0:
            await per_page.select_option(label="200 Per Page")
            await page.wait_for_load_state("networkidle", timeout=15000)
        else:
            # Try any per-page selector
            selects = page.locator("select")
            count = await selects.count()
            for i in range(count):
                options = await selects.nth(i).inner_text()
                if "200" in options:
                    await selects.nth(i).select_option(label="200 Per Page")
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    break
        print("[Georgia] Set 200 per page")
    except Exception as e:
        print(f"[Georgia] Could not set per-page (continuing): {e}")


async def _scrape_page(page: Page) -> list[dict[str, Any]]:
    """Scrape all contract rows from the current page."""
    rows = []

    # Wait for the results table header
    await page.wait_for_selector("th", timeout=15000)
    await page.wait_for_timeout(1000)

    # Get column headers from th elements
    headers = page.locator("th")
    header_count = await headers.count()
    col_names = []
    for i in range(header_count):
        text = (await headers.nth(i).inner_text()).strip()
        col_names.append(text)

    # Get all data rows (tr elements with td children)
    all_rows = page.locator("tr")
    row_count = await all_rows.count()

    for i in range(row_count):
        cells = all_rows.nth(i).locator("td")
        cell_count = await cells.count()
        if cell_count < 3:  # skip header rows and empty rows
            continue

        row: dict[str, Any] = {}
        for j in range(min(cell_count, len(col_names))):
            text = (await cells.nth(j).inner_text()).strip()
            if col_names[j]:
                row[col_names[j]] = text

        # Get detail URL from the contract number link
        link = all_rows.nth(i).locator("a").first
        if await link.count() > 0:
            href = await link.get_attribute("href")
            if href and "Contract" in href:
                row["_detail_url"] = (
                    href if href.startswith("http")
                    else f"https://solutions.sciquest.com{href}"
                )

        # Only add rows that have a Contract Number
        if row.get("Contract Number") or row.get("Contract Name"):
            rows.append(row)

    return rows


async def _get_total_pages(page: Page) -> int:
    """Extract total number of pages from pagination."""
    try:
        # Look for "Page X of Y" text
        page_text = await page.inner_text("body")
        match = re.search(r"Page\s+\d+\s+of\s+(\d+)", page_text)
        if match:
            return int(match.group(1))

        # Try pagination element
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
    """Navigate to next page. Returns False if no next page."""
    try:
        # Try clicking "Next" button
        next_btn = page.locator("a:has-text('Next'), button:has-text('Next'), [title='Next']").first
        if await next_btn.count() > 0:
            is_disabled = await next_btn.get_attribute("disabled")
            if is_disabled:
                return False
            await next_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            return True

        # Try clicking page number
        next_page_btn = page.locator(f"a:has-text('{current + 1}')").first
        if await next_page_btn.count() > 0:
            await next_page_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            return True

    except Exception as e:
        print(f"[Georgia] Pagination error: {e}")

    return False


async def fetch_georgia_contracts() -> list[dict[str, Any]]:
    """
    Login to TGM, apply last-30-days filter, paginate all results,
    and return list of raw contract dicts.
    """
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
            # Step 1: Login
            await _login(page)

            # Step 2: Navigate to contract search
            await _navigate_to_search(page)

            # Step 3: Apply last 30 days filter
            await _apply_last_30_days_filter(page)

            # Step 4: Set 200 per page
            await _set_200_per_page(page)

            # Step 5: Get total pages
            total_pages = await _get_total_pages(page)
            print(f"[Georgia] Total pages: {total_pages}")

            # Step 6: Scrape all pages
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
                await asyncio.sleep(1)  # polite delay

        finally:
            await browser.close()

    print(f"[Georgia] Total contracts scraped: {len(all_contracts)}")
    return all_contracts
