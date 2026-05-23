"""
Capture clean screenshots of the deployed Chardi Contracts dashboard.
Screenshots are saved to docs/screenshots/ for use in README.
No browser chrome (tabs/toolbar) — uses headless Chromium.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time

BASE_URL = "https://chardi-contracts.vercel.app"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORT_DESKTOP = {"width": 1440, "height": 900}
VIEWPORT_MOBILE  = {"width": 390,  "height": 844}   # iPhone 14 Pro

def wait_and_screenshot(page, path: Path, wait_ms: int = 2500):
    """Wait for network idle + extra ms, then screenshot."""
    page.wait_for_load_state("networkidle")
    time.sleep(wait_ms / 1000)
    page.screenshot(path=str(path), full_page=False)
    print(f"  ✓  {path.name}")


def run():
    with sync_playwright() as p:
        # ── Desktop screenshots ──────────────────────────────────────────
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport=VIEWPORT_DESKTOP,
            device_scale_factor=2,          # retina-quality
        )
        page = ctx.new_page()

        print("\n── Desktop (1440×900) ──")

        # 1. Dashboard / Overview
        page.goto(BASE_URL, wait_until="domcontentloaded")
        wait_and_screenshot(page, OUT_DIR / "01_dashboard_overview.png")

        # 2. Contracts Explorer — default view
        page.goto(f"{BASE_URL}/contracts", wait_until="domcontentloaded")
        wait_and_screenshot(page, OUT_DIR / "02_contracts_explorer.png")

        # 3. Contracts Explorer — with search active
        page.goto(f"{BASE_URL}/contracts?q=cloud+infrastructure", wait_until="domcontentloaded")
        wait_and_screenshot(page, OUT_DIR / "03_contracts_search.png")

        # 4. Contracts Explorer — filtered by Federal / SAM.gov
        page.goto(f"{BASE_URL}/contracts?portal=SAM.gov&status=OPEN", wait_until="domcontentloaded")
        wait_and_screenshot(page, OUT_DIR / "04_contracts_filtered_samgov.png")

        # 5. Trends / Charts page
        page.goto(f"{BASE_URL}/trends", wait_until="domcontentloaded")
        wait_and_screenshot(page, OUT_DIR / "05_trends_charts.png")

        # 6. Single contract detail — grab first id from contracts page
        page.goto(f"{BASE_URL}/contracts", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        # Try clicking first contract row/card
        try:
            first_link = page.locator("table tbody tr td a").first
            if first_link.count() == 0:
                first_link = page.locator("a[href*='/contracts/']").first
            href = first_link.get_attribute("href")
            if href:
                detail_url = BASE_URL + href if href.startswith("/") else href
                page.goto(detail_url, wait_until="domcontentloaded")
                wait_and_screenshot(page, OUT_DIR / "06_contract_detail.png")
            else:
                print("  ⚠  Could not find detail link — skipping detail screenshot")
        except Exception as e:
            print(f"  ⚠  Detail page skip: {e}")

        ctx.close()

        # ── Mobile screenshots ───────────────────────────────────────────
        ctx_mobile = browser.new_context(
            viewport=VIEWPORT_MOBILE,
            device_scale_factor=3,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        )
        page_m = ctx_mobile.new_page()

        print("\n── Mobile (390×844 — iPhone 14 Pro) ──")

        # 7. Dashboard mobile
        page_m.goto(BASE_URL, wait_until="domcontentloaded")
        wait_and_screenshot(page_m, OUT_DIR / "07_mobile_dashboard.png")

        # 8. Contracts mobile (card view)
        page_m.goto(f"{BASE_URL}/contracts", wait_until="domcontentloaded")
        wait_and_screenshot(page_m, OUT_DIR / "08_mobile_contracts_cards.png")

        ctx_mobile.close()
        browser.close()

    print(f"\n✅  All screenshots saved to: {OUT_DIR}\n")
    for f in sorted(OUT_DIR.glob("*.png")):
        size_kb = f.stat().st_size // 1024
        print(f"   {f.name}  ({size_kb} KB)")


if __name__ == "__main__":
    run()
