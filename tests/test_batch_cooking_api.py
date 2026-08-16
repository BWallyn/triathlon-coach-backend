"""
Integration tests for POST /batch-cooking/plans and GET /batch-cooking/plans/{id}/shopping-list.

This is the most intricate piece of logic in the app: creating a plan groups
portions by (date, slot) into Meal rows, computes per-portion macros via
compute_portion_macros, and the shopping list re-derives total quantities
from the same recipe + presets. It's exactly the kind of multi-step,
easy-to-regress flow that's worth locking down with a real request through
the API and a real (in-memory) DB.
"""
from __future__ import annotations

import pytest


def _create_recipe(client):
    resp = client.post("/batch-cooking/recipes", json={
        "name": "Riz poulet basmati",
        "instructions": "Cuire tout ensemble.",
        "base_portions": 4,
        "season": None,
        "ingredients": [
            {
                "ingredient_name": "Riz basmati",
                "quantity_per_serving": 100,
                "unit": "g",
                "is_scalable": True,
            },
            {
                "ingredient_name": "Blanc de poulet",
                "quantity_per_serving": 150,
                "unit": "g",
                "is_scalable": True,
            },
            {
                "ingredient_name": "Sel",
                "quantity_per_serving": 1,
                "unit": "pincée",
                "is_scalable": False,
            },
        ],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_recipe_auto_creates_missing_ingredient_nutrition_rows(client):
    # "Riz basmati" and "Blanc de poulet" are seeded via Ciqual; "Sel" isn't --
    # the endpoint should backfill a zeroed nutrition row rather than fail.
    recipe = _create_recipe(client)
    assert len(recipe["ingredients"]) == 3
    names = {i["ingredient_name"] for i in recipe["ingredients"]}
    assert names == {"Riz basmati", "Blanc de poulet", "Sel"}


def test_create_batch_plan_groups_portions_by_date_and_slot(client):
    recipe = _create_recipe(client)

    resp = client.post("/batch-cooking/plans", json={
        "recipe_id": recipe["id"],
        "created_date": "2026-08-16",
        "portions": [
            {"date": "2026-08-17", "slot": "lunch", "preset": "maintien"},
            {"date": "2026-08-17", "slot": "lunch", "preset": "masse_moderee"},
            {"date": "2026-08-18", "slot": "dinner", "preset": "reduction_legere"},
        ],
    })
    assert resp.status_code == 201, resp.text
    plan = resp.json()

    # Three portions but only two (date, slot) pairs -> two Meal rows.
    assert len(plan["meals"]) == 2
    lunch_meal = next(m for m in plan["meals"] if m["slot"] == "lunch")
    dinner_meal = next(m for m in plan["meals"] if m["slot"] == "dinner")
    assert len(lunch_meal["portions"]) == 2
    assert len(dinner_meal["portions"]) == 1


def test_batch_plan_portion_macros_reflect_preset_scaling(client):
    recipe = _create_recipe(client)

    resp = client.post("/batch-cooking/plans", json={
        "recipe_id": recipe["id"],
        "created_date": "2026-08-16",
        "portions": [
            {"date": "2026-08-17", "slot": "lunch", "preset": "maintien"},
            {"date": "2026-08-17", "slot": "dinner", "preset": "masse_agressive"},  # +30%
        ],
    })
    plan = resp.json()
    lunch = next(m for m in plan["meals"] if m["slot"] == "lunch")["portions"][0]
    dinner = next(m for m in plan["meals"] if m["slot"] == "dinner")["portions"][0]

    # The +30% portion should have meaningfully more kcal/protein than maintien,
    # roughly proportional (salt doesn't scale, so it won't be exactly 1.30x).
    assert dinner["kcal"] > lunch["kcal"]
    assert dinner["kcal"] == pytest.approx(lunch["kcal"] * 1.30, rel=0.05)


def test_batch_plan_creation_overwrites_existing_meal_at_same_slot(client):
    recipe = _create_recipe(client)

    # Manually create a plain (non-batch) meal at that date/slot first.
    resp = client.post("/meals/", json={
        "date": "2026-08-17",
        "slot": "lunch",
        "name": "Repas manuel",
        "ingredients": [{"name": "Pain", "quantity": "1"}],
    })
    assert resp.status_code == 201

    # Creating a batch plan for the same date/slot should replace it.
    resp = client.post("/batch-cooking/plans", json={
        "recipe_id": recipe["id"],
        "created_date": "2026-08-16",
        "portions": [{"date": "2026-08-17", "slot": "lunch", "preset": "maintien"}],
    })
    assert resp.status_code == 201

    meals = client.get("/meals/", params={"week_start": "2026-08-17", "week_end": "2026-08-17"}).json()
    assert len(meals) == 1
    assert meals[0]["name"] == recipe["name"]
    assert meals[0]["batch_plan_id"] is not None


def test_create_batch_plan_requires_at_least_one_portion(client):
    recipe = _create_recipe(client)
    resp = client.post("/batch-cooking/plans", json={
        "recipe_id": recipe["id"],
        "created_date": "2026-08-16",
        "portions": [],
    })
    assert resp.status_code == 422


def test_create_batch_plan_rejects_unknown_preset(client):
    recipe = _create_recipe(client)
    resp = client.post("/batch-cooking/plans", json={
        "recipe_id": recipe["id"],
        "created_date": "2026-08-16",
        "portions": [{"date": "2026-08-17", "slot": "lunch", "preset": "not_a_real_preset"}],
    })
    assert resp.status_code == 422


def test_shopping_list_sums_scaled_quantities_across_portions(client):
    recipe = _create_recipe(client)

    resp = client.post("/batch-cooking/plans", json={
        "recipe_id": recipe["id"],
        "created_date": "2026-08-16",
        "portions": [
            {"date": "2026-08-17", "slot": "lunch", "preset": "maintien"},       # x1.0
            {"date": "2026-08-18", "slot": "lunch", "preset": "masse_moderee"},  # x1.2
        ],
    })
    plan_id = resp.json()["id"]

    shopping_list = client.get(f"/batch-cooking/plans/{plan_id}/shopping-list").json()
    ingredients = {i["name"]: i["quantity"] for i in shopping_list["ingredients"]}

    # Riz basmati: 100g * 1.0 + 100g * 1.2 = 220g
    assert ingredients["Riz basmati"] == pytest.approx(220.0)
    # Blanc de poulet: 150g * 1.0 + 150g * 1.2 = 330g
    assert ingredients["Blanc de poulet"] == pytest.approx(330.0)
    # Sel is not scalable: 1 + 1 = 2 (unchanged by presets)
    assert ingredients["Sel"] == pytest.approx(2.0)


def test_delete_recipe_in_use_by_a_plan_is_rejected(client):
    recipe = _create_recipe(client)
    client.post("/batch-cooking/plans", json={
        "recipe_id": recipe["id"],
        "created_date": "2026-08-16",
        "portions": [{"date": "2026-08-17", "slot": "lunch", "preset": "maintien"}],
    })

    resp = client.delete(f"/batch-cooking/recipes/{recipe['id']}")
    assert resp.status_code == 409
