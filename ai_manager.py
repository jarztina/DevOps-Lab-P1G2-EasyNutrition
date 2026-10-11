# ai_manager.py - the only file that talks to outside APIs. No business rules.
import base64
import json
import logging
import os
import time

import anthropic
import requests

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
SPOON_ATTEMPTS = 2
SPOON_URL = "https://api.spoonacular.com/recipes/complexSearch"
MAX_QUERY_INGREDIENTS = 5
MAX_RECIPES = 10

JSON_EXAMPLE = """{
  "ingredients": [
    {"name": "rice", "quantity": "1 bowl", "confidence": 0.9},
    {"name": "egg", "quantity": "2", "confidence": 0.8}
  ]
}"""

ITEM_SPEC = {"name": str, "quantity": str, "confidence": (int, float)}


# Create the AI client from the environment. Never crashes if the key is missing.
def get_client() -> tuple[bool, object]:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return False, "AI API key is not configured."
    return True, anthropic.Anthropic(api_key=key, timeout=30.0, max_retries=0)


# Write the instructions we send with the photo.
def build_prompt() -> str:
    return (
        "You are a food-recognition assistant. Look at the photo of leftover food.\n"
        "List every separate food item or ingredient you can see. Use simple, common, "
        "singular English names (for example 'rice', 'egg', 'spring onion').\n"
        "Rules: quantity is short text like '1 bowl'. confidence is a number from 0 to 1. "
        "If no food is visible, return an empty list.\n"
        "Reply with ONLY a JSON object, no other text, in exactly this shape:\n"
        + JSON_EXAMPLE
    )


# Send photo + prompt. Return the raw text of the answer, or an error message.
def call_api(image_bytes: bytes, media_type: str, prompt: str) -> tuple[bool, str]:
    ok, client = get_client()
    if not ok:
        return False, client
    model = os.environ.get("AI_MODEL", "")
    if not model:
        return False, "AI model is not configured."
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    try:
        message = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64",
                                             "media_type": media_type,
                                             "data": image_b64}},
                {"type": "text", "text": prompt},
            ]}],
        )
    except anthropic.APIConnectionError:
        return False, "Cannot reach the AI service (network problem or timeout)."
    except anthropic.APIStatusError as exc:
        logger.error("AI API status error %s", exc.status_code)
        return False, f"AI service error (status {exc.status_code})."
    except Exception:
        logger.exception("Unexpected error calling the AI API")
        return False, "Unexpected error while calling the AI service."
    if not message.content:
        return False, "The AI service returned an empty answer."
    return True, message.content[0].text


# Keep only the part between the first { and the last }.
def extract_json_text(raw: str) -> str:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return raw
    return raw[start:end + 1]


# Check one object has every key in spec, each with the right type.
def check_fields(obj, spec: dict, label: str) -> tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, f"{label} is not an object"
    for key, expected in spec.items():
        if key not in obj:
            return False, f"{label} is missing '{key}'"
        if isinstance(obj[key], bool) or not isinstance(obj[key], expected):
            return False, f"{label} field '{key}' has the wrong type"
    return True, ""


# Check the whole AI answer against the agreed schema.
def validate_ingredients(data) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Answer is not a JSON object"
    items = data.get("ingredients")
    if not isinstance(items, list):
        return False, "ingredients is missing or not a list"
    for number, item in enumerate(items, start=1):
        ok, error = check_fields(item, ITEM_SPEC, f"ingredients[{number}]")
        if not ok:
            return False, error
    return True, ""


# Photo in, checked list of detected items out. Retries up to MAX_ATTEMPTS.
def identify_ingredients(image_bytes: bytes, media_type: str) -> tuple[bool, list | str]:
    prompt = build_prompt()
    last_error = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        ok, raw = call_api(image_bytes, media_type, prompt)
        if not ok:
            last_error = raw
            logger.warning("AI attempt %d/%d failed: %s", attempt, MAX_ATTEMPTS, raw)
            time.sleep(attempt)
            continue
        try:
            data = json.loads(extract_json_text(raw))
        except json.JSONDecodeError:
            last_error = "The AI did not return valid JSON."
            logger.warning("AI attempt %d/%d gave invalid JSON", attempt, MAX_ATTEMPTS)
            continue
        ok, error = validate_ingredients(data)
        if ok:
            return True, data["ingredients"]
        last_error = error
        logger.warning("AI attempt %d/%d failed schema: %s", attempt, MAX_ATTEMPTS, error)
    return False, f"The AI service failed after {MAX_ATTEMPTS} tries: {last_error}"


# Take the most confident ingredient names (no duplicates), best first.
def pick_query_ingredients(items: list) -> list[str]:
    ranked = sorted(items, key=lambda i: i.get("confidence", 0), reverse=True)
    names = []
    for item in ranked:
        name = str(item.get("name", "")).strip().lower()
        if name and name not in names:
            names.append(name)
    return names[:MAX_QUERY_INGREDIENTS]


