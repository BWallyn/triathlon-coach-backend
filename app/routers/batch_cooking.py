"""
Batch cooking endpoints for TriCouple.

POST /batch-cooking/recipes            → créer une recette batch (ingrédients par portion)
GET  /batch-cooking/recipes            → lister les recettes batch
POST /batch-cooking/plans              → créer un plan : assigner des portions (presets) aux
                                          créneaux, calculer macros par portion
GET  /batch-cooking/plans/{id}         → récupérer un plan
GET  /batch-cooking/plans/{id}/shopping-list → quantités totales à cuisiner
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.batch_utils import PRESET_FACTORS, compute_portion_macros, scale_quantity
from app.database import get_db
from app.models.base import (
    BatchCookingPlan,
    BatchRecipe,
    BatchRecipeIngredient,
    IngredientNutrition,
    Meal,
    MealPortion,
)
from app.schemas import (
    BatchCookingPlanCreate,
    BatchCookingPlanOut,
    BatchRecipeCreate,
    BatchRecipeOut,
)

router = APIRouter(prefix="/batch-cooking", tags=["batch-cooking"])


# ── Recipes ───────────────────────────────────────────────────

@router.get("/recipes", response_model=list[BatchRecipeOut])
def list_batch_recipes(db: DBSession = Depends(get_db)):
    """List all available batch-cooking recipes."""
    return db.query(BatchRecipe).all()


@router.post("/recipes", response_model=BatchRecipeOut, status_code=201)
def create_batch_recipe(body: BatchRecipeCreate, db: DBSession = Depends(get_db)):
    """Create a new batch-cooking recipe, ingredient quantities given per serving."""
    recipe = BatchRecipe(name=body.name, instructions=body.instructions)
    recipe.ingredients = [
        BatchRecipeIngredient(**i.model_dump()) for i in body.ingredients
    ]
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


# ── Plans ─────────────────────────────────────────────────────

@router.post("/plans", response_model=BatchCookingPlanOut, status_code=201)
def create_batch_plan(body: BatchCookingPlanCreate, db: DBSession = Depends(get_db)):
    """Create a batch-cooking plan: assign portions (each with its own preset) to
    meal slots, compute macros per portion. Quantities are scaled per-portion,
    so the preset changes how much of each ingredient is actually cooked.
    """
    recipe = db.query(BatchRecipe).filter(BatchRecipe.id == body.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    for portion in body.portions:
        if portion.preset not in PRESET_FACTORS:
            raise HTTPException(status_code=422, detail=f"Unknown preset '{portion.preset}'")

    nutrition_by_name = {
        n.name: n
        for n in db.query(IngredientNutrition)
        .filter(IngredientNutrition.name.in_([i.ingredient_name for i in recipe.ingredients]))
        .all()
    }

    plan = BatchCookingPlan(recipe_id=recipe.id, created_date=body.created_date)
    db.add(plan)
    db.flush()  # récupérer plan.id avant de créer les Meal

    grouped: dict[tuple[str, str], list] = {}
    for portion in body.portions:
        grouped.setdefault((portion.date, portion.slot), []).append(portion)

    for (date_str, slot), portions in grouped.items():
        existing = db.query(Meal).filter(Meal.date == date_str, Meal.slot == slot).first()
        if existing:
            db.delete(existing)
            db.flush()

        meal = Meal(date=date_str, slot=slot, name=recipe.name, batch_plan_id=plan.id)
        meal.portions = [
            MealPortion(preset=p.preset, **compute_portion_macros(recipe.ingredients, nutrition_by_name, p.preset))
            for p in portions
        ]
        db.add(meal)

    db.commit()
    db.refresh(plan)
    return plan


@router.get("/plans/{plan_id}", response_model=BatchCookingPlanOut)
def get_batch_plan(plan_id: int, db: DBSession = Depends(get_db)):
    """Retrieve a batch-cooking plan with its meals and portions."""
    plan = db.query(BatchCookingPlan).filter(BatchCookingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.get("/plans/{plan_id}/shopping-list")
def get_shopping_list(plan_id: int, db: DBSession = Depends(get_db)):
    """Compute total ingredient quantities to cook for a plan.

    Each portion's preset scales macro-relevant ingredients independently, so
    the total is the sum across all portions of their individually-scaled
    quantities.
    """
    plan = db.query(BatchCookingPlan).filter(BatchCookingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    presets_used = [portion.preset for meal in plan.meals for portion in meal.portions]

    result = []
    for ingr in plan.recipe.ingredients:
        total_qty = sum(scale_quantity(ingr.quantity_per_serving, preset, ingr.is_scalable) for preset in presets_used)
        result.append({"name": ingr.ingredient_name, "quantity": round(total_qty, 1), "unit": ingr.unit})

    return {"ingredients": result}
