"""Async PostgreSQL access for scrape observability and opportunity upserts."""

from __future__ import annotations

import json
from typing import Any

import asyncpg

from backend.core import settings

_pool: asyncpg.Pool | None = None

OPPORTUNITY_UPSERT_SQL = """
INSERT INTO opportunities (
    id,
    source_portal,
    source_record_id,
    solicitation_number,
    portal_region,
    title,
    description,
    notice_type,
    posted_date,
    deadline,
    state_region,
    industry,
    naics_code,
    value_numeric,
    value_min,
    value_max,
    currency,
    status,
    buyer_name,
    buyer_type,
    source_url,
    documents,
    raw_payload,
    last_seen_at
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8,
    $9::timestamptz, $10::timestamptz,
    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21,
    $22::jsonb, $23::jsonb,
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    notice_type = EXCLUDED.notice_type,
    deadline = EXCLUDED.deadline,
    status = EXCLUDED.status,
    documents = EXCLUDED.documents,
    last_seen_at = CURRENT_TIMESTAMP,
    raw_payload = EXCLUDED.raw_payload,
    updated_at = CURRENT_TIMESTAMP
"""


async def create_pool() -> asyncpg.Pool:
    """Create and cache the global asyncpg connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=1,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    """Close the global pool if it exists."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def insert_scrape_run(source_portal: str, metadata: dict | None = None) -> int:
    """Insert a RUNNING scrape_runs row and return its id."""
    pool = await create_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO scrape_runs (source_portal, status, metadata)
        VALUES ($1, 'RUNNING', $2::jsonb)
        RETURNING id
        """,
        source_portal,
        json.dumps(metadata or {}),
    )
    return int(row["id"])


async def finalize_scrape_run(
    run_id: int,
    status: str,
    records_scraped: int,
    metadata: dict | None = None,
) -> None:
    """Mark a scrape run complete with counts and metadata."""
    pool = await create_pool()
    await pool.execute(
        """
        UPDATE scrape_runs
        SET end_time = CURRENT_TIMESTAMP,
            status = $2,
            records_scraped = $3,
            metadata = COALESCE($4::jsonb, metadata)
        WHERE id = $1
        """,
        run_id,
        status,
        records_scraped,
        json.dumps(metadata) if metadata is not None else None,
    )


async def log_scrape_error(
    run_id: int,
    source_portal: str,
    error_message: str,
    raw_payload: dict | list | str | None = None,
) -> None:
    """Insert a row into scrape_errors for dead-letter style observability."""
    pool = await create_pool()
    payload = raw_payload
    if isinstance(payload, (dict, list)):
        payload = json.dumps(payload)
    await pool.execute(
        """
        INSERT INTO scrape_errors (run_id, source_portal, error_message, raw_payload)
        VALUES ($1, $2, $3, $4::jsonb)
        """,
        run_id,
        source_portal,
        error_message,
        payload,
    )


async def upsert_opportunities(rows: list[tuple[Any, ...]]) -> int:
    """
    Batch upsert mapped opportunity tuples.

    Each tuple must match OPPORTUNITY_UPSERT_SQL parameter order (23 fields).
    Returns the number of rows submitted.
    """
    if not rows:
        return 0
    pool = await create_pool()
    async with pool.acquire() as conn:
        await conn.executemany(OPPORTUNITY_UPSERT_SQL, rows)
    return len(rows)