# Ask Spoonacular for recipes. Returns the raw result list or an error message.
def call_spoonacular(ingredient_names: list[str]) -> tuple[bool, list | str]:
    key = os.environ.get("SPOONACULAR_API_KEY", "")
    if not key:
        return False, "The recipe service key is not configured."
    params = {"apiKey": key, "includeIngredients": ",".join(ingredient_names),
              "fillIngredients": "true", "addRecipeNutrition": "true",
              "instructionsRequired": "true", "sort": "max-used-ingredients",
              "number": MAX_RECIPES}
    for attempt in range(1, SPOON_ATTEMPTS + 1):
        try:
            response = requests.get(SPOON_URL, params=params, timeout=15)
        except requests.exceptions.RequestException as exc:
            logger.warning("Recipe service attempt %d/%d failed: %s",
                           attempt, SPOON_ATTEMPTS, type(exc).__name__)
            time.sleep(attempt)
            continue
        break                       # got an answer: leave the loop
    else:                           # loop finished without break: every try failed
        return False, "Cannot reach the recipe service. Please try again."
    if response.status_code in (401, 403):
        return False, "The recipe service rejected our key."
    if response.status_code == 402:
        return False, "The recipe service daily limit is used up. Try again tomorrow."
    if response.status_code == 429:
        return False, "Too many requests to the recipe service. Wait a minute."
    if response.status_code != 200:
        return False, f"Recipe service error (status {response.status_code})."
    try:
        body = response.json()
    except ValueError:
        return False, "The recipe service sent an unreadable answer."
    if not isinstance(body, dict) or not isinstance(body.get("results"), list):
        return False, "The recipe service answer had an unexpected shape."
    return True, body["results"]


# ['rice', 'egg'] from Spoonacular's list of ingredient objects.
def names_of(items) -> list[str]:
    return [str(i["name"]) for i in (items or []) if isinstance(i, dict) and i.get("name")]


# Find the 'Calories' amount (per serving) inside the nutrition block.
def find_calories(raw: dict) -> float | None:
    nutrition = raw.get("nutrition")
    nutrients = nutrition.get("nutrients", []) if isinstance(nutrition, dict) else []
    for nutrient in nutrients or []:
        if not isinstance(nutrient, dict):
            continue
        amount = nutrient.get("amount")
        is_calories = str(nutrient.get("name", "")).lower() == "calories"
        if is_calories and isinstance(amount, (int, float)) and not isinstance(amount, bool):
            return float(amount)
    return None


# Flatten Spoonacular's analyzedInstructions into a simple list of step texts.
def find_steps(raw: dict) -> list[str]:
    steps = []
    for block in raw.get("analyzedInstructions") or []:
        if not isinstance(block, dict):
            continue
        for step in block.get("steps") or []:
            if isinstance(step, dict) and step.get("step"):
                steps.append(str(step["step"]))
    return steps


# Keep True/False, turn anything else into None ('unknown').
def as_bool_or_none(value) -> bool | None:
    return value if isinstance(value, bool) else None


# One Spoonacular result -> one recipe dict in our format (or None).
def normalise_recipe(raw) -> dict | None:
    if not isinstance(raw, dict) or not raw.get("title"):
        return None
    calories = find_calories(raw)
    if calories is None:
        return None
    recipe_id = raw.get("id")
    return {
        "name": str(raw["title"]),
        "ingredients_used": names_of(raw.get("usedIngredients")),
        "extra_ingredients": names_of(raw.get("missedIngredients")),
        "calories": calories,
        "steps": find_steps(raw),
        "vegetarian": as_bool_or_none(raw.get("vegetarian")),
        "vegan": as_bool_or_none(raw.get("vegan")),
        "spoonacular_id": recipe_id if isinstance(recipe_id, int) else None,
        "source_url": str(raw.get("sourceUrl", "")),
    }


# Find recipes and convert them to our format. Tries fewer ingredients if empty.
def search_recipes(ingredient_names: list[str]) -> tuple[bool, list | str]:
    if not ingredient_names:
        return True, []
    attempts = [ingredient_names]
    if len(ingredient_names) > 2:
        attempts.append(ingredient_names[:2])
    for names in attempts:
        ok, results = call_spoonacular(names)
        if not ok:
            return False, results
        recipes = [normalise_recipe(raw) for raw in results]
        recipes = [r for r in recipes if r is not None]
        if recipes:
            return True, recipes
    return True, []


# Photo in, ai_data out: detected ingredients + candidate recipes.
def analyse_image(image_bytes: bytes, media_type: str) -> tuple[bool, dict | str]:
    ok, items = identify_ingredients(image_bytes, media_type)
    if not ok:
        return False, items
    ok, recipes = search_recipes(pick_query_ingredients(items))
    if not ok:
        return False, recipes
    return True, {"detected_items": items, "recipes": recipes}