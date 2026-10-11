"""
Physical-activity calorie estimation (MET-based).

calories_burned = MET * weight_kg * hours

MET values are standard approximations. Used to raise the day's calorie/carb
budget when the user logs exercise. Educational estimate, not a precise figure.
"""
from typing import List

# Common activities and their METs (metabolic equivalents).
MET_TABLE = {
    "walking": 3.5,
    "brisk walking": 4.3,
    "running": 8.0,
    "cycling": 6.0,
    "swimming": 6.0,
    "yoga": 2.5,
    "strength training": 5.0,
    "gym workout": 5.0,
    "sports": 7.0,
    "cricket": 5.0,
    "football": 7.0,
    "dancing": 5.0,
    "housework": 3.0,
    "gardening": 3.8,
    "other": 4.0,
}


class ActivityEstimator:
    """Estimates calories burned for a logged activity."""

    @staticmethod
    def activity_types() -> List[str]:
        return list(MET_TABLE.keys())

    @staticmethod
    def met_for(activity_type: str) -> float:
        return MET_TABLE.get((activity_type or "").strip().lower(), MET_TABLE["other"])

    @classmethod
    def calories(cls, activity_type: str, duration_min: float, weight_kg: float) -> float:
        """Estimate kcal burned. Falls back to 70 kg if weight is missing."""
        met = cls.met_for(activity_type)
        weight = weight_kg if weight_kg and weight_kg > 0 else 70.0
        hours = max(0.0, float(duration_min)) / 60.0
        return round(met * weight * hours, 0)
