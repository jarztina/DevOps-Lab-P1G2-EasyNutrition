"""Tests for WebApp (Justin). The four managers are replaced by fakes, so no AI, no database."""
import io

import pytest

from ai_manager.ai_service import AIService
from data_manager.data_manager import DataManager
from io_manager.io_manager import IOManager
from logic_manager.logic_manager import LogicManager
from web_app import WebApp

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 50
SCAN = {"scan_id": 7, "calorie_limit": 500, "diet": "none", "created_at": "2026-11-10",
        "image_name": "a.png",
        "detected_items": [{"name": "chicken", "quantity": "1", "confidence": 0.9}],
        "accepted": [], "rejected": []}
RECIPE = {"id": 5, "scan_id": 7, "name": "Egg rice", "calories": 400.0, "score": 80.0,
          "ingredients_used": ["rice"], "extra_ingredients": ["oil"], "steps": [],
          "notes": "", "diet": "none", "created_at": "2026-11-10"}
EGG_RICE = {"name": "Egg rice", "ingredients_used": ["rice", "egg"], "extra_ingredients": ["oil"],
            "calories": 400.0, "steps": ["Cook"], "vegetarian": True, "vegan": False}


class FakeAI(AIService):
    """A pretend AI manager. It records what it was asked and never touches the internet."""

    def __init__(self):
        self.fail = None
        self.searched = None

    def analyse_image(self, image_bytes, media_type):
        if self.fail:
            return False, self.fail
        return True, {"detected_items": [{"name": "rice", "quantity": "1", "confidence": 0.9},
                                         {"name": "egg", "quantity": "2", "confidence": 0.9}],
                      "recipes": [EGG_RICE]}

    def search_recipes(self, ingredient_names):
        self.searched = ingredient_names
        return (False, self.fail) if self.fail else (True, [EGG_RICE])

    def pick_query_ingredients(self, items):
        return [i["name"] for i in items]


class FakeData(DataManager):
    """A pretend database kept in memory. Every call returns (ok, value)."""

    def __init__(self):
        self.calls = []
        self.scan = dict(SCAN)
        self.recipe = dict(RECIPE)
        self.down = False

    def _reply(self, name, value, *args):
        self.calls.append((name,) + args)
        if self.down:
            return False, "The database is unavailable right now."
        return True, value

    def create_user(self, name, password, calorie_target=2000, dietary_preference="none"):
        return self._reply("create_user", 1, name)

    def verify_login(self, name, password):
        if password == "wrong-password":
            return False, "Wrong name or password."
        return self._reply("verify_login", 1, name)

    def get_user(self, user_id):
        return self._reply("get_user", {}, user_id)

    def update_user(self, user_id, calorie_target, dietary_preference):
        return self._reply("update_user", True)

    def delete_user(self, user_id):
        return self._reply("delete_user", True)

    def save_record(self, record):
        return self._reply("save_record", 7, record["user_id"])

    def load_recent(self, user_id, limit=5):
        return self._reply("load_recent", [], user_id)

    def get_scan(self, user_id, scan_id):
        return self._reply("get_scan", self.scan, user_id, scan_id)

    def delete_scan(self, user_id, scan_id):
        return self._reply("delete_scan", True, user_id, scan_id)

    def replace_scan_results(self, user_id, scan_id, record):
        return self._reply("replace_scan_results", True, scan_id)

    def filter_recipes(self, user_id, diet=None, max_calories=None, status="accepted"):
        return self._reply("filter_recipes", [self.recipe], user_id)

    def get_recipe(self, user_id, recipe_id):
        return self._reply("get_recipe", self.recipe, recipe_id)

    def update_recipe(self, user_id, recipe_id, changes):
        return self._reply("update_recipe", True, changes)

    def delete_recipe(self, user_id, recipe_id):
        return self._reply("delete_recipe", True, recipe_id)


@pytest.fixture
def setup():
    ai, data = FakeAI(), FakeData()
    web = WebApp(io=IOManager(), ai=ai, logic=LogicManager(), data=data)
    web.flask_app.config["TESTING"] = False   # let our own 500 handler run
    return web.flask_app.test_client(), ai, data


