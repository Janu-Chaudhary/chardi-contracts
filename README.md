# Chardi Contracts

Government procurement intelligence across federal, state, and city portals — normalized, deduplicated, and searchable in one place.

**Live** → [chardi-contracts.vercel.app](https://chardi-contracts.vercel.app)  
**Data** → 129,794 opportunities · 15 portals · 14,293 open · updated daily  
**Stack** → Python async workers · Next.js 16 · Neon PostgreSQL · GitHub Actions

---

![Dashboard Overview](docs/screenshots/01_dashboard_overview.png)

---

## Coverage

| Portal | Records | Open | Awarded/Closed | Region | Method |
|--------|---------|------|----------------|--------|--------|
| SAM.gov | 6,186 | 6,186 | 0 | Federal | REST API v2 |
| data.oregon.gov | 109,119 | 0 | 109,119 AWARDED | State — OR | Socrata API |
| datacatalog.cookcountyil.gov | 5,236 | 2,300 | 2,936 | County — IL | Socrata API |
| data.montgomerycountymd.gov | 2,394 | 2,394 | 0 | County — MD | Socrata API |
| data.houstontx.gov | 2,310 | 11 | 2,299 | City — TX | CKAN + XLSX |
| data.cityofnewyork.us | 1,018 | 0 | 1,018 | City — NY | Socrata API |
| nyscr.ny.gov | 999 | 953 | 46 | State — NY | Async HTTP |
| data.cityofchicago.org | 659 | 654 | 5 | City — IL | Socrata API |
| caleprocure.ca.gov | 467 | 467 | 0 | State — CA | Playwright + Excel |
| eva.virginia.gov | 385 | 383 | 2 | State — VA | Async HTTP |
| txsmartbuy.gov | 298 | 298 | 0 | State — TX | Playwright + CSV |
| doas.ga.gov | 201 | 201 | 0 | State — GA | Playwright |
| vita.virginia.gov | 190 | 190 | 0 | State — VA | Async HTTP |
| bidbuy.illinois.gov | 186 | 180 | 6 | State — IL | Playwright |
| dms.myflorida.com | 146 | 76 | 70 | State — FL | Async HTTP |
| **Total** | **129,794** | **14,293** | **115,501** | | |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Python Workers (15 portals)                       │
│  SAM.gov · Oregon · Cook County · Montgomery County · Houston        │
│  NYC · NY · Chicago · California · Virginia(×2) · TX · GA · IL · FL │
│  aiohttp / Playwright / CKAN → mapper → asyncpg upsert              │
└─────────────────────────┬────────────────────────────────────────────┘
                          │ ON CONFLICT upsert (SHA-256 deterministic IDs)
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  Neon PostgreSQL (serverless)                        │
│  opportunities (129,794 rows) · scrape_runs · scrape_errors         │
│  award_winners (18,212 rows) — pre-aggregated enrichment table      │
└─────────────────────────┬────────────────────────────────────────────┘
                          │ @neondatabase/serverless
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Next.js 16 (App Router, Edge runtime)                  │
│  /api/opportunities · /api/stats · /api/filters                     │
│  /api/charts/* · /api/export · /api/opportunities/[id]/winners      │
│  RSC pages: Overview · Contracts · Trends · Contract detail         │
└──────────────────────────────────────────────────────────────────────┘
                          ▲
                          │ GitHub Actions cron (06:00 UTC daily)
┌──────────────────────────────────────────────────────────────────────┐
│  .github/workflows/daily-ingest-all.yml                             │
│  14 parallel jobs · continue-on-error per job · smoke test verify   │
└──────────────────────────────────────────────────────────────────────┘
```

Each portal has a dedicated worker — `fetcher.py` handles network and rate limits, `mapper.py` normalizes to a canonical tuple, `main.py` orchestrates the run lifecycle. All workers share `core/db.py` for upserts and `core/fingerprint.py` for deterministic ID generation.

![System Architecture](docs/screenshots/architecture.png)

### Database

Four tables. No joins required for dashboard queries.

`opportunities` — the unified contract record. One row per unique opportunity across all portals, identified by a SHA-256 deterministic primary key. Safe to upsert 100 times a day without duplicates.

`award_winners` — pre-aggregated vendor win history by industry + state. Powers the "Who has won similar?" enrichment feature with <10ms query time. Refreshed automatically after each worker run.

`scrape_runs` — one row per worker execution. Tracks status (`RUNNING · SUCCESS · PARTIAL_SUCCESS · FAILED`), record counts, and a JSONB metadata column.

`scrape_errors` — dead-letter log. Every failed fetch or parse writes here with full traceback and context.

![Database Schema](docs/screenshots/db_schema.png)

---

## Product

### Contracts Explorer

Full-text search, filter by portal, state, status, and deadline range. Sortable table on desktop, card view on mobile. **Filters persist in URL** — back button restores exact filter state.

![Contracts Explorer](docs/screenshots/02_contracts_explorer.png)

![Search Active](docs/screenshots/03_contracts_search.png)

### Filtered View — SAM.gov Federal

![SAM.gov Filtered](docs/screenshots/04_contracts_filtered_samgov.png)

### Contract Detail + Award Enrichment

Each contract detail page shows **"Who has won similar?"** — a leaderboard of vendors who have won similar contracts before, matched by industry and state. Pre-computed from 109k+ awarded records. Zero latency — single indexed lookup.

![Contract Detail](docs/screenshots/06_contract_detail.png)

### Trends & Charts

Monthly posting volume (open vs. closed), upcoming deadlines. Both charts are fully interactive — hover tooltips anchored to bar height, legend toggles, responsive on mobile.

![Trends](docs/screenshots/05_trends_charts.png)

### Mobile

Designed mobile-first. Cards on small screens, table on desktop. Filter drawer, sticky header, thumb-friendly controls. All sections stack cleanly — no overflow or text clipping.

<p>
  <img src="docs/screenshots/07_mobile_dashboard.png" width="320" alt="Mobile Dashboard" />
  &nbsp;&nbsp;
  <img src="docs/screenshots/08_mobile_contracts_cards.png" width="320" alt="Mobile Cards" />
</p>

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL (Neon recommended)
- SAM.gov API key — free at [api.sam.gov](https://api.sam.gov)

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
# Add DATABASE_URL and SAM_GOV_API_KEY
```

Run a single worker:

```bash
python -m backend.workers.samgov.main --days 30
python -m backend.workers.california.main
python -m backend.workers.texas.main
python -m backend.workers.newyork.main
python -m backend.workers.virginia.main
python -m backend.workers.chicago.main
python -m backend.workers.georgia.main
python -m backend.workers.illinois.main
python -m backend.workers.florida.main
python -m backend.workers.oregon.main
python -m backend.workers.cook_county.main
python -m backend.workers.houston.main
python -m backend.workers.montgomery_county.main
```

Verify:

```bash
python scripts/smoke_test.py
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # add DATABASE_URL
npm install
npm run dev
# http://localhost:3000
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Neon PostgreSQL connection string |
| `SAM_GOV_API_KEY` | Yes | SAM.gov public API key |
| `USER_AGENT` | No | Identifying header (default provided) |
| `REQUEST_TIMEOUT_SECONDS` | No | Read timeout — default 60 |

### Tests

```bash
python -m pytest backend/tests -q
```

---

## API

All routes are Next.js Edge API routes deployed on Vercel.

| Route | Description |
|-------|-------------|
| `GET /api/stats` | KPI counts — total, open, federal, state, portals, states |
| `GET /api/opportunities` | Paginated list with filter + sort |
| `GET /api/opportunities/[id]` | Single record detail |
| `GET /api/opportunities/[id]/winners` | Award enrichment — top vendors who won similar contracts |
| `GET /api/filters` | Facet options — states, portals, statuses, buyer types |
| `GET /api/charts/by-portal` | Contract counts per portal |
| `GET /api/charts/by-state` | Contract counts per US state |
| `GET /api/charts/trend` | Monthly posting volume + upcoming deadlines |
| `GET /api/export?format=csv` | Filtered CSV download — up to 5,000 rows |
| `GET /api/export?format=json` | Filtered JSON download — up to 5,000 rows |

### Filter parameters

| Param | Type | Example |
|-------|------|---------|
| `q` | string | `cloud infrastructure` |
| `state` | string | `CA` |
| `status` | string | `OPEN` |
| `portal` | string | `SAM.gov` |
| `portal_region` | string | `Federal` · `State` |
| `deadline_from` | ISO date | `2026-06-01` |
| `deadline_to` | ISO date | `2026-06-30` |
| `sort` | string | `deadline` · `posted_date` · `title` · `buyer_name` |
| `order` | string | `asc` · `desc` |
| `page` | int | `1` |
| `limit` | int (max 100) | `20` |

---

## AI Leverage

This project was built using a deliberate **Human-Orchestrated Heterogeneous AI Pipeline** — one person acting as the routing layer between specialized models, each assigned to what it does best.

See [`docs/ai-usage.md`](docs/ai-usage.md) and [`KIRO_md/AI_USAGE_CONTEXT.md`](KIRO_md/AI_USAGE_CONTEXT.md) for the full breakdown.

### AI Tool Roles

| Tool | Role | Phase |
|------|------|-------|
| **Gemini Pro Extended** | Architecture, schema design, system prompts, constraint engineering | Planning |
| **Perplexity** | Research validation, prompt engineering, frontend design spec | Pre-build |
| **Manus AI** | UI/UX template design — palette, typography, component system, mobile-first rules | Frontend design |
| **Cursor** | Individual scraper prototypes + MASTER_PLAN.md handoff artifacts | Component build |
| **Kiro** | Full-project integration, all workers, frontend, GitHub Actions, debugging | End-to-end execution |

### AI Collaboration Flow

```
Gemini Pro Extended
  ↓ Architecture constraints, 3-table schema, SHA-256 fingerprint strategy
  ↓ Smart 429 Interceptor, Delta Sync, PAGE_LIMIT=1000, system prompt for Kiro

Perplexity
  ↓ Validates API patterns (asyncpg strictness, SAM.gov quota, Socrata CSV)
  ↓ Refines prompts before feeding to Gemini

Manus AI
  ↓ Full UI/UX design specification
  ↓ Warm palette, Playfair/Inter typography, shadcn theming, mobile-first rules
  ↓ Component customization: Button, Card, Table, Badge, Sheet, Input

Cursor (Free Tier)
  ↓ Chicago scraper (Socrata CSV API — no Selenium, 55s for 185k rows)
  ↓ Illinois BidBuy (JSF + Selenium click automation)
  ↓ Florida DMS (__NEXT_DATA__ parsing, ThreadPoolExecutor)
  ↓ NYC Open Data (Socrata metadata + file attachment)
  ↓ MASTER_PLAN.md for each → handoff artifacts for Kiro

Kiro
  ↓ Full project scaffold, all 15 workers integrated
  ↓ Frontend dashboard (Next.js 16, shadcn, Tailwind)
  ↓ Award enrichment feature (award_winners table, /winners API, WinnersSidebar)
  ↓ URL-based filter persistence, responsive layout fixes
  ↓ GitHub Actions cron (14 workers + smoke test)
  ↓ Debugging, testing, human evaluation loop
```

### Key AI-Assisted Engineering Decisions

| Decision | Source | Impact |
|----------|--------|--------|
| SHA-256 deterministic IDs | Gemini | Solved CDC / deduplication permanently |
| `ON CONFLICT DO UPDATE` upsert | Gemini | Idempotent pipeline, safe to run daily |
| Explicit `::timestamptz` / `::jsonb` casts | Gemini | Prevented all asyncpg type crashes |
| Smart 429 Interceptor | Gemini | Prevented burning daily API quota on retries |
| Delta Sync — `modifiedFrom` | Gemini | Captures updates to old records, not just new |
| PAGE_LIMIT = 1000 | Gemini | 10x reduction in API calls per run |
| Playwright `expect_download()` in-memory | Gemini | No local file I/O, no blocking |
| Socrata CSV API — no Selenium | Cursor | 55s vs. minutes for Chicago / NYC |
| `__NEXT_DATA__` parsing for Florida | Cursor | Pure stdlib, no BeautifulSoup |
| Mobile-first card / table dual rendering | Manus AI | Demo-ready on phone |
| Semantic CSS variables in globals.css | Manus AI | Consistent theming without scattered overrides |
| award_winners pre-aggregation table | Kiro | <10ms enrichment queries vs. 100ms+ live scan |
| URL-based filter persistence | Kiro | Back button restores exact filter state |

---

## Repository structure

```
CHARDI/
├── backend/
│   ├── core/
│   │   ├── db.py              # asyncpg pool, upsert SQL, award_winners refresh
│   │   ├── fingerprint.py     # SHA-256 deterministic ID generation
│   │   └── settings.py        # Env-backed config
│   ├── workers/
│   │   ├── samgov/            # Federal — fetcher, mapper, main
│   │   ├── california/        # Playwright + Excel intercept
│   │   ├── texas/             # Playwright + CSV export
│   │   ├── newyork/           # Async HTTP scraper
│   │   ├── nyc_contract_awards/ # Socrata API
│   │   ├── chicago/           # Socrata API
│   │   ├── virginia/          # eVA (Playwright) + VITA (async HTTP)
│   │   ├── georgia/           # Playwright
│   │   ├── illinois/          # Playwright
│   │   ├── florida/           # Async HTTP
│   │   ├── oregon/            # Socrata API — 109k awarded contracts
│   │   ├── cook_county/       # Socrata API — Cook County IL
│   │   ├── houston/           # CKAN + XLSX — Houston TX
│   │   └── montgomery_county/ # Socrata API — Montgomery County MD
│   ├── tests/                 # pytest
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── (dashboard)/       # Overview · Contracts · Trends
│   │   └── api/               # 10 Edge API routes incl. /winners
│   ├── components/
│   │   ├── contracts/         # ContractsExplorer, ContractDetail, WinnersSidebar
│   │   ├── charts/            # TrendVolumeChart, DeadlineTrendChart
│   │   └── layout/            # AppShell, AppHeader, DesktopSidebar, MobileNav
│   └── lib/                   # Types, API client, DB client
├── .github/workflows/
│   └── daily-ingest-all.yml   # Daily cron — all 14 portals + smoke test
├── docs/                      # Architecture, schema, portal coverage, metrics
├── KIRO_md/                   # AI usage context, leverage notes, action plans
├── scripts/                   # Smoke test, runner scripts
└── .env.example
```

---

## Limitations

| Portal | Note |
|--------|------|
| Virginia eVA | Returns 403 to CI/cloud IPs — graceful skip, VITA still runs |
| Pennsylvania | Requires vendor registration — not accessible |
| Ohio | Requires vendor registration — not accessible |
| North Carolina | Requires vendor registration — not accessible |
| `value_numeric` | Not published by most portals — ~0% coverage |

---

## Documentation

| File | Contents |
|------|----------|
| [`docs/architecture.md`](docs/architecture.md) | System design, data flow, design principles |
| [`docs/schema.md`](docs/schema.md) | Full schema, upsert behavior, parameter order |
| [`docs/portal-coverage.md`](docs/portal-coverage.md) | Per-portal field mapping and coverage |
| [`docs/metrics-summary.md`](docs/metrics-summary.md) | Live data metrics |
| [`docs/ai-usage.md`](docs/ai-usage.md) | Full AI tool breakdown and key prompts |
| [`docs/demo-script.md`](docs/demo-script.md) | Demo walkthrough |
| [`KIRO_md/AI_USAGE_CONTEXT.md`](KIRO_md/AI_USAGE_CONTEXT.md) | Master AI collaboration documentation |
| [`KIRO_md/AI_LEVERAGE.md`](KIRO_md/AI_LEVERAGE.md) | AI leverage notes, system prompts, Gemini/Perplexity/Manus AI inputs |
