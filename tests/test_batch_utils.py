"""
Unit tests for app/batch_utils.py -- pure functions, no DB involved.

These cover the batch-cooking scaling/macro math, which is exactly the kind
of code that's easy to subtly break during a "replace the whole file" edit
and hard to notice went wrong until a shopping list or macro count is off.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.batch_utils import (
    PRESET_FACTORS,
    SEASONS,
    compute_portion_macros,
    current_season,
    scale_quantity,
)

# ── current_season ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "month,expected",
    [
        (3, "spring"), (4, "spring"), (5, "spring"),
        (6, "summer"), (7, "summer"), (8, "summer"),
        (9, "autumn"), (10, "autumn"), (11, "autumn"),
        (12, "winter"), (1, "winter"), (2, "winter"),
    ],
)
def test_current_season_maps_month_to_season(month, expected):
    assert current_season(date(2026, month, 15)) == expected


def test_current_season_defaults_to_today():
    # Just verify it doesn't blow up and returns a valid season when no date given.
    assert current_season() in SEASONS


# ── scale_quantity ───────────────────────────────────────────────

def test_scale_quantity_unscalable_ignores_preset():
    # Spices/condiments (is_scalable=False) should never move, regardless of preset.
    assert scale_quantity(1.0, "masse_agressive", is_scalable=False) == 1.0
    assert scale_quantity(1.0, "reduction_agressive", is_scalable=False) == 1.0


def test_scale_quantity_maintien_is_a_no_op():
    assert scale_quantity(200.0, "maintien", is_scalable=True) == 200.0


@pytest.mark.parametrize("preset,expected_factor", PRESET_FACTORS.items())
def test_scale_quantity_applies_every_known_preset_factor(preset, expected_factor):
    base = 100.0
    assert scale_quantity(base, preset, is_scalable=True) == pytest.approx(base * (1 + expected_factor))


def test_scale_quantity_unknown_preset_defaults_to_zero_factor():
    # Falls back to 0.0 via PRESET_FACTORS.get(..., 0.0) rather than raising.
    assert scale_quantity(150.0, "not_a_real_preset", is_scalable=True) == 150.0


# ── compute_portion_macros ───────────────────────────────────────

def _ingr(name, qty, unit="g", is_scalable=True, unit_weight_g=None):
    return SimpleNamespace(
        ingredient_name=name,
        quantity_per_serving=qty,
        unit=unit,
        is_scalable=is_scalable,
        unit_weight_g=unit_weight_g,
    )


def _nutrition(kcal, protein, carbs, fat):
    return SimpleNamespace(kcal_100g=kcal, protein_100g=protein, carbs_100g=carbs, fat_100g=fat)


def test_compute_portion_macros_gram_based_ingredient_at_maintien():
    ingredients = [_ingr("Riz basmati", 100, unit="g")]
    nutrition_by_name = {"Riz basmati": _nutrition(349, 7.5, 78.0, 0.6)}

    macros = compute_portion_macros(ingredients, nutrition_by_name, "maintien")

    # 100g at maintien (0% factor) == the raw per-100g values.
    assert macros == {"kcal": 349.0, "protein_g": 7.5, "carbs_g": 78.0, "fat_g": 0.6}


def test_compute_portion_macros_scales_with_preset():
    ingredients = [_ingr("Riz basmati", 100, unit="g")]
    nutrition_by_name = {"Riz basmati": _nutrition(349, 7.5, 78.0, 0.6)}

    macros = compute_portion_macros(ingredients, nutrition_by_name, "masse_moderee")  # +20%

    assert macros["kcal"] == pytest.approx(349.0 * 1.2, abs=0.1)
    assert macros["protein_g"] == pytest.approx(7.5 * 1.2, abs=0.05)


def test_compute_portion_macros_unit_weight_g_conversion():
    # "3 eggs" at 60g/egg should behave like 180g for macro purposes.
    ingredients = [_ingr("Œufs", 3, unit="unité", unit_weight_g=60)]
    nutrition_by_name = {"Œufs": _nutrition(143, 12.5, 0.7, 9.5)}

    macros = compute_portion_macros(ingredients, nutrition_by_name, "maintien")

    ratio = 180 / 100
    assert macros["kcal"] == pytest.approx(round(143 * ratio, 1))
    assert macros["protein_g"] == pytest.approx(round(12.5 * ratio, 1))


def test_compute_portion_macros_skips_ingredient_with_no_known_weight():
    # "1 pincée" of salt with no unit_weight_g and unit not in (g, ml) -> contributes 0.
    ingredients = [
        _ingr("Sel", 1, unit="pincée", unit_weight_g=None),
        _ingr("Riz basmati", 100, unit="g"),
    ]
    nutrition_by_name = {
        "Sel": _nutrition(0, 0, 0, 0),
        "Riz basmati": _nutrition(349, 7.5, 78.0, 0.6),
    }

    macros = compute_portion_macros(ingredients, nutrition_by_name, "maintien")

    assert macros == {"kcal": 349.0, "protein_g": 7.5, "carbs_g": 78.0, "fat_g": 0.6}


def test_compute_portion_macros_skips_ingredient_missing_from_nutrition_table():
    # If an ingredient somehow isn't in nutrition_by_name, it must be silently
    # skipped rather than raising -- this is the behavior the endpoint relies on.
    ingredients = [_ingr("Ingrédient inconnu", 100, unit="g")]
    macros = compute_portion_macros(ingredients, nutrition_by_name={}, preset="maintien")

    assert macros == {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}


def test_compute_portion_macros_sums_across_multiple_ingredients():
    ingredients = [
        _ingr("Riz basmati", 100, unit="g"),
        _ingr("Blanc de poulet", 150, unit="g"),
    ]
    nutrition_by_name = {
        "Riz basmati": _nutrition(349, 7.5, 78.0, 0.6),
        "Blanc de poulet": _nutrition(110, 23.0, 0.0, 1.5),
    }

    macros = compute_portion_macros(ingredients, nutrition_by_name, "maintien")

    expected_kcal = 349.0 * 1.0 + 110.0 * 1.5
    expected_protein = 7.5 * 1.0 + 23.0 * 1.5
    assert macros["kcal"] == pytest.approx(expected_kcal, abs=0.1)
    assert macros["protein_g"] == pytest.approx(expected_protein, abs=0.1)
