# Implementation Plan — Diabetes Diet Assistant Pivot

Repurpose NutriWise from a general college-student nutrition tracker into a
**diabetes diet assistant**. The system takes a user profile and a daily fasting
blood-glucose reading, derives personalized nutrient goals (with a carbohydrate
budget), and drives assessment, recommendations, and a full-day meal plan around
low-GI, carb-controlled eating.

## Decisions (confirmed with user)

> [!IMPORTANT]
> - Daily input is **fasting blood glucose (mg/dL)**, logged once a day (optional post-meal reading supported). Not insulin.
> - Target population: **all diabetes types** (Type 1, Type 2, prediabetes, gestational).
> - Food suitability ranked using a **GI column + sugar/fiber/carb** heuristic.
> - Diet information only — no insulin dosing or medical treatment advice.

## Changes

### 1. Data — GI enrichment
- `[NEW] prepare_diabetes_data.py` adds `glycemic_index` + `gi_category` to `data/nutriwise_foods.csv` (approximate, labeled estimates).

### 2. Schemas (`models/schemas.py`)
- `[NEW]` `UserProfile`, `NutrientGoals`, `GlucoseReading`, `DailyPlan`, `DailyPlanMeal`.
- `[MODIFY]` `FoodItem` + `LLMFoodNutritionEstimate` gain `glycemic_index` (and FoodItem `gi_category`, `diabetes_rating`).

### 3. Goal calculator (`[NEW] nutrition/goals.py`)
- Mifflin-St Jeor BMR → TDEE → calorie target; diabetes macro split; fiber/sugar/sodium rules; condition-aware ceilings.

### 4. Glucose logic (`[NEW] nutrition/glucose.py`)
- Categorize fasting/post-meal readings; derive carb-budget adjustment and guidance text.

### 5. Food scoring (`[NEW] nutrition/diabetes_score.py`)
- Rate foods good/moderate/limit from GI + sugar + fiber + carb load.

### 6. Food lookup (`[MODIFY] nutrition/food_lookup.py`)
- Annotate `FoodItem` with GI/rating; add `get_rated_foods()` for recommender/planner.

### 7. Assessment (`[MODIFY] nutrition/assessment.py`)
- Compare intake against personal goals + today's glucose instead of fixed student thresholds.

### 8. Recommender (`[MODIFY] nutrition/recommender.py`)
- Diabetes-aware priorities; suggests dataset "good" foods; glucose-driven low-GI steer.

### 9. Meal planner (`[NEW] nutrition/meal_planner.py`)
- Generate a full day sized to the (glucose-adjusted) carb budget using low-GI foods.

### 10. Tracker (`[MODIFY] nutrition/tracker.py`)
- Persist `UserProfile` and a daily glucose log alongside meals; expose `get_goals()`.

### 11. LLM client (`llm/gemini_client.py`)
- Add `estimate_food_nutrition()` fallback (JSON mode) now returning an estimated GI.

### 12. Pipeline / CLI / demo
- `[MODIFY] meal_processor.py` — tag fallback foods with GI + rating.
- `[MODIFY] main.py` — diabetes menu (profile, glucose, meals, intake vs goals, assessment, recommendations, plan).
- `[MODIFY] demo.py` — offline diabetes walkthrough.

### 13. Tests & docs
- `[NEW] tests/test_diabetes.py`; `[MODIFY]` tracker tests, `test_integration.py`, `README.md`, `IMPLEMENTATION_REPORT.md`.

## Verification

```powershell
python prepare_diabetes_data.py
python -m pytest -q tests/test_calculator.py tests/test_food_lookup.py tests/test_tracker.py tests/test_llm_fallback.py tests/test_diabetes.py test_integration.py
python demo.py
```
