"""Everything about scans: save, recent list, open one, delete, replace after a fix."""
import logging

import psycopg
from psycopg.types.json import Jsonb

from .base_repository import BaseRepository
from .constants import DB_DOWN

logger = logging.getLogger(__name__)

INSERT_SCAN_SQL = """
INSERT INTO scans (user_id, image_name, calorie_limit, diet, detected_items)
VALUES (%s, %s, %s, %s, %s) RETURNING id
"""

INSERT_RECIPE_SQL = """
INSERT INTO recipes (scan_id, name, calories, status, score, leftovers_used,
                     reasons, ingredients_used, extra_ingredients, steps,
                     spoonacular_id, source_url)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


class ScanRepository(BaseRepository):
    """Reads and writes the scans table (and the recipes that belong to a scan)."""

    @staticmethod
    def _recipe_params(scan_id: int, recipe: dict) -> tuple:
        """Turn one recipe dict into the values INSERT_RECIPE_SQL needs."""
        return (
            scan_id,
            recipe["name"],
            recipe.get("calories"),
            recipe["status"],
            recipe["score"],
            recipe["leftovers_used"],
            Jsonb(recipe["reasons"]),
            Jsonb(recipe.get("ingredients_used", [])),
            Jsonb(recipe.get("extra_ingredients", [])),
            Jsonb(recipe.get("steps", [])),
            recipe.get("spoonacular_id"),
            recipe.get("source_url", ""),
        )

    def save_record(self, record: dict) -> tuple[bool, int | str]:
        """Save a scan and its recipes in one transaction. Returns the scan id."""
        conn = self._connect()
        if conn is None:
            return False, DB_DOWN
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(INSERT_SCAN_SQL, (
                        record["user_id"], record["image_name"],
                        record["calorie_limit"], record["diet"],
                        Jsonb(record["detected_items"]),
                    ))
                    scan_id = cursor.fetchone()["id"]
                    for recipe in record["accepted"] + record["rejected"]:
                        cursor.execute(
                            INSERT_RECIPE_SQL, self._recipe_params(scan_id, recipe)
                        )
            return True, scan_id
        except (psycopg.Error, KeyError, TypeError) as exc:
            logger.error("Could not save record: %s", exc)
            return False, "Your results could not be saved, but they are shown below."
        finally:
            conn.close()

    def load_recent(self, user_id: int, limit: int = 5) -> tuple[bool, list | str]:
        """Load recent scans and count accepted recipes."""
        conn = self._connect()
        if conn is None:
            return False, DB_DOWN
        sql = """
            SELECT s.id, s.created_at, s.image_name, s.calorie_limit, s.diet,
                   (SELECT COUNT(*) FROM recipes r
                    WHERE r.scan_id = s.id AND r.status = 'accepted')
                   AS accepted_count
            FROM scans s
            WHERE s.user_id = %s
            ORDER BY s.created_at DESC
            LIMIT %s
        """
        try:
            with conn:
                rows = conn.execute(sql, (user_id, limit)).fetchall()
            return True, rows
        except psycopg.Error as exc:
            logger.error("Could not load recent scans: %s", exc)
            return False, "Could not load your recent scans."
        finally:
            conn.close()
    
    def get_scan(self, user_id: int, scan_id: int) -> tuple[bool, dict | None | str]:
        """Open one scan with its recipes. Returns None when it is not this user's."""
        conn = self._connect()
        if conn is None:
            return False, DB_DOWN
        try:
            with conn:
                scan = conn.execute(
                    "SELECT id, created_at, image_name, calorie_limit, diet, "
                    "detected_items FROM scans WHERE id = %s AND user_id = %s",
                    (scan_id, user_id),
                ).fetchone()
                if scan is None:
                    return True, None
                rows = conn.execute(
                    "SELECT * FROM recipes WHERE scan_id = %s "
                    "ORDER BY score DESC, id",
                    (scan_id,),
                ).fetchall()
            return True, {
                "scan_id": scan["id"],
                "created_at": scan["created_at"],
                "image_name": scan["image_name"],
                "calorie_limit": scan["calorie_limit"],
                "diet": scan["diet"],
                "detected_items": scan["detected_items"],
                "accepted": [r for r in rows if r["status"] == "accepted"],
                "rejected": [r for r in rows if r["status"] == "rejected"],
            }
        except psycopg.Error as exc:
            logger.error("Could not read scan: %s", exc)
            return False, "Could not open this scan."
        finally:
            conn.close()
    
    def delete_scan(self, user_id: int, scan_id: int) -> tuple[bool, bool | str]:
        """Delete one scan. Its recipes go too (ON DELETE CASCADE)."""
        conn = self._connect()
        if conn is None:
            return False, DB_DOWN
        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM scans WHERE id = %s AND user_id = %s",
                    (scan_id, user_id),
                )
                deleted = cursor.rowcount > 0
            return True, deleted
        except psycopg.Error as exc:
            logger.error("Could not delete scan: %s", exc)
            return False, "Could not delete this scan."
        finally:
            conn.close()
    
    def replace_scan_results(
        self, user_id: int, scan_id: int, record: dict
    ) -> tuple[bool, bool | str]:
        """After a fix: save the new ingredient list and the new recipes together.

        Either everything is replaced or nothing is (one transaction).
        Returns (True, False) when the scan does not belong to this user.
        """
        conn = self._connect()
        if conn is None:
            return False, DB_DOWN
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE scans SET detected_items = %s "
                        "WHERE id = %s AND user_id = %s",
                        (Jsonb(record["detected_items"]), scan_id, user_id),
                    )
                    if cursor.rowcount == 0:
                        return True, False
                    cursor.execute("DELETE FROM recipes WHERE scan_id = %s", (scan_id,))
                    for recipe in record["accepted"] + record["rejected"]:
                        cursor.execute(
                            INSERT_RECIPE_SQL, self._recipe_params(scan_id, recipe)
                        )
            return True, True
        except (psycopg.Error, KeyError, TypeError) as exc:
            logger.error("Could not replace scan results: %s", exc)
            return False, "Could not save your corrections."
        finally:
            conn.close()