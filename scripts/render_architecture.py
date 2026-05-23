"""
Render the Mermaid architecture diagram to a clean PNG using Playwright.
Uses mermaid.live to render, then screenshots just the diagram element.
Output: docs/screenshots/architecture.png
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import urllib.parse
import json
import base64
import time

OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "screenshots" / "architecture.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

MERMAID_CODE = """flowchart TD
    subgraph SOURCES["  Data Sources  "]
        direction TB
        S1["SAM.gov · Federal API v2"]
        S2["Cal eProcure · Playwright + Excel"]
        S3["TxSmartBuy · Playwright + CSV"]
        S4["NYSCR · Async HTTP"]
        S5["NYC Open Data · Socrata API"]
        S6["Chicago Data Portal · Socrata API"]
        S7["Virginia eVA + VITA · Async HTTP"]
        S8["Georgia TGM · Playwright"]
        S9["Illinois BidBuy · Playwright"]
        S10["Florida DMS · Async HTTP"]
    end

    subgraph WORKERS["  Python Workers  ·  backend/workers/  "]
        W1["fetcher.py · aiohttp · rate limits · retry"]
        W2["mapper.py · normalize · sanitize · fingerprint"]
        W3["main.py · lifecycle orchestrator"]
    end

    subgraph CORE["  Shared Core  ·  backend/core/  "]
        FP["fingerprint.py · SHA-256 deterministic ID"]
        DB["db.py · asyncpg pool · upsert SQL"]
    end

    subgraph PG["  Neon PostgreSQL  "]
        T1[("opportunities · 10,735 records")]
        T2[("scrape_runs · lifecycle log")]
        T3[("scrape_errors · dead-letter log")]
    end

    subgraph CRON["  GitHub Actions · daily 06:00 UTC  "]
        GH["11 parallel jobs + smoke test"]
    end

    subgraph API["  Next.js Edge API  ·  /api/  "]
        A1["/stats · /opportunities · /filters"]
        A2["/charts/* · /export"]
    end

    subgraph UI["  Next.js Dashboard · Vercel  "]
        U1["Overview · KPIs"]
        U2["Contracts Explorer · search · filter · sort"]
        U3["Trends · charts · deadlines"]
    end

    SOURCES --> WORKERS
    WORKERS --> CORE
    FP --> DB
    DB --> T1 & T2 & T3
    CRON --> WORKERS
    T1 --> API
    API --> UI"""


def build_mermaid_live_url(diagram: str) -> str:
    """Build a mermaid.live URL with the diagram encoded."""
    config = {
        "code": diagram,
        "mermaid": {
            "theme": "default",
            "themeVariables": {
                "primaryColor": "#FFFBF7",
                "primaryTextColor": "#1F1A17",
                "primaryBorderColor": "#E0DCDA",
                "lineColor": "#1F1A17",
                "secondaryColor": "#F7F3F2",
                "tertiaryColor": "#FFFBF7",
                "background": "#FFFFFF",
                "mainBkg": "#FFFBF7",
                "nodeBorder": "#E0DCDA",
                "clusterBkg": "#F7F3F2",
                "titleColor": "#1F1A17",
                "edgeLabelBackground": "#FFFFFF",
                "fontFamily": "Inter, sans-serif",
            }
        },
        "autoSync": True,
        "rough": False,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(config).encode("utf-8")
    ).decode("utf-8")
    return f"https://mermaid.live/view#base64:{encoded}"


def render_via_cdn(page, diagram: str, out_path: Path) -> bool:
    """Render using mermaid CDN in a local HTML page."""
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
    padding: 40px;
    font-family: 'Inter', -apple-system, sans-serif;
  }}
  #diagram {{
    background: #ffffff;
    max-width: 1200px;
    width: 100%;
  }}
  .mermaid {{
    display: flex;
    justify-content: center;
  }}
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
    flowchart: {{
      curve: 'basis',
      padding: 20,
      nodeSpacing: 50,
      rankSpacing: 60,
    }},
    themeVariables: {{
      primaryColor: '#F7F3F2',
      primaryTextColor: '#1F1A17',
      primaryBorderColor: '#E0DCDA',
      lineColor: '#1A0D0A',
      secondaryColor: '#FFFBF7',
      tertiaryColor: '#FFFFFF',
      background: '#FFFFFF',
      mainBkg: '#F7F3F2',
      nodeBorder: '#E0DCDA',
      clusterBkg: '#FFFBF7',
      clusterBorder: '#E0DCDA',
      titleColor: '#1F1A17',
      edgeLabelBackground: '#FFFFFF',
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontSize: '14px',
    }}
  }});
  window.mermaidDone = false;
  document.addEventListener('DOMContentLoaded', function() {{
    setTimeout(function() {{ window.mermaidDone = true; }}, 3000);
  }});
</script>
</body>
</html>"""

    # Write temp HTML file
    tmp_html = out_path.parent / "_tmp_diagram.html"
    tmp_html.write_text(html, encoding="utf-8")

    try:
        page.goto(f"file://{tmp_html}", wait_until="domcontentloaded")
        # Wait for mermaid to render
        page.wait_for_function("() => document.querySelector('svg') !== null", timeout=15000)
        time.sleep(2)  # extra settle time

        # Screenshot just the diagram element
        diagram_el = page.locator("#diagram")
        diagram_el.screenshot(path=str(out_path))
        print(f"  ✓  Rendered via CDN: {out_path.name}")
        return True
    except Exception as e:
        print(f"  ✗  CDN render failed: {e}")
        return False
    finally:
        tmp_html.unlink(missing_ok=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            device_scale_factor=2,
        )
        page = ctx.new_page()

        print("\n── Rendering architecture diagram ──")
        success = render_via_cdn(page, MERMAID_CODE, OUT_PATH)

        if not success:
            # Fallback: screenshot the mermaid.live URL
            print("  → Trying mermaid.live fallback...")
            try:
                url = build_mermaid_live_url(MERMAID_CODE)
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle")
                time.sleep(4)
                # Try to get just the diagram container
                try:
                    el = page.locator("#view").or_(page.locator(".mermaid-diagram"))
                    el.first.screenshot(path=str(OUT_PATH))
                except Exception:
                    page.screenshot(path=str(OUT_PATH))
                print(f"  ✓  Rendered via mermaid.live: {OUT_PATH.name}")
            except Exception as e:
                print(f"  ✗  All render methods failed: {e}")

        ctx.close()
        browser.close()

    if OUT_PATH.exists():
        size_kb = OUT_PATH.stat().st_size // 1024
        print(f"\n✅  architecture.png saved ({size_kb} KB)")
        print(f"   Path: {OUT_PATH}")
    else:
        print("\n✗  architecture.png was not created")


if __name__ == "__main__":
    run()
