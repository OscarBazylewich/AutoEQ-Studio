"""Small helpers the window's screens share (ui\\window.py and its parts: ui\\devices_screen.py,
ui\\profiles_screen.py, ui\\settings_screen.py, ui\\setup_dialog.py): a line of words in the muted colour, and a
profile's EQ in a few words."""
from PySide6.QtWidgets import QLabel

from ui import theme


def muted(text=""):
    """A line of words in the theme's muted colour, wrapping."""
    lab = QLabel(text)
    lab.setWordWrap(True)
    theme.mark(lab, role="muted")
    return lab


def profile_line(p):
    """A profile's EQ in a few words ("5 filters, pre-amp -3.2 dB", or "GraphicEQ, …"); empty for no profile."""
    if not p:
        return ""
    n = p.get("filters", 0)
    what = "GraphicEQ" if p.get("graphic") and not n else f"{n} filter{'' if n == 1 else 's'}"
    return f"{what}, pre-amp {p.get('preamp', 0):g} dB"
