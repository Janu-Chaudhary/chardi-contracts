"""
Map Virginia eVA Non-IT Solr contract docs to opportunities upsert tuples.

Source fields (from Solr JSON):
  id                  → source_record_id  (e.g. "CN-CTR052340")
  contract_num        → solicitation_number
  contract_title      → title
  vendor_name         → raw_payload (buyer is the agency)
  agency_name         → buyer_name
  auth_dept_nm        → raw_payload
  start_date          → posted_date
  expiration_date     → deadline
  reg_status          → status derivation
  type_s              → notice_type ("Contract")

DB coverage (23 fields):
  ✅ id                  — SHA-256(portal + Solr id)
  ✅ source_portal        — "eva.virginia.gov"
  ✅ source_record_id     — Solr id (CN-CTRxxxxxx)
  ✅ solicitation_number  — contract_num
  ✅ portal_region        — "State"
  ✅ title                — contract_title
  ❌ description          — not in Solr
  ✅ notice_type          — type_s ("Contract")
  ✅ posted_date          — start_date
  ✅ deadline             — expiration_date
  ✅ state_region         — "VA"
  ❌ industry             — not in Solr list
  ❌ naics_code           — not in Solr list
  ❌ value_numeric        — not in Solr list
  ❌ value_min            — not in Solr list
  ❌ value_max            — not in Solr list
  ✅ currency             — "USD"
  ✅ status               — derived from reg_status / expiration_date
  ✅ buyer_name           — agency_name
  ✅ buyer_type           — "State"
  ✅ source_url           — constructed from contract_num
  ✅ documents            — []
  ✅ raw_payload          — full Solr doc as JSON
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "eva.virginia.gov"
SOURCE_URL_BASE = "https://mvendor.cgieva.com/Vendor/public/ContractDetails.jsp?contractId="


def _parse_date(val: str | None) -> datetime | None:
    """Parse ISO-8601 Solr date strings like '2026-05-20T04:00:00Z'."""
    if not val or not val.strip():
        return None
    text = val.strip().rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if v is not None)
    return str(value)


def _derive_status(reg_status: str | None, deadline: datetime | None) -> str:
    if reg_status:
        s = reg_status.strip().lower()
        if "cancel" in s:
            return "CANCELLED"
        if "award" in s:
            return "AWARDED"
    if deadline and deadline < datetime.today():
        return "CLOSED"
    return "OPEN"


def _build_source_url(contract_num: str | None) -> str:
    if not contract_num:
        return SOURCE_URL_BASE
    return f"{SOURCE_URL_BASE}{contract_num}"


def map_eva_contract(doc: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one eVA Solr contract doc to an opportunities upsert tuple.

    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    solr_id = _as_str(doc.get("id")).strip() or None
    contract_num = _as_str(doc.get("contract_num") or doc.get("contract_number")).strip() or None
    title = _as_str(doc.get("contract_title")).strip() or "Unknown Contract"
    agency = _as_str(doc.get("agency_name")).strip() or None
    start_raw = _as_str(doc.get("start_date")).strip() or None
    expiry_raw = _as_str(doc.get("expiration_date")).strip() or None
    reg_status = _as_str(doc.get("reg_status")).strip() or None
    notice_type = _as_str(doc.get("type_s")).strip() or "Contract"

    posted_date = _parse_date(start_raw)
    deadline = _parse_date(expiry_raw)
    status = _derive_status(reg_status, deadline)
    source_url = _build_source_url(contract_num)

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=solr_id,
        title=title,
    )

    return (
        record_id,              # $1  id
        SOURCE_PORTAL,          # $2  source_portal
        solr_id,                # $3  source_record_id
        contract_num,           # $4  solicitation_number
        "State",                # $5  portal_region
        title,                  # $6  title
        None,                   # $7  description
        notice_type,            # $8  notice_type
        posted_date,            # $9  posted_date
        deadline,               # $10 deadline
        "VA",                   # $11 state_region
        None,                   # $12 industry
        None,                   # $13 naics_code
        None,                   # $14 value_numeric
        None,                   # $15 value_min
        None,                   # $16 value_max
        "USD",                  # $17 currency
        status,                 # $18 status
        agency,                 # $19 buyer_name
        "State",                # $20 buyer_type
        source_url,             # $21 source_url
        json.dumps([]),         # $22 documents
        json.dumps({            # $23 raw_payload
            k: _as_str(v) for k, v in doc.items()
        }),
    )
