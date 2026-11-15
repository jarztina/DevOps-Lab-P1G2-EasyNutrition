"""Tests for the AI classes (Sebastian). No live AI and no internet needed."""
from types import SimpleNamespace
import anthropic
import pytest
import requests

from ai_manager.ai_manager import AIManager
from ai_manager.ai_service import AIService
from ai_manager.ingredient_parser import IngredientParser
from ai_manager.recipe_source import RecipeSource, SpoonacularSource
from ai_manager.vision_client import VisionClient

RAW_RECIPE = {
    "id": 101, "title": "Egg fried rice",
    "sourceUrl": "https://example.com/r",
    "vegetarian": True, "vegan": False,
    "usedIngredients": [{"name": "rice"}, {"name": "egg"}],
    "missedIngredients": [{"name": "soy sauce"}],
    "nutrition": {"nutrients": [
        {"name": "Fat", "amount": 9, "unit": "g"},
        {"name": "Calories", "amount": 450.5, "unit": "kcal"}
    ]},
    "analyzedInstructions": [{"steps": [{"step": "Heat oil"}, {"step": "Fry rice"}]}]
}
GOOD_ITEMS = [{"name": "rice", "quantity": "1 bowl", "confidence": 0.9}]

def fake_response(status, body=None, bad_json=False):
    def get_json():
        if bad_json:
            raise ValueError("not json")
        return body
    return SimpleNamespace(status_code=status, json=get_json)

def fake_claude(*blocks):
    """A fake Claude client whose answer holds the given content blocks."""
    message = SimpleNamespace(content=list(blocks))
    messages = SimpleNamespace(create=lambda **kwargs: message)
    return SimpleNamespace(messages=messages)

def text(value):
    return SimpleNamespace(type="text", text=value)

def thinking(value="hmm"):
    return SimpleNamespace(type="thinking", thinking=value) # has NO .text

# IngredientParser

def test_extract_json_text_removes_fences():
    raw = "Sure!\n```json\n{\"a\": 1}\n```"
    assert IngredientParser.extract_json_text(raw) == '{"a": 1}'

def test_validate_accepts_good_and_empty():
    parser = IngredientParser()
    assert parser.validate({"ingredients": GOOD_ITEMS})[0] is True
    assert parser.validate({"ingredients": []})[0] is True

@pytest.mark.parametrize("bad", [
    {"ingredients": "rice"},
    {"ingredients": [{"name": "x"}]},
    {"ingredients": [{"name": "x", "quantity": "1", "confidence": True}]},
    [1, 2],
    {},
])
def test_validate_rejects_bad_shapes(bad):
    assert IngredientParser().validate(bad)[0] is False

def test_parse_returns_items_or_a_reason():
    parser = IngredientParser()
    raw = 'Here: {"ingredients": [{"name": "egg", "quantity": "2", "confidence": 0.8}]}'
    ok, items = parser.parse(raw)
    assert ok is True and items[0]["name"] == "egg"
    assert parser.parse("no json at all") == (False, "The AI did not return valid JSON.")
    assert parser.parse('{"ingredients": 5}')[0] is False

# VisionClient

def test_ask_reports_a_missing_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ok, message = VisionClient().ask(b"x", "image/jpeg", "prompt")
    assert ok is False and "not configured" in message

def test_ask_reports_a_missing_model(monkeypatch):
    monkeypatch.delenv("AI_MODEL", raising=False)
    ok, message = VisionClient(fake_claude(text("hi"))).ask(b"x", "image/jpeg", "p")
    assert ok is False and "model" in message

def test_ask_returns_the_text(monkeypatch):
    monkeypatch.setenv("AI_MODEL", "m")
    assert VisionClient(fake_claude(text("hello"))).ask(b"x", "image/jpeg", "p") == (True, "hello")

def test_ask_skips_a_thinking_block_first(monkeypatch):
    # This is the bug from Part 1: content[0] was a thinking block with no .text
    monkeypatch.setenv("AI_MODEL", "m")
    client = VisionClient(fake_claude(thinking(), text("the answer")))
    assert client.ask(b"x", "image/jpeg", "p") == (True, "the answer")

