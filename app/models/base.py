from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Athlete(Base):
    __tablename__ = "athletes"

    id = Column(String, primary_key=True)  # "B" or "C"
    name = Column(String, nullable=False)

    sessions = relationship("Session", back_populates="athlete", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    date = Column(String, nullable=False)  # ISO date string YYYY-MM-DD
    discipline = Column(String, nullable=False)  # swim | bike | run
    kind = Column(String, nullable=False)  # Endurance | Fractionné | etc.
    duration = Column(String, nullable=False)  # 30min | 1h | etc.

    athlete = relationship("Athlete", back_populates="sessions")


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    slot = Column(String, nullable=False)  # lunch | dinner
    name = Column(String, nullable=False)

    ingredients = relationship("Ingredient", back_populates="meal", cascade="all, delete-orphan")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(String, nullable=False)

    meal = relationship("Meal", back_populates="ingredients")
