"""
caleprocure.ca.gov Historical Event Search scraper.

Steps (matching manual workflow):
1. Load page
2. Click "Advanced Search Criteria" to expand the panel
3. Set Event Status = Historical
4. Set Published Year = 2026
5. Type Start Date From in dd/mm/yyyy (Indian format) — one month ago
   Then click somewhere else (NOT Enter) to let portal accept it
6. Click Search
7. Click Download → capture JSON response with all records
8. Parse JSON → extract all fields including Published Date + UNSPSC
"""

import asyncio
import json
import os
import re
from datetime import datetime, timedelta

from playwright.async_api import async_playwright

TARGET_URL = "https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx"
DEBUG_DIR = os.path.join(os.path.dirname(__file__), "..", "debug")


def _one_month_ago_indian() -> str:
    """Return date one month ago in dd/mm/yyyy (Indian format)."""
    d = datetime.today() - timedelta(days=30)
    return d.strftime("%d/%m/%Y")


def extract_records_from_json(json_text: str) -> list[dict]:
    """Parse PeopleSoft JSON and extract all tblBodyTr event records."""
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return []

    records = []

    def get_text(children: dict, *field_names: str) -> str:
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

    def walk(obj):
        if isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            label = str(obj.get("Label", ""))
            if "tblBodyTr" in label:
                children = obj.get("Children", {})
                record = {
                    "Event ID":       get_text(children, "tdEventId"),
                    "Event Name":     get_text(children, "tdEventName"),
                    "Department":     get_text(children, "tdDepName"),
                    "Published Date": get_text(children, "tdPubDate", "tdPublishedDate", "tdStartDate"),
                    "End Date":       get_text(children, "tdEndDate"),
                    "Status":         get_text(children, "tdStatus"),
                    "UNSPSC":         get_text(children, "tdUnspsc", "tdUNSPSC", "tdCommodity"),
                    "Service Area":   get_text(children, "tdServiceArea"),
                }
                if record["Event ID"] or record["Event Name"]:
                    records.append(record)
            else:
                for v in obj.values():
                    walk(v)

    walk(data)
    return records


