from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.base import Session as TrainingSession
from app.models.base import SessionResult
from app.schemas import (
    SessionCreate,
    SessionOut,
    SessionResultIn,
    SessionResultOut,
    SessionResultWithSessionOut,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

VALID_DISCIPLINES = ("swim", "bike", "run", "strength")


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    week_start: str | None = None,
    week_end: str | None = None,
    athlete_id: str | None = None,
    db: DBSession = Depends(get_db),
):
    q = db.query(TrainingSession)
    if athlete_id:
        q = q.filter(TrainingSession.athlete_id == athlete_id)
    if week_start:
        q = q.filter(TrainingSession.date >= week_start)
    if week_end:
        q = q.filter(TrainingSession.date <= week_end)
    return q.order_by(TrainingSession.date).all()


@router.post("/", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate, db: DBSession = Depends(get_db)):
    if body.discipline not in VALID_DISCIPLINES:
        raise HTTPException(status_code=422, detail="Invalid discipline")
    session = TrainingSession(**body.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()


# ── Résultats réels (post-séance / futur Strava) ────────────────

@router.get("/results", response_model=list[SessionResultWithSessionOut])
def list_session_results(
    athlete_id: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    discipline: str | None = None,
    db: DBSession = Depends(get_db),
):
    """List logged session results, joined with their planned session, for the Performance page."""
    q = db.query(SessionResult).join(TrainingSession, SessionResult.session_id == TrainingSession.id)
    if athlete_id:
        q = q.filter(TrainingSession.athlete_id == athlete_id)
    if date_start:
        q = q.filter(TrainingSession.date >= date_start)
    if date_end:
        q = q.filter(TrainingSession.date <= date_end)
    if discipline:
        q = q.filter(TrainingSession.discipline == discipline)
    rows = q.order_by(TrainingSession.date).all()

    return [
        SessionResultWithSessionOut(
            id=r.id,
            session_id=r.session_id,
            actual_duration_min=r.actual_duration_min,
            actual_distance_km=r.actual_distance_km,
            avg_hr=r.avg_hr,
            max_hr=r.max_hr,
            avg_power_w=r.avg_power_w,
            avg_speed_kmh=r.avg_speed_kmh,
            elevation_gain_m=r.elevation_gain_m,
            calories=r.calories,
            rpe=r.rpe,
            notes=r.notes,
            source=r.source,
            strava_activity_id=r.strava_activity_id,
            date=r.session.date,
            athlete_id=r.session.athlete_id,
            discipline=r.session.discipline,
            kind=r.session.kind,
            planned_duration=r.session.duration,
        )
        for r in rows
    ]


@router.post("/{session_id}/result", response_model=SessionResultOut, status_code=201)
def upsert_session_result(session_id: int, body: SessionResultIn, db: DBSession = Depends(get_db)):
    """Create or update (upsert) the logged result for a session."""
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    existing = db.query(SessionResult).filter(SessionResult.session_id == session_id).first()
    if existing:
        for field, value in body.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    result = SessionResult(session_id=session_id, **body.model_dump())
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.get("/{session_id}/result", response_model=SessionResultOut)
def get_session_result(session_id: int, db: DBSession = Depends(get_db)):
    result = db.query(SessionResult).filter(SessionResult.session_id == session_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="No result logged for this session")
    return result


@router.delete("/{session_id}/result", status_code=204)
def delete_session_result(session_id: int, db: DBSession = Depends(get_db)):
    result = db.query(SessionResult).filter(SessionResult.session_id == session_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="No result logged for this session")
    db.delete(result)
    db.commit()
