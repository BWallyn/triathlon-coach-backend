"""Utility helpers for batch cooking: preset factors and macro/quantity scaling."""
from __future__ import annotations

from datetime import date

PRESET_FACTORS: dict[str, float] = {
    "reduction_agressive": -0.30,
    "reduction_moderee": -0.20,
    "reduction_legere": -0.10,
    "maintien": 0.0,
    "masse_legere": 0.10,
    "masse_moderee": 0.20,
    "masse_agressive": 0.30,
}
SEASONS: tuple[str, ...] = ("spring", "summer", "autumn", "winter")


def current_season(d: date | None = None) -> str:
    """Meteorological season (Northern hemisphere) for a given date.

    Args:
        d (date | None): Date to evaluate; defaults to today.

    Returns:
        (str): One of SEASONS.
    """
    d = d or date.today()
    month = d.month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"


def scale_quantity(base_quantity: float, preset: str, is_scalable: bool) -> float:
    """Scale one ingredient's quantity for a single portion according to the preset.

    Args:
        base_quantity (float): Quantity per serving as defined in the recipe.
        preset (str): One of PRESET_FACTORS keys.
        is_scalable (bool): False for spices/aromates/condiments that stay fixed
            regardless of the preset.

    Returns:
        (float): Scaled quantity for this portion.
    """
    if not is_scalable:
        return base_quantity
    return base_quantity * (1 + PRESET_FACTORS.get(preset, 0.0))


def compute_portion_macros(recipe_ingredients: list, nutrition_by_name: dict, preset: str) -> dict[str, float]:
    """Compute total macros for a single portion of a recipe under a given preset.

    Non-metric ingredients (unité, gousse...) contribute to macros only if
    `unit_weight_g` is set on the ingredient line; otherwise they're skipped
    (e.g. spices with no meaningful macro contribution).

    Args:
        recipe_ingredients (list): BatchRecipeIngredient rows for the recipe.
        nutrition_by_name (dict): ingredient_name -> IngredientNutrition row.
        preset (str): One of PRESET_FACTORS keys.

    Returns:
        (dict): {"kcal": float, "protein_g": float, "carbs_g": float, "fat_g": float}
    """
    totals = {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for ingr in recipe_ingredients:
        nutrition = nutrition_by_name.get(ingr.ingredient_name)
        if not nutrition:
            continue

        scaled_qty = scale_quantity(ingr.quantity_per_serving, preset, ingr.is_scalable)
        if ingr.unit in ("g", "ml"):
            grams = scaled_qty
        elif ingr.unit_weight_g:
            grams = scaled_qty * ingr.unit_weight_g
        else:
            continue  # pas de poids connu, ex: "1 pincée" — ignoré pour les macros

        ratio = grams / 100.0
        totals["kcal"] += nutrition.kcal_100g * ratio
        totals["protein_g"] += nutrition.protein_100g * ratio
        totals["carbs_g"] += nutrition.carbs_100g * ratio
        totals["fat_g"] += nutrition.fat_100g * ratio

    return {k: round(v, 1) for k, v in totals.items()}
