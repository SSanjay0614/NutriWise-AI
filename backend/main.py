"""
NutriWise AI — full-stack backend (FastAPI + Supabase).

Per-user auth (Supabase), cloud per-user data (profile, glucose, meals,
activities, audit trail), time-aware logging, activity-adjusted goals, history,
and weekly analysis. Reuses the Python nutrition engine. Serves the built React
frontend so the whole site runs from one command.

Run:
    conda activate conda_env
    uvicorn backend.main:app --port 8000      # http://localhost:8000
"""
import os
import sys
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import config, db
from backend.auth import AuthedUser, get_current_user

from nutrition.food_lookup import FoodDatabase
from nutrition.calculator import NutritionCalculator
from nutrition.goals import GoalCalculator
from nutrition.glucose import GlucoseMonitor
from nutrition.assessment import NutritionAssessment
from nutrition.recommender import MealRecommender
from nutrition.meal_planner import DiabetesMealPlanner
from nutrition.diabetes_score import DiabetesScorer
from nutrition.activity import ActivityEstimator
from nutrition import guidance
from nutrition.analysis import weekly_analysis
from models.schemas import (
    UserProfile, GlucoseReading, MealRecord, FoodItem, Nutrition, DailyIntake,
)
from llm.gemini_client import GeminiClient

app = FastAPI(title="NutriWise Diabetes Diet Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
)

_food_db = FoodDatabase(csv_path=config.FOODS_CSV)
_calc = NutritionCalculator()


def _make_llm():
    """Google Gemini client (graceful no-op when no API key is set)."""
    return GeminiClient(config.GEMINI_API_KEY, config.GEMINI_MODEL)


_parser = _make_llm()
_LLM_NAME = "gemini"

_PROFILE_FIELDS = {
    "name", "age", "gender", "weight_kg", "height_cm", "activity_level",
    "diabetes_type", "on_insulin", "hba1c", "conditions",
}

_SCHEMA_HINT = ("Database not up to date for this feature. Run the latest "
                "supabase_migration_*.sql files in your Supabase SQL editor, then retry. ({err})")


# ------------------------------ request models ------------------------------
class ProfileIn(BaseModel):
    name: str = "User"
    age: int
    gender: str = "male"
    weight_kg: float
    height_cm: float
    activity_level: str = "sedentary"
    diabetes_type: str = "type2"
    on_insulin: bool = False
    hba1c: Optional[float] = None
    conditions: List[str] = []


class GlucoseIn(BaseModel):
    value_mg_dl: float
    reading_type: str = "fasting"
    day: Optional[str] = None


class MealItemIn(BaseModel):
    food_name: str
    quantity: float = 1
    unit: str = "serving"


class MealIn(BaseModel):
    meal_type: str = "breakfast"
    items: List[MealItemIn]
    day: Optional[str] = None
    eaten_at: Optional[str] = None
    mode: Optional[str] = None  # None | "replace" | "merge" | "edit"


class ActivityIn(BaseModel):
    activity_type: str
    duration_min: float
    day: Optional[str] = None
    performed_at: Optional[str] = None
    note: str = ""


class MealCheckIn(BaseModel):
    items: List[MealItemIn] = []
    text: str = ""
    day: Optional[str] = None


class ParseIn(BaseModel):
    text: str


# PLACEHOLDER_HELPERS

# ------------------------------ helpers ------------------------------
def _resolve_day(day: Optional[str]) -> str:
    """Use the client-supplied local date when valid, else the server date."""
    if day:
        try:
            datetime.strptime(day, "%Y-%m-%d")
            return day
        except ValueError:
            pass
    return date.today().isoformat()


def _profile_from_row(row: Optional[dict]) -> Optional[UserProfile]:
    if not row:
        return None
    data = {k: row.get(k) for k in _PROFILE_FIELDS if row.get(k) is not None}
    data.setdefault("conditions", [])
    try:
        return UserProfile(**data)
    except Exception:
        return None


