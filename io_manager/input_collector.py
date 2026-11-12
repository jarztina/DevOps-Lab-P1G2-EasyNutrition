"""Collects and checks everything the user sends from a form."""
from collections.abc import Mapping
from werkzeug.datastructures import FileStorage
from .constants import MAX_INGREDIENTS, MAX_LIST_ITEMS
from .validators import (
    CaloriesValidator, DietValidator, NotesValidator, PasswordValidator,
    TextListValidator, UploadValidator, UsernameValidator,
)

class InputCollector:
    """Uses the validators (composition) and returns (ok, data) or (False, [errors])."""
    def __init__(self):
        self._username = UsernameValidator()
        self._password = PasswordValidator()
        self._calories = CaloriesValidator()
        self._diet = DietValidator()
        self._upload = UploadValidator()
        self._ingredients = TextListValidator(
            "Ingredient", MAX_INGREDIENTS, allow_empty=False)
        self._recipe_lines = TextListValidator("Ingredient list", MAX_LIST_ITEMS)
        self._notes = NotesValidator()

    def collect_credentials(
        self, form: Mapping[str, str], is_register: bool = False
    ) -> tuple[bool, dict | list[str]]:
        """Collect validated login or registration credentials, or all form errors."""
        errors = []
        ok_name, username = self._username.validate(form.get("username", ""))
        if not ok_name:
            errors.append(username)
        password = form.get("password", "")
        if is_register:
            ok_pw, pw_message = self._password.validate(password)
            if not ok_pw:
                errors.append(pw_message)
            elif password != form.get("confirm_password", ""):
                errors.append("The two passwords do not match.")
        elif password == "":
            errors.append("Please type your password.")
        if errors:
            return False, errors
        return True, {"username": username, "password": password}
    
    def collect_input(
        self, form: Mapping[str, str], files: Mapping[str, FileStorage]
    ) -> tuple[bool, dict | list[str]]:
        """Validate calories, diet and photo together and collect every error."""
        errors = []
        ok_cal, calories = self._calories.validate(form.get("calorie_limit", ""))
        if not ok_cal:
            errors.append(calories)
        ok_diet, diet = self._diet.validate(form.get("diet", "none"))
        if not ok_diet:
            errors.append(diet)
        ok_img, image = self._upload.validate(files.get("image"))
        if not ok_img:
            errors.append(image)
        if errors:
            return False, errors
        data = dict(image)
        data["calorie_limit"] = calories
        data["diet"] = diet
        return True, data
    
    def parse_history_filters(self, args: Mapping[str, str]) -> tuple[bool, dict | str]:
        """Validate history URL filters using the data_manager argument names."""
        filters = {"diet": None, "max_calories": None, "status": "accepted"}
        diet = args.get("diet", "").strip().lower()
        if diet:
            ok, value = self._diet.validate(diet)
            if not ok:
                return False, value
            
            filters["diet"] = value
        max_cal = args.get("max_calories", "").strip()

        if max_cal:
            ok, value = self._calories.validate(max_cal)
            if not ok:
                return False, value
            filters["max_calories"] = value
        return True, filters

### Part 2

 # ---- new in Part 2 -----------------------------------------------------
    def collect_corrections(self, form) -> tuple[bool, list[dict] | list[str]]:
        """The 'fix the AI' form: rows of name + quantity. A blank name removes the row."""
        names = form.getlist("name")
        quantities = form.getlist("quantity")
        quantities += [""] * (len(names) - len(quantities))   # never fewer quantities
        rows = [(n.strip(), q.strip()) for n, q in zip(names, quantities) if n.strip()]
        ok, cleaned = self._ingredients.validate([n for n, _ in rows])
        if not ok:
            return False, [cleaned]
        edits = []
        for name in cleaned:
            quantity = next((q for n, q in rows if n.lower() == name.lower()), "")
            edits.append({"name": name, "quantity": quantity[:30]})
        return True, edits
    def collect_recipe_edit(self, form) -> tuple[bool, dict | list[str]]:
        """The 'edit saved recipe' form: notes plus two ingredient lists (one per line)."""
        errors = []
        ok_notes, notes = self._notes.validate(form.get("notes", ""))
        if not ok_notes:
            errors.append(notes)
        ok_used, used = self._recipe_lines.validate(form.get("ingredients_used", "").splitlines())
        if not ok_used:
            errors.append(used)
        ok_extra, extra = self._recipe_lines.validate(
            form.get("extra_ingredients", "").splitlines())
        if not ok_extra:
            errors.append(extra)
        if errors:
            return False, errors
        return True, {"notes": notes, "ingredients_used": used, "extra_ingredients": extra}