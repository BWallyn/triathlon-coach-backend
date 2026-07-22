from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.base import Race
from app.schemas import RaceIn, RaceOut

router = APIRouter(prefix="/races", tags=["races"])

VALID_FORMATS = ("sprint", "olympic", "half_ironman", "ironman", "other")
VALID_PRIORITIES = ("A", "B", "C")


@router.get("/", response_model=list[RaceOut])
def list_races(
    athlete_id: str | None = None,
    upcoming_only: bool = False,
    db: DBSession = Depends(get_db),
):
    from datetime import date as date_cls

    q = db.query(Race)
    if athlete_id:
        # matches races assigned to this athlete OR shared races (athlete_id is None)
        q = q.filter((Race.athlete_id == athlete_id) | (Race.athlete_id.is_(None)))
    if upcoming_only:
        q = q.filter(Race.date >= date_cls.today().isoformat())
    return q.order_by(Race.date).all()


@router.post("/", response_model=RaceOut, status_code=201)
def create_race(body: RaceIn, db: DBSession = Depends(get_db)):
    if body.format not in VALID_FORMATS:
        raise HTTPException(status_code=422, detail=f"Invalid format '{body.format}'")
    if body.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"Invalid priority '{body.priority}'")
    race = Race(**body.model_dump())
    db.add(race)
    db.commit()
    db.refresh(race)
    return race


@router.put("/{race_id}", response_model=RaceOut)
def update_race(race_id: int, body: RaceIn, db: DBSession = Depends(get_db)):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    if body.format not in VALID_FORMATS:
        raise HTTPException(status_code=422, detail=f"Invalid format '{body.format}'")
    if body.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"Invalid priority '{body.priority}'")
    for field, value in body.model_dump().items():
        setattr(race, field, value)
    db.commit()
    db.refresh(race)
    return race


@router.delete("/{race_id}", status_code=204)
def delete_race(race_id: int, db: DBSession = Depends(get_db)):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    db.delete(race)
    db.commit()