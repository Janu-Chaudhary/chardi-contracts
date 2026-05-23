# Architecture

## Overview

Chardi Contracts is a full-stack government procurement intelligence platform. Python async workers scrape 6 portals (1 federal, 5 state) and normalize everything into a single Neon PostgreSQL schema. A Next.js 16 dashboard reads the same database directly via the Neon serverless driver and exposes 8 Edge API routes for browse, filter, search, charts, and export.

```
┌─────────────────────────────────────────────────────────────┐
│                     Python Workers                          │
│  SAM.gov · California · Texas · New York · Virginia (×2)   │
│  aiohttp / Playwright → mapper → asyncpg upsert            │
└────────────────────────┬────────────────────────────────────┘
                         │ ON CONFLICT upsert
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Neon PostgreSQL (serverless)                   │
│  opportunities · scrape_runs · scrape_errors               │
└────────────────────────┬────────────────────────────────────┘
                         │ @neondatabase/serverless
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Next.js 16 (App Router, Edge runtime)         │
│  /api/opportunities · /api/stats · /api/filters            │
│  /api/charts/* · /api/export                               │
│  RSC pages: Overview · Contracts · Contract detail         │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### Backend workers

| Worker | Portal | Method | Records |
|---|---|---|---|
| `backend/workers/samgov/` | SAM.gov (Federal) | REST API v2 + asyncpg | 1,879 |
| `backend/workers/california/` | Cal eProcure | Playwright + Excel intercept | 456 |
| `backend/workers/texas/` | TxSmartBuy | Playwright + CSV export | 297 |
| `backend/workers/newyork/` | NYSCR | Async HTTP scraper | 999 |
| `backend/workers/virginia/` | eVA + VITA | Async HTTP scrapers | 575 |

All workers share:
- `backend/core/db.py` — asyncpg pool, `upsert_opportunities`, scrape_runs helpers
- `backend/core/fingerprint.py` — SHA-256 deterministic ID
- `backend/core/settings.py` — env-backed config

### Frontend

| File | Role |
|---|---|
| `frontend/lib/db.ts` | Neon serverless client, `query()` helper, `VALID_US_STATES` |
| `frontend/lib/data/server.ts` | Server-only RSC data fetchers (stats, recent, charts) |
| `frontend/lib/api.ts` | Client-side fetchers → `/api/*` routes |
| `frontend/lib/types.ts` | `Contract`, `ContractFilters`, `DEFAULT_FILTERS` |
| `frontend/lib/api-types.ts` | API response shapes (`OpportunityRow`, `StatsResponse`, etc.) |
| `frontend/lib/map-opportunity.ts` | `OpportunityRow` → `Contract` normalization |
| `frontend/lib/normalize-charts.ts` | Chart API response normalizers |

---

## Ingestion flow

### SAM.gov (federal)

1. Insert `scrape_runs` row (`RUNNING`).
2. Partition date range into per-day windows (`postedFrom = postedTo`).
3. Fetch pages concurrently (semaphore = 3) with exponential backoff + jitter.
4. Backoff sleep runs **outside** the semaphore to release the concurrency slot.
5. Map each notice → deterministic SHA-256 `id` → upsert via `ON CONFLICT`.
6. Log per-window failures to `scrape_errors` with full traceback.
7. Finalize run as `SUCCESS`, `PARTIAL_SUCCESS`, or `FAILED`.

### State portals (Playwright-based)

1. Launch headless Chromium via Playwright.
2. Navigate to portal, set date/filter parameters.
3. Intercept network response (Excel or CSV download).
4. Parse with Pandas → map rows → batch upsert.
5. Log via same `scrape_runs` / `scrape_errors` tables.

---

## Frontend data flow

### Server Components (RSC pages)

Dashboard overview and contract detail pages call `lib/data/server.ts` directly — no HTTP round-trip. Neon serverless driver runs the SQL query from the edge.

### Client Components

`ContractsExplorer` and `DashboardCharts` are `"use client"` components. They call `/api/*` routes via `fetch`. This gives them real-time filter reactivity without full page reloads.

### Edge API routes

All API routes use `export const runtime = "edge"`. They use the same `lib/db.ts` Neon client. Parameterized queries throughout — no string interpolation of user input.

---

## Design principles

- **Deterministic IDs** — SHA-256(portal + source_record_id). Stable across daily refreshes. No UUID/autoincrement.
- **Graceful degradation** — one failed day window does not abort the run. `PARTIAL_SUCCESS` is a valid outcome.
- **No microservices** — single-repo workers invoked by CLI or cron. Simple to reason about.
- **Type safety** — asyncpg requires `datetime` objects (not strings). Frontend uses TypeScript strict mode.
- **SQL injection prevention** — all API routes use parameterized queries with a whitelist for sort columns.
- **State filter** — `VALID_US_STATES` list in `lib/db.ts` filters out international codes that SAM.gov includes in `state_region`.

---

## Daily refresh (target)

Run `python -m backend.workers.samgov.main --days 1` once per day via cron or GitHub Actions. State workers can run weekly or on-demand. No in-repo scheduler yet — see `docs/deployment.md`.
