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
"""
import re

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QWidget

LIGHT = {"bg": "#f4f4f1", "card": "#ffffff", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#6b6a65",
         "line": "#e4e3de", "field": "#fbfbfa", "meas": "#eb6834", "tgt": "#52514e", "c1": "#1f68bf", "c2": "#1baf7a",
         "c3": "#4a3aa7", "c4": "#e34948", "c5": "#eda100", "sel": "#e3eefb", "shade": "#efeee9", "warn": "#b35a00",
         "err": "#c62828", "btn": "#226cc4", "good": "#107a55", "pill": "#eef5ea", "grid": "#e4e3de",
         "on_btn": "#ffffff", "on_sel": "#ffffff", "sel_ink": "#0b0b0b", "sel_accent": "#1f68bf"}
DARK = {"bg": "#111110", "card": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#9d9c94", "line": "#34332f",
        "field": "#141413", "meas": "#d95926", "tgt": "#c3c2b7", "c1": "#5a9cf0", "c2": "#199e70", "c3": "#9085e9",
        "c4": "#e66767", "c5": "#c98500", "sel": "#1c3350", "shade": "#1f1f1d", "warn": "#f0a050", "err": "#ef7b7b",
        "btn": "#2a70cc", "good": "#199e70", "pill": "#1f3325", "grid": "#2a2a27",
        "on_btn": "#ffffff", "on_sel": "#ffffff", "sel_ink": "#ffffff", "sel_accent": "#5a9cf0"}
# (sel_ink, sel_accent: text on sel, the selected or checked background; in a contrast theme Windows' HighlightText)

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
    return f"""
    QMainWindow, QDialog {{ background: {t['bg']}; }}
    QWidget {{ color: {t['ink']}; font-size: 10pt; }}
    QToolTip {{ background: {t['card']}; color: {t['ink']}; border: 1px solid {t['line']}; padding: 4px; }}
    QGroupBox, QFrame[card="true"] {{
        background: {t['card']}; border: 1px solid {t['line']}; border-radius: 10px; }}
    QGroupBox {{ margin-top: 0px; padding: 34px 12px 12px 12px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: padding; subcontrol-position: top left; left: 12px; top: 10px;
        color: {t['ink']}; font-size: 10.5pt; font-weight: 600; }}
    QFrame[card="true"] {{ padding: 10px; }}
    QFrame[card="warn"] {{ background: {t['card']}; border: 1px solid {t['warn']}; border-left: 4px solid {t['warn']};
        border-radius: 10px; padding: 8px; }}
    QGroupBox QLabel, QFrame[card] QLabel {{ background: transparent; font-weight: 400; }}
    QLabel[role="title"] {{ font-size: 15pt; font-weight: 700; }}
    QLabel[role="muted"] {{ color: {t['muted']}; }}
    QLabel[role="warn"] {{ color: {t['warn']}; }}
    QLabel[role="good"] {{ color: {t['good']}; }}
    QLabel[role="chip"] {{ background: {t['shade']}; border: 1px solid {t['line']}; border-radius: 9px;
        padding: 2px 8px; }}
    QLabel[role="brand"] {{ font-size: 12pt; font-weight: 700; }}
    QPushButton, QToolButton {{ background: {t['field']}; border: 1px solid {t['line']}; border-radius: 7px;
        padding: 5px 12px; }}
    QPushButton:hover, QToolButton:hover {{ border-color: {t['c1']}; }}
    QPushButton:disabled {{ color: {t['muted']}; }}
    QPushButton:checked {{ background: {t['sel']}; border-color: {t['c1']}; color: {t['sel_accent']}; font-weight: 600; }}
    QPushButton[primary="true"] {{ background: {t['btn']}; color: {t['on_btn']}; border: 1px solid {t['btn']}; font-weight: 600; }}
    QPushButton[primary="true"]:disabled {{ background: {t['line']}; border-color: {t['line']}; color: {t['muted']}; }}
    QPushButton[nav="true"] {{ background: transparent; border: none; border-radius: 7px; padding: 6px 12px;
        color: {t['ink2']}; font-weight: 600; }}
    QPushButton[nav="true"]:checked {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QPushButton[nav="true"]:hover {{ color: {t['ink']}; }}
    QPushButton[online="true"] {{ border-radius: 12px; padding: 4px 12px; font-weight: 600; }}
    QPushButton[online="true"]:checked {{ background: {t['pill']}; color: {t['good']}; border-color: {t['good']}; }}
    QFrame[topbar="true"] {{ background: {t['card']}; border-bottom: 1px solid {t['line']}; }}
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QKeySequenceEdit {{ background: {t['field']};
        border: 1px solid {t['line']}; border-radius: 7px; padding: 4px 8px; }}
    QComboBox:hover, QLineEdit:focus {{ border-color: {t['c1']}; }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ background: {t['shade']};
        color: {t['muted']}; border-color: {t['line']}; }}
    QComboBox QAbstractItemView {{ background: {t['card']}; border: 1px solid {t['line']};
        selection-background-color: {t['sel']}; selection-color: {t['sel_ink']}; }}
    QListWidget, QTableWidget {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px;
        alternate-background-color: {t['field']}; gridline-color: {t['line']}; }}
    QListWidget::item {{ padding: 6px 4px; border-radius: 6px; }}
    QListWidget::item:selected, QTableWidget::item:selected {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QHeaderView::section {{ background: {t['shade']}; color: {t['ink2']}; border: none;
        border-bottom: 1px solid {t['line']}; padding: 5px 8px; font-weight: 600; }}
    QProgressBar {{ background: {t['shade']}; border: none; border-radius: 4px; height: 8px; text-align: center; }}
    QProgressBar::chunk {{ background: {t['c1']}; border-radius: 4px; }}
    QSlider::groove:horizontal {{ height: 6px; background: {t['line']}; border-radius: 3px; }}
    QSlider::sub-page:horizontal {{ background: {t['c1']}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: {t['card']}; border: 2px solid {t['c1']}; width: 14px; height: 14px;
        margin: -6px 0; border-radius: 9px; }}
    QSlider::groove:vertical {{ width: 6px; background: {t['line']}; border-radius: 3px; }}
    QSlider::sub-page:vertical, QSlider::add-page:vertical {{ background: {t['line']}; border-radius: 3px; }}
    QSlider::handle:vertical {{ background: {t['card']}; border: 2px solid {t['c1']}; width: 14px; height: 14px;
        margin: 0 -6px; border-radius: 9px; }}
    QSlider::handle:vertical:disabled {{ border-color: {t['muted']}; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QSplitter::handle {{ background: transparent; }}
    QStatusBar {{ color: {t['ink2']}; }}
    QMenu {{ background: {t['card']}; border: 1px solid {t['line']}; padding: 4px; }}
    QMenu::item {{ padding: 5px 18px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QMenu::item:disabled {{ color: {t['muted']}; }}
    QLineEdit[bad="true"], QPlainTextEdit[bad="true"] {{ border: 1px solid {t['err']}; background: {t['field']}; }}
    QPlainTextEdit {{ background: {t['field']}; border: 1px solid {t['line']}; border-radius: 7px; padding: 4px; }}
    QToolButton[tag="true"] {{ background: {t['shade']}; color: {t['muted']}; border: 1px solid {t['line']};
        border-radius: 9px; padding: 1px 8px; font-size: 8.5pt; }}
    QToolButton[tag="true"]:enabled {{ background: {t['sel']}; color: {t['sel_accent']}; border-color: {t['c1']}; }}
    QLabel[role="section"] {{ color: {t['muted']}; font-size: 8.5pt; font-weight: 700; letter-spacing: 1px;
        text-transform: uppercase; padding-top: 4px; }}
    QToolButton[fold="true"] {{ background: transparent; border: none; font-size: 10.5pt; font-weight: 600;
        padding: 6px 4px; }}
    QCheckBox, QRadioButton {{ background: transparent; spacing: 8px; }}
    QRadioButton::indicator, QCheckBox::indicator {{ width: 14px; height: 14px; background: {t['field']};
        border: 2px solid {t['muted']}; }}
    QRadioButton::indicator {{ border-radius: 9px; }}
    QCheckBox::indicator {{ border-radius: 4px; }}
    QRadioButton::indicator:hover, QCheckBox::indicator:hover {{ border-color: {t['c1']}; }}
    QRadioButton::indicator:checked {{ border: 2px solid {t['c1']};
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {t['c1']}, stop:0.45 {t['c1']},
        stop:0.55 {t['field']}, stop:1 {t['field']}); }}
    QCheckBox::indicator:checked {{ background: {t['c1']}; border-color: {t['c1']}; image: url({_tick()}); }}
    QTreeView::indicator, QListView::indicator {{ width: 12px; height: 12px; background: {t['field']};
        border: 2px solid {t['muted']}; border-radius: 4px; }}
    QTreeView::indicator:checked, QListView::indicator:checked {{ background: {t['c1']}; border-color: {t['c1']};
        image: url({_tick()}); }}
    QTreeView::indicator:indeterminate {{ background: {t['sel']}; border-color: {t['c1']}; }}
    QRadioButton:disabled, QCheckBox:disabled {{ color: {t['muted']}; }}
    """


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
