from unittest.mock import MagicMock

import bcrypt
import psycopg
import pytest

import data_manager


# ---- a tiny fake database (functions only, no OOP, per the build guide) ---
# data_manager reaches PostgreSQL only through get_connection(), so we hand it
# a fake connection built from MagicMock and the tests need no real database.
# fake_db() returns a connection whose execute/cursor reply with the rows we
# preload: one -> fetchone, many -> fetchall, rowcount -> UPDATE result. Pass
# error= to make the next execute raise, standing in for a database failure.

def fake_db(one=None, many=None, rowcount=0, error=None):
    cursor = MagicMock(name="cursor")
    cursor.fetchone.return_value = one
    cursor.fetchall.return_value = many if many is not None else []
    cursor.rowcount = rowcount
    cursor.__enter__.return_value = cursor       # used as: with conn.cursor() as cur
    cursor.__exit__.return_value = False         # must be False so errors propagate

    conn = MagicMock(name="conn")
    conn.execute.return_value = cursor           # conn.execute(...).fetchone()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn           # used as: with conn
    conn.__exit__.return_value = False
    if error is not None:
        conn.execute.side_effect = error
        cursor.execute.side_effect = error
    return conn


def use(monkeypatch, conn):
    """Point data_manager at this fake connection (pass None for 'DB down')."""
    monkeypatch.setattr(data_manager, "get_connection", lambda: conn)
    return conn


RECORD = {
    "user_id": 1, "image_name": "lunch.jpg", "calorie_limit": 600, "diet": "none",
    "detected_items": [{"name": "rice", "confidence": 0.9}],
    "accepted": [{
        "name": "Egg fried rice", "calories": 450.0, "status": "accepted",
        "score": 85.0, "leftovers_used": 2, "reasons": [],
        "ingredients_used": ["rice", "egg"], "extra_ingredients": ["oil"],
        "steps": ["Cook"], "spoonacular_id": 101, "source_url": "https://x",
    }],
    "rejected": [{
        "name": "Pork bowl", "calories": 900.0, "status": "rejected",
        "score": 0.0, "leftovers_used": 1, "reasons": ["too many calories"],
    }],
}


# ---- password_matches -----------------------------------------------------

def test_password_matches_true_for_right_password_false_for_wrong():
    hashed = bcrypt.hashpw(b"swordfish", bcrypt.gensalt()).decode("utf-8")
    assert data_manager.password_matches("swordfish", hashed) is True
    assert data_manager.password_matches("wrong", hashed) is False


def test_password_matches_handles_a_broken_hash_without_raising():
    assert data_manager.password_matches("anything", "not-a-real-hash") is False


# ---- create_user ----------------------------------------------------------

@pytest.mark.parametrize("name, password, calories, diet, message", [
    ("", "pw", 2000, "none", "Name cannot be empty."),
    ("ann", "", 2000, "none", "Password cannot be empty."),
    ("ann", "x" * 73, 2000, "none", "Password is too long."),
    ("ann", "pw", 0, "none", "Calorie target must be greater than 0."),
    ("ann", "pw", 2000, "  ", "Dietary preference cannot be empty."),
])
def test_create_user_rejects_bad_input_before_touching_db(name, password, calories, diet, message):
    assert data_manager.create_user(name, password, calories, diet) == (False, message)


def test_create_user_saves_and_returns_the_new_id(monkeypatch):
    conn = use(monkeypatch, fake_db(one={"user_id": 42}))
    ok, result = data_manager.create_user("  Ann  ", "pw", 1800, "vegan")
    assert ok is True and result == 42
    params = conn.execute.call_args.args[1]
    assert params[0] == "ann"                    # name is trimmed and lower-cased
    assert conn.close.called                     # connection is always closed


def test_create_user_reports_db_down(monkeypatch):
    use(monkeypatch, None)
    assert data_manager.create_user("ann", "pw") == (False, data_manager.DB_DOWN)


def test_create_user_detects_a_duplicate_name(monkeypatch):
    use(monkeypatch, fake_db(error=psycopg.errors.UniqueViolation()))
    ok, message = data_manager.create_user("ann", "pw")
    assert ok is False and "already taken" in message


def test_create_user_handles_a_database_error(monkeypatch):
    use(monkeypatch, fake_db(error=psycopg.Error("boom")))
    ok, message = data_manager.create_user("ann", "pw")
    assert ok is False and "try again" in message


# ---- verify_login ---------------------------------------------------------

def test_verify_login_needs_both_fields():
    assert data_manager.verify_login("", "pw")[0] is False
    assert data_manager.verify_login("ann", "")[0] is False