@pytest.fixture
def client(setup):
    return setup[0]


def log_in(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "ann"


def photo(name="a.png", data=PNG):
    return {"image": (io.BytesIO(data), name), "calorie_limit": "500", "diet": "none"}


# ---- login protection -----------------------------------------------------

@pytest.mark.parametrize("method, path", [
    ("get", "/"), ("post", "/analyse"), ("get", "/history"), ("get", "/scan/7"),
    ("get", "/scan/7/fix"), ("post", "/scan/7/fix"), ("post", "/scan/7/delete"),
    ("get", "/recipe/5/edit"), ("post", "/recipe/5/edit"), ("post", "/recipe/5/delete"),
])
def test_every_private_page_redirects_to_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302 and "/login" in response.location


# ---- accounts -------------------------------------------------------------

def test_register_and_login_flow(client):
    assert client.get("/register").status_code == 200
    bad = client.post("/register", data={"username": "a", "password": "x"})
    assert bad.status_code == 400
    good = client.post("/register", data={"username": "ann_01", "password": "password1",
                                          "confirm_password": "password1"})
    assert good.status_code == 302
    assert client.get("/").status_code == 200           # now logged in


def test_login_wrong_password_and_logout(client):
    wrong = client.post("/login", data={"username": "ann_01", "password": "wrong-password"})
    assert wrong.status_code == 401
    ok = client.post("/login", data={"username": "ann_01", "password": "password1"})
    assert ok.status_code == 302
    assert client.post("/logout").status_code == 302
    assert "/login" in client.get("/").location


# ---- main flow ------------------------------------------------------------

def test_home_shows_a_friendly_error_when_the_database_is_down(setup):
    client, _, data = setup
    log_in(client)
    data.down = True
    response = client.get("/")
    assert response.status_code == 503 and b"database is unavailable" in response.data


def test_analyse_runs_ai_then_logic_then_saves(setup):
    client, _, data = setup
    log_in(client)
    response = client.post("/analyse", data=photo())
    assert response.status_code == 200
    assert b"Egg rice" in response.data and b"/scan/7/fix" in response.data
    assert ("save_record", 1) in data.calls


def test_analyse_rejects_a_bad_photo_without_calling_the_ai(setup):
    client, ai, data = setup
    log_in(client)
    response = client.post("/analyse", data=photo("a.txt", b"not an image"))
    assert response.status_code == 400 and b"Only JPG or PNG" in response.data
    assert not data.calls


def test_analyse_shows_an_error_page_when_the_ai_fails(setup):
    client, ai, _ = setup
    log_in(client)
    ai.fail = "The AI service failed after 3 tries"
    response = client.post("/analyse", data=photo())
    assert response.status_code == 502 and b"failed after 3 tries" in response.data


def test_analyse_still_shows_results_when_saving_fails(setup):
    client, _, data = setup
    log_in(client)
    data.down = True
    response = client.post("/analyse", data=photo())
    assert response.status_code == 200
    assert b"database is unavailable" in response.data      # warning banner
    assert b"/fix" not in response.data                     # nothing saved, so nothing to fix


def test_history_passes_filters_and_handles_bad_ones(setup):
    client, _, _ = setup
    log_in(client)
    ok = client.get("/history?diet=vegan&max_calories=600")
    assert ok.status_code == 200 and b"/recipe/5/edit" in ok.data
    assert client.get("/history?diet=keto").status_code == 400


# ---- new feature: fix the AI ---------------------------------------------

def fix_form(*pairs):
    names = [p[0] for p in pairs]
    quantities = [p[1] for p in pairs]
    return {"name": names, "quantity": quantities}


def test_fix_page_opens(setup):
    client, _, _ = setup
    log_in(client)
    response = client.get("/scan/7/fix")
    assert response.status_code == 200 and b'value="chicken"' in response.data


def test_fix_runs_search_logic_and_replace(setup):
    client, ai, data = setup
    log_in(client)
    response = client.post("/scan/7/fix", data=fix_form(("rice", "1 bowl"), ("egg", "2")))
    assert response.status_code == 200
    assert ai.searched == ["rice", "egg"]                    # AI side searched with the NEW list
    assert ("replace_scan_results", 7) in data.calls          # Data side saved the fix
    assert b"added rice, egg" in response.data and b"removed chicken" in response.data
    assert b"Egg rice" in response.data                       # the recipe now passes


def test_fix_with_no_ingredients_shows_the_form_again(setup):
    client, ai, data = setup
    log_in(client)
    response = client.post("/scan/7/fix", data=fix_form(("", "")))
    assert response.status_code == 400 and b"at least one" in response.data
    assert ai.searched is None and ("replace_scan_results", 7) not in data.calls


def test_fix_keeps_old_results_when_the_recipe_service_fails(setup):
    client, ai, data = setup
    log_in(client)
    ai.fail = "Cannot reach the recipe service."
    response = client.post("/scan/7/fix", data=fix_form(("rice", "1")))
    assert response.status_code == 502
    assert not any(call[0] == "replace_scan_results" for call in data.calls)


def test_fix_unknown_scan_is_a_404(setup):
    client, _, data = setup
    log_in(client)
    data.scan = None
    assert client.get("/scan/99/fix").status_code == 404
    assert client.get("/scan/99").status_code == 404


def test_fix_database_failure_is_a_503(setup):
    client, _, data = setup
    log_in(client)
    data.down = True
    assert client.get("/scan/7/fix").status_code == 503


# ---- advanced feature: edit and delete -----------------------------------

def test_view_scan_shows_saved_results(setup):
    client, _, _ = setup
    log_in(client)
    assert client.get("/scan/7").status_code == 200


def test_edit_recipe_form_and_save(setup):
    client, _, data = setup
    log_in(client)
    assert client.get("/recipe/5/edit").status_code == 200
    response = client.post("/recipe/5/edit", data={
        "notes": "less salt", "ingredients_used": "rice", "extra_ingredients": "oil\nsalt"})
    assert response.status_code == 302 and "/history" in response.location
    assert ("update_recipe", {"notes": "less salt", "ingredients_used": ["rice"],
                              "extra_ingredients": ["oil", "salt"]}) in data.calls


def test_edit_recipe_rejects_bad_input(setup):
    client, _, data = setup
    log_in(client)
    response = client.post("/recipe/5/edit", data={"notes": "n" * 501})
    assert response.status_code == 400 and b"at most 500" in response.data
    assert not any(call[0] == "update_recipe" for call in data.calls)


def test_edit_missing_recipe_is_a_404(setup):
    client, _, data = setup
    log_in(client)
    data.recipe = None
    assert client.get("/recipe/5/edit").status_code == 404


def test_delete_recipe_and_scan(setup):
    client, _, data = setup
    log_in(client)
    assert client.post("/recipe/5/delete").status_code == 302
    assert client.post("/scan/7/delete").status_code == 302
    assert ("delete_recipe", 5) in data.calls and ("delete_scan", 1, 7) in data.calls


def test_delete_needs_post_not_get(setup):
    client, _, _ = setup
    log_in(client)
    assert client.get("/recipe/5/delete").status_code == 405
    assert client.get("/scan/7/delete").status_code == 405


# ---- error pages ----------------------------------------------------------

def test_too_big_photo_gets_a_friendly_413(setup):
    client, _, _ = setup
    log_in(client)
    big = {"image": (io.BytesIO(b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 10)), "big.jpg"),
           "calorie_limit": "500", "diet": "none"}
    response = client.post("/analyse", data=big)
    assert response.status_code == 413 and b"too big" in response.data


def test_unexpected_crash_gets_a_friendly_500(setup):
    client, _, data = setup
    log_in(client)
    def boom(*args, **kwargs):
        raise RuntimeError("bug")
    data.load_recent = boom
    response = client.get("/")
    assert response.status_code == 500 and b"Something went wrong" in response.data
    assert b"RuntimeError" not in response.data