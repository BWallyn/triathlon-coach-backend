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
    date: str        # YYYY-MM-DD
    discipline: str  # swim | bike | run
    kind: str
    duration: str    # 30min | 45min | 1h | …


class SessionOut(BaseModel):
    """Schema for returning training session data."""
    id: int
    athlete_id: str
    date: str
    discipline: str
    kind: str
    duration: str

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


class MealOut(BaseModel):
    """Schema for returning meal data."""
    id: int
    date: str
    slot: str
    name: str
    ingredients: list[IngredientOut]

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
