"""One look for the whole app: AutoEQ Local's colours (its app.css tokens), in light and dark, following Windows'
own setting (and changing with it). Every screen uses the same parts, so the EQ screen and the device screens match:

- a card: a QGroupBox (its title the card's heading) or a QFrame with the property card=true
- text roles (QLabel property "role"): "title" (a screen's big heading), "muted" (secondary text), "warn", "good"
- buttons: the property primary=true for the one main action of a card (Run, Set up…); others plain
- chips (QLabel role "chip"): a small value with its name ("Error 0.31 dB")
- graph colours: GRAPH (measurement, target, with EQ, the EQ itself) for pyqtgraph

apply(app) sets the style, palette and stylesheet; tokens() gives the colours in use (light or dark). With one of
Windows' contrast themes on (Settings > Accessibility > Contrast themes) the colours are Windows' own for it
(system_tokens(): window, text, highlight, links, grey text), followed when it's switched while the app runs.

The colours themselves are in theme_tokens.py (LIGHT, DARK), the stylesheet's rules in theme_sheet.py (in parts,
by kind of control; _stylesheet() joins them).
"""
import re

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QWidget

from ui import theme_sheet
from ui.theme_tokens import DARK, LIGHT  # (the colours: other code still takes LIGHT and DARK from here)

_state = {"dark": False, "listeners": []}


def dark():
    return _state["dark"]


def tokens():
    if _state.get("contrast"):
        return _state["contrast"]
    return DARK if _state["dark"] else LIGHT


def high_contrast():
    """Is one of Windows' contrast themes on?"""
    try:
        import ctypes

        class _HC(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwFlags", ctypes.c_uint), ("lpszDefaultScheme", ctypes.c_wchar_p)]
        hc = _HC()
        hc.cbSize = ctypes.sizeof(_HC)
        if ctypes.windll.user32.SystemParametersInfoW(0x0042, hc.cbSize, ctypes.byref(hc), 0):  # SPI_GETHIGHCONTRAST
            return bool(hc.dwFlags & 1)  # (HCF_HIGHCONTRASTON)
    except (AttributeError, OSError):
        pass
    return False


def system_tokens():
    """The app's colours from Windows' own for its contrast theme: few colours, each one Windows chose to be seen."""
    import ctypes

    def c(i):
        v = ctypes.windll.user32.GetSysColor(i)
        return f"#{v & 0xff:02x}{(v >> 8) & 0xff:02x}{(v >> 16) & 0xff:02x}"
    win, text, hi, hi_text, grey, link, face, face_text = c(5), c(8), c(13), c(14), c(17), c(26), c(15), c(18)
    return {"bg": win, "card": win, "ink": text, "ink2": text, "muted": text, "line": text, "field": win,
            "meas": link, "tgt": text, "c1": hi, "c2": grey, "c3": link, "c4": text, "c5": grey, "sel": hi,
            "shade": win, "warn": text, "err": text, "btn": hi, "good": text, "pill": win, "grid": grey,
            "on_btn": hi_text, "on_sel": hi_text, "face": face, "face_text": face_text, "sel_ink": hi_text,
            "sel_accent": hi_text}


def graph_colours():
    t = tokens()
    return {"meas": t["meas"], "target": t["tgt"], "with_eq": t["c1"], "eq": t["c2"], "grid": t["grid"],
            "axis": t["muted"], "bg": t["card"]}


def on_change(fn):
    """fn() after the theme changes (Windows switched light/dark): for what draws its own colours (the graph)."""
    _state["listeners"].append(fn)


def _stylesheet(t):
    """The whole app's stylesheet in the colours t: theme_sheet.py's parts, with the tick picture's path."""
    return theme_sheet.sheet(t, _tick())


def _tick():
    """A checkbox's tick (white, drawn here once and kept in the temporary folder: a stylesheet needs an image file)."""
    import os
    import tempfile
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPainter, QPen, QPixmap
    path = os.path.join(tempfile.gettempdir(), "autoeq-studio-tick.png")
    if not os.path.exists(path):
        pm = QPixmap(28, 28)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("white"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(6, 14.5), QPointF(11.5, 20), QPointF(22, 8)])
        p.end()
        part = f"{path}.{os.getpid()}.part"  # (whole or not at all: another copy may draw it at the same moment)
        pm.save(part, "PNG")
        try:
            os.replace(part, path)
        except OSError:  # (another copy put the same picture there first)
            try:
                os.remove(part)
            except OSError:
                pass
    return path.replace("\\", "/")


