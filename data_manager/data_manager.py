from abc import ABC, abstractmethod

# Every method returns (ok, value). ok is False when value is an error message.


class DataManager(ABC):
    # ---- users -------------------------------------------------------------
    @abstractmethod
    def create_user(
        self, name: str, password: str,
        calorie_target: int = 2000, dietary_preference: str = "none",
    ) -> tuple[bool, int | str]:
        """Create a user account."""

    @abstractmethod
    def verify_login(self, name: str, password: str) -> tuple[bool, int | str]:
        """Verify a user's login credentials."""

    @abstractmethod
    def get_user(self, user_id: int) -> tuple[bool, dict | None | str]:
        """Retrieve a user's profile."""

    @abstractmethod
    def update_user(
        self, user_id: int, calorie_target: int, dietary_preference: str
    ) -> tuple[bool, bool | str]:
        """Update a user's profile."""

    @abstractmethod
    def delete_user(self, user_id: int) -> tuple[bool, bool | str]:
        """Delete a user account."""

    # ---- scans -------------------------------------------------------------
    @abstractmethod
    def save_record(self, record: dict) -> tuple[bool, int | str]:
        """Save a scan and its recipes. Returns the new scan id."""

    @abstractmethod
    def load_recent(self, user_id: int, limit: int = 5) -> tuple[bool, list | str]:
        """Load a user's most recent scans."""

    @abstractmethod
    def get_scan(self, user_id: int, scan_id: int) -> tuple[bool, dict | None | str]:
        """Load one scan with its accepted and rejected recipes (None if not found)."""

    @abstractmethod
    def delete_scan(self, user_id: int, scan_id: int) -> tuple[bool, bool | str]:
        """Delete one scan and its recipes. True if a scan was deleted."""

    @abstractmethod
    def replace_scan_results(
        self, user_id: int, scan_id: int, record: dict
    ) -> tuple[bool, bool | str]:
        """Swap a scan's ingredients and recipes after the user fixed the AI."""

    # ---- recipes -----------------------------------------------------------
    @abstractmethod
    def filter_recipes(
        self, user_id: int, diet: str | None = None,
        max_calories: int | None = None, status: str = "accepted",
    ) -> tuple[bool, list | str]:
        """Filter a user's saved recipes."""

    @abstractmethod
    def get_recipe(self, user_id: int, recipe_id: int) -> tuple[bool, dict | None | str]:
        """Load one saved recipe (None if not found)."""

    @abstractmethod
    def update_recipe(
        self, user_id: int, recipe_id: int, changes: dict
    ) -> tuple[bool, bool | str]:
        """Edit notes or ingredient lists of a saved recipe. True if it changed."""

    @abstractmethod
    def delete_recipe(self, user_id: int, recipe_id: int) -> tuple[bool, bool | str]:
        """Delete one saved recipe. True if a recipe was deleted."""