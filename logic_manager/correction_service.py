"""NEW FEATURE (Part 2): fix the AI's mistakes. Builds corrected items and explains the change."""


class CorrectionService:
    """Pure Python helper for the 'fix the AI' flow."""

    USER_CONFIDENCE = 1.0   # the user is sure, so we trust their list fully

    @staticmethod
    def _clean_name(text) -> str:
        return " ".join(str(text).strip().lower().split())

    def build_items(self, edits: list[dict]) -> list[dict]:
        """User edits [{'name','quantity'}] -> items in the same shape the AI gives us."""
        items = []
        seen = set()
        for edit in edits:
            name = self._clean_name(edit.get("name", ""))
            if not name or name in seen:
                continue
            seen.add(name)
            quantity = str(edit.get("quantity", "")).strip() or "1"
            items.append({"name": name, "quantity": quantity,
                          "confidence": self.USER_CONFIDENCE})
        return items

    def diff_items(self, before: list, after: list) -> tuple[list[str], list[str]]:
        """Return (added names, removed names) between two item lists."""
        old = [self._clean_name(i.get("name", "")) for i in before]
        new = [self._clean_name(i.get("name", "")) for i in after]
        added = [n for n in new if n not in old]
        removed = [n for n in old if n not in new]
        return added, removed

    def summarise(self, before: dict, after: dict) -> dict:
        """Compare the scan before and after the fix, with a short plain message."""
        added, removed = self.diff_items(before.get("detected_items", []),
                                         after.get("detected_items", []))
        before_count = len(before.get("accepted", []))
        after_count = len(after.get("accepted", []))
        parts = []
        if added:
            parts.append("added " + ", ".join(added))
        if removed:
            parts.append("removed " + ", ".join(removed))
        changed = "You " + " and ".join(parts) + "." if parts else "No ingredients changed."
        message = f"{changed} Recipes you can make: {before_count} before, {after_count} now."
        return {"added": added, "removed": removed, "accepted_before": before_count,
                "accepted_after": after_count, "message": message}