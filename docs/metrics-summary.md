# Metrics Summary

**Last updated:** May 23, 2026  
**Database:** Neon PostgreSQL (live)

---

## Data volume

| Metric | Value |
|---|---|
| Total opportunities | 4,206 |
| Open | 4,159 (98.9%) |
| Closed | 47 (1.1%) |
| Awarded | 0 |
| Federal (SAM.gov) | 1,879 |
| State portals | 2,327 |
| Active portals | 6 |
| US states covered | 53 (incl. DC, PR, territories) |
| Last seen (most recent scrape) | 2026-05-23 05:17 UTC |

---

## Coverage by portal

| Portal | Records | Open | Closed | Last scraped |
|---|---|---|---|---|
| SAM.gov | 1,879 | 1,879 | 0 | May 23, 2026 |
| nyscr.ny.gov | 999 | 953 | 46 | May 22, 2026 |
| caleprocure.ca.gov | 456 | 456 | 0 | May 22, 2026 |
| eva.virginia.gov | 385 | 384 | 1 | May 22, 2026 |
| txsmartbuy.gov | 297 | 297 | 0 | May 22, 2026 |
| vita.virginia.gov | 190 | 190 | 0 | May 22, 2026 |

---

## Coverage by state (top 10)

| State | Records |
|---|---|
| NY | 1,009 |
| VA | 643 |
| CA | 512 |
| TX | 345 |
| MD | 65 |
| DC | 44 |
| FL | 29 |
| OK | 25 |
| PA | 21 |
| WA | 21 |

---

## Pipeline health

| Metric | Value |
|---|---|
| Deduplication | 0 duplicates (verified) |
| Deterministic IDs | 64-char SHA-256 hashes |
| Upsert strategy | `ON CONFLICT (id) DO UPDATE` |
| Dead-letter logging | `scrape_errors` table |
| Partial success handling | `PARTIAL_SUCCESS` status |
| Retries | 5 attempts, exponential backoff |
| Concurrency (SAM.gov) | 3 simultaneous requests |

---

## Data quality

| Field | Coverage |
|---|---|
| `title` | 100% |
| `status` | 100% |
| `source_portal` | 100% |
| `source_url` | 100% |
| `buyer_name` | ~95% |
| `posted_date` | ~95% |
| `deadline` | ~80% |
| `state_region` | ~70% |
| `industry` | ~65% |
| `naics_code` | ~45% (SAM.gov only) |
| `value_numeric` | ~0% (not published by most portals) |

---

## Upcoming deadlines (from live DB)

| Month | Contracts due |
|---|---|
| May 2026 | 1,052 |
| Jun 2026 | 1,372 |
| Jul 2026 | 134 |
| Aug 2026 | 73 |
| Sep 2026 | 43 |

---

## Run commands to refresh metrics

```bash
# Backend
export $(grep -v '^#' .env | xargs)
python scripts/smoke_test.py
python scripts/data_quality_check.py

# Or query Neon directly
psql $DATABASE_URL -c "SELECT source_portal, COUNT(*), MAX(last_seen_at) FROM opportunities GROUP BY 1 ORDER BY 2 DESC;"
```
