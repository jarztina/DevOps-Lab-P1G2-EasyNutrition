"""Tests for RecipeRepository. No real database needed."""
import psycopg
import pytest

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


# ---- get_recipe (new in Part 2) -------------------------------------------

def test_get_recipe_reports_db_down():
    assert RecipeRepository(FakeDatabase(None)).get_recipe(1, 5) == (False, DB_DOWN)


def test_get_recipe_returns_the_row_or_none():
    row = {"id": 5, "name": "Egg rice", "notes": ""}
    assert RecipeRepository(FakeDatabase(make_conn(one=row))).get_recipe(1, 5) == (True, row)
    assert RecipeRepository(FakeDatabase(make_conn(one=None))).get_recipe(1, 9) == (True, None)


def test_get_recipe_checks_the_owner():
    conn = make_conn(one=None)
    RecipeRepository(FakeDatabase(conn)).get_recipe(3, 5)
    sql, params = conn.execute.call_args.args
    assert "s.user_id = %s" in sql and params == (5, 3)


def test_get_recipe_handles_a_database_error():
    repo = RecipeRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.get_recipe(1, 5)
    assert ok is False and "open this recipe" in message



# ---- update_recipe (new in Part 2) ----------------------------------------

@pytest.mark.parametrize("changes", [
    {},                                       # nothing to change
    "notes",                                  # not a dict
    {"name": "Hacked"},                       # field not allowed
    {"calories": 1},                          # field not allowed
    {"notes": 123},                           # wrong type
    {"notes": "x" * 501},                     # too long
    {"extra_ingredients": "salt"},            # must be a list
    {"extra_ingredients": ["salt", ""]},      # empty item
    {"extra_ingredients": ["a"] * 31},        # too many items
    {"ingredients_used": ["x" * 101]},        # item too long
])
def test_update_recipe_rejects_bad_changes_before_touching_the_db(changes):
    conn = make_conn(rowcount=1)
    repo = RecipeRepository(FakeDatabase(conn))
    ok, message = repo.update_recipe(1, 5, changes)
    assert ok is False and isinstance(message, str)
    assert not conn.execute.called