# data_manager.py - all PostgreSQL access. OOP implementation using an abstract
# DataManager contract and a PostgreSQL implementation.

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

import bcrypt
import psycopg
from psycopg.types.json import Jsonb

from database.connection import get_connection

logger = logging.getLogger(__name__)

DB_DOWN = "The database is unavailable right now."
MAX_PASSWORD_BYTES = 72  # bcrypt cannot use more than 72 bytes

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


# The contract that all Data Manager implementations must follow.
class DataManager(ABC):
    """Abstract interface for EasyNutrition data operations."""

    @abstractmethod
    def create_user(
        self,
        name: str,
        password: str,
        calorie_target: int = 2000,
        dietary_preference: str = "none",
    ) -> tuple[bool, int | str]:
        """Create a user account."""

    @abstractmethod
    def verify_login(self, name: str, password: str) -> tuple[bool, int | str]:
        """Verify a user's login credentials."""

    @abstractmethod
    def get_user(self, user_id: int) -> tuple[bool, dict | None | str]:
        """Retrieve a user's profile."""

    @abstractmethod
    def update_user(
        self, user_id: int, calorie_target: int, dietary_preference: str
    ) -> tuple[bool, bool | str]:
        """Update a user's profile."""

    @abstractmethod
    def delete_user(self, user_id: int) -> tuple[bool, bool | str]:
        """Delete a user account."""

    @abstractmethod
    def save_record(self, record: dict) -> tuple[bool, int | str]:
        """Save a scan and its associated recipes."""

    @abstractmethod
    def load_recent(self, user_id: int, limit: int = 5) -> tuple[bool, list | str]:
        """Load a user's most recent scans."""

    @abstractmethod
    def filter_recipes(
        self,
        user_id: int,
        diet: str | None = None,
        max_calories: int | None = None,
        status: str = "accepted",
    ) -> tuple[bool, list | str]:
        """Filter a user's saved recipes."""

