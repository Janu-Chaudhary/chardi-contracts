"""
Step 1: Analyze caleprocure.ca.gov Event Search page.
- Intercept all network requests to find the download endpoint
- Click the Download button and capture the XLS file
- Analyze the file structure
"""

import asyncio
import os
import tempfile

from playwright.async_api import async_playwright


async def analyze_caleprocure():
    intercepted_requests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (compatible; Chardi.ai/1.0; +https://chardi.ai) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = await context.new_page()

        # Intercept all requests to understand the download mechanism
        async def on_request(request):
            url = request.url
            if any(kw in url.lower() for kw in ["download", "export", "excel", "xls", "report"]):
                intercepted_requests.append({
                    "url": url,
                    "method": request.method,
                    "headers": dict(request.headers),
                })

        page.on("request", on_request)

        print("=" * 60)
        print("STEP 1: Loading Event Search page...")
        print("=" * 60)

        await page.goto(
            "https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx",
            wait_until="networkidle",
            timeout=90000,
        )

        print(f"Page title: {await page.title()}")
        print(f"Page URL: {page.url}")

        # Take a screenshot to see the page state
        screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "debug")
        os.makedirs(screenshot_dir, exist_ok=True)
        await page.screenshot(path=os.path.join(screenshot_dir, "caleprocure_01_loaded.png"))
        print("Screenshot saved: debug/caleprocure_01_loaded.png")

        # Check what's visible on the page
        print("\n" + "=" * 60)
        print("STEP 2: Inspecting page elements...")
        print("=" * 60)

        # Look for the Download button
        download_selectors = [
            "a:has-text('Download')",
            "button:has-text('Download')",
            "[id*='download' i]",
            "[class*='download' i]",
            "a[href*='download' i]",
            "a[href*='excel' i]",
            "a[href*='xls' i]",
            ".icon-download",
            "a.btn:has-text('Download')",
        ]

        for sel in download_selectors:
            try:
                elements = await page.locator(sel).all()
                if elements:
                    print(f"  Found {len(elements)} element(s) with selector: {sel}")
                    for el in elements[:3]:
                        try:
                            text = await el.inner_text()
                            href = await el.get_attribute("href")
                            el_id = await el.get_attribute("id")
                            print(f"    text='{text.strip()}' href='{href}' id='{el_id}'")
                        except Exception:
                            pass
            except Exception:
                pass

        # Check if there's a search results section
        print("\n" + "=" * 60)
        print("STEP 3: Checking results section...")
        print("=" * 60)

        results_text = ""
        for sel in ["#results", ".results", "[id*='result']", "[class*='result']", "table"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    results_text = await el.inner_text()
                    print(f"  Results section found with selector: {sel}")
                    print(f"  First 300 chars: {results_text[:300]}")
                    break
            except Exception:
                pass

        # Get full page text to understand structure
        body_text = await page.inner_text("body")
        print(f"\n  Page body snippet (first 500 chars):\n  {body_text[:500]}")

        # Check for "Showing Results" text
        if "Showing" in body_text:
            import re
            match = re.search(r"Showing[^0-9]*(\d+)[^0-9]*of[^0-9]*(\d+)", body_text)
            if match:
                print(f"\n  Results count: {match.group(1)} of {match.group(2)}")

        print("\n" + "=" * 60)
        print("STEP 4: Attempting to click Download button...")
        print("=" * 60)

        # Try multiple approaches to find and click download
        download_file_path = None

        # Approach 1: Look for the download icon/link from the screenshot
        download_locators = [
            page.locator("a:has-text('Download')"),
            page.locator("button:has-text('Download')"),
            page.locator("[id*='download' i]").first,
            page.locator("a.btn").filter(has_text="Download"),
            page.locator("//a[contains(translate(text(),'DOWNLOAD','download'),'download')]"),
            page.locator("//button[contains(translate(text(),'DOWNLOAD','download'),'download')]"),
        ]

        for i, locator in enumerate(download_locators):
            try:
                if await locator.is_visible(timeout=3000):
                    print(f"  Download element found with locator #{i+1}")
                    href = await locator.get_attribute("href")
                    print(f"  href: {href}")

                    async with page.expect_download(timeout=30000) as dl_info:
                        await locator.click()

                    download = await dl_info.value
                    suggested = download.suggested_filename
                    print(f"  Download triggered! Filename: {suggested}")

                    tmp_path = os.path.join(
                        tempfile.gettempdir(),
                        suggested or "caleprocure_export.xls"
                    )
                    await download.save_as(tmp_path)
                    download_file_path = tmp_path
                    print(f"  Saved to: {tmp_path}")
                    break
            except Exception as e:
                print(f"  Locator #{i+1} failed: {e}")

        # Screenshot after download attempt
        await page.screenshot(path=os.path.join(screenshot_dir, "caleprocure_02_after_download.png"))

        print("\n" + "=" * 60)
        print("STEP 5: Intercepted download-related requests:")
        print("=" * 60)
        if intercepted_requests:
            for req in intercepted_requests:
                print(f"  {req['method']} {req['url']}")
        else:
            print("  None intercepted (download may be a direct link or POST)")

        await browser.close()

    # Analyze the downloaded file
    if download_file_path and os.path.exists(download_file_path):
        print("\n" + "=" * 60)
        print("STEP 6: Analyzing downloaded file...")
        print("=" * 60)
        analyze_file(download_file_path)
    else:
        print("\n  No file downloaded — will need to inspect page HTML for download URL")

    return download_file_path


def analyze_file(file_path: str):
    import pandas as pd

    print(f"  File: {file_path}")
    print(f"  Size: {os.path.getsize(file_path):,} bytes")

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in (".xls", ".xlsx"):
            df = pd.read_excel(file_path)
        elif ext == ".csv":
            df = pd.read_csv(file_path, low_memory=False)
        else:
            # Try excel first, then csv
            try:
                df = pd.read_excel(file_path)
            except Exception:
                df = pd.read_csv(file_path, low_memory=False)

        print(f"\n  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"\n  Columns:")
        for i, col in enumerate(df.columns):
            null_count = df[col].isnull().sum()
            pct = round((df.shape[0] - null_count) / df.shape[0] * 100)
            print(f"    {i:2d}. {col:<40} {pct}% populated")

        print(f"\n  Sample row (first row):")
        if not df.empty:
            for k, v in df.iloc[0].items():
                print(f"    {k}: {v}")

        print(f"\n  DB FIELD MAPPING ASSESSMENT:")
        cols_lower = [c.lower() for c in df.columns]
        checks = {
            "source_record_id": ["event id", "id", "event number", "contract"],
            "title": ["event name", "title", "name", "description"],
            "posted_date": ["start date", "posted", "open date", "publish"],
            "deadline": ["end date", "close date", "due date", "deadline"],
            "buyer_name": ["department", "agency", "buyer", "organization"],
            "notice_type": ["event type", "type", "format", "category"],
            "status": ["status", "event status"],
            "industry": ["commodity", "nigp", "category", "naics"],
            "value_numeric": ["value", "amount", "estimated", "price"],
            "source_url": ["url", "link", "href"],
        }
        for db_field, keywords in checks.items():
            found = next((df.columns[i] for i, c in enumerate(cols_lower)
                         if any(kw in c for kw in keywords)), None)
            status = f"✅ → '{found}'" if found else "❌ not found"
            print(f"    {db_field:<22} {status}")

    except Exception as e:
        print(f"  Error reading file: {e}")
        # Show raw bytes
        with open(file_path, "rb") as f:
            raw = f.read(200)
        print(f"  Raw bytes (first 200): {raw}")


if __name__ == "__main__":
    asyncio.run(analyze_caleprocure())
