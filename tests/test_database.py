"""Tests for the Database class"""
import psycopg

from database import database as database_module
from database.database import Database


def test_connect_returns_none_when_the_database_is_down(monkeypatch):
    def boom(**kwargs):
        raise psycopg.OperationalError("no server")
    monkeypatch.setattr(database_module.psycopg, "connect", boom)
    assert Database({"host": "x"}).connect() is None


def test_connect_passes_the_settings_to_psycopg(monkeypatch):
    seen = {}
    def fake_connect(**kwargs):
        seen.update(kwargs)
        return "a connection"
    monkeypatch.setattr(database_module.psycopg, "connect", fake_connect)
    assert Database({"host": "db", "dbname": "n"}).connect() == "a connection"
    assert seen["host"] == "db" and seen["dbname"] == "n" and seen["connect_timeout"] == 5


def test_settings_default_to_environment_variables(monkeypatch):
    monkeypatch.setenv("DB_HOST", "from-env")
    assert Database()._read_settings()["host"] == "from-env"