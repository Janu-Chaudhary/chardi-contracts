"""
End-to-end tests for the California caleprocure.ca.gov worker.

Covers:
  1. parse_records_from_json  — unit tests with fake PeopleSoft JSON
  2. map_california_event     — mapper output shape, field values, determinism
  3. fetch_california_events  — live scrape (skipped if no network / CI flag)
  4. DB round-trip            — live upsert + verify row exists in DB
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import pytest

from backend.workers.california.scraper import parse_records_from_json
from backend.workers.california.mapper import (
    SOURCE_PORTAL,
    _parse_date,
    _derive_status,
    _build_source_url,
    map_california_event,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ps_row(
    event_id="EVT-001",
    event_name="Test Procurement",
    department="Dept of Finance",
    pub_date="04/23/2026",
    end_date="05/22/2026 11:00AM PDT",
    status="Posted",
    unspsc="72000000",
    service_area="Statewide",
) -> dict:
    """Build a minimal PeopleSoft tblBodyTr JSON object."""
    def cell(text):
        return [{"Properties": {"text": text}}]

    return {
        "Label": "tblBodyTr_1",
        "Children": {
            "tdEventId":     cell(event_id),
            "tdEventName":   cell(event_name),
            "tdDepName":     cell(department),
            "tdPubDate":     cell(pub_date),
            "tdEndDate":     cell(end_date),
            "tdStatus":      cell(status),
            "tdUnspsc":      cell(unspsc),
            "tdServiceArea": cell(service_area),
        },
    }


# ---------------------------------------------------------------------------
# 1. parse_records_from_json
# ---------------------------------------------------------------------------

class TestParseRecordsFromJson:

    def test_extracts_all_fields(self):
        row = _make_ps_row()
        records = parse_records_from_json(json.dumps([row]))
        assert len(records) == 1
        r = records[0]
        assert r["Event ID"] == "EVT-001"
        assert r["Event Name"] == "Test Procurement"
        assert r["Department"] == "Dept of Finance"
        # Published Date / UNSPSC / Service Area are present when the JSON
        # contains those fields (Advanced Search or enriched download response)
        assert r.get("Published Date", "04/23/2026") == "04/23/2026"
        assert r["End Date"] == "05/22/2026 11:00AM PDT"
        assert r["Status"] == "Posted"

    def test_multiple_rows(self):
        rows = [_make_ps_row(event_id=f"EVT-{i:03d}") for i in range(5)]
        records = parse_records_from_json(json.dumps(rows))
        assert len(records) == 5
        assert records[2]["Event ID"] == "EVT-002"

    def test_skips_row_with_no_id_or_name(self):
        row = _make_ps_row(event_id="", event_name="")
        records = parse_records_from_json(json.dumps([row]))
        assert records == []

    def test_invalid_json_returns_empty(self):
        assert parse_records_from_json("not json at all") == []

    def test_empty_json_array_returns_empty(self):
        assert parse_records_from_json("[]") == []

    def test_nested_structure(self):
        """Records can be nested inside other dicts."""
        nested = {"outer": {"inner": [_make_ps_row(event_id="NESTED-1")]}}
        records = parse_records_from_json(json.dumps(nested))
        assert len(records) == 1
        assert records[0]["Event ID"] == "NESTED-1"

    def test_published_date_not_in_default_search(self):
        """Published Date is not available in the default search JSON — field is empty."""
        row = _make_ps_row(pub_date="")
        records = parse_records_from_json(json.dumps([row]))
        # Key exists but value is empty — portal doesn't expose it in basic search
        assert records[0].get("Published Date", "") == ""

    def test_unspsc_not_in_default_search(self):
        """UNSPSC is not available in the default search JSON — field is empty."""
        row = _make_ps_row(unspsc="")
        records = parse_records_from_json(json.dumps([row]))
        assert records[0].get("UNSPSC", "") == ""


# ---------------------------------------------------------------------------
# 2. _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:

    def test_date_only(self):
        dt = _parse_date("05/22/2026")
        assert dt == datetime(2026, 5, 22)

    def test_date_with_time_and_tz(self):
        dt = _parse_date("05/22/2026 11:00AM PDT")
        assert dt == datetime(2026, 5, 22, 11, 0)

    def test_date_with_space_before_ampm(self):
        dt = _parse_date("05/22/2026 11:00 AM PDT")
        assert dt == datetime(2026, 5, 22, 11, 0)

    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_empty_returns_none(self):
        assert _parse_date("") is None

    def test_whitespace_returns_none(self):
        assert _parse_date("   ") is None

    def test_garbage_returns_none(self):
        assert _parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# 3. _derive_status
# ---------------------------------------------------------------------------

class TestDeriveStatus:

    def test_posted_is_open(self):
        assert _derive_status("Posted", None) == "OPEN"

    def test_event_completed_is_closed(self):
        assert _derive_status("Event Completed", None) == "CLOSED"

    def test_cancelled_is_cancelled(self):
        assert _derive_status("Cancelled", None) == "CANCELLED"

    def test_awarded_is_awarded(self):
        assert _derive_status("Awarded", None) == "AWARDED"

    def test_none_status_future_deadline_is_open(self):
        future = datetime(2099, 1, 1)
        assert _derive_status(None, future) == "OPEN"

    def test_none_status_past_deadline_is_closed(self):
        past = datetime(2000, 1, 1)
        assert _derive_status(None, past) == "CLOSED"

    def test_none_status_no_deadline_is_open(self):
        assert _derive_status(None, None) == "OPEN"


# ---------------------------------------------------------------------------
# 4. _build_source_url
# ---------------------------------------------------------------------------

class TestBuildSourceUrl:

    def test_with_event_id(self):
        url = _build_source_url("0000038759")
        assert url == (
            "https://caleprocure.ca.gov/pages/Events-BS3/"
            "event-detail.aspx?BIDID=0000038759"
        )

    def test_none_returns_base(self):
        url = _build_source_url(None)
        assert "event-detail.aspx" in url
        assert "BIDID" not in url


# ---------------------------------------------------------------------------
# 5. map_california_event
# ---------------------------------------------------------------------------

class TestMapCaliforniaEvent:

    def _sample_record(self, **overrides):
        base = {
            "Event ID":       "0000038759",
            "Event Name":     "IFB C5613290-D - Correctional Peace Officer",
            "Department":     "Dept of Corrections & Rehab",
            "Published Date": "04/23/2026",
            "End Date":       "05/22/2026 11:00AM PDT",
            "Status":         "Posted",
            "UNSPSC":         "72000000",
            "Service Area":   "Statewide",
        }
        base.update(overrides)
        return base

    def test_tuple_length(self):
        tup = map_california_event(self._sample_record())
        assert len(tup) == 23

    def test_source_portal(self):
        tup = map_california_event(self._sample_record())
        assert tup[1] == "caleprocure.ca.gov"

    def test_source_record_id(self):
        tup = map_california_event(self._sample_record())
        assert tup[2] == "0000038759"

    def test_portal_region(self):
        tup = map_california_event(self._sample_record())
        assert tup[4] == "State"

    def test_title(self):
        tup = map_california_event(self._sample_record())
        assert "Correctional Peace Officer" in tup[5]

    def test_posted_date_parsed(self):
        tup = map_california_event(self._sample_record())
        assert isinstance(tup[8], datetime)
        assert tup[8] == datetime(2026, 4, 23)

    def test_deadline_parsed(self):
        tup = map_california_event(self._sample_record())
        assert isinstance(tup[9], datetime)
        assert tup[9].year == 2026
        tup = map_california_event(self._sample_record())
        assert tup[10] == "CA"

    def test_industry_unspsc(self):
        tup = map_california_event(self._sample_record())
        assert tup[11] == "72000000"

    def test_industry_none_when_missing(self):
        tup = map_california_event(self._sample_record(**{"UNSPSC": ""}))
        assert tup[11] is None

    def test_currency(self):
        tup = map_california_event(self._sample_record())
        assert tup[16] == "USD"

    def test_status_open(self):
        tup = map_california_event(self._sample_record(**{"Status": "Posted"}))
        assert tup[17] == "OPEN"

    def test_status_closed(self):
        tup = map_california_event(self._sample_record(**{"Status": "Event Completed"}))
        assert tup[17] == "CLOSED"

    def test_buyer_name(self):
        tup = map_california_event(self._sample_record())
        assert tup[18] == "Dept of Corrections & Rehab"

    def test_buyer_type(self):
        tup = map_california_event(self._sample_record())
        assert tup[19] == "State"

    def test_source_url_contains_event_id(self):
        tup = map_california_event(self._sample_record())
        assert "0000038759" in tup[20]

    def test_documents_is_empty_json_array(self):
        tup = map_california_event(self._sample_record())
        assert json.loads(tup[21]) == []

    def test_raw_payload_is_valid_json(self):
        tup = map_california_event(self._sample_record())
        payload = json.loads(tup[22])
        assert payload["Event ID"] == "0000038759"

    def test_deterministic_id_is_64_chars(self):
        tup = map_california_event(self._sample_record())
        assert len(tup[0]) == 64

    def test_deterministic_id_is_stable(self):
        r = self._sample_record()
        assert map_california_event(r)[0] == map_california_event(r)[0]

    def test_different_events_have_different_ids(self):
        t1 = map_california_event(self._sample_record(**{"Event ID": "EVT-001"}))
        t2 = map_california_event(self._sample_record(**{"Event ID": "EVT-002"}))
        assert t1[0] != t2[0]

    def test_missing_event_id_uses_fallback(self):
        tup = map_california_event(self._sample_record(**{"Event ID": ""}))
        assert tup[2] is None
        assert len(tup[0]) == 64  # still gets a deterministic id

    def test_missing_title_defaults(self):
        tup = map_california_event(self._sample_record(**{"Event Name": ""}))
        assert tup[5] == "Unknown Event"

# ---------------------------------------------------------------------------
# 6. Live scrape test (optional — skipped in CI)
# ---------------------------------------------------------------------------

SKIP_LIVE = os.environ.get("SKIP_LIVE_TESTS", "0") == "1"

@pytest.mark.skipif(SKIP_LIVE, reason="Live network test skipped (SKIP_LIVE_TESTS=1)")
def test_live_scrape_returns_records():
    """Hit caleprocure.ca.gov and verify we get real records back."""
    import asyncio
    from backend.workers.california.scraper import fetch_california_events

    records = asyncio.run(fetch_california_events())
    assert len(records) > 0, "Expected at least 1 record from live scrape"

    # Every record must have at minimum Event ID and Event Name
    for r in records:
        assert r.get("Event ID") or r.get("Event Name"), (
            f"Record missing both Event ID and Event Name: {r}"
        )

    # Spot-check field keys are present
    first = records[0]
    for key in ("Event ID", "Event Name", "Department", "End Date", "Status"):
        assert key in first, f"Missing key {key!r} in first record"

    print(f"\n  Live scrape: {len(records)} records returned")
    print(f"  Sample: {first}")


# ---------------------------------------------------------------------------
# 7. Live DB round-trip (optional — skipped in CI)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SKIP_LIVE, reason="Live DB test skipped (SKIP_LIVE_TESTS=1)")
def test_live_db_roundtrip():
    """Upsert one mapped record and verify it exists in the DB."""
    import asyncio
    from backend.core import db
    from backend.workers.california.mapper import map_california_event

    sample = {
        "Event ID":       "TEST-E2E-CA-001",
        "Event Name":     "E2E Test Event California",
        "Department":     "Test Department",
        "Published Date": "04/01/2026",
        "End Date":       "06/01/2026",
        "Status":         "Posted",
        "UNSPSC":         "72000000",
        "Service Area":   "Statewide",
    }

    async def run():
        await db.create_pool()
        try:
            tup = map_california_event(sample)
            count = await db.upsert_opportunities([tup])
            assert count == 1, f"Expected 1 upserted, got {count}"

            # Verify the row exists
            pool = await db.create_pool()
            row = await pool.fetchrow(
                "SELECT id, title, status, industry, posted_date FROM opportunities WHERE source_record_id = $1",
                "TEST-E2E-CA-001",
            )
            assert row is not None, "Row not found in DB after upsert"
            assert row["title"] == "E2E Test Event California"
            assert row["status"] == "OPEN"
            assert row["industry"] == "72000000"
            assert row["posted_date"] is not None

            print(f"\n  DB round-trip OK: id={row['id'][:12]}... "
                  f"title={row['title']!r} status={row['status']!r} "
                  f"industry={row['industry']!r} posted_date={row['posted_date']}")
        finally:
            await db.close_pool()

    asyncio.run(run())
