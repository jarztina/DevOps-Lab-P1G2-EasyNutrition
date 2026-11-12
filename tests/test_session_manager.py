"""Tests for SessionManager (Gabriel). Needs a tiny Flask app for the session."""

from flask import Flask

from io_manager.session_manager import SessionManager

app = Flask(__name__)
app.config["SECRET_KEY"] = "test-secret"
app.add_url_rule("/", endpoint="home", view_func=lambda: "home")
app.add_url_rule("/login", endpoint="login", view_func=lambda: "login")
app.add_url_rule("/scan/<int:scan_id>", endpoint="view_scan",
                 view_func=lambda scan_id: "scan")


def test_login_logout_and_current_user():
    sessions = SessionManager()
    with app.test_request_context("/"):
        assert sessions.current_user() is None
        sessions.login_user(10, "tester")
        assert sessions.current_user() == {"id": 10, "username": "tester"}
        sessions.logout_user()
        assert sessions.current_user() is None


def test_login_clears_the_old_session_first():
    from flask import session

    sessions = SessionManager()
    with app.test_request_context("/"):
        session["junk"] = "old data"
        sessions.login_user(1, "ann")
        assert "junk" not in session


def test_redirect_to_an_endpoint_with_a_value():
    sessions = SessionManager()
    with app.test_request_context("/"):
        response = sessions.redirect_to("login")
        assert response.status_code == 302 and response.location.endswith("/login")
        assert sessions.redirect_to("view_scan", scan_id=7).location.endswith("/scan/7")