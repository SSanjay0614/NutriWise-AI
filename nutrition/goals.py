"""
Personalized nutrient goal calculator for diabetes management.

Derives daily nutrient targets from a UserProfile using:
  - Mifflin-St Jeor BMR -> TDEE (calorie target)
  - A diabetes-oriented macronutrient split (controlled carbs, higher fiber)
  - Condition-aware ceilings (sodium, sugar)

All values are educational estimates, not medical prescriptions.
"""
from models.schemas import UserProfile, NutrientGoals


class GoalCalculator:
    """Computes NutrientGoals from a UserProfile."""

    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }

    # Share of total calories from each macronutrient (diabetes-oriented).
    CARB_PCT = 0.45
    PROTEIN_PCT = 0.20
    FAT_PCT = 0.35

    # Reference daily micronutrient targets (minimums / adequate intakes).
    MICRO_TARGETS = {
        "calcium_mg": 1000, "iron_mg": 12, "potassium_mg": 3500,
        "magnesium_mg": 400, "zinc_mg": 11, "vitamin_a_mcg": 800,
        "vitamin_c_mg": 75, "vitamin_d_mcg": 15, "vitamin_b12_mcg": 2.4,
        "folate_mcg": 400,
    }

    @staticmethod
    def calculate_bmr(profile: UserProfile) -> float:
        """Basal Metabolic Rate via the Mifflin-St Jeor equation (kcal/day)."""
        base = (10 * profile.weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age)
        if profile.gender == "male":
            return base + 5
        return base - 161

    @classmethod
    def calculate_tdee(cls, profile: UserProfile) -> float:
        """Total Daily Energy Expenditure (kcal/day)."""
        multiplier = cls.ACTIVITY_MULTIPLIERS.get(profile.activity_level, 1.2)
        return cls.calculate_bmr(profile) * multiplier

    @classmethod
    def calculate_goals(cls, profile: UserProfile, activity_kcal: float = 0.0) -> NutrientGoals:
        """
        Derive personalized daily nutrient goals for the user.

        `activity_kcal` is extra energy burned by today's logged exercise; it
        raises the calorie target and (proportionally) the carb budget.
        """
        notes = []
        tdee = cls.calculate_tdee(profile)
        calories = tdee

        # Gentle calorie reduction for overweight Type 2 / prediabetes users
        # to support gradual weight management (a key lever for Type 2 control).
        if profile.diabetes_type in ("type2", "prediabetes") and profile.bmi >= 25:
            calories = tdee * 0.90
            notes.append(
                f"Calories trimmed ~10% below maintenance for gradual weight management "
                f"(BMI {profile.bmi})."
            )

        activity_bonus = max(0.0, float(activity_kcal))
        if activity_bonus > 0:
            calories += activity_bonus
            notes.append(
                f"+{activity_bonus:.0f} kcal added for today's logged activity."
            )

        # Macronutrient targets from calorie split.
        carbohydrate_g = round((calories * cls.CARB_PCT) / 4.0, 0)
        protein_from_split = (calories * cls.PROTEIN_PCT) / 4.0
        # Ensure at least ~1.0 g protein per kg body weight.
        protein_g = round(max(protein_from_split, profile.weight_kg * 1.0), 0)
        fat_g = round((calories * cls.FAT_PCT) / 9.0, 0)

        # Fiber: ~14 g per 1000 kcal, with a sensible floor.
        fiber_min_g = round(max(25.0, (calories / 1000.0) * 14.0), 0)

        # Free/added sugar ceiling (stricter than the general population).
        sugar_max_g = 25.0

        # Sodium ceiling, tightened for hypertension / kidney concerns.
        sodium_max_mg = 2300.0
        conditions = [c.lower() for c in profile.conditions]
        if any(c in conditions for c in ("hypertension", "high bp", "kidney", "ckd")):
            sodium_max_mg = 1500.0
            notes.append("Sodium ceiling tightened to 1500 mg (hypertension/kidney).")

        if profile.diabetes_type == "type1":
            notes.append(
                "Type 1: keep carbohydrates consistent per meal for easier insulin "
                "matching. This app provides diet info only, never insulin dosing."
            )
        if profile.diabetes_type == "gestational":
            notes.append(
                "Gestational: spread carbohydrates across smaller, frequent meals; "
                "please follow your obstetric team's guidance."
            )
        if profile.on_insulin:
            notes.append(
                "On insulin: consistent meal timing and carb amounts help avoid lows/highs."
            )

        return NutrientGoals(
            calories_kcal=round(calories, 0),
            carbohydrate_g=carbohydrate_g,
            sugar_max_g=sugar_max_g,
            fiber_min_g=fiber_min_g,
            protein_g=protein_g,
            fat_g=fat_g,
            sodium_max_mg=sodium_max_mg,
            micro_targets=dict(cls.MICRO_TARGETS),
            activity_bonus_kcal=round(activity_bonus, 0),
            notes=notes,
        )
