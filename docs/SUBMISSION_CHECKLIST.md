# Submission Checklist — Chardi Contracts (Project A · United States)

## Deliverables required by brief

- [x] **Live deployed URL** — https://chardi-contracts.vercel.app
- [x] **GitHub repo** — https://github.com/Janu-Chaudhary/chardi-contracts
- [x] **README** — setup, architecture, schema, portal coverage, AI usage notes
- [x] **Metrics summary** — `docs/metrics-summary.md`
- [ ] **Loom walkthrough** — 5–10 min video (record before submission)
- [ ] **Share repo with Aaryan** — add as collaborator on GitHub

---

## README checklist

- [x] Setup instructions (backend + frontend)
- [x] Architecture diagram (ASCII + component table)
- [x] Schema docs (all 3 tables, upsert behavior, parameter order)
- [x] Portal coverage (11 portals, field mapping per portal)
- [x] AI usage notes (tools, what was built, key prompts)
- [x] API route reference
- [x] Environment variables
- [x] Data coverage table (live numbers)
- [x] Running tests

---

## Demo prep checklist

- [ ] Verify live site loads: https://chardi-contracts.vercel.app
- [ ] Confirm 10,735 contracts showing in KPI cards
- [ ] Test search ("cloud", "construction", "IT")
- [ ] Test filters (state → CA, status → OPEN, deadline range)
- [ ] Test CSV download
- [ ] Test JSON download
- [ ] Test contract detail page → source URL opens
- [ ] Test mobile view (resize browser or use phone)
- [ ] Test Trends page — chart tooltip on hover
- [ ] Prepare 2–3 AI workflow examples to show live

---

## Loom walkthrough outline (5–10 min)

1. **Overview page** (1 min) — KPI cards, analytics charts, recent contracts
2. **Contracts page** (2 min) — search, filter, sort, export CSV/JSON
3. **Contract detail** (1 min) — full metadata, source URL
4. **Trends page** (1 min) — volume chart, deadline chart
5. **Architecture** (2 min) — repo structure, worker pattern, DB schema
6. **AI workflow** (1 min) — show 1–2 real Kiro conversations that fixed bugs
7. **GitHub Actions** (30 sec) — show daily cron workflow

---

## One-page metrics summary

See `docs/metrics-summary.md` — print or screenshot for the demo.

---

## What's done vs not done

### Done ✅
- 11 portals scraped (1 federal + 10 state/city)
- 10,735 contracts in live DB
- Daily GitHub Actions cron
- Full-text search, 7 filters, sort, pagination
- CSV + JSON export with filters
- 3 chart types (by portal, by state, trend over time)
- Mobile-responsive
- Contract detail pages
- Deterministic IDs, deduplication, dead-letter logging
- Graceful degradation (PARTIAL_SUCCESS)

### Limitations (documented per brief ground rules)
- eVA Virginia: portal blocks CI IPs (403) — documented, graceful skip
- Florida DMS: historical/closed contracts only (no active tender feed)
- Illinois BidBuy: requires registration for full access
- Pennsylvania, Ohio, North Carolina: require vendor registration
- value_numeric: not published by most portals (~0% coverage)
- SAM.gov backfill: Apr 14–May 14 in progress (quota-limited, ~10 days/day)
