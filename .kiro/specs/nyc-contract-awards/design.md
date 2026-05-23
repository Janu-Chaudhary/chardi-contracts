# Design Document — NYC Contract Awards Worker

## Overview

This document describes the technical design for the `nyc_contract_awards` worker, a new Python package under `backend/workers/nyc_contract_awards/`. It follows the identical three-module pattern (`fetcher.py`, `mapper.py`, `main.py`) used by all existing CHARDI workers (florida, georgia, samgov, etc.).

The worker ingests NYC Open Data contract award records from Socrata dataset `qyyg-4tf5`, filters to 2026 start dates, and upserts them into the shared `opportunities` table via `backend.core.db`.

---

## Components and Interfaces

### `fetcher.py`
- **`fetch_daily_json(session: aiohttp.ClientSession) -> list[dict]`** — async; paginates Socrata JSON API, retries on transient errors, returns 2026-filtered records.
- **`fetch_initial_csv() -> list[dict]`** — sync; streams full CSV export via stdlib, returns 2026-filtered records.
- **`_fetch_page(session, offset: int) -> list[dict]`** — async internal; fetches one page with retry/backoff.
- **`_filter_2026(records: list[dict]) -> list[dict]`** — filters records to `start_date` year == 2026.
- **`_parse_date(val: str | None) -> datetime | None`** — shared date parser (ISO 8601 + date-only).

### `mapper.py`
- **`map_nyc_row(record: dict) -> tuple`** — maps one Socrata record to a 23-field upsert tuple.
- **`_parse_amount(val: str | None) -> float | None`** — strips currency symbols, parses to float.
- **`_derive_status(end_date: datetime | None) -> str`** — returns `"OPEN"` or `"CLOSED"`.
- **`_serialize_documents(val: str | None) -> str`** — returns JSON array string.
- **`SOURCE_PORTAL: str`** — module-level constant `"data.cityofnewyork.us"`.

### `main.py`
- **`run_nyc_ingestion(mode: str) -> dict`** — async orchestrator; calls fetcher, mapper, db upsert, observability.
- **`main()`** — CLI entry point; parses `--mode` arg, runs `asyncio.run(_async_main(mode))`.

### External Interfaces
- **Socrata JSON API**: `GET https://data.cityofnewyork.us/resource/qyyg-4tf5.json?$limit=1000&$offset=N`
- **Socrata CSV Export**: `GET https://data.cityofnewyork.us/api/views/qyyg-4tf5/rows.csv?accessType=DOWNLOAD`
- **`backend.core.db`**: `insert_scrape_run`, `finalize_scrape_run`, `log_scrape_error`, `upsert_opportunities`
- **`backend.core.fingerprint`**: `generate_deterministic_id`
- **`backend.core.settings`**: `USER_AGENT`, `REQUEST_TIMEOUT_SECONDS`

---

## Data Models

### Input — Socrata JSON Record (daily mode)

```json
{
  "request_id": "20261234",
  "short_title": "IT Services Contract",
  "agency_name": "Department of Information Technology",
  "vendor_name": "Acme Corp",
  "category_description": "Technology",
  "selection_method_description": "Competitive Sealed Bid",
  "start_date": "2026-01-15T00:00:00.000",
  "end_date": "2027-01-14T00:00:00.000",
  "contract_amount": "1250000.00",
  "document_links": "https://example.com/doc.pdf",
  "type_of_notice_description": "AWARD"
}
```

### Input — CSV Row (initial load mode)

Same fields as JSON but all values are strings; column names match Socrata field names.

### Output — 23-field Upsert Tuple

```python
(
    "sha256hex",                          # $1  id
    "data.cityofnewyork.us",              # $2  source_portal
    "20261234",                           # $3  source_record_id
    "20261234",                           # $4  solicitation_number
    "City",                               # $5  portal_region
    "IT Services Contract",               # $6  title
    "Acme Corp",                          # $7  description
    "Competitive Sealed Bid",             # $8  notice_type
    datetime(2026, 1, 15),                # $9  posted_date
    datetime(2027, 1, 14),                # $10 deadline
    "NY",                                 # $11 state_region
    "Technology",                         # $12 industry
    None,                                 # $13 naics_code
    1250000.0,                            # $14 value_numeric
    None,                                 # $15 value_min
    None,                                 # $16 value_max
    "USD",                                # $17 currency
    "OPEN",                               # $18 status
    "Department of Information Technology", # $19 buyer_name
    "City",                               # $20 buyer_type
    "https://data.cityofnewyork.us/resource/qyyg-4tf5/20261234", # $21 source_url
    '[{"title": "Document", "url": "https://example.com/doc.pdf"}]', # $22 documents
    '{"request_id": "20261234", ...}',    # $23 raw_payload
)
```

