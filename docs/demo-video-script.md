# 🎬 CHARDI Contracts — Demo Loom Video Plan

**Target: 7–9 minutes | Professional, investor/recruiter-grade**

---

## PRE-RECORDING SETUP

Before you hit record:
- Open the live site: `chardi-contracts.vercel.app`
- Have the GitHub repo open in another tab
- Have VS Code open with the project (for the architecture moment)
- Browser zoom at 100%, clean desktop, no notifications
- Record at 1920×1080

---

## SEGMENT 1 — THE HOOK (0:00–0:45)

**What's on screen:** Live dashboard, Overview page

**What you say:**

> "Government procurement is a $700 billion market. Every day, thousands of contracts get posted across federal, state, and city portals — SAM.gov, state procurement sites, county data portals. The problem? They're all different. Different formats, different APIs, different update schedules. Nobody has aggregated them into one searchable place.
>
> This is Chardi Contracts. One hundred and twenty-nine thousand opportunities. Fifteen portals. Updated every single day. Let me show you how it works."

**Why this works:** Opens with market context, names the real pain, then immediately shows the product. No fluff.

---

## SEGMENT 2 — THE OVERVIEW DASHBOARD (0:45–2:00)

**What's on screen:** Overview / dashboard page — KPI cards, charts

**What you say:**

> "The dashboard gives you the full picture at a glance. Right now we're tracking a hundred and twenty-nine thousand opportunities — fourteen thousand of those are currently open and accepting bids. We cover fifteen portals: one federal, multiple state, and city-level portals.
>
> These KPI cards update daily. The data you're seeing right now was ingested this morning.
>
> Scroll down and you get the trends view — monthly posting volume, open versus closed, and upcoming deadlines. These charts are fully interactive. Hover over any bar and you get the exact count. Toggle the legend to isolate open or closed contracts.
>
> This is built on Next.js 16 with server components — the page loads in under a second because the data is pre-fetched at the edge."

**Why this works:** Establishes scale immediately, shows the product is live and current, demonstrates interactivity.

---

## SEGMENT 3 — CONTRACTS EXPLORER (2:00–3:45)

**What's on screen:** Contracts page — search, filter, table

**What you say:**

> "Now the core feature — the Contracts Explorer. Every opportunity from every portal, in one searchable table.
>
> Let me search for something specific — I'll type 'cloud infrastructure'."

*[Type it, pause for results]*

> "Instant results. Full-text search across titles and descriptions. Now let me layer on a filter — I'll narrow to federal only, SAM.gov."

*[Apply the SAM.gov portal filter]*

> "Now I'm looking at only federal cloud infrastructure opportunities. I can also filter by state, by status — open or awarded — and by deadline range. Every filter I apply updates the URL. Watch the address bar."

*[Apply one more filter, point to URL]*

> "That URL is shareable. If I send this link to a colleague, they land on the exact same filtered view. The back button also restores your state — no lost context.
>
> The table is sortable — click any column header. On mobile this switches to a card layout automatically."

**Why this works:** Shows the product's core value prop in action. The URL persistence detail signals engineering maturity.

---

## SEGMENT 4 — CONTRACT DETAIL + THE KILLER FEATURE (3:45–5:30)

**What's on screen:** Click into a specific contract → detail page with WinnersSidebar

**What you say:**

> "Click any contract and you get the full detail view — title, buyer, deadline, description, portal source, status.
>
> But here's the feature I'm most proud of. On the right side — 'Who has won similar?'"

*[Pause, let the sidebar load]*

> "This is award enrichment. For this contract, the system has automatically matched it by industry and state, then queried our award history corpus — a hundred and nine thousand awarded contracts from Oregon's procurement database — and surfaced the vendors who have won the most similar contracts before.
>
> You can see the vendor name, how many times they've won, their average contract value, and when their last win was. This is a leaderboard of your likely competition.
>
> The query behind this runs in under ten milliseconds. It's not a live scan — we pre-aggregate this into a separate table that gets refreshed after every daily ingest. So the enrichment is instant, zero latency, regardless of how many contracts are in the database."

