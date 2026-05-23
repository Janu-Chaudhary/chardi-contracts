"""
Map caleprocure.ca.gov event records to opportunities upsert tuples.

Source fields (from Advanced Search JSON response):
  Event ID        → source_record_id
  Event Name      → title
  Department      → buyer_name
  Published Date  → posted_date
  End Date        → deadline
  Status          → status
  UNSPSC          → industry
  Service Area    → raw_payload only (informational)

DB coverage (23 fields):
  ✅ id                  — SHA-256(portal + Event ID)
  ✅ source_portal        — "caleprocure.ca.gov"
  ✅ source_record_id     — Event ID
  ❌ solicitation_number  — not in search results
  ✅ portal_region        — "State"
  ✅ title                — Event Name
  ❌ description          — not in search results
  ❌ notice_type          — not in search results
  ✅ posted_date          — Published Date (when present in JSON)
  ✅ deadline             — End Date
  ✅ state_region         — "CA" hardcoded
  ✅ industry             — UNSPSC code (when present in JSON)
  ❌ naics_code           — not in search results
  ❌ value_numeric        — not in search results
  ❌ value_min            — not in search results
  ❌ value_max            — not in search results
  ✅ currency             — "USD"
  ✅ status               — derived from Status field
  ✅ buyer_name           — Department
  ✅ buyer_type           — "State"
  ✅ source_url           — constructed from Event ID
  ✅ documents            — [] (no attachments in search results)
  ✅ raw_payload          — full record as JSON
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "caleprocure.ca.gov"
SOURCE_URL_BASE = "https://caleprocure.ca.gov/pages/Events-BS3/event-detail.aspx"


def _parse_date(val: str | None) -> datetime | None:
    """
    Parse Cal eProcure date strings to datetime.

    Format examples:
      "05/22/2026 11:00AM PDT"
      "05/22/2026"
      "04/23/2026"
    """
    if not val or not val.strip():
        return None
    text = val.strip()
    # Strip timezone suffix (PDT/PST/UTC) before parsing
    clean = re.sub(r"\s+[A-Z]{2,4}$", "", text).strip()
    for fmt in ("%m/%d/%Y %I:%M%p", "%m/%d/%Y %I:%M %p", "%m/%d/%Y"):
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue
    return None


def _derive_status(status_text: str | None, deadline: datetime | None) -> str:
    """
    Map Cal eProcure status text to our schema values.

    Portal values: "Posted", "Event Completed", "Cancelled", "Awarded"
    """
    if not status_text:
        if deadline and deadline < datetime.today():
            return "CLOSED"
        return "OPEN"

    s = status_text.strip().lower()
    if "posted" in s:
        return "OPEN"
    if "completed" in s or "closed" in s:
        return "CLOSED"
    if "cancelled" in s or "canceled" in s:
        return "CANCELLED"
    if "awarded" in s:
        return "AWARDED"
    return "OPEN"


def _build_source_url(event_id: str | None) -> str:
    """Construct a direct link to the event detail page."""
    if not event_id:
        return SOURCE_URL_BASE
    return f"{SOURCE_URL_BASE}?BIDID={event_id}"


def map_california_event(record: dict[str, Any]) -> tuple[Any, ...]:
    """
    Map one caleprocure event dict to an opportunities upsert tuple.

    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    event_id = record.get("Event ID", "").strip() or None
    title = record.get("Event Name", "").strip() or "Unknown Event"
    department = record.get("Department", "").strip() or None
    published_date_raw = record.get("Published Date", "").strip() or None
    end_date_raw = record.get("End Date", "").strip() or None
    status_raw = record.get("Status", "").strip() or None
    unspsc = record.get("UNSPSC", "").strip() or None

    posted_date = _parse_date(published_date_raw)
    deadline = _parse_date(end_date_raw)
    status = _derive_status(status_raw, deadline)
    source_url = _build_source_url(event_id)

    record_id = generate_deterministic_id(
        source_portal=SOURCE_PORTAL,
        source_record_id=event_id,
        title=title,
    )

    return (
        record_id,              # $1  id
        SOURCE_PORTAL,          # $2  source_portal
        event_id,               # $3  source_record_id
        None,                   # $4  solicitation_number
        "State",                # $5  portal_region
        title,                  # $6  title
        None,                   # $7  description
        None,                   # $8  notice_type
        posted_date,            # $9  posted_date (Published Date via Advanced Search)
        deadline,               # $10 deadline
        "CA",                   # $11 state_region
        unspsc,                 # $12 industry (UNSPSC code via Advanced Search)
        None,                   # $13 naics_code
        None,                   # $14 value_numeric
        None,                   # $15 value_min
        None,                   # $16 value_max
        "USD",                  # $17 currency
        status,                 # $18 status
        department,             # $19 buyer_name
        "State",                # $20 buyer_type
        source_url,             # $21 source_url
        json.dumps([]),         # $22 documents
        json.dumps({            # $23 raw_payload
            k: v for k, v in record.items()
        }),
    )
