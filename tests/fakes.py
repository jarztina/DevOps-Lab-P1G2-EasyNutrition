"""Tiny fakes so tests never need a real database or a live AI."""
from unittest.mock import MagicMock


def make_conn(one=None, many=None, rowcount=0, error=None):
    """A fake database connection.

    one      -> what fetchone() returns
    many     -> what fetchall() returns
    rowcount -> what an UPDATE or DELETE reports
    error    -> an exception to raise on the next execute (simulates a DB failure)
    """
    cursor = MagicMock(name="cursor")
    cursor.fetchone.return_value = one
    cursor.fetchall.return_value = many if many is not None else []
    cursor.rowcount = rowcount
    cursor.__enter__.return_value = cursor    # used as: with conn.cursor() as cur
    cursor.__exit__.return_value = False      # False so errors still propagate

    conn = MagicMock(name="conn")
    conn.execute.return_value = cursor        # conn.execute(...).fetchone()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn        # used as: with conn
    conn.__exit__.return_value = False
    if error is not None:
        conn.execute.side_effect = error
        cursor.execute.side_effect = error
    return conn


class FakeDatabase:
    """Stands in for database.database.Database. connect() hands back our fake conn."""

    def __init__(self, conn):
        self._conn = conn

    def connect(self):
        return self._conn   # pass None as conn to pretend the database is down