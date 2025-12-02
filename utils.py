# utils.py
import json
import os

FAV_FILE = "favorites.json"

def load_favorites():
    if not os.path.exists(FAV_FILE):
        return []
    try:
        with open(FAV_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        return []
    return []

def save_favorites(data):
    try:
        with open(FAV_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def add_to_favorites(meal):
    if not meal or not meal.get("idMeal"):
        return False
    favs = load_favorites()
    if any(m.get("idMeal") == meal.get("idMeal") for m in favs):
        return False
    favs.append(meal)
    return save_favorites(favs)

def remove_from_favorites(meal_id):
    favs = load_favorites()
    new = [m for m in favs if m.get("idMeal") != meal_id]
    if len(new) == len(favs):
        return False
    return save_favorites(new)
