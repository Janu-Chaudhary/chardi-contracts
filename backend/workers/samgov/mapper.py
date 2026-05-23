"""Map SAM.gov notice JSON into opportunities upsert tuples."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from backend.core.fingerprint import generate_deterministic_id

SOURCE_PORTAL = "SAM.gov"


def sanitize_date(value: str | None) -> datetime | None:
    """
    Normalize SAM.gov date strings to datetime objects for PostgreSQL timestamptz.

    Accepts YYYY-MM-DD, MM/dd/yyyy, and ISO datetime strings with offsets.
    Returns None when parsing fails or value is empty.
    """
    if not value or not str(value).strip():
        return None

    text = str(value).strip()

    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt)
        except ValueError:
            continue

    iso_match = re.match(
        r"^(\d{4}-\d{2}-\d{2})(?:T[\d:.+-Z]+)?",
        text,
    )
    if iso_match:
        date_part = iso_match.group(1)
        if "T" in text:
            try:
                normalized = text.replace("Z", "+00:00")
                return datetime.fromisoformat(normalized)
            except ValueError:
                return datetime.strptime(date_part, "%Y-%m-%d")
        return datetime.strptime(date_part, "%Y-%m-%d")

    return None


def _first_buyer_segment(full_parent_path_name: str | None) -> str | None:
    if not full_parent_path_name:
        return None
    segment = str(full_parent_path_name).split(".")[0].strip()
    return segment or None


def map_notice_to_tuple(item: dict) -> tuple:
    """
    Map one SAM.gov notice dict to an opportunities upsert tuple.

    Tuple order matches backend.core.db.OPPORTUNITY_UPSERT_SQL ($1..$23).
    """
    notice_id = item.get("noticeId")
    posted = sanitize_date(item.get("postedDate"))
    deadline = sanitize_date(item.get("responseDeadLine"))
    pop = item.get("placeOfPerformance") or {}
    pop_state = pop.get("state") or {}
    state_code = pop_state.get("code") if isinstance(pop_state, dict) else None

    resource_links = item.get("resourceLinks") or []
    documents = json.dumps(
        [{"title": "Attachment", "url": link} for link in resource_links if link]
    )
    raw_payload = json.dumps(item)

    status = "OPEN" if item.get("active") == "Yes" else "CLOSED"
    title = (item.get("title") or "Untitled Notice").strip()
    description = (
        item.get("description")
        or item.get("additionalInfoLink")
        or ""
    )

    source_url = item.get("uiLink") or ""
    if not source_url and notice_id:
        source_url = f"https://sam.gov/opp/{notice_id}/view"

    return (
        generate_deterministic_id(SOURCE_PORTAL, source_record_id=notice_id),
        SOURCE_PORTAL,
        notice_id,
        item.get("solicitationNumber"),
        "Federal",
        title,
        description,
        item.get("type"),
        posted,
        deadline,
        state_code,
        item.get("naicsCode"),
        item.get("naicsCode"),
        None,
        None,
        None,
        "USD",
        status,
        _first_buyer_segment(item.get("fullParentPathName")),
        item.get("organizationType"),
        source_url,
        documents,
        raw_payload,
    )
