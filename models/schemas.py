"""
Pydantic models for NutriWise data structures.
"""
from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class FoodItem(BaseModel):
    """Represents a food identified from the database or estimated via LLM fallback."""
    food_id: str
    food_name: str
    scientific_name: Optional[str] = None
    food_group: Optional[str] = None
    quantity: float  # Raw quantity value
    quantity_unit: str  # unit like "g", "piece", "cup", "bowl"
    weight_g: float  # Converted to grams
    source: Literal["dataset", "llm_fallback"] = "dataset"
    glycemic_index: Optional[int] = None  # Approximate GI (0-100)
    gi_category: Optional[str] = None  # "low" | "medium" | "high"
    diabetes_rating: Optional[str] = None  # "good" | "moderate" | "limit"


class LLMFoodNutritionEstimate(BaseModel):
    """Represents structured nutrition estimation returned by the LLM fallback."""
    food_name: str
    quantity: float = 1.0
    unit: str = "serving"
    serving_size_g: float = 100.0
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbohydrate_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0
    calcium_mg: float = 0.0
    iron_mg: float = 0.0
    potassium_mg: float = 0.0
    glycemic_index: Optional[int] = None  # Approximate GI estimated by the LLM
    source: Literal["LLM estimate"] = "LLM estimate"


class Nutrition(BaseModel):
    """Represents calculated nutrition values."""
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbohydrate_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0
    calcium_mg: float = 0.0
    iron_mg: float = 0.0
    potassium_mg: float = 0.0
    # Micronutrients (approximate estimates from the dataset)
    vitamin_a_mcg: float = 0.0
    vitamin_c_mg: float = 0.0
    vitamin_d_mcg: float = 0.0
    vitamin_b12_mcg: float = 0.0
    folate_mcg: float = 0.0
    magnesium_mg: float = 0.0
    zinc_mg: float = 0.0

    def __add__(self, other: "Nutrition") -> "Nutrition":
        """Add two nutrition records."""
        return Nutrition(
            calories_kcal=self.calories_kcal + other.calories_kcal,
            protein_g=self.protein_g + other.protein_g,
            carbohydrate_g=self.carbohydrate_g + other.carbohydrate_g,
            fat_g=self.fat_g + other.fat_g,
            fiber_g=self.fiber_g + other.fiber_g,
            sugar_g=self.sugar_g + other.sugar_g,
            sodium_mg=self.sodium_mg + other.sodium_mg,
            calcium_mg=self.calcium_mg + other.calcium_mg,
            iron_mg=self.iron_mg + other.iron_mg,
            potassium_mg=self.potassium_mg + other.potassium_mg,
            vitamin_a_mcg=self.vitamin_a_mcg + other.vitamin_a_mcg,
            vitamin_c_mg=self.vitamin_c_mg + other.vitamin_c_mg,
            vitamin_d_mcg=self.vitamin_d_mcg + other.vitamin_d_mcg,
            vitamin_b12_mcg=self.vitamin_b12_mcg + other.vitamin_b12_mcg,
            folate_mcg=self.folate_mcg + other.folate_mcg,
            magnesium_mg=self.magnesium_mg + other.magnesium_mg,
            zinc_mg=self.zinc_mg + other.zinc_mg,
        )


class ParsedFood(BaseModel):
    """Represents one food extracted from natural-language input."""
    food_name: str
    quantity: float
    unit: str = "g"  # Default to grams


class ParsedMeal(BaseModel):
    """Represents a meal parsed from natural language."""
    foods: List[ParsedFood]


class MealRecord(BaseModel):
    """Represents a single meal with all its components."""
    meal_type: str  # "breakfast", "lunch", "dinner", "snack"
    foods: List[FoodItem]  # List of foods in this meal
    nutrition: Nutrition  # Total nutrition for this meal
    timestamp: datetime = Field(default_factory=datetime.now)
    eaten_at: Optional[datetime] = None  # when the user actually ate it
    meal_date: Optional[str] = None  # ISO date (user-local) the meal belongs to
    unresolved_foods: List[ParsedFood] = Field(default_factory=list)  # Foods not found in DB


