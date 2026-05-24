# AI Usage Notes

> How AI tools were used to design, plan, and build Chardi Contracts. This is not a summary — it is a precise account of which tool did what, why, and what it produced.

---

## The Strategy: Human-Orchestrated Heterogeneous AI Pipeline

This project was not built by one AI. It was built by a human acting as the **routing layer** between five specialized AI tools, each assigned to what it does best. The outputs were chained forward — each tool's artifact became the next tool's input.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HUMAN (Orchestrator)                             │
│  Makes every routing decision · Evaluates every output             │
│  Decides scope · Debugs failures · Validates data quality          │
└──────┬──────────────┬──────────────┬──────────────┬────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
  Gemini Pro     Perplexity      Manus AI        Cursor
  Extended       (Free)                          (Free Tier)
       │              │              │              │
       │ Architecture │ Research &   │ UI/UX        │ Component
       │ constraints  │ validation   │ design spec  │ prototypes
       │ System prompt│ Prompt eng.  │ Palette      │ MASTER_PLANs
       │ SQL schema   │ Frontend     │ Typography   │
       │ SAM.gov spec │ design input │ Components   │
       └──────────────┴──────────────┴──────────────┘
                              │
                              ▼
                           Kiro
                    Full-project integrator
                    All 15 workers · Frontend
                    Award enrichment feature
                    GitHub Actions · Debugging
                    URL filter persistence
                    Responsive layout fixes
```

---

## 1. Gemini Pro Extended — Architect

**Role:** Primary architecture and planning brain for the entire backend.

**What it produced:**

### Database Architecture (Phase 1)
- Full 3-table PostgreSQL schema (`opportunities`, `scrape_runs`, `scrape_errors`)
- **Deterministic SHA-256 fingerprint IDs** — `SHA-256(portal + source_record_id)` — solving Change Data Capture permanently. Same contract scraped on different days always produces the same ID.
- `ON CONFLICT (id) DO UPDATE` upsert pattern — idempotent pipeline, safe to run 100× daily
- Explicit `::timestamptz` and `::jsonb` SQL casts — asyncpg is hyper-strict and crashes without them

### SAM.gov Federal Pipeline (Phase 2)
- **Smart 429 Interceptor** — distinguishes temporary rate limit (retry with backoff) from hard daily quota lockout (`nextAccessTime` in JSON → `RuntimeError`, abort immediately). Prevented burning all 1,000 daily API calls on retries.
- **Delta Sync** — use `modifiedFrom` (not `postedFrom`) to capture both new records and updates to existing ones in 2 requests
- **PAGE_LIMIT = 1000** — changed from default 100, 10× reduction in API calls per run
- **Semaphore + backoff outside semaphore** — retry sleep must happen outside `async with sem:` to release the concurrency slot during wait

### System Prompt Engineering
Gemini produced the full `SYSTEM PROMPT FOR KIRO CODE AGENT` — a structured directive injected into Kiro's context enforcing all architectural rules: async-only, type-safe SQL, no placeholders, idempotency, file structure, phase targets.

### `.cursorrules` File
Permanent workspace rules for Cursor: never use `requests`, never pass NaN from Pandas, always use `core/db.py`, always execute Playwright downloads in-memory.

---

## 2. Perplexity — Research & Validation

**Role:** Fast research layer, prompt engineering partner, planning validator.

**What it produced:**

### Research Validation
- Confirmed asyncpg type strictness (no ISO strings for timestamps)
- Confirmed SAM.gov daily quota limit (1,000 requests)
- Confirmed Socrata CSV export API works without auth (Chicago, NYC)
- Confirmed `__NEXT_DATA__` pattern in Next.js pages (Florida DMS)

### Prompt Engineering Loop
1. Draft architectural question or system prompt
2. Run through Perplexity to check for gaps
3. Refine the prompt
4. Feed refined version to Gemini for deep output

This loop improved Gemini output quality significantly — Perplexity caught ambiguities before they became architectural mistakes.

### Frontend Design Input
Perplexity contributed to the frontend design specification — confirming tech stack choices (Next.js 14, App Router, shadcn/ui, Tailwind CSS variables), mobile-first UX patterns, and Server Component architecture.

---

## 3. Manus AI — UI/UX Designer

**Role:** Full UI/UX design specification for the frontend.

**What it produced:**

### Design Language
- **Palette:** Warm off-white backgrounds (`#FFFBF7`, `#F7F3F2`), near-black text (`#1F1A17`, `#1A0D0A`), single coral/amber accent (`#F59E0B`, `#EA580C`)
- **Typography:** Playfair Display for editorial headings (H1–H3), Inter for all UI/data text
- **Geometry:** `rounded-lg` (8px) for inputs/buttons, `rounded-xl` (12px) for cards
- **Shadow:** `0 1px 2px 0 rgba(0,0,0,0.03)` — subtle, not loud
- **Density:** Generous whitespace, no enterprise-dashboard clutter

