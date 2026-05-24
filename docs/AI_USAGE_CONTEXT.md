# AI Usage Context — CHARDI Project A (United States)

> Master documentation of how AI tools were used to design, plan, and build the Chardi.ai government contracts aggregation platform. This document covers the full AI collaboration stack: Gemini Pro Extended, Perplexity, Cursor, and Kiro.

---

## Overview

This project was built using a deliberate multi-AI strategy where each tool played a distinct role. No single AI did everything — instead, each tool was chosen for what it does best, and the outputs were chained together into a working system.

| AI Tool | Primary Role | Phase |
|---------|-------------|-------|
| **Gemini Pro Extended** | Architecture planning, system design, constraint engineering | Phase 1 & 2 planning |
| **Perplexity (Free)** | Research, prompt engineering, planning validation | Pre-build & frontend planning |
| **Cursor (Free Tier)** | Component-level implementation, scraper prototyping | Individual worker builds |
| **Kiro** | Full-project orchestration, multi-worker implementation, debugging, testing | End-to-end execution |

---

## 1. Gemini Pro Extended

### Role in the Project

Gemini Pro Extended was used as the **primary architecture and planning brain** for the entire backend system. It acted as a "10x Staff Engineer sounding board" — not writing code directly, but producing the precise engineering constraints, schema designs, and system prompts that all other tools (especially Kiro) would follow.

### What Gemini Produced

#### Phase 1 — Database Architecture

Gemini designed the full 3-table PostgreSQL schema from scratch:

- **`opportunities`** — the core denormalized table with 24+ columns, JSONB flexibility, and a deterministic SHA-256 primary key strategy
- **`scrape_runs`** — operational lifecycle tracking (start/end time, status, metadata JSONB)
- **`scrape_errors`** — dead-letter log for fault isolation and debugging

Key architectural decisions Gemini made:

- **Deterministic Fingerprint IDs**: Instead of UUIDs or auto-increment, `opportunities.id` is a SHA-256 hash of `portal_name + native_id` (or fallback: `title + buyer + deadline`). This solves Change Data Capture (CDC) — the same contract scraped on different days always produces the same ID, enabling idempotent upserts.
- **`ON CONFLICT (id) DO UPDATE`**: Combined with the fingerprint strategy, this makes the pipeline safe to run 100 times a day without creating duplicates.
- **Explicit SQL type casting**: Gemini identified that `asyncpg` is hyper-strict and will crash if JSON or timestamp strings are not explicitly cast in SQL (`$9::timestamptz`, `$17::jsonb`). This constraint was baked into every worker.

#### Phase 2 — Federal Pipeline (SAM.gov)

Gemini designed the full async ingestion architecture:

- **100% async constraint**: No `requests`, no `psycopg2`, no `time.sleep()`. Only `aiohttp`, `asyncio`, `asyncpg`.
- **Smart 429 Interceptor**: Gemini designed a response handler that distinguishes between a temporary rate limit (retry with backoff) and a hard daily quota lockout (`nextAccessTime` in JSON → `RuntimeError`, abort immediately). This prevented wasting all 1,000 daily API calls on retries.
- **Delta Sync strategy**: Instead of `postedFrom` (which misses updates to old records), use `modifiedFrom` for the current date. This pulls all creations AND updates in 2 requests, staying well under the daily quota.
- **PAGE_LIMIT = 1000**: Gemini identified that the default of 100 was burning the daily quota 10x faster than necessary. Changing to 1000 was the single biggest efficiency fix.
- **Semaphore + backoff outside semaphore**: Retry sleep must happen outside the `async with sem:` block so the concurrency slot is released during the wait.

#### System Prompt Engineering

Gemini produced the full `SYSTEM PROMPT FOR KIRO CODE AGENT` — a structured directive that was injected into Kiro's context to enforce all architectural rules. This included:

- Strict directives (async-only, type-safe SQL, no placeholders, idempotency)
- File structure enforcement
- Phase-by-phase implementation targets
- Exact SQL upsert query with all casts
- Mapper field order table (18 columns, index 0–17)

#### `.cursorrules` Injection

