"""Tests for ScanRepository (Jovan). No real database needed."""
import psycopg

from tests.fakes import FakeDatabase, make_conn
from data_manager.constants import DB_DOWN
from data_manager.scan_repository import ScanRepository

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


def test_save_record_reports_db_down():
    repo = ScanRepository(FakeDatabase(None))
    assert repo.save_record(RECORD) == (False, DB_DOWN)


def test_save_record_inserts_the_scan_then_every_recipe():
    conn = make_conn(one={"id": 7})
    repo = ScanRepository(FakeDatabase(conn))
    ok, scan_id = repo.save_record(RECORD)
    assert ok is True and scan_id == 7
    cursor = conn.cursor.return_value
    # one scan insert, then one insert per accepted and rejected recipe
    assert cursor.execute.call_count == 1 + len(RECORD["accepted"]) + len(RECORD["rejected"])
    assert conn.close.called


def test_save_record_survives_a_malformed_record():
    repo = ScanRepository(FakeDatabase(make_conn(one={"id": 7})))
    broken = dict(RECORD)
    broken.pop("detected_items")        # missing key -> KeyError inside the transaction
    ok, message = repo.save_record(broken)
    assert ok is False and "could not be saved" in message


def test_save_record_handles_a_database_error():
    repo = ScanRepository(FakeDatabase(make_conn(one={"id": 7}, error=psycopg.Error("boom"))))
    ok, message = repo.save_record(RECORD)
    assert ok is False and "could not be saved" in message


# ---- load_recent ----------------------------------------------------------

def test_load_recent_reports_db_down():
    repo = ScanRepository(FakeDatabase(None))
    assert repo.load_recent(1) == (False, DB_DOWN)


def test_load_recent_returns_rows_and_passes_the_limit():
    rows = [{"id": 2}, {"id": 1}]
    conn = make_conn(many=rows)
    repo = ScanRepository(FakeDatabase(conn))
    ok, result = repo.load_recent(1, limit=3)
    assert ok is True and result == rows
    assert conn.execute.call_args.args[1] == (1, 3)


def test_load_recent_handles_a_database_error():
    repo = ScanRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.load_recent(1)
    assert ok is False and "recent scans" in message


# ---- get_scan ---------------------------------------------

SCAN_ROW = {
    "id": 7, "created_at": "2026-11-10", "image_name": "lunch.jpg",
    "calorie_limit": 600, "diet": "none", "detected_items": [{"name": "rice"}],
}


def test_get_scan_reports_db_down():
    repo = ScanRepository(FakeDatabase(None))
    assert repo.get_scan(1, 7) == (False, DB_DOWN)


def test_get_scan_returns_none_when_not_found_or_not_owned():
    repo = ScanRepository(FakeDatabase(make_conn(one=None)))
    assert repo.get_scan(1, 999) == (True, None)


def test_get_scan_splits_recipes_into_accepted_and_rejected():
    rows = [
        {"id": 1, "status": "accepted", "name": "Egg rice"},
        {"id": 2, "status": "rejected", "name": "Pork bowl"},
    ]
    conn = make_conn(one=SCAN_ROW, many=rows)
    repo = ScanRepository(FakeDatabase(conn))
    ok, record = repo.get_scan(1, 7)
    assert ok is True and record["scan_id"] == 7
    assert [r["name"] for r in record["accepted"]] == ["Egg rice"]
    assert [r["name"] for r in record["rejected"]] == ["Pork bowl"]
    assert conn.close.called


def test_get_scan_always_checks_the_owner():
    conn = make_conn(one=SCAN_ROW)
    ScanRepository(FakeDatabase(conn)).get_scan(5, 7)
    sql, params = conn.execute.call_args_list[0].args
    assert "user_id = %s" in sql and params == (7, 5)


def test_get_scan_handles_a_database_error():
    repo = ScanRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.get_scan(1, 7)
    assert ok is False and "open this scan" in message


# ---- delete_scan ------------------------------------------

def test_delete_scan_reports_db_down():
    assert ScanRepository(FakeDatabase(None)).delete_scan(1, 7) == (False, DB_DOWN)


def test_delete_scan_true_when_deleted_false_when_not_found():
    assert ScanRepository(FakeDatabase(make_conn(rowcount=1))).delete_scan(1, 7) == (True, True)
    assert ScanRepository(FakeDatabase(make_conn(rowcount=0))).delete_scan(1, 7) == (True, False)


def test_delete_scan_only_deletes_the_users_own_scan():
    conn = make_conn(rowcount=1)
    ScanRepository(FakeDatabase(conn)).delete_scan(5, 7)
    sql, params = conn.execute.call_args.args
    assert "user_id = %s" in sql and params == (7, 5)


def test_delete_scan_handles_a_database_error():
    repo = ScanRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.delete_scan(1, 7)
    assert ok is False and "delete this scan" in message



# ---- replace_scan_results ---------------------------------

def test_replace_reports_db_down():
    repo = ScanRepository(FakeDatabase(None))
    assert repo.replace_scan_results(1, 7, RECORD) == (False, DB_DOWN)


def test_replace_updates_scan_deletes_old_recipes_and_inserts_new_ones():
    conn = make_conn(rowcount=1)
    repo = ScanRepository(FakeDatabase(conn))
    assert repo.replace_scan_results(1, 7, RECORD) == (True, True)
    cursor = conn.cursor.return_value
    # 1 UPDATE + 1 DELETE + one INSERT per recipe
    assert cursor.execute.call_count == 2 + len(RECORD["accepted"]) + len(RECORD["rejected"])
    assert conn.close.called


def test_replace_does_nothing_when_scan_is_not_the_users():
    conn = make_conn(rowcount=0)
    repo = ScanRepository(FakeDatabase(conn))
    assert repo.replace_scan_results(1, 999, RECORD) == (True, False)
    assert conn.cursor.return_value.execute.call_count == 1   # only the UPDATE ran


def test_replace_survives_a_malformed_record():
    repo = ScanRepository(FakeDatabase(make_conn(rowcount=1)))
    ok, message = repo.replace_scan_results(1, 7, {"accepted": []})
    assert ok is False and "corrections" in message


def test_replace_handles_a_database_error():
    repo = ScanRepository(FakeDatabase(make_conn(error=psycopg.Error("boom"))))
    ok, message = repo.replace_scan_results(1, 7, RECORD)
    assert ok is False and "corrections" in message