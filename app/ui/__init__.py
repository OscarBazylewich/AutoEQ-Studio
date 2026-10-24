"""The window, the tray's icons and the bits of Windows the interface uses (Qt).

Loaded before the rest of the window (start.py imports ui.app right after making Qt's application; the tests import
ui.*), this turns off a check PySide6 (6.4 and later) makes on every module imported after it: it reads each one's
source file to see whether the word "PySide6" is in it, for its optional `from __feature__ import ...` (Qt's names
written another way). No module of the app uses that (tests\\ui\\test_preload.py checks it), so the answer is always
"no": given at once, instead of some 800 files read (about half a second, and 18 MB of their text kept in memory) as
Make an EQ opens (2026-10-24). A module answered "no" is one PySide6 ignores for its features, as it would have been
anyway. On a PySide6 without that check, nothing changes.
"""


def _never(module):
    return False


def _skip_pyside_source_check():
    import sys
    try:
        import PySide6  # noqa: F401 - (sets the check up)
        feature = sys.modules.get("PySide6.support.feature")
        if callable(getattr(feature, "_mod_uses_pyside", None)) and \
                isinstance(getattr(feature, "pyside_feature_dict", None), dict):
            feature._mod_uses_pyside = _never
    except Exception:  # noqa: BLE001 - (another PySide6: its check stays as it is)
        pass


_skip_pyside_source_check()
