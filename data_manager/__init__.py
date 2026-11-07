from .data_manager import DataManager
from .postgres_data_manager import (
    PostgresDataManager,
    DB_DOWN,
    MAX_PASSWORD_BYTES,
)

from database.connection import get_connection


# Temporary compatibility layer
_manager = PostgresDataManager(
    connection_factory=lambda: get_connection()
)


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