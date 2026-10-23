"""Small helpers the window's screens share (ui\\window.py and its parts: ui\\devices_screen.py,
ui\\profiles_screen.py, ui\\settings_screen.py, ui\\setup_dialog.py): a line of words in the muted colour, a profile's
EQ in a few words, a warning card as Windows 11 draws one (its sign, its words, its action), and Windows 11's symbol
in front of words."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

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


def glyph(name, role=None, said=""):
    """Windows 11's symbol `name` (ui\\icons.py's GLYPHS: "warning", "clock" …) as a label in front of words, in the
    colour of its role ("warn" …) or of a rule for its objectName: the stylesheet colours it, so it follows light,
    dark and the accent by itself. said: what a screen reader reads for it ("Warning")."""
    from PySide6.QtGui import QFontDatabase
    from ui import icons
    lab = QLabel(chr(int(icons.GLYPHS[name], 16)))
    font = lab.font()
    font.setFamily("Segoe Fluent Icons" if "Segoe Fluent Icons" in QFontDatabase.families() else "Segoe MDL2 Assets")
    lab.setFont(font)  # (only the family: the size is the stylesheet's, the colour its role's)
    lab.setAlignment(Qt.AlignCenter)
    lab.setAccessibleName(said or name.capitalize())
    theme.mark(lab, glyph=True, **({"role": role} if role else {}))
    return lab


def warning_card(text, button=None):
    """A warning as Windows 11 shows one (an InfoBar): the warning sign, the words (wrapping), and the action's button
    at the right, on the theme's warning colours (card="warn"). Returns (card, its words' label)."""
    card = QFrame()
    theme.mark(card, card="warn")
    row = QHBoxLayout(card)
    row.setContentsMargins(8, 6, 8, 6)
    row.setSpacing(12)
    row.addWidget(glyph("warning", role="warn"))
    words = QLabel(text)
    words.setWordWrap(True)
    row.addWidget(words, 1)
    if button is not None:
        row.addWidget(button, 0, Qt.AlignVCenter)
    return card, words
