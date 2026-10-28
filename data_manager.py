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