### Component Customization Rules
- **Button:** `rounded-lg`, coral primary, outline variant with warm border
- **Input:** Warm surface, coral focus ring, excellent placeholder contrast
- **Card:** `rounded-xl`, subtle border, warm background, generous padding
- **Table:** No noisy gridlines, `border-b` separators, quiet hover, tabular numeric alignment
- **Badge:** Restrained pills, coral for active state only, neutral for others

### Mobile-First UX Rules
- Sidebar collapses below `md` breakpoint
- Mobile navigation uses Sheet/Drawer
- Filters become full-screen modal on mobile
- Contract data renders as cards on mobile, table on desktop
- Touch-friendly targets, no hover-only interactions
- Sticky top search/actions

### Screens Defined
1. Root App Layout (sticky header, responsive shell)
2. Dashboard Home (KPIs, recent contracts, trends)
3. Contracts Explorer (search, filters, mobile cards, desktop table)
4. Contract Detail View (metadata blocks, attachments, responsive stacking)
5. Shared States (empty, loading skeletons, error, no-results)

### Design Reference
Manus AI referenced Linear, Vercel, and Stripe Dashboard as the design bar — premium and restrained, not generic SaaS.

---

## 4. Cursor — Component Builder

**Role:** Individual scraper prototypes with MASTER_PLAN.md handoff artifacts.

**What it built:**

### Chicago Data Portal Scraper
- **Discovery:** The UI "Export → CSV" button is a wrapper around the Socrata CSV API
- **Solution:** Direct `GET /api/views/rsxa-ify5/rows.csv?accessType=DOWNLOAD` — no Selenium
- **Speed:** ~55 seconds for 185k rows (vs. minutes with Selenium)
- **Output:** Full working `scrape_chicago_contracts.py` + MASTER_PLAN.md

### Illinois BidBuy Scraper
- **Challenge:** JSF (JavaServer Faces) site — table and CSV export load via JavaScript
- **Solution:** Selenium + Chrome with `download.default_directory` prefs, JavaScript click on CSV export icon
- **Output:** Full working `scrape_bidbuy_csv.py` + MASTER_PLAN.md

### Florida DMS Scraper
- **Discovery:** The paginated UI is fake — `search_contracts` API returns all rows in one request
- **Solution:** Direct API call + `ThreadPoolExecutor` for detail pages
- **Speed:** ~2s for list, ~25s for full details
- **Key technique:** `__NEXT_DATA__` JSON parsing — no BeautifulSoup needed
- **Output:** Full working `scrape_florida_contracts.py` + MASTER_PLAN.md

### NYC Open Data Scraper
- **Solution:** Socrata metadata API + file attachment download + CSV export stream
- **Speed:** ~73s for full download
- **Output:** Full working scraper + MASTER_PLAN.md

### MASTER_PLAN.md Format
Each master plan contained:
- Problem definition (manual vs. automated)
- Architecture flowchart (Mermaid)
- API reference (discovered endpoints, response shapes)
- Optimization table (why this approach beats Selenium)
- Full working code
- CLI reference
- QA checklist
- **Kiro Agent Instructions** — paste-ready prompt for integration handoff

---

## 5. Kiro — Integrator & Executor

**Role:** Full-project orchestration, integration, debugging, and iteration.

**What it built:**

### Full Project Scaffold
Repository structure, all shared core modules (`db.py`, `fingerprint.py`, `settings.py`), all 15 workers integrated to the shared core, frontend dashboard, GitHub Actions cron.

