"""The facts a rule needs to judge one recipe."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationContext:
    """Bundle of: the confident items, the calorie limit and the diet."""

    items: list
    limit: int
    diet: str
