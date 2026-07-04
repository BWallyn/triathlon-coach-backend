# =================
# ==== IMPORTS ====
# =================

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Options
Base = declarative_base()


# =================
# ==== CLASSES ====
# =================

class Athlete(Base):
    """SQLAlchemy model for an athlete."""
    __tablename__ = "athletes"

    id = Column(String, primary_key=True)  # "B" or "H"
    name = Column(String, nullable=False)

    sessions = relationship("Session", back_populates="athlete", cascade="all, delete-orphan")


class Session(Base):
    """SQLAlchemy model for a training session."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    date = Column(String, nullable=False)  # ISO date string YYYY-MM-DD
    discipline = Column(String, nullable=False)  # swim | bike | run
    kind = Column(String, nullable=False)  # Endurance | Fractionné | etc.
    duration = Column(String, nullable=False)  # 30min | 1h | etc.

    athlete = relationship("Athlete", back_populates="sessions")


class Meal(Base):
    """SQLAlchemy model for a meal."""
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    slot = Column(String, nullable=False)  # lunch | dinner
    name = Column(String, nullable=False)

    ingredients = relationship("Ingredient", back_populates="meal", cascade="all, delete-orphan")


class Ingredient(Base):
    """SQLAlchemy model for an ingredient."""
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(String, nullable=False)

    meal = relationship("Meal", back_populates="ingredients")


class SleepLog(Base):
    """SQLAlchemy model for a nightly sleep entry."""
    __tablename__ = "sleep_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    date = Column(String, nullable=False)          # YYYY-MM-DD
    duration_min = Column(Integer, nullable=False)
    quality = Column(Integer, nullable=False)       # 1-5
    deep_min = Column(Integer, nullable=True)
    rem_min = Column(Integer, nullable=True)
    source = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint("athlete_id", "date", name="uq_sleep_athlete_date"),)


class FeelingLog(Base):
    """SQLAlchemy model for a daily feeling entry (fatigue/motivation/soreness)."""
    __tablename__ = "feeling_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    date = Column(String, nullable=False)
    fatigue = Column(Integer, nullable=False)       # 1-5, "fraîcheur"
    motivation = Column(Integer, nullable=False)    # 1-5
    soreness = Column(Integer, nullable=False)      # 1-5, "courbatures"
    note = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint("athlete_id", "date", name="uq_feeling_athlete_date"),)


class WeightLog(Base):
    """SQLAlchemy model for a body weight entry."""
    __tablename__ = "weight_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    date = Column(String, nullable=False)
    weight_kg = Column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("athlete_id", "date", name="uq_weight_athlete_date"),)