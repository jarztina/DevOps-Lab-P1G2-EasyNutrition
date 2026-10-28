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