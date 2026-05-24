# Database Schema

Schema is live in Neon PostgreSQL. This document is the application contract for workers and API routes.

---

## Deterministic ID generation

```python
# backend/core/fingerprint.py
generate_deterministic_id(source_portal, source_record_id=..., title=..., buyer_name=..., deadline=...)
```

**Primary path:** `SHA-256(source_portal + ":" + source_record_id)`  
**Fallback:** normalized title + buyer_name + deadline date (for portals without stable record IDs)

Result is a 64-character lowercase hex string stored as `VARCHAR` primary key.

---

## Tables

### `opportunities`

The unified contract record. One row per unique opportunity across all portals.

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR PK | 64-char SHA-256 deterministic hash |
| `source_portal` | TEXT | e.g. `SAM.gov`, `nyscr.ny.gov`, `caleprocure.ca.gov` |
| `source_record_id` | TEXT | Portal's own ID (noticeId, contract number, etc.) |
| `solicitation_number` | TEXT | Solicitation/RFP number if available |
| `portal_region` | TEXT | `Federal`, `State`, `County`, or `City` |
| `title` | TEXT | Opportunity title (required) |
| `description` | TEXT | Full text or URL to description |
| `notice_type` | TEXT | e.g. `Solicitation`, `Award`, `Term`, `General` |
| `posted_date` | TIMESTAMPTZ | When the notice was published |
| `deadline` | TIMESTAMPTZ | Response/submission deadline |
| `state_region` | TEXT | 2-letter US state code (e.g. `CA`, `TX`, `NY`) |
| `industry` | TEXT | NAICS code or NIGP category description |
| `naics_code` | TEXT | NAICS code (SAM.gov only currently) |
| `value_numeric` | NUMERIC | Contract value. **89% overall coverage** — 100% for Oregon, NYC, Chicago; 94% for Cook County; 0% for SAM.gov, state portals (not published) |
| `value_min` | NUMERIC | Minimum value range |
| `value_max` | NUMERIC | Maximum value range |
| `currency` | TEXT | ISO 4217 code — always `USD` |
| `status` | TEXT | `OPEN`, `CLOSED`, `AWARDED`, `CANCELLED` |
| `buyer_name` | TEXT | Issuing agency/department name |
| `buyer_type` | TEXT | e.g. `OFFICE`, `State`, `Federal Agency` |
| `source_url` | TEXT | Direct link to the original notice |
| `documents` | JSONB | Array of `{title, url}` attachment objects |
| `raw_payload` | JSONB | Full original API/scrape response |
| `last_seen_at` | TIMESTAMPTZ | Updated on every successful upsert |
| `created_at` | TIMESTAMPTZ | First indexed timestamp |
| `updated_at` | TIMESTAMPTZ | Last modified timestamp (trigger-managed) |

### `scrape_runs`

One row per worker execution. Tracks health and throughput.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | Auto-increment run ID |
| `source_portal` | TEXT | Which portal this run covers |
| `start_time` | TIMESTAMPTZ | When the run started |
| `end_time` | TIMESTAMPTZ | When the run finished (NULL while running) |
| `status` | TEXT | `RUNNING`, `SUCCESS`, `PARTIAL_SUCCESS`, `FAILED` |
| `records_scraped` | INT | Count of rows upserted |
| `metadata` | JSONB | `{days, task_count, error_count, windows: [...]}` |

### `scrape_errors`

Dead-letter log for per-window or per-record failures.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `run_id` | INT FK | References `scrape_runs.id` |
| `source_portal` | TEXT | |
| `error_message` | TEXT | Exception message or HTTP status |
| `raw_payload` | JSONB | `{posted_from, posted_to, traceback}` |
| `created_at` | TIMESTAMPTZ | |

### `award_winners`

Pre-aggregated vendor win history. Powers the "Who has won similar?" enrichment feature.
Refreshed automatically after each worker upsert via `db.refresh_award_winners(source_portal)`.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `vendor_name` | TEXT | Winning vendor name |
| `industry` | TEXT | Industry or NAICS category |
| `state_region` | TEXT | 2-letter state code |
| `source_portal` | TEXT | Source portal |
| `win_count` | INT | Number of wins |
| `total_value` | NUMERIC | Sum of contract values |
| `avg_value` | NUMERIC | Average contract value |
| `last_win_date` | TIMESTAMPTZ | Most recent win date |
| `updated_at` | TIMESTAMPTZ | Refreshed after each ingest |

**Unique index:** `(vendor_name, industry, COALESCE(state_region,''), source_portal)` — safe to upsert concurrently.
**Current size:** 18,212 rows · 115,455 total wins across all portals.

---

## Upsert behavior

Workers use `INSERT ... ON CONFLICT (id) DO UPDATE`. Fields updated on conflict:

```sql
title, description, notice_type, deadline, status,
documents, last_seen_at, raw_payload, updated_at
```

Fields **not** overwritten on conflict (preserved from first insert):
`source_portal`, `source_record_id`, `portal_region`, `posted_date`, `state_region`, `buyer_name`, `created_at`

---

## Upsert tuple parameter order

`backend/core/db.py` `OPPORTUNITY_UPSERT_SQL` expects exactly 23 positional parameters:

```
$1  id                  (str)
$2  source_portal       (str)
$3  source_record_id    (str | None)
$4  solicitation_number (str | None)
$5  portal_region       (str)
$6  title               (str)
$7  description         (str | None)
$8  notice_type         (str | None)
$9  posted_date         (datetime | None)   ← must be datetime, not string
$10 deadline            (datetime | None)   ← must be datetime, not string
$11 state_region        (str | None)
$12 industry            (str | None)
$13 naics_code          (str | None)
$14 value_numeric       (float | None)
$15 value_min           (float | None)
$16 value_max           (float | None)
$17 currency            (str)
$18 status              (str)
$19 buyer_name          (str | None)
$20 buyer_type          (str | None)
$21 source_url          (str)
$22 documents           (str)   ← JSON string, cast to JSONB by SQL
$23 raw_payload         (str)   ← JSON string, cast to JSONB by SQL
```

**Critical:** asyncpg requires `datetime` objects for `timestamptz` columns. Passing ISO strings will raise a type error. Use `sanitize_date()` from each mapper.

---

## Indexes (live in Neon)

- `opportunities(source_portal)`
- `opportunities(status)`
- `opportunities(posted_date)`
- `opportunities(deadline)`
- `opportunities(state_region)`
- `opportunities(last_seen_at)`
- `scrape_runs(source_portal, start_time)`