def _activity_bonus(user_id: str, day: str) -> (float, list):
    acts = db.list_activities(user_id, day)
    bonus = sum(float(a.get("calories_burned", 0) or 0) for a in acts)
    return bonus, acts


def _effective_goals(profile: UserProfile, user_id: str, day: str):
    bonus, acts = _activity_bonus(user_id, day)
    goals = GoalCalculator.calculate_goals(profile, activity_kcal=bonus)
    return goals, acts


def _food_summary(record: dict) -> dict:
    rating, _ = DiabetesScorer.score_record(record)
    return {
        "food_id": str(record.get("food_id", "")),
        "food_name": str(record.get("food_name", "")),
        "category": str(record.get("category", "")),
        "serving_size_g": float(record.get("serving_size_g", 100) or 100),
        "glycemic_index": (int(record["glycemic_index"]) if record.get("glycemic_index") is not None else None),
        "gi_category": record.get("gi_category"),
        "diabetes_rating": rating,
        "calories_kcal": float(record.get("calories_kcal", 0) or 0),
        "carbohydrate_g": float(record.get("carbohydrate_g", 0) or 0),
        "sugar_g": float(record.get("sugar_g", 0) or 0),
        "fiber_g": float(record.get("fiber_g", 0) or 0),
        "protein_g": float(record.get("protein_g", 0) or 0),
    }


def _glucose_model(row: Optional[dict], day: str) -> Optional[GlucoseReading]:
    if not row:
        return None
    try:
        return GlucoseReading(
            value_mg_dl=float(row["value_mg_dl"]),
            reading_type=row.get("reading_type", "fasting"),
            date=row.get("reading_date", day),
            category=row.get("category", "unknown"),
        )
    except Exception:
        return None


def _gi_cat(gi) -> Optional[str]:
    if gi is None:
        return None
    try:
        gi = float(gi)
    except (TypeError, ValueError):
        return None
    return "low" if gi <= 55 else "medium" if gi <= 69 else "high"


def _meal_nutrition(items: List[MealItemIn]):
    """
    Resolve items -> (foods[], total Nutrition, unresolved[]).
    Dataset first; anything missing is estimated via the LLM so off-dataset
    foods can still be logged. Only truly unresolvable items are returned.
    """
    foods, total, unresolved = [], Nutrition(), []
    llm_ok = _parser.check_connection()
    for item in items:
        record = _food_db.lookup_food(item.food_name)
        if record:
            weight_g = _food_db.resolve_weight(record, item.quantity, item.unit)
            foods.append(_food_db.food_to_item(record, item.quantity, item.unit, "dataset"))
            total = total + _calc.calculate_nutrition(record, weight_g)
            continue
        est = _parser.estimate_food_nutrition(item.food_name, item.quantity, item.unit) if llm_ok else None
        if est:
            rating, _ = DiabetesScorer.score(est.glycemic_index, None, est.sugar_g,
                                             est.fiber_g, est.carbohydrate_g)
            weight = (est.quantity if str(est.unit).lower() in {"g", "gram", "grams"}
                      else est.quantity * est.serving_size_g)
            foods.append(FoodItem(
                food_id=f"LLM_{abs(hash(item.food_name)) % 10000:04d}",
                food_name=est.food_name or item.food_name, scientific_name="",
                food_group="LLM Estimated", quantity=item.quantity, quantity_unit=item.unit,
                weight_g=weight, source="llm_fallback",
                glycemic_index=est.glycemic_index, gi_category=_gi_cat(est.glycemic_index),
                diabetes_rating=rating))
            total = total + Nutrition(
                calories_kcal=est.calories_kcal, protein_g=est.protein_g,
                carbohydrate_g=est.carbohydrate_g, fat_g=est.fat_g, fiber_g=est.fiber_g,
                sugar_g=est.sugar_g, sodium_mg=est.sodium_mg, calcium_mg=est.calcium_mg,
                iron_mg=est.iron_mg, potassium_mg=est.potassium_mg)
        else:
            unresolved.append(item.food_name)
    return foods, total, unresolved


