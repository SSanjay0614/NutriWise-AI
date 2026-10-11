"""
Seed a ready-to-use demo account in Supabase (and populate it a little).

Run once after configuring .env and running supabase_schema.sql:
    conda activate conda_env
    python -m backend.seed_demo

Login on the site with DEMO_EMAIL / DEMO_PASSWORD (see .env).
"""
import sys
from datetime import date

from backend import config, db
from backend.supabase_client import service_client
from nutrition.food_lookup import FoodDatabase
from nutrition.calculator import NutritionCalculator
from nutrition.glucose import GlucoseMonitor
from models.schemas import GlucoseReading


def _find_user_by_email(email: str):
    """Return the auth user with this email, or None."""
    try:
        page = service_client().auth.admin.list_users()
        users = page if isinstance(page, list) else getattr(page, "users", page)
        for u in users:
            if (getattr(u, "email", "") or "").lower() == email.lower():
                return u
    except Exception as exc:
        print(f"[!] Could not list users: {exc}")
    return None


def main() -> None:
    if not config.is_configured():
        print(f"[x] Missing Supabase settings: {', '.join(config.missing_keys())}")
        print("    Fill .env (see .env.example) first.")
        sys.exit(1)

    email, password = config.DEMO_EMAIL, config.DEMO_PASSWORD
    svc = service_client()

    user = _find_user_by_email(email)
    if user is None:
        print(f"Creating demo user {email} ...")
        created = svc.auth.admin.create_user({
            "email": email, "password": password, "email_confirm": True,
        })
        user = getattr(created, "user", created)
    else:
        print(f"Demo user {email} already exists — reusing.")

    user_id = getattr(user, "id", None)
    if not user_id:
        print("[x] Could not resolve demo user id.")
        sys.exit(1)

    # Profile
    db.upsert_profile(user_id, {
        "name": "Demo", "age": 52, "gender": "male", "weight_kg": 82,
        "height_cm": 171, "activity_level": "light", "diabetes_type": "type2",
        "on_insulin": False, "hba1c": 7.5, "conditions": ["hypertension"],
    })

    # Today's glucose
    today = date.today().isoformat()
    reading = GlucoseMonitor.annotate(GlucoseReading(
        value_mg_dl=132, reading_type="fasting", date=today))
    db.upsert_glucose(user_id, {
        "value_mg_dl": reading.value_mg_dl, "reading_type": reading.reading_type,
        "reading_date": reading.date, "category": reading.category,
    })

    # One sample breakfast
    food_db = FoodDatabase(csv_path=config.FOODS_CSV)
    calc = NutritionCalculator()
    db.delete_meals_for_day(user_id, today)
    from models.schemas import Nutrition
    total = Nutrition()
    foods = []
    for name, qty, unit in [("Masala Dosa", 1, "piece"), ("Sambar", 1, "bowl")]:
        rec = food_db.lookup_food(name)
        if rec:
            foods.append(food_db.food_to_item(rec, qty, unit, "dataset").model_dump())
            total = total + calc.calculate_nutrition(
                rec, food_db.resolve_weight(rec, qty, unit))
    db.add_meal(user_id, {
        "meal_date": today, "meal_type": "breakfast",
        "nutrition": total.model_dump(), "foods": foods,
    })

    print(f"[OK] Demo account ready. Log in with {email} / {password}")


if __name__ == "__main__":
    main()
