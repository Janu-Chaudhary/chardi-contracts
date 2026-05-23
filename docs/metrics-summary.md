# Metrics Summary

**Last updated:** May 23, 2026  
**Live database:** Neon PostgreSQL  
**Live URL:** https://chardi-contracts.vercel.app

---

## Data volume

| Metric | Value |
|---|---|
| **Total opportunities** | **10,735** |
| Open | 9,588 (89.3%) |
| Closed | 1,147 (10.7%) |
| Federal (SAM.gov) | 6,186 |
| State + City portals | 4,549 |
| Active portals | 11 |
| US states covered | 53 (incl. DC, PR, territories via SAM.gov) |
| Last scraped | May 23, 2026 |

---

## Coverage by portal

| Portal | Label | Records | Open | Closed | Last Scraped | Method |
|---|---|---|---|---|---|---|
| api.sam.gov | Federal (SAM.gov) | 6,186 | 6,186 | 0 | May 23, 2026 | REST API v2 |
| data.cityofnewyork.us | NYC (Open Data) | 1,018 | 0 | 1,018 | May 23, 2026 | Socrata API |
| nyscr.ny.gov | New York (NYSCR) | 999 | 953 | 46 | May 23, 2026 | Async HTTP |
| data.cityofchicago.org | Chicago (Data Portal) | 659 | 654 | 5 | May 23, 2026 | Socrata API |
| caleprocure.ca.gov | California | 467 | 467 | 0 | May 23, 2026 | Playwright + Excel |
| eva.virginia.gov | Virginia (eVA) | 385 | 383 | 2 | May 23, 2026 | Async HTTP |
| txsmartbuy.gov | Texas | 298 | 298 | 0 | May 23, 2026 | Playwright + CSV |
| doas.ga.gov | Georgia (TGM) | 201 | 201 | 0 | May 23, 2026 | Playwright |
| vita.virginia.gov | Virginia (VITA) | 190 | 190 | 0 | May 23, 2026 | Async HTTP |
| bidbuy.illinois.gov | Illinois (BidBuy) | 186 | 180 | 6 | May 23, 2026 | Playwright |
| dms.myflorida.com | Florida (DMS) | 146 | 76 | 70 | May 23, 2026 | Async HTTP |
| **Total** | | **10,735** | **9,588** | **1,147** | | |

---

## Coverage by state (top 10)

| State | Records | Source |
|---|---|---|
| Federal | 6,186 | SAM.gov |
| New York | 2,017 | NYSCR + NYC Open Data |
| Illinois | 845 | Chicago + BidBuy |
| California | 467 | Cal eProcure |
| Virginia | 575 | eVA + VITA |
| Texas | 298 | TxSmartBuy |
| Georgia | 201 | Team Georgia Marketplace |
| Florida | 146 | DMS |

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

## Upcoming deadlines (live)

| Month | Contracts due |
|---|---|
| May 2026 | ~1,052 |
| Jun 2026 | ~1,372 |
| Jul 2026 | ~134 |
| Aug 2026 | ~73 |
| Sep 2026 | ~43 |

---

## SAM.gov backfill status

Historical backfill (Apr 14 → May 14, 2026) in progress using dedicated API key.
- Days completed: 10 / 30 (Apr 14–23)
- Records added: 4,307
- Quota resets: daily at 00:00 UTC
- Re-run command: `env $(cat .env | grep -v '^#' | xargs) .venv/bin/python -m backend.workers.samgov.backfill_historical`
