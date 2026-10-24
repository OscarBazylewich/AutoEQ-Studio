"""Small helpers the window's screens share (ui\\window.py and its parts: ui\\devices_screen.py,
ui\\profiles_screen.py, ui\\settings_screen.py, ui\\setup_dialog.py): a line of words in the muted colour, a profile's
EQ in a few words, a warning card as Windows 11 draws one (its sign, its words, its action), and Windows 11's symbol
in front of words. And one every window of the app uses: fit_to_screen, its size kept within the screen's room."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from ui import theme


def fit_to_screen(window, size, smallest=None):
    """A window kept within the screen's free room: the size it opens at and its smallest size no bigger than the room
    above the taskbar, less its title bar. A 1920 x 1080 laptop at 150 % has about 1280 x 672 px of it (569 high at
    175 %): opened taller, a window's bottom row (Close…) was under the taskbar, out of reach. size: (width, height) it
    opens at; smallest: (width, height), either one None to leave it to the window's own parts (smallest None: both).
    The screen: the one its owner (the main window) is on, where it opens; a window without one, the screen it opens
    on. Returns how many pixels lower than `smallest`'s height its smallest height had to be (0 on a screen with room,
    or without a smallest height): what its lists and chart give up, or scroll."""
    owner = window.parentWidget().window() if window.parentWidget() is not None else window
    free = owner.screen().availableGeometry()
    (w, h), (min_w, min_h) = size, smallest or (None, None)
    low = min_h
    if free.height() > 0:
        h = min(h, free.height() - 40)            # (its title bar above it: about 31 px at 150 %)
        if min_h is not None:
            low = min(min_h, free.height() - 80)  # (and some room to spare)
    if free.width() > 0:
        w = min(w, free.width() - 20)
        if min_w is not None:
            min_w = min(min_w, free.width() - 40)
    if min_w is not None:
        window.setMinimumWidth(min_w)
    if low is not None:
        window.setMinimumHeight(low)
    window.resize(w, h if low is None else max(h, low))
    return 0 if min_h is None else min_h - low


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
