# =================
# ==== IMPORTS ====
# =================

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import ATHLETE_NAMES
from app.models.base import Athlete, Base

# Options

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./triathlon_coach.db")

# Render/Neon fournissent parfois des URLs qui commencent par "postgres://"
# alors que SQLAlchemy attend "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ===================
# ==== FUNCTIONS ====
# ===================

def get_db():
    """Provide a database session to the caller, and close it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sync_athlete_names(db) -> None:
    """Create or update athlete names in the database based on the configuration.

    Args:
        db (Session): Active SQLAlchemy session.
    """
    for athlete_id, name in ATHLETE_NAMES.items():
        athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
        if athlete:
            athlete.name = name
        else:
            db.add(Athlete(id=athlete_id, name=name))
    db.commit()


def init_db():
    """Initialize the database by creating tables and syncing athlete names."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _sync_athlete_names(db)

        from app.data.ciqual_seed import seed_ingredient_nutrition
        seed_ingredient_nutrition(db)
    finally:
        db.close()