### Award Enrichment Feature (New)
- `award_winners` materialized table — 18,212 vendor-industry rows, 3 indexes
- `refresh_award_winners(source_portal)` in `db.py` — called automatically after each worker upsert
- `GET /api/opportunities/[id]/winners` — 2 indexed lookups, <10ms, 1hr CDN cache
- `WinnersSidebar` client component — lazy loaded, skeleton state, medal rank icons

### URL-Based Filter Persistence (New)
- All filters + page + sort synced to URL search params via `router.replace()`
- State initialized from URL on mount — back button restores exact filter state
- Filters are now shareable/bookmarkable

### Responsive Layout Fixes (New)
- Mobile-first layout: no grid on mobile, `lg:grid` only at 1024px+
- All cards: `w-full overflow-hidden min-w-0`
- `[overflow-wrap:anywhere]` on long URLs and Record IDs
- Premium custom scrollbar (4px, warm-toned, webkit + Firefox)

### Chart Improvements (New)
- Both charts: tooltip anchored to bar top (not chart top)
- Chart 2 (DeadlineTrendChart): converted to client component with full interactive tooltip
- Unified bar color and hover behavior across both charts

### Debugging & Human Evaluation
- Fixed asyncpg type casting errors in real runs
- Debugged Playwright download interception across portal behaviors
- Fixed NaN-to-None sanitization gaps in Pandas mappers
- Resolved PeopleSoft date validation traps
- Iterated on Smart 429 Interceptor logic
- Validated scraped data quality across all 15 portals

---

## Key AI-Assisted Engineering Decisions

| Decision | AI Source | Impact |
|----------|-----------|--------|
| SHA-256 deterministic IDs | Gemini | Solved CDC / deduplication permanently |
| `ON CONFLICT DO UPDATE` upsert | Gemini | Idempotent pipeline, safe to run daily |
| Explicit `::timestamptz` / `::jsonb` SQL casts | Gemini | Prevented all asyncpg type crashes |
| Smart 429 Interceptor | Gemini | Prevented wasting daily API quota on retries |
| Delta Sync (`modifiedFrom`) | Gemini | Captures updates to old records, not just new |
| PAGE_LIMIT = 1000 | Gemini | 10× reduction in API calls per run |
| Playwright `expect_download()` in-memory | Gemini | No local file I/O, no blocking |
| PeopleSoft explicit date bounds | Gemini | Bypassed "Date Out of Range" UI validation |
| `pd.isna()` → `None` sanitization | Gemini | Prevented NaN crashes in asyncpg |
| Socrata CSV API (not Selenium) | Cursor | 55s vs. minutes for Chicago/NYC |
| `__NEXT_DATA__` JSON parsing for Florida | Cursor | No BeautifulSoup, pure stdlib |
| ThreadPoolExecutor for Florida details | Cursor | ~25s vs. 10+ min sequential |
| Warm palette + Playfair/Inter typography | Manus AI | Premium editorial feel, not generic SaaS |
| Mobile-first card/table dual rendering | Manus AI | Demo-ready on phone |
| Semantic CSS variables in globals.css | Manus AI | Consistent theming without scattered overrides |
| award_winners pre-aggregation | Kiro | <10ms enrichment vs. 100ms+ live scan |
| URL-based filter persistence | Kiro | Back button restores exact filter state |
| Bar-anchored chart tooltips | Kiro | Tooltip follows bar height, not chart top |

---

## Honest Assessment

Heavy AI assistance, but significant human judgment throughout:

- Deciding which AI tool to use for which task
- Evaluating quality of AI-generated plans before committing
- Manual debugging when AI-generated code hit real-world edge cases
- Human evaluation of scraped data quality across 15 portals
- Making scope decisions (what to build vs. defer)
- Integrating outputs from five different AI tools into a coherent system

The AI tools were multipliers, not replacements. The architecture is sound because Gemini received precise constraints. The scrapers work because Cursor had focused, single-component scope. The UI looks premium because Manus AI produced a complete design system. The integrated project exists because Kiro received complete, well-specified plans. All of it was validated because a human was in the loop at every step.

---

*Document updated: May 24, 2026*  
*Project: Chardi.ai Trial Project A — United States Government Contracts*
