import json

class IngredientParser:
    ITEM_SPEC = {"name": str, "quantity": str, "confidence": (int, float)}

    @staticmethod
    def extract_json_text(raw: str) -> str:
        """Keep only the part between the first { and the last }."""
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            return raw
        return raw[start:end + 1]

    @staticmethod
    def _check_fields(obj, spec: dict, label: str) -> tuple[bool, str]:
        """Check one object has every key in spec, each with the right type."""
        if not isinstance(obj, dict):
            return False, f"{label} is not an object"
        for key, expected in spec.items():
            if key not in obj:
                return False, f"{label} is missing '{key}'"
            if isinstance(obj[key], bool) or not isinstance(obj[key], expected):
                return False, f"{label} field '{key}' has the wrong type"
        return True, ""

    def validate(self, data) -> tuple[bool, str]:
        """Check the whole AI answer against the agreed schema."""
        if not isinstance(data, dict):
            return False, "Answer is not a JSON object"
        items = data.get("ingredients")
        if not isinstance(items, list):
            return False, "ingredients is missing or not a list"
        for number, item in enumerate(items, start=1):
            ok, error = self._check_fields(item, self.ITEM_SPEC, f"ingredients[{number}]")
            if not ok:
                return False, error
        return True, ""

    def parse(self, raw: str) -> tuple[bool, list | str]:
        """Raw AI text in -> (True, list of items) or (False, reason)."""
        try:
            data = json.loads(self.extract_json_text(raw))
        except json.JSONDecodeError:
            return False, "The AI did not return valid JSON."
        ok, error = self.validate(data)
        if not ok:
            return False, error
        return True, data["ingredients"]
