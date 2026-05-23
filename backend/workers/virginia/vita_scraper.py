"""
Virginia VITA IT statewide contract search scraper.

Portal: https://vita.cobblestonesystems.com/public/
Approach:
  1. Open portal, click Search Records (empty = all contracts)
  2. Paginate through all result pages collecting list rows
  3. Return list of raw row dicts (no detail page scraping — list data is sufficient)

Adapted from /home/janu-chaudhary/AAA/vita_scraper.py (working Cursor script).
"""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urljoin

from playwright.async_api import Page, Playwright

VITA_BASE = "https://vita.cobblestonesystems.com/public/"
SEARCH_BUTTON = "#ctl00_PublicPortalContent_btnSearch_input"
RESULTS_GRID = "table.rgMasterTable"
RESULTS_ROWS = f"{RESULTS_GRID} tbody tr.rgRow, {RESULTS_GRID} tbody tr.rgAltRow"

LAUNCH_ARGS = ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage"]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
PAGER_RE = re.compile(
    r"Page\s+(\d+)\s+of\s+(\d+),\s*items\s+[\d,]+\s+to\s+[\d,]+\s+of\s+([\d,]+)",
    re.I,
)


class VitaScrapeError(RuntimeError):
    pass


def _parse_pager(text: str) -> tuple[int, int, int]:
    match = PAGER_RE.search(text)
    if not match:
        raise VitaScrapeError(f"Could not parse pager: {text!r}")
    current, total_pages, total_items = match.groups()
    return int(current), int(total_pages), int(total_items.replace(",", ""))


async def _open_browser(playwright: Playwright):
    browser = await playwright.chromium.launch(headless=True, args=LAUNCH_ARGS)
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1920, "height": 1080},
    )
    page = await context.new_page()
    return browser, page


async def _run_empty_search(page: Page) -> None:
    await page.goto(VITA_BASE, wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_selector(SEARCH_BUTTON, state="visible", timeout=30_000)
    await page.locator(SEARCH_BUTTON).click()
    await page.wait_for_selector(RESULTS_GRID, timeout=60_000)
    await page.wait_for_timeout(1500)


async def _get_pager_state(page: Page) -> tuple[int, int, int]:
    info = await page.locator(".rgInfoPart").first.inner_text()
    return _parse_pager(info)


async def _go_to_page(page: Page, page_num: int) -> None:
    if page_num == 1:
        current, _, _ = await _get_pager_state(page)
        if current == 1:
            return
    paginator = page.locator(".rgNumPart").first
    link = paginator.locator("a").filter(has_text=str(page_num))
    if await link.count() == 0:
        raise VitaScrapeError(f"Pager link for page {page_num} not found")
    await link.first.click()
    await page.wait_for_function(
        f"() => document.body.innerText.includes('Page {page_num} of')",
        timeout=30_000,
    )
    await page.wait_for_timeout(1000)


async def _extract_page_rows(page: Page) -> list[dict]:
    rows: list[dict] = []
    row_loc = page.locator(RESULTS_ROWS)
    count = await row_loc.count()

    for i in range(count):
        row = row_loc.nth(i)
        cells = [c.strip() for c in await row.locator("td").all_inner_texts()]

        # Get detail URL from first link
        detail_href = ""
        view_links = row.locator("td a")
        if await view_links.count():
            detail_href = (await view_links.first.get_attribute("href")) or ""
        detail_url = urljoin(VITA_BASE, detail_href) if detail_href else ""

        record = {
            "vita_contract_number":        cells[1] if len(cells) > 1 else "",
            "contract_title":              cells[2] if len(cells) > 2 else "",
            "supplier":                    cells[3] if len(cells) > 3 else "",
            "contract_end_date":           cells[4] if len(cells) > 4 else "",
            "swam":                        cells[5] if len(cells) > 5 else "",
            "eva_ctr_number":              cells[6] if len(cells) > 6 else "",
            "erate_ecf_eligible":          cells[7] if len(cells) > 7 else "",
            "erate_spin_number":           cells[8] if len(cells) > 8 else "",
            "erate_fcc_470_number":        cells[9] if len(cells) > 9 else "",
            "erate_category_1":            cells[10] if len(cells) > 10 else "",
            "erate_category_2":            cells[11] if len(cells) > 11 else "",
            "erate_allowable_contract_date": cells[12] if len(cells) > 12 else "",
            "detail_url":                  detail_url,
        }
        if record["vita_contract_number"]:
            rows.append(record)

    return rows


async def fetch_vita_contracts() -> list[dict]:
    """
    Open VITA portal, run empty search, paginate all results,
    and return list of raw row dicts.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser, page = await _open_browser(playwright)
        try:
            await _run_empty_search(page)
            _, total_pages, total_items = await _get_pager_state(page)
            print(f"[VITA] {total_items} contracts across {total_pages} pages")

            all_rows: list[dict] = []
            for page_num in range(1, total_pages + 1):
                await _go_to_page(page, page_num)
                batch = await _extract_page_rows(page)
                print(f"[VITA] Page {page_num}/{total_pages}: {len(batch)} rows")
                all_rows.extend(batch)

            print(f"[VITA] Total collected: {len(all_rows)}")
            return all_rows
        finally:
            await browser.close()