Gemini also produced the `.cursorrules` file content — permanent workspace rules for Cursor that enforced:
- Never use `requests` → use `aiohttp`
- Never pass NaN from Pandas → sanitize to `None`
- Never leave DB queries without explicit date/JSON casts
- Always use `core/db.py` for upserts and run lifecycle
- Always execute Playwright downloads in-memory

#### Execution Architecture Plan

Gemini produced a full 7-phase execution plan covering:
- Phase 3: State portal ingestion (Playwright + PeopleSoft)
- Phase 4: Backend API and search/filter layer
- Phase 5: Frontend dashboard
- Phase 6: Deployment, scheduling, observability
- Phase 7: README, Loom, metrics, demo prep

It also produced a **tool-usage strategy** — which tasks should use Kiro credits vs. free tools, and a **4-day sprint plan** with a compressed 3-day fallback.

### Summary of Gemini's Contribution

Gemini was the **architect**. It never wrote production code directly — it produced the blueprints, constraints, and system prompts that made every other tool's output correct and consistent. Without Gemini's Phase 1 and Phase 2 planning documents, the project would have had no coherent architecture to build against.

---

## 2. Perplexity (Free Version)

### Role in the Project

Perplexity was used for **research, planning validation, and prompt engineering**. It served as a fast, free research layer that complemented Gemini's deeper architectural work.

### What Perplexity Produced

#### Frontend Planning & Design System

Perplexity produced the full frontend design specification — a detailed prompt engineering document that defined:

**Design Language:**
- Warm off-white backgrounds (`#FFFBF7`, `#F7F3F2`)
- Near-black text (`#1F1A17`, `#1A0D0A`)
- Single coral/amber accent (`#F59E0B`, `#EA580C`)
- Playfair Display for editorial headings, Inter for UI/data
- Generous whitespace, subtle shadows, no loud gradients

**Tech Stack Decisions:**
- Next.js 14 with App Router
- TypeScript
- Tailwind CSS with semantic CSS variables
- shadcn/ui with CSS variable theming
- Server Components by default, `use client` only for interactive islands

**Mobile-First UX Rules:**
- Sidebar collapses below `md` breakpoint
- Mobile navigation uses Sheet/Drawer
- Filters become full-screen modal on mobile
- Contract data renders as cards on mobile, table on desktop
- Touch-friendly targets, no hover-only interactions

**Screens Defined:**
1. Root App Layout (sticky header, responsive shell)
2. Dashboard Home (KPIs, recent contracts, trends placeholder)
3. Contracts Explorer (search, filters, mobile cards, desktop table)
4. Contract Detail View (metadata blocks, attachments, responsive stacking)
5. Shared States (empty, loading skeletons, error, no-results)

**Component Customization Rules:**
- Button: `rounded-lg`, coral primary, outline variant
- Input: warm surface, coral focus ring
- Card: `rounded-xl`, subtle border, generous padding
- Table: no noisy gridlines, `border-b` separators, quiet hover
- Badges: restrained pills, coral for active state only

#### Prompt Engineering with Gemini

Perplexity was used to **refine and validate prompts** before feeding them to Gemini. This created a feedback loop:
1. Draft a system prompt or architectural question
2. Run it through Perplexity to check for gaps or ambiguities
3. Refine the prompt
4. Feed the refined version to Gemini for deep architectural output

#### Planning Validation

Perplexity was used to quickly validate decisions like:
- Is `asyncpg` actually strict about type casting? (confirmed)
- What is the SAM.gov daily quota limit? (confirmed 1,000 requests)
- Does Socrata's CSV export API work without authentication? (confirmed for Chicago, NYC)
- What is the `__NEXT_DATA__` pattern in Next.js pages? (confirmed for Florida DMS)

#### `.cursorrules` Content

Perplexity helped produce the Cursor rules file content, defining the design aesthetic and component rules that Cursor would follow when building the frontend.

### Summary of Perplexity's Contribution

Perplexity was the **research and validation layer**. It was fast, free, and good at confirming facts, finding API patterns, and helping refine prompts before they went to more expensive tools. It owned the frontend design specification and served as a prompt engineering partner for Gemini.

---

## 3. Cursor (Free Tier)

### Role in the Project

