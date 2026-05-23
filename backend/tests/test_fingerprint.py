"""Tests for deterministic opportunity IDs."""

from backend.core.fingerprint import generate_deterministic_id


def test_deterministic_id_stable_with_source_record_id():
    first = generate_deterministic_id("SAM.gov", source_record_id="NOTICE-123")
    second = generate_deterministic_id("SAM.gov", source_record_id="NOTICE-123")
    assert first == second
    assert len(first) == 64


def test_fallback_mode_without_source_record_id():
    first = generate_deterministic_id(
        "SAM.gov",
        title="Cloud Services",
        buyer_name="Department of Defense",
        deadline="2025-12-31T23:59:00",
    )
    second = generate_deterministic_id(
        "SAM.gov",
        title="Cloud Services",
        buyer_name="Department of Defense",
        deadline="2025-12-31",
    )
    assert first == second
    assert first != generate_deterministic_id(
        "SAM.gov",
        title="Different Title",
        buyer_name="Department of Defense",
        deadline="2025-12-31",
    )
