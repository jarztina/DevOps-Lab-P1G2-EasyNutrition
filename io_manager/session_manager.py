"""Login sessions and redirects (Flask session cookie)."""

from flask import Response, redirect, session, url_for


class SessionManager:
    """Remembers who is logged in. Only the user id and name are stored."""

    def login_user(self, user_id: int, username: str) -> None:
        """Clear the previous session and remember only the user ID and name."""
        session.clear()
        session["user_id"] = user_id
        session["username"] = username

    def logout_user(self) -> None:
        """Clear the login session."""
        session.clear()

    def current_user(self) -> dict | None:
        """Return the logged-in user's ID and name, or None when logged out."""
        user_id = session.get("user_id")
        if user_id is None:
            return None
        return {"id": user_id, "username": session.get("username", "")}

    def redirect_to(self, endpoint: str, **values) -> Response:
        """Redirect the browser to a Flask endpoint such as home or login."""
        return redirect(url_for(endpoint, **values))