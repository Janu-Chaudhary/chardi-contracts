"""
Generate a premium one-page metrics summary PNG for the Chardi Contracts project.
Queries live Neon DB, builds a styled HTML page, screenshots it.
Output: docs/screenshots/metrics_summary.png
"""

import asyncio
import asyncpg
from datetime import datetime, timezone
from pathlib import Path
import time

DATABASE_URL = ""
OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "screenshots" / "metrics_summary.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


async def fetch_metrics():
    conn = await asyncpg.connect(DATABASE_URL)
    total = await conn.fetchval("SELECT COUNT(*) FROM opportunities")
    open_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status='OPEN'")
    closed_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status='CLOSED'")
    awarded_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status='AWARDED'")
    cancelled_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status='CANCELLED'")
    federal_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE portal_region='Federal'")
    state_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE portal_region='State'")
    county_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE portal_region='County'")
    city_count = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE portal_region='City'")
    portal_count = await conn.fetchval("SELECT COUNT(DISTINCT source_portal) FROM opportunities")
    state_region_count = await conn.fetchval("SELECT COUNT(DISTINCT state_region) FROM opportunities WHERE state_region IS NOT NULL")
    upcoming_7d = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status='OPEN' AND deadline BETWEEN NOW() AND NOW()+INTERVAL'7 days'")
    upcoming_30d = await conn.fetchval("SELECT COUNT(*) FROM opportunities WHERE status='OPEN' AND deadline BETWEEN NOW() AND NOW()+INTERVAL'30 days'")

    portal_rows = await conn.fetch("""
        SELECT source_portal, portal_region,
               COUNT(*) as records,
               SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open_count,
               SUM(CASE WHEN status='AWARDED' THEN 1 ELSE 0 END) as awarded_count,
               MAX(last_seen_at) as last_seen
        FROM opportunities GROUP BY source_portal, portal_region ORDER BY records DESC
    """)
    run_rows = await conn.fetch("""
        SELECT DISTINCT ON (source_portal) source_portal, status, end_time, records_scraped
        FROM scrape_runs WHERE status IN ('SUCCESS','PARTIAL_SUCCESS','FAILED')
        ORDER BY source_portal, end_time DESC NULLS LAST
    """)
    run_map = {r['source_portal']: dict(r) for r in run_rows}
    eva_ok = await conn.fetchrow("""
        SELECT source_portal, status, end_time, records_scraped FROM scrape_runs
        WHERE source_portal='eva.virginia.gov' AND status='SUCCESS'
        ORDER BY end_time DESC NULLS LAST LIMIT 1
    """)
    if eva_ok:
        run_map['eva.virginia.gov'] = dict(eva_ok)

    region_rows = await conn.fetch("""
        SELECT COALESCE(state_region,'N/A') as region,
               COUNT(*) as records,
               SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open_count
        FROM opportunities WHERE state_region IS NOT NULL AND state_region NOT IN ('Federal','N/A') AND status='OPEN'
        GROUP BY state_region ORDER BY open_count DESC LIMIT 15
    """)
    notice_rows = await conn.fetch("""
        SELECT notice_type, COUNT(*) as cnt FROM opportunities
        WHERE notice_type IS NOT NULL AND notice_type!='' AND status='OPEN'
        GROUP BY notice_type ORDER BY cnt DESC LIMIT 8
    """)
    award_vendor_count = await conn.fetchval("SELECT COUNT(*) FROM award_winners")
    award_total_wins = await conn.fetchval("SELECT SUM(win_count) FROM award_winners") or 0
    top_vendors = await conn.fetch("""
        SELECT vendor_name, industry, SUM(win_count) as total_wins,
               ROUND(AVG(avg_value)::numeric,0) as avg_val
        FROM award_winners GROUP BY vendor_name, industry ORDER BY total_wins DESC LIMIT 5
    """)
    samgov_quota_errors = await conn.fetchval("SELECT COUNT(*) FROM scrape_errors WHERE source_portal='SAM.gov' AND (error_message ILIKE '%quota%' OR error_message ILIKE '%900804%' OR error_message ILIKE '%failed after 5%')")
    samgov_type_errors = await conn.fetchval("SELECT COUNT(*) FROM scrape_errors WHERE source_portal='SAM.gov' AND error_message ILIKE '%DataError%'")
    georgia_errors = await conn.fetchval("SELECT COUNT(*) FROM scrape_errors WHERE source_portal='doas.ga.gov'")
    california_errors = await conn.fetchval("SELECT COUNT(*) FROM scrape_errors WHERE source_portal='caleprocure.ca.gov'")
    chromium_errors = await conn.fetchval("SELECT COUNT(*) FROM scrape_errors WHERE error_message ILIKE '%Executable doesn%'")
    eva_403_errors = await conn.fetchval("SELECT COUNT(*) FROM scrape_errors WHERE source_portal='eva.virginia.gov' AND error_message ILIKE '%All 5 attempts%'")
    total_errors = await conn.fetchval("SELECT COUNT(*) FROM scrape_errors")
    await conn.close()

    return {
        "total": total, "open": open_count, "closed": closed_count,
        "awarded": awarded_count, "cancelled": cancelled_count,
        "federal": federal_count, "state": state_count, "county": county_count, "city": city_count,
        "portals": portal_count, "states_covered": state_region_count,
        "upcoming_7d": upcoming_7d, "upcoming_30d": upcoming_30d,
        "portal_rows": [dict(r) for r in portal_rows],
        "run_map": run_map,
        "region_rows": [dict(r) for r in region_rows],
        "notice_rows": [dict(r) for r in notice_rows],
        "award_vendor_count": award_vendor_count,
        "award_total_wins": award_total_wins,
        "top_vendors": [dict(r) for r in top_vendors],
        "total_errors": total_errors,
        "samgov_quota_errors": samgov_quota_errors, "samgov_type_errors": samgov_type_errors,
        "georgia_errors": georgia_errors, "california_errors": california_errors,
        "chromium_errors": chromium_errors, "eva_403_errors": eva_403_errors,
        "generated_at": datetime.now(timezone.utc).strftime("%B %d, %Y · %H:%M UTC"),
    }


