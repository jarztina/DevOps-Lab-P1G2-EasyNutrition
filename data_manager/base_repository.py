"""Parent class for every repository. Holds the database and opens connections."""


class BaseRepository:
    """Shared code for UserRepository, ScanRepository and RecipeRepository."""

    def __init__(self, database):
        # Encapsulation: the leading underscore means "private, do not touch from outside".
        self._database = database

    def _connect(self):
        """Return an open connection, or None when the database is down."""
        return self._database.connect()