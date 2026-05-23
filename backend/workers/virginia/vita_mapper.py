"""
Map Virginia VITA IT Cobblestone contract rows to opportunities upsert tuples.

Source fields (from grid rows):
  vita_contract_number → source_record_id + solicitation_number
  contract_title       → title
  supplier             → raw_payload (vendor, not the buyer)
  contract_end_date    → deadline
  swam                 → raw_payload
  eva_ctr_number       → raw_payload
  detail_url           → source_url

DB coverage (23 fields):
  ✅ id                  — SHA-256(portal + vita_contract_number)
  ✅ source_portal        — "vita.virginia.gov"
  ✅ source_record_id     — vita_contract_number
  ✅ solicitation_number  — vita_contract_number
  ✅ portal_region        — "State"
  ✅ title                — contract_title
  ❌ description          — not in list view
  ❌ notice_type          — not in list view
  ❌ posted_date          — not in list view
  ✅ deadline             — contract_end_date
  ✅ state_region         — "VA"
  ❌ industry             — not in list view
  ❌ naics_code           — not in list view
  ❌ value_numeric        — not in list view
  ❌ value_min            — not in list view
  ❌ value_max            — not in list view
  ✅ currency             — "USD"
  ✅ status               — derived from deadline
  ✅ buyer_name           — "Virginia IT Agency (VITA)" hardcoded
  ✅ buyer_type           — "State"
  ✅ source_url           — detail_url
  ✅ documents            — []
  ✅ raw_payload          — full row as JSON
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "vita.virginia.gov"
BUYER_NAME = "Virginia IT Agency (VITA)"


def _parse_date(val: str | None) -> datetime | None:
    """Parse VITA date strings — format is m/d/yyyy."""
    if not val or not val.strip():
        return None
    text = val.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _derive_status(deadline: datetime | None) -> str:
    if deadline and deadline < datetime.today():
        return "CLOSED"
    return "OPEN"


def map_vita_contract(row: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one VITA grid row dict to an opportunities upsert tuple.

    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    contract_num = row.get("vita_contract_number", "").strip() or None
    title = row.get("contract_title", "").strip() or "Unknown Contract"
    end_date_raw = row.get("contract_end_date", "").strip() or None
    source_url = row.get("detail_url", "").strip() or f"https://vita.cobblestonesystems.com/public/"

    deadline = _parse_date(end_date_raw)
    status = _derive_status(deadline)

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=contract_num,
        title=title,
    )

    return (
        record_id,              # $1  id
        SOURCE_PORTAL,          # $2  source_portal
        contract_num,           # $3  source_record_id
        contract_num,           # $4  solicitation_number
        "State",                # $5  portal_region
        title,                  # $6  title
        None,                   # $7  description
        None,                   # $8  notice_type
        None,                   # $9  posted_date
        deadline,               # $10 deadline
        "VA",                   # $11 state_region
        None,                   # $12 industry
        None,                   # $13 naics_code
        None,                   # $14 value_numeric
        None,                   # $15 value_min
        None,                   # $16 value_max
        "USD",                  # $17 currency
        status,                 # $18 status
        BUYER_NAME,             # $19 buyer_name
        "State",                # $20 buyer_type
        source_url,             # $21 source_url
        json.dumps([]),         # $22 documents
        json.dumps({            # $23 raw_payload
            k: v for k, v in row.items()
        }),
    )
