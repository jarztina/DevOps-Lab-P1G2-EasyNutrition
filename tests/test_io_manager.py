import io
from flask import Flask
from werkzeug.datastructures import FileStorage
import io_manager

# Minimal Flask app fixture to provide request/session contexts for Flask helpers
app = Flask(__name__)
app.config["SECRET_KEY"] = "test-secret"


def make_file_storage(content: bytes, filename: str) -> FileStorage:
    """Helper to construct a FileStorage object from raw bytes."""
    return FileStorage(stream=io.BytesIO(content), filename=filename)

# Credential Validation Tests

def test_validate_username_accepts_valid():
    ok, name = io_manager.validate_username("justin_01")
    assert ok is True
    assert name == "justin_01"


def test_validate_username_lowercases_and_strips():
    ok, name = io_manager.validate_username("  User_NAME_99  ")
    assert ok is True
    assert name == "user_name_99"


def test_validate_username_rejects_invalid_chars_and_length():
    assert io_manager.validate_username("ab")[0] is False  # too short (< 3)
    assert io_manager.validate_username("a" * 31)[0] is False  # too long (> 30)
    assert io_manager.validate_username("user name")[0] is False  # spaces disallowed
    assert io_manager.validate_username("user@name")[0] is False  # special chars disallowed


def test_validate_password_boundaries():
    assert io_manager.validate_password("1234567")[0] is False  # < 8 chars
    assert io_manager.validate_password("12345678")[0] is True  # exact min
    assert io_manager.validate_password("a" * 72)[0] is True  # exact max
    assert io_manager.validate_password("a" * 73)[0] is False  # > 72 chars


def test_collect_credentials_login_flow():
    # Valid login credentials
    form = {"username": "user_01", "password": "my_password"}
    ok, creds = io_manager.collect_credentials(form, is_register=False)
    assert ok is True
    assert creds == {"username": "user_01", "password": "my_password"}

    # Missing password on login
    bad_form = {"username": "user_01", "password": ""}
    ok, errors = io_manager.collect_credentials(bad_form, is_register=False)
    assert ok is False
    assert "Please type your password." in errors


def test_collect_credentials_register_flow():
    # Valid registration
    form = {
        "username": "user_01",
        "password": "valid_pass_123",
        "confirm_password": "valid_pass_123",
    }
    ok, creds = io_manager.collect_credentials(form, is_register=True)
    assert ok is True
    assert creds["username"] == "user_01"

    # Mismatched passwords
    mismatch_form = {
        "username": "user_01",
        "password": "valid_pass_123",
        "confirm_password": "different_pass",
    }
    ok, errors = io_manager.collect_credentials(mismatch_form, is_register=True)
    assert ok is False
    assert "The two passwords do not match." in errors

    # Weak password on registration
    weak_form = {
        "username": "user_01",
        "password": "123",
        "confirm_password": "123",
    }
    ok, errors = io_manager.collect_credentials(weak_form, is_register=True)
    assert ok is False
    assert any("at least" in err for err in errors)


# Calorie & Diet Validation Tests

def test_validate_calories():
    assert io_manager.validate_calories("500") == (True, 500)
    assert io_manager.validate_calories(" 100 ") == (True, 100)
    assert io_manager.validate_calories("3000") == (True, 3000)

    # Out of range or invalid format
    assert io_manager.validate_calories("99")[0] is False
    assert io_manager.validate_calories("3001")[0] is False
    assert io_manager.validate_calories("five_hundred")[0] is False
    assert io_manager.validate_calories("")[0] is False


def test_validate_diet():
    for diet in ["none", "vegetarian", "vegan", "halal"]:
        assert io_manager.validate_diet(diet) == (True, diet)
        assert io_manager.validate_diet(f"  {diet.upper()}  ") == (True, diet)

    assert io_manager.validate_diet("keto")[0] is False
    assert io_manager.validate_diet("")[0] is False


# Image & Upload Validation Tests

def test_detect_media_type():
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    other_bytes = b"GIF89a..."

    assert io_manager.detect_media_type(jpeg_bytes) == "image/jpeg"
    assert io_manager.detect_media_type(png_bytes) == "image/png"
    assert io_manager.detect_media_type(other_bytes) is None


def test_validate_upload_valid_files():
    jpeg_file = make_file_storage(b"\xff\xd8\xff\xe0fakejpegdata", "lunch.jpg")
    ok, data = io_manager.validate_upload(jpeg_file)
    assert ok is True
    assert data["media_type"] == "image/jpeg"
    assert data["image_name"] == "lunch.jpg"
    assert data["image_bytes"].startswith(b"\xff\xd8\xff")


def test_validate_upload_rejects_empty_missing_and_fake_extension():
    # None or empty filename
    assert io_manager.validate_upload(None)[0] is False
    assert io_manager.validate_upload(make_file_storage(b"", ""))[0] is False

    # Empty payload
    empty_file = make_file_storage(b"", "empty.jpg")
    ok, msg = io_manager.validate_upload(empty_file)
    assert ok is False
    assert "empty" in msg

    # Text file disguised with .jpg extension (fails magic byte check)
    spoofed_file = make_file_storage(b"this is plain text", "fake.jpg")
    ok, msg = io_manager.validate_upload(spoofed_file)
    assert ok is False
    assert "Only JPG or PNG" in msg


def test_validate_upload_oversized_file():
    # 5 MB + 1 byte
    too_big_bytes = b"\xff\xd8\xff" + (b"0" * (io_manager.MAX_UPLOAD_BYTES + 1))
    big_file = make_file_storage(too_big_bytes, "huge.jpg")
    ok, msg = io_manager.validate_upload(big_file)
    assert ok is False
    assert "Photo is too big" in msg


# Form Collection Tests

def test_collect_input_success():
    form = {"calorie_limit": "650", "diet": "vegetarian"}
    files = {"image": make_file_storage(b"\xff\xd8\xffphoto", "food.jpg")}

    ok, result = io_manager.collect_input(form, files)
    assert ok is True
    assert result["calorie_limit"] == 650
    assert result["diet"] == "vegetarian"
    assert result["image_name"] == "food.jpg"
    assert result["media_type"] == "image/jpeg"


def test_collect_input_aggregates_multiple_errors():
    # All fields invalid: bad calories, bad diet, bad upload
    form = {"calorie_limit": "50", "diet": "pescatarian"}
    files = {"image": make_file_storage(b"not-an-image", "test.txt")}

    ok, errors = io_manager.collect_input(form, files)
    assert ok is False
    assert len(errors) == 3


def test_parse_history_filters():
    # All filters present
    args = {"diet": "vegan", "max_calories": "600"}
    ok, filters = io_manager.parse_history_filters(args)
    assert ok is True
    assert filters == {"diet": "vegan", "max_calories": 600, "status": "accepted"}

    # Empty/default query parameters
    ok, empty_filters = io_manager.parse_history_filters({})
    assert ok is True
    assert empty_filters == {"diet": None, "max_calories": None, "status": "accepted"}

    # Invalid values
    assert io_manager.parse_history_filters({"diet": "unknown"})[0] is False
    assert io_manager.parse_history_filters({"max_calories": "lots"})[0] is False


def test_session_login_logout_and_current_user():
    with app.test_request_context("/"):
        assert io_manager.current_user() is None

        io_manager.login_user(10, "tester")
        assert io_manager.current_user() == {"id": 10, "username": "tester"}

        io_manager.logout_user()
        assert io_manager.current_user() is None