def test_verify_login_reports_db_down(monkeypatch):
    use(monkeypatch, None)
    assert data_manager.verify_login("ann", "pw") == (False, data_manager.DB_DOWN)


def test_verify_login_accepts_the_correct_password(monkeypatch):
    hashed = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8")
    use(monkeypatch, fake_db(one={"user_id": 7, "password_hash": hashed}))
    assert data_manager.verify_login("Ann", "pw") == (True, 7)


def test_verify_login_rejects_a_wrong_password(monkeypatch):
    hashed = bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8")
    use(monkeypatch, fake_db(one={"user_id": 7, "password_hash": hashed}))
    ok, message = data_manager.verify_login("ann", "nope")
    assert ok is False and message == "Wrong name or password."


def test_verify_login_rejects_an_unknown_user(monkeypatch):
    use(monkeypatch, fake_db(one=None))
    ok, message = data_manager.verify_login("ghost", "pw")
    assert ok is False and message == "Wrong name or password."


def test_verify_login_handles_a_database_error(monkeypatch):
    use(monkeypatch, fake_db(error=psycopg.Error("boom")))
    ok, message = data_manager.verify_login("ann", "pw")
    assert ok is False and "check your login" in message


# ---- get_user -------------------------------------------------------------

def test_get_user_reports_db_down(monkeypatch):
    use(monkeypatch, None)
    assert data_manager.get_user(1) == (False, data_manager.DB_DOWN)


def test_get_user_returns_the_row(monkeypatch):
    row = {"user_id": 1, "name": "ann", "calorie_target": 2000, "dietary_preference": "none"}
    use(monkeypatch, fake_db(one=row))
    assert data_manager.get_user(1) == (True, row)


def test_get_user_missing_user_is_not_an_error(monkeypatch):
    use(monkeypatch, fake_db(one=None))
    assert data_manager.get_user(999) == (True, None)


def test_get_user_handles_a_database_error(monkeypatch):
    use(monkeypatch, fake_db(error=psycopg.Error("boom")))
    ok, message = data_manager.get_user(1)
    assert ok is False and "load your profile" in message


# ---- update_user ----------------------------------------------------------

def test_update_user_rejects_bad_input():
    assert data_manager.update_user(1, 0, "none")[0] is False
    assert data_manager.update_user(1, 2000, " ")[0] is False


def test_update_user_reports_db_down(monkeypatch):
    use(monkeypatch, None)
    assert data_manager.update_user(1, 2000, "none") == (False, data_manager.DB_DOWN)


def test_update_user_reports_a_row_was_changed(monkeypatch):
    use(monkeypatch, fake_db(rowcount=1))
    assert data_manager.update_user(1, 2000, "none") == (True, True)


def test_update_user_returns_false_when_no_such_user(monkeypatch):
    use(monkeypatch, fake_db(rowcount=0))
    assert data_manager.update_user(999, 2000, "none") == (True, False)


def test_update_user_handles_a_database_error(monkeypatch):
    use(monkeypatch, fake_db(error=psycopg.Error("boom")))
    ok, message = data_manager.update_user(1, 2000, "none")
    assert ok is False and "update your profile" in message


# ---- save_record ----------------------------------------------------------

def test_save_record_reports_db_down(monkeypatch):
    use(monkeypatch, None)
    assert data_manager.save_record(RECORD) == (False, data_manager.DB_DOWN)


def test_save_record_inserts_the_scan_then_every_recipe(monkeypatch):
    conn = use(monkeypatch, fake_db(one={"id": 7}))
    ok, scan_id = data_manager.save_record(RECORD)
    assert ok is True and scan_id == 7
    cursor = conn.cursor.return_value
    # one scan insert, then one insert per accepted and rejected recipe
    assert cursor.execute.call_count == 1 + len(RECORD["accepted"]) + len(RECORD["rejected"])
    assert conn.close.called

def test_save_record_survives_a_malformed_record(monkeypatch):
    use(monkeypatch, fake_db(one={"id": 7}))
    broken = dict(RECORD)
    broken.pop("detected_items")        # missing key -> KeyError inside the transaction
    ok, message = data_manager.save_record(broken)
    assert ok is False and "could not be saved" in message


def test_save_record_handles_a_database_error(monkeypatch):
    use(monkeypatch, fake_db(one={"id": 7}, error=psycopg.Error("boom")))
    ok, message = data_manager.save_record(RECORD)
    assert ok is False and "could not be saved" in message


