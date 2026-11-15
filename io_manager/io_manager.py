"""The IO Manager: one front door for input, sessions and pages."""
from .constants import ALLOWED_DIETS
from .input_collector import InputCollector
from .page_renderer import PageRenderer
from .session_manager import SessionManager


class IOManager:
    """Composition: it builds an InputCollector, a SessionManager and a PageRenderer."""

    def __init__(self, collector: InputCollector | None = None,
                 sessions: SessionManager | None = None,
                 renderer: PageRenderer | None = None):
        self._collector = collector or InputCollector()
        self._sessions = sessions or SessionManager()
        self._renderer = renderer or PageRenderer(self._sessions, ALLOWED_DIETS)

    # ---- input (InputCollector) ---------------------------------------------
    def collect_credentials(self, form, is_register=False):
        return self._collector.collect_credentials(form, is_register)

    def collect_input(self, form, files):
        return self._collector.collect_input(form, files)

    def parse_history_filters(self, args):
        return self._collector.parse_history_filters(args)

    def collect_corrections(self, form):
        return self._collector.collect_corrections(form)

    def collect_recipe_edit(self, form):
        return self._collector.collect_recipe_edit(form)

    # ---- sessions (SessionManager) ------------------------------------------
    def login_user(self, user_id, username):
        return self._sessions.login_user(user_id, username)

    def logout_user(self):
        return self._sessions.logout_user()

    def current_user(self):
        return self._sessions.current_user()

    def redirect_to(self, endpoint, **values):
        return self._sessions.redirect_to(endpoint, **values)

    # ---- pages (PageRenderer) -----------------------------------------------
    def render_login(self, errors=None):
        return self._renderer.render_login(errors)

    def render_register(self, errors=None):
        return self._renderer.render_register(errors)

    def render_home(self, errors=None, recent=None):
        return self._renderer.render_home(errors, recent)

    def render_results(self, record):
        return self._renderer.render_results(record)

    def render_history(self, rows, filters):
        return self._renderer.render_history(rows, filters)

    def render_error(self, message):
        return self._renderer.render_error(message)

    def render_fix(self, scan, errors=None, rows=None):
        return self._renderer.render_fix(scan, errors, rows)

    def render_recipe_edit(self, recipe, errors=None):
        return self._renderer.render_recipe_edit(recipe, errors)