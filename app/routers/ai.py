"""
AI-powered endpoints for TriCouple.

POST /ai/training-plan        → generate a weekly training plan via LLM
POST /ai/meals/smart-generate → context-aware meal suggestions via LLM
GET  /ai/weekly-analysis      → load + nutrition + recovery analysis via LLM
"""
# =================
# ==== IMPORTS ====
# =================

from __future__ import annotations

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel

from app.database import get_db
from app.llm import LLMClient, get_llm_client
from app.models.base import Session as TrainingSession, Meal, Ingredient
from app.prompts import (
    TRAINING_PLAN_SYSTEM, TRAINING_PLAN_USER,
    MEAL_SUGGESTION_SYSTEM, MEAL_SUGGESTION_USER,
    WEEKLY_ANALYSIS_SYSTEM, WEEKLY_ANALYSIS_USER,
)

router = APIRouter(prefix="/ai", tags=["ai"])

DUR_WEIGHT = {
    "30min": 0.5, "45min": 0.75, "1h": 1.0, "1h15": 1.25,
    "1h30": 1.5, "2h": 2.0, "2h30": 2.5, "3h+": 3.5,
}


# ===================
# ==== FUNCTIONS ====
# ===================

# Helpers

def _sessions_in_range(db: DBSession, week_start: str, week_end: str) -> list[TrainingSession]:
    return (
        db.query(TrainingSession)
        .filter(TrainingSession.date >= week_start, TrainingSession.date <= week_end)
        .order_by(TrainingSession.date)
        .all()
    )


def _meals_in_range(db: DBSession, week_start: str, week_end: str) -> list[Meal]:
    return (
        db.query(Meal)
        .filter(Meal.date >= week_start, Meal.date <= week_end)
        .order_by(Meal.date, Meal.slot)
        .all()
    )


def _training_summary(sessions: list[TrainingSession]) -> str:
    if not sessions:
        return "Aucune séance planifiée."
    lines = []
    disc_label = {"swim": "Natation", "bike": "Vélo", "run": "Run"}
    for s in sessions:
        lines.append(
            f"  - {s.date} | {s.athlete_id} | {disc_label.get(s.discipline, s.discipline)} "
            f"| {s.kind} | {s.duration}"
        )
    return "\n".join(lines)


def _meals_summary(meals: list[Meal]) -> str:
    if not meals:
        return "Aucun repas planifié."
    lines = []
    slot_label = {"lunch": "Déjeuner", "dinner": "Dîner"}
    for m in meals:
        lines.append(f"  - {m.date} {slot_label.get(m.slot, m.slot)}: {m.name}")
    return "\n".join(lines)


def _week_dates(week_start: str) -> list[str]:
    start = date.fromisoformat(week_start)
    return [(start + timedelta(days=i)).isoformat() for i in range(7)]


def _compute_charge_label(sessions: list[TrainingSession]) -> str:
    if not sessions:
        return "rest"
    max_h = max(
        sum(DUR_WEIGHT.get(s.duration, 1) for s in sessions if s.athlete_id == a)
        for a in ("B", "C")
    )
    if max_h >= 2:
        return "high"
    if max_h >= 1:
        return "med"
    return "low"


# Schemas

class TrainingPlanRequest(BaseModel):
    week_start: str                        # YYYY-MM-DD (Monday)
    week_end: str                          # YYYY-MM-DD (Sunday)
    goal: str = "Développement de l'endurance de base"
    load_level: str = "modérée"            # légère | modérée | chargée
    constraints: str = "Aucune"
    max_sessions: int = 10


class SmartMealRequest(BaseModel):
    week_start: str
    week_end: str
    persist: bool = True  # if True, saves generated meals to DB


# Endpoints

@router.post("/training-plan")
async def generate_training_plan(
    body: TrainingPlanRequest,
    llm: LLMClient = Depends(get_llm_client),
) -> dict:
    """Generate a full weekly training plan using the LLM.
    Returns structured JSON ready for the frontend to display or import.

    Args:
        body (TrainingPlanRequest): Request body containing week range, goal, load level, constraints
        llm (LLMClient, optional): LLM client dependency. Defaults to Depends(get_llm_client).
    
    Returns:
        (dict): Structured JSON representing the generated training plan.
    """
    user_prompt = TRAINING_PLAN_USER.format(
        week_start=body.week_start,
        week_end=body.week_end,
        goal=body.goal,
        load_level=body.load_level,
        constraints=body.constraints,
        max_sessions=body.max_sessions,
    )
    try:
        plan = await llm.complete_json(TRAINING_PLAN_SYSTEM, user_prompt)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    return plan


@router.post("/meals/smart-generate")
async def smart_generate_meals(
    body: SmartMealRequest,
    db: DBSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> dict:
    """Generate meal suggestions based on the actual training load using the LLM.
    Optionally persists the meals to the database.

    Args:
        body (SmartMealRequest): Request body containing week range and persist flag
        db (DBSession, optional): Database session dependency. Defaults to Depends(get_db).
        llm (LLMClient, optional): LLM client dependency. Defaults to Depends(get_llm_client).

    Returns:
        (dict): Structured JSON representing the generated meal suggestions.
    """
    sessions = _sessions_in_range(db, body.week_start, body.week_end)
    training_summary = _training_summary(sessions)

    user_prompt = MEAL_SUGGESTION_USER.format(
        week_start=body.week_start,
        week_end=body.week_end,
        training_summary=training_summary,
    )

    try:
        result = await llm.complete_json(MEAL_SUGGESTION_SYSTEM, user_prompt)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    if body.persist:
        for day in result.get("days", []):
            date_str = day["date"]
            for slot in ("lunch", "dinner"):
                meal_data = day.get(slot)
                if not meal_data:
                    continue
                # Delete existing meal for this date/slot
                existing = db.query(Meal).filter(Meal.date == date_str, Meal.slot == slot).first()
                if existing:
                    db.delete(existing)
                meal = Meal(date=date_str, slot=slot, name=meal_data["name"])
                meal.ingredients = [
                    Ingredient(name=i["name"], quantity=i["quantity"])
                    for i in meal_data.get("ingredients", [])
                ]
                db.add(meal)
        db.commit()

    return result


@router.get("/weekly-analysis")
async def weekly_analysis(
    week_start: str,
    week_end: str,
    db: DBSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> dict:
    """Analyse the week's training load and nutrition, return personalised advice.

    Args:
        week_start (str): Start date of the week.
        week_end (str): End date of the week.
        db (DBSession, optional): Database session dependency. Defaults to Depends(get_db).
        llm (LLMClient, optional): LLM client dependency. Defaults to Depends(get_llm_client).

    Returns:
        (dict): Structured JSON representing the weekly analysis.
    """
    sessions = _sessions_in_range(db, week_start, week_end)
    meals = _meals_in_range(db, week_start, week_end)

    user_prompt = WEEKLY_ANALYSIS_USER.format(
        week_start=week_start,
        week_end=week_end,
        sessions_summary=_training_summary(sessions),
        meals_summary=_meals_summary(meals),
    )

    try:
        analysis = await llm.complete_json(WEEKLY_ANALYSIS_SYSTEM, user_prompt)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    return analysis
