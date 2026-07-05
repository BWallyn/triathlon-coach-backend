"""
Wellness endpoints: sleep, feeling (fatigue/motivation/soreness), weight,
and a weekly summary combining training load with these metrics for the
dashboard.
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.base import Athlete, FeelingLog, SleepLog, WeightLog
from app.models.base import Session as TrainingSession
from app.schemas import (
    DashboardSummaryOut,
    FeelingLogIn,
    FeelingLogOut,
    SleepLogIn,
    SleepLogOut,
    WeightLogIn,
    WeightLogOut,
)

router = APIRouter(prefix="/wellness", tags=["wellness"])

DUR_WEIGHT = {
    "30min": 0.5, "45min": 0.75, "1h": 1.0, "1h15": 1.25,
    "1h30": 1.5, "2h": 2.0, "2h30": 2.5, "3h+": 3.5,
}


# ── Helpers ───────────────────────────────────────────────────

def _week_dates(week_start: str, week_end: str) -> list[str]:
    start = date.fromisoformat(week_start)
    end = date.fromisoformat(week_end)
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _charge_for_day(sessions_by_athlete: dict[str, list]) -> str:
    if not any(sessions_by_athlete.values()):
        return "rest"
    max_h = max(
        sum(DUR_WEIGHT.get(s.duration, 1.0) for s in sessions)
        for sessions in sessions_by_athlete.values()
    )
    if max_h >= 2:
        return "high"
    if max_h >= 1:
        return "med"
    return "low"


def _charge_for_athlete_day(sessions: list) -> str:
    """Charge label for a single athlete on a single day."""
    if not sessions:
        return "rest"
    total_h = sum(DUR_WEIGHT.get(s.duration, 1.0) for s in sessions)
    if total_h >= 2:
        return "high"
    if total_h >= 1:
        return "med"
    return "low"


# ── Sleep ─────────────────────────────────────────────────────

@router.post("/sleep", response_model=SleepLogOut, status_code=201)
def log_sleep(body: SleepLogIn, db: DBSession = Depends(get_db)):
    """Create or update (upsert) the sleep entry for an athlete on a given date."""
    existing = (
        db.query(SleepLog)
        .filter(SleepLog.athlete_id == body.athlete_id, SleepLog.date == body.date)
        .first()
    )
    if existing:
        for field, value in body.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    log = SleepLog(**body.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/sleep", response_model=list[SleepLogOut])
def list_sleep(
    athlete_id: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    db: DBSession = Depends(get_db),
):
    q = db.query(SleepLog)
    if athlete_id:
        q = q.filter(SleepLog.athlete_id == athlete_id)
    if date_start:
        q = q.filter(SleepLog.date >= date_start)
    if date_end:
        q = q.filter(SleepLog.date <= date_end)
    return q.order_by(SleepLog.date).all()


# ── Feeling ───────────────────────────────────────────────────

@router.post("/feeling", response_model=FeelingLogOut, status_code=201)
def log_feeling(body: FeelingLogIn, db: DBSession = Depends(get_db)):
    """Create or update (upsert) the feeling entry for an athlete on a given date."""
    existing = (
        db.query(FeelingLog)
        .filter(FeelingLog.athlete_id == body.athlete_id, FeelingLog.date == body.date)
        .first()
    )
    if existing:
        for field, value in body.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    log = FeelingLog(**body.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/feeling", response_model=list[FeelingLogOut])
def list_feeling(
    athlete_id: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    db: DBSession = Depends(get_db),
):
    q = db.query(FeelingLog)
    if athlete_id:
        q = q.filter(FeelingLog.athlete_id == athlete_id)
    if date_start:
        q = q.filter(FeelingLog.date >= date_start)
    if date_end:
        q = q.filter(FeelingLog.date <= date_end)
    return q.order_by(FeelingLog.date).all()


# ── Weight ────────────────────────────────────────────────────

@router.post("/weight", response_model=WeightLogOut, status_code=201)
def log_weight(body: WeightLogIn, db: DBSession = Depends(get_db)):
    """Create or update (upsert) the weight entry for an athlete on a given date."""
    existing = (
        db.query(WeightLog)
        .filter(WeightLog.athlete_id == body.athlete_id, WeightLog.date == body.date)
        .first()
    )
    if existing:
        existing.weight_kg = body.weight_kg
        db.commit()
        db.refresh(existing)
        return existing

    log = WeightLog(**body.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/weight", response_model=list[WeightLogOut])
def list_weight(
    athlete_id: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    db: DBSession = Depends(get_db),
):
    q = db.query(WeightLog)
    if athlete_id:
        q = q.filter(WeightLog.athlete_id == athlete_id)
    if date_start:
        q = q.filter(WeightLog.date >= date_start)
    if date_end:
        q = q.filter(WeightLog.date <= date_end)
    return q.order_by(WeightLog.date).all()


@router.delete("/weight/{entry_id}", status_code=204)
def delete_weight(entry_id: int, db: DBSession = Depends(get_db)):
    entry = db.query(WeightLog).filter(WeightLog.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Weight entry not found")
    db.delete(entry)
    db.commit()


# ── Weekly summary (training load + sleep + feeling) ──────────

@router.get("/summary", response_model=DashboardSummaryOut)
def dashboard_summary(week_start: str, week_end: str, db: DBSession = Depends(get_db)):
    """Combine training load, sleep, and feeling data for the dashboard."""
    athlete_ids = [a.id for a in db.query(Athlete).all()]
    days = _week_dates(week_start, week_end)

    sessions = (
        db.query(TrainingSession)
        .filter(TrainingSession.date >= week_start, TrainingSession.date <= week_end)
        .all()
    )
    sessions_by_day: dict[str, dict[str, list]] = {
        d: {a: [] for a in athlete_ids} for d in days
    }
    for s in sessions:
        if s.date in sessions_by_day and s.athlete_id in sessions_by_day[s.date]:
            sessions_by_day[s.date][s.athlete_id].append(s)

    day_charges = {d: _charge_for_day(sessions_by_day[d]) for d in days}
    day_charges_by_athlete: dict[str, dict[str, str]] = {
        a: {d: _charge_for_athlete_day(sessions_by_day[d][a]) for d in days}
        for a in athlete_ids
    }

    weekly_load: dict[str, dict[str, float]] = {}
    for a in athlete_ids:
        totals = {"swim": 0.0, "bike": 0.0, "run": 0.0, "strength": 0.0}
        for s in sessions:
            if s.athlete_id == a and s.discipline in totals:
                totals[s.discipline] += DUR_WEIGHT.get(s.duration, 1.0)
        weekly_load[a] = totals

    sleep_logs = (
        db.query(SleepLog)
        .filter(SleepLog.date >= week_start, SleepLog.date <= week_end)
        .all()
    )
    sleep: dict[str, dict[str, dict]] = {a: {} for a in athlete_ids}
    for log in sleep_logs:
        sleep.setdefault(log.athlete_id, {})[log.date] = {
            "duration_min": log.duration_min,
            "quality": log.quality,
            "deep_min": log.deep_min,
            "rem_min": log.rem_min,
        }

    feeling_logs = (
        db.query(FeelingLog)
        .filter(FeelingLog.date >= week_start, FeelingLog.date <= week_end)
        .all()
    )
    feeling: dict[str, dict[str, dict]] = {a: {} for a in athlete_ids}
    for log in feeling_logs:
        feeling.setdefault(log.athlete_id, {})[log.date] = {
            "fatigue": log.fatigue,
            "motivation": log.motivation,
            "soreness": log.soreness,
            "note": log.note,
        }

    return DashboardSummaryOut(
        week_start=week_start,
        week_end=week_end,
        day_charges=day_charges,
        day_charges_by_athlete=day_charges_by_athlete,
        weekly_load=weekly_load,
        sleep=sleep,
        feeling=feeling,
    )
