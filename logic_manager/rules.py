"""Business rules. Each rule is its own class with the same check() method."""
from abc import ABC, abstractmethod

from .evaluation_context import EvaluationContext
from .ingredient_matcher import IngredientMatcher
from .number_parser import NumberParser

MEAT = ["chicken", "beef", "pork", "lamb", "mutton", "fish", "salmon", "tuna",
        "prawn", "shrimp", "crab", "bacon", "ham", "sausage", "meat", "lard", "anchovy"]
ANIMAL_EXTRAS = ["egg", "milk", "cheese", "butter", "cream", "yogurt", "honey", "ghee"]
DIET_BANNED = {
    "none": [],
    "vegetarian": MEAT,
    "vegan": MEAT + ANIMAL_EXTRAS,
    "halal": ["pork", "bacon", "ham", "lard", "wine", "beer", "alcohol", "rum", "gelatin"],
}


class Rule(ABC):
    """The contract: every rule answers (passed?, reason if it failed)."""

    @abstractmethod
    def check(self, recipe: dict, ctx: EvaluationContext) -> tuple[bool, str]:
        """Return (True, "") if the recipe passes, else (False, reason)."""


class CalorieRule(Rule):
    """Reject nonsense calories (0, negative, text) and anything over the limit."""

    def check(self, recipe, ctx):
        calories = NumberParser.safe_number(recipe.get("calories"))
        if calories <= 0:
            return False, "Calorie value from the recipe source is invalid"
        if calories > ctx.limit:
            return False, f"Over calorie limit ({calories:.0f} > {ctx.limit})"
        return True, ""


class DietRule(Rule):
    """Reject the recipe if an ingredient or the recipe source breaks the diet."""

    @staticmethod
    def find_banned(recipe: dict, diet: str) -> list[str]:
        """List the banned words this recipe contains for the chosen diet."""
        banned = set(DIET_BANNED.get(diet, []))
        parts = [str(recipe.get("name", ""))]
        parts += [str(i) for i in recipe.get("ingredients_used", [])]
        parts += [str(i) for i in recipe.get("extra_ingredients", [])]
        return sorted(IngredientMatcher.to_words(" ".join(parts)) & banned)

    def check(self, recipe, ctx):
        found = self.find_banned(recipe, ctx.diet)
        if found:
            return False, f"Not {ctx.diet}: contains {', '.join(found)}"
        if ctx.diet in ("vegetarian", "vegan") and recipe.get(ctx.diet) is False:
            return False, f"Not {ctx.diet}: the recipe source says it is not {ctx.diet}"
        return True, ""


class LeftoverRule(Rule):
    """The recipe must use enough of the user's leftovers."""

    def __init__(self, matcher: IngredientMatcher, min_used: int = 2):
        self._matcher = matcher
        self._min_used = min_used

    def check(self, recipe, ctx):
        used = self._matcher.count_leftovers_used(recipe, ctx.items)
        needed = max(1, min(self._min_used, len(ctx.items)))
        if used < needed:
            return False, f"Uses only {used} of your leftovers, needs {needed}"
        return True, ""


class RelevanceRule(Rule):
    """Enough of the recipe's ingredients must be the user's leftovers."""

    def __init__(self, matcher: IngredientMatcher, min_relevance: float = 0.4):
        self._matcher = matcher
        self._min_relevance = min_relevance

    def check(self, recipe, ctx):
        used = self._matcher.count_leftovers_used(recipe, ctx.items)
        relevance = self._matcher.relevance(recipe, used)
        if relevance < self._min_relevance:
            return False, (f"Only {relevance:.0%} of its ingredients are your leftovers "
                           f"(needs {self._min_relevance:.0%})")
        return True, ""
