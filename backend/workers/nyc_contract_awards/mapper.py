"""
Map NYC Open Data contract award records to opportunities upsert tuples.

Source: Socrata dataset qyyg-4tf5 — Recent Contract Awards
Portal: data.cityofnewyork.us

Socrata columns used:
  request_id                    → source_record_id, solicitation_number, id (fingerprint)
  short_title                   → title
  agency_name                   → buyer_name
  vendor_name                   → description
  category_description          → industry
  selection_method_description  → notice_type
  start_date                    → posted_date
  end_date                      → deadline, status
  contract_amount               → value_numeric
  document_links                → documents

DB schema coverage (23 fields):
  ✅ id                  — SHA-256(portal + request_id)
  ✅ source_portal        — "data.cityofnewyork.us"
  ✅ source_record_id     — request_id
  ✅ solicitation_number  — request_id
  ✅ portal_region        — "City"
  ✅ title                — short_title (fallback "Unknown Contract")
  ✅ description          — vendor_name
  ✅ notice_type          — selection_method_description
  ✅ posted_date          — start_date (parsed datetime)
  ✅ deadline             — end_date (parsed datetime)
  ✅ state_region         — "NY"
  ✅ industry             — category_description
  ❌ naics_code           — not in dataset → None
  ✅ value_numeric        — contract_amount (parsed float)
  ❌ value_min            — not in dataset → None
  ❌ value_max            — not in dataset → None
  ✅ currency             — "USD"
  ✅ status               — OPEN/CLOSED derived from end_date
  ✅ buyer_name           — agency_name
  ✅ buyer_type           — "City"
  ✅ source_url           — constructed from request_id
  ✅ documents            — document_links serialized as JSON array
  ✅ raw_payload          — full record as JSON
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "data.cityofnewyork.us"
SOURCE_URL_BASE = "https://data.cityofnewyork.us/resource/qyyg-4tf5.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(val: Any) -> datetime | None:
    """Parse ISO 8601 or date-only strings to datetime. Returns None on failure."""
    if not val:
        return None
    text = str(val).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt)
        except ValueError:
            continue
    return None


def _parse_amount(val: Any) -> float | None:
    """Strip currency symbols/commas and parse to float. Returns None if unparseable."""
    if not val:
        return None
    text = re.sub(r"[$,\s]", "", str(val).strip())
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _derive_status(end_date: datetime | None) -> str:
    """OPEN if end_date is today or future (or absent), else CLOSED."""
    if end_date is None:
        return "OPEN"
    # Strip timezone for comparison if present
    end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
    return "OPEN" if end_naive >= datetime.today() else "CLOSED"


def _serialize_documents(val: Any) -> str:
    """Serialize document_links to a JSON array string."""
    if not val:
        return "[]"
    text = str(val).strip()
    if not text:
        return "[]"
    return json.dumps([{"title": "Document", "url": text}])


def _sanitize(val: Any) -> str | None:
    """Return stripped string or None."""
    if val is None:
        return None
    text = str(val).strip()
    return text or None


# ── Main mapper ───────────────────────────────────────────────────────────────

def map_nyc_row(record: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one NYC contract award record to an opportunities upsert tuple.
    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).

    Extra columns captured in raw_payload / description:
      pin, vendor_address, email, contact_name, additional_description_1,
      special_case_reason_description, section_name
    """
    request_id = _sanitize(record.get("request_id"))
    short_title = _sanitize(record.get("short_title")) or "Unknown Contract"
    agency_name = _sanitize(record.get("agency_name"))
    vendor_name = _sanitize(record.get("vendor_name"))
    category = _sanitize(record.get("category_description"))
    selection_method = _sanitize(record.get("selection_method_description"))
    start_date = _parse_date(record.get("start_date"))
    end_date = _parse_date(record.get("end_date"))
    contract_amount = _parse_amount(record.get("contract_amount"))
    document_links = _serialize_documents(record.get("document_links"))

    # Use additional_description_1 as richer description when available,
    # strip HTML tags first; fall back to vendor_name
    raw_desc = _sanitize(record.get("additional_description_1")) or ""
    clean_desc = re.sub(r"<[^>]+>", " ", raw_desc)
    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
    description = clean_desc or vendor_name

    # PIN is the procurement ID number — useful for solicitation_number
    pin = _sanitize(record.get("pin")) or request_id

    status = _derive_status(end_date)

    source_url = (
        f"https://data.cityofnewyork.us/resource/qyyg-4tf5/{request_id}"
        if request_id
        else SOURCE_URL_BASE
    )

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=request_id,
    )

    # Build clean raw payload preserving all source fields
    raw_payload = {k: str(v) for k, v in record.items()}

    return (
        record_id,          # $1  id
        SOURCE_PORTAL,      # $2  source_portal
        request_id,         # $3  source_record_id
        pin,                # $4  solicitation_number (PIN preferred)
        "City",             # $5  portal_region
        short_title,        # $6  title
        description,        # $7  description (cleaned HTML or vendor_name)
        selection_method,   # $8  notice_type
        start_date,         # $9  posted_date
        end_date,           # $10 deadline
        "NY",               # $11 state_region
        category,           # $12 industry
        None,               # $13 naics_code
        contract_amount,    # $14 value_numeric
        None,               # $15 value_min
        None,               # $16 value_max
        "USD",              # $17 currency
        status,             # $18 status
        agency_name,        # $19 buyer_name
        "City",             # $20 buyer_type
        source_url,         # $21 source_url
        document_links,     # $22 documents
        json.dumps(raw_payload),  # $23 raw_payload
    )
