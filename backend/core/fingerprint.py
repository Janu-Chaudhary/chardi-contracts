"""Deterministic opportunity IDs for deduplication across scrapes."""

from __future__ import annotations

import hashlib
import re


def _norm(text: str | None) -> str:
    if not text:
        return "none"
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def generate_deterministic_id(
    source_portal: str,
    source_record_id: str | None = None,
    title: str | None = None,
    buyer_name: str | None = None,
    deadline: str | None = None,
) -> str:
    """
    Build a stable SHA-256 hex id from portal + source record id, or a fallback fingerprint.

    When source_record_id is present, it is the primary key for identity.
    Otherwise title, buyer_name, and deadline (date portion) form a fallback fingerprint.
    """
    portal_norm = _norm(source_portal)

    if source_record_id:
        fingerprint = f"{portal_norm}_id_{_norm(source_record_id)}"
    else:
        deadline_date = str(deadline)[:10] if deadline else "none"
        fingerprint = (
            f"{portal_norm}_fallback_{_norm(title)}_{_norm(buyer_name)}_{_norm(deadline_date)}"
        )

    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def portal_label(source_portal: str) -> str:
    """Normalized portal label for logging and metadata."""
    return str(source_portal).strip()
