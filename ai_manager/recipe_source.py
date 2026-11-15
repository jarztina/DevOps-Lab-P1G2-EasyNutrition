import logging
import os
import time
from abc import ABC, abstractmethod
import requests

logger = logging.getLogger(__name__)

class RecipeSource(ABC):
    @abstractmethod
    def find_recipes(self, ingredient_names: list[str]) -> tuple[bool, list | str]:
        """Return (True, [recipe dicts in our format]) or (False, message)."""

class SpoonacularSource(RecipeSource):
    URL = "https://api.spoonacular.com/recipes/complexSearch"
    ATTEMPTS = 2
    MAX_RECIPES = 10

    def __init__(self, http_get=requests.get, sleep=time.sleep):
        # Both are injected so tests can fake the internet and skip the waiting.
        self._http_get = http_get
        self._sleep = sleep

    def _call(self, ingredient_names: list[str]) -> tuple[bool, list | str]:
        """Ask Spoonacular. Returns the raw result list or an error message."""
        key = os.environ.get("SPOONACULAR_API_KEY", "")
        if not key:
            return False, "The recipe service key is not configured."
            
        params = {
            "apiKey": key, "includeIngredients": ",".join(ingredient_names),
            "fillIngredients": "true", "addRecipeNutrition": "true",
            "instructionsRequired": "true", "sort": "max-used-ingredients",
            "number": self.MAX_RECIPES
        }
        
        for attempt in range(1, self.ATTEMPTS + 1):
            try:
                response = self._http_get(self.URL, params=params, timeout=15)
            except requests.exceptions.RequestException as exc:
                logger.warning("Recipe service attempt %d/%d failed: %s",
                               attempt, self.ATTEMPTS, type(exc).__name__)
                self._sleep(attempt)
                continue
            break # got an answer: leave the loop
        else: # loop finished without break: every try failed
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

    @staticmethod
    def _names_of(items) -> list[str]:
        """['rice', 'egg'] from Spoonacular's list of ingredient objects."""
        return [str(i["name"]) for i in (items or []) if isinstance(i, dict) and i.get("name")]

    @staticmethod
    def _find_calories(raw: dict) -> float | None:
        """Find the 'Calories' amount (per serving) inside the nutrition block."""
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

    @staticmethod
    def _find_steps(raw: dict) -> list[str]:
        """Flatten analyzedInstructions into a simple list of step texts."""
        steps = []
        for block in raw.get("analyzedInstructions") or []:
            if not isinstance(block, dict):
                continue
            for step in block.get("steps") or []:
                if isinstance(step, dict) and step.get("step"):
                    steps.append(str(step["step"]))
        return steps

    @staticmethod
    def _as_bool_or_none(value) -> bool | None:
        """Keep True/False, turn anything else into None ('unknown')."""
        return value if isinstance(value, bool) else None

    def _normalise(self, raw) -> dict | None:
        """One Spoonacular result -> one recipe dict in our format (or None)."""
        if not isinstance(raw, dict) or not raw.get("title"):
            return None
        calories = self._find_calories(raw)
        if calories is None:
            return None
        recipe_id = raw.get("id")
        return {
            "name": str(raw["title"]),
            "ingredients_used": self._names_of(raw.get("usedIngredients")),
            "extra_ingredients": self._names_of(raw.get("missedIngredients")),
            "calories": calories,
            "steps": self._find_steps(raw),
            "vegetarian": self._as_bool_or_none(raw.get("vegetarian")),
            "vegan": self._as_bool_or_none(raw.get("vegan")),
            "spoonacular_id": recipe_id if isinstance(recipe_id, int) else None,
            "source_url": str(raw.get("sourceUrl", "")),
        }

    def find_recipes(self, ingredient_names: list[str]) -> tuple[bool, list | str]:
        """Find recipes and convert them. Tries fewer ingredients if nothing matches."""
        if not ingredient_names:
            return True, []
        attempts = [ingredient_names]
        if len(ingredient_names) > 2:
            attempts.append(ingredient_names[:2])
        for names in attempts:
            ok, results = self._call(names)
            if not ok:
                return False, results
            recipes = [self._normalise(raw) for raw in results]
            recipes = [r for r in recipes if r is not None]
            if recipes:
                return True, recipes
        return True, []
