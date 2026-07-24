# =================
# ==== IMPORTS ====
# =================

from typing import Any

from pydantic import BaseModel

# =================
# ==== CLASSES ====
# =================

# ── Athletes ──────────────────────────────────────────────────

class AthleteOut(BaseModel):
    """Schema for returning athlete data."""
    id: str
    name: str

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


class AthleteUpdate(BaseModel):
    """Schema for updating athlete data."""
    name: str


# ── Sessions ──────────────────────────────────────────────────

class SessionCreate(BaseModel):
    """Schema for creating a new training session."""
    athlete_id: str
    date: str
    discipline: str
    kind: str
    duration: str


class SessionResultIn(BaseModel):
    """Schema for creating/updating the actual metrics of a session."""
    actual_duration_min: int | None = None
    actual_distance_km: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_power_w: float | None = None
    avg_speed_kmh: float | None = None
    avg_pace_sec: int | None = None  # sec/km (run) ou sec/100m (swim)
    elevation_gain_m: float | None = None
    calories: int | None = None
    rpe: int | None = None
    notes: str | None = None
    source: str = "manual"
    strava_activity_id: str | None = None


class SessionResultOut(SessionResultIn):
    """Schema for returning a session result."""
    id: int
    session_id: int

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


class SessionOut(BaseModel):
    """Schema for returning training session data, including its logged result if any."""
    id: int
    athlete_id: str
    date: str
    discipline: str
    kind: str
    duration: str
    result: SessionResultOut | None = None

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


class SessionResultWithSessionOut(SessionResultOut):
    """Schema for a session result enriched with its parent session's planning info."""
    date: str
    athlete_id: str
    discipline: str
    kind: str
    planned_duration: str


# ── Races ─────────────────────────────────────────────────────

class RaceIn(BaseModel):
    """Schema for creating/updating a race."""
    athlete_id: str | None = None   # None = shared between B and H
    name: str
    date: str                        # YYYY-MM-DD
    discipline: str = "triathlon"    # triathlon | running | cycling | swim
    format: str                      # depends on discipline, see DISCIPLINE_FORMATS in routers/races.py
    priority: str = "B"              # A | B | C
    target_time: str | None = None
    location: str | None = None
    goal_notes: str | None = None


class RaceOut(RaceIn):
    """Schema for returning a race."""
    id: int

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


# ── Meals ─────────────────────────────────────────────────────

class IngredientIn(BaseModel):
    """Schema for creating a new ingredient."""
    name: str
    quantity: str


class IngredientOut(IngredientIn):
    """Schema for returning ingredient data."""
    id: int

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


class MealCreate(BaseModel):
    """Schema for creating a new meal."""
    date: str   # YYYY-MM-DD
    slot: str   # lunch | dinner
    name: str
    ingredients: list[IngredientIn]


class MealPortionOut(BaseModel):
    """Schema for returning one portion's computed macros."""
    id: int
    preset: str
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


class MealOut(BaseModel):
    """Schema for returning meal data."""
    id: int
    date: str
    slot: str
    name: str
    ingredients: list[IngredientOut]
    batch_plan_id: int | None = None
    portions: list[MealPortionOut] = []

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


# ── Sleep ─────────────────────────────────────────────────────

class SleepLogIn(BaseModel):
    """Schema for creating/updating a sleep entry."""
    athlete_id: str
    date: str
    duration_min: int
    quality: int
    deep_min: int | None = None
    rem_min: int | None = None
    source: str | None = None


class SleepLogOut(SleepLogIn):
    """Schema for returning a sleep entry."""
    id: int

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


# ── Feeling ───────────────────────────────────────────────────

class FeelingLogIn(BaseModel):
    """Schema for creating/updating a feeling entry."""
    athlete_id: str
    date: str
    fatigue: int
    motivation: int
    soreness: int
    note: str | None = None


class FeelingLogOut(FeelingLogIn):
    """Schema for returning a feeling entry."""
    id: int

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


# ── Weight ────────────────────────────────────────────────────

class WeightLogIn(BaseModel):
    """Schema for creating/updating a weight entry."""
    athlete_id: str
    date: str
    weight_kg: float


class WeightLogOut(WeightLogIn):
    """Schema for returning a weight entry."""
    id: int

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


# ── Dashboard summary ─────────────────────────────────────────

class DashboardSummaryOut(BaseModel):
    """Schema for the combined weekly dashboard summary."""
    week_start: str
    week_end: str
    day_charges: dict[str, str]
    day_charges_by_athlete: dict[str, dict[str, str]]
    weekly_load: dict[str, dict[str, float]]
    sleep: dict[str, dict[str, Any]]
    feeling: dict[str, dict[str, Any]]


# ── Batch cooking ─────────────────────────────────────────────

class BatchRecipeIngredientIn(BaseModel):
    """Schema for one ingredient line in a batch recipe, quantity given per serving."""
    ingredient_name: str
    quantity_per_serving: float
    unit: str
    is_scalable: bool = True
    unit_weight_g: float | None = None


class BatchRecipeIngredientOut(BatchRecipeIngredientIn):
    """Schema for returning a batch recipe ingredient."""
    id: int

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


class BatchRecipeCreate(BaseModel):
    """Schema for creating a batch-cooking recipe."""
    name: str
    instructions: str | None = None
    base_portions: int
    season: str | None = None
    recipe_link: str | None = None
    ref_kcal: float | None = None
    ref_protein_g: float | None = None
    ref_carbs_g: float | None = None
    ref_fat_g: float | None = None
    ingredients: list[BatchRecipeIngredientIn]


class BatchRecipeOut(BaseModel):
    """Schema for returning a batch-cooking recipe."""
    id: int
    name: str
    instructions: str | None
    base_portions: int
    season: str | None
    recipe_link: str | None
    ref_kcal: float | None = None
    ref_protein_g: float | None = None
    ref_carbs_g: float | None = None
    ref_fat_g: float | None = None
    ingredients: list[BatchRecipeIngredientOut]

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


class PortionAssignment(BaseModel):
    """One portion to create at a given date/slot, with its own preset."""
    date: str
    slot: str
    preset: str


class BatchCookingPlanCreate(BaseModel):
    """Schema for creating a batch-cooking plan: pick a recipe, assign portions."""
    recipe_id: int
    created_date: str
    portions: list[PortionAssignment]


class BatchMealOut(BaseModel):
    """Schema for a Meal created from a batch plan, with its portions."""
    id: int
    date: str
    slot: str
    name: str
    portions: list[MealPortionOut]

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True


class BatchCookingPlanOut(BaseModel):
    """Schema for returning a batch-cooking plan with its meals/portions."""
    id: int
    recipe_id: int
    created_date: str
    meals: list[BatchMealOut]

    class Config:
        """Enable ORM mode to allow returning SQLAlchemy models directly."""
        from_attributes = True
