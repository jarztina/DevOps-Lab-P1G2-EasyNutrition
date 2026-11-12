"""Everything about user accounts: register, login, profile, delete."""
import logging

import bcrypt
import psycopg

from .base_repository import BaseRepository
from .constants import DB_DOWN, MAX_PASSWORD_BYTES

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Reads and writes the users table."""

    @staticmethod
    def password_matches(password: str, stored_hash: str) -> bool:
        """Check whether a password matches its bcrypt hash."""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                stored_hash.encode("utf-8")
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
        """Register a user."""

        if not isinstance(name, str) or not isinstance(password, str):
            return False, "Name and password must be text."
        name = name.strip().lower()

        if not name:
            return False, "Name cannot be empty."
        if not password:
            return False, "Password cannot be empty."
        if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
            return False, "Password is too long."

        if (
            not isinstance(calorie_target, (int, float))
            or isinstance(calorie_target, bool)
        ):
            return False, "Calorie target must be a number."

        if calorie_target <= 0:
            return False, "Calorie target must be greater than 0."

        if not isinstance(dietary_preference, str):
            return False, "Dietary preference must be text."

        if not dietary_preference.strip():
            return False, "Dietary preference cannot be empty."

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        conn = self._connect()

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

    def verify_login(
        self, name: str, password: str
    ) -> tuple[bool, int | str]:
        """Check a user's login credentials."""

        if not isinstance(name, str) or not isinstance(password, str):
            return False, "Please type your name and password."

        name = name.strip().lower()

        if not name or not password:
            return False, "Please type your name and password."

        conn = self._connect()

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