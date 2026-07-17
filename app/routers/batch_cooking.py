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

from app.batch_utils import (
    PRESET_FACTORS,
    SEASONS,
    compute_portion_macros,
    scale_quantity,
)
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
def list_batch_recipes(season: str | None = None, db: DBSession = Depends(get_db)):
    """List batch-cooking recipes, optionally filtered by season.

    Recipes with season=None (year-round) are always included when a
    season filter is applied.
    """
    if season and season not in SEASONS:
        raise HTTPException(status_code=422, detail=f"Invalid season '{season}'")
    q = db.query(BatchRecipe)
    if season:
        q = q.filter((BatchRecipe.season == season) | (BatchRecipe.season.is_(None)))
    return q.all()


@router.post("/recipes", response_model=BatchRecipeOut, status_code=201)
def create_batch_recipe(body: BatchRecipeCreate, db: DBSession = Depends(get_db)):
    """Create a new batch-cooking recipe, ingredient quantities given per serving."""
    if body.season and body.season not in SEASONS:
        raise HTTPException(status_code=422, detail=f"Invalid season '{body.season}'")
    if body.base_portions < 1:
        raise HTTPException(status_code=422, detail="base_portions must be at least 1")

    recipe = BatchRecipe(
        name=body.name,
        instructions=body.instructions,
        base_portions=body.base_portions,
        season=body.season,
        recipe_link=body.recipe_link,
    )
    recipe.ingredients = [BatchRecipeIngredient(**i.model_dump()) for i in body.ingredients]
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


# ── Plans ─────────────────────────────────────────────────────

@router.post("/plans", response_model=BatchCookingPlanOut, status_code=201)
def create_batch_plan(body: BatchCookingPlanCreate, db: DBSession = Depends(get_db)):
    """Create a batch-cooking plan. The number of portions assigned must
    exactly match the recipe's base_portions, since that's how many
    portions cooking it once actually yields.
    """
    recipe = db.query(BatchRecipe).filter(BatchRecipe.id == body.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if len(body.portions) != recipe.base_portions:
        raise HTTPException(
            status_code=422,
            detail=f"This recipe yields {recipe.base_portions} portions; "
                   f"{len(body.portions)} were assigned.",
        )

    for portion in body.portions:
        if portion.preset not in PRESET_FACTORS:
            raise HTTPException(status_code=422, detail=f"Unknown preset '{portion.preset}'")


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
