"""Scoring. Scorer is the contract, WeightedScorer is today's formula."""

from abc import ABC, abstractmethod

from .ingredient_matcher import IngredientMatcher
from .number_parser import NumberParser


class Scorer(ABC):
    """Any scoring method must give a number from 0 to 100."""

    @abstractmethod
    def score(self, recipe: dict, items: list, limit: int) -> float:
        """Return the score for one accepted recipe."""


class WeightedScorer(Scorer):
    """40% leftover coverage, 30% relevance, 30% calorie fit."""

    def __init__(
        self,
        matcher: IngredientMatcher,
        w_coverage: float = 0.4,
        w_relevance: float = 0.3,
        w_fit: float = 0.3,
    ):
        self._matcher = matcher
        self._weights = (w_coverage, w_relevance, w_fit)

    def score(self, recipe, items, limit):
        used = self._matcher.count_leftovers_used(recipe, items)
        coverage = used / max(1, len(items))
        relevance = self._matcher.relevance(recipe, used)
        calories = NumberParser.safe_number(recipe.get("calories"))
        fit = max(0.0, 1 - abs(limit - calories) / limit) if limit > 0 else 0.0
        w_coverage, w_relevance, w_fit = self._weights
        return round(
            100 * (w_coverage * coverage + w_relevance * relevance + w_fit * fit), 1
        )
