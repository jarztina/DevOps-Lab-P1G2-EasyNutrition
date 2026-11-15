"""Tests for PageRenderer and the templates (Gabriel). Renders real HTML, no database."""

import pytest
from flask import Flask

from io_manager.constants import ALLOWED_DIETS
from io_manager.page_renderer import PageRenderer
from io_manager.session_manager import SessionManager

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["SECRET_KEY"] = "test-secret"
for path, name in [("/", "home"), ("/history", "history"), ("/login", "login")]:
    app.add_url_rule(path, endpoint=name, view_func=lambda: "x")

RECIPE = {"id": 5, "scan_id": 7, "name": "Egg fried rice", "calories": 450.0, "score": 85.0,
          "ingredients_used": ["rice", "egg"], "extra_ingredients": ["oil"],
          "steps": ["Cook"], "source_url": "https://x.example", "notes": "less salt",
          "diet": "none", "created_at": "2026-11-10", "reasons": []}
SCAN = {"scan_id": 7, "calorie_limit": 500, "diet": "none",
        "detected_items": [{"name": "rice", "quantity": "1 bowl", "confidence": 0.9}]}


@pytest.fixture
def renderer():
    return PageRenderer(SessionManager(), ALLOWED_DIETS)


def page(renderer, method, *args, **kwargs):
    with app.test_request_context("/"):
        return getattr(renderer, method)(*args, **kwargs)


def test_login_and_register_pages_show_errors(renderer):
    assert "Wrong name" in page(renderer, "render_login", ["Wrong name"])
    assert "Name taken" in page(renderer, "render_register", ["Name taken"])


def test_home_page_lists_diets_and_recent_scans(renderer):
    html = page(renderer, "render_home", None, [{"id": 3, "image_name": "lunch.jpg",
                                                 "accepted_count": 2}])
    assert "vegan" in html and "lunch.jpg" in html and "/scan/3" in html


def test_error_page_shows_the_message(renderer):
    assert "Photo is too big" in page(renderer, "render_error", "Photo is too big")


def test_results_page_has_fix_and_delete_buttons_for_a_saved_scan(renderer):
    record = dict(SCAN, accepted=[RECIPE], rejected=[])
    html = page(renderer, "render_results", record)
    assert "/scan/7/fix" in html and "/scan/7/delete" in html
    assert "Egg fried rice" in html and "less salt" in html


def test_results_page_hides_buttons_when_the_scan_was_not_saved(renderer):
    record = dict(SCAN, scan_id=None, accepted=[], rejected=[])
    html = page(renderer, "render_results", record)
    assert "/fix" not in html and "/delete" not in html


def test_results_page_shows_the_change_summary(renderer):
    record = dict(SCAN, accepted=[], rejected=[], changes={"message": "You added egg."})
    assert "You added egg." in page(renderer, "render_results", record)


def test_history_page_has_edit_and_delete_for_each_recipe(renderer):
    html = page(renderer, "render_history", [RECIPE], {"diet": None, "max_calories": None})
    assert "/recipe/5/edit" in html and "/recipe/5/delete" in html
    assert "confirm(" in html  # delete asks first


def test_history_page_empty_message(renderer):
    html = page(renderer, "render_history", [], {"diet": None, "max_calories": None})
    assert "Nothing saved yet" in html


def test_fix_page_shows_ai_items_plus_empty_rows(renderer):
    html = page(renderer, "render_fix", SCAN)
    assert 'value="rice"' in html and 'value="1 bowl"' in html
    assert html.count('placeholder="Add an ingredient"') == 3
    assert 'action="/scan/7/fix"' in html


def test_fix_page_can_show_what_the_user_typed_with_errors(renderer):
    html = page(renderer, "render_fix", SCAN, ["Please keep at least one ingredient."],
                [{"name": "tofu", "quantity": "2"}])
    assert "Please keep at least one" in html and 'value="tofu"' in html


def test_recipe_edit_page_is_filled_in(renderer):
    html = page(renderer, "render_recipe_edit", RECIPE)
    assert "less salt" in html and "rice\negg" in html and 'action="/recipe/5/edit"' in html


def test_text_from_users_is_escaped(renderer):
    evil = dict(RECIPE, name="<script>alert(1)</script>", notes="<b>x</b>")
    html = page(renderer, "render_recipe_edit", evil)
    assert "<script>alert(1)</script>" not in html