# Portal Coverage

## Summary (May 24, 2026)

| Portal | Label | Region | Records | Open | Method | Status |
|---|---|---|---|---|---|---|
| api.sam.gov | Federal (SAM.gov) | Federal | 6,186 | 6,186 | REST API v2 | ✅ Production |
| data.oregon.gov | Oregon (OregonBuys) | State (OR) | 109,119 | 0 | Socrata API | ✅ Done |
| datacatalog.cookcountyil.gov | Cook County IL | County (IL) | 5,236 | 2,300 | Socrata API | ✅ Done |
| data.montgomerycountymd.gov | Montgomery County MD | County (MD) | 2,394 | 2,394 | Socrata API | ✅ Done |
| data.houstontx.gov | Houston TX | City (TX) | 2,310 | 11 | CKAN + XLSX | ✅ Done |
| data.cityofnewyork.us | NYC (Open Data) | City (NY) | 1,018 | 0 | Socrata API | ✅ Done |
| nyscr.ny.gov | New York (NYSCR) | State (NY) | 999 | 953 | Async HTTP | ✅ Done |
| data.cityofchicago.org | Chicago (Data Portal) | City (IL) | 659 | 654 | Socrata API | ✅ Done |
| caleprocure.ca.gov | California | State (CA) | 467 | 467 | Playwright + Excel | ✅ Done |
| eva.virginia.gov | Virginia (eVA) | State (VA) | 385 | 383 | Async HTTP | ✅ Done* |
| txsmartbuy.gov | Texas | State (TX) | 298 | 298 | Playwright + CSV | ✅ Done |
| doas.ga.gov | Georgia (TGM) | State (GA) | 201 | 201 | Playwright | ✅ Done |
| vita.virginia.gov | Virginia (VITA) | State (VA) | 190 | 190 | Async HTTP | ✅ Done |
| bidbuy.illinois.gov | Illinois (BidBuy) | State (IL) | 186 | 180 | Playwright | ✅ Done |
| dms.myflorida.com | Florida (DMS) | State (FL) | 146 | 76 | Async HTTP | ✅ Done |
| **Total** | | | **129,794** | **14,293** | | |

*eVA: portal returns 403 to CI/cloud IPs. Graceful skip with fast-fail probe. VITA still runs.

---

## Federal — SAM.gov

- **API:** Opportunities Public API v2 (`/prod/opportunities/v2/search`)
- **Auth:** API key via `SAM_GOV_API_KEY` env var
- **Worker:** `backend/workers/samgov/`
  - `fetcher.py` — sequential pagination, exponential backoff + jitter, `QuotaExhaustedError`
  - `mapper.py` — `map_notice_to_tuple()`, `sanitize_date()`
  - `main.py` — per-day window loop, `PARTIAL_SUCCESS` on quota hit
  - `backfill_historical.py` — one-shot backfill with resume support
- **Rate limit:** Daily quota. Resets 00:00 UTC. Worker detects `nextAccessTime` in 429 and stops cleanly.
- **Concurrency:** Sequential (changed from concurrent to maximize quota usage)
- **Retries:** 6 attempts, exponential backoff outside semaphore

### Field mapping

| DB Field | SAM.gov field | Coverage |
|---|---|---|
| `source_record_id` | `noticeId` | 100% |
| `solicitation_number` | `solicitationNumber` | ~60% |
| `title` | `title` | 100% |
| `notice_type` | `type` | 100% |
| `posted_date` | `postedDate` | 100% |
| `deadline` | `responseDeadLine` | ~80% |
| `state_region` | `placeOfPerformance.state.code` | ~70% |
| `naics_code` | `naicsCode` | ~75% |
| `status` | `active == "Yes"` → OPEN | 100% |
| `buyer_name` | `fullParentPathName` (first segment) | 100% |
| `source_url` | `uiLink` or constructed | 100% |
| `value_numeric` | Not in search API | 0% |

---

## City — NYC (Open Data / Socrata)

- **Portal:** data.cityofnewyork.us
- **Worker:** `backend/workers/nyc_contract_awards/`
- **Method:** Socrata API (`/resource/...`)
- **Records:** 1,018
- **State code:** `NY`

---

## State — New York (NYSCR)

- **Portal:** nyscr.ny.gov
- **Worker:** `backend/workers/newyork/`
- **Method:** Async HTTP scraper
- **Records:** 999
- **State code:** `NY`

