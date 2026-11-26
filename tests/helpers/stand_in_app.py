"""The app that a window (ui.window.Window) talks to, stood in, for tests\\ui. Before the test audit of 2026-11-25
(candidate 59) four Python scripts and tests\\ui\\conftest.py each had their own copy of it.

StubApp   what the window asks of the app (selftest.py's Stub, lines 340-357): no hotkey problem, never this PC's
          Run key, Online / Offline through net. Each one keeps its own list of the titles it said in the tray (said).
STUB_APP  StubApp's source text, for a test's Python of its own (helpers.subproc.run_python): a script puts it after
          its imports, then makes StubApp().

It imports no module of the app but net, and that only when set_offline is called: tests\\ui\\conftest.py imports it
for every test of the folder, and app\\tools\\relevant_tests.py counts a helper's imports for each test that loads
it (tests\\infra\\test_relevant.py: a change to ui\\devices_screen.py chooses fewer than 25 test files). The
Switcher and the window on one stand-in device are in helpers.window_app, imported only by the tests that use them.
"""
import inspect


class StubApp:
    """What the window asks of the app."""

    hotkey_problem = ""

    def __init__(self):
        self.said = []

    def tray_message(self, title, text):
        self.said.append(title)

    @staticmethod
    def autostart_on():
        return False  # (never this PC's Run key)

    def set_autostart(self, on):
        pass

    @staticmethod
    def set_offline(on):
        import net
        net.set_offline(on)


STUB_APP = inspect.getsource(StubApp)
