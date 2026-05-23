"""Tests for SAM.gov notice mapping."""

import json
from pathlib import Path

from backend.core.fingerprint import generate_deterministic_id
from backend.workers.samgov.mapper import SOURCE_PORTAL, map_notice_to_tuple

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "samgov_notice_sample.json"
EXPECTED_TUPLE_LEN = 23


def _load_sample() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_map_notice_tuple_shape():
    item = _load_sample()
    row = map_notice_to_tuple(item)
    assert isinstance(row, tuple)
    assert len(row) == EXPECTED_TUPLE_LEN


def test_map_notice_deterministic_id():
    item = _load_sample()
    row = map_notice_to_tuple(item)
    expected = generate_deterministic_id(SOURCE_PORTAL, source_record_id=item["noticeId"])
    assert row[0] == expected


def test_map_notice_status_open():
    item = _load_sample()
    row = map_notice_to_tuple(item)
    assert row[17] == "OPEN"


def test_map_notice_status_closed_when_inactive():
    item = _load_sample()
    item["active"] = "No"
    row = map_notice_to_tuple(item)
    assert row[17] == "CLOSED"


def test_map_notice_buyer_extraction():
    item = _load_sample()
    row = map_notice_to_tuple(item)
    assert row[18] == "Department of Defense"
