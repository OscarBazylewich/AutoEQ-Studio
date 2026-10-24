"""One look for the whole app: Windows 11's (Fluent's colours, type and shapes; the user's choice from pictures,
2026-10-23), in light and dark following Windows' own setting, with Windows' own accent colour (Settings >
Personalization > Colors), both followed when they change. Every screen uses the same parts, so the EQ screen and the
device screens match:

- a card: a QGroupBox (its title the card's heading) or a QFrame with the property card=true
- text roles (QLabel property "role"): "title" (a screen's big heading), "muted" (secondary text), "warn", "good"
- buttons: the property primary=true for the one main action of a card (Run, Set up…: the accent); others plain
- chips (QLabel role "chip"): a small value with its name ("Error 0.31 dB")
- graph colours: graph_colours() (measurement, target, with EQ, the EQ itself) for pyqtgraph: fixed, never the accent
- icons: ui\\icons.py's put(button, name), Windows 11's symbols beside a button's words

apply(app) sets the style, the font (Segoe UI Variable, Windows 11's; Segoe UI on Windows 10), the palette and the
stylesheet; tokens() gives the colours in use. With one of Windows' contrast themes on (Settings > Accessibility >
Contrast themes) the colours are Windows' own for it (system_tokens(): window, text, highlight, links, grey text),
followed when it's switched while the app runs.

The colours themselves are in theme_tokens.py (build(): one theme's, with an accent), the stylesheet's rules in
theme_sheet.py (in parts, by kind of control; _stylesheet() joins them with the pictures _pictures() draws).
"""
import re

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QWidget

from ui import theme_sheet, theme_tokens
from ui.theme_tokens import DARK, LIGHT  # (the colours with Windows' default accent: other code still takes them)

_state = {"dark": False, "listeners": []}
FONT = "Segoe UI Variable Text"  # (Windows 11's; Windows 10 has Segoe UI)
ACCENT_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"


def dark():
    return _state["dark"]


def tokens():
    if _state.get("contrast"):
        return _state["contrast"]
    return _state.get("tokens") or (DARK if _state["dark"] else LIGHT)


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


def accent_palette():
    """Windows' accent colour as its seven shades (Light 3, Light 2, Light 1, the accent, Dark 1, Dark 2, Dark 3), as
    Windows keeps them for its own apps; Windows' default blue when they can't be read."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ACCENT_KEY) as k:
            data = winreg.QueryValueEx(k, "AccentPalette")[0]
    except OSError:
        return theme_tokens.DEFAULT_ACCENT
    if not isinstance(data, bytes) or len(data) < 28:
        return theme_tokens.DEFAULT_ACCENT
    return tuple(f"#{data[i]:02x}{data[i + 1]:02x}{data[i + 2]:02x}" for i in range(0, 28, 4))


def system_tokens():
    """The app's colours from Windows' own for its contrast theme: few colours, each one Windows chose to be seen."""
    import ctypes

    def c(i):
        v = ctypes.windll.user32.GetSysColor(i)
        return f"#{v & 0xff:02x}{(v >> 8) & 0xff:02x}{(v >> 16) & 0xff:02x}"
    win, text, hi, hi_text, grey, link, face, face_text = c(5), c(8), c(13), c(14), c(17), c(26), c(15), c(18)
    t = {k: win for k in ("bg", "card", "menu", "field", "field_hover", "field_press", "field_focus", "field_disabled",
                          "subtle", "subtle_hover", "subtle_press", "alt_row", "check_fill", "check_hover", "thumb",
                          "warn_bg", "pill", "accent_soft", "shade")}
    t.update({k: text for k in ("ink", "ink2", "muted", "line", "stroke", "stroke_bottom", "strong", "track",
                                "scroll", "warn", "err", "good", "tgt", "c4", "accent_soft_line")})
    t.update({k: hi for k in ("subtle_sel", "scroll_hover", "accent", "accent_hover", "accent_press", "accent_bottom",
                              "with_eq", "c1", "btn", "sel")})
    t.update({k: hi_text for k in ("on_accent", "on_btn", "on_sel", "sel_ink", "sel_accent")})
    t.update(disabled=grey, accent_disabled=grey, on_accent_disabled=win, meas=link, c2=grey, c3=link, c5=grey,
             grid=grey, accent_text=link, face=face, face_text=face_text)
    return t


def graph_colours():
    t = tokens()
    return {"meas": t["meas"], "target": t["tgt"], "with_eq": t["with_eq"], "eq": t["c2"], "grid": t["grid"],
            "axis": t["muted"], "bg": t["card"]}


def on_change(fn):
    """fn() after the theme changes (Windows switched light/dark or its accent): for what draws its own colours (the
    graph, the icons)."""
    _state["listeners"].append(fn)


def _stylesheet(t):
    """The whole app's stylesheet in the colours t: theme_sheet.py's parts, with the pictures' paths."""
    return theme_sheet.sheet(t, _pictures(t))


