"""Tests for RecipeRepository. No real database needed."""
import psycopg

from tests.fakes import FakeDatabase, make_conn
from data_manager.constants import DB_DOWN
from data_manager.recipe_repository import RecipeRepository


def test_filter_recipes_reports_db_down():
    repo = RecipeRepository(FakeDatabase(None))
    assert repo.filter_recipes(1) == (False, DB_DOWN)


def test_filter_recipes_basic_query_has_no_optional_clauses():
    conn = make_conn(many=[])
    repo = RecipeRepository(FakeDatabase(conn))
    ok, _ = repo.filter_recipes(1)
    assert ok is True
    sql, params = conn.execute.call_args.args
    assert "s.diet = %s" not in sql and "r.calories <= %s" not in sql
    assert params == [1, "accepted"]


def test_filter_recipes_adds_diet_and_calorie_filters():
    conn = make_conn(many=[])
    repo = RecipeRepository(FakeDatabase(conn))
    repo.filter_recipes(1, diet="vegan", max_calories=500, status="rejected")
    sql, params = conn.execute.call_args.args
    assert "s.diet = %s" in sql and "r.calories <= %s" in sql
    assert params == [1, "rejected", "vegan", 500]


def test_filter_recipes_treats_none_diet_as_no_filter():
    conn = make_conn(many=[])
    repo = RecipeRepository(FakeDatabase(conn))
    repo.filter_recipes(1, diet="none")
    sql, params = conn.execute.call_args.args
    assert "s.diet = %s" not in sql and params == [1, "accepted"]


def test_filter_recipes_sends_user_values_as_parameters_not_sql():
    conn = make_conn(many=[])
    repo = RecipeRepository(FakeDatabase(conn))
    attack = "vegan'; DROP TABLE users; --"
    repo.filter_recipes(1, diet=attack)
    sql, params = conn.execute.call_args.args
    assert "DROP TABLE" not in sql
    assert attack in params


def test_filter_recipes_handles_a_database_error():
    repo = RecipeRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.filter_recipes(1)
    assert ok is False and "saved recipes" in message