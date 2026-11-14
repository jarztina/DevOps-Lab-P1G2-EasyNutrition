import io
import pytest
from werkzeug.datastructures import FileStorage
from io_manager.constants import MAX_UPLOAD_BYTES
from io_manager.validators import (
    CaloriesValidator, DietValidator, NotesValidator, PasswordValidator,
    TextListValidator, UploadValidator, UsernameValidator, Validator,
)
def make_file_storage(content: bytes, filename: str) -> FileStorage:
    """Build a FileStorage object from raw bytes."""
    return FileStorage(stream=io.BytesIO(content), filename=filename)

def test_validate_username_accepts_valid():
    ok, name = UsernameValidator().validate("justin_01")
    assert ok is True
    assert name == "justin_01"

def test_validate_username_lowercases_and_strips():
    ok, name = UsernameValidator().validate("  User_NAME_99  ")
    assert ok is True
    assert name == "user_name_99"

def test_validate_username_rejects_invalid_chars_and_length():
    assert UsernameValidator().validate("ab")[0] is False  # too short (< 3)
    assert UsernameValidator().validate("a" * 31)[0] is False  # too long (> 30)
    assert UsernameValidator().validate("user name")[0] is False  # spaces disallowed
    assert UsernameValidator().validate("user@name")[0] is False  # special chars disallowed

def test_validate_password_boundaries():
    assert PasswordValidator().validate("1234567")[0] is False  # < 8 chars
    assert PasswordValidator().validate("12345678")[0] is True  # exact min
    assert PasswordValidator().validate("a" * 72)[0] is True  # exact max
    assert PasswordValidator().validate("a" * 73)[0] is False  # > 72 chars

def test_validate_calories():
    assert CaloriesValidator().validate("500") == (True, 500)
    assert CaloriesValidator().validate(" 100 ") == (True, 100)
    assert CaloriesValidator().validate("3000") == (True, 3000)
    # Out of range or invalid format
    assert CaloriesValidator().validate("99")[0] is False
    assert CaloriesValidator().validate("3001")[0] is False
    assert CaloriesValidator().validate("five_hundred")[0] is False
    assert CaloriesValidator().validate("")[0] is False

def test_validate_diet():
    for diet in ["none", "vegetarian", "vegan", "halal"]:
        assert DietValidator().validate(diet) == (True, diet)
        assert DietValidator().validate(f"  {diet.upper()}  ") == (True, diet)
    assert DietValidator().validate("keto")[0] is False
    assert DietValidator().validate("")[0] is False

def test_detect_media_type():
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    other_bytes = b"GIF89a..."
    assert UploadValidator.detect_media_type(jpeg_bytes) == "image/jpeg"
    assert UploadValidator.detect_media_type(png_bytes) == "image/png"
    assert UploadValidator.detect_media_type(other_bytes) is None

def test_validate_upload_valid_files():
    jpeg_file = make_file_storage(b"\xff\xd8\xff\xe0fakejpegdata", "lunch.jpg")
    ok, data = UploadValidator().validate(jpeg_file)
    assert ok is True
    assert data["media_type"] == "image/jpeg"
    assert data["image_name"] == "lunch.jpg"
    assert data["image_bytes"].startswith(b"\xff\xd8\xff")

def test_validate_upload_rejects_empty_missing_and_fake_extension():
    # None or empty filename
    assert UploadValidator().validate(None)[0] is False
    assert UploadValidator().validate(make_file_storage(b"", ""))[0] is False

     # Empty payload
    empty_file = make_file_storage(b"", "empty.jpg")
    ok, msg = UploadValidator().validate(empty_file)
    assert ok is False
    assert "empty" in msg

    # Text file disguised with .jpg extension (fails magic byte check)
    spoofed_file = make_file_storage(b"this is plain text", "fake.jpg")
    ok, msg = UploadValidator().validate(spoofed_file)
    assert ok is False
    assert "Only JPG or PNG" in msg

def test_validate_upload_oversized_file():
    # 5 MB + 1 byte
    too_big_bytes = b"\xff\xd8\xff" + (b"0" * (MAX_UPLOAD_BYTES + 1))
    big_file = make_file_storage(too_big_bytes, "huge.jpg")
    ok, msg = UploadValidator().validate(big_file)
    assert ok is False
    assert "Photo is too big" in msg

### Part 2

def test_validators_share_one_contract():
    for validator in (UsernameValidator(), PasswordValidator(), CaloriesValidator(),
                      DietValidator(), UploadValidator(), NotesValidator(),
                      TextListValidator("Ingredient", 5)):
        assert isinstance(validator, Validator)
    with pytest.raises(TypeError):
        Validator()

def test_text_list_cleans_blanks_spaces_and_duplicates():
    validator = TextListValidator("Ingredient", 5)
    ok, items = validator.validate(["  rice ", "", "Egg", "egg", "spring   onion"])
    assert ok is True and items == ["rice", "Egg", "spring onion"]

def test_text_list_rejects_empty_when_not_allowed():
    validator = TextListValidator("Ingredient", 5, allow_empty=False)
    assert validator.validate(["", "  "])[0] is False
    assert TextListValidator("Ingredient", 5).validate([""]) == (True, [])

def test_text_list_rejects_too_long_and_too_many():
    validator = TextListValidator("Ingredient", 2, max_length=10)
    ok, message = validator.validate(["x" * 11])
    assert ok is False and "too long" in message
    ok, message = validator.validate(["a", "b", "c"])
    assert ok is False and "at most 2" in message

def test_notes_validator():
    validator = NotesValidator()
    assert validator.validate("  tasty  ") == (True, "tasty")
    assert validator.validate("") == (True, "")
    ok, message = validator.validate("x" * 501)
    assert ok is False and "at most 500" in message