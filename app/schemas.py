# =================
# ==== IMPORTS ====
# =================

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
