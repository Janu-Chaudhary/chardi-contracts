"""
Map TxSmartBuy CSV rows to opportunities upsert tuples.

CSV columns (8 total):
  Contract, Description, Contract Type, Contract Group,
  Start Date, End Date, NIGP(s), FED

DB schema coverage (23 fields):
  ✅ id                  — SHA-256(portal + Contract)
  ✅ source_portal        — "txsmartbuy.gov"
  ✅ source_record_id     — Contract
  ✅ solicitation_number  — FED (federal contract ref, when present)
  ✅ portal_region        — "State"
  ✅ title                — Description
  ✅ description          — Description (same; no separate long-form available)
  ✅ notice_type          — Contract Type (Term / TXMAS)
  ✅ posted_date          — Start Date
  ✅ deadline             — End Date
  ✅ state_region         — "TX"
  ✅ industry             — first NIGP code (semicolon-separated list)
  ❌ naics_code           — not in CSV (NIGP ≠ NAICS; left None)
  ❌ value_numeric        — not in CSV
  ❌ value_min            — not in CSV
  ❌ value_max            — not in CSV
  ✅ currency             — "USD"
  ✅ status               — OPEN if End Date >= today, else CLOSED
  ✅ buyer_name           — Contract Group
  ✅ buyer_type           — "State"
  ✅ source_url           — constructed from Contract ID
  ✅ documents            — [] (no attachments in export)
  ✅ raw_payload          — full row as JSON
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "txsmartbuy.gov"
SOURCE_URL_BASE = "https://www.txsmartbuy.gov/sp"


def _sanitize(val: Any) -> str | None:
    """Convert NaN/NaT/empty to None; strip whitespace from strings."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    text = str(val).strip()
    return text or None


def _parse_date(val: Any) -> datetime | None:
    """Parse a date value into a datetime object for asyncpg timestamptz."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, pd.Timestamp):
        return val.to_pydatetime()
    if isinstance(val, datetime):
        return val
    raw = str(val).strip()
    if not raw:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(raw[:10], fmt)
        except ValueError:
            continue
    return None


def _derive_status(end_date: datetime | None) -> str:
    """OPEN if contract end date is today or in the future, else CLOSED."""
    if end_date is None:
        return "OPEN"
    return "OPEN" if end_date >= datetime.today() else "CLOSED"


def _first_nigp(nigp_str: str | None) -> str | None:
    """
    Extract the first NIGP code from a semicolon-separated list.

    NIGP codes are Texas's commodity classification (not NAICS).
    We store the first code in the `industry` field as a category proxy.
    """
    if not nigp_str:
        return None
    return nigp_str.split(";")[0].strip() or None


def _build_source_url(contract_id: str | None) -> str:
    """
    Construct a direct link to the contract detail page.

    TxSmartBuy contract detail URLs follow the pattern:
    https://www.txsmartbuy.gov/sp?contract=<CONTRACT_ID>
    """
    if not contract_id:
        return SOURCE_URL_BASE
    return f"{SOURCE_URL_BASE}?contract={contract_id}"


def _clean_payload(row: dict[str, Any]) -> dict[str, str | None]:
    """Sanitize all values in a row dict for safe JSON serialization."""
    return {str(k): _sanitize(v) for k, v in row.items()}


def map_texas_row(row: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one TxSmartBuy CSV row dict to an opportunities upsert tuple.

    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    contract_id = _sanitize(row.get("Contract"))
    title = _sanitize(row.get("Description")) or "Unknown Contract"
    posted_date = _parse_date(row.get("Start Date"))
    deadline = _parse_date(row.get("End Date"))
    nigp_raw = _sanitize(row.get("NIGP(s)"))
    fed_ref = _sanitize(row.get("FED"))  # federal contract reference (86/297 populated)

    status = _derive_status(deadline)
    industry = _first_nigp(nigp_raw)
    source_url = _build_source_url(contract_id)
    clean_payload = _clean_payload(row)

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=contract_id,
        title=title,
    )

    return (
        record_id,                          # $1  id
        SOURCE_PORTAL,                      # $2  source_portal
        contract_id,                        # $3  source_record_id
        fed_ref,                            # $4  solicitation_number (FED ref when present)
        "State",                            # $5  portal_region
        title,                              # $6  title
        title,                              # $7  description (no separate long-form)
        _sanitize(row.get("Contract Type")),# $8  notice_type (Term / TXMAS)
        posted_date,                        # $9  posted_date
        deadline,                           # $10 deadline
        "TX",                               # $11 state_region
        industry,                           # $12 industry (first NIGP code)
        None,                               # $13 naics_code (not in CSV)
        None,                               # $14 value_numeric
        None,                               # $15 value_min
        None,                               # $16 value_max
        "USD",                              # $17 currency
        status,                             # $18 status
        _sanitize(row.get("Contract Group")),# $19 buyer_name
        "State",                            # $20 buyer_type
        source_url,                         # $21 source_url
        json.dumps([]),                     # $22 documents (no attachments in export)
        json.dumps(clean_payload),          # $23 raw_payload
    )