Cursor was used for **individual component implementation** — building single, self-contained scrapers and workers in isolation before they were integrated into the master project. It was the "build one thing at a time" tool.

### What Cursor Built

#### Individual Scraper Prototypes

Cursor built each state/city scraper as a standalone, independently runnable script. Each scraper came with a detailed `MASTER_PLAN.md` that documented the full architecture, API discovery, optimizations, and QA checklist. These master plans were then handed to Kiro for integration.

**Chicago Data Portal Scraper (`chicago/`)**
- Target: Chicago City Contracts dataset (185,175 rows, ~48.6 MB)
- Discovery: The UI "Export → CSV" button is just a wrapper around the Socrata CSV API
- Solution: Direct `GET /api/views/rsxa-ify5/rows.csv?accessType=DOWNLOAD` — no Selenium needed
- Stack: Python stdlib only (`urllib`, `json`, `csv`)
- Speed: ~55 seconds for full download
- Cursor produced the full working `scrape_chicago_contracts.py` with CLI flags, metadata snapshot, and optional date filtering

**Illinois BidBuy Scraper (`illinois/`)**
- Target: Illinois BidBuy open bid solicitations (~186 rows)
- Challenge: JSF (JavaServer Faces) site — table and CSV export load via JavaScript
- Solution: Selenium + Chrome with `download.default_directory` prefs, JavaScript click on CSV export icon
- Stack: Python + Selenium + webdriver-manager
- Cursor produced the full working `scrape_bidbuy_csv.py` with headless/headed modes, exit codes, and overlay dismissal

**Florida DMS Scraper (`florida/`)**
- Target: Florida state contracts and agreements (147 contracts)
- Discovery: The paginated UI is fake — the `search_contracts` API returns all rows in one request
- Solution: Direct API call + parallel `ThreadPoolExecutor` for detail pages
- Stack: Python stdlib only
- Speed: ~2s for list, ~25s for full details with `--skip-archive`
- Cursor produced the full working `scrape_florida_contracts.py` with parallel detail fetching and `__NEXT_DATA__` JSON parsing

**NYC Open Data Scraper (`nyc_contract_awards/`)**
- Target: NYC Recent Contract Awards (~52k rows, ~35 MB)
- Solution: Socrata metadata API + file attachment download + CSV export stream
- Stack: Python stdlib only
- Speed: ~73s for full download including XLSX data dictionary

#### Master Plan Documents

For each scraper, Cursor produced a detailed `MASTER_PLAN.md` that included:
- Problem definition (what the user sees manually vs. what we automate)
- Architecture flowchart (Mermaid)
- API reference (discovered endpoints, response shapes)
- Optimization table (why this approach is faster than Selenium)
- Full working code
- CLI reference
- Step-by-step execution walkthrough
- QA checklist
- One-command reproduction
- **Kiro Agent Instructions** — a paste-ready prompt for handing the scraper to Kiro for integration

#### Turning One Component Into a Master Plan

The key workflow with Cursor was:
1. Build one scraper in isolation (e.g., Chicago)
2. Verify it works end-to-end
3. Document it as a `MASTER_PLAN.md`
4. Hand the master plan to Kiro for integration into the main project

This "single component → master plan → Kiro" pipeline was the core execution strategy.

### Debugging and Information Gathering

Cursor was also used for:
- Manual debugging of individual scrapers
- Researching portal-specific quirks (PeopleSoft date validation, Socrata API patterns)
- Generating test fixtures and smoke test scripts
- Producing the `.cursorrules` file that enforced architectural consistency

### Summary of Cursor's Contribution

Cursor was the **component builder**. It built each scraper in isolation, proved it worked, and documented it thoroughly. It was used strategically on the free tier — one component at a time, with clear scope, to avoid wasting requests on broad multi-file tasks. The master plans it produced became the handoff artifacts for Kiro.

---

## 4. Kiro

### Role in the Project

Kiro was the **full-project orchestrator and implementer**. It took all the plans from Gemini and the master plans from Cursor and implemented the entire integrated project. Kiro handled multi-file, multi-worker tasks that would have been too broad for Cursor's free tier.

### What Kiro Built

#### Full Project Scaffold

Kiro created the entire repository structure from scratch based on Gemini's architecture plan:

