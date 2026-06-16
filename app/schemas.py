from pydantic import BaseModel
from typing import Optional


# ── Athletes ──────────────────────────────────────────────────

class AthleteOut(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class AthleteUpdate(BaseModel):
    name: str


# ── Sessions ──────────────────────────────────────────────────

class SessionCreate(BaseModel):
    athlete_id: str
    date: str        # YYYY-MM-DD
    discipline: str  # swim | bike | run
    kind: str
    duration: str    # 30min | 45min | 1h | …


class SessionOut(BaseModel):
    id: int
    athlete_id: str
    date: str
    discipline: str
    kind: str
    duration: str

    class Config:
        from_attributes = True


# ── Meals ─────────────────────────────────────────────────────

class IngredientIn(BaseModel):
    name: str
    quantity: str


class IngredientOut(IngredientIn):
    id: int

    class Config:
        from_attributes = True


class MealCreate(BaseModel):
    date: str   # YYYY-MM-DD
    slot: str   # lunch | dinner
    name: str
    ingredients: list[IngredientIn]


class MealOut(BaseModel):
    id: int
    date: str
    slot: str
    name: str
    ingredients: list[IngredientOut]

    class Config:
        from_attributes = True
