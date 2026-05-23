"""Unit tests for the Texas TxSmartBuy mapper."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from backend.workers.texas.mapper import (
    SOURCE_PORTAL,
    _derive_status,
    _first_nigp,
    _parse_date,
    _sanitize,
    map_texas_row,
)

# ---------------------------------------------------------------------------
# Sample rows matching the real CSV structure
# ---------------------------------------------------------------------------

SAMPLE_ROW_FULL = {
    "Contract": "031-A1",
    "Description": "HVAC Air Filters",
    "Contract Type": "Term",
    "Contract Group": "TxSmartBuy",
    "Start Date": "9/25/2025",
    "End Date": "8/31/2026",
    "NIGP(s)": "03145",
    "FED": float("nan"),
}

SAMPLE_ROW_TXMAS = {
    "Contract": "177-A1",
    "Description": "IT Hardware",
    "Contract Type": "TXMAS",
    "Contract Group": "TxSmartBuy",
    "Start Date": "1/1/2023",
    "End Date": "12/31/2027",
    "NIGP(s)": "20400;20401;20402",
    "FED": "GSA GS-07F-0362T",
}

SAMPLE_ROW_EXPIRED = {
    "Contract": "999-Z9",
    "Description": "Old Supplies",
    "Contract Type": "Term",
    "Contract Group": "Managed",
    "Start Date": "1/1/2020",
    "End Date": "12/31/2022",
    "NIGP(s)": "09060",
    "FED": float("nan"),
}


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestSanitize:
    def test_normal_string(self):
        assert _sanitize("hello") == "hello"

    def test_strips_whitespace(self):
        assert _sanitize("  hello  ") == "hello"

    def test_nan_returns_none(self):
        import math
        assert _sanitize(float("nan")) is None

    def test_none_returns_none(self):
        assert _sanitize(None) is None

    def test_empty_string_returns_none(self):
        assert _sanitize("") is None

    def test_whitespace_only_returns_none(self):
        assert _sanitize("   ") is None


class TestParseDate:
    def test_mm_dd_yyyy(self):
        result = _parse_date("9/25/2025")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 9
        assert result.day == 25

    def test_yyyy_mm_dd(self):
        result = _parse_date("2025-09-25")
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_nan_returns_none(self):
        assert _parse_date(float("nan")) is None

    def test_empty_returns_none(self):
        assert _parse_date("") is None


class TestDeriveStatus:
    def test_future_date_is_open(self):
        future = datetime(2099, 12, 31)
        assert _derive_status(future) == "OPEN"

    def test_past_date_is_closed(self):
        past = datetime(2020, 1, 1)
        assert _derive_status(past) == "CLOSED"

    def test_none_defaults_to_open(self):
        assert _derive_status(None) == "OPEN"


class TestFirstNigp:
    def test_single_code(self):
        assert _first_nigp("03145") == "03145"

    def test_multi_code_returns_first(self):
        assert _first_nigp("05040;05060;78545") == "05040"

    def test_none_returns_none(self):
        assert _first_nigp(None) is None

    def test_empty_returns_none(self):
        assert _first_nigp("") is None


# ---------------------------------------------------------------------------
# Full tuple mapping tests
# ---------------------------------------------------------------------------

class TestMapTexasRow:
    def test_tuple_length(self):
        """Tuple must have exactly 23 fields to match OPPORTUNITY_UPSERT_SQL."""
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert len(result) == 23

    def test_source_portal(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[1] == SOURCE_PORTAL
        assert result[1] == "txsmartbuy.gov"

    def test_source_record_id(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[2] == "031-A1"

    def test_solicitation_number_nan_is_none(self):
        """FED=NaN should map to None for solicitation_number."""
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[3] is None

    def test_solicitation_number_fed_populated(self):
        """FED value should populate solicitation_number."""
        result = map_texas_row(SAMPLE_ROW_TXMAS)
        assert result[3] == "GSA GS-07F-0362T"

    def test_portal_region(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[4] == "State"

    def test_title(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[5] == "HVAC Air Filters"

    def test_notice_type(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[7] == "Term"
        result2 = map_texas_row(SAMPLE_ROW_TXMAS)
        assert result2[7] == "TXMAS"

    def test_posted_date_is_datetime(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert isinstance(result[8], datetime)

    def test_deadline_is_datetime(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert isinstance(result[9], datetime)

    def test_state_region(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[10] == "TX"

    def test_industry_single_nigp(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[11] == "03145"

    def test_industry_multi_nigp_takes_first(self):
        result = map_texas_row(SAMPLE_ROW_TXMAS)
        assert result[11] == "20400"

    def test_naics_code_is_none(self):
        """NAICS is not available in TxSmartBuy CSV."""
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[12] is None

    def test_value_fields_are_none(self):
        """Contract values are not in the CSV export."""
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[13] is None  # value_numeric
        assert result[14] is None  # value_min
        assert result[15] is None  # value_max

    def test_currency(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[16] == "USD"

    def test_status_open(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[17] == "OPEN"

    def test_status_closed_for_expired(self):
        result = map_texas_row(SAMPLE_ROW_EXPIRED)
        assert result[17] == "CLOSED"

    def test_buyer_name(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[18] == "TxSmartBuy"

    def test_buyer_type(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[19] == "State"

    def test_source_url_contains_contract_id(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert "031-A1" in result[20]
        assert "txsmartbuy.gov" in result[20]

    def test_documents_is_empty_json_array(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert result[21] == "[]"
        assert json.loads(result[21]) == []

    def test_raw_payload_is_valid_json(self):
        result = map_texas_row(SAMPLE_ROW_FULL)
        payload = json.loads(result[22])
        assert isinstance(payload, dict)
        assert "Contract" in payload
        assert payload["Contract"] == "031-A1"

    def test_deterministic_id_is_64_chars(self):
        """SHA-256 hex digest is always 64 characters."""
        result = map_texas_row(SAMPLE_ROW_FULL)
        assert len(result[0]) == 64

    def test_deterministic_id_is_stable(self):
        """Same input must always produce the same ID."""
        id1 = map_texas_row(SAMPLE_ROW_FULL)[0]
        id2 = map_texas_row(SAMPLE_ROW_FULL)[0]
        assert id1 == id2

    def test_different_contracts_have_different_ids(self):
        id1 = map_texas_row(SAMPLE_ROW_FULL)[0]
        id2 = map_texas_row(SAMPLE_ROW_TXMAS)[0]
        assert id1 != id2
