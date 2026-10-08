# data_manager.py - all PostgreSQL access. Plain SQL, no classes, no ORM.
import logging

import bcrypt
import psycopg
from psycopg.types.json import Jsonb

from database.connection import get_connection

logger = logging.getLogger(__name__)

DB_DOWN = "The database is unavailable right now."
MAX_PASSWORD_BYTES = 72          # bcrypt cannot use more than 72 bytes

INSERT_SCAN_SQL = """
INSERT INTO scans (user_id, image_name, calorie_limit, diet, detected_items)
VALUES (%s, %s, %s, %s, %s) RETURNING id
"""

INSERT_RECIPE_SQL = """
INSERT INTO recipes (scan_id, name, calories, status, score, leftovers_used,
                     reasons, ingredients_used, extra_ingredients, steps,
                     spoonacular_id, source_url)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


# True if the password matches the bcrypt hash. Never raises.
def password_matches(password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


# Register a user. Returns (True, user_id) or (False, message). Never raises.
def create_user(name: str, password: str, calorie_target: int = 2000,
                dietary_preference: str = "none") -> tuple[bool, int | str]:
    name = name.strip().lower()
    if not name:
        return False, "Name cannot be empty."
    if not password:
        return False, "Password cannot be empty."
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return False, "Password is too long."
    if calorie_target <= 0:
        return False, "Calorie target must be greater than 0."
    if not dietary_preference.strip():
        return False, "Dietary preference cannot be empty."
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    if conn is None:
        return False, DB_DOWN
    try:
        with conn:
            row = conn.execute(
                "INSERT INTO users (name, password_hash, calorie_target, dietary_preference) "
                "VALUES (%s, %s, %s, %s) RETURNING user_id",
                (name, password_hash, calorie_target, dietary_preference)).fetchone()
        return True, row["user_id"]
    except psycopg.errors.UniqueViolation:
        return False, "That name is already taken."
    except psycopg.Error as exc:
        logger.error("Could not create user: %s", exc)
        return False, "Could not create your account. Please try again."
    finally:
        conn.close()


# Check a login. Returns (True, user_id) or (False, message). Never raises.
def verify_login(name: str, password: str) -> tuple[bool, int | str]:
    name = name.strip().lower()
    if not name or not password:
        return False, "Please type your name and password."
    conn = get_connection()
    if conn is None:
        return False, DB_DOWN
    try:
        with conn:
            user = conn.execute(
                "SELECT user_id, password_hash FROM users WHERE name = %s",
                (name,)).fetchone()
    except psycopg.Error as exc:
        logger.error("Could not look up user: %s", exc)
        return False, "Could not check your login right now."
    finally:
        conn.close()
    if user is not None and password_matches(password, user["password_hash"]):
        return True, user["user_id"]
    return False, "Wrong name or password."


# Get a user's profile. Returns (True, row or None) or (False, message).
def get_user(user_id: int) -> tuple[bool, dict | None | str]:
    conn = get_connection()
    if conn is None:
        return False, DB_DOWN
    try:
        with conn:
            row = conn.execute(
                "SELECT user_id, name, calorie_target, dietary_preference "
                "FROM users WHERE user_id = %s", (user_id,)).fetchone()
        return True, row
    except psycopg.Error as exc:
        logger.error("Could not read user: %s", exc)
        return False, "Could not load your profile."
    finally:
        conn.close()


# Change a user's calorie target and diet. Returns (True, was_updated).
def update_user(user_id: int, calorie_target: int,
                dietary_preference: str) -> tuple[bool, bool | str]:
    if calorie_target <= 0:
        return False, "Calorie target must be greater than 0."
    if not dietary_preference.strip():
        return False, "Dietary preference cannot be empty."
    conn = get_connection()
    if conn is None:
        return False, DB_DOWN
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE users SET calorie_target = %s, dietary_preference = %s "
                "WHERE user_id = %s", (calorie_target, dietary_preference, user_id))
            updated = cursor.rowcount > 0
        return True, updated
    except psycopg.Error as exc:
        logger.error("Could not update user: %s", exc)
        return False, "Could not update your profile."
    finally:
        conn.close()


# Save one scan and all its recipes (accepted and rejected) in one transaction.
def save_record(record: dict) -> tuple[bool, int | str]:
    conn = get_connection()
    if conn is None:
        return False, DB_DOWN
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(INSERT_SCAN_SQL, (
                    record["user_id"], record["image_name"], record["calorie_limit"],
                    record["diet"], Jsonb(record["detected_items"])))
                scan_id = cursor.fetchone()["id"]
                for recipe in record["accepted"] + record["rejected"]:
                    cursor.execute(INSERT_RECIPE_SQL, (
                        scan_id, recipe["name"], recipe.get("calories"),
                        recipe["status"], recipe["score"], recipe["leftovers_used"],
                        Jsonb(recipe["reasons"]),
                        Jsonb(recipe.get("ingredients_used", [])),
                        Jsonb(recipe.get("extra_ingredients", [])),
                        Jsonb(recipe.get("steps", [])),
                        recipe.get("spoonacular_id"), recipe.get("source_url", "")))
        return True, scan_id
    except (psycopg.Error, KeyError, TypeError) as exc:
        logger.error("Could not save record: %s", exc)
        return False, "Your results could not be saved, but they are shown below."
    finally:
        conn.close()


# Load this user's newest scans, with a count of accepted recipes for each.
def load_recent(user_id: int, limit: int = 5) -> tuple[bool, list | str]:
    conn = get_connection()
    if conn is None:
        return False, DB_DOWN
    sql = """
        SELECT s.id, s.created_at, s.image_name, s.calorie_limit, s.diet,
               (SELECT COUNT(*) FROM recipes r
                 WHERE r.scan_id = s.id AND r.status = 'accepted') AS accepted_count
        FROM scans s WHERE s.user_id = %s ORDER BY s.created_at DESC LIMIT %s
    """
    try:
        with conn:
            rows = conn.execute(sql, (user_id, limit)).fetchall()
        return True, rows
    except psycopg.Error as exc:
        logger.error("Could not load recent scans: %s", exc)
        return False, "Could not load your recent scans."
    finally:
        conn.close()


# Find this user's saved recipes by status, diet and calorie ceiling.
def filter_recipes(user_id: int, diet: str | None = None, max_calories: int | None = None,
                   status: str = "accepted") -> tuple[bool, list | str]:
    conn = get_connection()
    if conn is None:
        return False, DB_DOWN
    # Fixed SQL text only. User values go ONLY through %s placeholders.
    sql = ("SELECT r.*, s.image_name, s.diet, s.created_at "
           "FROM recipes r JOIN scans s ON s.id = r.scan_id "
           "WHERE s.user_id = %s AND r.status = %s")
    params = [user_id, status]
    if diet and diet != "none":
        sql += " AND s.diet = %s"
        params.append(diet)
    if max_calories is not None:
        sql += " AND r.calories <= %s"
        params.append(max_calories)
    sql += " ORDER BY s.created_at DESC, r.score DESC, r.id LIMIT 100"
    try:
        with conn:
            rows = conn.execute(sql, params).fetchall()
        return True, rows
    except psycopg.Error as exc:
        logger.error("Could not filter recipes: %s", exc)
        return False, "Could not search your saved recipes."
    finally:
        conn.close()