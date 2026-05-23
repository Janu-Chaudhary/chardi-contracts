"""
Map Illinois BidBuy CSV rows to opportunities upsert tuples.

CSV columns (from export):
  Bid Solicitation #, Organization Name, Blanket #, Buyer,
  Description, Bid Opening Date, Bid Holder List, Awarded Vendor(s),
  Status, Alternate Id

DB schema coverage (23 fields):
  ✅ id                  — SHA-256(portal + Bid Solicitation #)
  ✅ source_portal        — "bidbuy.illinois.gov"
  ✅ source_record_id     — Bid Solicitation #
  ✅ solicitation_number  — Bid Solicitation #
  ✅ portal_region        — "State"
  ✅ title                — Description
  ✅ description          — Description
  ✅ notice_type          — "Bid" (all rows are open bids)
  ❌ posted_date          — not in CSV export
  ✅ deadline             — Bid Opening Date
  ✅ state_region         — "IL" hardcoded
  ❌ industry             — not in CSV
  ❌ naics_code           — not in CSV
  ❌ value_numeric        — not in CSV
  ❌ value_min            — not in CSV
  ❌ value_max            — not in CSV
  ✅ currency             — "USD"
  ✅ status               — derived from Status column
  ✅ buyer_name           — Organization Name
  ✅ buyer_type           — "State"
  ✅ source_url           — constructed from Bid Solicitation #
  ✅ documents            — []
  ✅ raw_payload          — full row as JSON
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "bidbuy.illinois.gov"
SOURCE_URL_BASE = "https://www.bidbuy.illinois.gov/bso/view/search/external/advancedSearchBid.xhtml"


def _sanitize(val: Any) -> str | None:
    """Convert NaN/empty to None; strip whitespace."""
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
    """Parse BidBuy date strings to datetime for asyncpg timestamptz."""
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
    # BidBuy format: "06/05/2026 14:00:00"
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19] if len(raw) >= 19 else raw, fmt)
        except ValueError:
            continue
    return None


def _derive_status(status_text: str | None, deadline: datetime | None) -> str:
    """
    Map BidBuy status to our schema values.

    Known BidBuy statuses: "Sent", "Open", "Closed", "Awarded", "Cancelled"
    """
    if not status_text:
        if deadline and deadline < datetime.today():
            return "CLOSED"
        return "OPEN"
    s = status_text.strip().lower()
    if s in ("sent", "open", "active"):
        return "OPEN"
    if s in ("closed", "completed"):
        return "CLOSED"
    if "award" in s:
        return "AWARDED"
    if "cancel" in s:
        return "CANCELLED"
    # Default: if deadline is past → CLOSED, else OPEN
    if deadline and deadline < datetime.today():
        return "CLOSED"
    return "OPEN"


def _build_source_url(bid_number: str | None) -> str:
    """Construct a link to the BidBuy search filtered to this bid."""
    if not bid_number:
        return SOURCE_URL_BASE
    return f"{SOURCE_URL_BASE}?openBids=true"


def map_illinois_row(row: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one BidBuy CSV row dict to an opportunities upsert tuple.
    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    bid_number = _sanitize(row.get("Bid Solicitation #"))
    org_name = _sanitize(row.get("Organization Name"))
    description = _sanitize(row.get("Description")) or "Unknown Bid"
    bid_opening_raw = row.get("Bid Opening Date")
    status_raw = _sanitize(row.get("Status"))
    alternate_id = _sanitize(row.get("Alternate Id"))

    deadline = _parse_date(bid_opening_raw)
    status = _derive_status(status_raw, deadline)
    source_url = _build_source_url(bid_number)

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=bid_number,
        title=description,
    )

    clean_payload = {
        str(k): _sanitize(v) for k, v in row.items()
    }

    return (
        record_id,          # $1  id
        SOURCE_PORTAL,      # $2  source_portal
        bid_number,         # $3  source_record_id
        bid_number,         # $4  solicitation_number
        "State",            # $5  portal_region
        description,        # $6  title
        description,        # $7  description
        "Bid",              # $8  notice_type
        None,               # $9  posted_date (not in CSV)
        deadline,           # $10 deadline (Bid Opening Date)
        "IL",               # $11 state_region
        None,               # $12 industry (not in CSV)
        None,               # $13 naics_code
        None,               # $14 value_numeric
        None,               # $15 value_min
        None,               # $16 value_max
        "USD",              # $17 currency
        status,             # $18 status
        org_name,           # $19 buyer_name (Organization Name)
        "State",            # $20 buyer_type
        source_url,         # $21 source_url
        json.dumps([]),     # $22 documents
        json.dumps(clean_payload),  # $23 raw_payload
    )