**Why this works:** This is the differentiator. No other procurement aggregator does this. Explain the engineering decision — it signals you thought about performance, not just features.

---

## SEGMENT 5 — THE DATA PIPELINE (5:30–7:00)

**What's on screen:** Switch to VS Code or GitHub — show the workers folder structure briefly, then the GitHub Actions workflow

**What you say:**

> "Let me show you what's running under the hood.
>
> Every portal has a dedicated Python worker. Each one handles the quirks of that specific source — SAM.gov uses a REST API with rate limiting and pagination. California's portal requires a headless browser to intercept an Excel download. Chicago uses Socrata's CSV API — no browser needed, fifty-five seconds for a hundred and eighty-five thousand rows. Florida embeds its data in a Next.js page's `__NEXT_DATA__` JSON blob — we parse that directly.
>
> Every worker normalizes its data into the same canonical schema. The key to making this idempotent — meaning safe to run every day without creating duplicates — is a SHA-256 deterministic ID. We hash the portal name plus the source record ID. Same contract, same hash, every time. The database upsert uses `ON CONFLICT DO UPDATE`, so re-running any worker is completely safe.
>
> All fifteen workers run in parallel every morning at six AM UTC via GitHub Actions."

*[Show the GitHub Actions workflow file briefly]*

> "Fourteen parallel jobs, each with `continue-on-error` — if one portal is down, the other thirteen still complete. After all workers finish, a smoke test verifies the record counts are within expected ranges."

**Why this works:** This is the engineering credibility segment. Shows you solved real problems — deduplication, rate limiting, heterogeneous sources — with clean, principled solutions.

---

## SEGMENT 6 — EXPORT + API (7:00–7:45)

**What's on screen:** Back to the live site — show the export button, briefly show an API response in a new tab

**What you say:**

> "The platform also exposes a full REST API. Ten Edge API routes — paginated list, single record, filters, charts, and export. You can pull up to five thousand records as CSV or JSON with a single request, with all the same filter parameters.
>
> This means the data is not just browsable — it's programmable. You can pipe it into your own analysis, your CRM, your bid tracking system."

---

## SEGMENT 7 — THE CLOSE (7:45–8:30)

**What's on screen:** Back to the Overview dashboard — full view

**What you say:**

> "To recap what you just saw: a hundred and twenty-nine thousand government contracts, fifteen portals, normalized into one schema, updated daily, with full-text search, smart filtering, award enrichment, and a REST API.
>
> The stack is Python async workers, Next.js 16 on Vercel, Neon PostgreSQL serverless. The entire pipeline runs on GitHub Actions — no infrastructure to manage, no servers to maintain.
>
> The live site is at chardi-contracts.vercel.app. The full source is on GitHub. Thanks for watching."

---

## PACING GUIDE

| Segment | Time | Screen |
|---|---|---|
| Hook | 0:00–0:45 | Overview dashboard |
| Dashboard walkthrough | 0:45–2:00 | Overview + charts |
| Contracts Explorer | 2:00–3:45 | Contracts page |
| Contract detail + Winners | 3:45–5:30 | Detail page |
| Pipeline / architecture | 5:30–7:00 | VS Code + GitHub |
| Export + API | 7:00–7:45 | Live site + browser |
| Close | 7:45–8:30 | Overview dashboard |

---

## PRO TIPS FOR RECORDING

- **Slow your mouse down** — move deliberately, don't dart around
- **Pause 1 second after every click** before speaking — let the UI respond first
- **Don't apologize** for anything — no "as you can see here" or "hopefully this makes sense"
- **Say numbers out loud** — "one hundred and twenty-nine thousand" lands harder than "129k"
- **The Winners sidebar is your money shot** — pause there, let it load, then explain it slowly
- **End on the dashboard** — full numbers visible, strong visual close
