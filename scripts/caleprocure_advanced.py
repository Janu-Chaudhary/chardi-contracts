"""
caleprocure.ca.gov - Advanced Search Criteria flow.

Exact steps from the screenshots:
1. Load page
2. Click "Advanced Search Criteria" button
3. Set Event Status = Historical
4. Set Published Year = 2026
5. Set Start Date From = 30 days ago (mm/dd/yyyy)
6. Click Search
7. Click Download → capture JSON response
8. Parse and analyze all fields
"""

import asyncio
import json
import os
import re
from datetime import datetime, timedelta

from playwright.async_api import async_playwright

TARGET_URL = "https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx"
DEBUG_DIR = os.path.join(os.path.dirname(__file__), "..", "debug")


def date_30_days_ago() -> str:
    return (datetime.today() - timedelta(days=30)).strftime("%m/%d/%Y")


def extract_records(json_text: str) -> list[dict]:
    """Extract tblBodyTr records from PeopleSoft JSON."""
    try:
        data = json.loads(json_text)
    except Exception:
        return []

    records = []

    def get_prop(children: dict, field: str, prop: str = "text") -> str:
        items = children.get(field, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    props = item.get("Properties", {})
                    if isinstance(props, dict):
                        val = props.get(prop, "")
                        if val:
                            return str(val).strip()
        return ""

    def walk(obj):
        if isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            if "tblBodyTr" in str(obj.get("Label", "")):
                ch = obj.get("Children", {})
                rec = {
                    "Event ID":       get_prop(ch, "tdEventId"),
                    "Event Name":     get_prop(ch, "tdEventName"),
                    "Department":     get_prop(ch, "tdDepName"),
                    "Published Date": get_prop(ch, "tdPubDate")
                                   or get_prop(ch, "tdPublishedDate")
                                   or get_prop(ch, "tdStartDate"),
                    "End Date":       get_prop(ch, "tdEndDate"),
                    "Status":         get_prop(ch, "tdStatus"),
                    "UNSPSC":         get_prop(ch, "tdUnspsc")
                                   or get_prop(ch, "tdUNSPSC")
                                   or get_prop(ch, "tdCommodity"),
                    "Service Area":   get_prop(ch, "tdServiceArea"),
                }
                if rec["Event ID"] or rec["Event Name"]:
                    records.append(rec)
            else:
                for v in obj.values():
                    walk(v)

    walk(data)
    return records


async def run():
    os.makedirs(DEBUG_DIR, exist_ok=True)
    start_date = date_30_days_ago()
    print(f"Date range: {start_date} → today")

    captured: list[str] = []

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

        # Capture large JSON responses
        async def on_response(response):
            ct = response.headers.get("content-type", "")
            if "json" in ct or "javascript" in ct:
                try:
                    body = await response.body()
                    if len(body) > 20000:
                        captured.append(body.decode("utf-8", errors="replace"))
                except Exception:
                    pass

        page.on("response", on_response)

        # ── Step 1: Load ──────────────────────────────────────────────────
        print("\n[1] Loading page...")
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=90000)
        await page.screenshot(path=os.path.join(DEBUG_DIR, "adv_01_loaded.png"))
        print(f"    Title: {await page.title()}")

        # ── Step 2: Click Advanced Search Criteria ────────────────────────
        print("\n[2] Clicking 'Advanced Search Criteria'...")
        clicked = False
        for locator in [
            page.locator("a:has-text('Advanced Search Criteria')"),
            page.locator("button:has-text('Advanced Search Criteria')"),
            page.get_by_text("Advanced Search Criteria", exact=False),
            page.locator("[id*='ADVANCED'], [id*='advanced']"),
        ]:
            try:
                el = locator.first
                if await el.is_visible(timeout=3000):
                    await el.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    print("    ✅ Advanced Search opened")
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            print("    ❌ Could not find Advanced Search button")
            await page.screenshot(path=os.path.join(DEBUG_DIR, "adv_02_fail.png"))

        await page.screenshot(path=os.path.join(DEBUG_DIR, "adv_02_advanced_open.png"))

        # Dump all select IDs and options to understand the form
        print("\n    --- Form elements after Advanced Search ---")
        selects = await page.locator("select").all()
        for sel in selects:
            sel_id = await sel.get_attribute("id")
            opts = await sel.locator("option").all()
            opt_vals = []
            for o in opts:
                v = await o.get_attribute("value")
                t = (await o.inner_text()).strip()
                opt_vals.append(f"{v}={t}")
            print(f"    SELECT id={sel_id!r}: {opt_vals}")

        inputs = await page.locator("input[type=text], input:not([type])").all()
        for inp in inputs:
            inp_id = await inp.get_attribute("id")
            inp_ph = await inp.get_attribute("placeholder")
            print(f"    INPUT id={inp_id!r} placeholder={inp_ph!r}")

        # ── Step 3: Set Event Status = Historical ─────────────────────────
        print("\n[3] Setting Event Status = Historical...")
        status_set = False
        for sel_id in [
            "#RESP_INQA_WK_ZZ_EVENT_STATUS",
            "select[id*='EVENT_STATUS']",
            "select[name*='EVENT_STATUS']",
        ]:
            try:
                el = page.locator(sel_id).first
                if await el.count() > 0:
                    # Get available options first
                    opts = await el.locator("option").all()
                    print(f"    Options in {sel_id}:")
                    for o in opts:
                        v = await o.get_attribute("value")
                        t = (await o.inner_text()).strip()
                        print(f"      value={v!r} text={t!r}")

                    # Try each possible value for Historical
                    for val in ["H", "Historical", "HISTORICAL", "historical", "C", "Completed"]:
                        try:
                            await el.select_option(value=val)
                            selected = await el.input_value()
                            print(f"    ✅ Selected value={val!r}, current={selected!r}")
                            status_set = True
                            break
                        except Exception:
                            pass

                    if not status_set:
                        # Try by label
                        for label in ["Historical", "Event Completed", "Completed", "All"]:
                            try:
                                await el.select_option(label=label)
                                print(f"    ✅ Selected by label={label!r}")
                                status_set = True
                                break
                            except Exception:
                                pass
                    break
            except Exception:
                continue

        await page.wait_for_load_state("networkidle", timeout=10000)

        # ── Step 4: Set Published Year = 2026 ────────────────────────────
        print("\n[4] Setting Published Year = 2026...")
        for sel_id in [
            "#RESP_INQA_WK_ZZ_PUBLISHED_YEAR",
            "select[id*='PUBLISHED_YEAR']",
            "select[id*='publishedYear']",
            "select[name*='PUBLISHED_YEAR']",
        ]:
            try:
                el = page.locator(sel_id).first
                if await el.count() > 0:
                    opts = await el.locator("option").all()
                    print(f"    Year options: {[(await o.get_attribute('value'), (await o.inner_text()).strip()) for o in opts]}")
                    await el.select_option(value="2026")
                    print(f"    ✅ Set year to 2026")
                    break
            except Exception:
                continue

        # ── Step 5: Set Start Date From ───────────────────────────────────
        print(f"\n[5] Setting Start Date From = {start_date}...")
        for inp_id in [
            "#RESP_INQA_WK_AUC_FROM_START_DT",
            "input[id*='FROM_START_DT']",
            "input[id*='START_DATE_FROM']",
            "input[placeholder*='mm/dd/yyyy']",
        ]:
            try:
                el = page.locator(inp_id).first
                if await el.count() > 0:
                    await el.triple_click()
                    await el.fill(start_date)
                    await page.keyboard.press("Tab")
                    await asyncio.sleep(0.5)
                    val = await el.input_value()
                    print(f"    ✅ Set via {inp_id!r}, value={val!r}")
                    break
            except Exception:
                continue

        await page.screenshot(path=os.path.join(DEBUG_DIR, "adv_03_filters.png"))

        # ── Step 6: Click Search ──────────────────────────────────────────
        print("\n[6] Clicking Search...")
        captured.clear()
        for sel in [
            "button[id*='GO_PB']",
            "input[id*='GO_PB']",
            "button:has-text('Search')",
            "input[value='Search']",
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=3000):
                    await el.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    print(f"    ✅ Clicked via {sel!r}")
                    break
            except Exception:
                continue

        await page.screenshot(path=os.path.join(DEBUG_DIR, "adv_04_results.png"))

        # Check result count and status
        body_text = await page.inner_text("body")
        match = re.search(r"Showing[^0-9]*(\d+)[^0-9]*of[^0-9]*(\d+)", body_text)
        if match:
            print(f"    Results: {match.group(1)} of {match.group(2)}")

        # Check what statuses are showing
        status_sample = re.findall(r"(Posted|Historical|Event Completed|Completed|Closed)", body_text)
        print(f"    Status values in page: {list(set(status_sample))}")

        # ── Step 7: Click Download ────────────────────────────────────────
        print("\n[7] Clicking Download...")
        captured.clear()

        download_btn = page.locator("[id='RESP_INQA_HD_VW_GR$hexcel$0']").first
        try:
            await download_btn.wait_for(state="visible", timeout=10000)
            await download_btn.click()
            await page.wait_for_load_state("networkidle", timeout=30000)
            print(f"    Captured {len(captured)} JSON responses")
        except Exception as e:
            print(f"    Primary download btn failed: {e}")
            # Try alternate
            for alt in ["button[aria-label='Download']", "[id*='hexcel']"]:
                try:
                    el = page.locator(alt).first
                    if await el.is_visible(timeout=3000):
                        await el.click()
                        await page.wait_for_load_state("networkidle", timeout=30000)
                        print(f"    ✅ Alternate download clicked: {alt}")
                        break
                except Exception:
                    continue

        await page.screenshot(path=os.path.join(DEBUG_DIR, "adv_05_downloaded.png"))
        await browser.close()

    # ── Step 8: Parse ─────────────────────────────────────────────────────
    print(f"\n[8] Parsing {len(captured)} JSON responses...")
    for i, j in enumerate(sorted(captured, key=len, reverse=True)[:5]):
        print(f"    Response {i}: {len(j):,} chars")

    records = []
    for json_text in sorted(captured, key=len, reverse=True):
        recs = extract_records(json_text)
        if recs:
            print(f"    ✅ Extracted {len(recs)} records")
            records = recs
            break

    # ── Step 9: Analyze ───────────────────────────────────────────────────
    if not records:
        print("\n❌ No records. Check debug/ screenshots.")
        return

    print(f"\n{'='*60}")
    print(f"RESULTS: {len(records)} records")
    print("=" * 60)

    all_keys = set(k for r in records for k in r)
    for col in sorted(all_keys):
        populated = sum(1 for r in records if r.get(col, "").strip())
        pct = round(populated / len(records) * 100)
        sample = next((r[col] for r in records if r.get(col, "").strip()), "N/A")
        print(f"  {col:<22} {populated}/{len(records)} ({pct}%)  sample: {str(sample)[:60]}")

    from collections import Counter
    print("\nStatus breakdown:")
    for s, c in Counter(r.get("Status", "") for r in records).most_common():
        print(f"  {s!r}: {c}")

    print("\nSample records:")
    for r in records[:5]:
        print(f"  {r.get('Event ID','?'):<12} | {r.get('Event Name','?')[:40]:<40} | "
              f"Pub={r.get('Published Date','?'):<18} | "
              f"End={r.get('End Date','?'):<18} | "
              f"Status={r.get('Status','?')}")


if __name__ == "__main__":
    asyncio.run(run())