# ---- load_recent ----------------------------------------------------------

def test_load_recent_reports_db_down(monkeypatch):
    use(monkeypatch, None)
    assert data_manager.load_recent(1) == (False, data_manager.DB_DOWN)


def test_load_recent_returns_rows_and_passes_the_limit(monkeypatch):
    rows = [{"id": 2}, {"id": 1}]
    conn = use(monkeypatch, fake_db(many=rows))
    ok, result = data_manager.load_recent(1, limit=3)
    assert ok is True and result == rows
    assert conn.execute.call_args.args[1] == (1, 3)


def test_load_recent_handles_a_database_error(monkeypatch):
    use(monkeypatch, fake_db(error=psycopg.Error("boom")))
    ok, message = data_manager.load_recent(1)
    assert ok is False and "recent scans" in message


# ---- filter_recipes -------------------------------------------------------

def test_filter_recipes_reports_db_down(monkeypatch):
    use(monkeypatch, None)
    assert data_manager.filter_recipes(1) == (False, data_manager.DB_DOWN)


def test_filter_recipes_basic_query_has_no_optional_clauses(monkeypatch):
    conn = use(monkeypatch, fake_db(many=[]))
    ok, _ = data_manager.filter_recipes(1)
    assert ok is True
    sql, params = conn.execute.call_args.args
    assert "s.diet = %s" not in sql and "r.calories <= %s" not in sql
    assert params == [1, "accepted"]


def test_filter_recipes_adds_diet_and_calorie_filters(monkeypatch):
    conn = use(monkeypatch, fake_db(many=[]))
    data_manager.filter_recipes(1, diet="vegan", max_calories=500, status="rejected")
    sql, params = conn.execute.call_args.args
    assert "s.diet = %s" in sql and "r.calories <= %s" in sql
    assert params == [1, "rejected", "vegan", 500]


def test_filter_recipes_treats_none_diet_as_no_filter(monkeypatch):
    conn = use(monkeypatch, fake_db(many=[]))
    data_manager.filter_recipes(1, diet="none")
    sql, params = conn.execute.call_args.args
    assert "s.diet = %s" not in sql and params == [1, "accepted"]


def test_filter_recipes_sends_user_values_as_parameters_not_sql(monkeypatch):
    conn = use(monkeypatch, fake_db(many=[]))
    attack = "vegan'; DROP TABLE users; --"
    data_manager.filter_recipes(1, diet=attack)
    sql, params = conn.execute.call_args.args
    assert "DROP TABLE" not in sql       # never concatenated into the query text
    assert attack in params              # travels safely as a bound parameter


def test_filter_recipes_handles_a_database_error(monkeypatch):
    use(monkeypatch, fake_db(error=psycopg.Error("boom")))
    ok, message = data_manager.filter_recipes(1)
    assert ok is False and "saved recipes" in message

# ---- delete_user -----------------------------------------------------------

def test_delete_user_reports_db_down(monkeypatch):
    use(monkeypatch, None)
    assert data_manager.delete_user(1) == (False, data_manager.DB_DOWN)


def test_delete_user_deletes_an_existing_user(monkeypatch):
    conn = use(monkeypatch, fake_db(rowcount=1))
    assert data_manager.delete_user(1) == (True, True)
    sql, params = conn.execute.call_args.args
    assert "DELETE FROM USERS" in sql.upper()
    assert params == (1,)
    assert conn.close.called


def test_delete_user_returns_false_when_user_does_not_exist(monkeypatch):
    conn = use(monkeypatch, fake_db(rowcount=0))
    assert data_manager.delete_user(999) == (True, False)
    assert conn.close.called


def test_delete_user_handles_a_database_error(monkeypatch):
    conn = use(monkeypatch, fake_db(error=psycopg.Error("boom")))
    ok, message = data_manager.delete_user(1)
    assert ok is False
    assert isinstance(message, str)
    assert conn.close.called

# ---- OOP structure ---------------------------------------------------------

def test_data_manager_is_abstract():
    with pytest.raises(TypeError):
        data_manager.DataManager()


def test_postgres_data_manager_implements_the_contract():
    manager = data_manager.PostgresDataManager()
    assert isinstance(manager, data_manager.DataManager)


def test_module_level_wrapper_delegates_to_manager(monkeypatch):
    class FakeManager:
        def create_user(
            self, name, password, calorie_target=2000, dietary_preference="none"
        ):
            return True, 123

    monkeypatch.setattr(data_manager, "_manager", FakeManager())
    assert data_manager.create_user("ann", "pw") == (True, 123)