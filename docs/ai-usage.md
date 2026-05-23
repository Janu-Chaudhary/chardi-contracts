# AI Usage

## Tools used

| Tool | Purpose |
|---|---|
| **Kiro (Claude)** | Primary coding agent — backend workers, API routes, bug fixes, documentation |
| **Cursor (Claude)** | Frontend scaffolding — Next.js dashboard, components, UI design |
| **Claude chat** | Architecture decisions, debugging, research |

---

## What AI built

### Backend (Kiro)

- Full async Python worker architecture (`aiohttp` + `asyncpg`)
- SAM.gov fetcher with semaphore concurrency, exponential backoff, daily quota detection
- Deterministic SHA-256 ID generation (`fingerprint.py`)
- Database layer (`db.py`) — pool management, upsert SQL, scrape_runs observability
- All 6 portal workers (SAM.gov, California, Texas, New York, Virginia eVA + VITA)
- Mapper functions for each portal with `sanitize_date()` type safety
- pytest unit tests (7 passing)
- Diagnostic scripts (`test_api_direct.py`, `smoke_test.py`, `data_quality_check.py`)
- Bug fixes: backoff-outside-semaphore, datetime type safety, jitter formula

### Frontend (Cursor + Kiro)

- Next.js 16 App Router dashboard with Tailwind CSS + Radix UI
- 8 Edge API routes with parameterized SQL, filter logic, pagination
- Dashboard overview: KPI cards, 3-tab analytics charts, recent contracts
- Contracts explorer: search, 7 filters (status, region, portal, state, notice type, deadline range, posted range), sort, pagination
- Contract detail page with full metadata, documents, activity timeline
- CSV + JSON export with all active filters applied
- Mobile-responsive layout (cards on mobile, table on desktop)
- Loading skeletons, error states, empty states, no-results states
- `normalize-charts.ts` — missing module fix that prevented dashboard from loading
- `useEffect` dependency array fix (rules-of-hooks violation after HMR)

---

## Key prompts that solved real problems

### 1. Backoff outside semaphore (critical bug)

**Problem:** Backoff sleep was inside the `async with self._semaphore:` block, holding the concurrency slot during retry delays — blocking all other requests.

**Fix:** Restructured `fetch_page` to set `should_retry = True` inside the semaphore, then sleep outside it.

### 2. asyncpg datetime type error

**Problem:** `sanitize_date()` was returning ISO strings. asyncpg requires `datetime` objects for `timestamptz` columns.

**Fix:** Changed return type from `str` to `datetime`, added `datetime.strptime` parsing for all date formats SAM.gov uses.

### 3. Missing `normalize-charts.ts`

**Problem:** `dashboard-charts.tsx` imported `normalizePortalChart`, `normalizeStateChart`, `normalizeTrend` from `@/lib/normalize-charts` — file didn't exist. Dashboard crashed on load.

**Fix:** Created the file with proper type-safe normalizers.

### 4. useEffect dependency array size change

**Problem:** Adding 4 new date filter fields to the `useEffect` dependency array changed its size from 6 to 10 between HMR renders, violating React's rules-of-hooks.

**Fix:** Derived a single `filterKey` string from all filter values joined with `|`, used as the sole dependency — array size is always 1.

---

## Human responsibilities

- Neon database provisioning and schema validation
- SAM.gov API key registration
- Running ingestion against live APIs and validating row counts
- Vercel deployment (pending)
- Demo narrative and Loom recording

---

## Disclosure

All AI-generated code was tested against live APIs and the real Neon database. TypeScript strict mode with `tsc --noEmit` was run after every change. End-to-end API tests were run against the running dev server before each feature was considered complete.
