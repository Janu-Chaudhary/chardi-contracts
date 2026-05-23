"""
Map Montgomery County MD contract records to opportunities upsert tuples.

Columns: contractno, solicitationnumber, contracttype, contractdesc,
         vendor, deptname, execution, expiration, buyerfirst, buyerlast
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "data.montgomerycountymd.gov"
SOURCE_URL_BASE = "https://www.montgomerycountymd.gov/procurement"


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
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _derive_status(expiration: datetime | None) -> str:
    if expiration is None:
        return "OPEN"
    exp_naive = expiration.replace(tzinfo=None) if expiration.tzinfo else expiration
    return "OPEN" if exp_naive >= datetime.today() else "CLOSED"


def map_montgomery_row(record: dict[str, Any]) -> tuple[Any, ...]:
    contract_no = _sanitize(record.get("contractno"))
    solicitation_no = _sanitize(record.get("solicitationnumber"))
    title = _sanitize(record.get("contractdesc")) or "Montgomery County Contract"
    vendor = _sanitize(record.get("vendor"))
    dept = _sanitize(record.get("deptname"))
    contract_type = _sanitize(record.get("contracttype"))
    execution = _parse_date(record.get("execution"))
    expiration = _parse_date(record.get("expiration"))
    buyer_first = _sanitize(record.get("buyerfirst")) or ""
    buyer_last = _sanitize(record.get("buyerlast")) or ""
    buyer_name = f"{buyer_first} {buyer_last}".strip() or dept

    status = _derive_status(expiration)

    description = vendor or title
    if vendor and dept:
        description = f"{vendor} — {dept}"

    rec_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=contract_no,
        title=title,
    )

    return (
        rec_id,             # $1  id
        SOURCE_PORTAL,      # $2  source_portal
        contract_no,        # $3  source_record_id
        solicitation_no,    # $4  solicitation_number
        "County",           # $5  portal_region
        title,              # $6  title
        description,        # $7  description
        contract_type,      # $8  notice_type
        execution,          # $9  posted_date
        expiration,         # $10 deadline
        "MD",               # $11 state_region
        contract_type,      # $12 industry
        None,               # $13 naics_code
        None,               # $14 value_numeric
        None,               # $15 value_min
        None,               # $16 value_max
        "USD",              # $17 currency
        status,             # $18 status
        dept,               # $19 buyer_name
        "County",           # $20 buyer_type
        SOURCE_URL_BASE,    # $21 source_url
        json.dumps([]),     # $22 documents
        json.dumps({k: str(v) if v is not None else None for k, v in record.items()}),
    )
