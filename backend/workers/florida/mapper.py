"""
Map Florida DMS contract records to opportunities upsert tuples.

API fields (from search_contracts):
  number, name, startDate, endDate, category, admin, link.url, link.locationId

Detail page fields (from __NEXT_DATA__, optional):
  description, benefits, commodity_codes

DB schema coverage (23 fields):
  ✅ id                  — SHA-256(portal + contract number)
  ✅ source_portal        — "dms.myflorida.com"
  ✅ source_record_id     — number (contract number)
  ✅ solicitation_number  — number
  ✅ portal_region        — "State"
  ✅ title                — name
  ✅ description          — from detail page (when available)
  ✅ notice_type          — category (contract category)
  ✅ posted_date          — startDate
  ✅ deadline             — endDate
  ✅ state_region         — "FL" hardcoded
  ✅ industry             — category
  ❌ naics_code           — not in API
  ❌ value_numeric        — not in API
  ❌ value_min            — not in API
  ❌ value_max            — not in API
  ✅ currency             — "USD"
  ✅ status               — derived from endDate vs today
  ✅ buyer_name           — admin (contract administrator)
  ✅ buyer_type           — "State"
  ✅ source_url           — link.url
  ✅ documents            — []
  ✅ raw_payload          — full merged record as JSON
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "dms.myflorida.com"
SOURCE_URL_BASE = "https://www.dms.myflorida.com/business_operations/state_purchasing/state_contracts_and_agreements"


def _parse_date(val: str | None) -> datetime | None:
    """Parse Florida DMS date strings (MM/DD/YYYY) to datetime."""
    if not val or not str(val).strip():
        return None
    text = str(val).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], fmt)
        except ValueError:
            continue
    return None


def _derive_status(end_date: datetime | None) -> str:
    """OPEN if end_date is today or future, else CLOSED."""
    if end_date is None:
        return "OPEN"
    return "OPEN" if end_date >= datetime.today() else "CLOSED"


def map_florida_contract(record: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one Florida DMS contract dict to an opportunities upsert tuple.
    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    contract_number = str(record.get("number") or "").strip() or None
    name = str(record.get("name") or "").strip() or "Unknown Contract"
    category = str(record.get("category") or "").strip() or None
    admin = str(record.get("admin") or "").strip() or None
    start_raw = record.get("startDate")
    end_raw = record.get("endDate")

    # Detail-enriched fields
    description = record.get("description")  # from detail page
    if not description:
        description = name  # fallback to title

    # Source URL from link object
    link = record.get("link") or {}
    source_url = str(link.get("url") or "").strip() or SOURCE_URL_BASE

    posted_date = _parse_date(start_raw)
    deadline = _parse_date(end_raw)
    status = _derive_status(deadline)

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=contract_number,
        title=name,
    )

    # Build clean raw payload (exclude large HTML blobs)
    raw = {
        "number": contract_number,
        "name": name,
        "startDate": start_raw,
        "endDate": end_raw,
        "category": category,
        "admin": admin,
        "detail_url": source_url,
        "location_id": link.get("locationId"),
        "benefits": record.get("benefits"),
        "commodity_codes": record.get("commodity_codes"),
    }

    return (
        record_id,          # $1  id
        SOURCE_PORTAL,      # $2  source_portal
        contract_number,    # $3  source_record_id
        contract_number,    # $4  solicitation_number
        "State",            # $5  portal_region
        name,               # $6  title
        description,        # $7  description (from detail or title)
        category,           # $8  notice_type (contract category)
        posted_date,        # $9  posted_date (startDate)
        deadline,           # $10 deadline (endDate)
        "FL",               # $11 state_region
        category,           # $12 industry (same as category)
        None,               # $13 naics_code
        None,               # $14 value_numeric
        None,               # $15 value_min
        None,               # $16 value_max
        "USD",              # $17 currency
        status,             # $18 status
        admin,              # $19 buyer_name (contract administrator)
        "State",            # $20 buyer_type
        source_url,         # $21 source_url
        json.dumps([]),     # $22 documents
        json.dumps(raw),    # $23 raw_payload
    )
