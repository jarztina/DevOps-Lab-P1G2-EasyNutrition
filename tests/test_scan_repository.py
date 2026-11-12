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

