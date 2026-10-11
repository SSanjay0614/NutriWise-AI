"""
One-time data preparation: add approximate micronutrient columns to
data/nutriwise_foods.csv (per standard serving).

Adds: vitamin_a_mcg, vitamin_c_mg, vitamin_d_mcg, vitamin_b12_mcg,
      folate_mcg, magnesium_mg, zinc_mg

Values are ROUGH educational estimates derived by food category with a few
food-specific overrides. They are NOT clinically validated (same disclaimer as
the glycemic index estimates). Run once:  python prepare_micros.py
"""
import os
import pandas as pd

CSV = os.path.join(os.path.dirname(__file__), "..", "data", "nutriwise_foods.csv")
MICROS = ["vitamin_a_mcg", "vitamin_c_mg", "vitamin_d_mcg",
          "vitamin_b12_mcg", "folate_mcg", "magnesium_mg", "zinc_mg"]

# Per-serving baseline estimates by category.
#                      A    C    D    B12   folate  Mg    Zn
CATEGORY = {
    "Dairy":            [90,  1,  1.2, 0.9,  10,  15, 0.6],
    "Dessert/Junk":     [40,  0,  0.4, 0.3,  12,  18, 0.5],
    "Drinks":           [20,  8,  0.2, 0.2,  12,  12, 0.3],
    "Fast Food":        [45,  3,  0.3, 0.4,  28,  35, 1.4],
    "Fruit":            [35, 25,  0,   0,    25,  18, 0.2],
    "Indian Breakfast": [15,  2,  0,   0,    20,  30, 0.8],
    "Indian Curry":     [120, 8,  0.1, 0.3,  55,  45, 1.3],
    "Indian Main":      [20,  2,  0,   0.1,  30,  45, 1.1],
    "Indian Side":      [60,  6,  0,   0,    35,  25, 0.7],
    "Indian Snack":     [25,  3,  0.1, 0.1,  22,  28, 0.9],
    "Indian Street Food":[90, 12, 0.1, 0.2,  40,  40, 1.2],
    "Nuts":             [2,   0,  0,   0,    30,  80, 1.6],
    "Packaged/Junk":    [20,  0,  0.2, 0.2,  14,  22, 0.6],
    "Protein":          [60,  1,  0.8, 1.2,  25,  30, 2.2],
    "Snack":            [10,  1,  0,   0,    25,  40, 1.0],
    "South Indian Breakfast":[15, 2, 0, 0.1, 22,  32, 0.9],
    "South Indian Snack":[12,  1,  0,   0,    20,  28, 0.8],
    "Spreads":          [0,   0,  0,   0,    25,  55, 1.1],
    "Traditional Drink":[10,  1,  0,   0.1,  15,  40, 0.9],
    "Vegetable":        [150, 20, 0,   0,    45,  25, 0.5],
}

# Food-specific overrides (standout sources). Keys = food_name.
OVERRIDES = {
    "Orange": {"vitamin_c_mg": 50, "folate_mcg": 40},
    "Guava": {"vitamin_c_mg": 180, "folate_mcg": 40},
    "Papaya": {"vitamin_c_mg": 60, "vitamin_a_mcg": 55},
    "Mango": {"vitamin_c_mg": 36, "vitamin_a_mcg": 54},
    "Pineapple": {"vitamin_c_mg": 48},
    "Carrot": {"vitamin_a_mcg": 835, "vitamin_c_mg": 6},
    "Spinach": {"vitamin_a_mcg": 470, "folate_mcg": 110, "vitamin_c_mg": 14, "magnesium_mg": 55},
    "Broccoli": {"vitamin_c_mg": 65, "folate_mcg": 60, "vitamin_a_mcg": 30},
    "Tomato": {"vitamin_c_mg": 18, "vitamin_a_mcg": 42},
    "Sweet Potato": {"vitamin_a_mcg": 700, "vitamin_c_mg": 12},
    "Boiled Egg": {"vitamin_d_mcg": 1.1, "vitamin_b12_mcg": 0.6, "vitamin_a_mcg": 80},
    "Omelette": {"vitamin_d_mcg": 1.3, "vitamin_b12_mcg": 0.7},
    "Egg Bhurji": {"vitamin_d_mcg": 1.3, "vitamin_b12_mcg": 0.8},
    "Grilled Fish": {"vitamin_d_mcg": 4.0, "vitamin_b12_mcg": 2.5},
    "Fish Curry": {"vitamin_d_mcg": 3.5, "vitamin_b12_mcg": 2.2},
    "Fish Fry": {"vitamin_d_mcg": 3.5, "vitamin_b12_mcg": 2.2},
    "Cow Milk": {"vitamin_d_mcg": 1.2, "vitamin_b12_mcg": 0.9, "vitamin_a_mcg": 95},
    "Greek Yogurt": {"vitamin_b12_mcg": 0.8, "vitamin_a_mcg": 27},
    "Plain Curd": {"vitamin_b12_mcg": 0.6},
    "Almonds": {"magnesium_mg": 80, "zinc_mg": 0.9, "vitamin_c_mg": 0},
    "Peanuts": {"magnesium_mg": 60, "folate_mcg": 68, "zinc_mg": 1.0},
    "Cashews": {"magnesium_mg": 82, "zinc_mg": 1.6},
    "Chana Masala": {"folate_mcg": 160, "magnesium_mg": 50, "zinc_mg": 1.5},
    "Rajma Curry": {"folate_mcg": 130, "magnesium_mg": 55, "zinc_mg": 1.4},
    "Dal Tadka": {"folate_mcg": 120, "magnesium_mg": 40},
    "Roasted Chana": {"folate_mcg": 160, "magnesium_mg": 60, "zinc_mg": 1.6},
}


def main() -> None:
    df = pd.read_csv(CSV)
    rows = {m: [] for m in MICROS}
    for _, row in df.iterrows():
        base = CATEGORY.get(str(row["category"]).strip(), [20, 2, 0.1, 0.2, 20, 25, 0.7])
        vals = dict(zip(MICROS, base))
        vals.update(OVERRIDES.get(str(row["food_name"]).strip(), {}))
        for m in MICROS:
            rows[m].append(round(float(vals[m]), 2))
    for m in MICROS:
        df[m] = rows[m]
    df.to_csv(CSV, index=False)
    print(f"[OK] Added {len(MICROS)} micronutrient columns to {CSV} ({len(df)} foods).")
    print("     Columns:", ", ".join(MICROS))


if __name__ == "__main__":
    main()
