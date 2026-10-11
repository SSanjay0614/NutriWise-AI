"""
Nutrition calculation engine.
All calculations are deterministic Python operations on the food database.
"""
from typing import Optional
import pandas as pd
from models.schemas import FoodItem, Nutrition


class NutritionCalculator:
    """
    Calculates nutrition values based on NutriWise dataset records.
    Scales proportionally based on serving_size_g.
    """

    @staticmethod
    def calculate_nutrition(food_record: dict, weight_g: float) -> Nutrition:
        """
        Calculate nutrition for a given weight of food.
        
        Formula:
            scale = weight_g / serving_size_g
            nutrition = nutrition_per_serving * scale
        
        Args:
            food_record: Dictionary from FoodDatabase lookup or LLM estimate
            weight_g: Weight in grams
            
        Returns:
            Nutrition object with calculated values
        """
        serving_size = float(food_record.get('serving_size_g', 100.0) or 100.0)
        if serving_size <= 0:
            serving_size = 100.0

        scale = weight_g / serving_size

        def _get_val(key_std, key_legacy=None):
            val = food_record.get(key_std)
            if val is not None and pd.notna(val):
                return float(val)
            if key_legacy:
                val_leg = food_record.get(key_legacy)
                if val_leg is not None and pd.notna(val_leg):
                    return float(val_leg)
            return 0.0
        
        return Nutrition(
            calories_kcal=_get_val('calories_kcal', 'energy_kcal_100g') * scale,
            protein_g=_get_val('protein_g', 'protein_g_100g') * scale,
            carbohydrate_g=_get_val('carbohydrate_g', 'carbohydrate_g_100g') * scale,
            fat_g=_get_val('fat_g', 'fat_g_100g') * scale,
            fiber_g=_get_val('fiber_g', 'fiber_g_100g') * scale,
            sugar_g=_get_val('sugar_g', 'sugar_g_100g') * scale,
            sodium_mg=_get_val('sodium_mg', 'sodium_mg_100g') * scale,
            calcium_mg=_get_val('calcium_mg', 'calcium_mg_100g') * scale,
            iron_mg=_get_val('iron_mg', 'iron_mg_100g') * scale,
            potassium_mg=_get_val('potassium_mg', 'potassium_mg_100g') * scale,
            vitamin_a_mcg=_get_val('vitamin_a_mcg') * scale,
            vitamin_c_mg=_get_val('vitamin_c_mg') * scale,
            vitamin_d_mcg=_get_val('vitamin_d_mcg') * scale,
            vitamin_b12_mcg=_get_val('vitamin_b12_mcg') * scale,
            folate_mcg=_get_val('folate_mcg') * scale,
            magnesium_mg=_get_val('magnesium_mg') * scale,
            zinc_mg=_get_val('zinc_mg') * scale,
        )

    @staticmethod
    def add_nutrition(*nutrition_list) -> Nutrition:
        """
        Add multiple nutrition records.
        
        Args:
            *nutrition_list: Variable number of Nutrition objects
            
        Returns:
            Combined Nutrition object
        """
        result = Nutrition()
        for nutrition in nutrition_list:
            result = result + nutrition
        return result

    @staticmethod
    def get_macronutrient_percentages(nutrition: Nutrition) -> dict:
        """
        Calculate macronutrient percentage distribution.
        
        Args:
            nutrition: Nutrition object
            
        Returns:
            Dictionary with protein_pct, carbs_pct, fat_pct
        """
        # Calories per gram
        protein_cal = nutrition.protein_g * 4
        carbs_cal = nutrition.carbohydrate_g * 4
        fat_cal = nutrition.fat_g * 9
        
        total_cal = protein_cal + carbs_cal + fat_cal
        
        if total_cal == 0:
            return {
                "protein_pct": 0.0,
                "carbs_pct": 0.0,
                "fat_pct": 0.0,
            }
        
        return {
            "protein_pct": round((protein_cal / total_cal) * 100, 1),
            "carbs_pct": round((carbs_cal / total_cal) * 100, 1),
            "fat_pct": round((fat_cal / total_cal) * 100, 1),
        }
