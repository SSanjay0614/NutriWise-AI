"""
Unit tests for the diabetes-specific modules:
goals, glucose, diabetes scoring, food GI annotation, and the meal planner.
No network dependency.
"""
from datetime import date
import pytest

from models.schemas import UserProfile, GlucoseReading
from nutrition.goals import GoalCalculator
from nutrition.glucose import GlucoseMonitor
from nutrition.diabetes_score import DiabetesScorer
from nutrition.food_lookup import FoodDatabase
from nutrition.meal_planner import DiabetesMealPlanner


@pytest.fixture(scope="module")
def food_db():
    return FoodDatabase(csv_path="data/nutriwise_foods.csv")


def make_profile(**kw):
    base = dict(
        name="T", age=50, gender="male", weight_kg=80, height_cm=175,
        activity_level="sedentary", diabetes_type="type2",
    )
    base.update(kw)
    return UserProfile(**base)


class TestGoalCalculator:
    def test_bmr_mifflin_st_jeor_male(self):
        p = make_profile(age=50, weight_kg=80, height_cm=175, gender="male")
        # 10*80 + 6.25*175 - 5*50 + 5 = 1648.75
        assert GoalCalculator.calculate_bmr(p) == pytest.approx(1648.75)

    def test_bmr_female_lower_than_male(self):
        male = make_profile(gender="male")
        female = make_profile(gender="female")
        assert GoalCalculator.calculate_bmr(female) < GoalCalculator.calculate_bmr(male)

    def test_goals_have_sensible_macros(self):
        p = make_profile(weight_kg=70, height_cm=175, activity_level="moderate")
        g = GoalCalculator.calculate_goals(p)
        assert g.calories_kcal > 0
        assert g.carbohydrate_g > 0
        assert g.fiber_min_g >= 25
        assert g.sugar_max_g == 25
        # protein at least ~1g/kg body weight
        assert g.protein_g >= 70

    def test_hypertension_tightens_sodium(self):
        g = GoalCalculator.calculate_goals(make_profile(conditions=["hypertension"]))
        assert g.sodium_max_mg == 1500.0

    def test_overweight_type2_trims_calories(self):
        overweight = make_profile(weight_kg=100, height_cm=170)  # BMI ~34.6
        lean = make_profile(weight_kg=60, height_cm=175)         # BMI ~19.6
        g_over = GoalCalculator.calculate_goals(overweight)
        # TDEE for the same-ish activity should be trimmed by the BMI rule
        assert any("weight management" in n for n in g_over.notes)
        assert "weight management" not in " ".join(
            GoalCalculator.calculate_goals(lean).notes
        )


class TestGlucoseMonitor:
    def test_fasting_categories(self):
        d = date.today().isoformat()
        assert GlucoseMonitor.categorize(
            GlucoseReading(value_mg_dl=90, reading_type="fasting", date=d)) == "normal"
        assert GlucoseMonitor.categorize(
            GlucoseReading(value_mg_dl=110, reading_type="fasting", date=d)) == "elevated"
        assert GlucoseMonitor.categorize(
            GlucoseReading(value_mg_dl=140, reading_type="fasting", date=d)) == "high"

    def test_post_meal_categories(self):
        d = date.today().isoformat()
        assert GlucoseMonitor.categorize(
            GlucoseReading(value_mg_dl=130, reading_type="post_meal", date=d)) == "normal"
        assert GlucoseMonitor.categorize(
            GlucoseReading(value_mg_dl=200, reading_type="post_meal", date=d)) == "high"

    def test_carb_adjustment(self):
        d = date.today().isoformat()
        assert GlucoseMonitor.carb_adjustment(None) == 1.0
        high = GlucoseMonitor.annotate(
            GlucoseReading(value_mg_dl=150, reading_type="fasting", date=d))
        assert GlucoseMonitor.carb_adjustment(high) == 0.8


class TestDiabetesScorer:
    def test_low_gi_high_fiber_is_good(self):
        rating, score = DiabetesScorer.score(
            glycemic_index=30, gi_category="low", sugar_g=2, fiber_g=6, carbohydrate_g=15)
        assert rating == "good"
        assert score >= 2

    def test_high_gi_sugary_is_limit(self):
        rating, _ = DiabetesScorer.score(
            glycemic_index=75, gi_category="high", sugar_g=30, fiber_g=0, carbohydrate_g=50)
        assert rating == "limit"

    def test_score_record_reads_dataset_fields(self, food_db):
        rice = food_db.lookup_food("Steamed White Rice")
        rating, _ = DiabetesScorer.score_record(rice)
        assert rating in ("limit", "moderate")


class TestFoodItemAnnotation:
    def test_lookup_item_carries_gi_and_rating(self, food_db):
        rec = food_db.lookup_food("Dal Tadka")
        item = food_db.food_to_item(rec, 1, "bowl")
        assert item.glycemic_index is not None
        assert item.gi_category in ("low", "medium", "high")
        assert item.diabetes_rating in ("good", "moderate", "limit")

    def test_get_rated_foods_filters_good(self, food_db):
        goods = food_db.get_rated_foods(ratings=["good"], limit=10)
        assert len(goods) > 0
        assert all(r["diabetes_rating"] == "good" for r in goods)


class TestMealPlanner:
    def test_generates_four_meals(self, food_db):
        goals = GoalCalculator.calculate_goals(make_profile())
        plan = DiabetesMealPlanner(food_db).generate(goals)
        assert [m.meal_type for m in plan.meals] == ["breakfast", "lunch", "dinner", "snack"]
        assert plan.total_nutrition.calories_kcal > 0

    def test_high_glucose_reduces_plan_carbs(self, food_db):
        goals = GoalCalculator.calculate_goals(make_profile())
        d = date.today().isoformat()
        high = GlucoseMonitor.annotate(
            GlucoseReading(value_mg_dl=160, reading_type="fasting", date=d))
        normal_plan = DiabetesMealPlanner(food_db).generate(goals)
        high_plan = DiabetesMealPlanner(food_db).generate(goals, high)
        assert any("reduced" in n for n in high_plan.notes)
        assert high_plan.total_nutrition.carbohydrate_g <= \
            normal_plan.total_nutrition.carbohydrate_g + 1
