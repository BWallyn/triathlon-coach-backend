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
    """Create a new batch-cooking recipe, ingredient quantities given per serving.
    ...
    """
    if body.season and body.season not in SEASONS:
        raise HTTPException(status_code=422, detail=f"Invalid season '{body.season}'")
    if body.base_portions < 1:
        raise HTTPException(status_code=422, detail="base_portions must be at least 1")

    ingredient_names = {i.ingredient_name for i in body.ingredients}
    existing_names = {
        name for (name,) in db.query(IngredientNutrition.name)
        .filter(IngredientNutrition.name.in_(ingredient_names))
        .all()
    }
    missing_names = ingredient_names - existing_names
    for name in missing_names:
        db.add(IngredientNutrition(
            name=name, kcal_100g=0, protein_100g=0, carbs_100g=0, fat_100g=0,
        ))
    if missing_names:
        db.flush()

    recipe = BatchRecipe(
        name=body.name,
        instructions=body.instructions,
        base_portions=body.base_portions,
        season=body.season,
        recipe_link=body.recipe_link,
        ref_kcal=body.ref_kcal,
        ref_protein_g=body.ref_protein_g,
        ref_carbs_g=body.ref_carbs_g,
        ref_fat_g=body.ref_fat_g,
    )
    recipe.ingredients = [BatchRecipeIngredient(**i.model_dump()) for i in body.ingredients]
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.put("/recipes/{recipe_id}", response_model=BatchRecipeOut)
def update_batch_recipe(recipe_id: int, body: BatchRecipeCreate, db: DBSession = Depends(get_db)):
    """Update an existing batch-cooking recipe, replacing its ingredients entirely."""
    recipe = db.query(BatchRecipe).filter(BatchRecipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if body.season and body.season not in SEASONS:
        raise HTTPException(status_code=422, detail=f"Invalid season '{body.season}'")
    if body.base_portions < 1:
        raise HTTPException(status_code=422, detail="base_portions must be at least 1")

    ingredient_names = {i.ingredient_name for i in body.ingredients}
    existing_names = {
        name for (name,) in db.query(IngredientNutrition.name)
        .filter(IngredientNutrition.name.in_(ingredient_names))
        .all()
    }
    missing_names = ingredient_names - existing_names
    for name in missing_names:
        db.add(IngredientNutrition(
            name=name, kcal_100g=0, protein_100g=0, carbs_100g=0, fat_100g=0,
        ))
    if missing_names:
        db.flush()

    recipe.name = body.name
    recipe.instructions = body.instructions
    recipe.base_portions = body.base_portions
    recipe.season = body.season
    recipe.recipe_link = body.recipe_link
    recipe.ref_kcal = body.ref_kcal
    recipe.ref_protein_g = body.ref_protein_g
    recipe.ref_carbs_g = body.ref_carbs_g
    recipe.ref_fat_g = body.ref_fat_g

    for ingr in list(recipe.ingredients):
        db.delete(ingr)
    recipe.ingredients = [BatchRecipeIngredient(**i.model_dump()) for i in body.ingredients]

    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/recipes/{recipe_id}", status_code=204)
def delete_batch_recipe(recipe_id: int, db: DBSession = Depends(get_db)):
    """Delete a batch-cooking recipe.

    Refuses if a batch-cooking plan already references it, to avoid orphaning
    meals/portions that were generated from it.
    """
    recipe = db.query(BatchRecipe).filter(BatchRecipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    in_use = db.query(BatchCookingPlan).filter(BatchCookingPlan.recipe_id == recipe_id).first()
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Cette recette est utilisée dans un plan de batch cooking existant et ne peut pas être supprimée.",
        )
    db.delete(recipe)
    db.commit()


# ── Plans ─────────────────────────────────────────────────────

@router.post("/plans", response_model=BatchCookingPlanOut, status_code=201)
def create_batch_plan(body: BatchCookingPlanCreate, db: DBSession = Depends(get_db)):
    """Create a batch-cooking plan.

    The number of portions is chosen freely by the user (independent of the
    recipe's base_portions) — each portion's ingredients/macros are computed
    individually from quantity_per_serving, so any count scales correctly.
    """
    recipe = db.query(BatchRecipe).filter(BatchRecipe.id == body.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if not body.portions:
        raise HTTPException(status_code=422, detail="At least one portion must be assigned")

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
    db.flush()  # need plan.id before creating meals

    # Group portions by (date, slot): each slot becomes one Meal, which can
    # hold several MealPortion rows if multiple portions land on the same meal.
    grouped: dict[tuple[str, str], list[PortionAssignment]] = {}
    for p in body.portions:
        grouped.setdefault((p.date, p.slot), []).append(p)

    for (date_str, slot), portions in grouped.items():
        existing = db.query(Meal).filter(Meal.date == date_str, Meal.slot == slot).first()
        if existing:
            db.delete(existing)
            db.flush()

        meal = Meal(date=date_str, slot=slot, name=recipe.name, batch_plan_id=plan.id)
        db.add(meal)
        db.flush()

        for p in portions:
            macros = compute_portion_macros(recipe.ingredients, nutrition_by_name, p.preset)
            db.add(MealPortion(meal_id=meal.id, preset=p.preset, **macros))

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
