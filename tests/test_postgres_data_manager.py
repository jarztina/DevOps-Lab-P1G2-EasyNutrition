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