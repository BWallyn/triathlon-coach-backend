from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.base import Athlete
from app.schemas import AthleteOut, AthleteUpdate

router = APIRouter(prefix="/athletes", tags=["athletes"])


@router.get("/", response_model=list[AthleteOut])
def list_athletes(db: Session = Depends(get_db)):
    return db.query(Athlete).all()


@router.patch("/{athlete_id}", response_model=AthleteOut)
def update_athlete(athlete_id: str, body: AthleteUpdate, db: Session = Depends(get_db)):
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete.name = body.name
    db.commit()
    db.refresh(athlete)
    return athlete
