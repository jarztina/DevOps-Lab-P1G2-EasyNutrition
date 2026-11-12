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


# ---- verify_login ---------------------------------------------------------

def test_verify_login_needs_both_fields():
    repo = UserRepository(FakeDatabase(make_conn()))
    assert repo.verify_login("", "pw")[0] is False
    assert repo.verify_login("ann", "")[0] is False


def test_verify_login_reports_db_down():
    repo = UserRepository(FakeDatabase(None))
    assert repo.verify_login("ann", "pw") == (False, DB_DOWN)


def test_verify_login_accepts_the_correct_password():
    hashed = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8")
    repo = UserRepository(FakeDatabase(make_conn(one={"user_id": 7, "password_hash": hashed})))
    assert repo.verify_login("Ann", "pw") == (True, 7)


def test_verify_login_rejects_a_wrong_password():
    hashed = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8")
    repo = UserRepository(FakeDatabase(make_conn(one={"user_id": 7, "password_hash": hashed})))
    ok, message = repo.verify_login("ann", "nope")
    assert ok is False and message == "Wrong name or password."


def test_verify_login_rejects_an_unknown_user():
    repo = UserRepository(FakeDatabase(make_conn(one=None)))
    ok, message = repo.verify_login("ghost", "pw")
    assert ok is False and message == "Wrong name or password."


def test_verify_login_handles_a_database_error():
    repo = UserRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.verify_login("ann", "pw")
    assert ok is False and "check your login" in message


# ---- get_user -------------------------------------------------------------

def test_get_user_reports_db_down():
    repo = UserRepository(FakeDatabase(None))
    assert repo.get_user(1) == (False, DB_DOWN)


def test_get_user_returns_the_row():
    row = {"user_id": 1, "name": "ann", "calorie_target": 2000, "dietary_preference": "none"}
    repo = UserRepository(FakeDatabase(make_conn(one=row)))
    assert repo.get_user(1) == (True, row)


def test_get_user_missing_user_is_not_an_error():
    repo = UserRepository(FakeDatabase(make_conn(one=None)))
    assert repo.get_user(999) == (True, None)


def test_get_user_handles_a_database_error():
    repo = UserRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.get_user(1)
    assert ok is False and "load your profile" in message


# ---- update_user ----------------------------------------------------------

def test_update_user_rejects_bad_input():
    repo = UserRepository(FakeDatabase(make_conn()))
    assert repo.update_user(1, 0, "none")[0] is False
    assert repo.update_user(1, 2000, " ")[0] is False


def test_update_user_reports_db_down():
    repo = UserRepository(FakeDatabase(None))
    assert repo.update_user(1, 2000, "none") == (False, DB_DOWN)


def test_update_user_reports_a_row_was_changed():
    repo = UserRepository(FakeDatabase(make_conn(rowcount=1)))
    assert repo.update_user(1, 2000, "none") == (True, True)


def test_update_user_returns_false_when_no_such_user():
    repo = UserRepository(FakeDatabase(make_conn(rowcount=0)))
    assert repo.update_user(999, 2000, "none") == (True, False)


def test_update_user_handles_a_database_error():
    repo = UserRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.update_user(1, 2000, "none")
    assert ok is False and "update your profile" in message


# ---- delete_user ----------------------------------------------------------

def test_delete_user_reports_db_down():
    repo = UserRepository(FakeDatabase(None))
    assert repo.delete_user(1) == (False, DB_DOWN)


def test_delete_user_deletes_an_existing_user():
    conn = make_conn(rowcount=1)
    repo = UserRepository(FakeDatabase(conn))
    assert repo.delete_user(1) == (True, True)
    sql, params = conn.execute.call_args.args
    assert "DELETE FROM USERS" in sql.upper()
    assert params == (1,)
    assert conn.close.called


def test_delete_user_returns_false_when_user_does_not_exist():
    conn = make_conn(rowcount=0)
    repo = UserRepository(FakeDatabase(conn))
    assert repo.delete_user(999) == (True, False)
    assert conn.close.called


def test_delete_user_handles_a_database_error():
    conn = make_conn(error=psycopg.Error("boom"))
    repo = UserRepository(FakeDatabase(conn))
    ok, message = repo.delete_user(1)
    assert ok is False
    assert isinstance(message, str)
    assert conn.close.called