def _palette(t):
    p = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.Base, "field"), (QPalette.AlternateBase, "shade"),
                      (QPalette.Button, "field"), (QPalette.Text, "ink"), (QPalette.WindowText, "ink"),
                      (QPalette.ButtonText, "ink"), (QPalette.Highlight, "btn"), (QPalette.ToolTipBase, "card"),
                      (QPalette.ToolTipText, "ink"), (QPalette.PlaceholderText, "muted"), (QPalette.Link, "c1")):
        p.setColor(role, QColor(t[key]))
    p.setColor(QPalette.HighlightedText, QColor(t["on_sel"]))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(t["muted"]))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(t["muted"]))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(t["muted"]))
    return p


def _windows_dark():
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


class _Names(QObject):
    """For a screen reader, the first time a control is drawn: a button showing only a symbol (✕, ↺ …) is named by
    its tooltip ("Delete from the app"), a text box without a name by its grey placeholder ("Search the help…").
    A name given in the code stays."""

    def eventFilter(self, obj, e):
        if e.type() == QEvent.ThemeChange and isinstance(obj, QWidget) and obj.isWindow() and \
                bool(_state.get("contrast")) != high_contrast() and _state.get("following"):
            from PySide6.QtCore import QTimer  # (a contrast theme switched on or off while the app runs)
            from PySide6.QtWidgets import QApplication
            QTimer.singleShot(0, lambda: apply(QApplication.instance()))
        if e.type() == QEvent.Polish and isinstance(obj, QWidget) and not obj.accessibleName():
            from PySide6.QtWidgets import QAbstractButton, QLineEdit, QPlainTextEdit
            if isinstance(obj, QAbstractButton) and len(re.sub(r"[^\w]", "", obj.text())) < 2 and obj.toolTip():
                obj.setAccessibleName(obj.toolTip().split("\n")[0].rstrip("."))
            elif isinstance(obj, (QLineEdit, QPlainTextEdit)) and obj.placeholderText():
                obj.setAccessibleName(obj.placeholderText().split("\n")[0].rstrip("…. "))
        return False


def apply(app, dark=None, contrast=None):
    """Style the whole app (dark: True/False, or None to follow Windows; contrast: Windows' contrast theme's colours
    {token: colour}, False for none, or None to follow Windows), and keep following Windows."""
    _state["dark"] = _windows_dark() if dark is None else dark
    if contrast is None:  # (a light or dark look asked for, as the checks do: that one, not the contrast theme)
        contrast = system_tokens() if dark is None and high_contrast() else False
    _state["contrast"] = contrast or None
    app.setStyle("Fusion")  # (the same drawing everywhere: Windows' own style ignores parts of the stylesheet)
    t = tokens()
    app.setPalette(_palette(t))
    app.setStyleSheet(_stylesheet(t))
    if "names" not in _state:  # (once: names for a screen reader, _Names)
        _state["names"] = _Names(app)
        app.installEventFilter(_state["names"])
    for fn in list(_state["listeners"]):  # (what draws its own colours: the graph, Help's page)
        try:
            fn()
        except RuntimeError:  # (its window is gone)
            _state["listeners"].remove(fn)
    if dark is None and not _state.get("following"):
        _state["following"] = True
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(lambda *_: apply(app))
        except AttributeError:
            pass


def mark(widget, **props):
    """Set style properties (role="muted", primary=True, card=True …) and redraw with them."""
    for k, v in props.items():
        widget.setProperty(k, "true" if v is True else v)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    return widget
