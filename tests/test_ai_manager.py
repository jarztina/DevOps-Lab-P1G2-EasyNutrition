from types import SimpleNamespace

import pytest
import requests

import ai_manager

RAW_RECIPE = {
    "id": 101, "title": "Egg fried rice", "sourceUrl": "https://example.com/r",
    "vegetarian": True, "vegan": False,
    "usedIngredients": [{"name": "rice"}, {"name": "egg"}],
    "missedIngredients": [{"name": "soy sauce"}],
    "nutrition": {"nutrients": [{"name": "Fat", "amount": 9, "unit": "g"},
                                {"name": "Calories", "amount": 450.5, "unit": "kcal"}]},
    "analyzedInstructions": [{"steps": [{"step": "Heat oil"}, {"step": "Fry rice"}]}],
}
GOOD_ITEMS = {"ingredients": [{"name": "rice", "quantity": "1 bowl", "confidence": 0.9}]}


def fake_response(status, body=None, bad_json=False):
    def get_json():
        if bad_json:
            raise ValueError("not json")
        return body
    return SimpleNamespace(status_code=status, json=get_json)


def test_extract_json_text_removes_fences():
    raw = "Sure!\n```json\n{\"a\": 1}\n```"
    assert ai_manager.extract_json_text(raw) == '{"a": 1}'


def test_validate_ingredients_accepts_good_and_empty():
    assert ai_manager.validate_ingredients(GOOD_ITEMS)[0] is True
    assert ai_manager.validate_ingredients({"ingredients": []})[0] is True


def test_validate_ingredients_rejects_bad_shapes():
    assert ai_manager.validate_ingredients({"ingredients": "rice"})[0] is False
    assert ai_manager.validate_ingredients({"ingredients": [{"name": "x"}]})[0] is False
    assert ai_manager.validate_ingredients([1, 2])[0] is False


def test_normalise_recipe_converts_spoonacular_shape():
    recipe = ai_manager.normalise_recipe(RAW_RECIPE)
    assert recipe["name"] == "Egg fried rice"
    assert recipe["calories"] == 450.5
    assert recipe["ingredients_used"] == ["rice", "egg"]
    assert recipe["extra_ingredients"] == ["soy sauce"]
    assert recipe["steps"] == ["Heat oil", "Fry rice"]
    assert recipe["vegetarian"] is True and recipe["vegan"] is False


def test_normalise_recipe_skips_recipe_without_calories():
    broken = dict(RAW_RECIPE, nutrition={"nutrients": []})
    assert ai_manager.normalise_recipe(broken) is None
    assert ai_manager.normalise_recipe("nonsense") is None


def test_pick_query_ingredients_best_first_no_duplicates():
    items = [{"name": "Egg", "confidence": 0.5}, {"name": "rice", "confidence": 0.9},
             {"name": "egg", "confidence": 0.4}]
    assert ai_manager.pick_query_ingredients(items) == ["rice", "egg"]


def test_spoonacular_quota_error_is_friendly(monkeypatch):
    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    monkeypatch.setattr(ai_manager.requests, "get", lambda *a, **k: fake_response(402))
    ok, message = ai_manager.call_spoonacular(["rice"])
    assert ok is False and "limit" in message


def test_spoonacular_bad_json_is_handled(monkeypatch):
    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    monkeypatch.setattr(ai_manager.requests, "get",
                        lambda *a, **k: fake_response(200, bad_json=True))
    ok, message = ai_manager.call_spoonacular(["rice"])
    assert ok is False and "unreadable" in message


def test_spoonacular_network_failure_retries_then_stops(monkeypatch):
    calls = []

    def failing_get(*args, **kwargs):
        calls.append(1)
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    monkeypatch.setattr(ai_manager.requests, "get", failing_get)
    monkeypatch.setattr(ai_manager.time, "sleep", lambda s: None)
    ok, message = ai_manager.call_spoonacular(["rice"])
    assert ok is False and "Cannot reach" in message
    assert len(calls) == ai_manager.SPOON_ATTEMPTS


def test_identify_ingredients_retries_after_bad_json(monkeypatch):
    answers = iter([(True, "not json"), (True, '{"ingredients": []}')])
    monkeypatch.setattr(ai_manager, "call_api", lambda *a: next(answers))
    monkeypatch.setattr(ai_manager.time, "sleep", lambda s: None)
    assert ai_manager.identify_ingredients(b"x", "image/jpeg") == (True, [])


def test_analyse_image_combines_both_steps(monkeypatch):
    monkeypatch.setattr(ai_manager, "identify_ingredients",
                        lambda b, m: (True, GOOD_ITEMS["ingredients"]))
    monkeypatch.setattr(ai_manager, "call_spoonacular", lambda names: (True, [RAW_RECIPE]))
    ok, data = ai_manager.analyse_image(b"x", "image/jpeg")
    assert ok is True
    assert data["detected_items"][0]["name"] == "rice"
    assert data["recipes"][0]["name"] == "Egg fried rice"


def test_no_food_skips_recipe_search(monkeypatch):
    monkeypatch.setattr(ai_manager, "identify_ingredients", lambda b, m: (True, []))

    def must_not_run(names):
        raise AssertionError("Spoonacular should not be called")

    monkeypatch.setattr(ai_manager, "call_spoonacular", must_not_run)
    assert ai_manager.analyse_image(b"x", "image/jpeg") == (
        True, {"detected_items": [], "recipes": []})