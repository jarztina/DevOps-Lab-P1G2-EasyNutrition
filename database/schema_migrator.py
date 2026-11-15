"""Adds columns that Part 2 needs to a database that already exists."""
import logging

import psycopg

from data_manager.constants import DB_DOWN

logger = logging.getLogger(__name__)


class SchemaMigrator:
    """Runs safe 'IF NOT EXISTS' changes so old Docker volumes keep working."""

    STATEMENTS = (
        "ALTER TABLE recipes ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT ''",
    )

    def __init__(self, database):
        self._database = database

    def run(self) -> tuple[bool, str]:
        """Apply every statement. Safe to run again and again."""
        conn = self._database.connect()
        if conn is None:
            return False, DB_DOWN
        try:
            with conn:
                for statement in self.STATEMENTS:
                    conn.execute(statement)
            return True, "Database is up to date."
        except psycopg.Error as exc:
            logger.error("Schema update failed: %s", exc)
            return False, "Could not update the database."
        finally:
            conn.close()