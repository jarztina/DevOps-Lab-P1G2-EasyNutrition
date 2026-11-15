import logging
import re
from abc import ABC, abstractmethod
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from .constants import (
    ALLOWED_DIETS, MAX_CALORIES, MAX_INGREDIENT_LENGTH, MAX_NOTES_LENGTH,
    MAX_PASSWORD_LENGTH, MAX_UPLOAD_BYTES, MIN_CALORIES, MIN_PASSWORD_LENGTH,
)
logger = logging.getLogger(__name__)

class Validator(ABC):
    """Every validator answers (ok, cleaned value) or (False, error message)."""
    @abstractmethod
    def validate(self, value) -> tuple[bool, object]:
        """Check one value."""

class UsernameValidator(Validator):
    """3-30 letters, numbers or underscores. Returns the name in lowercase."""
    def validate(self, value):
        text = str(value).strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", text):
            return False, "Name must be 3-30 letters, numbers or underscores."
        return True, text.lower()

class PasswordValidator(Validator):
    """A new password must be 8-72 characters."""
    def validate(self, value):
        text = str(value)
        if len(text) < MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        if len(text) > MAX_PASSWORD_LENGTH:
            return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        return True, text

class CaloriesValidator(Validator):
    """A whole number from 100 to 3000."""
    def validate(self, value):
        try:
            number = int(str(value).strip())
        except (ValueError, TypeError):
            return False, "Calories must be a whole number, for example 500."
        if number < MIN_CALORIES or number > MAX_CALORIES:
            return False, f"Calories must be between {MIN_CALORIES} and {MAX_CALORIES}."
        return True, number

class DietValidator(Validator):
    """Only the four diets the team agreed on."""
    def validate(self, value):
        text = str(value).strip().lower()
        if text not in ALLOWED_DIETS:
            return False, "Diet must be one of: " + ", ".join(ALLOWED_DIETS) + "."
        return True, text

class UploadValidator(Validator):
    """A JPEG or PNG photo, not empty, not over 5 MB."""
    @staticmethod
    def detect_media_type(data: bytes) -> str | None:
        """Identify JPEG or PNG by its file signature, not by its name."""
        if data.startswith(b"\xff\xd8\xff"):
             return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        return None

    def validate(self, value: FileStorage | None):
        if value is None or not value.filename:
            return False, "Please choose a photo."
        try:
            # Read once, with a limit so oversized files cannot fill memory.
            data = value.read(MAX_UPLOAD_BYTES + 1)
        except (OSError, ValueError):
            logger.warning("Could not read uploaded photo.")
            return False, "Could not read the photo. Please choose it again."
        if len(data) == 0:
            return False, "The file is empty."
        if len(data) > MAX_UPLOAD_BYTES:
            return False, "Photo is too big (max 5 MB)."
        media_type = self.detect_media_type(data)
        if media_type is None:
            return False, "Only JPG or PNG photos are allowed."
        name = secure_filename(value.filename) or "upload"
        return True, {"image_bytes": data, "media_type": media_type, "image_name": name}

class TextListValidator(Validator):
    """NEW (Part 2): a list of short texts, like ingredients. Blank lines are dropped."""
    def __init__(self, label: str, max_items: int, max_length: int = MAX_INGREDIENT_LENGTH,
                 allow_empty: bool = True):
        self._label = label
        self._max_items = max_items
        self._max_length = max_length
        self._allow_empty = allow_empty
    def validate(self, value):
        cleaned = []
        for entry in value:
            text = " ".join(str(entry).split())
            if not text:
                continue
            if len(text) > self._max_length:
                short = text[:15]
                return False, f"{self._label} '{short}...' is too long (max {self._max_length})."
            if text.lower() not in [c.lower() for c in cleaned]:
                cleaned.append(text)
        if not cleaned and not self._allow_empty:
            return False, f"Please keep at least one {self._label.lower()}."
        if len(cleaned) > self._max_items:
            return False, f"Please use at most {self._max_items} items in {self._label.lower()}."
        return True, cleaned
    
class NotesValidator(Validator):
    """NEW (Part 2): a short note for a saved recipe (can be empty)."""
    def validate(self, value):
        text = str(value).strip()
        if len(text) > MAX_NOTES_LENGTH:
            return False, f"Notes must be at most {MAX_NOTES_LENGTH} characters."
        return True, text