class DailyIntake(BaseModel):
    """Represents a day's nutritional intake."""
    date: str  # ISO format date string
    meals: List[MealRecord] = Field(default_factory=list)
    total_nutrition: Nutrition = Field(default_factory=Nutrition)

    def add_meal(self, meal: MealRecord) -> None:
        """Add a meal and update totals."""
        self.meals.append(meal)
        self.total_nutrition = self.total_nutrition + meal.nutrition


class Recommendation(BaseModel):
    """Represents a nutrition recommendation."""
    message: str
    priority: str  # "high", "medium", "low"
    reason: str
    suggested_foods: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Diabetes-specific models
# ---------------------------------------------------------------------------

DiabetesType = Literal["type1", "type2", "prediabetes", "gestational"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
Gender = Literal["male", "female"]


class UserProfile(BaseModel):
    """
    One-time user profile used to personalize nutrient goals.
    Collected on first run and reused every day (editable later).
    """
    name: str = "User"
    age: int = Field(ge=1, le=120)
    gender: Gender = "male"
    weight_kg: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    activity_level: ActivityLevel = "sedentary"
    diabetes_type: DiabetesType = "type2"
    on_insulin: bool = False
    hba1c: Optional[float] = None  # Optional last HbA1c (%)
    conditions: List[str] = Field(default_factory=list)  # e.g. ["hypertension", "kidney"]

    @property
    def bmi(self) -> float:
        """Body Mass Index (kg/m^2)."""
        height_m = self.height_cm / 100.0
        if height_m <= 0:
            return 0.0
        return round(self.weight_kg / (height_m ** 2), 1)


class NutrientGoals(BaseModel):
    """
    Personalized daily nutrient targets derived from a UserProfile.
    Carbohydrate is a *budget* (upper target); fiber is a *minimum*.
    """
    calories_kcal: float = 0.0
    carbohydrate_g: float = 0.0   # daily carb budget (upper target)
    sugar_max_g: float = 0.0      # free/added sugar ceiling
    fiber_min_g: float = 0.0      # minimum fiber
    protein_g: float = 0.0        # protein target
    fat_g: float = 0.0            # fat target
    sodium_max_mg: float = 2300.0 # sodium ceiling
    # Reference daily targets for micronutrients (minimums unless noted).
    micro_targets: dict = Field(default_factory=dict)
    activity_bonus_kcal: float = 0.0  # extra calories unlocked by today's exercise
    notes: List[str] = Field(default_factory=list)


class GlucoseReading(BaseModel):
    """A single blood-glucose (blood sugar) reading, logged once a day by default."""
    value_mg_dl: float = Field(gt=0)
    reading_type: Literal["fasting", "post_meal"] = "fasting"
    date: str  # ISO date string
    timestamp: datetime = Field(default_factory=datetime.now)
    category: str = "unknown"  # normal | elevated | high (set by GlucoseMonitor)


class DailyPlanMeal(BaseModel):
    """One meal slot within a generated daily meal plan."""
    meal_type: str  # breakfast | lunch | dinner | snack
    foods: List[str] = Field(default_factory=list)
    carb_budget_g: float = 0.0
    time_hint: str = ""  # suggested time window to eat
    nutrition: Nutrition = Field(default_factory=Nutrition)


class Activity(BaseModel):
    """A logged physical activity for a given day."""
    activity_type: str
    duration_min: float = Field(ge=0)
    calories_burned: float = 0.0
    date: str  # ISO date (user-local)
    performed_at: Optional[datetime] = None
    note: str = ""


class DailyPlan(BaseModel):
    """A full-day diabetes-friendly meal plan."""
    date: str
    meals: List[DailyPlanMeal] = Field(default_factory=list)
    total_nutrition: Nutrition = Field(default_factory=Nutrition)
    notes: List[str] = Field(default_factory=list)
