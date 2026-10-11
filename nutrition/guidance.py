"""
Diabetes diet guidance helpers: meal-timing advice, food exchanges
(swap suggestions), a single-meal "is this OK?" checker, and a rules-based
weekly analysis with a next-week plan.

All deterministic and educational; an optional LLM narrative is layered on top
via the Gemini LLM when configured.
"""
from typing import List, Optional
from models.schemas import NutrientGoals, GlucoseReading, Nutrition
from nutrition.glucose import GlucoseMonitor
from nutrition.diabetes_score import DiabetesScorer
from nutrition.calculator import NutritionCalculator

# Suggested eating windows (general guidance for steady blood sugar).
MEAL_WINDOWS = {
    "breakfast": "7:00–9:00 AM",
    "lunch": "12:30–2:00 PM",
    "snack": "4:00–5:00 PM",
    "dinner": "7:00–8:30 PM",
}


def timing_tips(diabetes_type: str = "type2", on_insulin: bool = False) -> List[str]:
    """General meal-timing guidance for diabetes."""
    tips = [
        "Eat at consistent times each day — regular spacing keeps blood sugar steady.",
        "Don't skip meals; skipping can cause lows then rebound highs.",
        "Finish dinner at least 2–3 hours before bed to help overnight glucose.",
        "Spread carbohydrates across the day rather than loading one meal.",
        "A short walk after meals helps blunt the post-meal glucose rise.",
    ]
    if on_insulin:
        tips.insert(1, "Keep meal timing and carb amounts consistent to match your insulin "
                       "(follow your doctor's dosing — this app never advises insulin).")
    if diabetes_type == "gestational":
        tips.append("Prefer smaller, more frequent meals with a protein-containing bedtime snack.")
    return tips


def _gi_rating(gi) -> str:
    try:
        gi = float(gi)
    except (TypeError, ValueError):
        return "moderate"
    return "good" if gi <= 55 else "moderate" if gi <= 69 else "limit"


def _general_good_foods(food_db, limit=4) -> List[dict]:
    recs = food_db.get_rated_foods(ratings=["good"],
                                   categories=["Indian Curry", "Protein", "Vegetable", "Indian Side"],
                                   limit=limit)
    return [{"food_name": str(r["food_name"]),
             "glycemic_index": int(r["glycemic_index"]) if r.get("glycemic_index") is not None else None,
             "rating": r["diabetes_rating"],
             "carbohydrate_g": float(r.get("carbohydrate_g", 0) or 0),
             "fiber_g": float(r.get("fiber_g", 0) or 0)} for r in recs]


def food_exchanges(food_db, food_name: str, limit: int = 4, parser=None) -> dict:
    """
    Given a food, return better diabetes-friendly swaps.

    - In the dataset  -> higher-scoring foods, preferring the same category.
    - Not in dataset  -> ask the LLM (Gemini) for an estimate + swaps, and still
      offer dataset "good" foods. If the LLM is unavailable, fall back to general
      dataset good foods so the user always gets options.
    """
    record = food_db.lookup_food(food_name)

    if record:
        rating, score = DiabetesScorer.score_record(record)
        category = str(record.get("category", ""))
        gi = record.get("glycemic_index")
        pool = [r for r in food_db.get_rated_foods(ratings=["good", "moderate"], categories=[category])
                if str(r["food_name"]).lower() != food_name.strip().lower()]
        better = [r for r in pool if r["diabetes_score"] > score]
        chosen = (better or pool)[:limit]
        return {
            "found": True, "source": "dataset",
            "food_name": str(record.get("food_name")), "category": category,
            "glycemic_index": int(gi) if gi is not None else None,
            "rating": rating, "needs_swap": rating == "limit",
            "note": "",
            "alternatives": [
                {"food_name": str(r["food_name"]),
                 "glycemic_index": int(r["glycemic_index"]) if r.get("glycemic_index") is not None else None,
                 "rating": r["diabetes_rating"],
                 "carbohydrate_g": float(r.get("carbohydrate_g", 0) or 0),
                 "fiber_g": float(r.get("fiber_g", 0) or 0)} for r in chosen],
        }

    # Not in the dataset -> try the LLM.
    guide = parser.food_guidance(food_name) if (parser and parser.check_connection()) else None
    alternatives, note, gi, rating = [], "", None, "moderate"
    if guide:
        gi = guide.get("glycemic_index")
        rating = _gi_rating(gi) if not guide.get("diabetes_friendly", True) or gi is not None else "moderate"
        note = (guide.get("note") or "").strip()
        # Prefer LLM-named swaps that exist in our dataset; keep others as text.
        for name in (guide.get("alternatives") or [])[:limit]:
            rec = food_db.lookup_food(str(name))
            if rec:
                r2, _ = DiabetesScorer.score_record(rec)
                alternatives.append({"food_name": str(rec.get("food_name")),
                                     "glycemic_index": int(rec["glycemic_index"]) if rec.get("glycemic_index") is not None else None,
                                     "rating": r2, "carbohydrate_g": float(rec.get("carbohydrate_g", 0) or 0),
                                     "fiber_g": float(rec.get("fiber_g", 0) or 0)})
            else:
                alternatives.append({"food_name": str(name), "glycemic_index": None,
                                     "rating": None, "carbohydrate_g": 0, "fiber_g": 0})
    if not alternatives:
        alternatives = _general_good_foods(food_db, limit)
        if not note:
            note = ("Not in our dataset" + ("" if guide else " and AI estimation is offline")
                    + " - here are solid low-GI options you can eat instead.")

    return {
        "found": bool(guide), "source": "llm" if guide else "fallback",
        "food_name": (guide.get("food_name") if guide else food_name),
        "category": (guide.get("category", "") if guide else ""),
        "glycemic_index": int(gi) if gi is not None else None,
        "rating": rating, "needs_swap": True, "note": note,
        "alternatives": alternatives,
    }