def _pictures(t):
    """The pictures a stylesheet needs as files, in t's colours: the tick (on the accent), Windows 11's chevrons
    (down: drop-downs, number boxes, buttons with a menu, an open fold; up: number boxes; right: a closed fold, a
    menu's submenu), the accent's bars that mark what's chosen (the one beside a chosen row in the chosen row's text
    colour when the accent wouldn't keep 3:1 on its fill: in a contrast theme they're both Windows' highlight, and the
    bar wasn't there to see). Drawn once each into the temporary folder (named by their colour), whole: a copy draws
    into a file of its own and puts it in place."""
    import os
    import tempfile
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QPainter, QPen, QPixmap

    def tick(p):
        p.setPen(QPen(QColor(t["on_accent"]), 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(7, 14.5), QPointF(11.5, 19), QPointF(21, 9)])

    def chevron(way):
        def draw(p):  # (the same chevron each way: down's turned up, or to the right)
            p.setPen(QPen(QColor(t["ink2"]), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            points = {"down": ((5, 9), (12, 16), (19, 9)), "up": ((5, 16), (12, 9), (19, 16)),
                      "right": ((9, 5), (16, 12), (9, 19))}[way]
            p.drawPolyline([QPointF(x, y) for x, y in points])
        return draw

    def bar(w, h, colour):
        def draw(p):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(colour))
            p.drawRoundedRect(QRectF(0, 0, w, h), min(w, h) / 2, min(w, h) / 2)
        return draw
    beside = t["accent"] if theme_tokens.contrast(t["accent"], t["sel"]) >= 3 else t["sel_ink"]  # (a chosen row's)
    out = {}
    for name, colour, (w, h), draw in (("tick", t["on_accent"], (28, 28), tick),
                                        ("chevron", t["ink2"], (24, 24), chevron("down")),
                                        ("chevron_up", t["ink2"], (24, 24), chevron("up")),
                                        ("chevron_right", t["ink2"], (24, 24), chevron("right")),
                                        ("pill_h", t["accent"], (16, 3), bar(16, 3, t["accent"])),
                                        ("pill_v", beside, (3, 16), bar(3, 16, beside))):
        path = os.path.join(tempfile.gettempdir(), f"autoeq-studio-{name}-{colour.lstrip('#')}.png")
        if not os.path.exists(path):
            pm = QPixmap(w, h)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            draw(p)
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
        out[name] = path.replace("\\", "/")
    return out


def _palette(t):
    p = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.Base, "field"), (QPalette.AlternateBase, "subtle"),
                      (QPalette.Button, "field"), (QPalette.Text, "ink"), (QPalette.WindowText, "ink"),
                      (QPalette.ButtonText, "ink"), (QPalette.Highlight, "accent"), (QPalette.ToolTipBase, "menu"),
                      (QPalette.ToolTipText, "ink"), (QPalette.PlaceholderText, "muted"), (QPalette.Link, "accent_text"),
                      (QPalette.Accent, "accent")):
        p.setColor(role, QColor(t[key]))
    p.setColor(QPalette.HighlightedText, QColor(t["on_accent"]))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(t["disabled"]))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(t["disabled"]))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(t["disabled"]))
    return p


