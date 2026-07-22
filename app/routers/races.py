from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.base import Race
from app.schemas import RaceIn, RaceOut

router = APIRouter(prefix="/races", tags=["races"])

DISCIPLINE_FORMATS: dict[str, tuple[str, ...]] = {
    "triathlon": ("sprint", "olympic", "half_ironman", "ironman", "other"),
    "running": ("5k", "10k", "half_marathon", "marathon", "trail", "other"),
    "cycling": ("criterium", "gran_fondo", "time_trial", "road_race", "other"),
    "swim": ("open_water", "pool", "other"),
}
VALID_PRIORITIES = ("A", "B", "C")


def _validate_race(body: RaceIn) -> None:
    """Validate discipline, format (per discipline), and priority."""
    if body.discipline not in DISCIPLINE_FORMATS:
        raise HTTPException(status_code=422, detail=f"Invalid discipline '{body.discipline}'")
    if body.format not in DISCIPLINE_FORMATS[body.discipline]:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid format '{body.format}' for discipline '{body.discipline}'",
        )
    if body.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"Invalid priority '{body.priority}'")


@router.get("/", response_model=list[RaceOut])
def list_races(
    athlete_id: str | None = None,
    upcoming_only: bool = False,
    db: DBSession = Depends(get_db),
):
    """List races, optionally filtered by athlete and/or upcoming only.

    Args:
        athlete_id (str | None): Filter by athlete ID ("B" or "H").
        upcoming_only (bool): If True, only return races with a date >= today.
        db (DBSession): Database session.

    Returns:
        list[RaceOut]: List of races matching the filters, ordered by date.
    """
    q = db.query(Race)
    if athlete_id:
        q = q.filter((Race.athlete_id == athlete_id) | (Race.athlete_id.is_(None)))
    if upcoming_only:
        q = q.filter(Race.date >= date_cls.today().isoformat())
    return q.order_by(Race.date).all()


@router.post("/", response_model=RaceOut, status_code=201)
def create_race(body: RaceIn, db: DBSession = Depends(get_db)):
    """Create a new race after validating the input data.

    Args:
        body (RaceIn): Race data to create.
        db (DBSession): Database session.

    Returns:
        RaceOut: The created race.
    """
    _validate_race(body)
    race = Race(**body.model_dump())
    db.add(race)
    db.commit()
    db.refresh(race)
    return race


@router.put("/{race_id}", response_model=RaceOut)
def update_race(race_id: int, body: RaceIn, db: DBSession = Depends(get_db)):
    """Update an existing race after validating the input data.

    Args:
        race_id (int): ID of the race to update.
        body (RaceIn): Updated race data.
        db (DBSession): Database session.

    Returns:
        RaceOut: The updated race.
    """
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    _validate_race(body)
    for field, value in body.model_dump().items():
        setattr(race, field, value)
    db.commit()
    db.refresh(race)
    return race


@router.delete("/{race_id}", status_code=204)
def delete_race(race_id: int, db: DBSession = Depends(get_db)):
    """Delete a race by its ID.

    Args:
        race_id (int): ID of the race to delete.
        db (DBSession): Database session.

    Returns:
        None
    """
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    db.delete(race)
    db.commit()