def meal_check(
    food_db,
    calculator: NutritionCalculator,
    items: List[dict],
    goals: Optional[NutrientGoals],
    glucose: Optional[GlucoseReading],
    consumed: Optional[Nutrition] = None,
    parser=None,
) -> dict:
    """
    "I'm going to eat X — is it OK?" checker.

    Resolves foods against the dataset; anything missing is estimated via the LLM
    (Gemini) when available. Judges the total against the remaining carb budget
    and today's glucose, and returns a verdict, reasons, and healthier swaps.
    """
    consumed = consumed or Nutrition()
    proposed = Nutrition()
    resolved, unresolved, weak = [], [], []
    llm_ok = bool(parser and parser.check_connection())

    for it in items:
        name = it.get("food_name", "")
        qty = float(it.get("quantity", 1) or 1)
        unit = it.get("unit", "serving")
        rec = food_db.lookup_food(name)
        if rec:
            weight = food_db.resolve_weight(rec, qty, unit)
            proposed = proposed + calculator.calculate_nutrition(rec, weight)
            rating, _ = DiabetesScorer.score_record(rec)
            resolved.append({"food_name": str(rec.get("food_name")), "rating": rating,
                             "glycemic_index": rec.get("glycemic_index"), "source": "dataset"})
            if rating == "limit":
                weak.append(str(rec.get("food_name")))
            continue

        # Not in dataset -> LLM estimate.
        est = parser.estimate_food_nutrition(name, qty, unit) if llm_ok else None
        if est:
            proposed = proposed + Nutrition(
                calories_kcal=est.calories_kcal, protein_g=est.protein_g,
                carbohydrate_g=est.carbohydrate_g, fat_g=est.fat_g, fiber_g=est.fiber_g,
                sugar_g=est.sugar_g, sodium_mg=est.sodium_mg)
            rating, _ = DiabetesScorer.score(est.glycemic_index, None, est.sugar_g,
                                             est.fiber_g, est.carbohydrate_g)
            resolved.append({"food_name": est.food_name or name, "rating": rating,
                             "glycemic_index": est.glycemic_index, "source": "llm"})
            if rating == "limit":
                weak.append(est.food_name or name)
        else:
            unresolved.append(name)

    reasons, swaps = [], []
    verdict = "good"

    if goals:
        carb_adj = GlucoseMonitor.carb_adjustment(glucose)
        budget = goals.carbohydrate_g * carb_adj
        remaining = budget - consumed.carbohydrate_g
        if proposed.carbohydrate_g > remaining:
            verdict = "caution"
            reasons.append(
                f"Adds {proposed.carbohydrate_g:.0f}g carbs, but only ~{max(0, remaining):.0f}g "
                f"remain in today's budget.")
        elif proposed.carbohydrate_g > remaining * 0.6:
            verdict = "ok" if verdict == "good" else verdict
            reasons.append(
                f"Uses a large share of your remaining ~{max(0, remaining):.0f}g carb budget.")
        if proposed.sugar_g > 15:
            verdict = "caution"
            reasons.append(f"High in sugar (~{proposed.sugar_g:.0f}g).")

    glucose_cat = None
    if glucose is not None:
        glucose_cat = glucose.category if glucose.category != "unknown" else GlucoseMonitor.categorize(glucose)
    if glucose_cat in ("elevated", "high") and weak:
        verdict = "caution"
        reasons.append(f"Your reading is {glucose_cat}; {', '.join(weak)} are high-GI picks today.")

    for w in weak:
        ex = food_exchanges(food_db, w, limit=3, parser=parser)
        if ex["alternatives"]:
            swaps.append({"instead_of": w,
                          "try": [a["food_name"] for a in ex["alternatives"]]})

    if not reasons:
        reasons.append("Fits within your remaining budget and today's targets.")

    return {
        "verdict": verdict,
        "reasons": reasons,
        "resolved": resolved,
        "unresolved": unresolved,
        "proposed_nutrition": proposed.model_dump(),
        "swaps": swaps,
    }