---

## City — Chicago (Data Portal / Socrata)

- **Portal:** data.cityofchicago.org
- **Worker:** `backend/workers/chicago/`
- **Method:** Socrata API
- **Records:** 659
- **State code:** `IL`

---

## State — California (Cal eProcure)

- **Portal:** caleprocure.ca.gov
- **Worker:** `backend/workers/california/`
  - `scraper.py` — Playwright headless, advanced search, Excel download intercept
  - `mapper.py` — Pandas DataFrame → upsert tuples
- **Method:** Playwright + Excel intercept
- **Records:** 467
- **State code:** `CA`

---

## State — Virginia (eVA)

- **Portal:** mvendor.cgieva.com (eVA)
- **Worker:** `backend/workers/virginia/eva_scraper.py` + `eva_mapper.py`
- **Method:** Playwright + Solr API (browser session required)
- **Records:** 385
- **State code:** `VA`
- **Limitation:** Portal returns 403 to GitHub Actions IPs. Fast-fail HTTP probe added. VITA runs regardless.

---

## State — Texas (TxSmartBuy)

- **Portal:** txsmartbuy.gov
- **Worker:** `backend/workers/texas/`
- **Method:** Playwright + CSV export intercept
- **Records:** 298
- **State code:** `TX`

---

## State — Georgia (Team Georgia Marketplace)

- **Portal:** doas.ga.gov
- **Worker:** `backend/workers/georgia/`
- **Method:** Playwright
- **Records:** 201
- **State code:** `GA`

---

## State — Virginia (VITA)

- **Portal:** vita.virginia.gov
- **Worker:** `backend/workers/virginia/vita_scraper.py` + `vita_mapper.py`
- **Method:** Async HTTP
- **Records:** 190
- **State code:** `VA`

---

## State — Illinois (BidBuy)

- **Portal:** bidbuy.illinois.gov
- **Worker:** `backend/workers/illinois/`
- **Method:** Playwright
- **Records:** 186
- **State code:** `IL`

---

## State — Florida (DMS)

- **Portal:** dms.myflorida.com
- **Worker:** `backend/workers/florida/`
- **Method:** Async HTTP
- **Records:** 146
- **State code:** `FL`
- **Note:** Primarily historical/framework contracts. "- EXPIRED" suffix stripped from titles.

---

## Portals documented but not scraped

| Portal | Reason |
|---|---|
| Pennsylvania (emarketplace.state.pa.us) | Requires vendor registration |
| Ohio (procure.ohio.gov) | Requires vendor registration |
| North Carolina (ips.nc.gov) | Requires vendor registration |

Per brief ground rules: "Don't bypass logins, paywalls, or auth walls. Document them as limitations."

---

## State — Oregon (OregonBuys)

- **Portal:** data.oregon.gov
- **Worker:** `backend/workers/oregon/`
- **Method:** Socrata API (`/resource/qyug-f2km.json`)
- **Records:** 109,119 (all AWARDED status)
- **State code:** `OR`
- **Purpose:** Award history corpus for "Who has won similar?" enrichment feature
- **Industries:** Supplies, Trade Services, Personal Services, ORS 190, A and E, Public Improvement, Ordinary Construction

---

## County — Cook County IL

- **Portal:** datacatalog.cookcountyil.gov
- **Worker:** `backend/workers/cook_county/`
- **Method:** Socrata API (`/resource/qh8j-6k63.json`)
- **Records:** 5,236 (2,300 OPEN, 2,936 CLOSED)
- **State code:** `IL`
- **Note:** Full history — CLOSED records serve as award history corpus for IL county contracts

---

## City — Houston TX

- **Portal:** data.houstontx.gov
- **Worker:** `backend/workers/houston/`
- **Method:** CKAN package_show API → XLSX download → pandas read
- **Records:** 2,310 (11 OPEN, 2,299 CLOSED)
- **State code:** `TX`
- **Note:** Downloads full XLSX via CKAN API, falls back to hardcoded direct URL

---

## County — Montgomery County MD

- **Portal:** data.montgomerycountymd.gov
- **Worker:** `backend/workers/montgomery_county/`
- **Method:** Socrata API
- **Records:** 2,394 (all OPEN)
- **State code:** `MD`