def _snapshot(user: AuthedUser, day: Optional[str] = None) -> dict:
    day = _resolve_day(day)
    profile = _profile_from_row(db.get_profile(user.id))
    goals, acts = (None, [])
    if profile:
        goals, acts = _effective_goals(profile, user.id, day)
    glucose = _glucose_model(db.get_glucose(user.id, day), day)
    meal_rows = db.list_meals(user.id, day)

    meals_models, total = [], Nutrition()
    for m in meal_rows:
        try:
            nut = Nutrition(**(m.get("nutrition") or {}))
            total = total + nut
            meals_models.append(MealRecord(
                meal_type=m.get("meal_type", "meal"),
                foods=[FoodItem(**f) for f in (m.get("foods") or []) if isinstance(f, dict)],
                nutrition=nut, meal_date=day, eaten_at=m.get("eaten_at")))
        except Exception:
            continue
    intake = DailyIntake(date=day, meals=meals_models, total_nutrition=total)

    snap = {
        "user": {"id": user.id, "email": user.email},
        "day": day,
        "has_profile": profile is not None,
        "profile": ((profile.model_dump() | {"bmi": profile.bmi}) if profile else None),
        "goals": goals.model_dump() if goals else None,
        "glucose": (glucose.model_dump(mode="json") if glucose else None),
        "glucose_message": GlucoseMonitor.interpret(glucose),
        "totals": total.model_dump(),
        "meals": [
            {"meal_type": m.get("meal_type"), "nutrition": m.get("nutrition") or {},
             "foods": m.get("foods") or [], "eaten_at": m.get("eaten_at"),
             "updated_at": m.get("updated_at")}
            for m in meal_rows
        ],
        "activities": [
            {"id": a.get("id"), "activity_type": a.get("activity_type"),
             "duration_min": a.get("duration_min"), "calories_burned": a.get("calories_burned"),
             "performed_at": a.get("performed_at"), "note": a.get("note", "")}
            for a in acts
        ],
        "assessment": None,
        "recommendations": [],
        "carb_budget_today": None,
    }
    if goals:
        snap["carb_budget_today"] = round(goals.carbohydrate_g * GlucoseMonitor.carb_adjustment(glucose), 0)
        snap["assessment"] = NutritionAssessment.assess_daily_intake(intake, goals, glucose)
        snap["recommendations"] = [
            r.model_dump() for r in MealRecommender.get_next_meal_recommendation(
                intake, goals, glucose, food_db=_food_db)
        ]
    return snap


# PLACEHOLDER_ROUTES

# ------------------------------ public ------------------------------
@app.get("/api/health")
def health():
    return {"configured": config.is_configured(), "missing": config.missing_keys(),
            "demo_email": config.DEMO_EMAIL}


@app.get("/api/config")
def public_config():
    return {
        "configured": config.is_configured(), "missing": config.missing_keys(),
        "supabase_url": config.SUPABASE_URL, "supabase_anon_key": config.SUPABASE_ANON_KEY,
        "demo_email": config.DEMO_EMAIL, "demo_password": config.DEMO_PASSWORD,
        "llm": _LLM_NAME, "llm_ready": _parser.check_connection(),
    }


# ------------------------------ state / profile ------------------------------
@app.get("/api/state")
def get_state(day: Optional[str] = None, user: AuthedUser = Depends(get_current_user)):
    return _snapshot(user, day)


