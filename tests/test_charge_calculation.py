"""
Unit tests for the "charge" (training load) calculation helpers, duplicated
across app/routers/meals.py and app/routers/wellness.py. These feed the
Dashboard calendar coloring, the Nutrition page's meal generation, and the
AI coach's context -- getting the high/med/low/rest thresholds wrong (or
having the two implementations drift apart) would be very easy to miss.

No DB needed: these functions only read `.duration` off whatever objects
they're given, so we use lightweight stand-ins instead of persisting rows.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.routers.meals import _compute_charge
from app.routers.wellness import _charge_for_athlete_day, _charge_for_day


def _session(duration: str):
    return SimpleNamespace(duration=duration)


# ── app/routers/meals.py::_compute_charge ────────────────────────

def test_compute_charge_no_sessions_is_rest():
    assert _compute_charge([], []) == "rest"


def test_compute_charge_uses_the_max_of_the_two_athletes():
    # B has a light day (0.5h), H has a heavy day (2h) -> charge should be "high",
    # driven by H, not averaged or driven by B.
    sessions_b = [_session("30min")]
    sessions_h = [_session("2h")]
    assert _compute_charge(sessions_b, sessions_h) == "high"


@pytest.mark.parametrize(
    "durations,expected",
    [
        (["30min"], "low"),       # 0.5h
        (["45min"], "low"),       # 0.75h
        (["1h"], "med"),          # exactly 1h -> med (>=1 boundary)
        (["1h", "30min"], "med"), # 1.5h
        (["2h"], "high"),         # exactly 2h -> high (>=2 boundary)
        (["1h", "1h"], "high"),   # 2h combined, same athlete
        (["3h+"], "high"),
    ],
)
def test_compute_charge_thresholds(durations, expected):
    sessions_b = [_session(d) for d in durations]
    assert _compute_charge(sessions_b, []) == expected


def test_compute_charge_unknown_duration_defaults_to_one_hour():
    # DUR_WEIGHT.get(duration, 1.0) -- an unrecognised duration string should
    # be treated as 1h, not silently ignored (which would under-count load).
    assert _compute_charge([_session("not-a-real-duration")], []) == "med"


# ── app/routers/wellness.py::_charge_for_day / _charge_for_athlete_day ──

def test_charge_for_day_rest_when_nobody_trains():
    assert _charge_for_day({"B": [], "H": []}) == "rest"


def test_charge_for_day_driven_by_busiest_athlete():
    sessions_by_athlete = {"B": [_session("30min")], "H": [_session("2h30")]}
    assert _charge_for_day(sessions_by_athlete) == "high"


def test_charge_for_athlete_day_matches_compute_charge_thresholds():
    # Sanity check the two independent implementations (meals.py vs
    # wellness.py) agree at the boundaries, since they're meant to represent
    # the same concept and are easy to let drift during separate edits.
    assert _charge_for_athlete_day([]) == "rest"
    assert _charge_for_athlete_day([_session("45min")]) == "low"
    assert _charge_for_athlete_day([_session("1h")]) == "med"
    assert _charge_for_athlete_day([_session("2h")]) == "high"


def test_charge_for_day_and_compute_charge_agree_on_same_input():
    sessions_b = [_session("1h15")]
    sessions_h = [_session("45min")]

    from_meals = _compute_charge(sessions_b, sessions_h)
    from_wellness = _charge_for_day({"B": sessions_b, "H": sessions_h})

    assert from_meals == from_wellness == "med"