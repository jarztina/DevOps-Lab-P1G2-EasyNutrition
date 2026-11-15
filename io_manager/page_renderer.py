"""Turns data into HTML pages with the Jinja templates."""

import logging

from flask import render_template

from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class PageRenderer:
    """One method per page. Every page also gets the logged-in user for the top bar."""

    def __init__(self, session_manager: SessionManager, diets: tuple[str, ...]):
        self._session = session_manager
        self._diets = diets

    def _page(self, template: str, **values) -> str:
        return render_template(template, user=self._session.current_user(), **values)

    def render_login(self, errors: list[str] | None = None) -> str:
        return self._page("login.html", errors=errors or [])

    def render_register(self, errors: list[str] | None = None) -> str:
        return self._page("register.html", errors=errors or [])

    def render_home(self, errors: list[str] | None = None,
                    recent: list[dict] | None = None) -> str:
        """The photo upload form, errors and recent scans."""
        return self._page("index.html", errors=errors or [], recent=recent or [],
                          diets=self._diets)

    def render_results(self, record: dict) -> str:
        """Detected food, accepted recipes and rejection reasons."""
        return self._page("results.html", record=record)

    def render_history(self, rows: list[dict], filters: dict) -> str:
        """Saved recipes and the history filter form."""
        return self._page("history.html", rows=rows, filters=filters,
                          diets=self._diets)

    def render_error(self, message: str) -> str:
        """A friendly error page without a traceback."""
        logger.warning("Showing error page: %s", message)
        return self._page("error.html", message=message)

    # ---- new in Part 2 ------------------------------------------------------

    def render_fix(self, scan: dict, errors: list[str] | None = None,
                   rows: list[dict] | None = None) -> str:
        """The 'fix the AI' page. rows = what to show in the boxes (default: the AI's items)."""
        return self._page("fix.html", scan=scan, errors=errors or [],
                          rows=rows if rows is not None else scan["detected_items"])

    def render_recipe_edit(self, recipe: dict, errors: list[str] | None = None) -> str:
        """The 'edit saved recipe' page."""
        return self._page("recipe_edit.html", recipe=recipe, errors=errors or [])