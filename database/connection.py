import logging
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()
logger = logging.getLogger(__name__)


def get_connection():
    """Open a connection (rows come back as dicts). Returns None if the DB is down."""
    try:
        return psycopg.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            row_factory=dict_row,
            connect_timeout=5,
        )
    except psycopg.OperationalError as exc:
        logger.error("Database connection failed: %s", exc)
        return None