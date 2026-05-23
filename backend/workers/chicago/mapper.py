"""
Map Chicago Data Portal contract records to opportunities upsert tuples.

Source: Socrata dataset rsxa-ify5 — Contracts
Portal: data.cityofchicago.org

Socrata columns:
  purchase_order_contract_number  → source_record_id, solicitation_number
  specification_number            → used in solicitation_number fallback
  purchase_order_description      → title
  vendor_name                     → description, buyer_name proxy
  department                      → buyer_name
  contract_type                   → notice_type
  procurement_type                → industry
  start_date                      → posted_date
  end_date                        → deadline, status
  award_amount                    → value_numeric
  address_1, city, state, zip     → captured in raw_payload

DB schema coverage (23 fields):
  ✅ id                  — SHA-256(portal + purchase_order_contract_number)
  ✅ source_portal        — "data.cityofchicago.org"
  ✅ source_record_id     — purchase_order_contract_number
  ✅ solicitation_number  — specification_number (or contract number)
  ✅ portal_region        — "City"
  ✅ title                — purchase_order_description
  ✅ description          — vendor_name + department
  ✅ notice_type          — contract_type
  ✅ posted_date          — start_date
  ✅ deadline             — end_date
  ✅ state_region         — "IL"
  ✅ industry             — procurement_type
  ❌ naics_code           — not in dataset → None
  ✅ value_numeric        — award_amount
  ❌ value_min/max        — not in dataset → None
  ✅ currency             — "USD"
  ✅ status               — OPEN/CLOSED from end_date
  ✅ buyer_name           — department
  ✅ buyer_type           — "City"
  ✅ source_url           — constructed from contract number
  ✅ documents            — []
  ✅ raw_payload          — full record as JSON
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "data.cityofchicago.org"
SOURCE_URL_BASE = "https://data.cityofchicago.org/resource/rsxa-ify5.json"


def _parse_date(val: Any) -> datetime | None:
    if not val:
        return None
    text = str(val).strip()
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
    if end_date is None:
        return "OPEN"
    end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
    return "OPEN" if end_naive >= datetime.today() else "CLOSED"


def _sanitize(val: Any) -> str | None:
    if val is None:
        return None
    text = str(val).strip()
    return text or None


def map_chicago_row(record: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one Chicago contract record to an opportunities upsert tuple.
    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    contract_number = _sanitize(record.get("purchase_order_contract_number"))
    spec_number = _sanitize(record.get("specification_number")) or contract_number
    description_raw = _sanitize(record.get("purchase_order_description")) or "Unknown Contract"
    vendor_name = _sanitize(record.get("vendor_name"))
    department = _sanitize(record.get("department"))
    contract_type = _sanitize(record.get("contract_type"))
    procurement_type = _sanitize(record.get("procurement_type"))
    start_date = _parse_date(record.get("start_date"))
    end_date = _parse_date(record.get("end_date"))
    award_amount = _parse_amount(record.get("award_amount"))

    status = _derive_status(end_date)

    # Build description from vendor + department
    description = vendor_name or description_raw
    if vendor_name and department:
        description = f"{vendor_name} — {department}"

    source_url = (
        f"https://data.cityofchicago.org/resource/rsxa-ify5/{contract_number}"
        if contract_number
        else SOURCE_URL_BASE
    )

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=contract_number,
    )

    return (
        record_id,          # $1  id
        SOURCE_PORTAL,      # $2  source_portal
        contract_number,    # $3  source_record_id
        spec_number,        # $4  solicitation_number
        "City",             # $5  portal_region
        description_raw,    # $6  title
        description,        # $7  description
        contract_type,      # $8  notice_type
        start_date,         # $9  posted_date
        end_date,           # $10 deadline
        "IL",               # $11 state_region
        procurement_type,   # $12 industry
        None,               # $13 naics_code
        award_amount,       # $14 value_numeric
        None,               # $15 value_min
        None,               # $16 value_max
        "USD",              # $17 currency
        status,             # $18 status
        department,         # $19 buyer_name
        "City",             # $20 buyer_type
        source_url,         # $21 source_url
        json.dumps([]),     # $22 documents
        json.dumps({k: str(v) for k, v in record.items()}),  # $23 raw_payload
    )
