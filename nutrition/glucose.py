"""
Blood-glucose (blood sugar) interpretation for diabetes management.

The user logs one fasting reading per day (optionally a post-meal reading).
This module categorizes a reading and derives how strict the day's carb
advice should be. Educational thresholds based on common clinical ranges;
not a diagnostic tool.
"""
from typing import Optional
from models.schemas import GlucoseReading


class GlucoseMonitor:
    """Categorizes glucose readings and derives day-level carb strictness."""

    # Fasting thresholds (mg/dL)
    FASTING_NORMAL_MAX = 99      # <100 normal
    FASTING_ELEVATED_MAX = 125   # 100-125 elevated (prediabetes range); >=126 high

    # Post-meal (2-hour) thresholds (mg/dL)
    POST_MEAL_NORMAL_MAX = 139   # <140 normal
    POST_MEAL_ELEVATED_MAX = 179  # 140-179 elevated; >=180 high

    @classmethod
    def categorize(cls, reading: GlucoseReading) -> str:
        """Return 'normal', 'elevated', or 'high' for a reading."""
        value = reading.value_mg_dl
        if reading.reading_type == "post_meal":
            if value <= cls.POST_MEAL_NORMAL_MAX:
                return "normal"
            if value <= cls.POST_MEAL_ELEVATED_MAX:
                return "elevated"
            return "high"
        # default: fasting
        if value <= cls.FASTING_NORMAL_MAX:
            return "normal"
        if value <= cls.FASTING_ELEVATED_MAX:
            return "elevated"
        return "high"

    @classmethod
    def annotate(cls, reading: GlucoseReading) -> GlucoseReading:
        """Return the reading with its category field populated."""
        reading.category = cls.categorize(reading)
        return reading

    @classmethod
    def carb_adjustment(cls, reading: Optional[GlucoseReading]) -> float:
        """
        Multiplier applied to the day's carb budget based on the reading.
        No reading -> 1.0 (use goals as-is).
        """
        if reading is None:
            return 1.0
        category = reading.category if reading.category != "unknown" else cls.categorize(reading)
        return {"normal": 1.0, "elevated": 0.9, "high": 0.8}.get(category, 1.0)

    @classmethod
    def interpret(cls, reading: Optional[GlucoseReading]) -> str:
        """Human-readable guidance for today's reading."""
        if reading is None:
            return "No glucose reading logged today. Log a fasting reading each morning."

        category = reading.category if reading.category != "unknown" else cls.categorize(reading)
        kind = "fasting" if reading.reading_type == "fasting" else "post-meal"
        value = reading.value_mg_dl

        if category == "normal":
            return (
                f"Today's {kind} reading ({value:.0f} mg/dL) is in the normal range. "
                "Maintain your usual balanced, low-GI choices."
            )
        if category == "elevated":
            return (
                f"Today's {kind} reading ({value:.0f} mg/dL) is elevated. "
                "Favor low-GI, high-fiber foods and keep carbs toward the lower end today."
            )
        return (
            f"Today's {kind} reading ({value:.0f} mg/dL) is high. "
            "Prioritize low-GI, high-fiber meals, cut sugary foods, and tighten carb "
            "portions. If high readings persist, consult your doctor."
        )