### Observability Records

**`scrape_runs` row** (created by `db.insert_scrape_run`):
```json
{
  "source_portal": "data.cityofnewyork.us",
  "status": "RUNNING" → "SUCCESS" | "FAILED",
  "records_scraped": 1234,
  "metadata": {"mode": "daily", "portal": "NYC Open Data — Recent Contract Awards"}
}
```

**`scrape_errors` row** (created by `db.log_scrape_error` on failure):
```json
{
  "run_id": 42,
  "source_portal": "data.cityofnewyork.us",
  "error_message": "...",
  "raw_payload": {"traceback": "..."}
}
```

---

## Architecture

### Package Structure

```
backend/workers/nyc_contract_awards/
├── __init__.py       # empty package marker
├── fetcher.py        # HTTP fetching (daily JSON API + initial CSV load)
├── mapper.py         # Socrata record → 23-field upsert tuple
└── main.py           # CLI entry point + orchestration
```

### Component Diagram

```
main.py (CLI: --mode daily|initial)
    │
    ├── fetcher.fetch_daily_json()     ← aiohttp + Socrata JSON API + pagination
    │       └── filter_2026()
    │
    ├── fetcher.fetch_initial_csv()    ← urllib.request + csv.DictReader (stdlib only)
    │       └── filter_2026()
    │
    └── mapper.map_nyc_row(record)     ← 23-field tuple
            └── db.upsert_opportunities(tuples)
```

---

## Module Design

### `fetcher.py`

Two public async/sync functions, both returning `list[dict]` filtered to 2026 start dates.

#### Daily Mode — `fetch_daily_json(session: aiohttp.ClientSession) -> list[dict]`

- Endpoint: `https://data.cityofnewyork.us/resource/qyyg-4tf5.json`
- Query params: `$limit=1000`, `$offset=0` (increments by 1000 per page)
- Pagination: loop until response length < `$limit`
- Retry: up to 3 attempts on `{429, 500, 502, 503, 504}` with exponential backoff + jitter (`2**attempt + random.uniform(0.1, 1.5)`)
- Headers: `User-Agent: settings.USER_AGENT`
- Timeout: `aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT_SECONDS)`
- After collecting all pages, filter records where `start_date` year == 2026

```python
DAILY_API_URL = "https://data.cityofnewyork.us/resource/qyyg-4tf5.json"
PAGE_LIMIT = 1000
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

async def fetch_daily_json(session: aiohttp.ClientSession) -> list[dict]:
    records = []
    offset = 0
    while True:
        page = await _fetch_page(session, offset)
        records.extend(page)
        if len(page) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT
    return _filter_2026(records)
```

#### Initial Load Mode — `fetch_initial_csv() -> list[dict]`

- Endpoint: `https://data.cityofnewyork.us/api/views/qyyg-4tf5/rows.csv?accessType=DOWNLOAD`
- Uses `urllib.request.urlopen` with `User-Agent` header (stdlib only — no aiohttp)
- Streams response through `io.TextIOWrapper` → `csv.DictReader` (no full-file memory load)
- Raises `RuntimeError(f"CSV download failed: HTTP {code}")` on non-200 status
- Returns list of dicts filtered to 2026 start dates

```python
CSV_URL = "https://data.cityofnewyork.us/api/views/qyyg-4tf5/rows.csv?accessType=DOWNLOAD"

def fetch_initial_csv() -> list[dict]:
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": settings.USER_AGENT})
    with urllib.request.urlopen(req, timeout=600) as resp:
        if resp.status != 200:
            raise RuntimeError(f"CSV download failed: HTTP {resp.status}")
        reader = csv.DictReader(io.TextIOWrapper(resp, encoding="utf-8"))
        return _filter_2026(list(reader))
```

#### `_filter_2026(records: list[dict]) -> list[dict]`

Shared helper used by both modes:

```python
def _filter_2026(records: list[dict]) -> list[dict]:
    result = []
    for r in records:
        dt = _parse_date(r.get("start_date", ""))
        if dt and dt.year == 2026:
            result.append(r)
    return result
```

---

### `mapper.py`

Single public function `map_nyc_row(record: dict) -> tuple` that produces the 23-field tuple matching `OPPORTUNITY_UPSERT_SQL` parameter order.

#### Column Mapping Table

