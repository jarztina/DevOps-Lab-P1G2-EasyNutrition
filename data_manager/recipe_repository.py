"""Everything about saved recipes: search, open one, edit, delete."""
import logging

import psycopg
from psycopg.types.json import Jsonb

from .base_repository import BaseRepository
from .constants import DB_DOWN

logger = logging.getLogger(__name__)

# A recipe belongs to a user only through its scan, so every query checks the scan.
OWNED_BY_USER = "scan_id IN (SELECT id FROM scans WHERE user_id = %s)"

class RecipeRepository(BaseRepository):
    """Reads and writes the recipes table."""

    TEXT_FIELDS = {"notes": 500}                          # field -> longest text
    LIST_FIELDS = ("ingredients_used", "extra_ingredients")
    MAX_LIST_ITEMS = 30
    MAX_ITEM_LENGTH = 100

    def filter_recipes(
        self, user_id: int, diet: str | None = None,
        max_calories: int | None = None, status: str = "accepted",
    ) -> tuple[bool, list | str]:
        """Find saved recipes by status, diet and calorie limit."""
        conn = self._connect()
        if conn is None:
            return False, DB_DOWN
        sql = (
            "SELECT r.*, s.image_name, s.diet, s.created_at "
            "FROM recipes r JOIN scans s ON s.id = r.scan_id "
            "WHERE s.user_id = %s AND r.status = %s"
        )
        params = [user_id, status]
        if diet and diet != "none":
            sql += " AND s.diet = %s"
            params.append(diet)
        if max_calories is not None:
            sql += " AND r.calories <= %s"
            params.append(max_calories)
        sql += " ORDER BY s.created_at DESC, r.score DESC, r.id LIMIT 100"
        try:
            with conn:
                rows = conn.execute(sql, params).fetchall()
            return True, rows
        except psycopg.Error as exc:
            logger.error("Could not filter recipes: %s", exc)
            return False, "Could not search your saved recipes."
        finally:
            conn.close()

    def get_recipe(self, user_id: int, recipe_id: int) -> tuple[bool, dict | None | str]:
        """Open one saved recipe. Returns None when it is not this user's."""
        conn = self._connect()
        if conn is None:
            return False, DB_DOWN
        try:
            with conn:
                row = conn.execute(
                    "SELECT r.*, s.image_name, s.diet, s.created_at "
                    "FROM recipes r JOIN scans s ON s.id = r.scan_id "
                    "WHERE r.id = %s AND s.user_id = %s",
                    (recipe_id, user_id),
                ).fetchone()
            return True, row
        except psycopg.Error as exc:
            logger.error("Could not read recipe: %s", exc)
            return False, "Could not open this recipe."
        finally:
            conn.close()

    
    def _check_changes(self, changes) -> tuple[bool, str]:
        """Allow only known fields with the right type and size."""
        if not isinstance(changes, dict) or not changes:
            return False, "There is nothing to change."
        for field, value in changes.items():
            if field in self.TEXT_FIELDS:
                if not isinstance(value, str):
                    return False, f"{field} must be text."
                if len(value) > self.TEXT_FIELDS[field]:
                    return False, f"{field} is too long."
            elif field in self.LIST_FIELDS:
                if not isinstance(value, list) or len(value) > self.MAX_LIST_ITEMS:
                    return False, f"{field} must be a short list."
                for item in value:
                    if not isinstance(item, str) or not item.strip():
                        return False, f"{field} can only hold text."
                    if len(item) > self.MAX_ITEM_LENGTH:
                        return False, f"An item in {field} is too long."
            else:
                return False, f"You cannot edit '{field}'."
        return True, ""
    
    def update_recipe(
        self, user_id: int, recipe_id: int, changes: dict
    ) -> tuple[bool, bool | str]:
        """Edit notes and ingredient lists. Returns (True, False) if not found."""
        ok, message = self._check_changes(changes)
        if not ok:
            return False, message
        conn = self._connect()
        if conn is None:
            return False, DB_DOWN
        # Column names come from our own whitelist above, never from the user.
        columns = list(changes)
        assignments = ", ".join(f"{column} = %s" for column in columns)
        values = [
            Jsonb(changes[c]) if c in self.LIST_FIELDS else changes[c] for c in columns
        ]
        sql = f"UPDATE recipes SET {assignments} WHERE id = %s AND {OWNED_BY_USER}"
        try:
            with conn:
                cursor = conn.execute(sql, values + [recipe_id, user_id])
                updated = cursor.rowcount > 0
            return True, updated
        except psycopg.Error as exc:
            logger.error("Could not update recipe: %s", exc)
            return False, "Could not save your changes."
        finally:
            conn.close()