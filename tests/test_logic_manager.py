"""Tests for the Logic classes (Justin). Pure Python: no database, no AI, no Flask."""
import pytest

from logic_manager.correction_service import CorrectionService
from logic_manager.evaluation_context import EvaluationContext
from logic_manager.ingredient_matcher import IngredientMatcher
from logic_manager.logic_manager import LogicManager
from logic_manager.number_parser import NumberParser
from logic_manager.recipe_evaluator import RecipeEvaluator
from logic_manager.rules import CalorieRule, DietRule, LeftoverRule, RelevanceRule, Rule
from logic_manager.scorer import Scorer, WeightedScorer

ITEMS = [
    {"name": "rice", "quantity": "1 bowl", "confidence": 0.95},
    {"name": "egg", "quantity": "2", "confidence": 0.9},
    {"name": "spring onion", "quantity": "1 stalk", "confidence": 0.8},
]
EGG_RICE = {"name": "Egg fried rice", "ingredients_used": ["rice", "egg", "spring onion"],
            "extra_ingredients": ["soy sauce", "oil"], "calories": 450.0,
            "steps": ["Heat oil", "Fry rice and egg"], "vegetarian": True, "vegan": False}
PORK_BOWL = {"name": "Pork rice bowl", "ingredients_used": ["rice"],
             "extra_ingredients": ["pork", "soy sauce", "garlic", "ginger"],
             "calories": 900.0, "steps": ["Cook"], "vegetarian": False, "vegan": False}
SAMPLE = {"detected_items": ITEMS, "recipes": [EGG_RICE, PORK_BOWL]}


def ctx(limit=500, diet="none", items=ITEMS):
    return EvaluationContext(items=items, limit=limit, diet=diet)


# ---- NumberParser and IngredientMatcher -----------------------------------

def test_safe_number():
    assert NumberParser.safe_number(5) == 5.0
    assert NumberParser.safe_number("5") == 0.0
    assert NumberParser.safe_number(True, default=-1) == -1
    assert NumberParser.safe_number(None, 7.5) == 7.5


def test_to_words_lowercases_and_removes_plural_s():
    assert IngredientMatcher.to_words("Fried Eggs") == {"fried", "egg"}
    assert IngredientMatcher.to_words("rice, 2 cups!") == {"rice", "cup"}


def test_confident_items_drops_unsure_and_bad_values():
    items = [{"name": "a", "confidence": 0.9}, {"name": "b", "confidence": 0.3},
             {"name": "c", "confidence": "high"}, {"name": "d"}]
    assert [i["name"] for i in IngredientMatcher().confident_items(items)] == ["a"]


def test_count_leftovers_used_and_relevance():
    matcher = IngredientMatcher()
    assert matcher.count_leftovers_used(EGG_RICE, ITEMS) == 3
    assert matcher.count_leftovers_used(PORK_BOWL, ITEMS) == 1
    assert matcher.relevance(EGG_RICE, 3) == pytest.approx(0.6)
    assert matcher.relevance({}, 0) == 0.0


# ---- the four rules (each one alone) --------------------------------------

def test_calorie_rule():
    rule = CalorieRule()
    assert rule.check(EGG_RICE, ctx(500)) == (True, "")
    assert "Over calorie limit" in rule.check(PORK_BOWL, ctx(500))[1]
    assert "invalid" in rule.check({"calories": 0}, ctx())[1]
    assert "invalid" in rule.check({"calories": "lots"}, ctx())[1]


def test_diet_rule_by_ingredient_and_by_source_flag():
    rule = DietRule()
    assert rule.check(EGG_RICE, ctx(diet="vegetarian")) == (True, "")
    ok, reason = rule.check(PORK_BOWL, ctx(diet="vegetarian"))
    assert ok is False and "pork" in reason
    ok, reason = rule.check(EGG_RICE, ctx(diet="vegan"))          # egg is animal food
    assert ok is False and "egg" in reason
    flagged = {"name": "Salad", "ingredients_used": [], "extra_ingredients": [], "vegan": False}
    assert "recipe source" in DietRule().check(flagged, ctx(diet="vegan"))[1]
    assert rule.check(PORK_BOWL, ctx(diet="none")) == (True, "")


def test_leftover_rule():
    rule = LeftoverRule(IngredientMatcher())
    assert rule.check(EGG_RICE, ctx()) == (True, "")
    assert "Uses only 1" in rule.check(PORK_BOWL, ctx())[1]
    # one photographed item only: needing 2 would be unfair, so 1 is enough
    assert rule.check(PORK_BOWL, ctx(items=ITEMS[:1])) == (True, "")


def test_relevance_rule():
    rule = RelevanceRule(IngredientMatcher())
    assert rule.check(EGG_RICE, ctx()) == (True, "")
    ok, reason = rule.check(PORK_BOWL, ctx())
    assert ok is False and "20%" in reason


def test_rules_share_one_contract():
    matcher = IngredientMatcher()
    rules = [CalorieRule(), DietRule(), LeftoverRule(matcher), RelevanceRule(matcher)]
    assert all(isinstance(rule, Rule) for rule in rules)
    with pytest.raises(TypeError):
        Rule()


# ---- scorer ---------------------------------------------------------------

def test_weighted_scorer_matches_the_hand_calculation():
    scorer = WeightedScorer(IngredientMatcher())
    assert isinstance(scorer, Scorer)
    assert scorer.score(EGG_RICE, ITEMS, 500) == pytest.approx(85.0)


def test_a_different_scorer_can_replace_the_default():
    class AlwaysTen(Scorer):
        def score(self, recipe, items, limit):
            return 10.0
    matcher = IngredientMatcher()
    evaluator = RecipeEvaluator([CalorieRule()], AlwaysTen(), matcher)
    assert evaluator.evaluate(EGG_RICE, ITEMS, 500, "none")["score"] == 10.0


