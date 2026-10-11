"""
Tests for NutriWise food database lookup.
"""
import pytest
from nutrition.food_lookup import FoodDatabase


class TestFoodLookup:
    """Test NutriWise food database lookup functionality."""

    @pytest.fixture
    def food_db(self):
        """Initialize food database with NutriWise dataset."""
        return FoodDatabase("data/nutriwise_foods.csv")

    def test_database_loaded(self, food_db):
        """Test database was loaded successfully with ~150 foods."""
        all_foods = food_db.get_all_foods()
        assert len(all_foods) >= 140
        assert "Idli" in all_foods
        assert "Chicken Fried Rice" in all_foods

    def test_exact_match(self, food_db):
        """Test exact match."""
        food = food_db.lookup_food("Idli")
        assert food is not None
        assert food['food_name'] == "Idli"
        assert food['serving_size_g'] == 40

    def test_lowercase_match(self, food_db):
        """Test lowercase lookup."""
        food = food_db.lookup_food("idli")
        assert food is not None
        assert food['food_name'] == "Idli"

    def test_uppercase_match(self, food_db):
        """Test uppercase lookup."""
        food = food_db.lookup_food("IDLI")
        assert food is not None
        assert food['food_name'] == "Idli"

    def test_whitespace_handling(self, food_db):
        """Test handling of extra whitespace."""
        food = food_db.lookup_food("   idli   ")
        assert food is not None
        assert food['food_name'] == "Idli"

    def test_plural_handling(self, food_db):
        """Test simple plural and curated alias matching."""
        food_idlis = food_db.lookup_food("idlis")
        assert food_idlis is not None
        assert food_idlis['food_name'] == "Idli"

        food_samosas = food_db.lookup_food("samosas")
        assert food_samosas is not None
        assert food_samosas['food_name'] == "Samosa"

        food_eggs = food_db.lookup_food("eggs")
        assert food_eggs is not None
        assert food_eggs['food_name'] == "Boiled Egg"

    def test_dish_match(self, food_db):
        """Test prepared dishes."""
        food = food_db.lookup_food("chicken fried rice")
        assert food is not None
        assert food['food_name'] == "Chicken Fried Rice"
        assert food['serving_size_g'] == 300

    def test_no_false_substitution(self, food_db):
        """Test that distinct foods are never substituted for each other."""
        idli = food_db.lookup_food("idli")
        assert idli['food_name'] != "Steamed White Rice"
        assert idli['food_name'] == "Idli"

        dosa = food_db.lookup_food("plain dosa")
        assert dosa['food_name'] != "Steamed White Rice"
        assert "Dosa" in dosa['food_name']

        # Generic terms are ambiguous and must not silently select a dish.
        assert food_db.lookup_food("fried rice") is None
        assert food_db.lookup_food("egg dish") is None

    def test_unambiguous_partial_match(self, food_db):
        """A specific longer phrase may match a single dataset dish."""
        food = food_db.lookup_food("chicken fried rice dish")
        assert food is not None
        assert food["food_name"] == "Chicken Fried Rice"

    def test_nonexistent_food(self, food_db):
        """Test lookup of food genuinely missing from dataset."""
        food = food_db.lookup_food("NonExistentFood12345XYZ")
        assert food is None

    def test_weight_resolution(self, food_db):
        """Test serving size and gram weight resolution."""
        idli = food_db.lookup_food("Idli")
        
        # 3 pieces of idli (40g each) -> 120g
        weight_pieces = food_db.resolve_weight(idli, quantity=3, quantity_unit="piece")
        assert weight_pieces == 120.0

        # 200 grams of idli -> 200g
        weight_grams = food_db.resolve_weight(idli, quantity=200, quantity_unit="g")
        assert weight_grams == 200.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

