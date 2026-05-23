"""
California caleprocure.ca.gov Event Search scraper.

Approach:
- Load the Event Search page (default: Posted status, all events)
- Click the Download button — PeopleSoft returns a large JSON payload
  containing all 456+ records (not an XLS file)
- Parse the JSON to extract event records

v2 reliability fixes:
  - Retry wrapper (3 attempts, 10s backoff)
  - Fallback selectors for download button (not just hardcoded PeopleSoft ID)
  - Increased page.goto timeout to 120s
  - Clear error message listing all tried selectors on failure
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from playwright.async_api import async_playwright

TARGET_URL = "https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx"

# Primary button ID (PeopleSoft-generated — may change between deployments)
DOWNLOAD_BTN_ID = "RESP_INQA_HD_VW_GR$hexcel$0"

# Fallback selectors tried in priority order
DOWNLOAD_BTN_FALLBACKS = [
    f"[id='{DOWNLOAD_BTN_ID}']",
    "img[alt*='Excel']",
    "img[alt*='Download']",
    "img[alt*='Export']",
    "a[title*='Download']",
    "button:has-text('Download')",
    "a:has-text('Download')",
]

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 10


def _get_text(children: dict, *field_names: str) -> str:
    """Extract text from a PeopleSoft JSON children dict by field name."""
    for field in field_names:
        field_data = children.get(field, [])
        if isinstance(field_data, list) and field_data:
            first = field_data[0]
            if isinstance(first, dict):
                props = first.get("Properties", {})
                if isinstance(props, dict):
                    val = str(props.get("text", "")).strip()
                    if val:
                        return val
    return ""


def parse_records_from_json(json_text: str) -> list[dict[str, str]]:
    """Parse PeopleSoft JSON response and extract all tblBodyTr event records."""
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return []

    records: list[dict[str, str]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            if "tblBodyTr" in str(obj.get("Label", "")):
                children = obj.get("Children", {})
                record = {
                    "Event ID":       _get_text(children, "tdEventId"),
                    "Event Name":     _get_text(children, "tdEventName"),
                    "Department":     _get_text(children, "tdDepName"),
                    "Published Date": _get_text(
                        children, "tdPubDate", "tdPublishedDate", "tdStartDate"
                    ),
                    "End Date":       _get_text(children, "tdEndDate"),
                    "Status":         _get_text(children, "tdStatus"),
                    "UNSPSC":         _get_text(
                        children, "tdUnspsc", "tdUNSPSC", "tdCommodity"
                    ),
                    "Service Area":   _get_text(children, "tdServiceArea"),
                }
                if record["Event ID"] or record["Event Name"]:
                    records.append(record)
            else:
                for v in obj.values():
                    walk(v)

    walk(data)
    return records


async def _scrape_once() -> list[dict[str, str]]:
    """Single attempt at the full scrape flow."""
    captured_json: list[str] = []

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

        async def on_response(response) -> None:
            ct = response.headers.get("content-type", "")
            if "json" in ct or "javascript" in ct:
                try:
                    body = await response.body()
                    if len(body) > 20000:
                        captured_json.append(body.decode("utf-8", errors="replace"))
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            resp = await page.goto(TARGET_URL, wait_until="networkidle", timeout=120000)
            if resp and resp.status >= 400:
                raise RuntimeError(
                    f"caleprocure.ca.gov returned HTTP {resp.status}"
                )

            # Try each fallback selector in priority order
            dl_btn = None
            used_selector = None
            for selector in DOWNLOAD_BTN_FALLBACKS:
                candidate = page.locator(selector).first
                try:
                    await candidate.wait_for(state="visible", timeout=5000)
                    if await candidate.count() > 0:
                        dl_btn = candidate
                        used_selector = selector
                        break
                except Exception:
                    continue

            if dl_btn is None:
                raise RuntimeError(
                    "Download button not found on caleprocure.ca.gov. "
                    f"Tried: {DOWNLOAD_BTN_FALLBACKS}"
                )

            print(f"[California] Found download button via: {used_selector}")
            await dl_btn.click()
            await page.wait_for_load_state("networkidle", timeout=60000)

        finally:
            await browser.close()

    for json_text in sorted(captured_json, key=len, reverse=True):
        records = parse_records_from_json(json_text)
        if records:
            return records

    return []


async def fetch_california_events() -> list[dict[str, str]]:
    """Fetch California caleprocure events with retry wrapper (3 attempts, 10s backoff)."""
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[California] Attempt {attempt}/{MAX_RETRIES}...")
            result = await _scrape_once()
            print(f"[California] Success on attempt {attempt} — {len(result)} events")
            return result
        except Exception as exc:
            last_exc = exc
            print(f"[California] Attempt {attempt} failed: {exc}")
            if attempt < MAX_RETRIES:
                print(f"[California] Retrying in {RETRY_BACKOFF_SECONDS}s...")
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

    raise RuntimeError(
        f"California scraper failed after {MAX_RETRIES} attempts"
    ) from last_exc
