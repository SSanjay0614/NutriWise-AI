"""
Diabetes-aware next-meal recommendation engine.

Uses the day's intake vs personalized goals and today's glucose reading to
suggest what the next meal should emphasize, drawing low-GI, high-fiber,
diabetes-"good" foods from the dataset.
"""
from typing import Optional, List
from models.schemas import Recommendation, DailyIntake, NutrientGoals, GlucoseReading
from nutrition.glucose import GlucoseMonitor


class MealRecommender:
    """Recommends next-meal priorities for diabetes management."""

    @staticmethod
    def _good_foods(food_db, categories: List[str], limit: int = 6) -> List[str]:
        """Pull diabetes-'good' food names from the dataset for given categories."""
        if food_db is None:
            return []
        records = food_db.get_rated_foods(
            ratings=["good"], categories=categories, limit=limit
        )
        return [str(r["food_name"]) for r in records]

    @staticmethod
    def get_next_meal_recommendation(
        daily_intake: DailyIntake,
        goals: NutrientGoals,
        glucose: Optional[GlucoseReading] = None,
        food_db=None,
    ) -> list:
        """Generate diabetes-aware recommendations for the next meal."""
        recommendations: List[Recommendation] = []
        nut = daily_intake.total_nutrition

        carb_adj = GlucoseMonitor.carb_adjustment(glucose)
        carb_budget = goals.carbohydrate_g * carb_adj
        remaining_carbs = carb_budget - nut.carbohydrate_g

        # High glucose today -> top-priority low-GI steer.
        glucose_cat = None
        if glucose is not None:
            glucose_cat = glucose.category if glucose.category != "unknown" \
                else GlucoseMonitor.categorize(glucose)
        if glucose_cat in ("elevated", "high"):
            recommendations.append(
                Recommendation(
                    message="Keep your next meal low-GI and high-fiber",
                    priority="high",
                    reason=(
                        f"Today's reading is {glucose_cat}. Low-GI, fiber-rich meals "
                        "raise blood sugar more slowly and steadily."
                    ),
                    suggested_foods=MealRecommender._good_foods(
                        food_db,
                        ["Indian Curry", "Protein", "Vegetable", "Dairy"],
                    ) or ["Dal", "Palak Paneer", "Vegetables", "Curd", "Tofu"],
                )
            )

        # Over / near carb budget.
        if carb_budget > 0 and remaining_carbs <= 0:
            recommendations.append(
                Recommendation(
                    message="You're out of carb budget — choose non-starchy foods next",
                    priority="high",
                    reason=(
                        f"Carbs so far ({nut.carbohydrate_g:.0f}g) have reached today's "
                        f"budget ({carb_budget:.0f}g). Favor protein and vegetables over "
                        "rice/bread/noodles."
                    ),
                    suggested_foods=MealRecommender._good_foods(
                        food_db, ["Protein", "Vegetable", "Indian Curry"],
                    ) or ["Grilled Chicken", "Paneer", "Broccoli", "Spinach", "Dal Tadka"],
                )
            )
        elif carb_budget > 0 and remaining_carbs < carb_budget * 0.25:
            recommendations.append(
                Recommendation(
                    message="Carb budget is running low — keep the next meal light on carbs",
                    priority="medium",
                    reason=(
                        f"About {remaining_carbs:.0f}g of carbs remain for today. "
                        "Lean on protein, vegetables, and low-GI sides."
                    ),
                    suggested_foods=MealRecommender._good_foods(
                        food_db, ["Protein", "Vegetable", "Indian Side"],
                    ) or ["Boiled Egg", "Tofu", "Carrot", "Sambar"],
                )
            )

        # Low fiber.
        if nut.fiber_g < goals.fiber_min_g:
            short = goals.fiber_min_g - nut.fiber_g
            recommendations.append(
                Recommendation(
                    message="Add fiber-rich foods to your next meal",
                    priority="high" if short > goals.fiber_min_g * 0.5 else "medium",
                    reason=(
                        f"Fiber is {short:.0f}g below today's {goals.fiber_min_g:.0f}g "
                        "minimum. Fiber slows glucose absorption and improves control."
                    ),
                    suggested_foods=MealRecommender._good_foods(
                        food_db, ["Indian Curry", "Vegetable", "Snack"],
                    ) or ["Chana Masala", "Rajma Curry", "Broccoli", "Roasted Chana"],
                )
            )

        # Low protein.
        if nut.protein_g < goals.protein_g:
            recommendations.append(
                Recommendation(
                    message="Include lean protein in your next meal",
                    priority="medium",
                    reason=(
                        f"Protein ({nut.protein_g:.0f}g) is below today's "
                        f"{goals.protein_g:.0f}g target. Protein steadies blood sugar "
                        "and keeps you full."
                    ),
                    suggested_foods=MealRecommender._good_foods(
                        food_db, ["Protein", "Dairy"],
                    ) or ["Grilled Chicken", "Paneer", "Tofu", "Greek Yogurt", "Boiled Egg"],
                )
            )

        # Sugar over ceiling.
        if nut.sugar_g > goals.sugar_max_g:
            recommendations.append(
                Recommendation(
                    message="Avoid added sugar for the rest of the day",
                    priority="high",
                    reason=(
                        f"Sugar ({nut.sugar_g:.0f}g) is over the {goals.sugar_max_g:.0f}g "
                        "ceiling. Skip sweets and sugary drinks."
                    ),
                    suggested_foods=["Water", "Buttermilk", "Black Coffee", "Plain Curd"],
                )
            )

        # Sodium over ceiling.
        if nut.sodium_mg > goals.sodium_max_mg:
            recommendations.append(
                Recommendation(
                    message="Choose lower-sodium options next",
                    priority="medium",
                    reason=(
                        f"Sodium ({nut.sodium_mg:.0f}mg) is over the "
                        f"{goals.sodium_max_mg:.0f}mg ceiling, which affects blood pressure."
                    ),
                    suggested_foods=MealRecommender._good_foods(
                        food_db, ["Vegetable", "Fruit"],
                    ) or ["Fresh vegetables", "Whole fruit", "Home-cooked dal"],
                )
            )

        # Nothing flagged.
        if not recommendations:
            recommendations.append(
                Recommendation(
                    message="On track — keep meals balanced and low-GI",
                    priority="low",
                    reason=(
                        "Your intake is within your diabetes goals so far. Maintain "
                        "low-GI, high-fiber, portion-controlled meals."
                    ),
                    suggested_foods=MealRecommender._good_foods(
                        food_db, ["Indian Curry", "Protein", "Vegetable"],
                    ) or ["Dal Tadka", "Grilled Fish", "Mixed Vegetable Curry"],
                )
            )

        return recommendations

    @staticmethod
    def format_recommendations(recommendations: list) -> str:
        """Format recommendations as readable text."""
        text = "\n==== NEXT MEAL RECOMMENDATIONS ====\n\n"
        for rec in recommendations:
            icon = "[HIGH]" if rec.priority == "high" else \
                   "[MED] " if rec.priority == "medium" else "[OK]  "
            text += f"{icon} {rec.message}\n"
            text += f"       Reason: {rec.reason}\n"
            if rec.suggested_foods:
                text += f"       Try: {', '.join(rec.suggested_foods)}\n"
            text += "\n"
        return text
