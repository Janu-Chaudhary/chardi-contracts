# Metrics Summary

**Last updated:** May 24, 2026  
**Live database:** Neon PostgreSQL  
**Live URL:** https://chardi-contracts.vercel.app

---

## Data volume

| Metric | Value |
|---|---|
| **Total opportunities** | **129,794** |
| Open | 14,293 (11.0%) |
| Closed | 6,382 (4.9%) |
| Awarded | 109,119 (84.1%) |
| Federal (SAM.gov) | 6,186 |
| State + City + County portals | 123,608 |
| Active portals | 15 |
| US states covered | 107 (incl. territories via SAM.gov) |
| Award history vendors | 18,212 unique vendor-industry combinations |
| Last scraped | May 24, 2026 |

---

## Coverage by portal

| Portal | Label | Records | Open | Closed | Awarded | Last Scraped | Method |
|---|---|---|---|---|---|---|---|
| data.oregon.gov | Oregon (OregonBuys) | 109,119 | 0 | 0 | 109,119 | May 24, 2026 | Socrata API |
| SAM.gov | Federal (SAM.gov) | 6,186 | 6,186 | 0 | 0 | May 24, 2026 | REST API v2 |
| datacatalog.cookcountyil.gov | Cook County IL | 5,236 | 2,300 | 2,936 | 0 | May 24, 2026 | Socrata API |
| data.montgomerycountymd.gov | Montgomery County MD | 2,394 | 2,394 | 0 | 0 | May 24, 2026 | Socrata API |
| data.houstontx.gov | Houston TX | 2,310 | 11 | 2,299 | 0 | May 24, 2026 | CKAN + XLSX |
| data.cityofnewyork.us | NYC (Open Data) | 1,018 | 0 | 1,018 | 0 | May 24, 2026 | Socrata API |
| nyscr.ny.gov | New York (NYSCR) | 999 | 953 | 46 | 0 | May 24, 2026 | Async HTTP |
| data.cityofchicago.org | Chicago (Data Portal) | 659 | 654 | 5 | 0 | May 24, 2026 | Socrata API |
| caleprocure.ca.gov | California | 467 | 467 | 0 | 0 | May 24, 2026 | Playwright + Excel |
| eva.virginia.gov | Virginia (eVA) | 385 | 383 | 2 | 0 | May 24, 2026 | Async HTTP |
| txsmartbuy.gov | Texas | 298 | 298 | 0 | 0 | May 24, 2026 | Playwright + CSV |
| doas.ga.gov | Georgia (TGM) | 201 | 201 | 0 | 0 | May 24, 2026 | Playwright |
| vita.virginia.gov | Virginia (VITA) | 190 | 190 | 0 | 0 | May 24, 2026 | Async HTTP |
| bidbuy.illinois.gov | Illinois (BidBuy) | 186 | 180 | 6 | 0 | May 24, 2026 | Playwright |
| dms.myflorida.com | Florida (DMS) | 146 | 76 | 70 | 0 | May 24, 2026 | Async HTTP |
| **Total** | | **129,794** | **14,293** | **6,382** | **109,119** | | |

---

## Coverage by region

| Region | Records | Portals |
|---|---|---|
| Federal | 6,186 | SAM.gov |
| State — Oregon | 109,119 | OregonBuys |
| County — Illinois | 5,236 | Cook County |
| County — Maryland | 2,394 | Montgomery County |
| City — Texas | 2,310 | Houston |
| City — New York | 1,018 | NYC Open Data |
| State — New York | 999 | NYSCR |
| City — Illinois | 659 | Chicago |
| State — California | 467 | Cal eProcure |
| State — Virginia | 575 | eVA + VITA |
| State — Texas | 298 | TxSmartBuy |
| State — Georgia | 201 | Team Georgia Marketplace |
| State — Illinois | 186 | BidBuy |
| State — Florida | 146 | DMS |

---

## Award enrichment corpus

| Source Portal | Status | Vendor-Industry Combos | Total Wins |
|---|---|---|---|
| data.oregon.gov | AWARDED | 14,962 | 109,119 |
| datacatalog.cookcountyil.gov | CLOSED | 2,417 | 2,936 |
| data.houstontx.gov | CLOSED | 1 | 2,299 |
| data.cityofnewyork.us | CLOSED | 755 | 1,018 |
| dms.myflorida.com | CLOSED | 64 | 70 |
| others | CLOSED | 13 | 19 |
| **Total** | | **18,212** | **115,461** |

Top vendors by win count (Oregon corpus):
- CDWG — 4,398 wins (Supplies)
- STAPLES CONTRACT & COMMERCIAL LLC — 1,512 wins (Supplies)
- OREGON CORRECTIONS ENTERPRISES — 1,445 wins (Supplies)
- W. W. GRAINGER — 1,432 wins (Supplies)
- RICOH USA — 982 wins (Supplies) + 741 wins (Trade Services)

---

## Pipeline health

| Metric | Value |
|---|---|
| Deduplication | 0 duplicates (SHA-256 deterministic IDs) |
| Upsert strategy | `ON CONFLICT (id) DO UPDATE` |
| Dead-letter logging | `scrape_errors` table |
| Partial success handling | `PARTIAL_SUCCESS` status |
| Retries | 5–6 attempts, exponential backoff + jitter |
| Daily cron | GitHub Actions — 06:00 UTC |
| SAM.gov concurrency | Sequential (quota-safe) |
| Graceful degradation | eVA 403 → fast-fail probe, VITA still runs |
| Award enrichment refresh | Auto after each worker upsert |

---

## Data quality

| Field | Coverage | Notes |
|---|---|---|
| `title` | 100% | EXPIRED suffix stripped from Florida titles |
| `status` | 100% | OPEN / CLOSED / AWARDED / CANCELLED |
| `source_portal` | 100% | |
| `source_url` | 100% | Direct link to original notice |
| `buyer_name` | ~95% | |
| `posted_date` | ~95% | |
| `deadline` | ~80% | SAM.gov ~80%, state portals ~90% |
| `state_region` | ~70% | SAM.gov place-of-performance ~70% |
| `industry` | ~65% | NAICS (SAM.gov) or NIGP (state) |
| `naics_code` | ~45% | SAM.gov only |
| `value_numeric` | ~0% | Not published by most portals |

---

## Frontend performance

| Metric | Value |
|---|---|
| API response (list) | ~30ms (Edge runtime + Neon serverless) |
| API response (winners) | <10ms (pre-aggregated award_winners table) |
| Filter persistence | URL-based — back button restores state |
| Mobile layout | Single-column stack, no overflow |
| Chart tooltips | Bar-anchored, responsive on all screen sizes |
| Scrollbar | Custom 4px warm-toned (webkit + Firefox) |
