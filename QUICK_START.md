# Quick Start — Chardi Contracts

**Status:** ✅ Live — 4,206 contracts across 6 portals  
**Frontend:** http://localhost:3000 (run `npm run dev` in `frontend/`)  
**Database:** Neon PostgreSQL (configured in `.env` and `frontend/.env.local`)

---

## Start the dashboard

```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

---

## Run a worker

```bash
# Load env vars
export $(grep -v '^#' .env | xargs)

# Federal (SAM.gov)
python -m backend.workers.samgov.main --days 1      # today only
python -m backend.workers.samgov.main --days 30     # 30-day backfill

# State portals
python -m backend.workers.california.main
python -m backend.workers.texas.main
python -m backend.workers.newyork.main
python -m backend.workers.virginia.main
```

---

## Verify data

```bash
export $(grep -v '^#' .env | xargs)
python scripts/smoke_test.py          # total counts + recent runs
python scripts/data_quality_check.py  # field coverage + duplicate check
python scripts/test_api_direct.py     # SAM.gov API connectivity
```

---

## Run tests

```bash
python -m pytest backend/tests -q
# Expected: 7 passed
```

---

## Project structure

```
CHARDI/
├── backend/workers/          # 6 portal scrapers
│   ├── samgov/               # Federal — REST API
│   ├── california/           # State — Playwright + Excel
│   ├── texas/                # State — Playwright + CSV
│   ├── newyork/              # State — async HTTP
│   └── virginia/             # State — eVA + VITA
├── backend/core/             # db.py, fingerprint.py, settings.py
├── frontend/                 # Next.js 16 dashboard
│   ├── app/api/              # 8 Edge API routes
│   ├── components/           # UI components
│   └── lib/                  # Types, API client, DB client
├── scripts/                  # Diagnostic and runner scripts
├── docs/                     # Full documentation
└── .env                      # Backend secrets
```

---

## Current data

| Portal | Records |
|---|---|
| SAM.gov (Federal) | 1,879 |
| nyscr.ny.gov (NY) | 999 |
| caleprocure.ca.gov (CA) | 456 |
| eva.virginia.gov (VA) | 385 |
| txsmartbuy.gov (TX) | 297 |
| vita.virginia.gov (VA) | 190 |
| **Total** | **4,206** |

---

## Documentation

| Doc | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, data flow |
| [`docs/schema.md`](docs/schema.md) | Database schema, upsert behavior |
| [`docs/portal-coverage.md`](docs/portal-coverage.md) | Per-portal field mapping |
| [`docs/deployment.md`](docs/deployment.md) | Vercel + worker deployment |
| [`docs/ai-usage.md`](docs/ai-usage.md) | AI tools and key fixes |
| [`docs/metrics-summary.md`](docs/metrics-summary.md) | Live data metrics |
| [`docs/demo-script.md`](docs/demo-script.md) | 30-minute demo walkthrough |
| [`frontend/README.md`](frontend/README.md) | Frontend API docs, structure |