| Position | DB Field | Source | Logic |
|---|---|---|---|
| $1 | `id` | computed | `generate_deterministic_id("data.cityofnewyork.us", request_id)` |
| $2 | `source_portal` | fixed | `"data.cityofnewyork.us"` |
| $3 | `source_record_id` | `request_id` | raw string |
| $4 | `solicitation_number` | `request_id` | same as source_record_id |
| $5 | `portal_region` | fixed | `"City"` |
| $6 | `title` | `short_title` | fallback `"Unknown Contract"` |
| $7 | `description` | `vendor_name` | raw string or None |
| $8 | `notice_type` | `selection_method_description` | raw string |
| $9 | `posted_date` | `start_date` | `_parse_date()` → datetime |
| $10 | `deadline` | `end_date` | `_parse_date()` → datetime |
| $11 | `state_region` | fixed | `"NY"` |
| $12 | `industry` | `category_description` | raw string |
| $13 | `naics_code` | — | `None` |
| $14 | `value_numeric` | `contract_amount` | `_parse_amount()` → float or None |
| $15 | `value_min` | — | `None` |
| $16 | `value_max` | — | `None` |
| $17 | `currency` | fixed | `"USD"` |
| $18 | `status` | computed | `"OPEN"` if end_date >= today else `"CLOSED"` |
| $19 | `buyer_name` | `agency_name` | raw string |
| $20 | `buyer_type` | fixed | `"City"` |
| $21 | `source_url` | computed | `f"https://data.cityofnewyork.us/resource/qyyg-4tf5/{request_id}"` or base URL |
| $22 | `documents` | `document_links` | `_serialize_documents()` → JSON string |
| $23 | `raw_payload` | full record | `json.dumps(record)` |

#### Helper Functions

**`_parse_date(val: str | None) -> datetime | None`**
- Tries ISO 8601 with time component: `datetime.fromisoformat(val.replace("Z", "+00:00"))`
- Falls back to date-only: `datetime.strptime(val[:10], "%Y-%m-%d")`
- Returns `None` on any parse failure

**`_parse_amount(val: str | None) -> float | None`**
- Strips `$`, `,`, whitespace with `re.sub(r"[$,\s]", "", val)`
- Parses with `float()`
- Returns `None` if absent, empty, or unparseable

**`_derive_status(end_date: datetime | None) -> str`**
- Returns `"OPEN"` if `end_date` is None or `end_date >= datetime.today()`
- Returns `"CLOSED"` otherwise

**`_serialize_documents(val: str | None) -> str`**
- If `val` is non-empty: `json.dumps([{"title": "Document", "url": val}])`
- Otherwise: `"[]"`

---

### `main.py`

Orchestration entry point following the exact pattern of `backend/workers/georgia/main.py` and `backend/workers/florida/main.py`.

```python
async def run_nyc_ingestion(mode: str = "daily") -> dict:
    run_id = await db.insert_scrape_run(
        SOURCE_PORTAL,
        metadata={"mode": mode, "portal": "NYC Open Data — Recent Contract Awards"},
    )
    status = "FAILED"
    records_upserted = 0
    error_msg = None

    try:
        if mode == "initial":
            raw_records = fetch_initial_csv()          # sync, stdlib
        else:
            async with aiohttp.ClientSession(...) as session:
                raw_records = await fetch_daily_json(session)

        mapped = [map_nyc_row(r) for r in raw_records]
        records_upserted = await db.upsert_opportunities(mapped)
        status = "SUCCESS"

    except Exception as exc:
        error_msg = str(exc)
        await db.log_scrape_error(run_id, SOURCE_PORTAL, error_msg, ...)

    await db.finalize_scrape_run(run_id, status, records_upserted, ...)
    print(f"Run {run_id} complete: {status} — {records_upserted} records")
    return {"run_id": run_id, "status": status, "records_upserted": records_upserted, "error": error_msg}
```

CLI entry:
```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "initial"], default="daily")
    args = parser.parse_args()
    asyncio.run(_async_main(args.mode))

if __name__ == "__main__":
    main()
```

Executable as: `python -m backend.workers.nyc_contract_awards.main --mode daily`

---

## Data Flow

```
Socrata JSON API / CSV Export
        │
        ▼
fetcher.py  ──── paginate + retry ──── raw list[dict]
        │
        ▼
_filter_2026()  ──── keep only start_date year == 2026
        │
        ▼
mapper.map_nyc_row()  ──── 23-field tuple per record
        │
        ▼
db.upsert_opportunities()  ──── INSERT … ON CONFLICT DO UPDATE
        │
        ▼
opportunities table (PostgreSQL)
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| HTTP 429/5xx from Socrata JSON API | Retry up to 3× with exponential backoff + jitter |
| HTTP 4xx (non-429) from Socrata JSON API | Raise immediately, no retry |
| CSV download non-200 | Raise `RuntimeError("CSV download failed: HTTP {code}")` |
| `start_date` unparseable | Record excluded by `_filter_2026()` |
| `contract_amount` unparseable | `value_numeric = None`, record still upserted |
| Any unhandled exception in `main.py` | `db.log_scrape_error` + `finalize_scrape_run(status="FAILED")` |

---

## CI Integration

Add a new job to `.github/workflows/daily-ingest-all.yml`:

```yaml
nyc-contract-awards:
  name: NYC Contract Awards (Socrata) — daily
  runs-on: ubuntu-latest
  timeout-minutes: 30
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
        cache: 'pip'
        cache-dependency-path: backend/requirements.txt
    - run: pip install -r backend/requirements.txt
    - name: Ingest NYC Contract Awards
      run: python -m backend.workers.nyc_contract_awards.main --mode daily
