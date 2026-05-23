"""
Map Houston procurement contract rows to opportunities upsert tuples.

Source: data.houstontx.gov — All City of Houston Procurement Contracts (XLSX)
Columns (normalized): contract_number, description, vendor_name, department,
                      contract_type, start_date, end_date, contract_amount, etc.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import pandas as pd

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "data.houstontx.gov"
SOURCE_URL_BASE = "https://data.houstontx.gov/dataset/all-city-of-houston-procurement-contracts"


def _sanitize(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    text = str(val).strip()
    return text or None


def _parse_date(val: Any) -> datetime | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    # Handle pandas Timestamp
    if hasattr(val, 'to_pydatetime'):
        try:
            return val.to_pydatetime().replace(tzinfo=None)
        except Exception:
            pass
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    text = str(val).strip()
    if not text or text == 'NaT':
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _parse_amount(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    text = re.sub(r"[$,\s]", "", str(val).strip())
    try:
        return float(text)
    except ValueError:
        return None


def _derive_status(end_date: datetime | None) -> str:
    if end_date is None:
        return "OPEN"
    end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
    return "OPEN" if end_naive >= datetime.today() else "CLOSED"


def map_houston_row(record: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one Houston contract row to an opportunities upsert tuple.
    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    # Try common column name variants
    contract_number = _sanitize(
        record.get("contract_number") or record.get("contract_no") or record.get("po_number")
    )
    title = _sanitize(
        record.get("description") or record.get("contract_description") or record.get("title")
    ) or "Houston Procurement Contract"
    vendor = _sanitize(record.get("vendor_name") or record.get("vendor"))
    department = _sanitize(record.get("department") or record.get("dept_name"))
    contract_type = _sanitize(record.get("contract_type") or record.get("type"))
    start_date = _parse_date(record.get("start_date") or record.get("begin_date"))
    end_date = _parse_date(record.get("end_date") or record.get("expiration_date"))
    amount = _parse_amount(record.get("contract_amount") or record.get("amount"))

    status = _derive_status(end_date)

    description = vendor or title
    if vendor and department:
        description = f"{vendor} — {department}"

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=contract_number,
        title=title,
        buyer_name=department,
        deadline=str(end_date) if end_date else None,
    )

    raw = {k: (str(v) if v is not None else None) for k, v in record.items()}

    return (
        record_id,          # $1  id
        SOURCE_PORTAL,      # $2  source_portal
        contract_number,    # $3  source_record_id
        contract_number,    # $4  solicitation_number
        "City",             # $5  portal_region
        title,              # $6  title
        description,        # $7  description
        contract_type,      # $8  notice_type
        start_date,         # $9  posted_date
        end_date,           # $10 deadline
        "TX",               # $11 state_region
        contract_type,      # $12 industry
        None,               # $13 naics_code
        amount,             # $14 value_numeric
        None,               # $15 value_min
        None,               # $16 value_max
        "USD",              # $17 currency
        status,             # $18 status
        department,         # $19 buyer_name
        "City",             # $20 buyer_type
        SOURCE_URL_BASE,    # $21 source_url
        json.dumps([]),     # $22 documents
        json.dumps(raw),    # $23 raw_payload
    )