```
/backend
  /core
    db.py               # Shared asyncpg pool & UPSERT execution
    fingerprint.py      # Deterministic SHA-256 ID generator
    settings.py         # Environment variable management
  /workers
    /samgov             # Federal SAM.gov pipeline
    /california         # Playwright + Excel interception
    /texas              # State portal worker
    /newyork            # NY state portal worker
    /chicago            # Socrata CSV API worker
    /illinois           # BidBuy Selenium worker
    /florida            # DMS API + parallel detail worker
    /georgia            # State portal worker
    /virginia           # EVA portal scraper
    /nyc_contract_awards # NYC Open Data worker
  /tests
    test_fingerprint.py
    test_samgov_mapper.py
    test_texas_mapper.py
    test_california_e2e.py
    fixtures/
/frontend
  (Next.js 14 dashboard)
/database/migrations
/.github/workflows
  daily-ingest-all.yml
```

#### Phase 2 — SAM.gov Federal Pipeline

Kiro implemented the full SAM.gov ingestion pipeline following Gemini's exact specifications:

- `core/fingerprint.py` — deterministic SHA-256 ID generation with fallback strategy
- `core/db.py` — asyncpg pool, `insert_scrape_run`, `finalize_scrape_run`, `log_scrape_error`, `upsert_opportunities` with explicit `::timestamptz` and `::jsonb` casts
- `core/settings.py` — environment variable management
- `samgov/mapper.py` — pure JSON-to-tuple transformation with `sanitize_date()` helper
- `samgov/fetcher.py` — aiohttp client, `Semaphore(5)`, 5-retry loop, jittered backoff, Smart 429 Interceptor, Delta Sync
- `samgov/main.py` — full run lifecycle orchestrator with `asyncio.gather`, error counting, `SUCCESS/PARTIAL_SUCCESS/FAILED` status

#### Phase 3 — State Portal Workers

Kiro integrated all the Cursor-built scrapers into the main project architecture, adapting each one to:
- Use `core/db.py` for upserts (not standalone CSV output)
- Use `core/fingerprint.py` for deterministic IDs
- Follow the run lifecycle pattern (scrape_runs + scrape_errors)
- Use the canonical opportunities schema

**California (Playwright + PeopleSoft)**
- Async Playwright with `expect_download()` stream interception
- Excel file read via `temp_file_path` into Pandas (no local file save)
- Explicit date bounds to avoid PeopleSoft "Date Out of Range" errors
- `pd.isna(val)` → `None` to prevent asyncpg NaN crashes

**Virginia (EVA Portal)**
- `eva_scraper.py` — custom scraper for Virginia's EVA procurement portal

**All Other States**
- Chicago, Illinois, Florida, Georgia, New York, NYC Contract Awards — each integrated with the shared core

#### Frontend Dashboard

Kiro built the full Next.js 14 frontend following Perplexity's design specification:
- App Router with Server Components by default
- Tailwind CSS with semantic CSS variables in `globals.css`
- shadcn/ui with CSS variable theming
- Warm palette (off-white backgrounds, coral accent, near-black text)
- Mobile-first: cards on mobile, table on desktop
- Filter drawer/sheet on mobile
- `contracts-explorer.tsx` — the main contracts browsing component
- Responsive layout with sticky header

#### GitHub Actions — Daily Ingestion

Kiro set up `.github/workflows/daily-ingest-all.yml` — a scheduled workflow that runs all workers daily to keep the database fresh.

#### Testing

Kiro built and ran the test suite:
- `test_fingerprint.py` — deterministic ID stability, fallback mode
- `test_samgov_mapper.py` — tuple shape, ID generation, status mapping, buyer extraction
- `test_texas_mapper.py` — Texas-specific mapper tests
- `test_california_e2e.py` — end-to-end California scraper test
- `fixtures/samgov_notice_sample.json` — realistic SAM.gov notice fixture

#### Debugging and Human Evaluation

A significant portion of Kiro's work was **manual debugging and iteration**:
- Fixing asyncpg type casting errors discovered during real runs
- Debugging Playwright download interception on different portal behaviors
- Fixing NaN-to-None sanitization gaps in Pandas mappers
- Resolving PeopleSoft date validation traps
- Iterating on the Smart 429 Interceptor logic
- Testing and validating scrape run lifecycle tracking
- Human evaluation of scraped data quality

