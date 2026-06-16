import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.base import Meal, Ingredient
from app.schemas import MealCreate, MealOut, IngredientIn

router = APIRouter(prefix="/meals", tags=["meals"])

# ── Recipe bank ───────────────────────────────────────────────
RECIPES: dict[str, dict[str, list[dict]]] = {
    "high": {
        "lunch": [
            {"name": "Pâtes complètes poulet pesto", "ingredients": [{"name": "Pâtes complètes", "quantity": "150g"}, {"name": "Blanc de poulet", "quantity": "180g"}, {"name": "Pesto", "quantity": "2 c.à.s"}, {"name": "Parmesan", "quantity": "30g"}, {"name": "Épinards", "quantity": "50g"}]},
            {"name": "Riz thaï bœuf brocolis", "ingredients": [{"name": "Riz thaï", "quantity": "150g"}, {"name": "Bœuf haché", "quantity": "150g"}, {"name": "Brocolis", "quantity": "200g"}, {"name": "Sauce soja", "quantity": "2 c.à.s"}, {"name": "Gingembre", "quantity": "1 c.à.c"}]},
            {"name": "Quinoa saumon avocat", "ingredients": [{"name": "Quinoa", "quantity": "120g"}, {"name": "Saumon", "quantity": "180g"}, {"name": "Avocat", "quantity": "1"}, {"name": "Citron", "quantity": "1"}, {"name": "Graines de chia", "quantity": "1 c.à.s"}]},
            {"name": "Patate douce thon haricots", "ingredients": [{"name": "Patate douce", "quantity": "300g"}, {"name": "Thon en boîte", "quantity": "2 boîtes"}, {"name": "Haricots verts", "quantity": "150g"}, {"name": "Huile d'olive", "quantity": "1 c.à.s"}]},
        ],
        "dinner": [
            {"name": "Saumon lentilles corail curry", "ingredients": [{"name": "Saumon", "quantity": "200g"}, {"name": "Lentilles corail", "quantity": "100g"}, {"name": "Lait de coco", "quantity": "200ml"}, {"name": "Épices curry", "quantity": "1 c.à.c"}, {"name": "Citron vert", "quantity": "1"}]},
            {"name": "Poulet rôti patate douce épinards", "ingredients": [{"name": "Poulet rôti", "quantity": "200g"}, {"name": "Patate douce", "quantity": "250g"}, {"name": "Épinards", "quantity": "100g"}, {"name": "Ail", "quantity": "2 gousses"}]},
            {"name": "Steak riz basmati brocolis", "ingredients": [{"name": "Steak", "quantity": "180g"}, {"name": "Riz basmati", "quantity": "120g"}, {"name": "Brocolis", "quantity": "200g"}, {"name": "Beurre", "quantity": "10g"}]},
        ],
    },
    "med": {
        "lunch": [
            {"name": "Salade quinoa légumes grillés", "ingredients": [{"name": "Quinoa", "quantity": "100g"}, {"name": "Courgettes", "quantity": "1"}, {"name": "Poivrons", "quantity": "1"}, {"name": "Feta", "quantity": "60g"}, {"name": "Huile d'olive", "quantity": "1 c.à.s"}]},
            {"name": "Wrap poulet crudités", "ingredients": [{"name": "Tortillas", "quantity": "2"}, {"name": "Blanc de poulet", "quantity": "120g"}, {"name": "Salade", "quantity": "50g"}, {"name": "Tomates", "quantity": "2"}, {"name": "Yaourt nature", "quantity": "1"}]},
            {"name": "Soupe potiron lentilles", "ingredients": [{"name": "Potiron", "quantity": "400g"}, {"name": "Lentilles vertes", "quantity": "80g"}, {"name": "Oignon", "quantity": "1"}, {"name": "Crème légère", "quantity": "50ml"}]},
        ],
        "dinner": [
            {"name": "Omelette champignons épinards", "ingredients": [{"name": "Œufs", "quantity": "3"}, {"name": "Champignons", "quantity": "150g"}, {"name": "Épinards", "quantity": "80g"}, {"name": "Gruyère", "quantity": "30g"}]},
            {"name": "Cabillaud vapeur haricots verts", "ingredients": [{"name": "Cabillaud", "quantity": "180g"}, {"name": "Haricots verts", "quantity": "200g"}, {"name": "Citron", "quantity": "1"}, {"name": "Herbes fraîches", "quantity": "1 c.à.s"}]},
            {"name": "Risotto aux champignons", "ingredients": [{"name": "Riz arborio", "quantity": "100g"}, {"name": "Champignons", "quantity": "200g"}, {"name": "Bouillon légumes", "quantity": "500ml"}, {"name": "Parmesan", "quantity": "30g"}, {"name": "Échalote", "quantity": "1"}]},
        ],
    },
    "low": {
        "lunch": [
            {"name": "Salade niçoise légère", "ingredients": [{"name": "Thon en boîte", "quantity": "1 boîte"}, {"name": "Œufs", "quantity": "2"}, {"name": "Tomates cerises", "quantity": "100g"}, {"name": "Olives", "quantity": "20g"}, {"name": "Salade", "quantity": "80g"}]},
            {"name": "Velouté courgette menthe", "ingredients": [{"name": "Courgettes", "quantity": "3"}, {"name": "Menthe fraîche", "quantity": "5 feuilles"}, {"name": "Yaourt grec", "quantity": "1"}, {"name": "Oignon", "quantity": "1"}]},
        ],
        "dinner": [
            {"name": "Poulet citron herbes salade", "ingredients": [{"name": "Blanc de poulet", "quantity": "150g"}, {"name": "Salade verte", "quantity": "100g"}, {"name": "Citron", "quantity": "1"}, {"name": "Huile d'olive", "quantity": "1 c.à.s"}, {"name": "Moutarde", "quantity": "1 c.à.c"}]},
            {"name": "Soupe miso tofu", "ingredients": [{"name": "Bouillon dashi", "quantity": "500ml"}, {"name": "Tofu soyeux", "quantity": "100g"}, {"name": "Pâte miso", "quantity": "2 c.à.s"}, {"name": "Oignon vert", "quantity": "2"}]},
        ],
    },
    "rest": {
        "lunch": [
            {"name": "Salade lentilles chèvre noix", "ingredients": [{"name": "Lentilles", "quantity": "100g"}, {"name": "Fromage de chèvre", "quantity": "60g"}, {"name": "Noix", "quantity": "20g"}, {"name": "Salade", "quantity": "80g"}, {"name": "Vinaigre balsamique", "quantity": "1 c.à.s"}]},
            {"name": "Gaspacho tomates concombre", "ingredients": [{"name": "Tomates", "quantity": "4"}, {"name": "Concombre", "quantity": "1"}, {"name": "Poivron", "quantity": "1"}, {"name": "Pain complet", "quantity": "2 tranches"}, {"name": "Ail", "quantity": "1 gousse"}]},
        ],
        "dinner": [
            {"name": "Ratatouille riz complet", "ingredients": [{"name": "Aubergine", "quantity": "1"}, {"name": "Courgettes", "quantity": "2"}, {"name": "Tomates", "quantity": "3"}, {"name": "Riz complet", "quantity": "80g"}, {"name": "Herbes de Provence", "quantity": "1 c.à.c"}]},
            {"name": "Tartare avocat saumon fumé", "ingredients": [{"name": "Saumon fumé", "quantity": "100g"}, {"name": "Avocat", "quantity": "1"}, {"name": "Câpres", "quantity": "1 c.à.s"}, {"name": "Pain de seigle", "quantity": "2 tranches"}, {"name": "Citron", "quantity": "1"}]},
        ],
    },
}

