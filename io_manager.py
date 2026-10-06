"""Handle browser input, validation, login sessions and HTML output."""

import logging
import re
from collections.abc import Mapping

from flask import Response, redirect, render_template, session, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Keep these values and dictionary keys consistent with the team contract.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MIN_CALORIES = 100
MAX_CALORIES = 3000
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
ALLOWED_DIETS = ("none", "vegetarian", "vegan", "halal")


def validate_username(text: str) -> tuple[bool, str]:
    """Check for 3-30 letters, numbers or underscores and return lowercase."""
    value = str(text).strip()
    if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", value):
        return False, "Name must be 3-30 letters, numbers or underscores."
    return True, value.lower()


def validate_password(text: str) -> tuple[bool, str]:
    """Check that a new password contains 8-128 characters."""
    value = str(text)
    if len(value) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(value) > MAX_PASSWORD_LENGTH:
        return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    return True, value


def collect_credentials(
    form: Mapping[str, str], is_register: bool = False
) -> tuple[bool, dict | list[str]]:
    """Collect validated login or registration credentials, or all form errors."""
    errors = []
    ok_name, username = validate_username(form.get("username", ""))
    if not ok_name:
        errors.append(username)

    password = form.get("password", "")
    if is_register:
        ok_pw, pw_message = validate_password(password)
        if not ok_pw:
            errors.append(pw_message)
        elif password != form.get("confirm_password", ""):
            errors.append("The two passwords do not match.")
    elif password == "":
        errors.append("Please type your password.")

    if errors:
        return False, errors
    return True, {"username": username, "password": password}


def login_user(user_id: int, username: str) -> None:
    """Clear the previous session and remember only the user ID and name."""
    session.clear()
    session["user_id"] = user_id
    session["username"] = username


def logout_user() -> None:
    """Clear the login session."""
    session.clear()


def current_user() -> dict | None:
    """Return the logged-in user's ID and name, or None when logged out."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return {"id": user_id, "username": session.get("username", "")}


def redirect_to(endpoint: str) -> Response:
    """Redirect the browser to a Flask endpoint such as home or login."""
    return redirect(url_for(endpoint))


def validate_calories(text: str) -> tuple[bool, int | str]:
    """Convert the calorie limit to a whole number between 100 and 3000."""
    try:
        value = int(str(text).strip())
    except (ValueError, TypeError):
        return False, "Calories must be a whole number, for example 500."
    if value < MIN_CALORIES or value > MAX_CALORIES:
        return False, f"Calories must be between {MIN_CALORIES} and {MAX_CALORIES}."