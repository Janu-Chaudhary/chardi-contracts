# Chardi Contracts — Trial Project A (United States)

A full-stack government contracts intelligence platform. Scrapes federal and state procurement portals, normalizes everything into a single PostgreSQL schema, and surfaces it through a production-quality Next.js dashboard with search, filters, charts, and CSV/JSON export.

**Live database:** 4,200+ opportunities across 6 portals · **Stack:** Python async workers + Next.js 16 + Neon PostgreSQL

---

## What's built

| Layer | Status | Details |
|---|---|---|
| Database schema | ✅ Live | Neon PostgreSQL — `opportunities`, `scrape_runs`, `scrape_errors` |
| SAM.gov worker | ✅ Production-ready | Federal API v2, async, 30-day backfill, rate-limit handling |
| California worker | ✅ Done | Cal eProcure — Playwright + Excel intercept — 456 records |
| Texas worker | ✅ Done | TxSmartBuy — Playwright + CSV export — 297 records |
| New York worker | ✅ Done | NYSCR — async scraper — 999 records |
| Virginia eVA worker | ✅ Done | eVA portal — 385 records |
| Virginia VITA worker | ✅ Done | VITA portal — 190 records |
| Next.js dashboard | ✅ Live locally | Full browse/filter/search/charts/export |
| Vercel deployment | ⏳ Pending | Run `vercel` in `frontend/` |

---

## Repository structure

```
CHARDI/
├── backend/
│   ├── core/
│   │   ├── db.py              # asyncpg pool, upsert SQL, scrape_runs helpers
│   │   ├── fingerprint.py     # SHA-256 deterministic ID generation
│   │   └── settings.py        # Env-backed config (DATABASE_URL, SAM_GOV_API_KEY)
│   ├── workers/
│   │   ├── samgov/            # Federal: fetcher, mapper, main
│   │   ├── california/        # State: scraper, mapper, main
│   │   ├── texas/             # State: scraper, mapper, main
│   │   ├── newyork/           # State: scraper, mapper, main
│   │   └── virginia/          # State: eVA + VITA scrapers, mappers, main
│   ├── tests/                 # pytest unit tests
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── (dashboard)/       # Overview + Contracts pages
│   │   └── api/               # Edge API routes (opportunities, stats, filters, charts, export)
│   ├── components/            # UI components (contracts, dashboard, charts, layout, states)
│   ├── lib/                   # Types, API client, DB client, data helpers
│   └── .env.local             # DATABASE_URL for Neon
├── scripts/                   # CLI runners and diagnostic tools
├── docs/                      # Architecture, schema, portal coverage, deployment
├── database/migrations/       # Schema placeholders (live in Neon)
└── .env                       # Backend env vars
```

---

## Quick start

### Backend (Python workers)

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Load environment variables
export $(grep -v '^#' .env | xargs)

# 3. Test SAM.gov API connectivity
python scripts/test_api_direct.py

# 4. Run ingestion
python -m backend.workers.samgov.main --days 1      # 1-day
python -m backend.workers.samgov.main --days 30     # 30-day backfill
python -m backend.workers.california.main
python -m backend.workers.texas.main
python -m backend.workers.newyork.main
python -m backend.workers.virginia.main

# 5. Verify data
python scripts/smoke_test.py
python scripts/data_quality_check.py
```

### Frontend (Next.js dashboard)

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

The frontend reads from the same Neon database via `frontend/.env.local`.

---

## Environment variables

### Backend (`.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Neon PostgreSQL connection string |
| `SAM_GOV_API_KEY` | Yes | SAM.gov public API key |
| `SAM_GOV_BASE_URL` | No | Defaults to prod search endpoint |
| `USER_AGENT` | No | Identifying User-Agent header |
| `REQUEST_TIMEOUT_SECONDS` | No | Read timeout (default 60) |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Same Neon connection string |

---

## Running tests

```bash
python -m pytest backend/tests -q
```

All 7 unit tests cover SAM.gov mapper, fingerprint generation, and California e2e.

---

## API routes (frontend)

| Route | Description |
|---|---|
| `GET /api/stats` | KPI counts — total, open, federal, state, portals, states |
| `GET /api/opportunities` | Paginated list with full filter + sort support |
| `GET /api/opportunities/[id]` | Single record detail |
| `GET /api/filters` | Facet options (states, portals, statuses, buyer types, notice types, industries) |
| `GET /api/charts/by-portal` | Contract counts per source portal |
| `GET /api/charts/by-state` | Contract counts per US state + Federal |
| `GET /api/charts/trend` | Monthly posting volume + upcoming deadlines |
| `GET /api/export` | Filtered CSV or JSON download (up to 5,000 rows) |

### Filter parameters (`/api/opportunities`)

| Param | Type | Example |
|---|---|---|
| `q` | string | `cloud infrastructure` |
| `state` | string (comma-sep) | `CA,TX` |
| `status` | string | `OPEN` |
| `portal` | string | `SAM.gov` |
| `portal_region` | string | `Federal` or `State` |
| `buyer_type` | string | `OFFICE` |
| `notice_type` | string | `Solicitation` |
| `industry` | string | `Information Technology` |
| `deadline_from` | ISO date | `2026-06-01` |
| `deadline_to` | ISO date | `2026-06-30` |
| `posted_from` | ISO date | `2026-05-01` |
| `posted_to` | ISO date | `2026-05-23` |
| `page` | int | `1` |
| `limit` | int (max 100) | `20` |
| `sort` | string | `deadline`, `posted_date`, `title`, `buyer_name` |
| `order` | string | `asc` or `desc` |

---

## Data coverage (as of May 23, 2026)

| Portal | Records | Region | Method |
|---|---|---|---|
| SAM.gov | 1,879 | Federal | REST API v2 |
| nyscr.ny.gov | 999 | State (NY) | Async scraper |
| caleprocure.ca.gov | 456 | State (CA) | Playwright + Excel |
| eva.virginia.gov | 385 | State (VA) | Async scraper |
| txsmartbuy.gov | 297 | State (TX) | Playwright + CSV |
| vita.virginia.gov | 190 | State (VA) | Async scraper |
| **Total** | **4,206** | | |

---

## Deployment

See [`docs/deployment.md`](docs/deployment.md) for Vercel + worker deployment instructions.

---

## Documentation index

| File | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, data flow, design principles |
| [`docs/schema.md`](docs/schema.md) | Database schema contract, upsert behavior |
| [`docs/portal-coverage.md`](docs/portal-coverage.md) | Per-portal field mapping and coverage |
| [`docs/deployment.md`](docs/deployment.md) | Environment setup, deploy commands |
| [`docs/ai-usage.md`](docs/ai-usage.md) | AI tooling and workflow notes |
| [`docs/metrics-summary.md`](docs/metrics-summary.md) | Live data metrics |
| [`docs/demo-script.md`](docs/demo-script.md) | 30-minute demo walkthrough |
