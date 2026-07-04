from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.base import Session as TrainingSession
from app.schemas import SessionCreate, SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    week_start: str | None = None,  # YYYY-MM-DD of Monday
    week_end: str | None = None,    # YYYY-MM-DD of Sunday
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
    if body.discipline not in ("swim", "bike", "run"):
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
