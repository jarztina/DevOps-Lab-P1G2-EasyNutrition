"""The web app: every Flask route is a method of one class. No business logic here."""
import logging
import os
import secrets

from flask import Flask, request

from io_manager.constants import MAX_UPLOAD_BYTES

logger = logging.getLogger(__name__)


class WebApp:
    """Glues the four managers together. It decides the ORDER of calls, nothing else."""

    def __init__(self, io, ai, logic, data):
        # Aggregation: AppFactory builds the managers and hands them in.
        self._io = io
        self._ai = ai
        self._logic = logic
        self._data = data
        self.flask_app = self._build_flask_app()

    # ---- setup ---------------------------------------------------------------
    def _build_flask_app(self) -> Flask:
        app = Flask(__name__)
        app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
        if not os.environ.get("SECRET_KEY"):
            logger.warning("SECRET_KEY is not set: logins will reset when the app restarts.")
        self._register_routes(app)
        app.register_error_handler(413, self.too_big)
        app.register_error_handler(500, self.server_error)
        return app

    def _register_routes(self, app: Flask) -> None:
        both = ["GET", "POST"]
        rules = [
            ("/register", "register", self.register, both),
            ("/login", "login", self.login, both),
            ("/logout", "logout", self.logout, ["POST"]),
            ("/", "home", self.home, ["GET"]),
            ("/analyse", "analyse", self.analyse, ["POST"]),
            ("/history", "history", self.history, ["GET"]),
            ("/scan/<int:scan_id>", "view_scan", self.view_scan, ["GET"]),
            ("/scan/<int:scan_id>/fix", "fix_scan", self.fix_scan, both),
            ("/scan/<int:scan_id>/delete", "delete_scan", self.delete_scan, ["POST"]),
            ("/recipe/<int:recipe_id>/edit", "edit_recipe", self.edit_recipe, both),
            ("/recipe/<int:recipe_id>/delete", "delete_recipe", self.delete_recipe, ["POST"]),
        ]
        for path, endpoint, view, methods in rules:
            app.add_url_rule(path, endpoint=endpoint, view_func=view, methods=methods)

    def _login_required(self):
        """Return the logged-in user, or None (the route then redirects to login)."""
        return self._io.current_user()

    # ---- accounts ------------------------------------------------------------
    def register(self):
        if request.method == "GET":
            return self._io.render_register()
        ok, creds = self._io.collect_credentials(request.form, is_register=True)
        if not ok:
            return self._io.render_register(errors=creds), 400
        ok, user_id = self._data.create_user(creds["username"], creds["password"])
        if not ok:
            return self._io.render_register(errors=[user_id]), 400
        self._io.login_user(user_id, creds["username"])
        return self._io.redirect_to("home")

    def login(self):
        if request.method == "GET":
            return self._io.render_login()
        ok, creds = self._io.collect_credentials(request.form)
        if not ok:
            return self._io.render_login(errors=creds), 400
        ok, user_id = self._data.verify_login(creds["username"], creds["password"])
        if not ok:
            return self._io.render_login(errors=[user_id]), 401
        self._io.login_user(user_id, creds["username"])
        return self._io.redirect_to("home")

    def logout(self):
        self._io.logout_user()
        return self._io.redirect_to("login")

    # ---- the main flow -------------------------------------------------------
    def home(self):
        user = self._login_required()
        if user is None:
            return self._io.redirect_to("login")
        ok, recent = self._data.load_recent(user["id"], 5)
        if not ok:
            logger.error("Failed to load recent scans: %s", recent)
            return self._io.render_home(errors=[recent], recent=[]), 503
        return self._io.render_home(recent=recent)

    def analyse(self):
        user = self._login_required()
        if user is None:
            return self._io.redirect_to("login")
        ok, data = self._io.collect_input(request.form, request.files)
        if not ok:
            return self._io.render_home(errors=data), 400
        ok, ai_data = self._ai.analyse_image(data["image_bytes"], data["media_type"])
        if not ok:
            return self._io.render_error(ai_data), 502
        record = self._logic.process_ai_result(ai_data, data["calorie_limit"], data["diet"])
        record["image_name"] = data["image_name"]
        record["user_id"] = user["id"]
        ok, saved = self._data.save_record(record)
        record["save_warning"] = "" if ok else saved
        record["scan_id"] = saved if ok else None
        return self._io.render_results(record)

    def history(self):
        user = self._login_required()
        if user is None:
            return self._io.redirect_to("login")
        ok, filters = self._io.parse_history_filters(request.args)
        if not ok:
            return self._io.render_error(filters), 400
        ok, rows = self._data.filter_recipes(user_id=user["id"], **filters)
        if not ok:
            return self._io.render_error(rows), 503
        return self._io.render_history(rows, filters)

    # ---- scans: open, fix (new feature), delete -----------------------------
    def _load_scan(self, user_id: int, scan_id: int):
        """Return (scan, None) or (None, an error page tuple)."""
        ok, scan = self._data.get_scan(user_id, scan_id)
        if not ok:
            return None, (self._io.render_error(scan), 503)
        if scan is None:
            return None, (self._io.render_error("That scan was not found."), 404)
        return scan, None

    def view_scan(self, scan_id: int):
        user = self._login_required()
        if user is None:
            return self._io.redirect_to("login")
        scan, problem = self._load_scan(user["id"], scan_id)
        if problem:
            return problem
        return self._io.render_results(scan)

    def fix_scan(self, scan_id: int):
        user = self._login_required()
        if user is None:
            return self._io.redirect_to("login")
        scan, problem = self._load_scan(user["id"], scan_id)
        if problem:
            return problem
        if request.method == "GET":
            return self._io.render_fix(scan)
        ok, edits = self._io.collect_corrections(request.form)
        if not ok:
            return self._io.render_fix(scan, errors=edits), 400
        items = self._logic.build_corrected_items(edits)
        ok, recipes = self._ai.search_recipes(self._ai.pick_query_ingredients(items))
        if not ok:
            return self._io.render_error(recipes), 502
        record = self._logic.process_ai_result(
            {"detected_items": items, "recipes": recipes}, scan["calorie_limit"], scan["diet"])
        ok, saved = self._data.replace_scan_results(user["id"], scan_id, record)
        if not ok:
            return self._io.render_error(saved), 503
        if not saved:
            return self._io.render_error("That scan was not found."), 404
        record["scan_id"] = scan_id
        record["changes"] = self._logic.summarise_changes(scan, record)
        return self._io.render_results(record)

    def delete_scan(self, scan_id: int):
        user = self._login_required()
        if user is None:
            return self._io.redirect_to("login")
        ok, deleted = self._data.delete_scan(user["id"], scan_id)
        if not ok:
            return self._io.render_error(deleted), 503
        if not deleted:
            return self._io.render_error("That scan was not found."), 404
        return self._io.redirect_to("home")

    # ---- saved recipes: edit and delete (advanced feature) ------------------
    def edit_recipe(self, recipe_id: int):
        user = self._login_required()
        if user is None:
            return self._io.redirect_to("login")
        ok, recipe = self._data.get_recipe(user["id"], recipe_id)
        if not ok:
            return self._io.render_error(recipe), 503
        if recipe is None:
            return self._io.render_error("That recipe was not found."), 404
        if request.method == "GET":
            return self._io.render_recipe_edit(recipe)
        ok, changes = self._io.collect_recipe_edit(request.form)
        if not ok:
            return self._io.render_recipe_edit(recipe, errors=changes), 400
        ok, updated = self._data.update_recipe(user["id"], recipe_id, changes)
        if not ok:
            return self._io.render_recipe_edit(recipe, errors=[updated]), 400
        return self._io.redirect_to("history")

    def delete_recipe(self, recipe_id: int):
        user = self._login_required()
        if user is None:
            return self._io.redirect_to("login")
        ok, deleted = self._data.delete_recipe(user["id"], recipe_id)
        if not ok:
            return self._io.render_error(deleted), 503
        if not deleted:
            return self._io.render_error("That recipe was not found."), 404
        return self._io.redirect_to("history")

    # ---- error pages ---------------------------------------------------------
    def too_big(self, _error):
        return self._io.render_error("Photo is too big (max 5 MB)."), 413

    def server_error(self, _error):
        logger.exception("Unexpected error")
        return self._io.render_error("Something went wrong. Please try again later."), 500