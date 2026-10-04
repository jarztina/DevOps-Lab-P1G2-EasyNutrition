import bcrypt
import psycopg
from database.connection import get_connection
from psycopg.types.json import Jsonb


def create_user(name, password, calorie_target, dietary_preference):
    #Create a new user and store their profile in the database

    if not name.strip():
        raise ValueError("Name cannot be empty")

    if not password:
        raise ValueError("Password cannot be empty")

    if calorie_target <= 0:
        raise ValueError("Calorie target must be greater than 0")

    if not dietary_preference.strip():
        raise ValueError("Dietary preference cannot be empty")
    
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO users
                    (name, password_hash, calorie_target, dietary_preference)
                    VALUES (%s, %s, %s, %s)
                    RETURNING user_id;
                    """,
                    (name, password_hash, calorie_target, dietary_preference)
                )
            
                user_id = cursor.fetchone()[0]
                conn.commit()

                return user_id
            
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                return None
        

    finally:
        conn.close()

def verify_login(name, password):
    #Verify a user's login credentials

    if not name.strip():
        raise ValueError("Name cannot be empty")

    if not password:
        raise ValueError("Password cannot be empty")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, password_hash
                FROM users
                WHERE name = %s;
                """,
                (name,)
            )

            user = cursor.fetchone()

            if user is None:
                return None

            user_id, password_hash = user

            if bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8")
            ):
                return user_id

            return None

    finally:
        conn.close()

def get_user(user_id):
    #Retrieve a user's profile from the database

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, name, calorie_target, dietary_preference
                FROM users
                WHERE user_id = %s;
                """,
                (user_id,)
            )

            return cursor.fetchone()

    finally:
        conn.close()

def update_user(user_id, calorie_target, dietary_preference):
    #Update a user's calorie target and dietary preference

    if calorie_target <= 0:
        raise ValueError("Calorie target must be greater than 0")

    if not dietary_preference.strip():
        raise ValueError("Dietary preference cannot be empty")
    
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET calorie_target = %s,
                    dietary_preference = %s
                WHERE user_id = %s;
                """,
                (calorie_target, dietary_preference, user_id)
            )

            conn.commit()

            return cursor.rowcount > 0

    finally:
        conn.close()

def save_record(record):
    #Save one scan and all its recipes (accepted + rejected) in one transaction.
    #Returns (True, scan_id) on success, or (False, message) if it fails. 
    #Need to check this function
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cursor:
                #insert the scan, get its new id back
                cursor.execute(
                    """
                    INSERT INTO scans
                        (user_id, image_name, calorie_limit, diet, detected_items)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        record["user_id"],
                        record["image_name"],
                        record["calorie_limit"],
                        record["diet"],
                        Jsonb(record["detected_items"]),
                    ),
                )
                scan_id = cursor.fetchone()[0]

                #insert every recipe, linked to that scan
                for recipe in record["accepted"] + record["rejected"]:
                    cursor.execute(
                        """
                        INSERT INTO recipes
                            (scan_id, name, calories, status, score, leftovers_used,
                             reasons, ingredients_used, extra_ingredients, steps,
                             spoonacular_id, source_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            scan_id,
                            recipe["name"],
                            recipe.get("calories"),
                            recipe["status"],
                            recipe["score"],
                            recipe["leftovers_used"],
                            Jsonb(recipe["reasons"]),
                            Jsonb(recipe.get("ingredients_used", [])),
                            Jsonb(recipe.get("extra_ingredients", [])),
                            Jsonb(recipe.get("steps", [])),
                            recipe.get("spoonacular_id"),
                            recipe.get("source_url", ""),
                        ),
                    )

        return True, scan_id

    except (psycopg.Error, KeyError, TypeError) as exc:
        return False, "Your results could not be saved, but they are shown below."

    finally:
        conn.close()
