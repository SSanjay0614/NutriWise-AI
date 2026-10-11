"""
One-time data preparation for the diabetes pivot.

Adds two columns to data/nutriwise_foods.csv:
  - glycemic_index : approximate GI (0-100) for each food
  - gi_category    : "low" (<=55), "medium" (56-69), or "high" (>=70)

GI values are APPROXIMATE educational estimates compiled from common
published GI references and category reasoning. They are NOT clinically
validated. Pure (non-carb) protein/fat foods are given a low nominal GI
because they cause little blood-glucose rise on their own.

Run once:  python prepare_diabetes_data.py
"""
import os
import pandas as pd

# Project root is the parent of this scripts/ folder.
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nutriwise_foods.csv")

# Per-food approximate glycemic index (keyed by exact food_name).
GI_BY_FOOD = {
    # South Indian Breakfast
    "Idli": 69, "Plain Dosa": 68, "Masala Dosa": 69, "Rava Dosa": 65,
    "Set Dosa": 68, "Onion Uttapam": 65, "Ven Pongal": 72, "Upma": 65,
    "Pesarattu": 50, "Adai": 45, "Appam": 65, "Puttu": 65, "Idiyappam": 65,
    # Indian Breakfast
    "Poha": 60,
    # Indian Main
    "Chapati": 52, "Aloo Paratha": 60, "Puri": 72, "Bhatura": 75,
    "Steamed White Rice": 73, "Brown Rice": 55, "Curd Rice": 65,
    "Lemon Rice": 70, "Tomato Rice": 70, "Vegetable Rice": 68,
    "Veg Biryani": 65, "Chicken Biryani": 60, "Egg Biryani": 60,
    "Mutton Biryani": 58, "Dal Rice": 65, "Vegetable Pulao": 65,
    "Chole Bhature": 72,
    # Indian Curry
    "Dal Tadka": 30, "Chana Masala": 35, "Rajma Curry": 35,
    "Mixed Vegetable Curry": 40, "Palak Paneer": 30, "Paneer Butter Masala": 30,
    "Chicken Curry": 30, "Butter Chicken": 30, "Mutton Curry": 30,
    # Indian Side
    "Sambar": 35, "Rasam": 35, "Coconut Chutney": 35,
    # Indian Snack
    "Samosa": 60, "Aloo Bonda": 65, "Pakora": 60, "Pani Puri": 70,
    "Bhel Puri": 65, "Sev Puri": 65, "Vada Pav": 70,
    # Indian Street Food
    "Pav Bhaji": 65,
    # Nuts
    "Almonds": 15, "Peanuts": 15, "Cashews": 25,
    # Packaged/Junk
    "Maggi Noodles": 65, "Cheese Maggi": 62, "Potato Chips": 56,
    "Biscuits": 70, "Chocolate Cookies": 72,
    # Protein (meat/egg/paneer -> little glucose rise)
    "Grilled Chicken": 5, "Tandoori Chicken": 5, "Boiled Egg": 5,
    "Omelette": 5, "Egg Bhurji": 10, "Paneer": 27, "Tofu": 15,
    "Paneer Tikka": 27, "Fish Curry": 30, "Grilled Fish": 5, "Fish Fry": 35,
    "Soy Chunks Curry": 35, "Chicken Tikka": 5,
    # Snack
    "Popcorn": 58, "Roasted Chana": 35,
    # Dairy
    "Plain Curd": 35, "Greek Yogurt": 15, "Cow Milk": 40,
    # Dessert/Junk
    "Chocolate Bar": 60, "Cake": 70, "Pastry": 70, "Donut": 75,
    "Brownie": 70, "Ice Cream": 60,
    # Drinks
    "Buttermilk": 30, "Sweet Lassi": 65, "Tea with Milk": 45,
    "Filter Coffee with Milk": 45, "Black Coffee": 5, "Cola": 63,
    "Orange Juice": 50, "Milkshake": 60, "Chocolate Milkshake": 65,
    "Energy Drink": 70,
    # Fast Food
    "Chicken Fried Rice": 68, "Veg Fried Rice": 70, "Egg Fried Rice": 68,
    "Schezwan Fried Rice": 70, "Chicken Noodles": 60, "Veg Noodles": 62,
    "Egg Noodles": 60, "Schezwan Noodles": 62, "Chicken 65": 45,
    "Chilli Chicken": 50, "Gobi Manchurian": 60, "Chicken Shawarma": 55,
    "Chicken Roll": 60, "Egg Roll": 60, "Paneer Roll": 58, "Chicken Burger": 65,
    "Veg Burger": 66, "Cheese Burger": 65, "Chicken Pizza": 65,
    "Margherita Pizza": 68, "Veg Pizza": 66, "French Fries": 70,
    "Chicken Nuggets": 55, "Fried Chicken": 45, "White Sauce Pasta": 55,
    "Red Sauce Pasta": 55, "Chicken Pasta": 52, "Grilled Sandwich": 60,
    "Chicken Sandwich": 60, "Bread Omelette": 58, "Vegetable Sandwich": 62,
    "Chicken Kathi Roll": 60, "Chicken Momos": 55, "Veg Momos": 58,
    "Spring Rolls": 60, "Chicken Popcorn": 55, "Nachos with Cheese": 60,
    "Hot Dog": 65,
    # Fruit
    "Banana": 55, "Apple": 38, "Orange": 43, "Mango": 55, "Papaya": 60,
    "Guava": 35, "Watermelon": 72, "Pomegranate": 53, "Grapes": 59,
    "Pineapple": 66,
    # Vegetable
    "Carrot": 39, "Spinach": 15, "Tomato": 15, "Potato": 78,
    "Sweet Potato": 63, "Broccoli": 15,
    # Spreads
    "Peanut Butter": 14,
    # Traditional Drink
    "Ragi Malt": 55,
}

# Fallback default GI by category when a food is not in GI_BY_FOOD.
GI_BY_CATEGORY = {
    "Dairy": 35, "Dessert/Junk": 70, "Drinks": 55, "Fast Food": 62,
    "Fruit": 50, "Indian Breakfast": 62, "Indian Curry": 32,
    "Indian Main": 66, "Indian Side": 35, "Indian Snack": 63,
    "Indian Street Food": 65, "Nuts": 20, "Packaged/Junk": 65,
    "Protein": 10, "Snack": 50, "South Indian Breakfast": 66,
    "South Indian Snack": 62, "Spreads": 20, "Traditional Drink": 55,
    "Vegetable": 35,
}


def gi_category(gi: int) -> str:
    if gi <= 55:
        return "low"
    if gi <= 69:
        return "medium"
    return "high"


def main() -> None:
    df = pd.read_csv(CSV_PATH)

    gis = []
    for _, row in df.iterrows():
        name = str(row["food_name"]).strip()
        cat = str(row["category"]).strip()
        gi = GI_BY_FOOD.get(name, GI_BY_CATEGORY.get(cat, 55))
        gis.append(int(gi))

    df["glycemic_index"] = gis
    df["gi_category"] = [gi_category(g) for g in gis]

    df.to_csv(CSV_PATH, index=False)

    counts = df["gi_category"].value_counts().to_dict()
    print(f"[OK] Updated {CSV_PATH} with glycemic_index + gi_category")
    print(f"  Foods: {len(df)} | GI breakdown: {counts}")
    missing = [n for n in df['food_name'] if n not in GI_BY_FOOD]
    if missing:
        print(f"  [!] Used category default for: {missing}")


if __name__ == "__main__":
    main()
