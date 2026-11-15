"""The Logic Manager: the one class the web app talks to for business rules."""
import logging

from .correction_service import CorrectionService
from .ingredient_matcher import IngredientMatcher
from .recipe_evaluator import RecipeEvaluator
from .rules import CalorieRule, DietRule, LeftoverRule, RelevanceRule
from .scorer import WeightedScorer

logger = logging.getLogger(__name__)


class LogicManager:
    """Judges recipes and handles corrections. No Flask, no API, no database."""

    def __init__(self, evaluator: RecipeEvaluator | None = None,
                 corrections: CorrectionService | None = None):
        if evaluator is None:
            # Composition: the default evaluator is built here from its small parts.
            matcher = IngredientMatcher()
            rules = [CalorieRule(), DietRule(), LeftoverRule(matcher), RelevanceRule(matcher)]
            evaluator = RecipeEvaluator(rules, WeightedScorer(matcher), matcher)
        self._evaluator = evaluator
        self._corrections = corrections or CorrectionService()

    def evaluate_recipe(self, recipe: dict, detected_items: list, limit: int, diet: str) -> dict:
        """Judge one recipe."""
        return self._evaluator.evaluate(recipe, detected_items, limit, diet)

    def process_ai_result(self, ai_data: dict, limit: int, diet: str) -> dict:
        """Judge every recipe in the ai_data and build the record to save and show."""
        items = ai_data.get("detected_items", [])
        recipes = ai_data.get("recipes", [])
        accepted = []
        rejected = []
        for recipe in recipes:
            result = self.evaluate_recipe(recipe, items, limit, diet)
            if result["status"] == "accepted":
                accepted.append(result)
            else:
                rejected.append(result)
        accepted.sort(key=lambda r: r["score"], reverse=True)
        logger.info("Judged %d recipes: %d accepted", len(recipes), len(accepted))
        return {"calorie_limit": limit, "diet": diet, "detected_items": items,
                "accepted": accepted, "rejected": rejected}

    # ---- new feature: fix the AI's mistakes --------------------------------
    def build_corrected_items(self, edits: list[dict]) -> list[dict]:
        """Turn the user's edited ingredient list into detected items."""
        return self._corrections.build_items(edits)

    def summarise_changes(self, before: dict, after: dict) -> dict:
        """Explain what the correction changed."""
        return self._corrections.summarise(before, after)