class PostgresDataManager(DataManager):
    """Data Manager implementation using PostgreSQL and psycopg."""

    def __init__(self, connection_factory: Callable | None = None):
        # Dependency injection lets tests provide fake connections.
        # The default factory uses the existing database connection module.
        self._connection_factory = connection_factory or (lambda: get_connection())

    def _get_connection(self):
        """Return a database connection, or None when the database is down."""
        return self._connection_factory()

    @staticmethod
    def password_matches(password: str, stored_hash: str) -> bool:
        """Return whether a password matches its bcrypt hash. Never raises."""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), stored_hash.encode("utf-8")
            )
        except (ValueError, TypeError, AttributeError):
            return False

    
    def create_user(
        self,
        name: str,
        password: str,
        calorie_target: int = 2000,
        dietary_preference: str = "none",
    ) -> tuple[bool, int | str]:
        """Register a user. Returns (True, user_id) or (False, message)."""

        # Validate input types before using string methods
        if not isinstance(name, str) or not isinstance(password, str):
            return False, "Name and password must be text."

        name = name.strip().lower()

        if not name:
            return False, "Name cannot be empty."
        if not password:
            return False, "Password cannot be empty."
        if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
            return False, "Password is too long."

        if not isinstance(calorie_target, (int, float)) or isinstance(calorie_target, bool):
            return False, "Calorie target must be a number."
        if calorie_target <= 0:
            return False, "Calorie target must be greater than 0."

        if not isinstance(dietary_preference, str):
            return False, "Dietary preference must be text."
        if not dietary_preference.strip():
            return False, "Dietary preference cannot be empty."

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        conn = self._get_connection()
        if conn is None:
            return False, DB_DOWN

        try:
            with conn:
                row = conn.execute(
                    "INSERT INTO users "
                    "(name, password_hash, calorie_target, dietary_preference) "
                    "VALUES (%s, %s, %s, %s) RETURNING user_id",
                    (name, password_hash, calorie_target, dietary_preference),
                ).fetchone()

            return True, row["user_id"]

        except psycopg.errors.UniqueViolation:
            return False, "That name is already taken."
        except psycopg.Error as exc:
            logger.error("Could not create user: %s", exc)
            return False, "Could not create your account. Please try again."
        finally:
            conn.close()


    def verify_login(self, name: str, password: str) -> tuple[bool, int | str]:
        """Check a login. Returns (True, user_id) or (False, message)."""
        name = name.strip().lower()

        if not name or not password:
            return False, "Please type your name and password."

        conn = self._get_connection()
        if conn is None:
            return False, DB_DOWN

        try:
            with conn:
                user = conn.execute(
                    "SELECT user_id, password_hash FROM users WHERE name = %s",
                    (name,),
                ).fetchone()
        except psycopg.Error as exc:
            logger.error("Could not look up user: %s", exc)
            return False, "Could not check your login right now."
        finally:
            conn.close()

        if user is not None and self.password_matches(
            password, user["password_hash"]
        ):
            return True, user["user_id"]

        return False, "Wrong name or password."

    def get_user(self, user_id: int) -> tuple[bool, dict | None | str]:
        """Get a user's profile. A missing user is not a database error."""
        conn = self._get_connection()
        if conn is None:
            return False, DB_DOWN

        try:
            with conn:
                row = conn.execute(
                    "SELECT user_id, name, calorie_target, dietary_preference "
                    "FROM users WHERE user_id = %s",
                    (user_id,),
                ).fetchone()

            return True, row

        except psycopg.Error as exc:
            logger.error("Could not read user: %s", exc)
            return False, "Could not load your profile."
        finally:
            conn.close()

    def update_user(
        self, user_id: int, calorie_target: int, dietary_preference: str
    ) -> tuple[bool, bool | str]:
        """Update a user's calorie target and diet."""
        if calorie_target <= 0:
            return False, "Calorie target must be greater than 0."
        if not dietary_preference.strip():
            return False, "Dietary preference cannot be empty."

        conn = self._get_connection()
        if conn is None:
            return False, DB_DOWN

        try:
            with conn:
                cursor = conn.execute(
                    "UPDATE users SET calorie_target = %s, "
                    "dietary_preference = %s WHERE user_id = %s",
                    (calorie_target, dietary_preference, user_id),
                )
                updated = cursor.rowcount > 0

            return True, updated

        except psycopg.Error as exc:
            logger.error("Could not update user: %s", exc)
            return False, "Could not update your profile."
        finally:
            conn.close()

    def delete_user(self, user_id: int) -> tuple[bool, bool | str]:
        """Delete a user and related scans/recipes through database cascades."""
        conn = self._get_connection()
        if conn is None:
            return False, DB_DOWN

        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM users WHERE user_id = %s", (user_id,)
                )
                deleted = cursor.rowcount > 0

            return True, deleted

        except psycopg.Error as exc:
            logger.error("Could not delete user: %s", exc)
            return False, "Could not delete the user."
        finally:
            conn.close()

    def save_record(self, record: dict) -> tuple[bool, int | str]:
        """Save a scan and all its accepted/rejected recipes in one transaction."""
        conn = self._get_connection()
        if conn is None:
            return False, DB_DOWN

        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        INSERT_SCAN_SQL,
                        (
                            record["user_id"],
                            record["image_name"],
                            record["calorie_limit"],
                            record["diet"],
                            Jsonb(record["detected_items"]),
                        ),
                    )
                    scan_id = cursor.fetchone()["id"]

                    for recipe in record["accepted"] + record["rejected"]:
                        cursor.execute(
                            INSERT_RECIPE_SQL,
                            (
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
                            ),
                        )

            return True, scan_id

        except (psycopg.Error, KeyError, TypeError) as exc:
            logger.error("Could not save record: %s", exc)
            return False, "Your results could not be saved, but they are shown below."
        finally:
            conn.close()

    def load_recent(self, user_id: int, limit: int = 5) -> tuple[bool, list | str]:
        """Load recent scans and count accepted recipes for each scan."""
        conn = self._get_connection()
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

    def filter_recipes(
        self,
        user_id: int,
        diet: str | None = None,
        max_calories: int | None = None,
        status: str = "accepted",
    ) -> tuple[bool, list | str]:
        """Find saved recipes by status, diet and calorie ceiling."""
        conn = self._get_connection()
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



# Temporary compatibility layer:
# main.py and existing tests still call data_manager.function_name(...).
# We will remove these wrappers after updating the callers to use an instance.
_manager = PostgresDataManager()


def password_matches(password: str, stored_hash: str) -> bool:
    return _manager.password_matches(password, stored_hash)


def create_user(
    name: str,
    password: str,
    calorie_target: int = 2000,
    dietary_preference: str = "none",
) -> tuple[bool, int | str]:
    return _manager.create_user(name, password, calorie_target, dietary_preference)


def verify_login(name: str, password: str) -> tuple[bool, int | str]:
    return _manager.verify_login(name, password)


def get_user(user_id: int) -> tuple[bool, dict | None | str]:
    return _manager.get_user(user_id)


def update_user(
    user_id: int, calorie_target: int, dietary_preference: str
) -> tuple[bool, bool | str]:
    return _manager.update_user(user_id, calorie_target, dietary_preference)


def delete_user(user_id: int) -> tuple[bool, bool | str]:
    return _manager.delete_user(user_id)


def save_record(record: dict) -> tuple[bool, int | str]:
    return _manager.save_record(record)


def load_recent(user_id: int, limit: int = 5) -> tuple[bool, list | str]:
    return _manager.load_recent(user_id, limit)


def filter_recipes(
    user_id: int,
    diet: str | None = None,
    max_calories: int | None = None,
    status: str = "accepted",
) -> tuple[bool, list | str]:
    return _manager.filter_recipes(user_id, diet, max_calories, status)
