"""
Render the database schema diagram to a clean PNG using Playwright.
Shows the 3-table architecture with columns, types, relationships, and key design decisions.
Output: docs/screenshots/db_schema.png
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time

OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "screenshots" / "db_schema.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

MERMAID_CODE = """erDiagram
    scrape_runs {
        int id PK "SERIAL — auto-increment run ID"
        text source_portal "SAM.gov · caleprocure · etc."
        timestamptz start_time "Run start"
        timestamptz end_time "NULL while running"
        text status "RUNNING · SUCCESS · PARTIAL_SUCCESS · FAILED"
        int records_scraped "Rows upserted this run"
        jsonb metadata "days · task_count · error_count · windows"
    }

    scrape_errors {
        int id PK "SERIAL"
        int run_id FK "→ scrape_runs.id"
        text source_portal "Which portal failed"
        text error_message "Exception or HTTP status"
        jsonb raw_payload "posted_from · posted_to · traceback"
        timestamptz created_at "Auto-set on insert"
    }

    opportunities {
        varchar id PK "SHA-256 deterministic hash (64 chars)"
        text source_portal "Portal name"
        text source_record_id "Portal native ID"
        text solicitation_number "RFP number if available"
        text portal_region "Federal · State · County · City"
        text title "Opportunity title — required"
        text description "Full text or URL"
        text notice_type "Solicitation · Award · Term · General"
        timestamptz posted_date "Publication date"
        timestamptz deadline "Submission deadline"
        text state_region "2-letter state code"
        text industry "NAICS or NIGP category"
        text naics_code "NAICS code — SAM.gov only"
        numeric value_numeric "Contract value — NULL most portals"
        text status "OPEN · CLOSED · AWARDED · CANCELLED"
        text buyer_name "Issuing agency"
        text buyer_type "OFFICE · State · Federal Agency"
        text source_url "Direct link to notice"
        jsonb documents "Array of title+url attachments"
        jsonb raw_payload "Full original API response"
        timestamptz last_seen_at "Updated every upsert"
        timestamptz created_at "First indexed"
        timestamptz updated_at "Trigger-managed"
    }

    award_winners {
        int id PK "SERIAL"
        text vendor_name "Winning vendor name"
        text industry "Industry or NAICS category"
        text state_region "2-letter state code"
        text source_portal "Source portal"
        int win_count "Number of wins"
        numeric total_value "Sum of contract values"
        numeric avg_value "Average contract value"
        timestamptz last_win_date "Most recent win date"
        timestamptz updated_at "Refreshed after each ingest"
    }

    scrape_runs ||--o{ scrape_errors : "has"
    opportunities ||--o{ award_winners : "aggregated into"
"""


def render_db_schema(page, diagram: str, out_path: Path) -> bool:
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #ffffff;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 48px 40px;
    font-family: 'Inter', -apple-system, sans-serif;
  }}
  #diagram {{
    background: #ffffff;
    width: 100%;
    max-width: 1300px;
  }}
  .mermaid {{
    display: flex;
    justify-content: center;
  }}
  /* Style the ER diagram */
  .er.entityBox {{ fill: #F7F3F2 !important; stroke: #E0DCDA !important; }}
  .er.attributeBoxEven {{ fill: #FFFBF7 !important; stroke: #E0DCDA !important; }}
  .er.attributeBoxOdd {{ fill: #F7F3F2 !important; stroke: #E0DCDA !important; }}
</style>
</head>
<body>
<div id="diagram">
<div class="mermaid">
{diagram}
</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'default',
    er: {{
      diagramPadding: 40,
      layoutDirection: 'TB',
      minEntityWidth: 100,
      minEntityHeight: 75,
      entityPadding: 15,
      useMaxWidth: true,
    }},
    themeVariables: {{
      primaryColor: '#F7F3F2',
      primaryTextColor: '#1F1A17',
      primaryBorderColor: '#E0DCDA',
      lineColor: '#1A0D0A',
      secondaryColor: '#FFFBF7',
      background: '#FFFFFF',
      mainBkg: '#F7F3F2',
      nodeBorder: '#E0DCDA',
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontSize: '13px',
      attributeBackgroundColorEven: '#FFFBF7',
      attributeBackgroundColorOdd: '#F7F3F2',
    }}
  }});
</script>
</body>
</html>"""

    tmp_html = out_path.parent / "_tmp_db_schema.html"
    tmp_html.write_text(html, encoding="utf-8")

    try:
        page.goto(f"file://{tmp_html}", wait_until="domcontentloaded")
        page.wait_for_function("() => document.querySelector('svg') !== null", timeout=15000)
        time.sleep(3)  # ER diagrams need more settle time

        diagram_el = page.locator("#diagram")
        diagram_el.screenshot(path=str(out_path))
        print(f"  ✓  Rendered: {out_path.name}")
        return True
    except Exception as e:
        print(f"  ✗  Render failed: {e}")
        return False
    finally:
        tmp_html.unlink(missing_ok=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1600, "height": 1200},
            device_scale_factor=2,
        )
        page = ctx.new_page()

        print("\n── Rendering DB schema diagram ──")
        render_db_schema(page, MERMAID_CODE, OUT_PATH)

        ctx.close()
        browser.close()

    if OUT_PATH.exists():
        size_kb = OUT_PATH.stat().st_size // 1024
        print(f"\n✅  db_schema.png saved ({size_kb} KB)")
        print(f"   Path: {OUT_PATH}")
    else:
        print("\n✗  db_schema.png was not created")


if __name__ == "__main__":
    run()
