"""Compares the user's leftovers with a recipe's ingredients."""

import re

from .number_parser import NumberParser


class IngredientMatcher:
    """Word matching, confidence filtering and relevance. No Flask, no API, no database."""

    def __init__(self, min_confidence: float = 0.6):
        self._min_confidence = min_confidence

    @staticmethod
    def to_words(text: str) -> set[str]:
        """'Fried Eggs' -> {'fried', 'egg'}: lowercase whole words, plural s removed."""
        words = re.findall(r"[a-z]+", str(text).lower())
        return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words}

    def confident_items(self, detected_items: list) -> list:
        """Keep only items the AI was reasonably sure about."""
        return [
            i
            for i in detected_items
            if NumberParser.safe_number(i.get("confidence")) >= self._min_confidence
        ]

    def count_leftovers_used(self, recipe: dict, items: list) -> int:
        """How many of the photographed items does this recipe actually use?"""
        used_words = [self.to_words(i) for i in recipe.get("ingredients_used", [])]
        count = 0
        for item in items:
            item_words = self.to_words(item.get("name", ""))
            if item_words and any(item_words & words for words in used_words):
                count += 1
        return count

    @staticmethod
    def relevance(recipe: dict, used: int) -> float:
        """Share of the recipe's ingredients that are the user's leftovers (0 to 1)."""
        extra = len(recipe.get("extra_ingredients", []))
        if used + extra == 0:
            return 0.0
        return round(used / (used + extra), 2)
