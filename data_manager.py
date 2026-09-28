import bcrypt
from database.connection import get_connection


def create_user(name, password, calorie_target, dietary_preference):
    # Create a new user and store their profile in the database

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
