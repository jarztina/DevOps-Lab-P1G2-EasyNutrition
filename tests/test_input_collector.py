import io
from werkzeug.datastructures import FileStorage, MultiDict
from io_manager.input_collector import InputCollector

collector = InputCollector()

def make_file_storage(content: bytes, filename: str) -> FileStorage:
    """Build a FileStorage object from raw bytes."""
    return FileStorage(stream=io.BytesIO(content), filename=filename)

def test_collect_credentials_login_flow():
    # Valid login credentials
    form = {"username": "user_01", "password": "my_password"}
    ok, creds = collector.collect_credentials(form, is_register=False)
    assert ok is True
    assert creds == {"username": "user_01", "password": "my_password"}

    # Missing password on login
    bad_form = {"username": "user_01", "password": ""}
    ok, errors = collector.collect_credentials(bad_form, is_register=False)
    assert ok is False
    assert "Please type your password." in errors

def test_collect_credentials_register_flow():
    # Valid registration
    form = {
        "username": "user_01",
        "password": "valid_pass_123",
        "confirm_password": "valid_pass_123",
    }

    ok, creds = collector.collect_credentials(form, is_register=True)
    assert ok is True
    assert creds["username"] == "user_01"
    # Mismatched passwords
    mismatch_form = {
        "username": "user_01",
        "password": "valid_pass_123",
        "confirm_password": "different_pass",
    }

    ok, errors = collector.collect_credentials(mismatch_form, is_register=True)
    assert ok is False
    assert "The two passwords do not match." in errors
    # Weak password on registration
    weak_form = {
        "username": "user_01",
        "password": "123",
        "confirm_password": "123",
    }

    ok, errors = collector.collect_credentials(weak_form, is_register=True)
    assert ok is False
    assert any("at least" in err for err in errors)

def test_collect_input_success():
    form = {"calorie_limit": "650", "diet": "vegetarian"}
    files = {"image": make_file_storage(b"\xff\xd8\xffphoto", "food.jpg")}
    ok, result = collector.collect_input(form, files)
    assert ok is True
    assert result["calorie_limit"] == 650
    assert result["diet"] == "vegetarian"
    assert result["image_name"] == "food.jpg"
    assert result["media_type"] == "image/jpeg"

def test_collect_input_aggregates_multiple_errors():
    # All fields invalid: bad calories, bad diet, bad upload
    form = {"calorie_limit": "50", "diet": "pescatarian"}

    files = {"image": make_file_storage(b"not-an-image", "test.txt")}
    ok, errors = collector.collect_input(form, files)
    assert ok is False
    assert len(errors) == 3

def test_parse_history_filters():
    # All filters present
    args = {"diet": "vegan", "max_calories": "600"}
    ok, filters = collector.parse_history_filters(args)
    assert ok is True
    assert filters == {"diet": "vegan", "max_calories": 600, "status": "accepted"}
    # Empty/default query parameters
    ok, empty_filters = collector.parse_history_filters({})
    assert ok is True
    assert empty_filters == {"diet": None, "max_calories": None, "status": "accepted"}
    # Invalid values
    assert collector.parse_history_filters({"diet": "unknown"})[0] is False
    assert collector.parse_history_filters({"max_calories": "lots"})[0] is False

### # Part 2 : Fix the AI and edit a recipe

def test_collect_corrections_keeps_names_with_their_quantities():
    form = MultiDict([("name", "Tofu"), ("quantity", "2 blocks"),
                      ("name", ""), ("quantity", "9"),            # blank name = removed
                      ("name", "rice"), ("quantity", "")])
    ok, edits = collector.collect_corrections(form)
    assert ok is True
    assert edits == [{"name": "Tofu", "quantity": "2 blocks"},
                     {"name": "rice", "quantity": ""}]

def test_collect_corrections_needs_at_least_one_ingredient():
    form = MultiDict([("name", ""), ("quantity", "")])
    ok, errors = collector.collect_corrections(form)
    assert ok is False and "at least one" in errors[0]

def test_collect_corrections_rejects_too_many_and_too_long():
    many = MultiDict([("name", f"item{n}") for n in range(21)])
    assert collector.collect_corrections(many)[0] is False
    long_name = MultiDict([("name", "x" * 51)])
    assert collector.collect_corrections(long_name)[0] is False

def test_collect_corrections_handles_missing_quantity_fields():
    form = MultiDict([("name", "egg")])                   # no quantity key at all
    assert collector.collect_corrections(form) == (True, [{"name": "egg", "quantity": ""}])

def test_collect_recipe_edit_success():
    form = {"notes": " less salt ", "ingredients_used": "rice\r\negg\n",
            "extra_ingredients": "soy sauce\n\noil"}
    ok, changes = collector.collect_recipe_edit(form)
    assert ok is True
    assert changes == {"notes": "less salt", "ingredients_used": ["rice", "egg"],
                       "extra_ingredients": ["soy sauce", "oil"]}

def test_collect_recipe_edit_allows_empty_lists_and_notes():
    ok, changes = collector.collect_recipe_edit({})
    assert ok is True
    assert changes == {"notes": "", "ingredients_used": [], "extra_ingredients": []}

def test_collect_recipe_edit_collects_every_error():
    form = {"notes": "n" * 501, "ingredients_used": "a" * 60, "extra_ingredients": "ok"}
    ok, errors = collector.collect_recipe_edit(form)
    assert ok is False and len(errors) == 2