@app.post("/api/profile")
def save_profile(body: ProfileIn, user: AuthedUser = Depends(get_current_user)):
    try:
        UserProfile(**body.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid profile: {exc}")
    db.upsert_profile(user.id, body.model_dump())
    return _snapshot(user)


# ------------------------------ glucose ------------------------------
@app.post("/api/glucose")
def log_glucose(body: GlucoseIn, user: AuthedUser = Depends(get_current_user)):
    day = _resolve_day(body.day)
    reading = GlucoseMonitor.annotate(GlucoseReading(
        value_mg_dl=body.value_mg_dl,
        reading_type=body.reading_type if body.reading_type in ("fasting", "post_meal") else "fasting",
        date=day))
    db.upsert_glucose(user.id, {
        "value_mg_dl": reading.value_mg_dl, "reading_type": reading.reading_type,
        "reading_date": reading.date, "category": reading.category})
    return {"reading": reading.model_dump(mode="json"),
            "message": GlucoseMonitor.interpret(reading), "state": _snapshot(user, day)}


# ------------------------------ activity ------------------------------
@app.get("/api/activity/types")
def activity_types():
    return {"types": ActivityEstimator.activity_types()}


@app.post("/api/activity")
def log_activity(body: ActivityIn, user: AuthedUser = Depends(get_current_user)):
    day = _resolve_day(body.day)
    profile = _profile_from_row(db.get_profile(user.id))
    weight = profile.weight_kg if profile else 70.0
    burned = ActivityEstimator.calories(body.activity_type, body.duration_min, weight)
    try:
        db.add_activity(user.id, {
            "activity_date": day, "activity_type": body.activity_type,
            "duration_min": body.duration_min, "calories_burned": burned,
            "performed_at": body.performed_at, "note": body.note})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_SCHEMA_HINT.format(err=str(exc)[:160]))
    return {"calories_burned": burned, "state": _snapshot(user, day)}


@app.delete("/api/activity/{activity_id}")
def remove_activity(activity_id: int, day: Optional[str] = None,
                    user: AuthedUser = Depends(get_current_user)):
    db.delete_activity(user.id, activity_id)
    return _snapshot(user, day)


# PLACEHOLDER_ROUTES2

# ------------------------------ foods ------------------------------
@app.get("/api/foods")
def search_foods(q: str = "", rating: str = "", limit: int = 40,
                 user: AuthedUser = Depends(get_current_user)):
    results, q_norm = [], q.strip().lower()
    for _, row in _food_db.df.iterrows():
        record = row.to_dict()
        name, cat = str(record.get("food_name", "")), str(record.get("category", ""))
        if q_norm and q_norm not in name.lower() and q_norm not in cat.lower():
            continue
        s = _food_summary(record)
        if rating and s["diabetes_rating"] != rating:
            continue
        results.append(s)
    results.sort(key=lambda r: r["food_name"])
    return {"foods": results[:limit], "count": len(results)}


# ------------------------------ meals (one per type/day + audit) ------------------------------
@app.post("/api/meal")
def add_meal(body: MealIn, user: AuthedUser = Depends(get_current_user)):
    day = _resolve_day(body.day)
    foods, total, unresolved = _meal_nutrition(body.items)
    if not foods:
        raise HTTPException(status_code=400,
                            detail=f"No foods matched: {', '.join(unresolved) or 'none'}")

    existing = db.get_meal(user.id, day, body.meal_type)

    # Already have this meal type today and no decision yet -> ask the client.
    if existing and body.mode not in ("replace", "merge", "edit"):
        return {"status": "exists",
                "existing": {"meal_type": existing.get("meal_type"),
                             "nutrition": existing.get("nutrition") or {},
                             "foods": existing.get("foods") or []},
                "state": _snapshot(user, day)}

    action = "create"
    new_foods = [f.model_dump() for f in foods]
    new_nutrition = total

    if existing and body.mode == "merge":
        action = "merge"
        try:
            new_nutrition = Nutrition(**(existing.get("nutrition") or {})) + total
        except Exception:
            new_nutrition = total
        new_foods = (existing.get("foods") or []) + new_foods
    elif existing and body.mode in ("replace", "edit"):
        action = body.mode

    db.add_audit(user.id, day, body.meal_type, action,
                 {"before": existing, "items": [i.model_dump() for i in body.items]})
    try:
        db.upsert_meal(user.id, {
            "meal_date": day, "meal_type": body.meal_type,
            "nutrition": new_nutrition.model_dump(), "foods": new_foods,
            "eaten_at": body.eaten_at, "updated_at": datetime.now().isoformat()})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_SCHEMA_HINT.format(err=str(exc)[:160]))
    return {"status": "ok", "action": action, "unresolved": unresolved,
            "state": _snapshot(user, day)}


