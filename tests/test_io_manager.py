"""Tests for the IOManager front door (Gabriel). It must hand work to the right part."""
from io_manager.io_manager import IOManager


class Spy:
    """Records every call so we can see where IOManager sent the work."""

    def __init__(self, name):
        self.name = name

    def __getattr__(self, method):
        return lambda *args, **kwargs: (self.name, method, args)


def make_io():
    return IOManager(collector=Spy("collector"), sessions=Spy("sessions"),
                     renderer=Spy("renderer"))


def test_input_methods_go_to_the_collector():
    io = make_io()
    assert io.collect_input({}, {})[0] == "collector"
    assert io.collect_corrections({})[1] == "collect_corrections"
    assert io.collect_recipe_edit({})[1] == "collect_recipe_edit"
    assert io.parse_history_filters({})[1] == "parse_history_filters"
    assert io.collect_credentials({}, True)[2] == ({}, True)


def test_session_methods_go_to_the_session_manager():
    io = make_io()
    assert io.login_user(1, "ann")[0] == "sessions"
    assert io.current_user()[1] == "current_user"
    assert io.redirect_to("home")[2] == ("home",)


def test_page_methods_go_to_the_renderer():
    io = make_io()
    assert io.render_login(["e"])[:2] == ("renderer", "render_login")
    assert io.render_register()[1] == "render_register"
    assert io.render_home()[1] == "render_home"
    assert io.render_results({})[1] == "render_results"
    assert io.render_history([], {})[1] == "render_history"
    assert io.render_error("x")[1] == "render_error"
    assert io.render_fix({"scan_id": 1})[1] == "render_fix"
    assert io.render_recipe_edit({"id": 1})[1] == "render_recipe_edit"


def test_default_io_manager_builds_its_own_parts():
    io = IOManager()
    assert io._collector is not None and io._sessions is not None and io._renderer is not None