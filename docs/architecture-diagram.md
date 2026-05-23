# Architecture Diagram

```mermaid
flowchart TD
    subgraph SOURCES["Data Sources"]
        direction TB
        S1["SAM.gov\nFederal API v2"]
        S2["Cal eProcure\nPlaywright + Excel"]
        S3["TxSmartBuy\nPlaywright + CSV"]
        S4["NYSCR\nAsync HTTP"]
        S5["NYC Open Data\nSocrata API"]
        S6["Chicago Data Portal\nSocrata API"]
        S7["Virginia eVA + VITA\nAsync HTTP"]
        S8["Georgia TGM\nPlaywright"]
        S9["Illinois BidBuy\nPlaywright"]
        S10["Florida DMS\nAsync HTTP"]
    end

    subgraph WORKERS["Python Workers  ·  backend/workers/"]
        direction TB
        W1["fetcher.py\naiohttp · rate limits · retry"]
        W2["mapper.py\nnormalize · sanitize · fingerprint"]
        W3["main.py\nlifecycle orchestrator"]
    end

    subgraph CORE["Shared Core  ·  backend/core/"]
        FP["fingerprint.py\nSHA-256 deterministic ID"]
        DB["db.py\nasyncpg pool · upsert SQL"]
    end

    subgraph PG["Neon PostgreSQL"]
        T1[("opportunities\n10,735 records")]
        T2[("scrape_runs\nlifecycle log")]
        T3[("scrape_errors\ndead-letter log")]
    end

    subgraph CRON["GitHub Actions  ·  daily 06:00 UTC"]
        GH["11 parallel jobs\n+ smoke test verify"]
    end

    subgraph API["Next.js Edge API  ·  /api/"]
        A1["/stats"]
        A2["/opportunities"]
        A3["/filters"]
        A4["/charts/*"]
        A5["/export"]
    end

    subgraph UI["Next.js Dashboard  ·  Vercel"]
        U1["Overview\nKPIs + recent"]
        U2["Contracts Explorer\nsearch · filter · sort"]
        U3["Trends\ncharts + deadlines"]
        U4["Detail View\nfull record"]
    end

    SOURCES --> WORKERS
    WORKERS --> CORE
    FP --> DB
    DB --> T1
    DB --> T2
    DB --> T3
    CRON --> WORKERS
    T1 --> API
    API --> UI
```
