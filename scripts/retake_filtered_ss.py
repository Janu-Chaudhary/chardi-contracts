"""
Retake the filtered SAM.gov screenshot — uses shadcn combobox click interaction.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time

BASE_URL = "https://chardi-contracts.vercel.app"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"


def select_combobox_option(page, button_id: str, option_text: str):
    """Click a shadcn combobox button and select an option by visible text."""
    btn = page.locator(f"#{button_id}")
    btn.click()
    time.sleep(0.8)
    # Options appear in a listbox/popover
    option = page.get_by_role("option", name=option_text, exact=False).first
    if option.count() == 0:
        # fallback: find by text in any visible element
        option = page.locator(f"[role='listbox'] [role='option']").filter(has_text=option_text).first
    option.click()
    time.sleep(0.8)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page = ctx.new_page()

        print("Opening contracts page...")
        page.goto(f"{BASE_URL}/contracts", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Apply Portal = SAM.gov
        print("Applying Portal filter: SAM.gov...")
        try:
            select_combobox_option(page, "filter-portal", "SAM.gov")
            print("  ✓ Portal set to SAM.gov")
        except Exception as e:
            print(f"  ✗ Portal filter failed: {e}")

        page.wait_for_load_state("networkidle")
        time.sleep(1.5)

        # Apply Status = OPEN
        print("Applying Status filter: OPEN...")
        try:
            select_combobox_option(page, "filter-status", "OPEN")
            print("  ✓ Status set to OPEN")
        except Exception as e:
            print(f"  ✗ Status filter failed: {e}")

        page.wait_for_load_state("networkidle")
        time.sleep(2.5)

        out_path = OUT_DIR / "04_contracts_filtered_samgov.png"
        page.screenshot(path=str(out_path), full_page=False)
        size_kb = out_path.stat().st_size // 1024
        print(f"\n✅  Saved: {out_path.name} ({size_kb} KB)")

        ctx.close()
        browser.close()


if __name__ == "__main__":
    run()
