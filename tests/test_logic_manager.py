import pytest

import logic_manager

SAMPLE = {
    "detected_items": [
        {"name": "rice", "quantity": "1 bowl", "confidence": 0.95},
        {"name": "egg", "quantity": "2", "confidence": 0.9},
        {"name": "spring onion", "quantity": "1 stalk", "confidence": 0.8},
    ],
    "recipes": [
        {"name": "Egg fried rice", "ingredients_used": ["rice", "egg", "spring onion"],
         "extra_ingredients": ["soy sauce", "oil"], "calories": 450.0,
         "steps": ["Heat oil", "Fry rice and egg"], "vegetarian": True, "vegan": False},
        {"name": "Pork rice bowl", "ingredients_used": ["rice"],
         "extra_ingredients": ["pork", "soy sauce", "garlic", "ginger"],
         "calories": 900.0, "steps": ["Cook"], "vegetarian": False, "vegan": False},
    ],
}


def test_good_recipe_is_accepted_and_bad_one_rejected():
    record = logic_manager.process_ai_result(SAMPLE, 500, "vegetarian")
    assert [r["name"] for r in record["accepted"]] == ["Egg fried rice"]
    assert [r["name"] for r in record["rejected"]] == ["Pork rice bowl"]


def test_rejected_recipe_lists_every_reason():
    record = logic_manager.process_ai_result(SAMPLE, 500, "vegetarian")
    reasons = " ".join(record["rejected"][0]["reasons"]).lower()
    assert "calorie" in reasons and "pork" in reasons and "leftovers" in reasons


def test_score_and_relevance_are_calculated():
    record = logic_manager.process_ai_result(SAMPLE, 500, "vegetarian")
    best = record["accepted"][0]
    assert best["leftovers_used"] == 3
    assert best["relevance"] == pytest.approx(0.6)
    assert best["score"] == pytest.approx(85.0)


def test_vegan_rejects_egg():
    record = logic_manager.process_ai_result(SAMPLE, 500, "vegan")
    assert record["accepted"] == []
    assert "egg" in " ".join(record["rejected"][0]["reasons"])


def test_recipe_source_flag_rejects_when_no_keyword_matches():
    recipe = dict(SAMPLE["recipes"][0], vegetarian=False, extra_ingredients=["oil"])
    ok, reason = logic_manager.check_diet(recipe, "vegetarian")
    assert ok is False and "recipe source" in reason


def test_unknown_flag_is_not_a_rejection():
    recipe = dict(SAMPLE["recipes"][0], vegetarian=None, vegan=None)
    assert logic_manager.check_diet(recipe, "vegetarian")[0] is True


def test_eggplant_is_not_mistaken_for_egg():
    recipe = {"name": "Eggplant stir fry", "ingredients_used": ["eggplant", "rice"],
              "extra_ingredients": [], "calories": 300.0, "vegan": True}
    assert logic_manager.check_diet(recipe, "vegan")[0] is True


def test_plural_words_are_caught():
    recipe = {"name": "Snack", "ingredients_used": ["sausages"],
              "extra_ingredients": [], "calories": 200.0}
    ok, reason = logic_manager.check_diet(recipe, "vegetarian")
    assert ok is False and "sausage" in reason


def test_halal_rejects_pork_by_keyword():
    ok, reason = logic_manager.check_diet(SAMPLE["recipes"][1], "halal")
    assert ok is False and "pork" in reason


def test_invalid_calories_are_rejected():
    recipe = dict(SAMPLE["recipes"][0], calories="lots")
    ok, reason = logic_manager.check_calories(recipe, 500)
    assert ok is False and "invalid" in reason


def test_low_relevance_is_rejected():
    recipe = dict(SAMPLE["recipes"][0], ingredients_used=["rice", "egg"],
                  extra_ingredients=["a", "b", "c", "d", "e", "f"])
    result = logic_manager.evaluate_recipe(recipe, SAMPLE["detected_items"], 500, "none")
    assert result["status"] == "rejected"
    assert "of its ingredients" in " ".join(result["reasons"])


def test_weak_detections_are_ignored():
    items = [{"name": "rice", "quantity": "1", "confidence": 0.95},
             {"name": "egg", "quantity": "1", "confidence": 0.3}]
    result = logic_manager.evaluate_recipe(SAMPLE["recipes"][0], items, 500, "none")
    assert result["leftovers_used"] == 1


def test_no_food_detected_gives_no_accepted_recipes():
    empty = {"detected_items": [], "recipes": [SAMPLE["recipes"][0]]}
    record = logic_manager.process_ai_result(empty, 500, "none")
    assert record["accepted"] == []


def test_accepted_recipes_are_sorted_best_first():
    second = dict(SAMPLE["recipes"][0], name="Plain rice and egg",
                  ingredients_used=["rice", "egg"], extra_ingredients=[], calories=100.0)
    data = {"detected_items": SAMPLE["detected_items"],
            "recipes": [second, SAMPLE["recipes"][0]]}
    record = logic_manager.process_ai_result(data, 500, "none")
    scores = [r["score"] for r in record["accepted"]]
    assert len(scores) == 2 and scores == sorted(scores, reverse=True)