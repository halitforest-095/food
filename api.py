# api.py
import requests

API_BASE = "https://www.themealdb.com/api/json/v1/1/"

def search_meal(name):
    try:
        r = requests.get(f"{API_BASE}search.php", params={"s": name}, timeout=8)
        data = r.json()
        if data and data.get("meals"):
            return data["meals"][0]
    except Exception:
        return None
    return None

def get_random_meal():
    try:
        r = requests.get(f"{API_BASE}random.php", timeout=8)
        data = r.json()
        return data["meals"][0]
    except Exception:
        return None

def get_meal_by_id(meal_id):
    try:
        r = requests.get(f"{API_BASE}lookup.php", params={"i": meal_id}, timeout=8)
        data = r.json()
        if data and data.get("meals"):
            return data["meals"][0]
    except Exception:
        return None
    return None

def get_categories():
    try:
        r = requests.get(f"{API_BASE}categories.php", timeout=8)
        data = r.json()
        if data and data.get("categories"):
            return [c["strCategory"] for c in data["categories"]]
    except Exception:
        return []
    return []

def get_areas():
    try:
        r = requests.get(f"{API_BASE}list.php?a=list", timeout=8)
        data = r.json()
        if data and data.get("meals"):
            return [a["strArea"] for a in data["meals"]]
    except Exception:
        return []
    return []

def filter_meals(category=None, area=None):
    params = {}
    if category:
        params["c"] = category
    if area:
        params["a"] = area
    if not params:
        return []
    try:
        r = requests.get(f"{API_BASE}filter.php", params=params, timeout=10)
        data = r.json()
        if data and data.get("meals"):
            return data["meals"]  # each item has idMeal, strMeal, strMealThumb
    except Exception:
        return []
    return []
