"""
Diabetes-friendly daily meal plan generator.

Builds a full day (breakfast / lunch / dinner / snack) that fits the user's
carbohydrate budget and today's glucose status, preferring low-GI,
diabetes-"good" foods from the dataset.
"""
from datetime import date
from typing import Optional, List
from models.schemas import (
    NutrientGoals, GlucoseReading, DailyPlan, DailyPlanMeal, Nutrition,
)
from nutrition.calculator import NutritionCalculator
from nutrition.glucose import GlucoseMonitor


class DiabetesMealPlanner:
    """Generates a one-day diabetes-friendly meal plan."""

    # Share of the daily carb budget assigned to each meal slot.
    CARB_SPLIT = {
        "breakfast": 0.25,
        "lunch": 0.30,
        "dinner": 0.30,
        "snack": 0.15,
    }

    # Preferred dataset categories per meal slot (best-first within each).
    CATEGORY_POOLS = {
        "breakfast": ["South Indian Breakfast", "Indian Breakfast", "Dairy", "Protein"],
        "lunch": ["Indian Main", "Indian Curry", "Protein", "Vegetable", "Indian Side"],
        "dinner": ["Indian Curry", "Protein", "Vegetable", "Indian Main", "Indian Side"],
        "snack": ["Nuts", "Snack", "Fruit", "Dairy"],
    }

    # Suggested eating windows for each meal slot.
    TIME_HINTS = {
        "breakfast": "7:00–9:00 AM",
        "lunch": "12:30–2:00 PM",
        "dinner": "7:00–8:30 PM",
        "snack": "4:00–5:00 PM",
    }

    def __init__(self, food_db, calculator: Optional[NutritionCalculator] = None):
        self.food_db = food_db
        self.calculator = calculator or NutritionCalculator()

    def generate(
        self,
        goals: NutrientGoals,
        glucose: Optional[GlucoseReading] = None,
    ) -> DailyPlan:
        """Create a DailyPlan sized to the (glucose-adjusted) carb budget."""
        carb_adj = GlucoseMonitor.carb_adjustment(glucose)
        carb_budget = goals.carbohydrate_g * carb_adj

        plan = DailyPlan(date=date.today().isoformat())
        notes = list(goals.notes)
        if carb_adj < 1.0:
            notes.append(
                f"Carb budget reduced to {carb_budget:.0f}g today based on your "
                "glucose reading."
            )
        plan.notes = notes

        total = Nutrition()
        used_foods: set = set()

        for meal_type, share in self.CARB_SPLIT.items():
            slot_budget = carb_budget * share
            meal = self._build_meal(meal_type, slot_budget, used_foods)
            plan.meals.append(meal)
            total = total + meal.nutrition

        plan.total_nutrition = total
        return plan

    def _build_meal(
        self, meal_type: str, carb_slot_g: float, used_foods: set
    ) -> DailyPlanMeal:
        """Greedily fill one meal slot with low-GI foods up to its carb budget."""
        candidates = self.food_db.get_rated_foods(
            ratings=["good", "moderate"],
            categories=self.CATEGORY_POOLS.get(meal_type),
        )

        meal = DailyPlanMeal(meal_type=meal_type, carb_budget_g=round(carb_slot_g, 0),
                             time_hint=self.TIME_HINTS.get(meal_type, ""))
        meal_nutrition = Nutrition()
        carbs_so_far = 0.0
        max_items = 3 if meal_type != "snack" else 2

        for record in candidates:
            if len(meal.foods) >= max_items:
                break
            name = str(record["food_name"])
            if name in used_foods:
                continue

            serving_g = float(record.get("serving_size_g", 100) or 100)
            item_nut = self.calculator.calculate_nutrition(record, serving_g)

            # Keep the slot within ~1.2x its carb budget.
            if carbs_so_far + item_nut.carbohydrate_g > carb_slot_g * 1.2 and meal.foods:
                continue

            meal.foods.append(f"{name} (1 serving, GI {record.get('glycemic_index', '?')})")
            meal_nutrition = meal_nutrition + item_nut
            carbs_so_far += item_nut.carbohydrate_g
            used_foods.add(name)

        meal.nutrition = meal_nutrition
        return meal

    @staticmethod
    def format_plan(plan: DailyPlan) -> str:
        """Readable text rendering of a daily plan."""
        text = "\n==== TODAY'S DIABETES-FRIENDLY MEAL PLAN ====\n\n"
        for meal in plan.meals:
            text += f"{meal.meal_type.capitalize()} "
            text += f"(carb budget ~{meal.carb_budget_g:.0f}g"
            text += f", {meal.time_hint})" if meal.time_hint else ")"
            text += ":\n"
            if meal.foods:
                for food in meal.foods:
                    text += f"  - {food}\n"
            else:
                text += "  - (no suitable item found)\n"
            n = meal.nutrition
            text += (
                f"    => {n.calories_kcal:.0f} kcal | carbs {n.carbohydrate_g:.0f}g | "
                f"protein {n.protein_g:.0f}g | fiber {n.fiber_g:.0f}g\n\n"
            )
        t = plan.total_nutrition
        text += (
            f"Day total: {t.calories_kcal:.0f} kcal | carbs {t.carbohydrate_g:.0f}g | "
            f"protein {t.protein_g:.0f}g | fiber {t.fiber_g:.0f}g | sugar {t.sugar_g:.0f}g\n"
        )
        if plan.notes:
            text += "\nNotes:\n"
            for note in plan.notes:
                text += f"  - {note}\n"
        return text
