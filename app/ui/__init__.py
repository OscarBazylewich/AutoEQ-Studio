"""The window, the tray's icons and the bits of Windows the interface uses (Qt).

Loaded before the rest of the window (start.py imports ui.app right after making Qt's application; the tests import
ui.*), this turns off a check PySide6 (6.4 and later) makes on every module imported after it: it reads each one's
source file to see whether the word "PySide6" is in it, for its optional `from __feature__ import ...` (Qt's names
written another way). No module of the app uses that (tests\\ui\\test_preload.py checks it), so the answer is always
"no": given at once, instead of some 800 files read (about half a second, and 18 MB of their text kept in memory) as
Make an EQ opens (2026-10-24). A module answered "no" is one PySide6 ignores for its features, as it would have been
anyway. On a PySide6 without that check, nothing changes.

It also has Python hand its lock to the window's thread at once when that asks (SWITCH, 2026-10-24). Each call from
Qt into Python needs the lock, and a thread of the app's own working meanwhile (the database lists, This PC's search,
Make an EQ's loading) kept each one waiting: ~2.5 ms at Python's usual 5 ms switch, ~3 ms at 1 ms (on Windows a wait of
1 ms or more lasts until the clock's next tick; under 1 ms, Python asks for the lock without waiting). A click while
Make an EQ was made ahead was drawn ~0.1 s late. At 0.5 ms each call waits ~7 µs. The cost is a thread waiting for
the lock spins on a core of its own meanwhile; two busy threads did their work about 1 % slower.

Layouts (2026-11-15): a layout goes into its place in another layout while it is empty, and gets its items after
that (placed()). If a layout that has items goes into a layout on a widget, PySide6 6.11 makes a Python object for
each of its items and keeps it. Qt deletes such an item itself when its widget goes to another place or is deleted,
and does not tell PySide6: the old object stays at the address of the deleted item. A new Qt object at the same
address then got the old object, and Python stopped with an access violation (the tests, now and then: a menu's
action in Find… and in the graph of Make an EQ). QLayout.itemAt, called from Python, makes such an object too: the
code keeps a reference to the part that it needs. The app's own layout classes (forms.FlowLayout, picker.Lines,
listen's rows, eq_page_parts.WrapRow) get each item from Qt as a Python object and keep it in a list, which Qt
empties through their takeAt: own_items() also empties it when Qt deletes the layout, so that no such object stays
after its layout.
tests\\helpers\\qt.py checks these rules in every test.
"""
import sys

SWITCH = 0.0005  # (seconds: Python's thread switch interval for the whole app)


def placed(outer, inner, *args):
    """inner, an empty layout, put into outer now (outer.addLayout with its other arguments: a stretch, or a grid's
    row, column and spans), so that its items come after: see "Layouts" above. Returns inner."""
    outer.addLayout(inner, *args)
    return inner


def own_items(layout):
    """A new list for the items of one of the app's own layout classes, emptied when Qt deletes the layout (see
    "Layouts" above)."""
    items = []
    layout.destroyed.connect(lambda *_args: items.clear())  # (the lambda holds the list only, not the layout)
    return items


def _never(module):
    return False


def _skip_pyside_source_check():
    try:
        import PySide6  # noqa: F401 - (sets the check up)
        feature = sys.modules.get("PySide6.support.feature")
        if callable(getattr(feature, "_mod_uses_pyside", None)) and \
                isinstance(getattr(feature, "pyside_feature_dict", None), dict):
            feature._mod_uses_pyside = _never
    except Exception:  # noqa: BLE001 - (another PySide6: its check stays as it is)
        pass


_skip_pyside_source_check()
sys.setswitchinterval(SWITCH)
