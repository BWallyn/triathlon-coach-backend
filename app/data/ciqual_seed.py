"""
Seed data for IngredientNutrition, valeurs approximatives issues de la table
Ciqual (ANSES), pour 100g de portion comestible. Couvre les ingrédients déjà
utilisés dans app/routers/meals.py.
"""
from __future__ import annotations

# name -> (kcal, protein_g, carbs_g, fat_g) pour 100g
CIQUAL_SEED: dict[str, tuple[float, float, float, float]] = {
    "Pâtes complètes": (348, 13.0, 66.0, 2.5),
    "Blanc de poulet": (110, 23.0, 0.0, 1.5),
    "Riz thaï": (356, 7.0, 79.0, 0.6),
    "Riz basmati": (349, 7.5, 78.0, 0.6),
    "Bœuf haché": (215, 20.0, 0.0, 15.0),
    "Quinoa": (368, 14.0, 64.0, 6.0),
    "Saumon": (208, 20.0, 0.0, 13.0),
    "Avocat": (160, 2.0, 8.5, 14.7),
    "Patate douce": (86, 1.6, 20.0, 0.1),
    "Thon en boîte": (116, 26.0, 0.0, 1.0),
    "Haricots verts": (31, 1.8, 7.0, 0.2),
    "Lentilles corail": (352, 24.0, 60.0, 1.0),
    "Poulet rôti": (190, 27.0, 0.0, 9.0),
    "Steak": (200, 26.0, 0.0, 10.0),
    "Œufs": (143, 12.5, 0.7, 9.5),
    "Champignons": (22, 3.1, 3.3, 0.3),
    "Cabillaud": (82, 18.0, 0.0, 0.7),
    "Riz arborio": (356, 6.7, 79.0, 0.6),
    "Tofu soyeux": (55, 5.0, 1.5, 3.0),
    "Fromage de chèvre": (364, 21.0, 4.0, 29.0),
    "Saumon fumé": (184, 21.0, 0.0, 11.0),
    "Lait de coco": (197, 2.0, 3.0, 20.0),
}


def seed_ingredient_nutrition(db) -> None:
    """Insert IngredientNutrition rows from CIQUAL_SEED if not already present.

    Args:
        db (Session): Active SQLAlchemy session.
    """
    from app.models.base import IngredientNutrition

    for name, (kcal, protein, carbs, fat) in CIQUAL_SEED.items():
        if not db.query(IngredientNutrition).filter(IngredientNutrition.name == name).first():
            db.add(IngredientNutrition(
                name=name, kcal_100g=kcal, protein_100g=protein, carbs_100g=carbs, fat_100g=fat,
            ))
    db.commit()