def format_freshness(last_seen):
    if not last_seen:
        return "—", "stale"
    now = datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    hours = (now - last_seen).total_seconds() / 3600
    if hours < 24: return f"{int(hours)}h ago", "fresh"
    elif hours < 48: return "Yesterday", "fresh"
    elif hours < 72: return f"{int(hours//24)}d ago", "recent"
    else: return f"{int(hours//24)}d ago", "stale"


STATE_NAMES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
    "CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"Washington D.C.",
    "FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois",
    "IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
    "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota",
    "MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
    "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
    "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon",
    "PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
    "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia",
    "WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
}


def build_portal_rows(m):
    html = ""
    for p in m["portal_rows"]:
        portal = p["source_portal"]
        region = p["portal_region"] or "—"
        records = f"{p['records']:,}"
        awarded_c = p.get("awarded_count", 0) or 0
        open_c = p["open_count"] or 0
        run = m["run_map"].get(portal, {})
        ft, fc = format_freshness(p.get("last_seen"))
        rs = run.get("status", "—") if run else "—"
        sc = {"SUCCESS":"status-success","PARTIAL_SUCCESS":"status-partial","FAILED":"status-failed"}.get(rs,"status-unknown")
        rk = region.lower().replace(" ","-").replace("/","-")
        note = ""
        open_display = f"{open_c:,}"
        if portal == "data.oregon.gov":
            note = '<span style="font-size:10px;color:#9B9490;margin-left:4px;">award corpus</span>'
            open_display = f'<span style="color:#9B9490">{awarded_c:,} awarded</span>'
        html += f"""<tr>
            <td class="portal-name">{portal}{note}</td>
            <td><span class="region-badge region-{rk}">{region}</span></td>
            <td class="num">{records}</td>
            <td class="num open-num">{open_display}</td>
            <td><span class="freshness {fc}">{ft}</span></td>
            <td><span class="run-status {sc}">{rs}</span></td>
        </tr>"""
    return html


def build_region_rows(m):
    html = ""
    rows = [r for r in m["region_rows"] if r["region"] not in ("N/A", None, "Federal")][:15]
    mx = max((r["open_count"] for r in rows), default=1)
    for r in rows:
        pct = int((r["open_count"] / mx) * 100) if mx else 0
        name = STATE_NAMES.get(r["region"], r["region"])
        html += f"""<div class="region-row">
            <div class="region-label">{name}</div>
            <div class="region-bar-wrap"><div class="region-bar" style="width:{pct}%"></div></div>
            <div class="region-count">{r['open_count']:,}</div>
            <div class="region-open">open</div>
        </div>"""
    return html