def test_ask_handles_an_empty_or_text_free_answer(monkeypatch):
    monkeypatch.setenv("AI_MODEL", "m")
    assert VisionClient(fake_claude()).ask(b"x", "image/jpeg", "p")[0] is False
    assert VisionClient(fake_claude(thinking())).ask(b"x", "image/jpeg", "p")[0] is False

def test_ask_handles_a_network_failure(monkeypatch):
    monkeypatch.setenv("AI_MODEL", "m")
    def boom(**kwargs):
        raise anthropic.APIConnectionError(request=SimpleNamespace())
    client = SimpleNamespace(messages=SimpleNamespace(create=boom))
    ok, message = VisionClient(client).ask(b"x", "image/jpeg", "p")
    assert ok is False and "Cannot reach" in message

def test_ask_handles_any_unexpected_error(monkeypatch):
    monkeypatch.setenv("AI_MODEL", "m")
    def boom(**kwargs):
        raise RuntimeError("weird")
    client = SimpleNamespace(messages=SimpleNamespace(create=boom))
    ok, message = VisionClient(client).ask(b"x", "image/jpeg", "p")
    assert ok is False and "Unexpected" in message

def test_prompt_asks_for_json_only():
    assert "ONLY a JSON object" in VisionClient.build_prompt()

# SpoonacularSource

def make_source(get, sleep=lambda s: None):
    return SpoonacularSource(http_get=get, sleep=sleep)

def test_normalise_converts_the_spoonacular_shape():
    recipe = make_source(None)._normalise(RAW_RECIPE)
    assert recipe["name"] == "Egg fried rice"
    assert recipe["calories"] == 450.5
    assert recipe["ingredients_used"] == ["rice", "egg"]
    assert recipe["extra_ingredients"] == ["soy sauce"]
    assert recipe["steps"] == ["Heat oil", "Fry rice"]
    assert recipe["vegetarian"] is True and recipe["vegan"] is False

def test_normalise_skips_a_recipe_without_calories():
    source = make_source(None)
    assert source._normalise(dict(RAW_RECIPE, nutrition={"nutrients": []})) is None
    assert source._normalise("nonsense") is None

def test_missing_recipe_key_is_reported(monkeypatch):
    monkeypatch.delenv("SPOONACULAR_API_KEY", raising=False)
    ok, message = make_source(None)._call(["rice"])
    assert ok is False and "not configured" in message

@pytest.mark.parametrize("status, word", [
    (401, "rejected"), (402, "limit"), (429, "Too many"), (500, "status 500"),
])
def test_spoonacular_error_codes_are_friendly(monkeypatch, status, word):
    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    ok, message = make_source(lambda a, **k: fake_response(status))._call(["rice"])
    assert ok is False and word in message

def test_spoonacular_bad_json_is_handled(monkeypatch):
    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    ok, message = make_source(lambda a, **k: fake_response(200, bad_json=True))._call(["rice"])
    assert ok is False and "unreadable" in message

def test_spoonacular_unexpected_shape_is_handled(monkeypatch):
    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    ok, message = make_source(lambda a, **k: fake_response(200, {"oops": 1}))._call(["rice"])
    assert ok is False and "unexpected" in message

def test_spoonacular_network_failure_retries_then_stops(monkeypatch):
    calls = []
    def failing_get(*args, **kwargs):
        calls.append(1)
        raise requests.exceptions.Timeout("slow")
    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    ok, message = make_source(failing_get)._call(["rice"])
    assert ok is False and "Cannot reach" in message
    assert len(calls) == SpoonacularSource.ATTEMPTS

def test_find_recipes_returns_normalised_recipes(monkeypatch):
    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    source = make_source(lambda a, **k: fake_response(200, {"results": [RAW_RECIPE]}))
    ok, recipes = source.find_recipes(["rice", "egg"])
    assert ok is True and recipes[0]["name"] == "Egg fried rice"

def test_find_recipes_with_no_names_makes_no_call():
    def must_not_run(*a, **k):
        raise AssertionError("no call expected")
    assert make_source(must_not_run).find_recipes([]) == (True, [])

