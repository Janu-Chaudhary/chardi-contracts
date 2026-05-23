"""
Texas TxSmartBuy contract scraper.

Uses Playwright to navigate to the Browse Contracts page and intercept
the CSV export download. No login required — the export is public.
"""

from __future__ import annotations

import os
import tempfile

import pandas as pd
from playwright.async_api import async_playwright

TARGET_URL = "https://www.txsmartbuy.gov/browsecontracts"


async def fetch_texas_dataframe() -> pd.DataFrame:
    """
    Navigate TxSmartBuy Browse Contracts, click Export Results,
    intercept the CSV download, and return a DataFrame.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (compatible; Chardi.ai/1.0; "
                "+https://chardi.ai) AppleWebKit/537.36"
            ),
            locale="en-US",
        )
        page = await context.new_page()

        try:
            response = await page.goto(
                TARGET_URL,
                wait_until="networkidle",
                timeout=60000,
            )
            if response and response.status >= 400:
                raise RuntimeError(
                    f"TxSmartBuy returned HTTP {response.status}; "
                    "portal may be blocking automated access."
                )

            export_button = page.locator("button:has-text('Export Results')")
            await export_button.wait_for(state="visible", timeout=30000)

            async with page.expect_download(timeout=60000) as download_info:
                await export_button.click()

            download = await download_info.value

            # Save to a temp file then read into pandas
            with tempfile.NamedTemporaryFile(
                suffix=".csv", delete=False
            ) as tmp:
                tmp_path = tmp.name

            await download.save_as(tmp_path)
            df = pd.read_csv(tmp_path, low_memory=False)
            return df

        finally:
            await browser.close()
            # Clean up temp file if it exists
            try:
                if "tmp_path" in dir() and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
