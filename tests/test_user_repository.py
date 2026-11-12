"""Tests for UserRepository"""
import bcrypt
import psycopg
import pytest

from tests.fakes import FakeDatabase, make_conn
from data_manager.constants import DB_DOWN
from data_manager.user_repository import UserRepository


def test_password_matches_true_for_right_password_false_for_wrong():
    hashed = bcrypt.hashpw(b"swordfish", bcrypt.gensalt()).decode("utf-8")
    assert UserRepository.password_matches("swordfish", hashed) is True
    assert UserRepository.password_matches("wrong", hashed) is False


def test_password_matches_handles_a_broken_hash_without_raising():
    assert UserRepository.password_matches("anything", "not-a-real-hash") is False


# ---- create_user ----------------------------------------------------------

@pytest.mark.parametrize("name, password, calories, diet, message", [
    ("", "pw", 2000, "none", "Name cannot be empty."),
    ("ann", "", 2000, "none", "Password cannot be empty."),
    ("ann", "x" * 73, 2000, "none", "Password is too long."),
    ("ann", "pw", 0, "none", "Calorie target must be greater than 0."),
    ("ann", "pw", 2000, " ", "Dietary preference cannot be empty."),
])
def test_create_user_rejects_bad_input_before_touching_db(name, password, calories, diet, message):
    repo = UserRepository(FakeDatabase(make_conn()))
    assert repo.create_user(name, password, calories, diet) == (False, message)


def test_create_user_saves_and_returns_the_new_id():
    conn = make_conn(one={"user_id": 42})
    repo = UserRepository(FakeDatabase(conn))
    ok, result = repo.create_user(" Ann ", "pw", 1800, "vegan")
    assert ok is True and result == 42
    params = conn.execute.call_args.args[1]
    assert params[0] == "ann"                   
    assert conn.close.called                


def test_create_user_reports_db_down():
    repo = UserRepository(FakeDatabase(None))
    assert repo.create_user("ann", "pw") == (False, DB_DOWN)


def test_create_user_detects_a_duplicate_name():
    repo = UserRepository(FakeDatabase(make_conn(error=psycopg.errors.UniqueViolation())))
    ok, message = repo.create_user("ann", "pw")
    assert ok is False and "already taken" in message


def test_create_user_handles_a_database_error():
    repo = UserRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.create_user("ann", "pw")
    assert ok is False and "try again" in message