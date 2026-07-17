# =================
# ==== IMPORTS ====
# =================

from sqlalchemy import (
    Boolean,
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
    batch_plan_id = Column(Integer, ForeignKey("batch_cooking_plans.id"), nullable=True)
    batch_plan = relationship("BatchCookingPlan", back_populates="meals")
    portions = relationship("MealPortion", back_populates="meal", cascade="all, delete-orphan")


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


class IngredientNutrition(Base):
    """SQLAlchemy model for per-100g nutrition data (source: Ciqual/ANSES)."""
    __tablename__ = "ingredient_nutrition"

    name = Column(String, primary_key=True)
    kcal_100g = Column(Float, nullable=False)
    protein_100g = Column(Float, nullable=False)
    carbs_100g = Column(Float, nullable=False)
    fat_100g = Column(Float, nullable=False)


class BatchRecipe(Base):
    """SQLAlchemy model for a batch-cooking recipe (cook once, portion across days)."""
    __tablename__ = "batch_recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    instructions = Column(String, nullable=True)
    base_portions = Column(Integer, nullable=False, default=4)
    season = Column(String, nullable=True)       # "spring"|"summer"|"autumn"|"winter"|None (toutes saisons)
    recipe_link = Column(String, nullable=True)

    ingredients = relationship("BatchRecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")


class BatchRecipeIngredient(Base):
    """SQLAlchemy model for one ingredient line in a batch recipe, quantity given per serving."""
    __tablename__ = "batch_recipe_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("batch_recipes.id"), nullable=False)
    ingredient_name = Column(String, ForeignKey("ingredient_nutrition.name"), nullable=False)
    quantity_per_serving = Column(Float, nullable=False)
    unit = Column(String, nullable=False)  # "g" | "ml" | "unité" | "gousse" | "c.à.s" ...
    is_scalable = Column(Boolean, nullable=False, default=True)  # False = épices/aromates fixes
    unit_weight_g = Column(Float, nullable=True)  # grammes/unité, requis pour macros si unit != g/ml

    recipe = relationship("BatchRecipe", back_populates="ingredients")


class BatchCookingPlan(Base):
    """SQLAlchemy model for one batch-cooking session (a recipe cooked once, portioned across meals)."""
    __tablename__ = "batch_cooking_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("batch_recipes.id"), nullable=False)
    created_date = Column(String, nullable=False)

    recipe = relationship("BatchRecipe")
    meals = relationship("Meal", back_populates="batch_plan")


class MealPortion(Base):
    """SQLAlchemy model for one portion of a batch meal, with its own preset and macros."""
    __tablename__ = "meal_portions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False)
    preset = Column(String, nullable=False)
    kcal = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)

    meal = relationship("Meal", back_populates="portions")
