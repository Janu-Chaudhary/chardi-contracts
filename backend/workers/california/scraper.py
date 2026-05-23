"""
California caleprocure.ca.gov Event Search scraper.

Approach:
- Load the Event Search page (default: Posted status, all events)
- Click the Download button — PeopleSoft returns a large JSON payload
  containing all 456+ records (not an XLS file)
- Parse the JSON to extract event records

Fields available from the JSON response:
  tdEventId   → source_record_id
  tdEventName → title
  tdDepName   → buyer_name (department)
  tdEndDate   → deadline
  tdStatus    → status (Posted / Event Completed)

Note: posted_date (Published Date) is not available in the basic search
JSON. Advanced Search adds it but requires complex PeopleSoft AJAX
interaction that is unreliable in headless mode. Skipped intentionally.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from playwright.async_api import async_playwright

TARGET_URL = "https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx"
DOWNLOAD_BTN_ID = "RESP_INQA_HD_VW_GR$hexcel$0"


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
    """
    Parse PeopleSoft JSON response and extract all tblBodyTr event records.

    Each record contains: Event ID, Event Name, Department, End Date, Status.
    """
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


async def fetch_california_events() -> list[dict[str, str]]:
    """
    Navigate caleprocure.ca.gov, click Download, capture the JSON response,
    and return a list of event record dicts.
    """
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
            resp = await page.goto(TARGET_URL, wait_until="networkidle", timeout=90000)
            if resp and resp.status >= 400:
                raise RuntimeError(
                    f"caleprocure.ca.gov returned HTTP {resp.status}"
                )

            # Click the Download button — triggers JSON response with all records
            dl_btn = page.locator(f"[id='{DOWNLOAD_BTN_ID}']").first
            await dl_btn.wait_for(state="visible", timeout=30000)
            await dl_btn.click()
            await page.wait_for_load_state("networkidle", timeout=30000)

        finally:
            await browser.close()

    # Parse records from the largest JSON response
    for json_text in sorted(captured_json, key=len, reverse=True):
        records = parse_records_from_json(json_text)
        if records:
            return records

    return []
