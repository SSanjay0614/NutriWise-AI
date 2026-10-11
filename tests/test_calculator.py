"""
Tests for nutrition calculator.
"""
import pytest
from nutrition.calculator import NutritionCalculator
from models.schemas import Nutrition


class TestNutritionCalculator:
    """Test nutrition calculation."""

    @pytest.fixture
    def calculator(self):
        """Initialize calculator."""
        return NutritionCalculator()

    def test_basic_calculation(self, calculator):
        """Test basic nutrition calculation."""
        # Create a mock food record
        food_record = {
            'energy_kcal_100g': 356.1,
            'protein_g_100g': 14.59,
            'carbohydrate_g_100g': 59.98,
            'fat_g_100g': 5.74,
            'fiber_g_100g': 7.02,
            'sugar_g_100g': 0.88,
            'sodium_mg_100g': 2.7,
            'calcium_mg_100g': 181.0,
            'iron_mg_100g': 9.33,
            'potassium_mg_100g': 433.0,
        }

        nutrition = calculator.calculate_nutrition(food_record, 100)

        # For 100g, values should match per-100g values
        assert nutrition.calories_kcal == pytest.approx(356.1, rel=0.01)
        assert nutrition.protein_g == pytest.approx(14.59, rel=0.01)
        assert nutrition.carbohydrate_g == pytest.approx(59.98, rel=0.01)
        assert nutrition.fat_g == pytest.approx(5.74, rel=0.01)

    def test_fifty_gram_calculation(self, calculator):
        """Test calculation for 50g."""
        food_record = {
            'energy_kcal_100g': 100.0,
            'protein_g_100g': 10.0,
            'carbohydrate_g_100g': 50.0,
            'fat_g_100g': 5.0,
            'fiber_g_100g': 2.0,
            'sugar_g_100g': 1.0,
            'sodium_mg_100g': 100.0,
            'calcium_mg_100g': 200.0,
            'iron_mg_100g': 2.0,
            'potassium_mg_100g': 300.0,
        }

        nutrition = calculator.calculate_nutrition(food_record, 50)

        # For 50g, values should be half
        assert nutrition.calories_kcal == pytest.approx(50.0, rel=0.01)
        assert nutrition.protein_g == pytest.approx(5.0, rel=0.01)
        assert nutrition.carbohydrate_g == pytest.approx(25.0, rel=0.01)
        assert nutrition.fat_g == pytest.approx(2.5, rel=0.01)

    def test_add_nutrition(self, calculator):
        """Test adding nutrition records."""
        nut1 = Nutrition(
            calories_kcal=100,
            protein_g=10,
            carbohydrate_g=50,
            fat_g=5,
        )
        nut2 = Nutrition(
            calories_kcal=150,
            protein_g=15,
            carbohydrate_g=30,
            fat_g=8,
        )

        result = calculator.add_nutrition(nut1, nut2)

        assert result.calories_kcal == pytest.approx(250, rel=0.01)
        assert result.protein_g == pytest.approx(25, rel=0.01)
        assert result.carbohydrate_g == pytest.approx(80, rel=0.01)
        assert result.fat_g == pytest.approx(13, rel=0.01)

    def test_macronutrient_percentages(self, calculator):
        """Test macronutrient percentage calculation."""
        nutrition = Nutrition(
            protein_g=20,      # 20 * 4 = 80 kcal
            carbohydrate_g=50, # 50 * 4 = 200 kcal
            fat_g=10,          # 10 * 9 = 90 kcal
        )

        result = calculator.get_macronutrient_percentages(nutrition)

        # Total = 80 + 200 + 90 = 370
        assert result['protein_pct'] == pytest.approx(21.6, rel=1)  # 80/370 * 100
        assert result['carbs_pct'] == pytest.approx(54.1, rel=1)    # 200/370 * 100
        assert result['fat_pct'] == pytest.approx(24.3, rel=1)      # 90/370 * 100

    def test_bajra_example(self, calculator):
        """Test calculation with Bajra from specification."""
        # From spec: Bajra has protein=10.96 g/100g, fiber=11.49 g/100g
        bajra_record = {
            'energy_kcal_100g': 347.99,
            'protein_g_100g': 10.96,
            'carbohydrate_g_100g': 61.78,
            'fat_g_100g': 5.43,
            'fiber_g_100g': 11.49,
            'sugar_g_100g': 0.81,
            'sodium_mg_100g': 4.11,
            'calcium_mg_100g': 27.35,
            'iron_mg_100g': 6.42,
            'potassium_mg_100g': 365.0,
        }

        # For 100g
        nutrition = calculator.calculate_nutrition(bajra_record, 100)
        assert nutrition.protein_g == pytest.approx(10.96, rel=0.01)
    def test_nutriwise_serving_size_calculation(self, calculator):
        """Test calculation with standard NutriWise serving size."""
        # Idli: serving_size_g = 40, calories_kcal = 58, protein_g = 1.9
        idli_record = {
            'food_name': 'Idli',
            'serving_size_g': 40.0,
            'calories_kcal': 58.0,
            'protein_g': 1.9,
            'carbohydrate_g': 12.0,
            'fat_g': 0.2,
            'fiber_g': 0.8,
            'sodium_mg': 120.0,
            'calcium_mg': 10.0,
            'iron_mg': 0.5,
            'potassium_mg': 35.0,
        }

        # 3 idlis = 120g (scale = 3.0)
        nutrition_3 = calculator.calculate_nutrition(idli_record, 120.0)
        assert nutrition_3.calories_kcal == pytest.approx(174.0, rel=0.01)
        assert nutrition_3.protein_g == pytest.approx(5.7, rel=0.01)
        assert nutrition_3.carbohydrate_g == pytest.approx(36.0, rel=0.01)

        # 200g Chicken Fried Rice (serving_size_g = 300, calories = 520)
        cfr_record = {
            'food_name': 'Chicken Fried Rice',
            'serving_size_g': 300.0,
            'calories_kcal': 520.0,
            'protein_g': 22.0,
            'carbohydrate_g': 65.0,
            'fat_g': 18.0,
        }
        nutrition_cfr = calculator.calculate_nutrition(cfr_record, 200.0)
        assert nutrition_cfr.calories_kcal == pytest.approx(520.0 * (200.0 / 300.0), rel=0.01)
        assert nutrition_cfr.protein_g == pytest.approx(22.0 * (200.0 / 300.0), rel=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

