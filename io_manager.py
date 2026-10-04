import logging
import re
from flask import redirect, render_template, session, url_for
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Constants agreed upon across managers
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_CALORIES = 100
MAX_CALORIES = 3000
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
ALLOWED_DIETS = ("none", "vegetarian", "vegan", "halal")

def validate_username(text: str) -> tuple[bool, str]:
    value = str(text).strip()
    # Name must be 3-30 letters, numbers or underscores. 
    if not re.fullmatch(r"^[A-Za-z0-9_]{3,30}$", value):
        return False,
    return True, value.lower()

def validate_password(text: str) -> tuple[bool, str]:
    value = str(text)
    if len(value) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(value) > MAX_PASSWORD_LENGTH:
        return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    return True, value

def collect_credentials(form, is_register: bool = False) -> tuple[bool, dict | list]:
    errors = []

    ok_name, username = validate_username(form.get("username", ""))
    if not ok_name:
        errors.append(username)

    password = form.get("password", "")
    if is_register:
        ok_pw, pw_msg = validate_password(password)
        if not ok_pw:
            errors.append(pw_msg)
        elif password != form.get("confirm_password", ""):
            errors.append("The two passwords do not match.")
    elif password == "":
        errors.append("Please type your password.")

    if errors:
        return False, errors
    return True, {"username": username, "password": password}