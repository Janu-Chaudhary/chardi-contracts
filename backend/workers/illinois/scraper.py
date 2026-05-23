"""
Illinois BidBuy open-bids CSV scraper.

Portal: https://www.bidbuy.illinois.gov/bso/view/search/external/advancedSearchBid.xhtml
Approach:
  1. Load the open-bids search page (JSF/JavaServer Faces — requires real browser)
  2. Dismiss any "Do It Later" overlay if present
  3. Wait for the Results table to render
  4. Click the CSV export icon (img alt="Export to CSV File")
  5. Capture the downloaded CSV file
  6. Parse with Pandas and return list of row dicts

CSV columns:
  Bid Solicitation #, Organization Name, Blanket #, Buyer,
  Description, Bid Opening Date, Bid Holder List, Awarded Vendor(s),
  Status, Alternate Id

Note: The CSV export returns ALL open bids (~186 rows) in a single click,
not just the current page. Verified in the master plan.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

import pandas as pd
from playwright.async_api import async_playwright

OPEN_BIDS_URL = (
    "https://www.bidbuy.illinois.gov/bso/view/search/external/"
    "advancedSearchBid.xhtml?openBids=true"
)

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


async def fetch_illinois_dataframe() -> pd.DataFrame:
    """
    Navigate BidBuy, click CSV export, capture download, return DataFrame.

    Mirrors the Selenium plan but uses Playwright + asyncio to match
    the existing worker pattern (Texas, California, Georgia).
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=LAUNCH_ARGS)
        context = await browser.new_context(
            accept_downloads=True,
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = await context.new_page()

        try:
            print("[Illinois] Loading BidBuy open bids page...")
            resp = await page.goto(OPEN_BIDS_URL, wait_until="networkidle", timeout=90000)
            if resp and resp.status >= 400:
                raise RuntimeError(f"BidBuy returned HTTP {resp.status}")

            # ── Dismiss "Do It Later" overlay if present ──────────────────
            for selector in [
                "button:has-text('Do It Later')",
                "a:has-text('Do It Later')",
                "button:has-text('Close')",
            ]:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(500)
                        print(f"[Illinois] Dismissed overlay: {selector}")
                except Exception:
                    pass

            # ── Wait for Results table ────────────────────────────────────
            print("[Illinois] Waiting for results table...")
            await page.wait_for_selector("table", timeout=60000)
            # Wait for the Results count text to appear
            try:
                await page.wait_for_function(
                    "() => document.body.innerText.includes('Results')",
                    timeout=30000,
                )
            except Exception:
                pass
            await page.wait_for_timeout(1500)  # allow export icons to paint

            # ── Find and click CSV export icon ────────────────────────────
            print("[Illinois] Looking for CSV export icon...")
            csv_img = page.locator("img[alt*='Export to CSV']").first
            if await csv_img.count() == 0:
                csv_img = page.locator("img[alt*='CSV']").first
            if await csv_img.count() == 0:
                raise RuntimeError(
                    "CSV export icon not found on BidBuy page. "
                    "The portal may have changed its layout."
                )

            await csv_img.wait_for(state="visible", timeout=15000)

            # Use expect_download to capture the file
            async with page.expect_download(timeout=120000) as download_info:
                # JS click on the parent <a> element (more reliable than direct click)
                await page.evaluate(
                    """(img) => {
                        const link = img.closest('a') || img;
                        link.click();
                    }""",
                    await csv_img.element_handle(),
                )

            download = await download_info.value
            print(f"[Illinois] Download started: {download.suggested_filename}")

            # Save to temp file and read with pandas
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                tmp_path = tmp.name

            await download.save_as(tmp_path)
            df = pd.read_csv(tmp_path, low_memory=False)
            print(f"[Illinois] Parsed {len(df)} rows from CSV")
            return df

        finally:
            await browser.close()
            try:
                if "tmp_path" in dir() and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
