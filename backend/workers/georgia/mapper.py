"""
Map Georgia TGM contract rows to opportunities upsert tuples.

Portal columns (from search results table):
  Contract Number, Contract Name, Supplier, Contract Type,
  Version, Start Date, End Date, Last Modified

DB schema coverage:
  ✅ id                  — SHA-256(portal + Contract Number)
  ✅ source_portal        — "doas.ga.gov"
  ✅ source_record_id     — Contract Number
  ✅ solicitation_number  — Contract Number
  ✅ portal_region        — "State"
  ✅ title                — Contract Name
  ✅ description          — Contract Name + Supplier
  ✅ notice_type          — Contract Type
  ✅ posted_date          — Start Date
  ✅ deadline             — End Date
  ✅ state_region         — "GA"
  ❌ industry             — not in search results
  ❌ naics_code           — not in search results
  ❌ value_numeric        — not published
  ✅ currency             — "USD"
  ✅ status               — OPEN if End Date >= today, else CLOSED
  ✅ buyer_name           — "Georgia DOAS" (state agency)
  ✅ buyer_type           — "State"
  ✅ source_url           — detail URL or constructed
  ✅ documents            — []
  ✅ raw_payload          — full row as JSON
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "doas.ga.gov"
SOURCE_URL_BASE = "https://solutions.sciquest.com/apps/Router/ContractSearch?DocTypeId=2000&OrgName=Georgia"


def _sanitize(val: Any) -> str | None:
    if val is None:
        return None
    text = str(val).strip()
    return text or None


def _parse_date(val: Any) -> datetime | None:
    if not val:
        return None
    text = str(val).strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(text[:10], fmt[:8] if len(fmt) > 8 else fmt)
        except ValueError:
            continue
    return None


def _derive_status(end_date: datetime | None) -> str:
    if end_date is None:
        return "OPEN"
    return "OPEN" if end_date >= datetime.today() else "CLOSED"


def map_georgia_row(row: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one Georgia TGM contract row to an opportunities upsert tuple.
    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    contract_number = _sanitize(row.get("Contract Number") or row.get("Contract #"))
    contract_name = _sanitize(row.get("Contract Name") or row.get("Name")) or "Unknown Contract"
    supplier = _sanitize(row.get("Supplier") or row.get("Vendor"))
    contract_type = _sanitize(row.get("Contract Type") or row.get("Type"))
    start_date = _parse_date(row.get("Start Date"))
    end_date = _parse_date(row.get("End Date"))
    detail_url = _sanitize(row.get("_detail_url")) or SOURCE_URL_BASE

    status = _derive_status(end_date)
    description = contract_name
    if supplier:
        description = f"{contract_name} — Supplier: {supplier}"

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=contract_number,
        title=contract_name,
    )

    return (
        record_id,          # $1  id
        SOURCE_PORTAL,      # $2  source_portal
        contract_number,    # $3  source_record_id
        contract_number,    # $4  solicitation_number
        "State",            # $5  portal_region
        contract_name,      # $6  title
        description,        # $7  description
        contract_type,      # $8  notice_type
        start_date,         # $9  posted_date
        end_date,           # $10 deadline
        "GA",               # $11 state_region
        None,               # $12 industry (not in search results)
        None,               # $13 naics_code
        None,               # $14 value_numeric
        None,               # $15 value_min
        None,               # $16 value_max
        "USD",              # $17 currency
        status,             # $18 status
        "Georgia DOAS",     # $19 buyer_name
        "State",            # $20 buyer_type
        detail_url,         # $21 source_url
        json.dumps([]),     # $22 documents
        json.dumps({k: str(v) for k, v in row.items() if not k.startswith("_")}),  # $23 raw_payload
    )
