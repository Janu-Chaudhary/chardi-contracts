"""
Map NYSCR (nyscr.ny.gov) PDF records to opportunities upsert tuples.

Source fields (from PDF):
  CR#        → source_record_id
  Title      → title
  Agency     → buyer_name  (falls back to Company for Contractor Ads)
  Division   → raw_payload only
  Issue Date → posted_date
  Due date   → deadline
  Location   → raw_payload only
  Category   → industry
  Ad type    → notice_type

DB coverage (23 fields):
  ✅ id                  — SHA-256(portal + CR#)
  ✅ source_portal        — "nyscr.ny.gov"
  ✅ source_record_id     — CR#
  ❌ solicitation_number  — not in PDF
  ✅ portal_region        — "State"
  ✅ title                — Title
  ❌ description          — not in PDF
  ✅ notice_type          — Ad type
  ✅ posted_date          — Issue Date
  ✅ deadline             — Due date
  ✅ state_region         — "NY" hardcoded
  ✅ industry             — Category
  ❌ naics_code           — not in PDF
  ❌ value_numeric        — not in PDF
  ❌ value_min            — not in PDF
  ❌ value_max            — not in PDF
  ✅ currency             — "USD"
  ✅ status               — derived from deadline
  ✅ buyer_name           — Agency (or Company)
  ✅ buyer_type           — "State" (Agency) or "Private" (Company)
  ✅ source_url           — constructed from CR#
  ✅ documents            — []
  ✅ raw_payload          — full record as JSON
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "nyscr.ny.gov"
SOURCE_URL_BASE = "https://www.nyscr.ny.gov/Ads/Details/"


def _parse_date(val: str | None) -> datetime | None:
    """Parse NYSCR date strings — format is m/d/yyyy or mm/dd/yyyy."""
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
    """All records in the PDF are open opportunities — close if deadline passed."""
    if deadline and deadline < datetime.today():
        return "CLOSED"
    return "OPEN"


def _build_source_url(cr_number: str | None) -> str:
    """Construct a direct link to the opportunity detail page."""
    if not cr_number:
        return SOURCE_URL_BASE
    return f"{SOURCE_URL_BASE}{cr_number}"


def map_newyork_event(record: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one NYSCR PDF record dict to an opportunities upsert tuple.

    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    cr_number = record.get("CR#", "").strip() or None
    title = record.get("Title", "").strip() or "Unknown Opportunity"

    # Agency for government ads, Company for contractor ads
    agency = record.get("Agency", "").strip() or None
    company = record.get("Company", "").strip() or None
    buyer_name = agency or company
    buyer_type = "State" if agency else "Private"

    issue_date_raw = record.get("Issue Date", "").strip() or None
    due_date_raw = record.get("Due date", "").strip() or None
    category = record.get("Category", "").strip() or None
    ad_type = record.get("Ad type", "").strip() or None

    posted_date = _parse_date(issue_date_raw)
    deadline = _parse_date(due_date_raw)
    status = _derive_status(deadline)
    source_url = _build_source_url(cr_number)

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=cr_number,
        title=title,
    )

    return (
        record_id,              # $1  id
        SOURCE_PORTAL,          # $2  source_portal
        cr_number,              # $3  source_record_id
        None,                   # $4  solicitation_number
        "State",                # $5  portal_region
        title,                  # $6  title
        None,                   # $7  description
        ad_type,                # $8  notice_type
        posted_date,            # $9  posted_date
        deadline,               # $10 deadline
        "NY",                   # $11 state_region
        category,               # $12 industry
        None,                   # $13 naics_code
        None,                   # $14 value_numeric
        None,                   # $15 value_min
        None,                   # $16 value_max
        "USD",                  # $17 currency
        status,                 # $18 status
        buyer_name,             # $19 buyer_name
        buyer_type,             # $20 buyer_type
        source_url,             # $21 source_url
        json.dumps([]),         # $22 documents
        json.dumps({            # $23 raw_payload
            k: v for k, v in record.items()
        }),
    )
