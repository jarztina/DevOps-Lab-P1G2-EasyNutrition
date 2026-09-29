import bcrypt
from database.connection import get_connection


def create_user(name, password, calorie_target, dietary_preference):
    #Create a new user and store their profile in the database

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
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

    finally:
        conn.close()

def verify_login(name, password):
    #Verify a user's login credentials

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
