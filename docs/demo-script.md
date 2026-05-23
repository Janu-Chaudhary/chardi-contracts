# Demo Script (30 minutes)

## Before the demo

```bash
# 1. Verify API is live
export $(grep -v '^#' .env | xargs)
python scripts/test_api_direct.py
# Expected: Status 200, 700+ records for today

# 2. Check database state
python scripts/smoke_test.py
# Expected: 4,200+ total opportunities

# 3. Start frontend (if not deployed)
cd frontend && npm run dev
# Open http://localhost:3000
```

---

## Segment 1 — Live dashboard (5 min)

**Open https://chardi-contracts.vercel.app**

Point out:
- KPI cards: **10,735 total contracts**, 9,588 open, 6,186 federal, 4,549 state+city
- "11 active portals" in the subtitle
- Analytics tabs: By portal → By state
  - By portal: SAM.gov leads at 6,186, then NYC (1,018), NY State (999), Chicago (659), CA (467)
  - By state: Federal top, then New York (2,017), Illinois (845), Virginia (575), California (467)
- Trend chart: spike in Apr/May 2026 as SAM.gov backfill ran

**Switch to Contracts page.**

- Default view: OPEN contracts, soonest deadline first (not stale expired data)
- Search "cloud" → shows federal IT contracts
- Filter by State → select CA → 467 California contracts
- Set Deadline range → June 2026 → contracts due next month
- Click a contract → detail page with source URL, buyer, documents, timestamps
- Click "View source" → opens original portal page
- Download button → dropdown with CSV and JSON options
- Both respect all active filters

---

## Segment 2 — Architecture walkthrough (10 min)

**Show `docs/architecture.md` or draw on whiteboard.**

Key points:

1. **Unified schema** — one `opportunities` table, 23 fields, all portals write to the same columns
2. **Deterministic IDs** — SHA-256(portal + source_record_id). Run the same scrape twice → 0 duplicates
3. **6 portals, 2 methods:**
   - SAM.gov: REST API v2, async pagination, semaphore-limited concurrency
   - State portals: Playwright headless browser, intercept Excel/CSV downloads
4. **Graceful degradation** — `PARTIAL_SUCCESS` when some day-windows fail. One bad day doesn't abort the run.
5. **Frontend architecture** — Next.js Edge runtime, Neon serverless driver, parameterized SQL throughout

**Show `backend/workers/samgov/fetcher.py`**

- Semaphore(3) limits concurrency
- Backoff sleep is **outside** the semaphore — critical fix that allows other requests to proceed during retry delays
- `nextAccessTime` in 429 response → fatal error (daily quota exhausted)

**Show `backend/core/db.py`**

- `OPPORTUNITY_UPSERT_SQL` — 23 params, `ON CONFLICT (id) DO UPDATE`
- `scrape_runs` + `scrape_errors` for observability

**Show `frontend/app/api/opportunities/route.ts`**

- Dynamic WHERE clause built with parameterized `$N` placeholders
- Sort column whitelist prevents SQL injection
- Parallel data + count queries

---

## Segment 3 — AI workflow demo (5 min)

**Show `docs/ai-usage.md`**

Walk through 2–3 real bugs that AI helped fix:

1. **Backoff outside semaphore** — show the before/after in `fetcher.py`. The bug was holding the concurrency slot during sleep, blocking all other requests.

2. **asyncpg datetime type error** — show `sanitize_date()` in `mapper.py`. asyncpg requires `datetime` objects, not ISO strings. AI caught this from the error message.

3. **Missing `normalize-charts.ts`** — dashboard was crashing silently. AI identified the missing import, created the file with proper type-safe normalizers.

**Show Kiro conversation history** — demonstrate the iterative debugging workflow.

---

## Segment 4 — Q&A (10 min)

**Likely questions and answers:**

**Q: Why only 6 portals, not 50?**  
A: 6 portals are fully scraped and live. The other 44 require vendor registration or login — documented in `docs/portal-coverage.md` as limitations per the brief's ground rules. The architecture supports adding new portals in ~2 hours each.

**Q: How do you handle duplicates?**  
A: Deterministic SHA-256 IDs. Run the same scrape twice — `ON CONFLICT DO UPDATE` means 0 new rows. Verified in testing.

**Q: What about rate limits?**  
A: SAM.gov has a daily quota. Worker detects `nextAccessTime` in the 429 response and raises a fatal error rather than wasting retries. Concurrency reduced from 5 to 3 after hitting the limit in testing.

**Q: How would you add a new state portal?**  
A: Create `backend/workers/newstate/` with `scraper.py`, `mapper.py`, `main.py`. Reuse `backend/core/db.py` and `fingerprint.py`. The mapper just needs to produce a 23-element tuple matching `OPPORTUNITY_UPSERT_SQL`. ~2 hours for a simple portal.

**Q: Add a feature live** (expect this)  
Likely candidates: add a "posted in last 7 days" quick filter, add industry filter to the UI, or add a count badge to the filter sidebar.

---

## Post-demo

```bash
# Run 30-day SAM.gov backfill if more volume is needed
python -m backend.workers.samgov.main --days 30

# Check results
python scripts/smoke_test.py
```
