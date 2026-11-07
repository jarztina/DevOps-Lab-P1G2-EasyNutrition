from abc import ABC, abstractmethod

# The contract that all Data Manager implementations must follow.
class DataManager(ABC):
    """Abstract interface for EasyNutrition data operations."""

    @abstractmethod
    def create_user(
        self,
        name: str,
        password: str,
        calorie_target: int = 2000,
        dietary_preference: str = "none",
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

    @abstractmethod
    def save_record(self, record: dict) -> tuple[bool, int | str]:
        """Save a scan and its associated recipes."""

    @abstractmethod
    def load_recent(self, user_id: int, limit: int = 5) -> tuple[bool, list | str]:
        """Load a user's most recent scans."""

    @abstractmethod
    def filter_recipes(
        self,
        user_id: int,
        diet: str | None = None,
        max_calories: int | None = None,
        status: str = "accepted",
    ) -> tuple[bool, list | str]:
        """Filter a user's saved recipes."""