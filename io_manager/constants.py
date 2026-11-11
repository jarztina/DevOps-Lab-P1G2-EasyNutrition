"""Shared IO settings. Every IO class imports its limits from here."""

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MIN_CALORIES = 100
MAX_CALORIES = 3000
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 72
ALLOWED_DIETS = ("none", "vegetarian", "vegan", "halal")

# New in Part 2 (edit and fix screens)
MAX_INGREDIENTS = 20        # most ingredients a user can keep after fixing
MAX_INGREDIENT_LENGTH = 50  # longest ingredient name
MAX_NOTES_LENGTH = 500      # longest recipe note
MAX_LIST_ITEMS = 30         # most lines in an ingredient list on the edit page