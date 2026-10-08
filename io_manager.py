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
    return True, value


def validate_diet(text: str) -> tuple[bool, str]:
    """Accept only the four diet values agreed upon by the team."""
    value = str(text).strip().lower()
    if value not in ALLOWED_DIETS:
        return False, "Diet must be one of: " + ", ".join(ALLOWED_DIETS) + "."
    return True, value


def detect_media_type(data: bytes) -> str | None:
    """Identify JPEG or PNG using its file signature rather than its name."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def validate_upload(file_storage: FileStorage | None) -> tuple[bool, dict | str]:
    """Validate a photo's size and signature and return bytes and a safe name."""
    if file_storage is None or not file_storage.filename:
        return False, "Please choose a photo."
    try:
        # Read once, with a limit so oversized files cannot fill memory.
        data = file_storage.read(MAX_UPLOAD_BYTES + 1)
    except (OSError, ValueError):
        logger.warning("Could not read uploaded photo.")
        return False, "Could not read the photo. Please choose it again."
    if len(data) == 0:
        return False, "The file is empty."
    if len(data) > MAX_UPLOAD_BYTES:
        return False, "Photo is too big (max 5 MB)."
    media_type = detect_media_type(data)
    if media_type is None:
        return False, "Only JPG or PNG photos are allowed."
    name = secure_filename(file_storage.filename) or "upload"
    return True, {"image_bytes": data, "media_type": media_type, "image_name": name}


def collect_input(
    form: Mapping[str, str], files: Mapping[str, FileStorage]
) -> tuple[bool, dict | list[str]]:
    """Validate calories, diet and photo together and collect every error."""
    errors = []
    ok_cal, calories = validate_calories(form.get("calorie_limit", ""))
    if not ok_cal:
        errors.append(calories)
    ok_diet, diet = validate_diet(form.get("diet", "none"))
    if not ok_diet:
        errors.append(diet)
    ok_img, image = validate_upload(files.get("image"))
    if not ok_img:
        errors.append(image)
    if errors:
        return False, errors
    data = dict(image)
    data["calorie_limit"] = calories
    data["diet"] = diet
    return True, data


def parse_history_filters(args: Mapping[str, str]) -> tuple[bool, dict | str]:
    """Validate history URL filters using the data_manager argument names."""
    filters = {"diet": None, "max_calories": None, "status": "accepted"}
    diet = args.get("diet", "").strip().lower()
    if diet:
        ok, value = validate_diet(diet)
        if not ok:
            return False, value
        filters["diet"] = value
    max_cal = args.get("max_calories", "").strip()
    if max_cal:
        ok, value = validate_calories(max_cal)
        if not ok:
            return False, value
        filters["max_calories"] = value
    return True, filters


def render_login(errors: list[str] | None = None) -> str:
    """Render the login form and any validation errors."""
    return render_template("login.html", errors=errors or [], user=current_user())


def render_register(errors: list[str] | None = None) -> str:
    """Render the registration form and any validation errors."""
    return render_template("register.html", errors=errors or [], user=current_user())


def render_home(
    errors: list[str] | None = None, recent: list[dict] | None = None
) -> str:
    """Render the photo upload form, errors and recent scans."""
    return render_template(
        "index.html", errors=errors or [], recent=recent or [],
        diets=ALLOWED_DIETS, user=current_user()
    )


def render_results(record: dict) -> str:
    """Render detected food, accepted recipes and rejection reasons."""
    return render_template("results.html", record=record, user=current_user())


def render_history(rows: list[dict], filters: dict) -> str:
    """Render saved recipes and the history filter form."""
    return render_template(
        "history.html", rows=rows, filters=filters,
        diets=ALLOWED_DIETS, user=current_user()
    )


def render_error(message: str) -> str:
    """Render a friendly error page without exposing a traceback."""
    logger.warning("Showing error page: %s", message)
    return render_template("error.html", message=message, user=current_user())
