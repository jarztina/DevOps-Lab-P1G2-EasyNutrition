"""The PostgreSQL Data Manager. It owns three repositories and hands work to them."""
from database.database import Database

from .data_manager import DataManager
from .recipe_repository import RecipeRepository
from .scan_repository import ScanRepository
from .user_repository import UserRepository


class PostgresDataManager(DataManager):
    """One front door for all data work (composition: it creates and owns its parts)."""

    def __init__(self, database=None):
        self._database = database or Database()
        self._users = UserRepository(self._database)
        self._scans = ScanRepository(self._database)
        self._recipes = RecipeRepository(self._database)

    # ---- users -------------------------------------------------------------
    def create_user(self, name, password, calorie_target=2000, dietary_preference="none"):
        return self._users.create_user(name, password, calorie_target, dietary_preference)

    def verify_login(self, name, password):
        return self._users.verify_login(name, password)

    def get_user(self, user_id):
        return self._users.get_user(user_id)

    def update_user(self, user_id, calorie_target, dietary_preference):
        return self._users.update_user(user_id, calorie_target, dietary_preference)

    def delete_user(self, user_id):
        return self._users.delete_user(user_id)

    # ---- scans -------------------------------------------------------------
    def save_record(self, record):
        return self._scans.save_record(record)

    def load_recent(self, user_id, limit=5):
        return self._scans.load_recent(user_id, limit)

    def get_scan(self, user_id, scan_id):
        return self._scans.get_scan(user_id, scan_id)

    def delete_scan(self, user_id, scan_id):
        return self._scans.delete_scan(user_id, scan_id)

    def replace_scan_results(self, user_id, scan_id, record):
        return self._scans.replace_scan_results(user_id, scan_id, record)

    # ---- recipes -----------------------------------------------------------
    def filter_recipes(self, user_id, diet=None, max_calories=None, status="accepted"):
        return self._recipes.filter_recipes(user_id, diet, max_calories, status)

    def get_recipe(self, user_id, recipe_id):
        return self._recipes.get_recipe(user_id, recipe_id)

    def update_recipe(self, user_id, recipe_id, changes):
        return self._recipes.update_recipe(user_id, recipe_id, changes)

    def delete_recipe(self, user_id, recipe_id):
        return self._recipes.delete_recipe(user_id, recipe_id)