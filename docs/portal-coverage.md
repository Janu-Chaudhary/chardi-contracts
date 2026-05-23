# Portal Coverage

## Summary (as of May 23, 2026)

| Portal | Label | Region | Records | Method | Status |
|---|---|---|---|---|---|
| api.sam.gov | `SAM.gov` | Federal | 1,879 | REST API v2 | ✅ Production-ready |
| nyscr.ny.gov | `nyscr.ny.gov` | State (NY) | 999 | Async HTTP scraper | ✅ Done |
| caleprocure.ca.gov | `caleprocure.ca.gov` | State (CA) | 456 | Playwright + Excel | ✅ Done |
| mvendor.cgieva.com | `eva.virginia.gov` | State (VA) | 385 | Async HTTP scraper | ✅ Done |
| txsmartbuy.gov | `txsmartbuy.gov` | State (TX) | 297 | Playwright + CSV | ✅ Done |
| vita.virginia.gov | `vita.virginia.gov` | State (VA) | 190 | Async HTTP scraper | ✅ Done |
| **Total** | | | **4,206** | | |

---

## Federal — SAM.gov

- **API:** Opportunities Public API v2 (`/prod/opportunities/v2/search`)
- **Auth:** API key via `SAM_GOV_API_KEY` env var
- **Worker:** `backend/workers/samgov/`
  - `fetcher.py` — async pagination, semaphore (3), exponential backoff + jitter
  - `mapper.py` — `map_notice_to_tuple()`, `sanitize_date()`
  - `main.py` — per-day window partitioning, `asyncio.gather`, scrape_runs observability
- **CLI:** `python -m backend.workers.samgov.main --days N`
- **Rate limit:** Daily quota. Resets at 00:00 UTC. Worker detects `nextAccessTime` in 429 response and raises fatal error.
- **Concurrency:** 3 simultaneous requests (reduced from 5 after rate-limit testing)
- **Retries:** 5 attempts, backoff outside semaphore

### Field mapping

| DB Field | SAM.gov field | Coverage |
|---|---|---|
| `source_record_id` | `noticeId` | ✅ 100% |
| `solicitation_number` | `solicitationNumber` | ~60% |
| `title` | `title` | ✅ 100% |
| `notice_type` | `type` | ✅ 100% |
| `posted_date` | `postedDate` | ✅ 100% |
| `deadline` | `responseDeadLine` | ~80% |
| `state_region` | `placeOfPerformance.state.code` | ~70% |
| `industry` | `naicsCode` | ~75% |
| `naics_code` | `naicsCode` | ~75% |
| `status` | `active == "Yes"` → OPEN | ✅ 100% |
| `buyer_name` | `fullParentPathName` (first segment) | ✅ 100% |
| `buyer_type` | `organizationType` | ✅ 100% |
| `source_url` | `uiLink` or constructed | ✅ 100% |
| `documents` | `resourceLinks[]` | ~40% |
| `value_numeric` | Not in search API | ❌ 0% |

---

## State — New York (NYSCR)

- **Portal:** nyscr.ny.gov
- **Worker:** `backend/workers/newyork/`
- **Method:** Async HTTP scraper
- **Records:** 999
- **State code:** `NY`

---

## State — California (Cal eProcure)

- **Portal:** caleprocure.ca.gov
- **Worker:** `backend/workers/california/`
  - `scraper.py` — Playwright headless, advanced search, Excel download intercept
  - `mapper.py` — Pandas DataFrame → upsert tuples
  - `main.py` — orchestration + scrape_runs
- **Method:** Playwright + Excel intercept
- **Records:** 456
- **State code:** `CA`
- **CLI:** `python -m backend.workers.california.main`

---

## State — Texas (TxSmartBuy)

- **Portal:** txsmartbuy.gov
- **Worker:** `backend/workers/texas/`
  - `scraper.py` — Playwright headless, CSV export intercept
  - `mapper.py` — Pandas DataFrame → upsert tuples
  - `main.py` — orchestration + scrape_runs
- **Method:** Playwright + CSV export
- **Records:** 297 (Term + TXMAS contracts)
- **State code:** `TX`
- **CLI:** `python -m backend.workers.texas.main`

### Field coverage

| DB Field | Coverage | Notes |
|---|---|---|
| `id` | ✅ 100% | SHA-256(portal + Contract ID) |
| `source_record_id` | ✅ 100% | Contract column |
| `solicitation_number` | 29% | FED column (TXMAS only) |
| `title` | ✅ 100% | Description column |
| `notice_type` | ✅ 100% | Term / TXMAS |
| `posted_date` | ✅ 100% | Start Date |
| `deadline` | ✅ 100% | End Date |
| `state_region` | ✅ 100% | Hardcoded `TX` |
| `industry` | ✅ 100% | First NIGP code |
| `status` | ✅ 100% | Derived from End Date vs today |
| `buyer_name` | ✅ 100% | Contract Group |
| `source_url` | ✅ 100% | Constructed from Contract ID |
| `naics_code` | ❌ 0% | NIGP ≠ NAICS, not in CSV |
| `value_numeric` | ❌ 0% | Not published in CSV |
| `documents` | ❌ 0% | Not in CSV |

---

## State — Virginia (eVA)

- **Portal:** mvendor.cgieva.com (eVA)
- **Worker:** `backend/workers/virginia/eva_scraper.py` + `eva_mapper.py`
- **Records:** 385
- **State code:** `VA`

---

## State — Virginia (VITA)

- **Portal:** vita.virginia.gov
- **Worker:** `backend/workers/virginia/vita_scraper.py` + `vita_mapper.py`
- **Records:** 190
- **State code:** `VA`

---

## Portals documented but not yet scraped

| Portal | Reason |
|---|---|
| Florida (myfloridamarketplace.com) | Requires vendor registration |
| Illinois (bidbuy.illinois.gov) | Requires registration |
| Pennsylvania (emarketplace.state.pa.us) | Requires registration |
| Ohio (procure.ohio.gov) | Requires registration |
| Georgia (doas.ga.gov) | Requires registration |
| North Carolina (ips.nc.gov) | Requires registration |

These are documented as limitations per the brief's ground rules: "Don't bypass logins, paywalls, or auth walls. Document them as limitations."