```

Also add `nyc-contract-awards` to the `verify` job's `needs` array.

No Playwright install step required — this worker uses HTTP APIs only.

---

## Dependencies

No new packages required. Uses only:
- `aiohttp` — already in `backend/requirements.txt` (daily mode)
- `asyncpg` — already in `backend/requirements.txt` (via `backend.core.db`)
- Python stdlib: `urllib.request`, `csv`, `io`, `json`, `datetime`, `re`, `argparse`, `asyncio` (initial load mode)

---

## Property-Based Testing

Key correctness properties to validate:

1. **Filter correctness**: For any record with `start_date` year ≠ 2026, `_filter_2026()` must exclude it. For any record with `start_date` year == 2026, it must be included.
2. **Mapper tuple length**: `map_nyc_row(record)` always returns a tuple of exactly 23 elements.
3. **Amount parsing idempotency**: `_parse_amount("$1,250,000.00")` == `_parse_amount("1250000.00")` == `1250000.0`.
4. **Fingerprint stability**: `map_nyc_row(record)[0]` (the `id`) is identical across two calls with the same `request_id`.
5. **Status derivation**: For any `end_date` in the past, `_derive_status(end_date)` == `"CLOSED"`. For future dates, `"OPEN"`.

---

## Correctness Properties

### Property 1: Filter Completeness
Every record in the output of `_filter_2026()` has `start_date` year == 2026; no record with year ≠ 2026 appears in the output.

**Validates: Requirements 4.3, 4.4**

### Property 2: Tuple Arity
`map_nyc_row(record)` always returns a tuple of exactly 23 elements for any non-empty input dict.

**Validates: Requirements 3.1, 3.2**

### Property 3: Fingerprint Stability
Two calls to `map_nyc_row` with the same `request_id` produce the same value at position $1 (`id`).

**Validates: Requirements 3.3**

### Property 4: Amount Parsing Safety
`_parse_amount` correctly handles `"$1,250,000.00"`, `"1250000"`, `""`, `None`, and non-numeric strings, returning `float` or `None` as appropriate.

**Validates: Requirements 5.1, 5.2, 5.3**

### Property 5: Status Correctness
`_derive_status(end_date)` returns `"CLOSED"` for any `end_date` strictly before today, and `"OPEN"` for any `end_date` on or after today or `None`.

**Validates: Requirements 4.5**

### Property 6: Pagination Termination
`fetch_daily_json` terminates when a page returns fewer than `PAGE_LIMIT` records and does not make an additional request.

**Validates: Requirements 1.2, 1.3**

### Property 7: No Data Loss on Upsert
Every tuple produced by `map_nyc_row` for a 2026 record is passed to `db.upsert_opportunities`; no records are silently dropped between filter and upsert.

**Validates: Requirements 7.2**

---

## Testing Strategy

### Unit Tests (`backend/tests/test_nyc_mapper.py`)

- Test `map_nyc_row` with a complete fixture record — assert all 23 positions.
- Test `_parse_amount` with: `"$1,250,000.00"`, `"0"`, `""`, `None`, `"N/A"`.
- Test `_parse_date` with ISO 8601 with time, date-only, empty string, None.
- Test `_derive_status` with past date, future date, None.
- Test `_serialize_documents` with a URL string, empty string, None.
- Test `_filter_2026` with a mixed list of 2025/2026/2027 records.

### Property-Based Tests (`backend/tests/test_nyc_pbt.py`)

Using `hypothesis`:
- **Tuple arity property**: For any dict with string keys/values, `map_nyc_row` returns a 23-tuple.
- **Filter idempotency**: Applying `_filter_2026` twice yields the same result as once.
- **Amount round-trip**: For any valid float `f`, `_parse_amount(str(f))` == `f`.

### Integration Test (`backend/tests/test_nyc_e2e.py`)

- Mock `aiohttp.ClientSession.get` to return two pages (1000 records + 50 records).
- Assert pagination stops after second page.
- Assert only 2026 records are returned.
- Assert `db.upsert_opportunities` is called with the correct number of tuples.