@app.delete("/api/meal")
def remove_meal(meal_type: str, day: Optional[str] = None,
                user: AuthedUser = Depends(get_current_user)):
    day = _resolve_day(day)
    existing = db.get_meal(user.id, day, meal_type)
    if existing:
        db.add_audit(user.id, day, meal_type, "delete", {"before": existing})
        db.delete_meal(user.id, day, meal_type)
    return _snapshot(user, day)


@app.get("/api/meal/audit")
def meal_audit(day: Optional[str] = None, user: AuthedUser = Depends(get_current_user)):
    return {"audit": db.meal_audit(user.id, _resolve_day(day) if day else None)}


@app.post("/api/meal/parse")
def parse_meal(body: ParseIn, user: AuthedUser = Depends(get_current_user)):
    if not _parser.check_connection():
        return {"ok": False, "reason": "AI meal parsing isn't configured (set GEMINI_API_KEY).", "items": []}
    parsed = _parser.parse_meal(body.text)
    if not parsed:
        return {"ok": False, "reason": "Could not parse that meal.", "items": []}
    return {"ok": True, "items": [
        {"food_name": f.food_name, "quantity": f.quantity, "unit": f.unit} for f in parsed.foods]}


# ------------------------------ guidance ------------------------------
@app.get("/api/exchanges")
def exchanges(food: str, user: AuthedUser = Depends(get_current_user)):
    return guidance.food_exchanges(_food_db, food, parser=_parser)


@app.post("/api/meal-check")
def meal_check(body: MealCheckIn, user: AuthedUser = Depends(get_current_user)):
    day = _resolve_day(body.day)
    profile = _profile_from_row(db.get_profile(user.id))
    goals = _effective_goals(profile, user.id, day)[0] if profile else None
    glucose = _glucose_model(db.get_glucose(user.id, day), day)

    items = [i.model_dump() for i in body.items]
    if body.text and not items and _parser.check_connection():
        parsed = _parser.parse_meal(body.text)
        if parsed:
            items = [{"food_name": f.food_name, "quantity": f.quantity, "unit": f.unit}
                     for f in parsed.foods]

    consumed = Nutrition(**_snapshot(user, day)["totals"])
    return guidance.meal_check(_food_db, _calc, items, goals, glucose, consumed, parser=_parser)


@app.get("/api/recommendations")
def recommendations(day: Optional[str] = None, user: AuthedUser = Depends(get_current_user)):
    day = _resolve_day(day)
    snap = _snapshot(user, day)
    profile = _profile_from_row(db.get_profile(user.id))
    tips = guidance.timing_tips(
        profile.diabetes_type if profile else "type2",
        profile.on_insulin if profile else False)
    return {"recommendations": snap["recommendations"], "timing_tips": tips,
            "meal_windows": guidance.MEAL_WINDOWS, "glucose_message": snap["glucose_message"]}


# PLACEHOLDER_ROUTES3

# ------------------------------ plan ------------------------------
@app.get("/api/plan")
def get_plan(day: Optional[str] = None, user: AuthedUser = Depends(get_current_user)):
    day = _resolve_day(day)
    profile = _profile_from_row(db.get_profile(user.id))
    if not profile:
        raise HTTPException(status_code=400, detail="Set up a profile first.")
    goals = _effective_goals(profile, user.id, day)[0]
    glucose = _glucose_model(db.get_glucose(user.id, day), day)
    plan = DiabetesMealPlanner(_food_db, _calc).generate(goals, glucose)
    return {
        "date": plan.date, "notes": plan.notes,
        "total_nutrition": plan.total_nutrition.model_dump(),
        "meals": [
            {"meal_type": m.meal_type, "carb_budget_g": m.carb_budget_g,
             "time_hint": m.time_hint, "foods": m.foods, "nutrition": m.nutrition.model_dump()}
            for m in plan.meals
        ],
    }


