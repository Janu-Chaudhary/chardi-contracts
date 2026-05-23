# Deployment

## Prerequisites

- Neon PostgreSQL with schema applied (tables: `opportunities`, `scrape_runs`, `scrape_errors`)
- SAM.gov public API key (register at api.sam.gov)
- Python 3.11+ for workers
- Node.js 18+ for frontend

---

## Environment variables

### Backend (`.env`)

```bash
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
SAM_GOV_API_KEY=SAM-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
SAM_GOV_BASE_URL=https://api.sam.gov/prod/opportunities/v2/search   # optional
USER_AGENT=YourName-ChardiAI-Trial/1.0                               # optional
REQUEST_TIMEOUT_SECONDS=60                                            # optional
```

### Frontend (`frontend/.env.local`)

```bash
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require   # same Neon DB
```

---

## Local development

### Backend workers

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Load env
export $(grep -v '^#' .env | xargs)

# Run workers
python -m backend.workers.samgov.main --days 1
python -m backend.workers.california.main
python -m backend.workers.texas.main
python -m backend.workers.newyork.main
python -m backend.workers.virginia.main

# Verify
python scripts/smoke_test.py
python scripts/data_quality_check.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

---

## Production deployment

### Frontend → Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy from frontend directory
cd frontend
vercel

# Set environment variable in Vercel dashboard:
# DATABASE_URL = <your Neon connection string>
```

Or via Vercel dashboard:
1. New Project → Import GitHub repo
2. Set root directory to `frontend`
3. Add env var: `DATABASE_URL`
4. Deploy

### Workers → Railway / Render / cron

Workers are Python CLI scripts. Deploy to any service that can run Python:

**Railway:**
```bash
# railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "python -m backend.workers.samgov.main --days 1"
```

**GitHub Actions cron (recommended for daily refresh):**
```yaml
# .github/workflows/daily-ingest.yml
name: Daily ingestion
on:
  schedule:
    - cron: '0 6 * * *'   # 6am UTC daily
jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r backend/requirements.txt
      - run: python -m backend.workers.samgov.main --days 1
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          SAM_GOV_API_KEY: ${{ secrets.SAM_GOV_API_KEY }}
```

---

## Playwright workers (California, Texas)

Playwright requires Chromium to be installed:

```bash
pip install playwright
playwright install chromium
```

On headless servers (Railway, Render):
```bash
playwright install --with-deps chromium
```

---

## Monitoring

Check scrape health after each run:

```sql
-- Latest run status
SELECT id, source_portal, status, records_scraped,
       EXTRACT(EPOCH FROM (end_time - start_time)) as duration_s,
       metadata->>'error_count' as errors
FROM scrape_runs
ORDER BY id DESC
LIMIT 10;

-- Error patterns
SELECT LEFT(error_message, 100) as error, COUNT(*)
FROM scrape_errors
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC;

-- Data freshness
SELECT source_portal, COUNT(*), MAX(last_seen_at) as last_seen
FROM opportunities
GROUP BY source_portal
ORDER BY last_seen DESC;
```

---

## SAM.gov rate limits

- Daily quota resets at **00:00 UTC**
- Worker detects `nextAccessTime` in 429 response → raises fatal `RuntimeError`
- Concurrency: 3 simultaneous requests
- Retries: 5 attempts with exponential backoff (2^attempt + jitter 0.1–1.5s)
- Backoff sleep runs **outside** the semaphore to release the concurrency slot
