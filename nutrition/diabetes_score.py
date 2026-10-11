"""
Diabetes-suitability scoring for foods.

Combines Glycemic Index with per-serving sugar, fiber, and carbohydrate load
into a simple rating: "good", "moderate", or "limit". Used to rank foods for
recommendations and the daily meal planner.

This is an educational heuristic, not medical guidance.
"""
from typing import Optional, Tuple


class DiabetesScorer:
    """Rates how suitable a food is for a diabetes-friendly diet."""

    @staticmethod
    def _gi_category(gi: Optional[float]) -> Optional[str]:
        if gi is None:
            return None
        if gi <= 55:
            return "low"
        if gi <= 69:
            return "medium"
        return "high"

    @classmethod
    def score(
        cls,
        glycemic_index: Optional[float],
        gi_category: Optional[str],
        sugar_g: float,
        fiber_g: float,
        carbohydrate_g: float,
    ) -> Tuple[str, int]:
        """
        Return (rating, score) where rating is "good" | "moderate" | "limit".
        Inputs are per standard serving.
        """
        points = 0

        category = (gi_category or cls._gi_category(glycemic_index) or "medium").lower()
        if category == "low":
            points += 2
        elif category == "high":
            points -= 2

        # Sugar load (per serving)
        if sugar_g < 5:
            points += 1
        elif sugar_g > 15:
            points -= 2

        # Fiber (per serving) — protective
        if fiber_g >= 5:
            points += 2
        elif fiber_g >= 3:
            points += 1

        # Carbohydrate load (per serving)
        if carbohydrate_g > 45:
            points -= 2
        elif carbohydrate_g > 30:
            points -= 1

        if points >= 2:
            return "good", points
        if points >= 0:
            return "moderate", points
        return "limit", points

    @classmethod
    def score_record(cls, food_record: dict) -> Tuple[str, int]:
        """Score a raw dataset/estimate record dict (per its standard serving)."""
        def _num(key: str) -> float:
            try:
                val = food_record.get(key)
                return float(val) if val is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        gi = food_record.get("glycemic_index")
        try:
            gi = float(gi) if gi is not None else None
        except (TypeError, ValueError):
            gi = None

        return cls.score(
            glycemic_index=gi,
            gi_category=food_record.get("gi_category"),
            sugar_g=_num("sugar_g"),
            fiber_g=_num("fiber_g"),
            carbohydrate_g=_num("carbohydrate_g"),
        )
