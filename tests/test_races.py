"""
Tests for app/routers/races.py: the discipline/format/priority validation
(`_validate_race`) as a pure unit test, plus a few integration tests through
the real API + DB to make sure invalid races are actually rejected end-to-end
and valid ones round-trip correctly.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.routers.races import DISCIPLINE_FORMATS, _validate_race
from app.schemas import RaceIn


def _race(**overrides):
    defaults = {
        "athlete_id": "B",
        "name": "Half de Nice",
        "date": "2026-09-20",
        "discipline": "triathlon",
        "format": "half_ironman",
        "priority": "B",
    }
    defaults.update(overrides)
    return RaceIn(**defaults)


# ── _validate_race (unit) ─────────────────────────────────────────

def test_validate_race_accepts_valid_combination():
    _validate_race(_race())  # should not raise


@pytest.mark.parametrize("discipline,valid_format", [
    ("triathlon", "olympic"),
    ("running", "marathon"),
    ("cycling", "gran_fondo"),
    ("swim", "open_water"),
])
def test_validate_race_accepts_every_discipline_with_its_own_valid_format(discipline, valid_format):
    _validate_race(_race(discipline=discipline, format=valid_format))


def test_validate_race_rejects_unknown_discipline():
    with pytest.raises(HTTPException) as exc_info:
        _validate_race(_race(discipline="triathlon_but_typo", format="olympic"))
    assert exc_info.value.status_code == 422


def test_validate_race_rejects_format_that_belongs_to_a_different_discipline():
    # "marathon" is a running format, not valid for triathlon.
    with pytest.raises(HTTPException) as exc_info:
        _validate_race(_race(discipline="triathlon", format="marathon"))
    assert exc_info.value.status_code == 422


def test_validate_race_rejects_invalid_priority():
    with pytest.raises(HTTPException) as exc_info:
        _validate_race(_race(priority="Z"))
    assert exc_info.value.status_code == 422


def test_discipline_formats_table_is_internally_consistent():
    # Guard against a future edit adding a discipline without formats, or vice versa.
    for discipline, formats in DISCIPLINE_FORMATS.items():
        assert "other" in formats, f"{discipline} should always allow an 'other' fallback format"
        assert len(formats) == len(set(formats)), f"{discipline} has duplicate formats"


# ── Through the API (integration) ─────────────────────────────────

def test_create_race_rejects_invalid_format_via_api(client):
    resp = client.post("/races/", json={
        "athlete_id": "B",
        "name": "Bad race",
        "date": "2026-09-20",
        "discipline": "swim",
        "format": "marathon",  # not a valid swim format
        "priority": "B",
    })
    assert resp.status_code == 422


def test_create_and_list_race_round_trips_via_api(client, seeded_athletes):
    resp = client.post("/races/", json={
        "athlete_id": "H",
        "name": "10k de printemps",
        "date": "2027-04-12",
        "discipline": "running",
        "format": "10k",
        "priority": "C",
        "target_time": "0:45",
    })
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "10k de printemps"
    assert created["athlete_id"] == "H"

    listed = client.get("/races/", params={"athlete_id": "H"}).json()
    assert any(r["id"] == created["id"] for r in listed)


def test_shared_race_athlete_id_none_is_visible_to_both_athletes(client, seeded_athletes):
    resp = client.post("/races/", json={
        "athlete_id": None,
        "name": "Course en couple",
        "date": "2027-06-01",
        "discipline": "triathlon",
        "format": "olympic",
        "priority": "A",
    })
    assert resp.status_code == 201

    for athlete_id in ("B", "H"):
        listed = client.get("/races/", params={"athlete_id": athlete_id}).json()
        assert any(r["name"] == "Course en couple" for r in listed)
