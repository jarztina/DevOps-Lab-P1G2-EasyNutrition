# logic_manager.py - business rules. Pure Python: no Flask, no API, no database.
import logging
import re

logger = logging.getLogger(__name__)

MIN_ITEM_CONFIDENCE = 0.6
MIN_LEFTOVERS_USED = 2
MIN_RELEVANCE = 0.4

MEAT = ["chicken", "beef", "pork", "lamb", "mutton", "fish", "salmon", "tuna",
        "prawn", "shrimp", "crab", "bacon", "ham", "sausage", "meat", "lard", "anchovy"]
ANIMAL_EXTRAS = ["egg", "milk", "cheese", "butter", "cream", "yogurt", "honey", "ghee"]
DIET_BANNED = {
    "none": [],
    "vegetarian": MEAT,
    "vegan": MEAT + ANIMAL_EXTRAS,
    "halal": ["pork", "bacon", "ham", "lard", "wine", "beer", "alcohol", "rum", "gelatin"],
}


# 'Fried Eggs' -> {'fried', 'egg'}: lowercase whole words, plural s removed.
def to_words(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", str(text).lower())
    return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words}


# Return value as a float, or default if it is not a real number.
def safe_number(value, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


# List the banned words this recipe contains for the chosen diet.
def find_banned(recipe: dict, diet: str) -> list[str]:
    banned = set(DIET_BANNED.get(diet, []))
    parts = [str(recipe.get("name", ""))]
    parts += [str(i) for i in recipe.get("ingredients_used", [])]
    parts += [str(i) for i in recipe.get("extra_ingredients", [])]
    return sorted(to_words(" ".join(parts)) & banned)


# Reject the recipe if an ingredient or the recipe source breaks the diet.
def check_diet(recipe: dict, diet: str) -> tuple[bool, str]:
    found = find_banned(recipe, diet)
    if found:
        return False, f"Not {diet}: contains {', '.join(found)}"
    if diet in ("vegetarian", "vegan") and recipe.get(diet) is False:
        return False, f"Not {diet}: the recipe source says it is not {diet}"
    return True, ""


# Reject nonsense calories (0, negative, text) and anything over the limit.
def check_calories(recipe: dict, limit: int) -> tuple[bool, str]:
    calories = safe_number(recipe.get("calories"))
    if calories <= 0:
        return False, "Calorie value from the recipe source is invalid"
    if calories > limit:
        return False, f"Over calorie limit ({calories:.0f} > {limit})"
    return True, ""


# Keep only items the AI was reasonably sure about.
def confident_items(detected_items: list) -> list:
    return [i for i in detected_items
            if safe_number(i.get("confidence")) >= MIN_ITEM_CONFIDENCE]


# How many of the photographed items does this recipe actually use?
def count_leftovers_used(recipe: dict, items: list) -> int:
    used_words = [to_words(i) for i in recipe.get("ingredients_used", [])]
    count = 0
    for item in items:
        item_words = to_words(item.get("name", ""))
        if item_words and any(item_words & words for words in used_words):
            count += 1
    return count


# Share of the recipe's ingredients that are the user's leftovers (0 to 1).
def calculate_relevance(recipe: dict, used: int) -> float:
    extra = len(recipe.get("extra_ingredients", []))
    if used + extra == 0:
        return 0.0
    return round(used / (used + extra), 2)


# Score 0-100: 40% leftover coverage, 30% relevance, 30% calorie fit.
def calculate_score(recipe: dict, items: list, limit: int) -> float:
    used = count_leftovers_used(recipe, items)
    coverage = used / max(1, len(items))
    relevance = calculate_relevance(recipe, used)
    calories = safe_number(recipe.get("calories"))
    fit = max(0.0, 1 - abs(limit - calories) / limit) if limit > 0 else 0.0
    return round(100 * (0.4 * coverage + 0.3 * relevance + 0.3 * fit), 1)


# Apply the three checks. Return a copy of the recipe with the decision.
def evaluate_recipe(recipe: dict, detected_items: list, limit: int, diet: str) -> dict:
    items = confident_items(detected_items)
    reasons = []
    ok, message = check_calories(recipe, limit)
    if not ok:
        reasons.append(message)
    ok, message = check_diet(recipe, diet)
    if not ok:
        reasons.append(message)
    used = count_leftovers_used(recipe, items)
    needed = max(1, min(MIN_LEFTOVERS_USED, len(items)))
    relevance = calculate_relevance(recipe, used)
    if used < needed:
        reasons.append(f"Uses only {used} of your leftovers, needs {needed}")
    if relevance < MIN_RELEVANCE:
        reasons.append(f"Only {relevance:.0%} of its ingredients are your leftovers "
                       f"(needs {MIN_RELEVANCE:.0%})")

    result = dict(recipe)
    result["leftovers_used"] = used
    result["relevance"] = relevance
    result["reasons"] = reasons
    if reasons:
        result["status"] = "rejected"
        result["score"] = 0.0
    else:
        result["status"] = "accepted"
        result["score"] = calculate_score(recipe, items, limit)
    return result


# Judge every recipe in the ai_data and build the record to save and show.
def process_ai_result(ai_data: dict, limit: int, diet: str) -> dict:
    items = ai_data.get("detected_items", [])
    recipes = ai_data.get("recipes", [])
    accepted = []
    rejected = []
    for recipe in recipes:
        result = evaluate_recipe(recipe, items, limit, diet)
        if result["status"] == "accepted":
            accepted.append(result)
        else:
            rejected.append(result)
    accepted.sort(key=lambda r: r["score"], reverse=True)
    logger.info("Judged %d recipes: %d accepted", len(recipes), len(accepted))
    return {"calorie_limit": limit, "diet": diet, "detected_items": items,
            "accepted": accepted, "rejected": rejected}