"""Opens PostgreSQL connections"""
import logging
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()
logger = logging.getLogger(__name__)


class Database:
    def __init__(self, settings: dict | None = None):
        self._settings = settings

    def _read_settings(self) -> dict:
        if self._settings is not None:
            return self._settings
        return {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
        }

    def connect(self):
        """Open a connection (rows come back as dicts). Returns None if the DB is down."""
        try:
            return psycopg.connect(
                **self._read_settings(), row_factory=dict_row, connect_timeout=5
            )
        except psycopg.OperationalError as exc:
            logger.error("Database connection failed: %s", exc)
            return None