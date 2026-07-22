"""
AI-powered endpoints for TriCouple.

POST /ai/training-plan        → generate a weekly training plan via LLM,
                                 informed by upcoming races and recent wellness data
POST /ai/meals/smart-generate → context-aware meal suggestions via LLM
GET  /ai/weekly-analysis      → load + nutrition + recovery analysis via LLM
"""
# =================
# ==== IMPORTS ====
# =================

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.llm import LLMClient, get_llm_client
from app.models.base import Athlete, FeelingLog, Ingredient, Meal, Race, SleepLog
from app.models.base import Session as TrainingSession
from app.prompts import (
    MEAL_SUGGESTION_SYSTEM,
    MEAL_SUGGESTION_USER,
    TRAINING_PLAN_SYSTEM,
    TRAINING_PLAN_USER,
    WEEKLY_ANALYSIS_SYSTEM,
    WEEKLY_ANALYSIS_USER,
)

router = APIRouter(prefix="/ai", tags=["ai"])

DUR_WEIGHT = {
    "30min": 0.5, "45min": 0.75, "1h": 1.0, "1h15": 1.25,
    "1h30": 1.5, "2h": 2.0, "2h30": 2.5, "3h+": 3.5,
}

FORMAT_LABEL = {
    "sprint": "Sprint", "olympic": "Olympique",
    "half_ironman": "Half-Ironman", "ironman": "Ironman", "other": "Autre",
}


# ===================
# ==== FUNCTIONS ====
# ===================

# Helpers — existing

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
    disc_label = {"swim": "Natation", "bike": "Vélo", "run": "Run", "strength": "Muscu"}
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


def _compute_charge_label(sessions: list[TrainingSession]) -> str:
    if not sessions:
        return "rest"
    max_h = max(
        sum(DUR_WEIGHT.get(s.duration, 1) for s in sessions if s.athlete_id == a)
        for a in ("B", "H")
    )
    if max_h >= 2:
        return "high"
    if max_h >= 1:
        return "med"
    return "low"


# Helpers — race-aware context (new)

def _training_phase(weeks_to_race: float) -> str:
    """Map a weeks-to-race distance to a coaching phase label."""
    if weeks_to_race < 0.5:
        return "semaine de course"
    if weeks_to_race < 2:
        return "affûtage (taper)"
    if weeks_to_race < 6:
        return "développement spécifique"
    if weeks_to_race < 12:
        return "développement"
    return "base"


def _race_context(db: DBSession, week_start: str) -> str:
    """Build a per-athlete summary of the next upcoming race and its phase."""
    week_start_date = date.fromisoformat(week_start)
    athletes = db.query(Athlete).all()
    lines = []

    for athlete in athletes:
        race = (
            db.query(Race)
            .filter(
                (Race.athlete_id == athlete.id) | (Race.athlete_id.is_(None)),
                Race.date >= week_start,
            )
            .order_by(Race.date)
            .first()
        )
        if not race:
            lines.append(f"  - {athlete.name} : aucune course cible enregistrée.")
            continue

        race_date = date.fromisoformat(race.date)
        weeks_to_race = (race_date - week_start_date).days / 7
        phase = _training_phase(weeks_to_race)
        target = f", objectif {race.target_time}" if race.target_time else ""
        lines.append(
            f"  - {athlete.name} : {race.name} ({FORMAT_LABEL.get(race.format, race.format)}, "
            f"priorité {race.priority}) le {race.date}, dans {weeks_to_race:.1f} semaines{target} "
            f"→ phase actuelle : {phase}."
        )

    return "\n".join(lines) if lines else "Aucune course enregistrée."


def _recent_feedback_summary(db: DBSession, week_start: str, lookback_days: int = 14) -> str:
    """Summarize each athlete's actual training load and wellness over the past N days."""
    end = date.fromisoformat(week_start) - timedelta(days=1)
    start = end - timedelta(days=lookback_days - 1)
    start_str, end_str = start.isoformat(), end.isoformat()

    athletes = db.query(Athlete).all()
    lines = []

    for athlete in athletes:
        sessions = (
            db.query(TrainingSession)
            .filter(
                TrainingSession.athlete_id == athlete.id,
                TrainingSession.date >= start_str,
                TrainingSession.date <= end_str,
            )
            .all()
        )
        total_hours = sum(DUR_WEIGHT.get(s.duration, 1.0) for s in sessions)

        feelings = (
            db.query(FeelingLog)
            .filter(
                FeelingLog.athlete_id == athlete.id,
                FeelingLog.date >= start_str,
                FeelingLog.date <= end_str,
            )
            .all()
        )
        sleeps = (
            db.query(SleepLog)
            .filter(
                SleepLog.athlete_id == athlete.id,
                SleepLog.date >= start_str,
                SleepLog.date <= end_str,
            )
            .all()
        )

        parts = [f"{total_hours:.1f}h sur {lookback_days}j"]
        if feelings:
            avg_fatigue = sum(f.fatigue for f in feelings) / len(feelings)
            avg_motivation = sum(f.motivation for f in feelings) / len(feelings)
            avg_soreness = sum(f.soreness for f in feelings) / len(feelings)
            parts.append(
                f"fraîcheur moy. {avg_fatigue:.1f}/5, motivation moy. {avg_motivation:.1f}/5, "
                f"courbatures moy. {avg_soreness:.1f}/5"
            )
        else:
            parts.append("pas de ressenti saisi récemment")
        if sleeps:
            avg_sleep_h = sum(s.duration_min for s in sleeps) / len(sleeps) / 60
            parts.append(f"sommeil moy. {avg_sleep_h:.1f}h")

        lines.append(f"  - {athlete.name} : {', '.join(parts)}.")

    return "\n".join(lines) if lines else "Aucune donnée récente."


# Schemas

class TrainingPlanRequest(BaseModel):
    week_start: str                        # YYYY-MM-DD (Monday)
    week_end: str                          # YYYY-MM-DD (Sunday)
    goal: str | None = None                # optional manual override; else inferred from races
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
    db: DBSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> dict:
    """Generate a full weekly training plan using the LLM, informed by each
    athlete's next race (phase-aware) and their recent actual training load
    and wellness data.
    """
    race_context = _race_context(db, body.week_start)
    recent_feedback = _recent_feedback_summary(db, body.week_start)

    user_prompt = TRAINING_PLAN_USER.format(
        week_start=body.week_start,
        week_end=body.week_end,
        goal=body.goal or "Non précisé — déduis-le des courses cibles et de la phase actuelle.",
        load_level=body.load_level,
        constraints=body.constraints,
        max_sessions=body.max_sessions,
        race_context=race_context,
        recent_feedback=recent_feedback,
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
    """Analyse the week's training load and nutrition, return personalised advice."""
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