# ---- evaluator and LogicManager -------------------------------------------

def test_good_recipe_is_accepted_and_bad_one_rejected():
    record = LogicManager().process_ai_result(SAMPLE, 500, "vegetarian")
    assert [r["name"] for r in record["accepted"]] == ["Egg fried rice"]
    assert [r["name"] for r in record["rejected"]] == ["Pork rice bowl"]


def test_rejected_recipe_lists_every_reason():
    record = LogicManager().process_ai_result(SAMPLE, 500, "vegetarian")
    reasons = " ".join(record["rejected"][0]["reasons"]).lower()
    assert "calorie" in reasons and "pork" in reasons and "leftovers" in reasons


def test_score_and_relevance_are_calculated():
    best = LogicManager().process_ai_result(SAMPLE, 500, "vegetarian")["accepted"][0]
    assert best["leftovers_used"] == 3
    assert best["relevance"] == pytest.approx(0.6)
    assert best["score"] == pytest.approx(85.0)


def test_the_original_recipe_is_not_changed():
    recipe = dict(EGG_RICE)
    LogicManager().evaluate_recipe(recipe, ITEMS, 500, "none")
    assert recipe == EGG_RICE


def test_accepted_recipes_are_sorted_best_first():
    low = dict(EGG_RICE, name="Plain rice", ingredients_used=["rice", "egg"],
               extra_ingredients=["a", "b"])
    record = LogicManager().process_ai_result({"detected_items": ITEMS, "recipes": [low, EGG_RICE]},
                                              500, "none")
    scores = [r["score"] for r in record["accepted"]]
    assert scores == sorted(scores, reverse=True) and len(scores) == 2


def test_unsure_items_do_not_count():
    unsure = [{"name": "rice", "quantity": "1", "confidence": 0.2},
              {"name": "egg", "quantity": "1", "confidence": 0.2}]
    record = LogicManager().process_ai_result({"detected_items": unsure, "recipes": [EGG_RICE]},
                                              500, "none")
    assert record["accepted"] == [] and len(record["rejected"]) == 1


def test_empty_input_gives_an_empty_record():
    record = LogicManager().process_ai_result({}, 500, "none")
    assert record["accepted"] == [] and record["rejected"] == []


def test_a_new_rule_can_be_added_without_changing_existing_code():
    class NoSoySauce(Rule):
        def check(self, recipe, ctx):
            if "soy sauce" in recipe.get("extra_ingredients", []):
                return False, "No soy sauce allowed"
            return True, ""
    matcher = IngredientMatcher()
    evaluator = RecipeEvaluator([NoSoySauce()], WeightedScorer(matcher), matcher)
    result = LogicManager(evaluator=evaluator).evaluate_recipe(EGG_RICE, ITEMS, 500, "none")
    assert result["status"] == "rejected" and result["reasons"] == ["No soy sauce allowed"]


# ---- new feature: CorrectionService ---------------------------------------

def test_build_items_cleans_names_and_trusts_the_user():
    edits = [{"name": "  Tofu ", "quantity": "2 blocks"}, {"name": "TOFU", "quantity": "1"},
             {"name": "", "quantity": "9"}, {"name": "spring   onion", "quantity": ""}]
    items = CorrectionService().build_items(edits)
    assert items == [
        {"name": "tofu", "quantity": "2 blocks", "confidence": 1.0},
        {"name": "spring onion", "quantity": "1", "confidence": 1.0},
    ]


def test_build_items_with_nothing_returns_an_empty_list():
    assert CorrectionService().build_items([]) == []


def test_diff_items_finds_added_and_removed():
    before = [{"name": "chicken"}, {"name": "rice"}]
    after = [{"name": "rice"}, {"name": "Tofu"}]
    assert CorrectionService().diff_items(before, after) == (["tofu"], ["chicken"])


def test_summarise_explains_the_change_in_plain_words():
    before = {"detected_items": [{"name": "chicken"}], "accepted": [], "rejected": [1]}
    after = {"detected_items": [{"name": "tofu"}], "accepted": [1, 2], "rejected": []}
    summary = CorrectionService().summarise(before, after)
    assert summary["accepted_before"] == 0 and summary["accepted_after"] == 2
    assert "added tofu" in summary["message"] and "removed chicken" in summary["message"]
    assert "0 before, 2 now" in summary["message"]


def test_summarise_when_nothing_changed():
    same = {"detected_items": [{"name": "rice"}], "accepted": [1], "rejected": []}
    assert "No ingredients changed" in CorrectionService().summarise(same, same)["message"]


def test_the_fix_flow_can_turn_a_rejected_recipe_into_an_accepted_one():
    """The AI saw only rice. The user adds egg. Now the recipe passes the leftover rule."""
    manager = LogicManager()
    recipe = dict(EGG_RICE, ingredients_used=["rice", "egg"], extra_ingredients=["oil"])
    wrong = [{"name": "rice", "quantity": "1", "confidence": 0.9},
             {"name": "noodle", "quantity": "1", "confidence": 0.9}]
    before = manager.process_ai_result({"detected_items": wrong, "recipes": [recipe]}, 500, "none")
    assert before["accepted"] == []
    fixed = manager.build_corrected_items([{"name": "rice", "quantity": "1"},
                                           {"name": "egg", "quantity": "2"}])
    after = manager.process_ai_result({"detected_items": fixed, "recipes": [recipe]}, 500, "none")
    assert len(after["accepted"]) == 1
    assert manager.summarise_changes(before, after)["accepted_after"] == 1