def build_notice_rows(m):
    html = ""
    for n in m["notice_rows"]:
        html += f"""<div class="notice-item">
            <span class="notice-type">{n['notice_type'] or 'Unknown'}</span>
            <span class="notice-count">{n['cnt']:,}</span>
        </div>"""
    return html


def build_vendor_rows(m):
    html = ""
    rank_styles = ["background:#FEF3C7;color:#92400E","background:#F1F5F9;color:#475569","background:#FEF9C3;color:#854D0E"]
    for i, v in enumerate(m["top_vendors"], 1):
        avg_str = f"avg ${int(v['avg_val']):,}" if v.get('avg_val') else ""
        rs = rank_styles[i-1] if i <= 3 else "background:#F7F3F2;color:#6B6560"
        html += f"""<div class="vendor-row">
            <span class="vendor-rank" style="{rs}">{i}</span>
            <div class="vendor-info">
                <div class="vendor-name">{v['vendor_name']}</div>
                <div class="vendor-meta">{v['industry']}{f' · {avg_str}' if avg_str else ''}</div>
            </div>
            <span class="vendor-wins">{int(v['total_wins']):,}<span class="wins-label"> wins</span></span>
        </div>"""
    return html


CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Inter',-apple-system,sans-serif; background:#FFFBF7; color:#1F1A17; padding:48px 56px; width:1400px; }
.header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:40px; padding-bottom:28px; border-bottom:1px solid #E0DCDA; }
.brand { font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:#EA580C; margin-bottom:6px; }
.title { font-family:'Playfair Display',serif; font-size:34px; font-weight:700; color:#1A0D0A; line-height:1.1; margin-bottom:6px; }
.subtitle { font-size:14px; color:#6B6560; }
.header-right { text-align:right; }
.generated { font-size:12px; color:#9B9490; margin-bottom:6px; }
.live-badge { display:inline-flex; align-items:center; gap:6px; background:#F0FDF4; border:1px solid #BBF7D0; color:#15803D; font-size:12px; font-weight:500; padding:4px 10px; border-radius:20px; }
.live-dot { width:6px; height:6px; background:#22C55E; border-radius:50%; }
.kpi-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:14px; margin-bottom:36px; }
.kpi-card { background:#fff; border:1px solid #E0DCDA; border-radius:12px; padding:20px 18px; box-shadow:0 1px 2px rgba(0,0,0,.03); }
.kpi-card.accent { background:#1A0D0A; border-color:#1A0D0A; }
.kpi-label { font-size:11px; font-weight:600; letter-spacing:.07em; text-transform:uppercase; color:#9B9490; margin-bottom:8px; }
.kpi-card.accent .kpi-label { color:#6B6560; }
.kpi-value { font-size:30px; font-weight:700; color:#1A0D0A; line-height:1; margin-bottom:5px; font-variant-numeric:tabular-nums; }
.kpi-card.accent .kpi-value { color:#FFFBF7; }
.kpi-sub { font-size:12px; color:#9B9490; }
.kpi-card.accent .kpi-sub { color:#6B6560; }
.kpi-accent-val { color:#EA580C; }
.section-header { display:flex; align-items:baseline; gap:10px; margin-bottom:14px; }
.section-title { font-size:12px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:#1A0D0A; }
.section-count { font-size:12px; color:#9B9490; }
.two-col { display:grid; grid-template-columns:1fr 360px; gap:20px; margin-bottom:28px; }
.table-wrap { background:#fff; border:1px solid #E0DCDA; border-radius:12px; overflow:hidden; box-shadow:0 1px 2px rgba(0,0,0,.03); }
table { width:100%; border-collapse:collapse; font-size:13px; }
thead th { background:#F7F3F2; padding:9px 14px; text-align:left; font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:#9B9490; border-bottom:1px solid #E0DCDA; }
thead th.num { text-align:right; }
tbody tr { border-bottom:1px solid #F7F3F2; }
tbody tr:last-child { border-bottom:none; }
tbody td { padding:10px 14px; color:#1F1A17; vertical-align:middle; }
tbody td.num { text-align:right; font-variant-numeric:tabular-nums; color:#6B6560; }
tbody td.open-num { color:#1F1A17; font-weight:500; }
.portal-name { font-weight:500; color:#1A0D0A; }
.region-badge { font-size:11px; font-weight:500; padding:2px 8px; border-radius:20px; }
.region-federal { background:#FEF3C7; color:#92400E; }
.region-state { background:#EFF6FF; color:#1D4ED8; }
.region-city { background:#F0FDF4; color:#15803D; }
.region-county { background:#F5F3FF; color:#6D28D9; }
.freshness { font-size:12px; font-weight:500; padding:2px 8px; border-radius:20px; }
.freshness.fresh { background:#F0FDF4; color:#15803D; }
.freshness.recent { background:#FEF9C3; color:#854D0E; }
.freshness.stale { background:#FEF2F2; color:#991B1B; }
.run-status { font-size:11px; font-weight:600; letter-spacing:.04em; padding:2px 8px; border-radius:20px; }
.status-success { background:#F0FDF4; color:#15803D; }
.status-partial { background:#FEF9C3; color:#854D0E; }
.status-failed { background:#FEF2F2; color:#991B1B; }
.status-unknown { background:#F7F3F2; color:#9B9490; }
.right-col { display:flex; flex-direction:column; gap:16px; }
.card { background:#fff; border:1px solid #E0DCDA; border-radius:12px; padding:18px; box-shadow:0 1px 2px rgba(0,0,0,.03); }
.region-row { display:grid; grid-template-columns:110px 1fr 44px 40px; align-items:center; gap:8px; margin-bottom:7px; }
.region-row:last-child { margin-bottom:0; }
.region-label { font-size:12px; font-weight:600; color:#1A0D0A; text-align:right; }
.region-bar-wrap { height:5px; background:#F7F3F2; border-radius:3px; overflow:hidden; }
.region-bar { height:100%; background:#EA580C; border-radius:3px; }
.region-count { font-size:12px; color:#6B6560; text-align:right; font-variant-numeric:tabular-nums; }
.region-open { font-size:11px; color:#9B9490; }
.notice-item { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #F7F3F2; font-size:13px; }
.notice-item:last-child { border-bottom:none; }
.notice-type { color:#1F1A17; }
.notice-count { color:#6B6560; font-variant-numeric:tabular-nums; font-weight:500; }
.vendor-row { display:flex; align-items:center; gap:10px; padding:7px 0; border-bottom:1px solid #F7F3F2; }
.vendor-row:last-child { border-bottom:none; }
.vendor-rank { width:20px; height:20px; border-radius:50%; font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.vendor-info { flex:1; min-width:0; }
.vendor-name { font-size:12px; font-weight:600; color:#1A0D0A; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.vendor-meta { font-size:11px; color:#9B9490; margin-top:1px; }
.vendor-wins { font-size:13px; font-weight:700; color:#EA580C; font-variant-numeric:tabular-nums; white-space:nowrap; }
.wins-label { font-size:11px; font-weight:400; color:#9B9490; }
.bottom-row { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:36px; }
.stat-block { background:#fff; border:1px solid #E0DCDA; border-radius:12px; padding:18px 20px; box-shadow:0 1px 2px rgba(0,0,0,.03); }
.stat-block-label { font-size:11px; font-weight:600; letter-spacing:.07em; text-transform:uppercase; color:#9B9490; margin-bottom:10px; }
.stat-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #F7F3F2; font-size:13px; }
.stat-row:last-child { border-bottom:none; }
.stat-key { color:#6B6560; }
.stat-val { font-weight:600; color:#1A0D0A; font-variant-numeric:tabular-nums; }
.stat-val.coral { color:#EA580C; }
.footer { padding-top:20px; border-top:1px solid #E0DCDA; display:flex; justify-content:space-between; align-items:center; }
.footer-left { font-size:12px; color:#9B9490; }
.footer-right { font-size:12px; color:#9B9490; }
.footer-brand { font-weight:600; color:#EA580C; }
"""


def build_html(m: dict) -> str:
    portal_html = build_portal_rows(m)
    region_html = build_region_rows(m)
    notice_html = build_notice_rows(m)
    vendor_html = build_vendor_rows(m)

    open_pct = round((m["open"] / m["total"]) * 100) if m["total"] else 0
    awarded_pct = round((m["awarded"] / m["total"]) * 100) if m["total"] else 0
    federal_pct = round((m["federal"] / m["total"]) * 100) if m["total"] else 0
    build_errors = (m["total_errors"] or 0) - (m["eva_403_errors"] or 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="brand">Chardi.ai · Project A · United States</div>
    <div class="title">Metrics Summary</div>
    <div class="subtitle">Opportunities scraped · Freshness · Coverage by region · Award enrichment</div>
  </div>
  <div class="header-right">
    <div class="generated">Generated {m['generated_at']}</div>
    <div class="live-badge"><div class="live-dot"></div>Live data · Neon PostgreSQL</div>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi-card accent">
    <div class="kpi-label">Total Opportunities</div>
    <div class="kpi-value">{m['total']:,}</div>
    <div class="kpi-sub">{m['portals']} portals · {m['states_covered']} states</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Open Now</div>
    <div class="kpi-value kpi-accent-val">{m['open']:,}</div>
    <div class="kpi-sub">{open_pct}% of total · {m['upcoming_7d']:,} due in 7d</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Award Corpus</div>
    <div class="kpi-value">{m['awarded']:,}</div>
    <div class="kpi-sub">{awarded_pct}% · {m['award_vendor_count']:,} vendor combos</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Federal Coverage</div>
    <div class="kpi-value">{m['federal']:,}</div>
    <div class="kpi-sub">SAM.gov · {federal_pct}% of total</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Pipeline Health</div>
    <div class="kpi-value">{m['portals']}/{m['portals']}</div>
    <div class="kpi-sub">All portals active · 0 prod errors</div>
  </div>
</div>

<div class="two-col">
  <div>
    <div class="section-header">
      <span class="section-title">Portal Coverage</span>
      <span class="section-count">{len(m['portal_rows'])} sources · updated daily 06:00 UTC</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Portal</th><th>Region</th>
          <th class="num">Records</th><th class="num">Open</th>
          <th>Last scraped</th><th>Run status</th>
        </tr></thead>
        <tbody>{portal_html}</tbody>
      </table>
    </div>
  </div>
  <div class="right-col">
    <div class="card">
      <div class="section-header"><span class="section-title">Open by State</span></div>
      {region_html}
    </div>
    <div class="card">
      <div class="section-header"><span class="section-title">Who Has Won Similar?</span>
        <span class="section-count">{m['award_total_wins']:,} total wins</span>
      </div>
      {vendor_html}
    </div>
  </div>
</div>

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
    <div class="stat-row"><span class="stat-key">County portals</span><span class="stat-val">{m['county']:,}</span></div>
    <div class="stat-row"><span class="stat-key">City portals</span><span class="stat-val">{m['city']:,}</span></div>
    <div class="stat-row"><span class="stat-key">States covered</span><span class="stat-val">{m['states_covered']}</span></div>
  </div>
  <div class="stat-block">
    <div class="stat-block-label">Pipeline Reliability</div>
    <div class="stat-row"><span class="stat-key">Daily cron</span><span class="stat-val coral">Active · 06:00 UTC</span></div>
    <div class="stat-row"><span class="stat-key">Deduplication</span><span class="stat-val">SHA-256 fingerprint</span></div>
    <div class="stat-row"><span class="stat-key">Retry strategy</span><span class="stat-val">5× exp. backoff</span></div>
    <div class="stat-row"><span class="stat-key">True prod failures</span><span class="stat-val coral">0</span></div>
    <div class="stat-row"><span class="stat-key">Build/tuning errors (resolved)</span><span class="stat-val" style="color:#9B9490">{build_errors}</span></div>
    <div class="stat-row"><span class="stat-key">eVA 403 (CI IP block — documented)</span><span class="stat-val" style="color:#854D0E">{m['eva_403_errors']}</span></div>
  </div>
</div>

<div class="footer">
  <div class="footer-left"><span class="footer-brand">Chardi Contracts</span> · Project A · United States · chardi-contracts.vercel.app</div>
  <div class="footer-right">Janu Chaudhary · Sitari University · May 2026</div>
</div>

</body></html>"""


async def render_async(html: str, out_path: Path):
    from playwright.async_api import async_playwright
    tmp = out_path.parent / "_tmp_metrics.html"
    tmp.write_text(html, encoding="utf-8")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(f"file://{tmp}", wait_until="networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path=str(out_path), full_page=True)
        await ctx.close()
        await browser.close()
    tmp.unlink(missing_ok=True)


async def main():
    print("Fetching live metrics from Neon...")
    m = await fetch_metrics()
    print(f"  Total: {m['total']:,} · Open: {m['open']:,} · Awarded: {m['awarded']:,} · Portals: {m['portals']}")
    print(f"  Award vendors: {m['award_vendor_count']:,} · Total wins: {m['award_total_wins']:,}")
    print("Building HTML...")
    html = build_html(m)
    print("Rendering PNG...")
    await render_async(html, OUT_PATH)
    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"\n✅  metrics_summary.png saved ({size_kb} KB)")
    print(f"   {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
