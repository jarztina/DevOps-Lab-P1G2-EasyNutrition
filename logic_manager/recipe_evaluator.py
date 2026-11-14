"""Judges one recipe by running every rule and then the scorer."""

from .evaluation_context import EvaluationContext
from .ingredient_matcher import IngredientMatcher
from .rules import Rule
from .scorer import Scorer


class RecipeEvaluator:
    """Open for extension: add a new Rule class to the list, no change needed here."""

    def __init__(self, rules: list[Rule], scorer: Scorer, matcher: IngredientMatcher):
        # Aggregation: the rules and the scorer are made elsewhere and handed in.
        self._rules = rules
        self._scorer = scorer
        self._matcher = matcher

    def evaluate(
        self, recipe: dict, detected_items: list, limit: int, diet: str
    ) -> dict:
        """Return a copy of the recipe with its decision, reasons and score."""
        items = self._matcher.confident_items(detected_items)
        ctx = EvaluationContext(items=items, limit=limit, diet=diet)
        reasons = []
        for rule in self._rules:
            passed, message = rule.check(recipe, ctx)
            if not passed:
                reasons.append(message)
        used = self._matcher.count_leftovers_used(recipe, items)
        result = dict(recipe)
        result["leftovers_used"] = used
        result["relevance"] = self._matcher.relevance(recipe, used)
        result["reasons"] = reasons
        if reasons:
            result["status"] = "rejected"
            result["score"] = 0.0
        else:
            result["status"] = "accepted"
            result["score"] = self._scorer.score(recipe, items, limit)
        return result
