"""Tests for SchemaMigrator (Hanni). No real database needed."""
import psycopg

from data_manager.constants import DB_DOWN
from database.schema_migrator import SchemaMigrator
from tests.fakes import FakeDatabase, make_conn


def test_run_reports_db_down():
    assert SchemaMigrator(FakeDatabase(None)).run() == (False, DB_DOWN)


def test_run_executes_every_statement_and_closes_the_connection():
    conn = make_conn()
    ok, _ = SchemaMigrator(FakeDatabase(conn)).run()
    assert ok is True
    assert conn.execute.call_count == len(SchemaMigrator.STATEMENTS)
    assert conn.close.called


def test_the_notes_column_is_added_safely():
    joined = " ".join(SchemaMigrator.STATEMENTS)
    assert "ADD COLUMN IF NOT EXISTS notes" in joined    # safe to run twice


def test_run_handles_a_database_error():
    ok, message = SchemaMigrator(FakeDatabase(make_conn(error=psycopg.Error("boom")))).run()
    assert ok is False and "Could not update" in message