"""
Map Oregon OregonBuys contract records to opportunities upsert tuples.

Columns: record_id, sent_date, po_nbr, po_type, org_name, discipline_type,
         short_description, purchase_order_total_amount, vendor_name
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "data.oregon.gov"
SOURCE_URL_BASE = "https://data.oregon.gov/dataset/OregonBuys-Purchases-and-Contracts/qyug-f2km"


def _sanitize(val: Any) -> str | None:
    if val is None:
        return None
    text = str(val).strip()
    return text or None


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
    try:
        return float(str(val).replace(",", "").strip())
    except ValueError:
        return None


def map_oregon_row(record: dict[str, Any]) -> tuple[Any, ...]:
    record_id_raw = _sanitize(record.get("record_id") or record.get("po_nbr"))
    title = _sanitize(record.get("short_description")) or "Oregon State Contract"
    org_name = _sanitize(record.get("org_name"))
    vendor = _sanitize(record.get("vendor_name"))
    discipline = _sanitize(record.get("discipline_type"))
    po_type = _sanitize(record.get("po_type"))
    sent_date = _parse_date(record.get("sent_date") or record.get("date_retrieved"))
    amount = _parse_amount(record.get("purchase_order_total_amount"))

    description = vendor or title
    if vendor and org_name:
        description = f"{vendor} — {org_name}"

    rec_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=record_id_raw,
        title=title,
    )

    return (
        rec_id,             # $1  id
        SOURCE_PORTAL,      # $2  source_portal
        record_id_raw,      # $3  source_record_id
        _sanitize(record.get("po_nbr")),  # $4  solicitation_number
        "State",            # $5  portal_region
        title,              # $6  title
        description,        # $7  description
        po_type,            # $8  notice_type
        sent_date,          # $9  posted_date
        None,               # $10 deadline (not in dataset)
        "OR",               # $11 state_region
        discipline,         # $12 industry
        None,               # $13 naics_code
        amount,             # $14 value_numeric
        None,               # $15 value_min
        None,               # $16 value_max
        "USD",              # $17 currency
        "AWARDED",          # $18 status (these are completed purchases)
        org_name,           # $19 buyer_name
        "State",            # $20 buyer_type
        SOURCE_URL_BASE,    # $21 source_url
        json.dumps([]),     # $22 documents
        json.dumps({k: str(v) if v is not None else None for k, v in record.items()}),  # $23
    )