DUR_WEIGHT = {"30min": 0.5, "45min": 0.75, "1h": 1.0, "1h15": 1.25, "1h30": 1.5, "2h": 2.0, "2h30": 2.5, "3h+": 3.5}


def _compute_charge(sessions_b: list, sessions_c: list) -> str:
    all_sessions = sessions_b + sessions_c
    if not all_sessions:
        return "rest"
    h_b = sum(DUR_WEIGHT.get(s.duration, 1.0) for s in sessions_b)
    h_c = sum(DUR_WEIGHT.get(s.duration, 1.0) for s in sessions_c)
    max_h = max(h_b, h_c)
    if max_h >= 2:
        return "high"
    if max_h >= 1:
        return "med"
    return "low"


# ── Routes ────────────────────────────────────────────────────

@router.get("/", response_model=list[MealOut])
def list_meals(
    week_start: str | None = None,
    week_end: str | None = None,
    db: DBSession = Depends(get_db),
):
    q = db.query(Meal)
    if week_start:
        q = q.filter(Meal.date >= week_start)
    if week_end:
        q = q.filter(Meal.date <= week_end)
    return q.order_by(Meal.date, Meal.slot).all()


@router.post("/generate", response_model=list[MealOut])
def generate_meals(
    week_start: str,
    week_end: str,
    db: DBSession = Depends(get_db),
):
    """Generate meals for the week based on actual training load."""
    from datetime import date, timedelta
    from app.models.base import Session as TrainingSession

    start = date.fromisoformat(week_start)
    end = date.fromisoformat(week_end)
    generated = []

    current = start
    while current <= end:
        date_str = current.isoformat()

        sessions_b = db.query(TrainingSession).filter(
            TrainingSession.athlete_id == "B",
            TrainingSession.date == date_str,
        ).all()
        sessions_c = db.query(TrainingSession).filter(
            TrainingSession.athlete_id == "C",
            TrainingSession.date == date_str,
        ).all()

        charge = _compute_charge(sessions_b, sessions_c)

        for slot in ("lunch", "dinner"):
            # Remove existing meal for this date+slot
            existing = db.query(Meal).filter(Meal.date == date_str, Meal.slot == slot).first()
            if existing:
                db.delete(existing)

            recipe = random.choice(RECIPES[charge][slot])
            meal = Meal(date=date_str, slot=slot, name=recipe["name"])
            meal.ingredients = [
                Ingredient(name=i["name"], quantity=i["quantity"])
                for i in recipe["ingredients"]
            ]
            db.add(meal)

        current += timedelta(days=1)

    db.commit()

    return db.query(Meal).filter(Meal.date >= week_start, Meal.date <= week_end).order_by(Meal.date, Meal.slot).all()


@router.put("/{meal_id}", response_model=MealOut)
def update_meal(meal_id: int, body: MealCreate, db: DBSession = Depends(get_db)):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    meal.name = body.name
    meal.date = body.date
    meal.slot = body.slot
    for ing in meal.ingredients:
        db.delete(ing)
    meal.ingredients = [Ingredient(name=i.name, quantity=i.quantity) for i in body.ingredients]
    db.commit()
    db.refresh(meal)
    return meal


@router.post("/", response_model=MealOut, status_code=201)
def create_meal(body: MealCreate, db: DBSession = Depends(get_db)):
    existing = db.query(Meal).filter(Meal.date == body.date, Meal.slot == body.slot).first()
    if existing:
        raise HTTPException(status_code=409, detail="Meal already exists for this date/slot. Use PUT to update.")
    meal = Meal(date=body.date, slot=body.slot, name=body.name)
    meal.ingredients = [Ingredient(name=i.name, quantity=i.quantity) for i in body.ingredients]
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/{meal_id}", status_code=204)
def delete_meal(meal_id: int, db: DBSession = Depends(get_db)):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    db.delete(meal)
    db.commit()
