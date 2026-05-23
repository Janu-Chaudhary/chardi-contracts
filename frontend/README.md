# Chardi Contracts — Frontend

Production-quality Next.js 16 dashboard for the Chardi.ai government contracts intelligence platform. Reads live data from Neon PostgreSQL via 8 Edge API routes.

**Stack:** Next.js 16 (App Router) · TypeScript · Tailwind CSS v4 · Radix UI · Neon serverless

---

## Quick start

```bash
npm install
npm run dev
# Open http://localhost:3000
```

`DATABASE_URL` must be set in `.env.local` (already configured for Neon).

---

## Structure

```
app/
  (dashboard)/
    page.tsx                  # Overview — KPIs, charts, recent contracts
    layout.tsx                # AppShell wrapper
    contracts/
      page.tsx                # Contracts explorer
      [id]/page.tsx           # Contract detail
  api/
    opportunities/route.ts    # GET /api/opportunities — paginated, filtered list
    opportunities/[id]/route.ts  # GET /api/opportunities/[id] — single record
    stats/route.ts            # GET /api/stats — KPI counts
    filters/route.ts          # GET /api/filters — facet options
    charts/by-portal/route.ts # GET /api/charts/by-portal
    charts/by-state/route.ts  # GET /api/charts/by-state
    charts/trend/route.ts     # GET /api/charts/trend
    export/route.ts           # GET /api/export — CSV or JSON download

components/
  ui/                         # Radix-based primitives (Button, Card, Input, Select, Sheet, …)
  layout/                     # AppHeader, AppShell, DesktopSidebar, MobileNav
  contracts/                  # ContractsExplorer, ContractsFilters, ContractsTable,
                              # ContractCard, ContractDetail, ContractsPagination, StatusBadge
  dashboard/                  # KpiCards, DashboardCharts, RecentContracts, WatchlistPlaceholder
  charts/                     # HorizontalBarChart, VerticalBarChart
  states/                     # EmptyState, ErrorState, NoResultsState, LoadingSkeletons

lib/
  db.ts                       # Neon serverless client, query(), VALID_US_STATES
  data/server.ts              # Server-only RSC fetchers (stats, recent, charts)
  api.ts                      # Client-side fetchers → /api/* routes
  api-types.ts                # API response interfaces (OpportunityRow, StatsResponse, …)
  types.ts                    # Contract, ContractFilters, DEFAULT_FILTERS
  map-opportunity.ts          # OpportunityRow → Contract normalization
  normalize-charts.ts         # Chart API response normalizers
  status.ts                   # statusBadgeVariant, statusLabel
  utils.ts                    # cn(), formatCurrency(), formatDate()
  mock-data.ts                # @deprecated — demo fixtures only, not used in UI

hooks/
  use-debounce.ts             # useDebounce hook for search input
```

---

## API routes

All routes use `export const runtime = "edge"` and parameterized SQL.

### `GET /api/opportunities`

Paginated, filtered list of contracts.

**Query params:**

| Param | Type | Description |
|---|---|---|
| `q` | string | Full-text search (title, description, buyer_name) |
| `state` | string | Comma-separated state codes: `CA,TX` |
| `status` | string | `OPEN`, `CLOSED`, `AWARDED` |
| `portal` | string | `SAM.gov`, `nyscr.ny.gov`, etc. |
| `portal_region` | string | `Federal` or `State` |
| `buyer_type` | string | `OFFICE`, `State`, etc. |
| `notice_type` | string | `Solicitation`, `Award`, etc. |
| `industry` | string | Partial match on industry field |
| `deadline_from` | ISO date | `2026-06-01` |
| `deadline_to` | ISO date | `2026-06-30` |
| `posted_from` | ISO date | `2026-05-01` |
| `posted_to` | ISO date | `2026-05-23` |
| `page` | int | Default 1 |
| `limit` | int | Default 20, max 100 |
| `sort` | string | `deadline`, `posted_date`, `title`, `buyer_name`, `state_region` |
| `order` | string | `asc` or `desc` |

**Response:**
```json
{
  "data": [...],
  "pagination": { "page": 1, "limit": 20, "total": 4206, "total_pages": 211, "has_next": true, "has_prev": false },
  "filters_applied": { ... }
}
```

### `GET /api/stats`

```json
{ "total": 4206, "open": 4159, "closed": 47, "awarded": 0, "federal": 1879, "state_count": 2327, "portals": 6, "states": 53, "last_updated": "2026-05-23T05:17:23Z" }
```

### `GET /api/filters`

Returns facet options with counts for all filter dropdowns.

### `GET /api/charts/by-portal`

Contract counts per source portal with labels and colors.

### `GET /api/charts/by-state`

Contract counts per US state + Federal aggregate.

### `GET /api/charts/trend?months=6`

Monthly posting volume + upcoming deadlines by month.

### `GET /api/export?format=csv|json`

Accepts same filter params as `/api/opportunities`. Returns up to 5,000 rows as CSV or JSON attachment.

---

## Data flow

### Server Components (RSC)

`app/(dashboard)/page.tsx` and `app/(dashboard)/contracts/[id]/page.tsx` call `lib/data/server.ts` directly — no HTTP round-trip. Neon serverless driver runs SQL from the edge.

### Client Components

`ContractsExplorer` (`"use client"`) calls `/api/opportunities` + `/api/filters` via `fetch`. `DashboardCharts` (`"use client"`) calls `/api/charts/*`.

### Filter state

`ContractFilters` type in `lib/types.ts` holds all filter state. `filtersToQuery()` in `lib/api.ts` maps it to `OpportunitiesQuery`. A stable `filterKey` string (all values joined with `|`) is used as the single `useEffect` dependency to avoid rules-of-hooks violations.

---

## Design decisions

| Choice | Rationale |
|---|---|
| Warm monochrome + coral accent | Matches Chardi.ai editorial tone |
| Playfair Display (headings only) | Editorial hierarchy without serif overload |
| Inter for UI/body | Legible at small sizes for dense metadata |
| Mobile cards / desktop table | Cards below `lg`; table at `lg+` |
| Bottom sheet filters on mobile | Full-width filter UX with sticky Apply/Reset |
| Server Components default | Pages are RSC; client islands for interactive explorer and charts |
| Edge runtime | All API routes run on Vercel Edge for low latency |
| Parameterized SQL | All user input goes through `$N` params — no string interpolation |

---

## Scripts

```bash
npm run dev      # Development server (Turbopack)
npm run build    # Production build
npm run lint     # ESLint
```

---

## Known limitations / TODOs

- `vendor` field is NULL for all records (not in any portal's data)
- `value_numeric` is NULL for ~99% of records (portals don't publish contract values)
- Value range filter UI not built (no data to filter on)
- Watchlist / saved searches — placeholder only
- Vercel deployment pending
