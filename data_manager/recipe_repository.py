"""Everything about saved recipes: search, open one, edit, delete."""
import logging

import psycopg

from .base_repository import BaseRepository
from .constants import DB_DOWN

logger = logging.getLogger(__name__)


class RecipeRepository(BaseRepository):
    """Reads and writes the recipes table."""

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