# ------------------------------ history + analysis ------------------------------
def _day_summaries(user_id: str) -> List[dict]:
    """Aggregate all logged data per day for history/analysis."""
    meals = db.all_meals(user_id)
    glucose = {g["reading_date"]: g for g in db.all_glucose(user_id)}
    acts = db.all_activities(user_id)

    by_day = {}
    for m in meals:
        d = m["meal_date"]
        day = by_day.setdefault(d, {"date": d, "total": Nutrition(), "meal_types": [],
                                    "meals": [], "activity_min": 0, "activities": []})
        try:
            day["total"] = day["total"] + Nutrition(**(m.get("nutrition") or {}))
        except Exception:
            pass
        day["meal_types"].append(m.get("meal_type"))
        day["meals"].append({"meal_type": m.get("meal_type"), "foods": m.get("foods") or [],
                             "nutrition": m.get("nutrition") or {}, "eaten_at": m.get("eaten_at")})
    for a in acts:
        d = a["activity_date"]
        day = by_day.setdefault(d, {"date": d, "total": Nutrition(), "meal_types": [],
                                    "meals": [], "activity_min": 0, "activities": []})
        day["activity_min"] += float(a.get("duration_min", 0) or 0)
        day["activities"].append({"activity_type": a.get("activity_type"),
                                  "duration_min": a.get("duration_min"),
                                  "calories_burned": a.get("calories_burned")})
    for d, g in glucose.items():
        day = by_day.setdefault(d, {"date": d, "total": Nutrition(), "meal_types": [],
                                    "meals": [], "activity_min": 0, "activities": []})
        day["glucose_value"] = float(g.get("value_mg_dl"))
        day["glucose_category"] = g.get("category")
    return [by_day[d] for d in sorted(by_day.keys(), reverse=True)]


@app.get("/api/history")
def history(user: AuthedUser = Depends(get_current_user)):
    days = _day_summaries(user.id)
    return {"days": [
        {"date": d["date"], "totals": d["total"].model_dump(),
         "meal_types": d["meal_types"], "meals": d["meals"],
         "glucose_value": d.get("glucose_value"), "glucose_category": d.get("glucose_category"),
         "activity_min": d["activity_min"], "activities": d["activities"]}
        for d in days]}


@app.get("/api/analysis")
def analysis(period: str = "week", user: AuthedUser = Depends(get_current_user)):
    """Ad-hoc analysis (not saved). Kept for compatibility."""
    return _compute_analysis(user.id, period)[0]


class AnalysisRunIn(BaseModel):
    period: str = "week"           # week | all | custom
    range_from: Optional[str] = None
    range_to: Optional[str] = None


def _compute_analysis(user_id: str, period: str,
                      rfrom: Optional[str] = None, rto: Optional[str] = None):
    profile = _profile_from_row(db.get_profile(user_id))
    base_goals = GoalCalculator.calculate_goals(profile) if profile else None
    summaries = _day_summaries(user_id)

    label = "All time"
    if period == "week":
        cutoff = (date.today() - timedelta(days=6)).isoformat()
        summaries = [d for d in summaries if d["date"] >= cutoff]
        label = "This week"
    elif period == "custom" and rfrom and rto:
        summaries = [d for d in summaries if rfrom <= d["date"] <= rto]
        label = f"{rfrom} → {rto}"

    days = []
    for d in summaries:
        gc = d.get("glucose_category")
        budget = 0
        if base_goals and gc:
            adj = {"normal": 1.0, "elevated": 0.9, "high": 0.8}.get(gc, 1.0)
            budget = base_goals.carbohydrate_g * adj
        elif base_goals:
            budget = base_goals.carbohydrate_g
        days.append({"date": d["date"], "totals": d["total"].model_dump(),
                     "glucose_value": d.get("glucose_value"), "glucose_category": gc,
                     "carb_budget": budget, "meal_count": len(d["meal_types"]),
                     "activity_min": d["activity_min"]})

    result = weekly_analysis(days, base_goals)
    # Narrative is generated separately (non-blocking) so the analysis is instant.
    result["narrative"] = None
    result["period"] = period
    result["label"] = label
    result["range_from"] = rfrom if period == "custom" else (summaries[-1]["date"] if summaries else None)
    result["range_to"] = rto if period == "custom" else (summaries[0]["date"] if summaries else None)
    return result, label