async def scrape_caleprocure() -> list[dict]:
    os.makedirs(DEBUG_DIR, exist_ok=True)

    start_date_indian = _one_month_ago_indian()
    print(f"Start Date (Indian dd/mm/yyyy): {start_date_indian}")

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

        async def on_response(response):
            ct = response.headers.get("content-type", "")
            if "json" in ct or "javascript" in ct:
                try:
                    body = await response.body()
                    if len(body) > 20000:
                        captured_json.append(body.decode("utf-8", errors="replace"))
                except Exception:
                    pass

        page.on("response", on_response)

        # ── 1. Load page ──────────────────────────────────────────────────
        print("Loading page...")
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=90000)
        await page.screenshot(path=os.path.join(DEBUG_DIR, "ca_01_loaded.png"))

        # ── 2. Click "Advanced Search Criteria" ───────────────────────────
        print("Clicking Advanced Search Criteria...")
        adv_btn = page.get_by_text("Advanced Search Criteria", exact=False)
        await adv_btn.first.click()
        # Wait for the new fields to render — PeopleSoft AJAX
        await page.wait_for_timeout(3000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.screenshot(path=os.path.join(DEBUG_DIR, "ca_02_advanced_open.png"))
        print("  Advanced Search panel opened.")

        # ── 3. Set Event Status = Historical ─────────────────────────────
        print("Setting Event Status = Historical...")
        status_sel = page.locator("#RESP_INQA_WK_ZZ_EVENT_STATUS")
        await status_sel.select_option(value="H")
        await page.wait_for_timeout(1000)
        print("  Status set to Historical.")

        # ── 4. Set Published Year = 2026 ──────────────────────────────────
        print("Setting Published Year = 2026...")
        # Find the year dropdown — it appears after Advanced Search opens
        year_sel = page.locator("select[id*='PUBLISHED_YEAR'], select[id*='publishedYear'], #RESP_INQA_WK_ZZ_PUBLISHED_YEAR")
        if await year_sel.count() > 0:
            await year_sel.first.select_option(value="2026")
            await page.wait_for_timeout(500)
            print("  Published Year set to 2026.")
        else:
            # Try by visible text near "Published Year" label
            all_selects = await page.locator("select").all()
            print(f"  Could not find year dropdown by ID. Found {len(all_selects)} selects total.")
            for sel in all_selects:
                sel_id = await sel.get_attribute("id")
                opts = await sel.locator("option").all()
                opt_vals = [await o.get_attribute("value") for o in opts]
                if "2026" in opt_vals:
                    await sel.select_option(value="2026")
                    print(f"  Set year via select id={sel_id}")
                    break

        # ── 5. Type Start Date in Indian format, then click elsewhere ─────
        print(f"Setting Start Date From = {start_date_indian} (Indian dd/mm/yyyy)...")

        # Find the Start Date From input
        date_input = page.locator(
            "#RESP_INQA_WK_AUC_FROM_START_DT, "
            "input[id*='FROM_START_DT'], "
            "input[id*='START_DATE_FROM'], "
            "input[id*='AUC_FROM']"
        ).first

        if await date_input.count() == 0:
            # Fallback: find by placeholder hint
            date_input = page.locator("input[placeholder*='mm/dd']").first

        await date_input.click()
        await date_input.fill("")  # Clear first
        await date_input.type(start_date_indian, delay=50)  # Type slowly like a human

        # Click somewhere else (NOT Enter) — click the page title / body
        await page.locator("body").click(position={"x": 400, "y": 100})
        await page.wait_for_timeout(1500)

        # Verify what got accepted
        accepted_val = await date_input.input_value()
        print(f"  Date field accepted: '{accepted_val}'")
        await page.screenshot(path=os.path.join(DEBUG_DIR, "ca_03_date_set.png"))

        # ── 6. Click Search ───────────────────────────────────────────────
        print("Clicking Search...")
        search_btn = page.locator(
            "button[id*='GO_PB'], input[id*='GO_PB'], button:has-text('Search')"
        ).first
        await search_btn.click()
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Check result count
        body_text = await page.inner_text("body")
        match = re.search(r"Showing[^0-9]*(\d+)[^0-9]*of[^0-9]*(\d+)", body_text)
        if match:
            print(f"  Results: {match.group(1)} of {match.group(2)}")
        else:
            print("  Could not find result count")

        await page.screenshot(path=os.path.join(DEBUG_DIR, "ca_04_results.png"))

        # ── 7. Click Download ─────────────────────────────────────────────
        print("Clicking Download...")
        captured_json.clear()

        # The download button ID contains $ — use attribute selector
        dl_btn = page.locator("[id='RESP_INQA_HD_VW_GR$hexcel$0']").first
        if await dl_btn.count() == 0:
            dl_btn = page.locator("button[aria-label='Download']").first

        await dl_btn.wait_for(state="visible", timeout=15000)
        await dl_btn.click()
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        print(f"  Captured {len(captured_json)} JSON responses")
        for i, j in enumerate(sorted(captured_json, key=len, reverse=True)[:5]):
            print(f"    Response {i}: {len(j):,} chars")

        await page.screenshot(path=os.path.join(DEBUG_DIR, "ca_05_downloaded.png"))
        await browser.close()

    # ── 8. Parse records ──────────────────────────────────────────────────
    all_records = []
    for json_text in sorted(captured_json, key=len, reverse=True):
        records = extract_records_from_json(json_text)
        if records:
            print(f"\nExtracted {len(records)} records from JSON ({len(json_text):,} chars)")
            all_records = records
            break

    return all_records


def analyze(records: list[dict]):
    if not records:
        print("\n❌ No records. Check debug/ screenshots.")
        return

    print(f"\n{'='*60}")
    print(f"RESULTS: {len(records)} records")
    print("=" * 60)

    all_keys = list(records[0].keys())
    print("\nColumn coverage:")
    for col in all_keys:
        populated = sum(1 for r in records if r.get(col, "").strip())
        pct = round(populated / len(records) * 100)
        sample = next((r[col] for r in records if r.get(col, "").strip()), "N/A")
        print(f"  {col:<22} {populated}/{len(records)} ({pct}%)  sample: {str(sample)[:55]}")

    from collections import Counter
    print("\nStatus breakdown:")
    for s, c in Counter(r.get("Status", "") for r in records).most_common():
        print(f"  {s}: {c}")

    print("\nSample records (first 5):")
    for r in records[:5]:
        print(
            f"  {r.get('Event ID','?'):<14} | "
            f"{r.get('Event Name','?')[:40]:<40} | "
            f"Published={r.get('Published Date','?'):<18} | "
            f"Status={r.get('Status','?')}"
        )

    print(f"\n{'='*60}")
    print("DB FIELD MAPPING")
    print("=" * 60)
    pub_ok = any(r.get("Published Date", "").strip() for r in records)
    unspsc_ok = any(r.get("UNSPSC", "").strip() for r in records)
    rows = [
        ("source_record_id", "Event ID",        "✅"),
        ("title",            "Event Name",       "✅"),
        ("posted_date",      "Published Date",   "✅" if pub_ok else "❌"),
        ("deadline",         "End Date",         "✅"),
        ("buyer_name",       "Department",       "✅"),
        ("status",           "Status",           "✅"),
        ("industry",         "UNSPSC code",      "✅" if unspsc_ok else "❌"),
        ("state_region",     '"CA" hardcoded',   "✅"),
        ("portal_region",    '"State" hardcoded',"✅"),
        ("currency",         '"USD" hardcoded',  "✅"),
        ("source_url",       "Constructed URL",  "✅"),
        ("notice_type",      "NOT IN DATA",      "❌"),
        ("naics_code",       "NOT IN DATA",      "❌"),
        ("value_numeric",    "NOT IN DATA",      "❌"),
        ("description",      "NOT IN DATA",      "❌"),
    ]
    for db_field, source, icon in rows:
        print(f"  {icon} {db_field:<22} → {source}")

    ok = sum(1 for _, _, i in rows if i == "✅")
    print(f"\nDB coverage: {ok}/{len(rows)} fields ({round(ok/len(rows)*100)}%)")


if __name__ == "__main__":
    records = asyncio.run(scrape_caleprocure())
    analyze(records)
