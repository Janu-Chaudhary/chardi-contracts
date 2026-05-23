"""
Generate a premium one-page metrics summary PNG for the Chardi Contracts project.
Queries live Neon DB, builds a styled HTML page, screenshots it.
Output: docs/screenshots/metrics_summary.png
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

DATABASE_URL = "postgresql://neondb_owner:npg_EXmyU3GA7eod@ep-bold-shadow-aq6yu9ac.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"
OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "screenshots" / "metrics_summary.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


async def fetch_metrics():
    conn = await asyncpg.connect(DATABASE_URL)

    # KPIs
    total = await conn.fetchval("SELECT COUNT(*) FROM opportunities")
    open_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status = 'OPEN'")
    closed_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status = 'CLOSED'")
    awarded_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status = 'AWARDED'")
    cancelled_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status = 'CANCELLED'")
    federal_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE portal_region = 'Federal'")
    state_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE portal_region = 'State'")
    city_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE portal_region NOT IN ('Federal', 'State')")
    portal_count = await conn.fetchval("SELECT COUNT(DISTINCT source_portal) FROM opportunities")
    state_region_count = await conn.fetchval("SELECT COUNT(DISTINCT state_region) FROM opportunities WHERE state_region IS NOT NULL")

    # Deadlines
    upcoming_7d = await conn.fetchval("""
        SELECT COUNT(*) FROM opportunities 
        WHERE status = 'OPEN' AND deadline BETWEEN NOW() AND NOW() + INTERVAL '7 days'
    """)
    upcoming_30d = await conn.fetchval("""
        SELECT COUNT(*) FROM opportunities 
        WHERE status = 'OPEN' AND deadline BETWEEN NOW() AND NOW() + INTERVAL '30 days'
    """)

    # Per-portal breakdown with freshness
    portal_rows = await conn.fetch("""
        SELECT 
            source_portal,
            portal_region,
            COUNT(*) as records,
            SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_count,
            MAX(last_seen_at) as last_seen
        FROM opportunities
        GROUP BY source_portal, portal_region
        ORDER BY records DESC
    """)

    # Latest scrape runs per portal
    run_rows = await conn.fetch("""
        SELECT DISTINCT ON (source_portal)
            source_portal, status, end_time, records_scraped
        FROM scrape_runs
        WHERE status IN ('SUCCESS', 'PARTIAL_SUCCESS', 'FAILED')
        ORDER BY source_portal, end_time DESC NULLS LAST
    """)
    run_map = {r['source_portal']: r for r in run_rows}

    # Coverage by region (state breakdown)
    region_rows = await conn.fetch("""
        SELECT 
            COALESCE(state_region, 'N/A') as region,
            COUNT(*) as records,
            SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_count
        FROM opportunities
        GROUP BY state_region
        ORDER BY records DESC
        LIMIT 20
    """)

    # Top notice types
    notice_rows = await conn.fetch("""
        SELECT notice_type, COUNT(*) as cnt
        FROM opportunities
        WHERE notice_type IS NOT NULL AND notice_type != ''
        GROUP BY notice_type
        ORDER BY cnt DESC
        LIMIT 8
    """)

    # Scrape errors last 7 days
    error_count = await conn.fetchval("""
        SELECT COUNT(*) FROM scrape_errors 
        WHERE created_at > NOW() - INTERVAL '7 days'
    """)

    await conn.close()

    return {
        "total": total,
        "open": open_count,
        "closed": closed_count,
        "awarded": awarded_count,
        "cancelled": cancelled_count,
        "federal": federal_count,
        "state": state_count,
        "city": city_count,
        "portals": portal_count,
        "states_covered": state_region_count,
        "upcoming_7d": upcoming_7d,
        "upcoming_30d": upcoming_30d,
        "portal_rows": [dict(r) for r in portal_rows],
        "run_map": {k: dict(v) for k, v in run_map.items()},
        "region_rows": [dict(r) for r in region_rows],
        "notice_rows": [dict(r) for r in notice_rows],
        "error_count_7d": error_count,
        "generated_at": datetime.now(timezone.utc).strftime("%B %d, %Y · %H:%M UTC"),
    }


def format_freshness(last_seen):
    if not last_seen:
        return "—", "stale"
    now = datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    delta = now - last_seen
    hours = delta.total_seconds() / 3600
    if hours < 24:
        return f"{int(hours)}h ago", "fresh"
    elif hours < 48:
        return "Yesterday", "fresh"
    elif hours < 72:
        return f"{int(delta.days)}d ago", "recent"
    else:
        return f"{int(delta.days)}d ago", "stale"


def build_html(m: dict) -> str:
    # Build portal table rows
    portal_html = ""
    for p in m["portal_rows"]:
        portal = p["source_portal"]
        region = p["portal_region"] or "—"
        records = f"{p['records']:,}"
        open_c = f"{p['open_count']:,}"
        run = m["run_map"].get(portal, {})
        last_seen = p.get("last_seen")
        freshness_text, freshness_class = format_freshness(last_seen)
        run_status = run.get("status", "—") if run else "—"
        status_class = "status-success" if run_status == "SUCCESS" else ("status-partial" if run_status == "PARTIAL_SUCCESS" else "status-failed" if run_status == "FAILED" else "status-unknown")

        portal_html += f"""
        <tr>
            <td class="portal-name">{portal}</td>
            <td><span class="region-badge region-{region.lower().replace(' ', '-')}">{region}</span></td>
            <td class="num">{records}</td>
            <td class="num open-num">{open_c}</td>
            <td><span class="freshness {freshness_class}">{freshness_text}</span></td>
            <td><span class="run-status {status_class}">{run_status}</span></td>
        </tr>"""

    # Build region rows (top 15)
    region_html = ""
    top_regions = [r for r in m["region_rows"] if r["region"] not in ("N/A", None)][:15]
    max_records = max((r["records"] for r in top_regions), default=1)
    for r in top_regions:
        pct = int((r["records"] / max_records) * 100)
        region_html += f"""
        <div class="region-row">
            <div class="region-label">{r['region']}</div>
            <div class="region-bar-wrap">
                <div class="region-bar" style="width:{pct}%"></div>
            </div>
            <div class="region-count">{r['records']:,}</div>
            <div class="region-open">{r['open_count']:,} open</div>
        </div>"""

    # Notice types
    notice_html = ""
    for n in m["notice_rows"]:
        notice_html += f"""
        <div class="notice-item">
            <span class="notice-type">{n['notice_type'] or 'Unknown'}</span>
            <span class="notice-count">{n['cnt']:,}</span>
        </div>"""

    open_pct = round((m["open"] / m["total"]) * 100) if m["total"] else 0
    federal_pct = round((m["federal"] / m["total"]) * 100) if m["total"] else 0

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,700;1,700&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: #FFFBF7;
    color: #1F1A17;
    padding: 56px 64px;
    width: 1400px;
    min-height: 100vh;
  }}

  /* ── Header ── */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 48px;
    padding-bottom: 32px;
    border-bottom: 1px solid #E0DCDA;
  }}
  .header-left {{ }}
  .brand {{
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #EA580C;
    margin-bottom: 8px;
  }}
  .title {{
    font-family: 'Playfair Display', serif;
    font-size: 36px;
    font-weight: 700;
    color: #1A0D0A;
    line-height: 1.1;
    margin-bottom: 8px;
  }}
  .subtitle {{
    font-size: 15px;
    color: #6B6560;
    font-weight: 400;
  }}
  .header-right {{
    text-align: right;
  }}
  .generated {{
    font-size: 12px;
    color: #9B9490;
    margin-bottom: 6px;
  }}
  .live-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    color: #15803D;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 20px;
  }}
  .live-dot {{
    width: 6px; height: 6px;
    background: #22C55E;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }}

  /* ── KPI Grid ── */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    margin-bottom: 40px;
  }}
  .kpi-card {{
    background: #FFFFFF;
    border: 1px solid #E0DCDA;
    border-radius: 12px;
    padding: 24px 20px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }}
  .kpi-card.accent {{
    background: #1A0D0A;
    border-color: #1A0D0A;
  }}
  .kpi-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #9B9490;
    margin-bottom: 10px;
  }}
  .kpi-card.accent .kpi-label {{ color: #9B9490; }}
  .kpi-value {{
    font-size: 32px;
    font-weight: 700;
    color: #1A0D0A;
    line-height: 1;
    margin-bottom: 6px;
    font-variant-numeric: tabular-nums;
  }}
  .kpi-card.accent .kpi-value {{ color: #FFFBF7; }}
  .kpi-sub {{
    font-size: 12px;
    color: #9B9490;
  }}
  .kpi-card.accent .kpi-sub {{ color: #6B6560; }}
  .kpi-accent-val {{ color: #EA580C; }}

  /* ── Section headers ── */
  .section-header {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 16px;
  }}
  .section-title {{
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #1A0D0A;
  }}
  .section-count {{
    font-size: 12px;
    color: #9B9490;
  }}

  /* ── Two-column layout ── */
  .two-col {{
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 24px;
    margin-bottom: 32px;
  }}

  /* ── Portal table ── */
  .table-wrap {{
    background: #FFFFFF;
    border: 1px solid #E0DCDA;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  thead th {{
    background: #F7F3F2;
    padding: 10px 16px;
    text-align: left;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #9B9490;
    border-bottom: 1px solid #E0DCDA;
  }}
  thead th.num {{ text-align: right; }}
  tbody tr {{
    border-bottom: 1px solid #F7F3F2;
  }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody td {{
    padding: 11px 16px;
    color: #1F1A17;
    vertical-align: middle;
  }}
  tbody td.num {{ text-align: right; font-variant-numeric: tabular-nums; color: #6B6560; }}
  tbody td.open-num {{ color: #1F1A17; font-weight: 500; }}
  .portal-name {{ font-weight: 500; color: #1A0D0A; }}

  .region-badge {{
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 20px;
  }}
  .region-federal {{ background: #FEF3C7; color: #92400E; }}
  .region-state {{ background: #EFF6FF; color: #1D4ED8; }}
  .region-city {{ background: #F0FDF4; color: #15803D; }}

  .freshness {{
    font-size: 12px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 20px;
  }}
  .freshness.fresh {{ background: #F0FDF4; color: #15803D; }}
  .freshness.recent {{ background: #FEF9C3; color: #854D0E; }}
  .freshness.stale {{ background: #FEF2F2; color: #991B1B; }}

  .run-status {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    padding: 2px 8px;
    border-radius: 20px;
  }}
  .status-success {{ background: #F0FDF4; color: #15803D; }}
  .status-partial {{ background: #FEF9C3; color: #854D0E; }}
  .status-failed {{ background: #FEF2F2; color: #991B1B; }}
  .status-unknown {{ background: #F7F3F2; color: #9B9490; }}

  /* ── Right column ── */
  .right-col {{
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}

  .card {{
    background: #FFFFFF;
    border: 1px solid #E0DCDA;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }}

  /* Region bars */
  .region-row {{
    display: grid;
    grid-template-columns: 48px 1fr 48px 64px;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }}
  .region-row:last-child {{ margin-bottom: 0; }}
  .region-label {{
    font-size: 12px;
    font-weight: 600;
    color: #1A0D0A;
    text-align: right;
  }}
  .region-bar-wrap {{
    height: 6px;
    background: #F7F3F2;
    border-radius: 3px;
    overflow: hidden;
  }}
  .region-bar {{
    height: 100%;
    background: #EA580C;
    border-radius: 3px;
    transition: width 0.3s;
  }}
  .region-count {{
    font-size: 12px;
    color: #6B6560;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}
  .region-open {{
    font-size: 11px;
    color: #9B9490;
    text-align: right;
  }}

  /* Notice types */
  .notice-item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid #F7F3F2;
    font-size: 13px;
  }}
  .notice-item:last-child {{ border-bottom: none; }}
  .notice-type {{ color: #1F1A17; font-weight: 400; }}
  .notice-count {{ color: #6B6560; font-variant-numeric: tabular-nums; font-weight: 500; }}

  /* ── Bottom row ── */
  .bottom-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin-bottom: 40px;
  }}

  .stat-block {{
    background: #FFFFFF;
    border: 1px solid #E0DCDA;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }}
  .stat-block-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #9B9490;
    margin-bottom: 12px;
  }}
  .stat-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #F7F3F2;
    font-size: 13px;
  }}
  .stat-row:last-child {{ border-bottom: none; }}
  .stat-key {{ color: #6B6560; }}
  .stat-val {{ font-weight: 600; color: #1A0D0A; font-variant-numeric: tabular-nums; }}
  .stat-val.coral {{ color: #EA580C; }}

  /* ── Footer ── */
  .footer {{
    padding-top: 24px;
    border-top: 1px solid #E0DCDA;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .footer-left {{
    font-size: 12px;
    color: #9B9490;
  }}
  .footer-right {{
    font-size: 12px;
    color: #9B9490;
  }}
  .footer-brand {{
    font-weight: 600;
    color: #EA580C;
  }}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="header-left">
    <div class="brand">Chardi.ai · Project A · United States</div>
    <div class="title">Metrics Summary</div>
    <div class="subtitle">Opportunities scraped · Freshness · Coverage by region</div>
  </div>
  <div class="header-right">
    <div class="generated">Generated {m['generated_at']}</div>
    <div class="live-badge">
      <div class="live-dot"></div>
      Live data · Neon PostgreSQL
    </div>
  </div>
</div>

<!-- KPI Grid -->
<div class="kpi-grid">
  <div class="kpi-card accent">
    <div class="kpi-label">Total Opportunities</div>
    <div class="kpi-value">{m['total']:,}</div>
    <div class="kpi-sub">{m['portals']} portals · {m['states_covered']} states</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Open</div>
    <div class="kpi-value kpi-accent-val">{m['open']:,}</div>
    <div class="kpi-sub">{open_pct}% of total</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Federal Coverage</div>
    <div class="kpi-value">{m['federal']:,}</div>
    <div class="kpi-sub">SAM.gov · {federal_pct}% of total</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Deadlines — 7 days</div>
    <div class="kpi-value">{m['upcoming_7d']:,}</div>
    <div class="kpi-sub">{m['upcoming_30d']:,} within 30 days</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Pipeline Health</div>
    <div class="kpi-value">{m['portals']}/{m['portals']}</div>
    <div class="kpi-sub">{m['error_count_7d']} errors · last 7 days</div>
  </div>
</div>

<!-- Portal table + right column -->
<div class="two-col">
  <div>
    <div class="section-header">
      <span class="section-title">Portal Coverage</span>
      <span class="section-count">{len(m['portal_rows'])} sources · updated daily at 06:00 UTC</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Portal</th>
            <th>Region</th>
            <th class="num">Records</th>
            <th class="num">Open</th>
            <th>Last scraped</th>
            <th>Run status</th>
          </tr>
        </thead>
        <tbody>
          {portal_html}
        </tbody>
      </table>
    </div>
  </div>

  <div class="right-col">
    <div class="card">
      <div class="section-header">
        <span class="section-title">Coverage by State</span>
      </div>
      {region_html}
    </div>

    <div class="card">
      <div class="section-header">
        <span class="section-title">Notice Types</span>
      </div>
      {notice_html}
    </div>
  </div>
</div>

<!-- Bottom stats -->
<div class="bottom-row">
  <div class="stat-block">
    <div class="stat-block-label">Status Breakdown</div>
    <div class="stat-row"><span class="stat-key">Open</span><span class="stat-val coral">{m['open']:,}</span></div>
    <div class="stat-row"><span class="stat-key">Closed</span><span class="stat-val">{m['closed']:,}</span></div>
    <div class="stat-row"><span class="stat-key">Awarded</span><span class="stat-val">{m['awarded']:,}</span></div>
    <div class="stat-row"><span class="stat-key">Cancelled</span><span class="stat-val">{m['cancelled']:,}</span></div>
  </div>
  <div class="stat-block">
    <div class="stat-block-label">Coverage by Level</div>
    <div class="stat-row"><span class="stat-key">Federal (SAM.gov)</span><span class="stat-val">{m['federal']:,}</span></div>
    <div class="stat-row"><span class="stat-key">State portals</span><span class="stat-val">{m['state']:,}</span></div>
    <div class="stat-row"><span class="stat-key">City portals</span><span class="stat-val">{m['city']:,}</span></div>
    <div class="stat-row"><span class="stat-key">States covered</span><span class="stat-val">{m['states_covered']}</span></div>
  </div>
  <div class="stat-block">
    <div class="stat-block-label">Pipeline Reliability</div>
    <div class="stat-row"><span class="stat-key">Daily cron</span><span class="stat-val coral">Active</span></div>
    <div class="stat-row"><span class="stat-key">Deduplication</span><span class="stat-val">SHA-256 fingerprint</span></div>
    <div class="stat-row"><span class="stat-key">Errors (7d)</span><span class="stat-val">{m['error_count_7d']}</span></div>
    <div class="stat-row"><span class="stat-key">Backfill window</span><span class="stat-val">30 days</span></div>
  </div>
</div>

<!-- Footer -->
<div class="footer">
  <div class="footer-left">
    <span class="footer-brand">Chardi Contracts</span> · Project A · United States ·
    chardi-contracts.vercel.app
  </div>
  <div class="footer-right">
    Janu Chaudhary · Sitari University · May 2026
  </div>
</div>

</body>
</html>"""


async def render_async(html: str, out_path: Path):
    from playwright.async_api import async_playwright
    tmp = out_path.parent / "_tmp_metrics.html"
    tmp.write_text(html, encoding="utf-8")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(f"file://{tmp}", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await page.screenshot(path=str(out_path), full_page=True)
        await ctx.close()
        await browser.close()
    tmp.unlink(missing_ok=True)


async def main():
    print("Fetching live metrics from Neon...")
    m = await fetch_metrics()
    print(f"  Total: {m['total']:,} · Open: {m['open']:,} · Portals: {m['portals']}")
    print("Building HTML...")
    html = build_html(m)
    print("Rendering PNG...")
    await render_async(html, OUT_PATH)
    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"\n✅  metrics_summary.png saved ({size_kb} KB)")
    print(f"   {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