@app.get("/api/analyses")
def list_analyses(user: AuthedUser = Depends(get_current_user)):
    return {"analyses": db.list_analyses(user.id)}


@app.post("/api/analysis/run")
def run_analysis(body: AnalysisRunIn, user: AuthedUser = Depends(get_current_user)):
    result, label = _compute_analysis(user.id, body.period, body.range_from, body.range_to)
    try:
        saved = db.add_analysis(user.id, {
            "period": body.period, "range_from": result.get("range_from"),
            "range_to": result.get("range_to"), "label": label,
            "stats": result["stats"], "insights": result["insights"],
            "next_week_plan": result["next_week_plan"],
            "narrative": result.get("summary")})  # deterministic, clean, instant
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_SCHEMA_HINT.format(err=str(exc)[:160]))
    return {"analysis": saved, "computed": result, "llm_ready": _parser.check_connection()}


def _valid_ai_summary(text: Optional[str]) -> bool:
    """Reject empty / raw-JSON / truncated LLM output."""
    if not text:
        return False
    t = text.strip()
    if len(t) < 40 or "{" in t or '"summary"' in t.lower():
        return False
    return t[-1] in ".!?"  # must end as a complete sentence


@app.post("/api/analysis/{analysis_id}/narrative")
def analysis_narrative(analysis_id: int, user: AuthedUser = Depends(get_current_user)):
    """Optionally rewrite a saved analysis summary with the LLM. Falls back to the
    existing (clean, deterministic) summary if the model output isn't usable."""
    row = next((a for a in db.list_analyses(user.id, limit=100) if a.get("id") == analysis_id), None)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    existing = row.get("narrative")
    if not _parser.check_connection():
        return {"narrative": existing, "ai": False, "reason": "LLM not configured."}
    ctx = ("Stats: " + str(row.get("stats", {})) + "\nInsights: "
           + "; ".join(row.get("insights", []) or []))
    text = _parser.narrative(ctx)
    if _valid_ai_summary(text):
        try:
            db.update_analysis(user.id, analysis_id, {"narrative": text})
        except Exception:
            pass
        return {"narrative": text, "ai": True}
    return {"narrative": existing, "ai": False, "reason": "AI summary unavailable; kept the standard summary."}


@app.delete("/api/analysis/{analysis_id}")
def remove_analysis(analysis_id: int, user: AuthedUser = Depends(get_current_user)):
    db.delete_analysis(user.id, analysis_id)
    return {"analyses": db.list_analyses(user.id)}


@app.post("/api/reset-day")
def reset_day(day: Optional[str] = None, user: AuthedUser = Depends(get_current_user)):
    day = _resolve_day(day)
    db.delete_meals_for_day(user.id, day)
    return _snapshot(user, day)


# ------------------------------ serve built frontend ------------------------------
_DIST = config.FRONTEND_DIST
if os.path.isdir(os.path.join(_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")


@app.get("/{full_path:path}")
def spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    index = os.path.join(_DIST, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse(status_code=503, content={
        "detail": "Frontend not built yet. Run: cd frontend && npm install && npm run build"})