### How Kiro Was Used Strategically

Kiro was given **complete, well-specified plans** before being asked to implement anything. The workflow was:

1. Gemini produces architecture + system prompt
2. Perplexity validates and refines
3. Cursor builds individual components + master plans
4. Kiro receives the full context and implements the integrated system

This meant Kiro spent its credits on **implementation**, not on figuring out architecture. Every Kiro session started with a clear spec.

### Summary of Kiro's Contribution

Kiro was the **multi-tasker and integrator**. It took all the plans, master plans, and system prompts from the other tools and turned them into a working, integrated project. It handled the full project scaffold, all backend workers, the frontend, GitHub Actions, and the test suite. It also did the heavy lifting of debugging, testing, and human evaluation that no amount of planning can replace.

---

## AI Collaboration Flow

```
Gemini Pro Extended
  ↓ Architecture, constraints, system prompts, SQL schema
  ↓ Phase 1 DB design, Phase 2 SAM.gov spec, .cursorrules

Perplexity (Free)
  ↓ Research validation, prompt engineering, frontend design spec
  ↓ Confirms API patterns, refines prompts before Gemini

Cursor (Free Tier)
  ↓ Individual scraper prototypes (Chicago, Illinois, Florida, NYC)
  ↓ MASTER_PLAN.md for each scraper → handoff artifacts for Kiro

Kiro
  ↓ Full project scaffold, all workers integrated, frontend built
  ↓ Debugging, testing, human evaluation, GitHub Actions
  ↓ Working deployed product with real data
```

---

## Key AI-Assisted Engineering Decisions

| Decision | AI Source | Impact |
|----------|-----------|--------|
| SHA-256 deterministic IDs | Gemini | Solved CDC / deduplication permanently |
| `ON CONFLICT DO UPDATE` upsert pattern | Gemini | Idempotent pipeline, safe to run daily |
| Explicit `::timestamptz` / `::jsonb` SQL casts | Gemini | Prevented all asyncpg type crashes |
| Smart 429 Interceptor (quota vs. rate limit) | Gemini | Prevented wasting daily API quota on retries |
| Delta Sync (`modifiedFrom` not `postedFrom`) | Gemini | Captures updates to old records, not just new ones |
| PAGE_LIMIT = 1000 (not 100) | Gemini | 10x reduction in API calls per run |
| Playwright `expect_download()` in-memory | Gemini | No local file I/O, no blocking |
| PeopleSoft explicit date bounds | Gemini | Bypassed "Date Out of Range" UI validation |
| `pd.isna()` → `None` sanitization | Gemini | Prevented NaN crashes in asyncpg |
| Socrata CSV API (not Selenium Export click) | Cursor/Perplexity | 55s vs. minutes for Chicago/NYC |
| `__NEXT_DATA__` JSON parsing for Florida | Cursor | No BeautifulSoup needed, pure stdlib |
| ThreadPoolExecutor for Florida details | Cursor | ~25s vs. 10+ min sequential |
| Mobile-first card/table dual rendering | Perplexity | Demo-ready on phone |
| Semantic CSS variables in globals.css | Perplexity | Consistent theming without scattered overrides |
| Server Components by default | Perplexity | Minimal client-side JS bundle |

---

## Honest Assessment

This project was built with heavy AI assistance, but it required significant **human judgment** throughout:

- Deciding which AI tool to use for which task
- Evaluating the quality of AI-generated plans before committing to them
- Manual debugging when AI-generated code hit real-world edge cases
- Human evaluation of scraped data quality
- Making scope decisions (what to build vs. defer)
- Integrating outputs from four different AI tools into a coherent system

The AI tools were multipliers, not replacements. The architecture is sound because Gemini was given precise constraints. The scrapers work because Cursor was given focused, single-component tasks. The integrated project exists because Kiro was given complete, well-specified plans. And all of it was validated because a human was in the loop at every step.

---

*Document generated: May 23, 2026*
*Project: Chardi.ai Trial Project A — United States Government Contracts*