def test_find_recipes_tries_fewer_ingredients_when_nothing_matches(monkeypatch):
    monkeypatch.setenv("SPOONACULAR_API_KEY", "x")
    asked = []
    def get(url, params, timeout):
        asked.append(params["includeIngredients"])
        results = [] if len(asked) == 1 else [RAW_RECIPE]
        return fake_response(200, {"results": results})
    ok, recipes = make_source(get).find_recipes(["a", "b", "c"])
    assert ok is True and len(recipes) == 1 and asked == ["a,b,c", "a,b"]

# AIManager (a fake vision client and fake recipe source are plugged in)

class FakeVision:
    def __init__(self, answers):
        self._answers = iter(answers)
        self.calls = 0
    def build_prompt(self):
        return "prompt"
    def ask(self, image_bytes, media_type, prompt):
        self.calls += 1
        return next(self._answers)

class FakeSource(RecipeSource):
    """A second RecipeSource: proves the manager works with any source (polymorphism)."""
    def __init__(self, result=(True, [{"name": "Fake pie"}])):
        self.result = result
        self.asked = []
    def find_recipes(self, ingredient_names):
        self.asked.append(ingredient_names)
        return self.result

def make_manager(answers, source=None):
    return AIManager(vision=FakeVision(answers), recipe_source=source or FakeSource(),
                     sleep=lambda s: None)

GOOD_TEXT = '{"ingredients": [{"name": "rice", "quantity": "1", "confidence": 0.9}]}'

def test_manager_follows_the_ai_service_contract():
    assert isinstance(make_manager([]), AIService)
    with pytest.raises(TypeError):
        AIService()

def test_identify_retries_after_bad_json():
    manager = make_manager([(True, "not json"), (True, GOOD_TEXT)])
    ok, items = manager.identify_ingredients(b"x", "image/jpeg")
    assert ok is True and items[0]["name"] == "rice"

def test_identify_gives_up_after_max_attempts():
    manager = make_manager([(False, "down")] * 3)
    ok, message = manager.identify_ingredients(b"x", "image/jpeg")
    assert ok is False and "failed after 3 tries" in message
    assert manager._vision.calls == 3

def test_pick_query_ingredients_best_first_no_duplicates():
    items = [{"name": "Egg", "confidence": 0.5}, {"name": "rice", "confidence": 0.9},
             {"name": "egg", "confidence": 0.4}]
    assert make_manager([]).pick_query_ingredients(items) == ["rice", "egg"]

def test_pick_query_ingredients_keeps_at_most_five():
    items = [{"name": f"item{n}", "confidence": 0.9} for n in range(8)]
    assert len(make_manager([]).pick_query_ingredients(items)) == 5

def test_analyse_image_combines_both_steps():
    source = FakeSource()
    ok, data = make_manager([(True, GOOD_TEXT)], source).analyse_image(b"x", "image/jpeg")
    assert ok is True and data["detected_items"][0]["name"] == "rice"
    assert data["recipes"][0]["name"] == "Fake pie" and source.asked == [["rice"]]

def test_analyse_image_stops_when_the_photo_cannot_be_read():
    manager = make_manager([(False, "down")] * 3)
    assert manager.analyse_image(b"x", "image/jpeg")[0] is False

def test_analyse_image_passes_on_a_recipe_service_error():
    manager = make_manager([(True, GOOD_TEXT)], FakeSource((False, "recipes down")))
    assert manager.analyse_image(b"x", "image/jpeg") == (False, "recipes down")

def test_no_food_skips_the_recipe_search():
    def must_not_run(*args, **kwargs):
        raise AssertionError("Spoonacular should not be called")
    manager = AIManager(vision=FakeVision([(True, '{"ingredients": []}')]),
                        recipe_source=SpoonacularSource(http_get=must_not_run),
                        sleep=lambda s: None)
    assert manager.analyse_image(b"x", "image/jpeg") == (
        True, {"detected_items": [], "recipes": []})

def test_search_recipes_is_available_for_the_fix_feature():
    source = FakeSource()
    assert make_manager([], source).search_recipes(["egg"]) == (True, [{"name": "Fake pie"}])
    assert source.asked == [["egg"]]
