# main.py - glue only. Calls the four managers in order. No business logic here.
import logging
import os
import secrets

from dotenv import load_dotenv
from flask import Flask, request

import ai_manager
import data_manager
import io_manager
import logic_manager

load_dotenv()
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = io_manager.MAX_UPLOAD_BYTES
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
if not os.environ.get("SECRET_KEY"):
    logging.warning("SECRET_KEY is not set: logins will reset when the app restarts.")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return io_manager.render_register()
    ok, creds = io_manager.collect_credentials(request.form, is_register=True)
    if not ok:
        return io_manager.render_register(errors=creds), 400
    ok, user_id = data_manager.create_user(creds["username"], creds["password"])
    if not ok:
        return io_manager.render_register(errors=[user_id]), 400
    io_manager.login_user(user_id, creds["username"])
    return io_manager.redirect_to("home")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return io_manager.render_login()
    ok, creds = io_manager.collect_credentials(request.form)
    if not ok:
        return io_manager.render_login(errors=creds), 400
    ok, user_id = data_manager.verify_login(creds["username"], creds["password"])
    if not ok:
        return io_manager.render_login(errors=[user_id]), 401
    io_manager.login_user(user_id, creds["username"])
    return io_manager.redirect_to("home")


@app.route("/logout", methods=["POST"])
def logout():
    io_manager.logout_user()
    return io_manager.redirect_to("login")


@app.route("/")
def home():
    user = io_manager.current_user()
    if user is None:
        return io_manager.redirect_to("login")
    ok, recent = data_manager.load_recent(user["id"], 5)
    return io_manager.render_home(recent=recent if ok else [])


@app.route("/analyse", methods=["POST"])
def analyse():
    user = io_manager.current_user()
    if user is None:
        return io_manager.redirect_to("login")
    ok, data = io_manager.collect_input(request.form, request.files)
    if not ok:
        return io_manager.render_home(errors=data), 400
    ok, ai_data = ai_manager.analyse_image(data["image_bytes"], data["media_type"])
    if not ok:
        return io_manager.render_error(ai_data), 502
    record = logic_manager.process_ai_result(ai_data, data["calorie_limit"], data["diet"])
    record["image_name"] = data["image_name"]
    record["user_id"] = user["id"]
    ok, saved = data_manager.save_record(record)
    record["save_warning"] = "" if ok else saved
    return io_manager.render_results(record)


@app.route("/history")
def history():
    user = io_manager.current_user()
    if user is None:
        return io_manager.redirect_to("login")
    ok, filters = io_manager.parse_history_filters(request.args)
    if not ok:
        return io_manager.render_error(filters), 400
    ok, rows = data_manager.filter_recipes(user_id=user["id"], **filters)
    if not ok:
        return io_manager.render_error(rows), 503
    return io_manager.render_history(rows, filters)


@app.errorhandler(413)
def too_big(_error):
    return io_manager.render_error("Photo is too big (max 5 MB)."), 413