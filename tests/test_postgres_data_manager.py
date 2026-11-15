"""Tests for the PostgresDataManager facade"""
import pytest

from data_manager.data_manager import DataManager
from data_manager.postgres_data_manager import PostgresDataManager
from data_manager.recipe_repository import RecipeRepository
from data_manager.scan_repository import ScanRepository
from data_manager.user_repository import UserRepository
from tests.fakes import FakeDatabase, make_conn


def test_data_manager_is_abstract():
    with pytest.raises(TypeError):
        DataManager()


def test_postgres_data_manager_implements_the_contract():
    assert isinstance(PostgresDataManager(FakeDatabase(None)), DataManager)


def test_postgres_data_manager_covers_every_abstract_method():
    assert PostgresDataManager.__abstractmethods__ == frozenset()


def test_it_owns_one_repository_of_each_kind():
    manager = PostgresDataManager(FakeDatabase(None))
    assert isinstance(manager._users, UserRepository)
    assert isinstance(manager._scans, ScanRepository)
    assert isinstance(manager._recipes, RecipeRepository)

def test_calls_are_handed_to_the_right_repository():
    class Spy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: (True, f"{name}{args}")
    manager = PostgresDataManager(FakeDatabase(None))
    manager._users, manager._scans, manager._recipes = Spy(), Spy(), Spy()
    assert manager.verify_login("a", "b") == (True, "verify_login('a', 'b')")
    assert manager.get_scan(1, 2) == (True, "get_scan(1, 2)")
    assert manager.delete_recipe(1, 3) == (True, "delete_recipe(1, 3)")


def test_it_works_end_to_end_with_a_fake_database():
    manager = PostgresDataManager(FakeDatabase(make_conn(rowcount=1)))
    assert manager.delete_scan(1, 7) == (True, True)