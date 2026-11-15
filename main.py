"""Starts the app. It builds the four managers and the web app, nothing else."""
import logging

from dotenv import load_dotenv

from ai_manager.ai_manager import AIManager
from data_manager.postgres_data_manager import PostgresDataManager
from database.database import Database
from database.schema_migrator import SchemaMigrator
from io_manager.io_manager import IOManager
from logic_manager.logic_manager import LogicManager
from web_app import WebApp


class AppFactory:
    """Builds the finished Flask app. gunicorn runs 'main:app'."""

    @staticmethod
    def create():
        load_dotenv()
        logging.basicConfig(level=logging.INFO)
        database = Database()
        ok, message = SchemaMigrator(database).run()   # adds the notes column if missing
        if not ok:
            logging.warning("Schema update skipped: %s", message)
        web_app = WebApp(
            io=IOManager(),
            ai=AIManager(),
            logic=LogicManager(),
            data=PostgresDataManager(database),
        )
        return web_app.flask_app


app = AppFactory.create()