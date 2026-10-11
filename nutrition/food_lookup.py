"""
Food database lookup using NutriWise food dataset (data/nutriwise_foods.csv).
Provides exact, case-insensitive, normalized, and fuzzy matching for prepared foods and ingredients.
"""
import os
from typing import Optional, List
import pandas as pd
from models.schemas import FoodItem
from nutrition.diabetes_score import DiabetesScorer


class FoodDatabase:
    """
    Manages the NutriWise food database.
    Loads nutriwise_foods.csv and provides robust lookup methods.
    """

    def __init__(
        self,
        csv_path: str = "data/nutriwise_foods.csv",
        aliases_path: str = "data/food_aliases.csv"
    ):
        """Initialize the food database."""
        self.csv_path = csv_path
        self.aliases_path = aliases_path
        self.df: Optional[pd.DataFrame] = None
        self.aliases: dict = {}
        self.load_database()
        self.load_aliases()

    def load_database(self) -> None:
        """Load the nutriwise_foods.csv file into memory."""
        # The NutriWise dataset is the only supported primary database.
        target_path = self.csv_path
        if not os.path.exists(target_path):
            if os.path.exists("nutriwise_foods.csv"):
                target_path = "nutriwise_foods.csv"
            else:
                raise FileNotFoundError(f"NutriWise food database not found at {self.csv_path}")
        
        self.df = pd.read_csv(target_path)
        print(f"[OK] Loaded {len(self.df)} foods from {target_path}")

    def load_aliases(self) -> None:
        """Load optional food aliases from CSV."""
        path_to_try = self.aliases_path
        if not os.path.exists(path_to_try) and os.path.exists("food_aliases.csv"):
            path_to_try = "food_aliases.csv"
            
        if os.path.exists(path_to_try):
            try:
                aliases_df = pd.read_csv(path_to_try)
                alias_col = "alias" if "alias" in aliases_df.columns else "user_term"
                canonical_col = "canonical_food_name" if "canonical_food_name" in aliases_df.columns else "canonical_name"
                canonical_names = {
                    self._normalize_name(name): str(name).strip()
                    for name in self.df["food_name"].dropna()
                }
                for _, row in aliases_df.iterrows():
                    alias_key = str(row[alias_col]).strip().lower()
                    canonical_val = str(row[canonical_col]).strip()
                    canonical_key = self._normalize_name(canonical_val)
                    # Ignore stale IFCT aliases that do not name a NutriWise record.
                    if canonical_key in canonical_names:
                        self.aliases[self._normalize_name(alias_key)] = canonical_names[canonical_key]
            except Exception as e:
                print(f"⚠ Warning loading aliases from {path_to_try}: {e}")

    def lookup_food(self, food_name: str) -> Optional[dict]:
        """
        Look up a food by name in the NutriWise database.
        Supports case-insensitive, normalized, alias, and substring matching.
        Never substitutes unrelated foods.
        
        Args:
            food_name: The name of the food to look up
            
        Returns:
            Dictionary of food data if found, None otherwise
        """
        if self.df is None or self.df.empty:
            raise RuntimeError("Database not loaded")
        
        clean = self._normalize_name(food_name)
        if not clean:
            return None

        # Build list of potential candidates to search
        candidates = []
        
        # 1. Alias expansion
        if clean in self.aliases:
            candidates.append(self._normalize_name(self.aliases[clean]))
        
        candidates.append(clean)

        # 2. Singularize simple English plurals (e.g., idlis -> idli, samosas -> samosa, eggs -> egg)
        if clean.endswith("s") and len(clean) > 3:
            singular = clean[:-1]
            if singular in self.aliases:
                candidates.append(self._normalize_name(self.aliases[singular]))
            candidates.append(singular)
        if clean.endswith("es") and len(clean) > 4:
            singular_es = clean[:-2]
            candidates.append(singular_es)

        candidates = list(dict.fromkeys(candidates))
        normalized_rows = [
            (self._normalize_name(row["food_name"]), row.to_dict())
            for _, row in self.df.iterrows()
        ]

        # Stage 1: Exact case-insensitive match.
        for candidate in candidates:
            for row_name, row_dict in normalized_rows:
                if row_name == candidate:
                    return row_dict

        # Stage 2: Safe phrase matching. One-word partials ("egg", "rice") are
        # ambiguous, and multiple candidate dishes are never guessed.
        for candidate in candidates:
            if len(candidate.split()) < 2:
                continue
            matches = [
                row_dict for row_name, row_dict in normalized_rows
                if self._is_whole_phrase(candidate, row_name)
                or self._is_whole_phrase(row_name, candidate)
            ]
            if len(matches) == 1:
                return matches[0]

        return None

    @staticmethod
    def _normalize_name(value: str) -> str:
        """Normalize names for exact and whole-phrase comparisons."""
        normalized = "".join(character if character.isalnum() else " " for character in str(value).lower())
        return " ".join(normalized.split())

    @staticmethod
    def _is_whole_phrase(phrase: str, text: str) -> bool:
        """Return whether phrase occurs as a consecutive sequence of whole words."""
        phrase_words = phrase.split()
        text_words = text.split()
        width = len(phrase_words)
        return any(text_words[index:index + width] == phrase_words for index in range(len(text_words) - width + 1))

    def lookup_foods(self, food_name: str, limit: int = 5) -> List[dict]:
        """
        Look up foods with fuzzy matching, returning multiple candidate records.
        """
        if self.df is None:
            raise RuntimeError("Database not loaded")
        
        clean = self._normalize_name(food_name)
        matches = []

        for _, row in self.df.iterrows():
            row_name = self._normalize_name(row['food_name'])
            if row_name == clean:
                matches.append(row.to_dict())
            elif len(clean.split()) >= 2 and (
                self._is_whole_phrase(clean, row_name) or self._is_whole_phrase(row_name, clean)
            ):
                if row.to_dict() not in matches:
                    matches.append(row.to_dict())

        return matches[:limit]

    def get_all_foods(self) -> List[str]:
        """Get all food names in the database."""
        if self.df is None:
            raise RuntimeError("Database not loaded")
        return self.df['food_name'].tolist()

    def get_rated_foods(
        self,
        ratings: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        """
        Return dataset records annotated with their diabetes rating + score,
        filtered by rating ("good"/"moderate"/"limit") and/or category.
        Sorted best-first (highest diabetes score, then lowest GI).
        """
        if self.df is None:
            raise RuntimeError("Database not loaded")

        results = []
        for _, row in self.df.iterrows():
            record = row.to_dict()
            rating, score = DiabetesScorer.score_record(record)
            record["diabetes_rating"] = rating
            record["diabetes_score"] = score
            if ratings and rating not in ratings:
                continue
            if categories and str(record.get("category", "")) not in categories:
                continue
            results.append(record)

        def _gi(rec):
            try:
                return float(rec.get("glycemic_index") or 999)
            except (TypeError, ValueError):
                return 999

        results.sort(key=lambda r: (-r["diabetes_score"], _gi(r)))
        return results[:limit] if limit else results

    def resolve_weight(
        self,
        food_dict: dict,
        quantity: float,
        quantity_unit: str = "g"
    ) -> float:
        """
        Resolve the total weight in grams based on quantity, unit, and dataset serving size.
        
        Args:
            food_dict: Food record from database
            quantity: Numeric quantity
            quantity_unit: Unit string (g, piece, plate, bowl, cup, etc.)
            
        Returns:
            Weight in grams
        """
        serving_size_g = float(food_dict.get('serving_size_g', 100.0) or 100.0)
        unit_clean = quantity_unit.strip().lower()

        # Direct weight units
        if unit_clean in ["g", "grams", "gram", "ml"]:
            return float(quantity)
        elif unit_clean in ["kg", "kilogram", "kilograms"]:
            return float(quantity) * 1000.0
        
        # Serving/count units use the dataset standard serving size
        # e.g., 3 idlis -> 3 * 40g = 120g
        return float(quantity) * serving_size_g

    def food_to_item(
        self,
        food_dict: dict,
        quantity: float,
        quantity_unit: str = "g",
        source: str = "dataset"
    ) -> FoodItem:
        """
        Convert a food record to a Pydantic FoodItem with resolved gram weight.
        
        Args:
            food_dict: Food record from database
            quantity: The quantity value
            quantity_unit: The unit (g, piece, cup, bowl, etc.)
            source: Source identifier ("dataset" or "llm_fallback")
            
        Returns:
            FoodItem object
        """
        weight_g = self.resolve_weight(food_dict, quantity, quantity_unit)
        category = str(food_dict.get('category', food_dict.get('food_group', 'General')))

        # Glycemic index + diabetes suitability (per standard serving).
        gi_raw = food_dict.get('glycemic_index')
        try:
            glycemic_index = int(float(gi_raw)) if gi_raw is not None and pd.notna(gi_raw) else None
        except (TypeError, ValueError):
            glycemic_index = None
        gi_category = food_dict.get('gi_category')
        if gi_category is not None and (isinstance(gi_category, float) and pd.isna(gi_category)):
            gi_category = None
        diabetes_rating, _ = DiabetesScorer.score_record(food_dict)

        return FoodItem(
            food_id=str(food_dict.get('food_id', 'UNKNOWN')),
            food_name=str(food_dict.get('food_name', 'Unknown Food')),
            scientific_name=str(food_dict.get('scientific_name', '')),
            food_group=category,
            quantity=quantity,
            quantity_unit=quantity_unit,
            weight_g=weight_g,
            source=source,
            glycemic_index=glycemic_index,
            gi_category=str(gi_category) if gi_category is not None else None,
            diabetes_rating=diabetes_rating,
        )

