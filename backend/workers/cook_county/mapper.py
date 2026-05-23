"""
Map Cook County IL contract records to opportunities upsert tuples.

Columns: contract_number, vendor_name, amount, description, lead_department,
         start_date, end_date, category (dict with url+description), commodity_type
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "datacatalog.cookcountyil.gov"
SOURCE_URL_BASE = "https://datacatalog.cookcountyil.gov/Procurement/Procurement-Awarded-Contracts-Amendments/qh8j-6k63"


def _sanitize(val: Any) -> str | None:
    if val is None:
        return None
    text = str(val).strip()
    return text or None


def _truncate(val: str | None, max_len: int = 255) -> str | None:
    if val is None:
        return None
    return val[:max_len]


def _parse_date(val: Any) -> datetime | None:
    if not val:
        return None
    text = str(val).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _parse_amount(val: Any) -> float | None:
    if not val:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except ValueError:
        return None


def _derive_status(end_date: datetime | None) -> str:
    if end_date is None:
        return "OPEN"
    end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
    return "OPEN" if end_naive >= datetime.today() else "CLOSED"


def map_cook_county_row(record: dict[str, Any]) -> tuple[Any, ...]:
    contract_number = _sanitize(record.get("contract_number"))
    title = _sanitize(record.get("description")) or "Cook County Contract"
    vendor = _sanitize(record.get("vendor_name"))
    dept = _sanitize(record.get("lead_department"))
    amount = _parse_amount(record.get("amount"))
    start_date = _parse_date(record.get("start_date") or record.get("system_release"))
    end_date = _parse_date(record.get("end_date"))
    commodity = _sanitize(record.get("commodity_type"))

    # category is a dict with url + description
    category_raw = record.get("category") or {}
    if isinstance(category_raw, dict):
        notice_type = _sanitize(category_raw.get("description"))
        doc_url = _sanitize(category_raw.get("url"))
    else:
        notice_type = _sanitize(str(category_raw))
        doc_url = None

    status = _derive_status(end_date)

    description = vendor or title
    if vendor and dept:
        description = f"{vendor} — {dept}"

    documents = json.dumps([{"title": "Contract Document", "url": doc_url}] if doc_url else [])

    rec_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=contract_number,
        title=title,
    )

    raw = {
        "contract_number": contract_number,
        "vendor_name": vendor,
        "amount": str(amount) if amount else None,
        "description": title,
        "lead_department": dept,
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
        "category": str(category_raw),
        "commodity_type": commodity,
    }

    return (
        rec_id,                     # $1  id
        SOURCE_PORTAL,              # $2  source_portal
        contract_number,            # $3  source_record_id
        contract_number,            # $4  solicitation_number
        "County",                   # $5  portal_region
        title,                      # $6  title
        description,                # $7  description
        _truncate(notice_type, 100),# $8  notice_type
        start_date,                 # $9  posted_date
        end_date,                   # $10 deadline
        "IL",                       # $11 state_region
        _truncate(commodity, 100),  # $12 industry
        None,                       # $13 naics_code
        amount,                     # $14 value_numeric
        None,                       # $15 value_min
        None,                       # $16 value_max
        "USD",                      # $17 currency
        status,                     # $18 status
        _truncate(dept, 255),       # $19 buyer_name
        "County",                   # $20 buyer_type
        SOURCE_URL_BASE,            # $21 source_url
        documents,                  # $22 documents
        json.dumps(raw),            # $23 raw_payload
    )
