"""Safe number reading for values that come from the outside world."""


class NumberParser:
    """Small helper: turns 'maybe a number' into a real float."""

    @staticmethod
    def safe_number(value, default: float = 0.0) -> float:
        """Return value as a float, or default if it is not a real number."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)
