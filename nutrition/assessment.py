"""
Diabetes-aware nutrition assessment (rule-based).

Compares the day's accumulated intake against the user's personalized
NutrientGoals, factors in today's glucose reading, and produces
observations + suggestions. Educational only, not a medical diagnosis.
"""
from typing import Optional
from models.schemas import DailyIntake, NutrientGoals, GlucoseReading
from nutrition.glucose import GlucoseMonitor


class NutritionAssessment:
    """Rule-based assessment of daily intake against diabetes goals."""

    @staticmethod
    def assess_daily_intake(
        daily_intake: DailyIntake,
        goals: NutrientGoals,
        glucose: Optional[GlucoseReading] = None,
    ) -> dict:
        """
        Assess daily intake against personalized goals + today's glucose.

        Returns a dict with observations, suggestions, and status maps.
        """
        nut = daily_intake.total_nutrition
        assessment = {
            "observations": [],
            "suggestions": [],
            "goal_status": {},
            "glucose": None,
        }

        # Carbohydrate budget (adjusted down when glucose is elevated/high).
        carb_adj = GlucoseMonitor.carb_adjustment(glucose)
        carb_budget = goals.carbohydrate_g * carb_adj
        if carb_budget > 0:
            carb_pct = (nut.carbohydrate_g / carb_budget) * 100
            if nut.carbohydrate_g > carb_budget:
                over = nut.carbohydrate_g - carb_budget
                assessment["observations"].append(
                    f"Carbohydrates ({nut.carbohydrate_g:.0f}g) are over today's budget "
                    f"({carb_budget:.0f}g) by {over:.0f}g."
                )
                assessment["suggestions"].append(
                    "Shift remaining meals to low-GI, non-starchy choices (vegetables, "
                    "dal, paneer, eggs) and reduce rice/bread portions."
                )
                assessment["goal_status"]["carbohydrate"] = "Over"
            elif carb_pct >= 80:
                assessment["observations"].append(
                    f"Carbohydrates ({nut.carbohydrate_g:.0f}g) are near today's budget "
                    f"({carb_budget:.0f}g)."
                )
                assessment["goal_status"]["carbohydrate"] = "Near limit"
            else:
                assessment["goal_status"]["carbohydrate"] = "Within budget"

        # Sugar ceiling.
        if nut.sugar_g > goals.sugar_max_g:
            assessment["observations"].append(
                f"Sugar ({nut.sugar_g:.0f}g) exceeds the daily ceiling "
                f"({goals.sugar_max_g:.0f}g)."
            )
            assessment["suggestions"].append(
                "Cut sweets, sugary drinks, and desserts. Prefer whole fruit in moderation."
            )
            assessment["goal_status"]["sugar"] = "Over"
        else:
            assessment["goal_status"]["sugar"] = "Within limit"

        # Fiber minimum.
        if nut.fiber_g < goals.fiber_min_g:
            short = goals.fiber_min_g - nut.fiber_g
            assessment["observations"].append(
                f"Fiber ({nut.fiber_g:.0f}g) is {short:.0f}g below the daily minimum "
                f"({goals.fiber_min_g:.0f}g)."
            )
            assessment["suggestions"].append(
                "Add fiber: whole grains, legumes, vegetables, and whole fruit. "
                "Fiber slows glucose absorption."
            )
            assessment["goal_status"]["fiber"] = "Low"
        else:
            assessment["goal_status"]["fiber"] = "Adequate"

        # Protein target.
        if nut.protein_g < goals.protein_g:
            assessment["goal_status"]["protein"] = "Low"
            assessment["suggestions"].append(
                "Include lean protein (dal, paneer, tofu, eggs, chicken, fish) to "
                "stay full and steady blood sugar."
            )
        else:
            assessment["goal_status"]["protein"] = "Adequate"

        # Sodium ceiling.
        if nut.sodium_mg > goals.sodium_max_mg:
            assessment["observations"].append(
                f"Sodium ({nut.sodium_mg:.0f}mg) exceeds the ceiling "
                f"({goals.sodium_max_mg:.0f}mg)."
            )
            assessment["suggestions"].append(
                "Reduce processed/fried foods and added salt to protect blood pressure."
            )
            assessment["goal_status"]["sodium"] = "High"
        else:
            assessment["goal_status"]["sodium"] = "Acceptable"

        # Calories vs target.
        if goals.calories_kcal > 0:
            cal_pct = (nut.calories_kcal / goals.calories_kcal) * 100
            assessment["goal_status"]["calories"] = (
                f"{nut.calories_kcal:.0f}/{goals.calories_kcal:.0f} kcal "
                f"({cal_pct:.0f}% of target)"
            )

        # Glucose interpretation.
        assessment["glucose"] = GlucoseMonitor.interpret(glucose)

        # Meal diversity note.
        meal_types = set(m.meal_type for m in daily_intake.meals)
        assessment["observations"].append(
            f"Logged {len(daily_intake.meals)} meal(s) across "
            f"{len(meal_types)} meal type(s): {', '.join(meal_types) or 'none'}."
        )

        return assessment

    @staticmethod
    def get_assessment_summary(
        daily_intake: DailyIntake,
        goals: NutrientGoals,
        glucose: Optional[GlucoseReading] = None,
    ) -> str:
        """Readable text summary of the assessment."""
        assessment = NutritionAssessment.assess_daily_intake(daily_intake, goals, glucose)

        summary = "==== DIABETES NUTRITION ASSESSMENT ====\n\n"
        if assessment["glucose"]:
            summary += f"Glucose: {assessment['glucose']}\n\n"

        summary += "Observations:\n"
        for obs in assessment["observations"]:
            summary += f"  - {obs}\n"

        if assessment["suggestions"]:
            summary += "\nSuggestions:\n"
            for sugg in assessment["suggestions"]:
                summary += f"  - {sugg}\n"

        return summary