def _windows_dark():
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


class _Names(QObject):
    """For a screen reader, the first time a control is drawn: a button showing only a symbol (✕, ↺ …) is named by
    its tooltip ("Delete from the app"), a text box without a name by its grey placeholder ("Search the help…").
    A name given in the code stays. Also: Windows' contrast theme or accent colour changed while the app runs, and a
    pop-up (a menu, a drop-down's list, a tooltip) shown with Windows 11's rounded corners (winsys.round_corners, on
    Windows 11's own screen only)."""

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Show and _state.get("corners") and isinstance(obj, QWidget) and obj.isWindow() and \
                obj.windowType() in (Qt.Popup, Qt.ToolTip) and not obj.property("roundedByWindows"):
            from ui import winsys
            obj.setProperty("roundedByWindows", winsys.round_corners(int(obj.winId())))
        if e.type() == QEvent.ThemeChange and isinstance(obj, QWidget) and obj.isWindow() and \
                _state.get("following") and not _state.get("again") and \
                (bool(_state.get("contrast")) != high_contrast() or accent_palette() != _state.get("accent")):
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication
            _state["again"] = True  # (once for all the windows told)

            def again():
                _state["again"] = False
                apply(QApplication.instance())
            QTimer.singleShot(0, again)
        if e.type() == QEvent.Polish and isinstance(obj, QWidget) and not obj.accessibleName():
            from PySide6.QtWidgets import QAbstractButton, QLineEdit, QPlainTextEdit
            if isinstance(obj, QAbstractButton) and len(re.sub(r"[^\w]", "", obj.text())) < 2 and obj.toolTip():
                obj.setAccessibleName(obj.toolTip().split("\n")[0].rstrip("."))
            elif isinstance(obj, (QLineEdit, QPlainTextEdit)) and obj.placeholderText():
                obj.setAccessibleName(obj.placeholderText().split("\n")[0].rstrip("…. "))
        return False


def apply(app, dark=None, contrast=None):
    """Style the whole app (dark: True/False, or None to follow Windows; contrast: Windows' contrast theme's colours
    {token: colour}, False for none, or None to follow Windows), with Windows' accent colour, and keep following
    Windows."""
    from PySide6.QtGui import QFontDatabase
    following = dark is None
    _state["dark"] = _windows_dark() if following else dark
    if contrast is None:  # (a light or dark look asked for, as the checks do: that one, not the contrast theme)
        contrast = system_tokens() if following and high_contrast() else False
    _state["contrast"] = contrast or None
    _state["accent"] = accent_palette()
    _state["tokens"] = theme_tokens.build(_state["dark"], _state["accent"])
    app.setStyle("Fusion")  # (the same drawing everywhere: Windows' own style ignores parts of the stylesheet)
    font = app.font()
    font.setFamily(FONT if FONT in QFontDatabase.families() else "Segoe UI")
    app.setFont(font)
    t = tokens()
    app.setPalette(_palette(t))
    app.setStyleSheet(_stylesheet(t))
    if "names" not in _state:  # (once: names for a screen reader, pop-ups' corners: _Names)
        from ui import winsys
        _state["corners"] = winsys.materials(QGuiApplication.platformName())[1]
        _state["names"] = _Names(app)
        app.installEventFilter(_state["names"])
    for fn in list(_state["listeners"]):  # (what draws its own colours: the graph, Help's page, the icons)
        try:
            fn()
        except RuntimeError:  # (its window is gone)
            _state["listeners"].remove(fn)
    if following and not _state.get("following"):
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
