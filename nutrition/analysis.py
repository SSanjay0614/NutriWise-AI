"""
Rules-based weekly / overall analysis and a next-week plan.

Consumes a list of per-day summaries and produces deterministic statistics,
insight bullets, and concrete targets for the coming week. A natural-language
narrative can be layered on top via the LLM when available (see llm/narrative).
"""
from typing import List, Optional
from models.schemas import NutrientGoals


def _avg(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def weekly_analysis(days: List[dict], goals: Optional[NutrientGoals]) -> dict:
    """
    `days`: list of {date, totals(dict), glucose_value, glucose_category,
                     carb_budget, meal_count, activity_min}
    Most-recent-first or oldest-first both fine; we sort by date.
    """
    days = sorted(days, key=lambda d: d.get("date", ""))
    logged = [d for d in days if d.get("meal_count", 0) > 0 or d.get("glucose_value")]

    glucose_vals = [d.get("glucose_value") for d in days if d.get("glucose_value")]
    categories = [d.get("glucose_category") for d in days if d.get("glucose_category")]
    in_range = sum(1 for c in categories if c == "normal")

    carbs = [(d["totals"] or {}).get("carbohydrate_g") for d in logged]
    fiber = [(d["totals"] or {}).get("fiber_g") for d in logged]
    sugar = [(d["totals"] or {}).get("sugar_g") for d in logged]
    calories = [(d["totals"] or {}).get("calories_kcal") for d in logged]

    over_budget_days = sum(
        1 for d in logged
        if (d.get("carb_budget") or 0) > 0
        and ((d["totals"] or {}).get("carbohydrate_g", 0) > d["carb_budget"])
    )
    active_days = sum(1 for d in days if d.get("activity_min", 0) > 0)
    total_activity = sum(d.get("activity_min", 0) for d in days)

    stats = {
        "days_tracked": len(logged),
        "glucose_readings": len(glucose_vals),
        "avg_fasting_glucose": _avg(glucose_vals),
        "days_in_range": in_range,
        "avg_carbs_g": _avg(carbs),
        "avg_fiber_g": _avg(fiber),
        "avg_sugar_g": _avg(sugar),
        "avg_calories_kcal": _avg(calories),
        "days_over_carb_budget": over_budget_days,
        "active_days": active_days,
        "total_activity_min": total_activity,
    }

    # Glucose trend: first half vs second half.
    trend = "flat"
    if len(glucose_vals) >= 4:
        half = len(glucose_vals) // 2
        first, second = _avg(glucose_vals[:half]), _avg(glucose_vals[half:])
        if first and second:
            if second > first + 5:
                trend = "rising"
            elif second < first - 5:
                trend = "improving"
    stats["glucose_trend"] = trend

    # ----- insights (rules) -----
    insights = []
    if stats["avg_fasting_glucose"] is not None:
        insights.append(f"Average fasting glucose was {stats['avg_fasting_glucose']} mg/dL "
                        f"across {stats['glucose_readings']} reading(s); {in_range} day(s) in range.")
        if trend == "rising":
            insights.append("Fasting readings trended upward — tighten carbs and sugar this week.")
        elif trend == "improving":
            insights.append("Fasting readings trended downward — nice, keep it up.")
    if goals and carbs:
        if over_budget_days >= max(1, len(logged) // 2):
            insights.append(f"Carbs were over budget on {over_budget_days}/{len(logged)} logged day(s).")
        else:
            insights.append(f"Carbs stayed within budget on most logged days.")
    if goals and stats["avg_fiber_g"] is not None and stats["avg_fiber_g"] < goals.fiber_min_g:
        insights.append(f"Fiber averaged {stats['avg_fiber_g']}g, below your {goals.fiber_min_g:.0f}g target.")
    if stats["avg_sugar_g"] is not None and goals and stats["avg_sugar_g"] > goals.sugar_max_g:
        insights.append(f"Sugar averaged {stats['avg_sugar_g']}g, above the {goals.sugar_max_g:.0f}g ceiling.")
    insights.append(f"Active on {active_days} day(s), {total_activity:.0f} min total.")
    if not logged:
        insights = ["Not enough logged days yet — log meals and a daily glucose reading to build your analysis."]

    # ----- next-week plan (rules) -----
    plan = []
    if goals:
        plan.append(f"Keep daily carbs at or under {goals.carbohydrate_g:.0f}g, spread across meals.")
        if stats["avg_fiber_g"] is None or stats["avg_fiber_g"] < goals.fiber_min_g:
            plan.append(f"Add fiber to reach {goals.fiber_min_g:.0f}g/day (dals, vegetables, whole grains).")
        if stats["avg_sugar_g"] is not None and stats["avg_sugar_g"] > goals.sugar_max_g:
            plan.append("Cut sugary drinks/desserts to get under the 25g sugar ceiling.")
    if stats["glucose_readings"] < len(days):
        plan.append("Log a fasting reading every morning for a complete picture.")
    if total_activity < 150:
        plan.append(f"Aim for 150 min of activity next week (you did {total_activity:.0f} min).")
    else:
        plan.append("Maintain your activity — 150+ min/week supports insulin sensitivity.")
    plan.append("Favor low-GI, high-fiber meals and a short post-meal walk.")

    return {"stats": stats, "insights": insights, "next_week_plan": plan,
            "summary": coach_summary(stats, goals)}


def coach_summary(stats: dict, goals: Optional[NutrientGoals]) -> str:
    """
    A clean, deterministic 3-4 sentence coach summary from the stats.
    Always well-formed (no LLM needed) — used as the default narrative.
    """
    tracked = stats.get("days_tracked", 0)
    if not tracked:
        return ("No meals or readings logged in this period yet. Start by logging your "
                "meals and a morning glucose reading - once there's a few days of data, "
                "you'll get a real summary and a plan here.")

    fiber_target = goals.fiber_min_g if goals else 25
    sugar_ceiling = goals.sugar_max_g if goals else 25
    carb_budget = goals.carbohydrate_g if goals else 0

    wins = []
    if stats.get("total_activity_min", 0) >= 60:
        wins.append(f"you got {stats['total_activity_min']:.0f} minutes of activity in")
    if stats.get("avg_fiber_g") is not None and stats["avg_fiber_g"] >= fiber_target:
        wins.append(f"your fiber averaged a strong {stats['avg_fiber_g']:.0f}g")
    if stats.get("glucose_trend") == "improving":
        wins.append("your fasting readings are trending down")
    if stats.get("avg_sugar_g") is not None and stats["avg_sugar_g"] <= sugar_ceiling:
        wins.append("you kept sugar under control")
    if stats.get("days_over_carb_budget", 0) == 0 and carb_budget:
        wins.append("you stayed within your carb budget")

    if stats.get("glucose_trend") == "rising":
        focus = "your fasting glucose crept up, so tightening carbs and sugar is the thing to watch next week"
    elif stats.get("avg_sugar_g") is not None and stats["avg_sugar_g"] > sugar_ceiling:
        focus = (f"your sugar averaged {stats['avg_sugar_g']:.0f}g against a {sugar_ceiling:.0f}g ceiling - "
                 "cutting sugary drinks and sweets is the biggest lever")
    elif carb_budget and stats.get("days_over_carb_budget", 0) >= max(1, tracked // 2):
        focus = (f"carbs ran over budget on {stats['days_over_carb_budget']} of {tracked} days - "
                 "smaller rice/bread portions and more low-GI choices will help")
    elif stats.get("avg_fiber_g") is not None and stats["avg_fiber_g"] < fiber_target:
        focus = (f"fiber averaged {stats['avg_fiber_g']:.0f}g below your {fiber_target:.0f}g target - "
                 "lean on dals, vegetables, and whole grains")
    elif stats.get("total_activity_min", 0) < 150:
        focus = (f"you logged {stats.get('total_activity_min', 0):.0f} minutes of activity - "
                 "nudging toward 150 a week will improve your numbers")
    else:
        focus = "keep doing exactly what you're doing - your targets are in a good place"

    opener = (f"Nice work logging {tracked} day{'s' if tracked != 1 else ''} this period"
              + (f" - {wins[0]}" if wins else "") + ".")
    second = f"On top of that, {wins[1]}." if len(wins) > 1 else ""
    glu = ""
    if stats.get("avg_fasting_glucose") is not None:
        glu = f"Your fasting glucose averaged {stats['avg_fasting_glucose']:.0f} mg/dL. "
    focus_sentence = f"The one thing to focus on next week: {focus}."
    return " ".join(p for p in [opener, second, (glu + focus_sentence).strip()] if p)
