"""Trace a graph image (AutoEQ Local's tracer window, natively; the workings are ui/trace_core.py): a picture of a
frequency-response graph (a maker's sheet, a review's screenshot) becomes a measurement or a target.

- the picture (open, drop or paste it): the four calibration lines (red: dB, blue: Hz) dragged onto gridlines, the
  traces drawn over it, zoom (wheel, + / -, Fit) and move (Move, Space or the right button); the Hz and dB under the
  pointer
- the side: Automatic settings (switch, Why these settings), 1 Axes (the four values, Snap to
  gridlines, Follow every gridline, Find axes again, Read labels), 2 Trace (Click curve, Draw, Erase, Move; the curves
  with their names; Add a curve; Auto trace; colour tolerance; dashed lines; Smooth, Undo, Redo, Clear), 3 Save
  (name, points per octave, what the graph shows, the range; Add as measurement, Add as target, Save .txt…)
- keys: T D E H tools, A Auto trace, S Smooth, F fit, + - zoom, Delete clears, Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y,
  arrows move a selected line (Shift: 10 px), Ctrl+V pastes a picture; a key of a tab's control shows that tab first
  (the tools, A, S, Delete, Undo and Redo: 2 Trace; the arrows: 1 Axes)
- the message line (what the tracer did, the tool's words) under the side, in sight on every tab
sample_image() draws AutoEQ Local's sample graph (an IEM's two channels and a dashed target) for checks and the tour.

The look is Windows 11's, as the rest of the app (2026-10-23): the picture on a card, the tools as one group, Windows
11's symbols beside the main actions' words; the window's own rules are theme_sheet.py's tracer part (by the
objectNames and the tr* properties set here). The tracer's marks on the picture keep their colours (the red and blue
lines, the green boxes: the Guide and Help name them): they're drawn on the graph's own picture, not on the app.
"""
import math
import os

import numpy as np
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSlider,
                               QStackedWidget, QToolButton, QVBoxLayout, QWidget)

import textfile
from ui import help_window, icons, tasks, theme
from ui.forms import Fold, Limits, help_of
from ui import trace_core as tc
from ui.search_combo import SearchCombo
from ui.theme_sheet import CARD
from ui.window_parts import fit_to_screen

RED, BLUE, GREEN = "#d93025", "#1a73e8", "#16a34a"
STROKES = ["#ff00d4", "#00a8e8", "#ff8a00", "#8e44ff", "#00b35f", "#e6b800"]
TOOLS = [("trace", "Click curve", "Click a curve to follow it (T)"),
         ("draw", "Make a line", "Drag along the curve to make a line (D)"),
         ("erase", "Erase", "Drag a box around the traced line to remove it (E)"),
         ("pan", "Move", "Drag to move the picture, or hold Space, or drag with the right mouse button (H)")]
TOOL_SYMBOLS = {"trace": "trace", "draw": "pen", "erase": "erase", "pan": "move"}  # (icons.GLYPHS' names)
SIDE = 500  # (the settings' width: room for 10.5 pt text, "the actual response (not compensated)" whole, symbols)
RADIUS = 8  # (the picture's card: a card's corners, as theme_sheet's)
HINTS = {"trace": "Click a curve to follow it.", "draw": "Drag along the curve to make a line manually.",
         "erase": "Drag a box around a part of the traced line to remove it.", "pan": "Drag to move the picture."}
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".gif", ".tif", ".tiff")
IMAGES = "Images (*.png *.jpg *.jpeg *.jfif *.webp *.bmp *.gif *.tif *.tiff)"


def _no_focus(root):
    """Buttons and tick boxes that don't take the keyboard when clicked: Space stays the picture's (hold it to move
    the picture), as do the tracer's other keys. Text boxes, lists and sliders keep it."""
    for kind in (QPushButton, QCheckBox, QToolButton):
        for w in root.findChildren(kind):
            w.setFocusPolicy(Qt.NoFocus)


def _label(text="", role=None, wrap=True):
    lab = QLabel(text)
    lab.setWordWrap(wrap)
    if role:
        theme.mark(lab, role=role)
    return lab


class _Note(QLabel):
    """A muted note under a card's controls that takes no room while it says nothing (no empty row at the card's
    foot)."""

    def __init__(self):
        super().__init__("")
        self.setWordWrap(True)
        theme.mark(self, role="muted")
        self.hide()

    def setText(self, text):
        super().setText(text)
        self.setVisible(bool(text))


class _Elided(QLabel):
    """A one-line label that never widens its window: a text longer than its room ends in "…", the whole text in its
    tooltip and its name for a screen reader (the picture's name: a long file name made the tracer wider than the
    screen, 2026-11-10)."""

    def __init__(self):
        super().__init__("")
        self.whole = ""

    def setText(self, text):
        self.whole = text or ""
        self.setToolTip(self.whole)
        self.setAccessibleName(self.whole)
        self.updateGeometry()
        self._fit()

    def sizeHint(self):
        self.ensurePolished()
        return QSize(self.fontMetrics().horizontalAdvance(self.whole) + 4, super().sizeHint().height())

    def minimumSizeHint(self):
        self.ensurePolished()
        return QSize(min(self.sizeHint().width(), self.fontMetrics().horizontalAdvance("M…") * 4),
                     super().minimumSizeHint().height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        QLabel.setText(self, self.fontMetrics().elidedText(self.whole, Qt.ElideMiddle, max(0, self.width() - 2)))


def _dot(colour, size=16):
    """A curve's coloured dot (its trace's colour on the picture), for the button that selects it."""
    pm = QPixmap(size * 2, size * 2)  # (drawn at twice the size: sharp at 125 % and 150 %)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(colour))
    p.drawEllipse(QRectF(size * 0.2, size * 0.2, size * 0.6, size * 0.6))
    p.end()
    return QIcon(pm)


def _name_curve_buttons(pick, delete, label, i):
    """A curve's dot and ✕ named with the curve's name for a screen reader ("Select curve L", "Remove curve L"), again
    when it's renamed: every row's were read alike ("Trace into this curve", "Delete this curve"), 2026-10-23. (✕ is
    Remove: Undo brings the curve back, .claude/notes/UI-RULES.md 10.)"""
    name = label or str(i + 1)
    pick.setAccessibleName(f"Select curve {name}")
    delete.setAccessibleName(f"Remove curve {name}")


def _symbol_only(button, name):
    """Windows 11's symbol `name` alone on a button (no words: its tooltip names it for a screen reader)."""
    button.setText("")
    theme.mark(button, trIcon=True)  # (theme_sheet's tracer part centres the symbol)
    icons.put(button, name)


def rgb_of(img):
    """A QImage as an RGB NumPy array (transparent parts on white), scaled down to MAX_PIXELS at most."""
    w, h = img.width(), img.height()
    k = min(1.0, math.sqrt(tc.MAX_PIXELS / max(1, w * h)))
    W, H = max(1, round(w * k)), max(1, round(h * k))
    out = QImage(W, H, QImage.Format_RGB888)
    out.fill(QColor("white"))
    p = QPainter(out)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawImage(QRectF(0, 0, W, H), img)
    p.end()
    a = np.frombuffer(out.constBits(), np.uint8, count=out.bytesPerLine() * H).reshape(H, out.bytesPerLine())
    return a[:, :W * 3].reshape(H, W, 3).copy()


def sample_image():
    """AutoEQ Local's sample graph (squiglink's style): an IEM's left and right channel and a dashed target. Returns
    (QImage, {"curves": [[(x, y)…] per channel], "target": [(x, y)…], "db": dB at a height, "hz": Hz at a column})."""
    inks = ["#e8743b", "#2f9e5b"]  # (not the traces' own colours, so a trace shows on top of its curve)
    Wd, Hd, L, R, T, B, lo, hi = 1200, 720, 96, 40, 76, 84, 40, 90
    img = QImage(Wd, Hd, QImage.Format_RGB888)
    img.fill(QColor("white"))
    g = QPainter(img)
    X = lambda f: L + (math.log10(f) - math.log10(20)) / 3 * (Wd - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (Hd - T - B)

    def line(x0, y0, x1, y1, col, w=1.0, dash=None):
        pen = QPen(QColor(col), w)
        if dash:
            pen.setDashPattern([d / w for d in dash])
        pen.setCapStyle(Qt.FlatCap)
        g.setPen(pen)
        g.drawLine(QPointF(x0, y0), QPointF(x1, y1))
    for d in (10, 100, 1000, 10000):  # minor frequency lines (20, 30 … 90, 200 …)
        for k in range(2, 10):
            if d * k <= 20000:
                x = round(X(d * k)) + 0.5
                line(x, T, x, Hd - B, "#eeeeee")
    for v in range(lo, hi + 1, 5):
        y = round(Y(v)) + 0.5
        line(L, y, Wd - R, y, "#d0d0d0")
    major = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    for f in major:
        x = round(X(f)) + 0.5
        line(x, T, x, Hd - B, "#d0d0d0")
    font = QFont("Arial")
    font.setPixelSize(22)
    g.setFont(font)
    g.setPen(QColor("#333333"))
    for f in major:
        t = f"{f // 1000}k" if f >= 1000 else str(f)
        g.drawText(QRectF(X(f) - 60, Hd - B + 12, 120, 30), Qt.AlignHCenter | Qt.AlignTop, t)
    for v in range(lo, hi + 1, 10):
        g.drawText(QRectF(0, Y(v) - 15, L - 12, 30), Qt.AlignRight | Qt.AlignVCenter, str(v))
    font.setBold(True)
    font.setPixelSize(24)
    g.setFont(font)
    g.drawText(QPointF(L, 44), "Sample IEM")
    font.setBold(False)
    font.setPixelSize(18)
    g.setFont(font)
    g.setPen(QColor("#666666"))
    g.drawText(QPointF(Wd / 2 - 60, Hd - 18), "Frequency (Hz)")
    g.setRenderHint(QPainter.Antialiasing)
    fq = [20 * 1000 ** (i / 479) for i in range(480)]
    l2 = math.log2
    iem = lambda f: (62 + 6 / (1 + (f / 140) ** 2) + 9 * math.exp(-(l2(f / 2700) ** 2) / 0.7)
                     - 7 * math.exp(-(l2(f / 7800) ** 2) / 0.06) + 4 * math.exp(-(l2(f / 12500) ** 2) / 0.12)
                     - 7 * max(0, l2(f / 15000)))
    chans = [lambda f: iem(f) + 0.6 * math.sin(l2(f) * 2.3), lambda f: iem(f) - 0.8 + 0.9 * math.sin(l2(f) * 3.1 + 1)]
    tgt = lambda f: 60 + 4 / (1 + (f / 100) ** 2) + 8 * math.exp(-(l2(f / 3000) ** 2) / 1.3) - 3 * max(0, l2(f / 10000))

    def path(pts, col, w, dash=None):
        pen = QPen(QColor(col), w)
        pen.setJoinStyle(Qt.RoundJoin)
        if dash:
            pen.setDashPattern([d / w for d in dash])
            pen.setCapStyle(Qt.FlatCap)
        g.setPen(pen)
        pp = QPainterPath(QPointF(*pts[0]))
        for p in pts[1:]:
            pp.lineTo(QPointF(*p))
        g.drawPath(pp)
    # (dashes with wide gaps: a plain trace stops at the first one, “Dashed or dotted line” bridges them)
    tp = [(X(f), Y(tgt(f))) for f in fq]
    path(tp, "#888888", 2.5, [12, 34])
    pts = []
    for k, fn in enumerate(chans):
        p = [(X(f), Y(fn(f))) for f in fq]
        pts.append(p)
        path(p, inks[k], 3)
    g.setPen(QColor("#333333"))
    for i, (t, col, dash) in enumerate((("Left", inks[0], None), ("Right", inks[1], None), ("Target", "#888888", [10, 8]))):
        x, y = Wd - R - 330 + i * 110, 40
        line(x, y - 6, x + 30, y - 6, col, 3, dash)
        g.setPen(QColor("#333333"))
        g.drawText(QPointF(x + 38, y), t)
    g.end()
    return img, {"curves": pts, "target": tp, "db": lambda y: hi - (y - T) / (Hd - T - B) * (hi - lo),
                 "hz": lambda x: 20 * 10 ** ((x - L) / (Wd - L - R) * 3), "chans": chans, "tgt": tgt}


# ---------------------------------------------------------------- the picture
class Stage(QWidget):
    """The picture, the calibration lines and the traces; zoom, move and the tools."""

    def __init__(self, win):
        super().__init__()
        self.win, self.t = win, win.t
        self.view = {"s": 1.0, "ox": 0.0, "oy": 0.0, "auto": True}  # auto: keep fitting until zoomed or moved
        self.qimg = None
        self.drag = self.hover = self.mouse = self.sel_line = None
        self.space = False
        self.setMouseTracking(True)
        self.grabGesture(Qt.PinchGesture)  # (a touch screen: two fingers pinch to zoom and drag the picture)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setMinimumSize(420, 320)
        # the empty stage: what to do (inside the dashed drop zone paintEvent draws)
        self.empty = QWidget(self)
        ev = QVBoxLayout(self.empty)
        ev.setAlignment(Qt.AlignCenter)
        ev.setSpacing(10)
        head = QLabel("Drag a frequency response graph here")
        head.setObjectName("trDropHead")
        head.setAlignment(Qt.AlignCenter)
        ev.addWidget(head)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(QLabel("or paste it with Ctrl+V, or"))
        self.choose_btn = choose = QPushButton("Open image…")  # (the header's words for it: one act, one name)
        theme.mark(choose, primary=True)  # (the one thing to do here)
        icons.put(choose, "open")
        choose.clicked.connect(win.choose_image)
        row.addWidget(choose)
        row.addStretch(1)
        ev.addLayout(row)
        sub = _label("You can use screenshots of graphs from data sheets or websites (PNG, JPG, WebP).", "muted")
        sub.setAlignment(Qt.AlignCenter)
        ev.addWidget(sub)
        self._zoom_bar()
        self.update_empty()  # (no picture yet: the drop zone, without the zoom bar)

    def _zoom_bar(self):
        """Zoom out, Fit, zoom in: a small bar floating at the picture's corner (as Windows 11's flyouts)."""
        self.zoom_box = QFrame(self)
        self.zoom_box.setObjectName("trZoom")
        zl = QHBoxLayout(self.zoom_box)
        zl.setContentsMargins(3, 3, 3, 3)
        zl.setSpacing(2)
        self.zoom_btns = {}
        for key, text, tip, fn in (("out", "", "Zoom out (-)", lambda: self.zoom(0.8)),
                                   ("fit", "Show all", "Show all the picture (F)", self.fit_now),
                                   ("in", "", "Zoom in (+)", lambda: self.zoom(1.25))):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(fn)
            theme.mark(b, quiet=True, trCompact=True)
            if text:
                icons.put(b, "fit")
            else:
                _symbol_only(b, "zoom_" + key)
            zl.addWidget(b)
            self.zoom_btns[key] = b

    def set_image(self, rgb):
        h, w = rgb.shape[:2]
        self._buf = np.ascontiguousarray(rgb)
        self.qimg = QImage(self._buf.data, w, h, w * 3, QImage.Format_RGB888).copy()
        self.drag = self.hover = self.sel_line = None
        self.fit()
        self.update_empty()

    def clear_image(self):
        self.qimg = None
        self.drag = self.hover = self.sel_line = self.mouse = None
        self.view["auto"] = True
        self.update_empty()

    def update_empty(self):
        self.empty.setVisible(self.qimg is None)
        self.zoom_box.setVisible(self.qimg is not None)
        self.update()

    def resizeEvent(self, e):
        self.empty.setGeometry(self.rect())
        self.zoom_box.adjustSize()
        self.zoom_box.move(self.width() - self.zoom_box.width() - 12, self.height() - self.zoom_box.height() - 12)
        if self.view["auto"]:
            self.fit()
        super().resizeEvent(e)

    # view
    def fit(self):
        v, t = self.view, self.t
        v["auto"] = True
        if not t.W or self.width() < 30:
            return
        v["s"] = min((self.width() - 20) / t.W, (self.height() - 20) / t.H)
        v["ox"], v["oy"] = (self.width() - t.W * v["s"]) / 2, (self.height() - t.H * v["s"]) / 2
        self.update()

    def fit_now(self):
        self.fit()

    def zoom(self, f, at=None):
        v = self.view
        sx, sy = at or (self.width() / 2, self.height() / 2)
        x, y = self.to_img(sx, sy)
        v["auto"] = False
        v["s"] = min(max(v["s"] * f, 0.05), 40)
        v["ox"], v["oy"] = sx - x * v["s"], sy - y * v["s"]
        self.update()

    def to_img(self, sx, sy):
        v = self.view
        return (sx - v["ox"]) / v["s"], (sy - v["oy"]) / v["s"]

    def to_scr(self, x, y):
        v = self.view
        return x * v["s"] + v["ox"], y * v["s"] + v["oy"]

    def line_at(self, sx, sy):
        best, bd = None, 6
        for key in ("y1", "y2"):
            d = abs(self.to_scr(0, self.t.cal[key])[1] - sy)
            if d < bd:
                bd, best = d, key
        for key in ("x1", "x2"):
            d = abs(self.to_scr(self.t.cal[key], 0)[0] - sx)
            if d < bd:
                bd, best = d, key
        return best

    # drawing
    def paintEvent(self, _e):
        """A card (as the app's: its colours, border and corners, in the theme in use), the picture on it (outlined,
        so a white picture's edge shows), the lines, labels and traces; without a picture, a dashed drop zone."""
        p = QPainter(self)
        tk = theme.tokens()
        p.setRenderHint(QPainter.Antialiasing)
        card = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(tk["line"]), 1))
        p.setBrush(QColor(tk["card"]))
        p.drawRoundedRect(card, RADIUS, RADIUS)
        t = self.t
        if self.qimg is None or not t.has_image:
            zone = QColor(tk["strong"])
            zone.setAlphaF(0.6)
            pen = QPen(zone, 1.5)
            pen.setDashPattern([4, 3])
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(card.adjusted(12, 12, -12, -12), 4, 4)
            return
        inside = QPainterPath()
        inside.addRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS - 0.5, RADIUS - 0.5)
        p.setClipPath(inside)  # (a zoomed picture stays inside the card's corners)
        s = self.view["s"]
        p.setRenderHint(QPainter.SmoothPixmapTransform, s < 2)
        ix0, iy0 = self.to_scr(0, 0)
        ix1, iy1 = self.to_scr(t.W, t.H)
        p.drawImage(QRectF(ix0, iy0, ix1 - ix0, iy1 - iy0), self.qimg)
        p.setPen(QPen(QColor(tk["stroke_bottom"]), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(ix0 - 0.5, iy0 - 0.5, ix1 - ix0 + 1, iy1 - iy0 + 1))
        k = t.calib()
        font = QFont(self.font())
        font.setPixelSize(12)
        font.setWeight(QFont.DemiBold)

        def label(text, x, y, col):
            p.setFont(font)
            w = p.fontMetrics().horizontalAdvance(text) + 8
            if x + w > min(ix1, self.width()) - 2:  # (at the right edge: on the line's left)
                x -= w + 6
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(col))
            p.drawRoundedRect(QRectF(x, y - 9, w, 18), 3, 3)
            p.setPen(QColor("white"))
            p.drawText(QRectF(x, y - 9, w, 18), Qt.AlignCenter, text)
        # the calibration lines
        for key, horiz, val, unit in (("y1", True, "d1", "dB"), ("y2", True, "d2", "dB"), ("x1", False, "f1", "Hz"),
                                      ("x2", False, "f2", "Hz")):
            col = RED if horiz else BLUE
            on = self.hover == key or (self.drag and self.drag.get("line") == key) or self.sel_line == key
            pen = QPen(QColor(col), 2.5 if on else 1.5)
            if not on:
                pen.setDashPattern([6 / 1.5, 4 / 1.5])
            p.setPen(pen)
            v = str(t.v[val]).strip()
            text = f"type {unit}" if v == "" else f"{v} {unit}"
            if horiz:
                y = self.to_scr(0, t.cal[key])[1]
                p.drawLine(QPointF(ix0, y), QPointF(ix1, y))
                label(text, max(4, ix0 + 4), y, col)
            else:
                x = self.to_scr(t.cal[key], 0)[0]
                p.drawLine(QPointF(x, iy0), QPointF(x, iy1))
                label(text, x + 3, min(iy1, self.height()) - 14, col)
        # gridlines used between the main lines (uneven axes): small ticks with their values
        if k:
            small = QFont(self.font())
            small.setPixelSize(11)
            p.setFont(small)
            fm = p.fontMetrics()
            top, left = self.to_scr(0, t.box["y0"])[1], self.to_scr(t.box["x0"], 0)[0]
            edge = -math.inf
            p.setPen(QPen(QColor(BLUE), 1.5))
            for a in k.ax[1:-1]:
                x = self.to_scr(a["p"], 0)[0]
                txt = tc.fmt_hz(a["v"]).replace(" Hz", "").replace(" kHz", "k")
                p.drawLine(QPointF(x, top), QPointF(x, top + 10))
                if x + 2 > edge:
                    p.drawText(QPointF(x + 2, top + 20), txt)
                    edge = x + 2 + fm.horizontalAdvance(txt) + 4
            edge = -math.inf
            p.setPen(QPen(QColor(RED), 1.5))
            for a in k.ay[1:-1]:
                y = self.to_scr(0, a["p"])[1]
                p.drawLine(QPointF(left, y), QPointF(left + 10, y))
                if y - 12 > edge:
                    p.drawText(QPointF(left + 13, y + 4), f"{round(a['v'], 2):g}")
                    edge = y
        # labels the reader used
        p.setPen(QPen(QColor(GREEN), 1.5))
        p.setBrush(Qt.NoBrush)
        for w in t.label_words:
            a, b = self.to_scr(w["x0"] - 2, w["y0"] - 2)
            c, d = self.to_scr(w["x1"] + 2, w["y1"] + 2)
            p.drawRect(QRectF(a, b, c - a, d - b))
        # the traces (gaps of up to 40 px, e.g. over gridlines or between dashes, joined as they will be when saved)
        order = [i for i in range(len(t.curves)) if i != t.cur] + ([t.cur] if t.curves else [])
        for i in order:
            ys = t.curves[i]["ys"]
            xs = np.flatnonzero(np.isfinite(ys))
            if not len(xs):
                continue
            pen = QPen(QColor(STROKES[i % len(STROKES)]), 2.5 if i == t.cur else 1.5)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setOpacity(1 if i == t.cur else 0.75)
            p.setPen(pen)
            path, last = QPainterPath(), -99
            for x in xs:
                sx, sy = self.to_scr(x + 0.5, ys[x] + 0.5)
                if x - last > 40:
                    path.moveTo(sx, sy)
                else:
                    path.lineTo(sx, sy)
                last = x
            p.drawPath(path)
        p.setOpacity(1)
        if self.drag and self.drag["kind"] == "erase":
            d = self.drag
            a, b = self.to_scr(d["x0"], d["y0"])
            c, e = self.to_scr(d["x1"], d["y1"])
            p.setPen(QPen(QColor(RED), 1))
            p.setBrush(QColor(217, 48, 37, 38))
            p.drawRect(QRectF(a, b, c - a, e - b))
        # the Hz and dB under the pointer
        if self.mouse and k:
            mx, my = self.to_img(*self.mouse)
            f, v = k.hz_at(mx), k.db_at(my)
            hz = f"{f / 1000:.{1 if f >= 10000 else 2}f} kHz" if f >= 1000 else f"{f:.{1 if f < 100 else 0}f} Hz"
            text = f"{hz} · {'+' if v >= 0 else ''}{v:.1f} dB"
            p.setFont(font)
            w = p.fontMetrics().horizontalAdvance(text) + 16
            box = QRectF(12.5, 12.5, w, 26)  # (as Windows 11's tooltips: the menu's colour, a thin border, 4 px corners)
            p.setPen(QPen(QColor(tk["stroke"]), 1))
            p.setBrush(QColor(tk["menu"]))
            p.drawRoundedRect(box, 4, 4)
            p.setPen(QColor(tk["ink"]))
            p.drawText(box, Qt.AlignCenter, text)

    # the mouse
    def mousePressEvent(self, e):
        t, win = self.t, self.win
        if not t.has_image:
            return
        sx, sy = e.position().x(), e.position().y()
        if e.button() in (Qt.MiddleButton, Qt.RightButton) or self.space or win.tool == "pan":
            self.drag = {"kind": "pan", "sx": sx, "sy": sy, "ox": self.view["ox"], "oy": self.view["oy"]}
            self.setCursor(Qt.ClosedHandCursor)
            return
        line = self.line_at(sx, sy)
        if line and win.tool != "draw":
            self.drag = {"kind": "line", "line": line, "from": t.cal[line]}
            self.sel_line = line
            self.update()
            return
        self.sel_line = None
        x, y = self.to_img(sx, sy)
        if win.tool == "trace" and e.source() == Qt.MouseEventSynthesizedBySystem:
            # (a finger: a tap traces, a finger that moves drags the picture, as AutoEQ Local's)
            self.drag = {"kind": "tap", "x": x, "y": y, "sx": sx, "sy": sy, "ox": self.view["ox"], "oy": self.view["oy"]}
        elif win.tool == "trace":
            win.say(t.trace_at(x, y))
            win.changed()
        elif win.tool == "draw":
            t.push_undo()
            t.draw_segment(x, y, x, y)
            self.drag = {"kind": "draw", "x": x, "y": y}
            win.changed()
        elif win.tool == "erase":
            self.drag = {"kind": "erase", "x0": x, "y0": y, "x1": x, "y1": y}

    def mouseMoveEvent(self, e):
        sx, sy = e.position().x(), e.position().y()
        self.mouse = (sx, sy)
        t, win, d = self.t, self.win, self.drag
        if not d:
            h = self.line_at(sx, sy) if t.has_image else None
            self.hover = h
            self.setCursor(Qt.OpenHandCursor if self.space or win.tool == "pan" else
                           (Qt.SizeVerCursor if h[0] == "y" else Qt.SizeHorCursor) if h and win.tool != "draw" else
                           Qt.CrossCursor)
            self.update()
            return
        x, y = self.to_img(sx, sy)
        if d["kind"] == "tap" and (sx - d["sx"]) ** 2 + (sy - d["sy"]) ** 2 > 64:
            d["kind"] = "pan"  # (the finger moved: it drags)
        if d["kind"] == "pan":
            self.view.update(auto=False, ox=d["ox"] + sx - d["sx"], oy=d["oy"] + sy - d["sy"])
        elif d["kind"] == "line":
            t.move_line(d["line"], y if d["line"][0] == "y" else x, self.view["s"])
            win.lines_moved()
        elif d["kind"] == "draw":
            t.draw_segment(d["x"], d["y"], x, y)
            d["x"], d["y"] = x, y
            win.update_ui()
        elif d["kind"] == "erase":
            d["x1"], d["y1"] = x, y
        self.update()

    def mouseReleaseEvent(self, _e):
        d = self.drag
        self.drag = None
        if d and d["kind"] == "tap":
            self.win.say(self.t.trace_at(d["x"], d["y"]))
            self.win.changed()
        elif d and d["kind"] == "erase":
            self.t.erase(d["x0"], d["y0"], d["x1"], d["y1"])
            self.win.changed()
        elif d and d["kind"] == "draw":
            self.win.changed()
        elif d and d["kind"] == "line":
            self.win.fit_and_show()
        self.setCursor(Qt.CrossCursor)
        self.update()

    def leaveEvent(self, _e):
        self.mouse = None
        if not self.drag:
            self.hover = None
        self.update()

    def event(self, e):
        from PySide6.QtCore import QEvent
        if e.type() == QEvent.Gesture:
            g = e.gesture(Qt.PinchGesture)
            if g is not None and self.t.has_image:
                self.drag = None  # (a second finger: what the first one began doesn't happen)
                c = self.mapFromGlobal(g.centerPoint().toPoint())
                f = g.scaleFactor()
                if f and f > 0:
                    self.zoom(f, (c.x(), c.y()))
                dp = g.centerPoint() - g.lastCenterPoint()  # (two fingers that move drag the picture)
                self.view.update(auto=False, ox=self.view["ox"] + dp.x(), oy=self.view["oy"] + dp.y())
                self.update()
                e.accept()
                return True
        return super().event(e)

    def wheelEvent(self, e):
        if not self.t.has_image:
            return
        self.zoom(1.0015 ** e.angleDelta().y(), (e.position().x(), e.position().y()))


# ---------------------------------------------------------------- the window
class TraceWindow(QWidget):
    def __init__(self, page):
        super().__init__(None, Qt.Window)
        self.page = page
        self.setWindowTitle("Trace a graph image - AutoEQ Studio")  # (a window of its own: the app's name, UI-RULES 3)
        fit_to_screen(self, (1320, 860))  # (within the screen's room: a laptop's at 150 % is 1280 x 672)
        self.setAcceptDrops(True)
        self.t = tc.Tracer()
        # (a picture from a website, eq_page_files.trace_from_website: its database entry, for the name, the file's
        # first line and the source record; whether the picture's curves went into the app; the last automatic read's
        # result: None with no read)
        self.entry = None
        self.added = False
        self.read_ok = None
        self.reading_graph = False
        self.graph_token = 0
        self.auto_note = ""  # (3 Save's note after an automatic read that passed)
        st = page.sw.s.get("trace") or {}
        if isinstance(st.get("enabled"), bool):
            self.t.ta["enabled"] = st["enabled"]
        self.tool = "trace"
        self.limits = Limits((page.meta or {}).get("limits", {}), [])
        v = QVBoxLayout(self)
        v.setContentsMargins(CARD, CARD, CARD, CARD)  # (Windows 11's roomier edges, as every window's)
        v.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(8)
        # (no large title: the title bar says "Trace a graph image", as Help's says its name. The picture's name in bold
        # where the title was, its size in gray beside it, or "No picture". The UI audit, 2026-11-08)
        self.file_lab = _Elided()  # (a long name cut in its middle, the whole name in its tooltip)
        theme.mark(self.file_lab, role="heading")  # (bold, a card title's size)
        head.addWidget(self.file_lab)
        self.size_lab = _label("", "muted", wrap=False)
        head.addWidget(self.size_lab, 1)
        self.show_name()
        # (the picture's own actions together, Remove last; then Guide apart at the right end, as the top bar's: it sat
        # between them, UI-RULES 14 and 28)
        self.open_btn = opn = QPushButton("Open image…")
        opn.setToolTip("Open a different picture (or drag or paste it here)")
        opn.clicked.connect(self.choose_image)
        icons.put(opn, "open")
        head.addWidget(opn)
        head.addSpacing(12)  # (Remove set apart, as every row's: UI-RULES 14)
        self.remove_btn = QPushButton("Remove image")
        self.remove_btn.setToolTip("Remove this picture (for example, an incorrect picture) and the curves that you traced on it")
        self.remove_btn.clicked.connect(self.remove_image)
        icons.put(self.remove_btn, "remove")
        head.addWidget(self.remove_btn)
        head.addSpacing(16)
        self.guide_btn = QPushButton("Guide")  # (Windows 11's symbol where "? " was, as the top bar's Guide)
        self.guide_btn.setToolTip("The Guide of the tracer (on a sample graph if no picture is open)")
        self.guide_btn.clicked.connect(self.start_guide)
        icons.put(self.guide_btn, "guide")
        head.addWidget(self.guide_btn)
        v.addLayout(head)
        body = QHBoxLayout()
        body.setSpacing(12)
        self.stage = Stage(self)
        body.addWidget(self.stage, 1)
        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QFrame.NoFrame)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        side_scroll.setFixedWidth(SIDE)
        self.side_scroll = side_scroll
        side = QWidget()
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 6, 0)
        sv.setSpacing(8)
        sv.addWidget(self._auto_box())
        # (one step at a time: the tabs 1 Axes, 2 Trace and 3 Save, and the step's card under them, so the side does not
        # scroll. The Automatic settings card stays above them, as it is for all the steps. The UI audit, 2026-11-08)
        tabs = QHBoxLayout()
        tabs.setSpacing(20)
        self.tab_btns = []
        for i, name in enumerate(("1  Axes", "2  Trace", "3  Save")):
            b = QPushButton(name)
            b.setCheckable(True)
            theme.mark(b, nav=True, flush=True)
            b.clicked.connect(lambda _=False, i=i: self.show_tab(i))
            tabs.addWidget(b)
            self.tab_btns.append(b)
        tabs.addStretch(1)
        sv.addLayout(tabs)
        self.pages = QStackedWidget()
        for box in (self._axes_box(), self._trace_box(), self._save_box()):
            page = QWidget()  # (the card at its own height, not the tallest card's)
            pv = QVBoxLayout(page)
            pv.setContentsMargins(0, 0, 0, 0)
            pv.addWidget(box)
            pv.addStretch(1)
            self.pages.addWidget(page)
        sv.addWidget(self.pages)
        sv.addStretch(1)
        side_scroll.setWidget(side)
        _no_focus(side)
        # (the tracer's message line under the side, outside its scrolling part: in sight on every tab. It was in 2
        # Trace's card, so a value moved to its limit, an empty clipboard or Remove image said nothing on 1 Axes and
        # 3 Save, 2026-11-10. As wide as the side: a long message wraps, the window never grows)
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(side_scroll, 1)
        self.status = _label("", "muted")  # (the tool's words, and what the tracer did)
        self.status.setFixedWidth(SIDE)
        col.addWidget(self.status)
        body.addLayout(col)
        v.addLayout(body, 1)
        for w, key in ((self.auto_on, "#tr-auto-on"), (self.snap, "#tr-snap"), (self.every, "#tr-every"),
                       (self.tol, "#tr-tol"), (self.ppo, "#tr-ppo"), (self.fmin, "#tr-fmin"), (self.fmax, "#tr-fmin"),
                       (self.name, "#tr-name"), (self.dashed, "#tr-dashed"), (self.comp, "#tr-comp"),
                       *((self.boxes[k], "#tr-" + k) for k in ("d1", "d2", "f1", "f2"))):
            help_window.tag(w, key)
        self.set_tool("trace")
        self.show_tab(0)
        self.show_values()
        self.render_auto_settings()
        self.update_ui()

    def show_tab(self, i):
        """The side's step i (0: Axes, 1: Trace, 2: Save): its tab lit and its card shown."""
        self.pages.setCurrentIndex(i)
        for k, b in enumerate(self.tab_btns):
            b.setChecked(k == i)

    def show_name(self, name="", size=None):
        """The picture's name in bold at the top and its size (w, h) in gray beside it; "No picture" without one."""
        self.file_lab.setText(name or ("Picture" if size else "No picture"))
        self.size_lab.setText(f"{size[0]}×{size[1]}" if size else "")

    # ---------------------------------------------------------------- the side
    def _tag(self, key):
        b = QToolButton()
        theme.mark(b, tag=True)
        b.clicked.connect(lambda: self.make_auto(key))
        self.tags[key] = b
        return b

    def _auto_box(self):
        self.tags = {}
        box = QFrame()
        theme.mark(box, card=True)
        v = QVBoxLayout(box)
        # (a card frame's padding leaves 4 px for its layout's margin, theme_sheet's cards part, as a fold card's: with
        # Qt's own 9 px its content started 5 px further in than the cards under it, 2026-10-23)
        v.setContentsMargins(4, 2, 4, 4)
        top = QHBoxLayout()
        self.auto_on = QCheckBox("Automatic settings")
        self.auto_on.setObjectName("trAutoOn")  # (the card's heading: semibold, theme_sheet's tracer part)
        self.auto_on.setToolTip(help_of("#tr-auto-on"))
        self.auto_on.toggled.connect(self.auto_switched)
        top.addWidget(self.auto_on)
        self.auto_state = _label("", "muted", wrap=False)
        top.addWidget(self.auto_state, 1)
        v.addLayout(top)
        why = Fold("About these settings")
        why.setObjectName("trWhy")  # (flat inside this card: no card in a card)
        why.layout().setContentsMargins(0, 0, 0, 0)
        self.why = why
        self.auto_notes = _label("")
        self.auto_notes.setTextFormat(Qt.RichText)
        why.body_lay.addWidget(self.auto_notes)
        why.body_lay.addWidget(_label("Active settings", "muted"))  # (no label's colon: UI-RULES 15)
        self.auto_eff = _label("")
        self.auto_eff.setTextFormat(Qt.RichText)
        why.body_lay.addWidget(self.auto_eff)
        self.auto_manual = _label("")
        self.auto_manual.setTextFormat(Qt.RichText)
        self.auto_manual.linkActivated.connect(lambda k: self.make_auto(None if k == "*" else k))
        why.body_lay.addWidget(self.auto_manual)
        why.body_lay.addWidget(_label("The settings follow the picture. If you change a setting, it shows “your value” and the "
                                       "app keeps it.", "muted"))
        v.addWidget(why)
        return box

    def _card(self):
        """A step's card (its tab is its title): a card frame, its content at a card's inset, as the Automatic settings
        card's."""
        box = QFrame()
        theme.mark(box, card=True)
        v = QVBoxLayout(box)
        v.setContentsMargins(4, 4, 4, 4)  # (the card's padding and these 4 px: the same inset as the card above)
        return box, v

    def _axes_box(self):
        box, v = self._card()
        v.addWidget(_label("Drag the red lines to two dB grid lines. Drag the blue lines to two frequency grid lines. "
                           "Type their values.", "muted"))
        # (two rows with their labels in a column at the left, as 3 Save's form; Top, Bottom, Left and Right small and
        # gray in the row, the boxes' full names for a screen reader. The UI audit, 2026-11-08)
        g = QGridLayout()
        g.setColumnStretch(2, 1)
        g.setColumnStretch(4, 1)
        self.boxes = {}
        rows = (("Red lines (dB)", (("d1", "Top", "Top red line (dB)", "trace.db"),
                                    ("d2", "Bottom", "Bottom red line (dB)", "trace.db"))),
                ("Blue lines (Hz)", (("f1", "Left", "Left blue line (Hz)", "trace.hz"),
                                     ("f2", "Right", "Right blue line (Hz)", "trace.hz"))))
        for r, (label, pair) in enumerate(rows):
            g.addWidget(_label(label, wrap=False), r, 0)
            for c, (key, short, text, lim) in enumerate(pair):
                g.addWidget(_label(short, "muted", wrap=False), r, 1 + 2 * c)
                b = QLineEdit()
                b.setAccessibleName(text)
                b.setToolTip(help_of(f"#tr-{key}") + f"\nPermitted: {self.limits.text(lim)}.")
                b.textEdited.connect(lambda _t, k=key, lim=lim: self.value_typed(k, lim))
                b.editingFinished.connect(lambda k=key, lim=lim: self.value_left(k, lim))
                g.addWidget(b, r, 2 + 2 * c)
                self.boxes[key] = b
        v.addLayout(g)
        checks = QHBoxLayout()
        self.snap = QCheckBox("Align with grid lines")
        self.snap.setToolTip(help_of("#tr-snap"))
        self.snap.setChecked(True)
        self.snap.toggled.connect(lambda on: self.t.v.__setitem__("snap", on))
        self.every = QCheckBox("Follow all grid lines")
        self.every.setToolTip(help_of("#tr-every"))
        self.every.setChecked(True)
        self.every.toggled.connect(self.every_changed)
        checks.addWidget(self.snap)
        checks.addWidget(self.every)
        checks.addStretch(1)
        v.addLayout(checks)
        btns = QHBoxLayout()
        self.detect_btn = detect = QPushButton("Find axes again")
        detect.setToolTip("Find the grid lines and put the lines on them again")
        detect.clicked.connect(self.detect_again)
        self.ocr_btn = QPushButton("Read labels")
        self.ocr_btn.setToolTip("Read the numbers on the axes again and write the values in the boxes")
        self.ocr_btn.clicked.connect(self.read_again)
        btns.addWidget(detect)
        btns.addWidget(self.ocr_btn)
        btns.addStretch(1)
        v.addLayout(btns)
        self.axis_note = _Note()
        v.addWidget(self.axis_note)
        return box

    def _trace_box(self):
        # (automatic first, the button the Guide says to use first, with its two settings; then the curves; then "Trace
        # manually": the tools, their words and the edit row, Clear set apart. The UI audit, 2026-11-08)
        box, v = self._card()
        # Trace automatically with the colour it traced beside it; the tolerance on a row of its own (the slider's room
        # at 10.5 pt text)
        row = QHBoxLayout()
        self.auto_btn = QPushButton("Trace automatically")
        theme.mark(self.auto_btn, primary=True)
        self.auto_btn.setToolTip("The app finds and follows a curve. Click again for the next curve (A)")
        self.auto_btn.clicked.connect(self.auto_trace)
        icons.put(self.auto_btn, "run")
        row.addWidget(self.auto_btn)
        self.swatch = QLabel()
        self.swatch.setObjectName("trSwatch")  # (its frame: theme_sheet's tracer part; its colour: the traced one)
        self.swatch.setFixedSize(18, 18)
        self.swatch.setToolTip("Color that you trace")
        row.addWidget(self.swatch)
        row.addStretch(1)
        v.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(_label("Color tolerance", wrap=False))
        self.tol = QSlider(Qt.Horizontal)
        self.tol.setAccessibleName("Color tolerance")
        self.tol.setRange(8, 128)
        self.tol.setToolTip(help_of("#tr-tol"))
        self.tol.valueChanged.connect(self.tol_moved)
        row.addWidget(self.tol, 1)
        row.addWidget(self._tag("tol"))
        v.addLayout(row)
        row = QHBoxLayout()
        self.dashed = QCheckBox("Dashed or dotted line")
        self.dashed.setToolTip(help_of("#tr-dashed"))
        self.dashed.toggled.connect(self.dashed_changed)
        row.addWidget(self.dashed)
        row.addWidget(self._tag("dashed"))
        row.addStretch(1)
        v.addLayout(row)
        self.curves_box = QWidget()
        self.curves_lay = QVBoxLayout(self.curves_box)
        self.curves_lay.setContentsMargins(0, 0, 0, 0)
        self.curves_lay.setSpacing(2)
        v.addWidget(self.curves_box)
        row = QHBoxLayout()
        self.add_btn = QPushButton("Add a curve")  # (verb first, UI-RULES 15: it was "Another curve"; Windows 11's +)
        self.add_btn.setToolTip("Trace one more curve on the same graph (for example, the other channel)")
        self.add_btn.clicked.connect(self.add_curve)
        icons.put(self.add_btn, "add")
        row.addWidget(self.add_btn)
        self.curves_note = _label("", "muted")
        row.addWidget(self.curves_note, 1)
        v.addLayout(row)
        self.manual_head = QLabel("Trace manually")  # (a section title in the card: UI-RULES 26)
        theme.mark(self.manual_head, role="section")
        v.addWidget(self.manual_head)
        tools = QHBoxLayout()
        tools.setSpacing(0)  # (one group: theme_sheet's tracer part rounds only its two ends; the one on is filled in
        # the accent, as Windows 11's toggle buttons: UI-RULES 8)
        self.tool_btns = {}
        group = QButtonGroup(self)
        for n, (key, text, tip) in enumerate(TOOLS):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            theme.mark(b, trTool="first" if n == 0 else "last" if n == len(TOOLS) - 1 else "mid")
            icons.put(b, TOOL_SYMBOLS[key])
            group.addButton(b)
            tools.addWidget(b)
            self.tool_btns[key] = b
        tools.addStretch(1)
        v.addLayout(tools)
        row = QHBoxLayout()
        self.edit_btns = {}
        for key, text, tip, fn in (("smooth", "Make smooth", "Make the pixel steps smooth (S)", self.smooth),
                                   ("undo", "Undo", "Undo (Ctrl+Z)", self.undo), ("redo", "Redo", "Redo (Ctrl+Shift+Z)", self.redo),
                                   ("clear", "Clear", "Clear the selected curve (Delete)", self.clear)):
            if key == "clear":
                row.addSpacing(12)  # (Clear set apart, as every row's: UI-RULES 14)
            b = QPushButton(text)  # (no symbols in this row: Smooth and Clear have none, UI-RULES 9)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
            self.edit_btns[key] = b
        row.addStretch(1)
        v.addLayout(row)
        return box

    def _save_box(self):
        box, v = self._card()
        g = QGridLayout()
        v.addLayout(g)
        g.addWidget(_label("Name", wrap=False), 0, 0)
        self.name = QLineEdit()
        self.name.setToolTip(help_of("#tr-name"))
        self.name.textEdited.connect(lambda s: self.t.v.__setitem__("name", s))
        g.addWidget(self.name, 0, 1, 1, 3)
        g.addWidget(_label("Points in each octave", wrap=False), 1, 0)
        self.ppo = SearchCombo()
        for n in (12, 24, 48, 96):
            self.ppo.addItem(str(n), n)
        self.ppo.sort_items()
        self.ppo.setToolTip(help_of("#tr-ppo"))
        self.ppo.activated.connect(self.ppo_changed)
        g.addWidget(self.ppo, 1, 1)
        g.addWidget(self._tag("ppo"), 1, 2)
        g.addWidget(_label("The graph shows", wrap=False), 2, 0)
        self.comp = SearchCombo()
        self.comp.setToolTip(help_of("#tr-comp"))
        self.comp.setMinimumContentsLength(16)  # (a long target name doesn't widen the side)
        self.comp.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        g.addWidget(self.comp, 2, 1, 1, 3)
        g.addWidget(_label("Save from (Hz)", wrap=False), 3, 0)
        rng = QHBoxLayout()
        self.fmin, self.fmax = QLineEdit(), QLineEdit()
        for key, b in (("fmin", self.fmin), ("fmax", self.fmax)):
            b.setMaximumWidth(80)
            b.setToolTip(help_of("#tr-fmin") + f"\nPermitted: {self.limits.text('trace.save')}.")
            b.textEdited.connect(lambda _t, k=key: self.value_typed(k, "trace.save"))
            b.editingFinished.connect(lambda k=key: self.value_left(k, "trace.save"))
            self.boxes[key] = b
        rng.addWidget(self.fmin)
        rng.addWidget(self._tag("fmin"))
        rng.addWidget(_label("to", wrap=False))
        rng.addWidget(self.fmax)
        rng.addWidget(self._tag("fmax"))
        rng.addStretch(1)
        g.addLayout(rng, 3, 1, 1, 3)
        btns = QHBoxLayout()
        self.save_meas = QPushButton("Add as measurement")
        theme.mark(self.save_meas, primary=True)
        self.save_meas.clicked.connect(lambda: self.save("measurement"))
        icons.put(self.save_meas, "add")
        self.save_tgt = QPushButton("Add as target")
        self.save_tgt.clicked.connect(lambda: self.save("target"))
        icons.put(self.save_tgt, "add")  # (every button in the row with its symbol, UI-RULES 9)
        self.download_btn = QPushButton("Save .txt…")
        self.download_btn.clicked.connect(self.save_txt)
        icons.put(self.download_btn, "save")
        for b in (self.save_meas, self.save_tgt, self.download_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        g.addLayout(btns, 4, 0, 1, 4)
        # (the target line that the automatic read found in a picture from a website: a row of its own under the
        # buttons, shown only with such a line)
        line_row = QHBoxLayout()
        self.save_line = QPushButton("Add the target line as target…")
        self.save_line.setToolTip("Adds the target line of the picture as a target. You give its name first.")
        self.save_line.clicked.connect(self.add_target_line)
        icons.put(self.save_line, "add")
        help_window.tag(self.save_line, "#tr-target-line")
        line_row.addWidget(self.save_line)
        line_row.addStretch(1)
        g.addLayout(line_row, 5, 0, 1, 4)
        self.save_line.hide()
        self.save_note = _Note()
        g.addWidget(self.save_note, 6, 0, 1, 4)
        g.setColumnStretch(3, 1)
        return box

    # ---------------------------------------------------------------- showing the state
    def show_values(self):
        """The tracer's values into the boxes (not the one being typed in)."""
        tv = self.t.v
        for key, b in self.boxes.items():
            if not b.hasFocus():
                b.setText(str(tv[key]))
                theme.mark(b, bad=False)
        for w, on in ((self.snap, tv["snap"]), (self.every, tv["every"]), (self.dashed, tv["dashed"])):
            w.blockSignals(True)
            w.setChecked(bool(on))
            w.blockSignals(False)
        self.tol.blockSignals(True)
        self.tol.setValue(int(tv["tol"]))
        self.tol.blockSignals(False)
        self.ppo.setCurrentIndex(max(0, self.ppo.findData(int(tv["ppo"]))))
        if not self.name.hasFocus():
            self.name.setText(tv["name"])
        self.axis_note.setText(getattr(self.t, "axis_note", "") if self.t.has_image else "")

    def render_auto_settings(self):
        t, ta = self.t, self.t.ta
        on = ta["enabled"]
        self.auto_on.blockSignals(True)
        self.auto_on.setChecked(on)
        self.auto_on.blockSignals(False)
        self.auto_state.setText("off" if not on else "adjusted for this picture" if t.has_image else "no picture")
        esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
        notes = [(k, x) for k, x in ta["notes"].items() if x]
        if on:
            items = "".join(f"<li><i>your value</i> Automatic: {esc(x)} The app uses your value.</li>" if t.is_your_value(k)
                            else f"<li>{esc(x)}</li>" for k, x in notes) or "<li>Open a picture to adjust the settings for it.</li>"
        else:
            items = "<li>The automatic settings are off.</li>"
        self.auto_notes.setText(f"<ul style='margin-left: -24px'>{items}</ul>")
        tv = t.v
        eff = [("Color tolerance", tv["tol"], "tol"), ("Points in each octave", tv["ppo"], "ppo"),
               ("Save", f"{tv['fmin']}–{tv['fmax']} Hz", "fmin"), ("Dashed line", "yes" if tv["dashed"] else "no", "dashed")]
        def whose(k):
            return f" <i>{'your value' if t.is_your_value(k) else 'automatic'}</i>" if on and k else ""
        self.auto_eff.setText("<br>".join(f"{a}: <b>{esc(str(b))}</b>" + whose(k) for a, b, k in eff))
        mine = sorted(ta["manual"])
        self.auto_manual.setVisible(on and bool(mine))
        self.auto_manual.setText("Your values (not changed): " + ", ".join(
            f"{tc.NAMES[k]} <a href='{k}'>↺</a>" for k in mine) + " · <a href='*'>Make all automatic</a>")
        for k, b in self.tags.items():
            yours = t.is_your_value(k)
            b.setVisible(on)
            b.setEnabled(yours)
            b.setText("your value ↺" if yours else "automatic")
            b.setToolTip("You set this value. Click to make it automatic." if yours else
                         "The automatic settings set this value. Change it to use your value.")

    def update_ui(self):
        t = self.t
        cur = t.curves[t.cur] if t.curves else None
        has = bool(cur and t.has_data(cur))
        anything = any(t.has_data(c) for c in t.curves)
        self.edit_btns["undo"].setEnabled(bool(t.undo_stack))
        self.edit_btns["redo"].setEnabled(bool(t.redo_stack))
        self.edit_btns["smooth"].setEnabled(has)
        self.edit_btns["clear"].setEnabled(has)
        img = t.has_image
        for b in (self.add_btn, self.auto_btn, self.save_meas, self.save_tgt, self.save_line, self.download_btn,
                  self.ocr_btn):
            b.setEnabled(img and (b is not self.ocr_btn or not getattr(self, "reading", False)))
        self.remove_btn.setVisible(img)
        need = "" if not img else "Type the dB values of the red lines (and examine the blue Hz values) to save the curve." \
            if not t.calib() else "Trace a curve to save it." if not anything else None
        # (the target line of a picture from a website: its button while a curve has the "target" mark; a line that
        # the user changed lost the mark, trace_core.user_edit, and is a measurement curve: said, not silent)
        self.save_line.setVisible(img and any(c.get("target") and t.has_data(c) for c in t.curves))
        changed_line = next((c for c in t.curves if c.get("website_line") and not c.get("target") and t.has_data(c)),
                            None)
        if need or not getattr(self, "saved_note", False):  # ("Saved as …" stays until something is needed)
            self.saved_note = False
            self.save_note.setText(need or (
                f"You changed the curve “{changed_line['label']}”. Thus, it is a measurement curve: Add as measurement "
                "also adds it. To add it as a target, select it, then click Add as target." if changed_line else
                self.auto_note))
        colour = cur and cur["colour"]
        self.swatch.setVisible(bool(colour))
        if colour:  # (the colour traced: the picture's own, set here; its frame follows the theme, from the sheet)
            self.swatch.setStyleSheet(f"background: rgb{tuple(int(c) for c in colour)};")
        for k in ("d1", "d2"):
            self.boxes[k].setPlaceholderText("type it" if img else "")
        self.stage.update()

    def render_curves(self):
        lay, t = self.curves_lay, self.t
        while lay.count():
            w = lay.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.curve_rows = []
        for i, c in enumerate(t.curves):
            row = QFrame()
            self.curve_rows.append(row)
            theme.mark(row, trRow="chosen" if i == t.cur else "")  # (chosen: as a chosen list row, the accent's bar)
            h = QHBoxLayout(row)
            h.setContentsMargins(8, 3, 4, 3)
            h.setSpacing(6)
            pick = QPushButton()  # (its trace's colour on the picture, as a dot)
            pick.setIcon(_dot(STROKES[i % len(STROKES)]))
            pick.setIconSize(QSize(16, 16))
            theme.mark(pick, quiet=True, trCompact=True)
            pick.setToolTip("Trace into this curve")
            pick.clicked.connect(lambda _=False, i=i: self.select_curve(i))
            h.addWidget(pick)
            name = QLineEdit(c["label"])
            name.setAccessibleName(f"Curve {i + 1}'s name")
            name.setMaxLength(12)
            name.setToolTip("Curve name (the app uses it in the file names, for example, L and R)")
            name.installEventFilter(self)
            name.setProperty("curve", i)
            h.addWidget(name, 1)
            n = int(np.isfinite(c["ys"]).sum())
            h.addWidget(_label(f"{n} px" if n else "empty", "muted", wrap=False))
            x = QPushButton("✕")
            x.setToolTip("Remove this curve (you can undo this)")
            theme.mark(x, quiet=True, trCompact=True)
            x.clicked.connect(lambda _=False, i=i: self.remove_curve(i))
            h.addWidget(x)
            _name_curve_buttons(pick, x, c["label"], i)

            def renamed(s, c=c, pick=pick, x=x, i=i):
                c["label"] = s.strip()
                _name_curve_buttons(pick, x, c["label"], i)
                if c.get("target"):  # (a renamed target line is a measurement curve: the core does not see a rename)
                    self.t.user_edit(i)
                    self.update_ui()
            name.textEdited.connect(renamed)
            lay.addWidget(row)
        _no_focus(self.curves_box)
        self.curves_note.setText("The app saves the curves as one device: one file for each curve, with its label in the name "
                                 "(for example, L and R)."
                                 if sum(map(t.has_data, t.curves)) > 1 else "")

    def eventFilter(self, obj, e):
        from PySide6.QtCore import QEvent
        if e.type() == QEvent.FocusIn and obj.property("curve") is not None and obj.property("curve") != self.t.cur:
            # (the curve whose name is being typed becomes the selected one; its row isn't rebuilt under the click)
            self.t.cur = int(obj.property("curve"))
            for i, row in enumerate(getattr(self, "curve_rows", [])):
                theme.mark(row, trRow="chosen" if i == self.t.cur else "")
            self.update_ui()
        return super().eventFilter(obj, e)

    def changed(self):
        """After a trace or an edit: the curves, the buttons and the picture."""
        self.saved_note = False
        self.render_curves()
        self.show_values()  # (a trace may have ticked Dashed or raised the tolerance)
        self.render_auto_settings()
        self.update_ui()

    def fit_and_show(self):
        self.t.fit_settings()
        self.show_values()
        self.render_auto_settings()
        self.update_ui()

    def say(self, text):
        if text:
            self.status.setText(text)

    def start_guide(self):
        from ui import guide
        self.tour = guide.start_trace(self)

    # ---------------------------------------------------------------- the picture
    def choose_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "A graph to trace", os.path.expanduser("~"), IMAGES + ";;All files (*)")
        if f:
            self.open_file(f)

    def open_file(self, path, entry=None):
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, "Trace", "The app cannot read this file as a picture (PNG, JPG, WebP, BMP, GIF, TIFF).")
            return
        name = os.path.splitext(os.path.basename(path))[0]
        self.load_image(img, name, os.path.splitext(path)[1].lower() in (".jpg", ".jpeg", ".jfif"), entry)

    def kept_entry(self):
        """The entry a picture pasted or dropped here keeps: the present one only when nothing was added from the
        picture before and its automatic read was not OK (the user gives a better picture of the same graph)."""
        return self.entry if self.entry and not self.added and self.read_ok is False else None

    def load_image(self, qimg, name="Traced graph", jpeg=False, entry=None):
        """A picture into the tracer. entry: the database entry of a picture from a website (/api/db/entry's): its
        name with its tag is the picture's name, and the automatic read (read_graph) replaces the label read."""
        self.sample_open = False  # (a picture of yours: the Guide's sample, set again by the Guide, isn't on any more)
        self.entry = entry
        self.added = False
        self.read_ok = None
        self.auto_note = ""
        self.graph_token += 1  # (an automatic read still running for the picture before is dropped)
        self._reading_graph(False)
        if entry:
            name = self.entry_name()
        rgb = rgb_of(qimg)
        try:
            self.t.load(rgb, name, jpeg)
        except Exception as e:  # noqa: BLE001 - a picture whose axes trip the reader: said, the tracer left empty
            import traceback
            traceback.print_exc()
            self.t.unload()
            self.stage.clear_image()
            self.show_name()
            self.changed()
            QMessageBox.warning(self, "Trace", f"The app cannot read the axes of this picture ({e}). Send the picture "
                                "and data\\app.log. Then we can correct the problem.")
            return
        h, w = rgb.shape[:2]
        self.show_name(name if name != "Traced graph" else "Pasted picture", (w, h))
        self.show_tab(0)  # (a new picture: its axes first)
        self.stage.set_image(rgb)
        self.saved_note = False
        self.status.setText(HINTS[self.tool])
        self.fill_comp()
        self.show_values()
        self.changed()
        self.read_graph() if entry else self.read_labels()

    def entry_name(self):
        """The name of a picture from a website: the entry's name and its database's tag, as a downloaded entry's."""
        e = self.entry or {}
        return f"{e.get('name', '')} ({e.get('tag', '')})" if e.get("tag") else e.get("name", "")

    def source_note(self):
        """The part of a traced file's first line that names the website and the entry's link."""
        e = self.entry
        return f" (a picture from {e.get('site')}: {e.get('link')})" if e and e.get("link") else ""

    def _reading_graph(self, on):
        """While the automatic read runs, the picture and the side take no input (take() then replaces the tracer's
        state: the user's work would go)."""
        self.reading_graph = on
        for w in (self.stage, self.side_scroll, self.guide_btn):
            w.setEnabled(not on)

    def read_graph(self):
        """The automatic read of a picture from a website (trace_core.auto_read) off the window's thread; its answer
        taken into the window's tracer: all checks OK, 3 Save with the traced curve; else the tab of the first check
        that failed, with its reason (the user corrects that step); an error, 1 Axes and the labels read."""
        t = self.t
        if not t.has_image or not self.entry:
            return
        from ui import ocr
        rgb, jpeg, name, entry = t.px.copy(), bool(t.ta["jpeg"]), self.entry_name(), self.entry
        self.graph_token += 1
        token = self.graph_token
        t.label_token += 1  # (a label read still running is dropped)
        self.reading = False
        self._reading_graph(True)
        self.status.setText("The app reads the graph…")
        self.update_ui()

        def done(res, err):
            if token != self.graph_token:  # (another picture, or the picture removed, meanwhile)
                return
            self._reading_graph(False)
            if err is not None:
                self.read_ok = False
                self.show_tab(0)
                self.status.setText(f"The app cannot trace this picture automatically ({err}). Correct this step. "
                                    "Then go to 3 Save.")
                self.read_labels()
                return
            self.take_read(res, entry)
        tasks.background(lambda: tc.auto_read(rgb, ocr.words, jpeg, name), done, owner=self)

    def take_read(self, r, entry):
        """auto_read's answer (an AutoRead) into the window: the tracer's state taken (a crop of the picture: the
        stage, the name, the size, the values and the settings shown again), then the tab that the result needs.
        entry: the one the read was for (the window's can go meanwhile: its close)."""
        t = self.t
        if r.target is not None:
            r.target["website_line"] = True  # (this curve was the target line: said when the user changes it)
        t.take(r.tracer)
        self.stage.set_image(t.px)
        self.show_name(t.src_name, (t.W, t.H))
        self.read_ok = bool(r.ok)
        e = entry or {}
        if r.ok:
            self.auto_note = (f"The app traced the graph of “{e.get('name', '')}” from {e.get('site', '')}. Compare the "
                              "curve with the picture. If they agree, click Add as measurement."
                              + (" The picture also has a target line. Add the target line as target… adds it as a "
                                 "target." if r.target is not None else ""))
            self.status.setText(HINTS[self.tool])
            self.show_tab(2)
        else:
            first = next(c for c in r.checks if not c.ok)
            text = f"The app cannot trace this picture automatically. {first.reason} Correct this step. Then go to 3 Save."
            axes = first.name.startswith("axes")
            if axes:
                t.axis_note = t.detect_note = text  # (also on 1 Axes; a label read starts from it)
            self.show_tab(0 if axes else 1)
            self.status.setText(text)
        self.show_values()
        self.changed()
        if not r.ok and r.checks and next(c for c in r.checks if not c.ok).name == "axes_plot":
            self.read_labels()  # (not a graph of the website: today's way for a picture)

    def remove_image(self):
        t = self.t
        if not t.has_image:
            return
        if any(map(t.has_data, t.curves)) and QMessageBox.question(  # (No the default: the curves can't be had back)
                self, "Remove image", "Remove this picture and the curves that you traced on it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.entry, self.added, self.read_ok, self.auto_note = None, False, None, ""
        self.graph_token += 1  # (an automatic read still running is dropped)
        self._reading_graph(False)
        t.unload()
        t.v.update(d1="", d2="", f1="", f2="", name="")
        t.typed = {"d": False, "f": False}
        t.ta.update(notes={}, dashed_found=False, last_ocr=None, last_trace=None)
        if t.ta["enabled"] and not t.is_your_value("dashed"):
            t.v["dashed"] = False
        self.reading = False
        self.stage.clear_image()
        self.show_name()
        self.saved_note = False
        self.save_note.setText("")
        self.show_values()
        self.changed()
        self.status.setText("The app removed the picture. Open, drag or paste a different picture.")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() or e.mimeData().hasImage():
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        entry = self.kept_entry()
        for u in md.urls():
            if u.isLocalFile():
                self.open_file(u.toLocalFile(), entry)
                return
        if md.hasImage():
            self.load_image(QImage(md.imageData()), entry=entry)

    def paste(self):
        img = QApplication.clipboard().image()
        if img.isNull():
            self.say("There is no picture on the clipboard. First, copy a picture of a graph.")
            return
        self.load_image(img, entry=self.kept_entry())

    def closeEvent(self, e):
        self.entry = None  # (the next picture is a picture of yours, unless it comes from a website again)
        super().closeEvent(e)

    # ---------------------------------------------------------------- axes
    def value_typed(self, key, lim):
        b, t = self.boxes[key], self.t
        text = b.text().strip().replace(",", ".")
        if text == "":
            t.v[key] = ""
            theme.mark(b, bad=False)
        else:
            try:
                x = float(text)
                bad = self.limits.check(lim, x, lambda _k: None)
            except ValueError:
                bad = ("bad", "Enter a number")
            theme.mark(b, bad=bool(bad))
            b.setToolTip(bad[1] if bad else help_of(f"#tr-{key if key[0] in 'df' else 'fmin'}") + f"\nPermitted: {self.limits.text(lim)}.")
            if bad:
                return
            t.v[key] = text
        if key in ("d1", "d2", "f1", "f2"):
            t.typed[key[0]] = True
            t.fit_settings()
        else:
            t.mark_your_value(key)
        self.show_values()  # (points per octave and the range follow the axes' values; the box typed in is left be)
        self.render_auto_settings()
        self.update_ui()

    def value_left(self, key, lim):
        """Leaving a box with a value past its limits: moved to the limit (said)."""
        b = self.boxes[key]
        try:
            x = float(b.text().strip().replace(",", "."))
        except ValueError:
            return
        y = self.limits.clamp(lim, x)
        if y != x:
            b.setText(f"{y:g}")
            self.value_typed(key, lim)
            self.say(f"The app changed the value to {y:g} (permitted: {self.limits.text(lim)}).")

    def lines_moved(self):
        self.show_values()
        self.update_ui()

    def every_changed(self, on):
        self.t.v["every"] = on
        self.update_ui()

    def detect_again(self):
        t = self.t
        if not t.has_image:
            return
        try:
            t.detect()
        except Exception as e:  # noqa: BLE001 - (as on loading)
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Trace", f"The app cannot find the axes again ({e}).")
            return
        t.typed = {"d": False, "f": False}
        self.fit_and_show()
        self.read_labels()

    def read_again(self):
        self.t.typed = {"d": False, "f": False}
        self.read_labels()

    def read_labels(self):
        """The axis labels read with Windows' text reader, off the window's thread; the values filled in after."""
        t = self.t
        if not t.has_image:
            return
        from ui import ocr
        before = getattr(t, "detect_note", t.axis_note)  # (not the last reading's note: it added up)
        self.axis_note.setText(before + " The app reads the axis labels…")
        t.moved = {"d": False, "f": False}
        t.label_token += 1
        self.reading = True
        self.update_ui()

        def done(res, err):
            if t.label_token != token:  # (another picture, or read again, meanwhile)
                return
            self.reading = False
            if err is not None:
                t.axis_note = before + f" (The app cannot read the labels: {err}. Type the values.)"
            else:
                t.use_labels(res, before)
            self.show_values()
            self.render_auto_settings()
            self.update_ui()
        token = t.label_token
        tasks.background(lambda: t.read_labels(ocr.words), done, owner=self)

    # ---------------------------------------------------------------- trace
    def set_tool(self, key):
        self.tool = key
        for k, b in self.tool_btns.items():
            b.setChecked(k == key)
        self.status.setText(HINTS[key])

    def select_curve(self, i):
        self.t.cur = i
        self.changed()

    def add_curve(self):
        if self.t.has_image:
            self.say(self.t.add_curve())
            self.changed()

    def remove_curve(self, i):
        self.t.remove_curve(i)
        self.changed()

    def auto_trace(self):
        self.say(self.t.auto_trace())
        self.changed()

    def smooth(self):
        self.t.smooth()
        self.changed()

    def undo(self):
        self.t.undo()
        self.changed()

    def redo(self):
        self.t.redo()
        self.changed()

    def clear(self):
        self.say(self.t.clear())
        self.changed()

    def tol_moved(self, v):
        self.t.v["tol"] = v
        self.t.mark_your_value("tol")
        self.render_auto_settings()

    def dashed_changed(self, on):
        self.t.v["dashed"] = on
        self.t.mark_your_value("dashed")
        self.render_auto_settings()

    def ppo_changed(self, _i):
        self.t.v["ppo"] = self.ppo.currentData()
        self.t.mark_your_value("ppo")
        self.render_auto_settings()

    # ---------------------------------------------------------------- automatic settings
    def _save_trace_settings(self):
        """The automatic settings' switch into the app's settings, written half a second after the last change,
        without redrawing the other screens (as Listen's)."""
        ta, sw = self.t.ta, self.page.sw
        sw.s["trace"] = {"enabled": ta["enabled"]}
        if not hasattr(self, "_save_timer"):
            self._save_timer = QTimer(self, singleShot=True, interval=500, timeout=sw.save)
            QApplication.instance().aboutToQuit.connect(sw.save)
        self._save_timer.start()

    def auto_switched(self, on):
        self.t.ta["enabled"] = on
        self._save_trace_settings()
        self.fit_and_show() if on else self.render_auto_settings()

    def make_auto(self, k):
        self.t.make_auto(k)
        self.fit_and_show()

    # ---------------------------------------------------------------- save
    def fill_comp(self):
        """The targets a graph may have been drawn relative to."""
        was = self.comp.currentData()
        self.comp.clear()
        self.comp.addItem("Frequency response (not compensated)", "")  # (sentence case, as every choice: 15)
        for n in (getattr(self.page, "inputs", None) or {}).get("targets", []):
            self.comp.addItem(f"Difference from {os.path.splitext(n)[0]}", n)
        self.comp.sort_items(pinned=1)  # ("the actual response" on top)
        self.comp.setCurrentIndex(max(0, self.comp.findData(was)))

    def compensation(self):
        """The graph was drawn relative to a target (compensated): that target's curve, to add back."""
        name = self.comp.currentData()
        if not name:
            return None, ""
        S = self.page.S
        # (as it is: the site's graph smoothing off, which would round off its peaks; its level is evened out later)
        r = self.page.svc.call("/api/preview", {"src": "app", "kind": "target", "names": [name],
                                                "settings": dict(S, site=dict(S["site"], smooth_level=0))})
        if r.get("error"):
            raise ValueError(r["error"])
        f = [20.0]
        while f[-1] < 20000:
            f.append(f[-1] * 2 ** (1 / 48))  # (squiglink's grid)
        lf, vals = np.log(f), np.asarray(r["vals"], float)
        return (lambda x: float(np.interp(math.log(x), lf, vals))), \
            f" (the graph showed the difference from {os.path.splitext(name)[0]}: the app added this target)"

    def outputs(self, only_current=False, name=None):
        """The files to save (trace_core's outputs; name: in place of the Name box's). A picture from a website: their
        first line also names the website and the entry's link."""
        comp, note = self.compensation()
        return self.t.outputs(only_current, comp, note + self.source_note(), name=name)

    def source(self, name):
        """The source record of an add from a picture from a website (eq.service records it for the files: their rig
        is the database's), with `name`: the entry's for a measurement, the target's own for a target."""
        e = self.entry
        return dict(e, name=name) if e and e.get("site_url") else None

    def save(self, kind, outs=None, title=None):
        """Into the app: a measurement (the traced curves as one device, made the one in use) or a target. outs: the
        files to add (none: the window's curves, as outputs() makes them); title: the message boxes' title."""
        page = self.page
        title = title or f"Add as {kind}"
        try:
            outs = outs if outs is not None else self.outputs(kind == "target")
        except (ValueError, ArithmeticError) as e:
            QMessageBox.warning(self, "Trace", str(e))
            return
        # (all channels in one go: one number for the set when names are taken, so they stay one device)
        body = {"kind": kind, "files": [{"name": o["file"], "content": o["text"]} for o in outs], "settings": page.S}
        src = self.source(self.entry["name"] if kind == "measurement" and self.entry else
                          os.path.splitext(outs[0]["file"])[0])
        if src:
            body["source"] = src
        r = page.svc.call("/api/files/add", body)
        if r.get("error"):
            QMessageBox.warning(self, title, r["error"])
            return
        self.added = True
        names, page.S, inputs = r["names"], r["settings"], r["inputs"]
        if kind == "measurement" and inputs:  # a traced graph is a device of its own: exactly its files in use
            page.S["files"]["excluded"] = [m["name"] for m in inputs["measurements"] if m["name"] not in names]
            page.svc.call("/api/settings", {"settings": page.S})
        st = page.svc.call("/api/state")
        if "inputs" in st:
            page.S = st["settings"]
            page.show_inputs(st["inputs"])
            page.show_settings()
            page.load_curves()
        what = "the target" if kind == "target" else f"{len(names)} files of one measurement" if len(names) > 1 else "the measurement"
        shown = "”, “".join(os.path.splitext(n)[0] for n in names)
        self.saved_note = True
        self.save_note.setText(f"The app saved {what} “{shown}”. To see it on the graph, close this window. "
                               "You can also trace more curves."
                               + (" (The app saved only the selected curve, because a target is one curve.)"
                                  if kind == "target" and title == "Add as target"
                                  and sum(map(self.t.has_data, self.t.curves)) > 1 else ""))
        gaps = self.t.gaps_text(outs)
        if gaps:
            QMessageBox.information(self, "Trace", gaps)

    def add_target_line(self):
        """Add the target line as target…: the curve that the automatic read marked as the target line, added as a
        target under the name that the user gives (Add as measurement leaves it out)."""
        from ui.window_parts import ask_text  # (looked up here: the tests answer it)
        t = self.t
        i = next((i for i, c in enumerate(t.curves) if c.get("target") and t.has_data(c)), None)
        if i is None:
            return
        title = "Add the target line as target"
        name, ok = ask_text(self, title, "Name of the target", f"Target from {t.src_name}", "Add")
        if not ok or not name.strip():
            return
        was = t.cur
        t.cur = i  # (outputs' "only the selected curve" is this one)
        try:
            outs = self.outputs(True, name=name.strip())
        except (ValueError, ArithmeticError) as e:
            QMessageBox.warning(self, title, str(e))
            return
        finally:
            t.cur = was
        self.save("target", outs, title)

    def save_txt(self):
        """The traced curves as .txt files wherever you choose."""
        try:
            outs = self.outputs(False)
        except (ValueError, ArithmeticError) as e:
            QMessageBox.warning(self, "Trace", str(e))
            return
        start = os.path.join(os.path.expanduser("~"), "Downloads")
        if len(outs) == 1:
            path, _ = QFileDialog.getSaveFileName(self, "Save the traced curve", os.path.join(start, outs[0]["file"]),
                                                  "Text (*.txt)")
            paths = [path] if path else []
        else:
            folder = QFileDialog.getExistingDirectory(self, "A folder for the traced curves", start)
            paths = [os.path.join(folder, o["file"]) for o in outs] if folder else []
            there = [os.path.basename(p) for p in paths if os.path.exists(p)]
            if there and QMessageBox.question(self, "Save .txt", "These files are in that folder:\n\n" + "\n".join(there)
                                              + "\n\nReplace them?", QMessageBox.Yes | QMessageBox.No,
                                              QMessageBox.No) != QMessageBox.Yes:
                return
        for path, o in zip(paths, outs):
            try:
                textfile.write_atomic(path, o["text"])
            except OSError as e:  # (a folder you can't write to, a file another program holds: said, not silent)
                QMessageBox.warning(self, "Trace", f"The app cannot save {os.path.basename(path)}: {e}")
                return
        if paths:  # (said here, under the buttons, as Add as measurement's: never in the window behind, UI-RULES 7)
            self.save_note.setText(f"The app saved {', '.join(os.path.basename(p) for p in paths)}.")
            self.saved_note = True  # (kept until something changes, as "Saved as …": the next redraw wiped it at once)
            gaps = self.t.gaps_text(outs)
            if gaps:
                QMessageBox.information(self, "Trace", gaps)

    # ---------------------------------------------------------------- keys
    def keyPressEvent(self, e):
        st = self.stage
        typing = isinstance(QApplication.focusWidget(), (QLineEdit, QComboBox))
        key, mods = e.key(), e.modifiers()
        if self.reading_graph and not (mods & Qt.ControlModifier and key == Qt.Key_V):
            return super().keyPressEvent(e)  # (the automatic read runs: no key changes the tracer, but a new picture)
        if key == Qt.Key_Space and not typing:
            if not e.isAutoRepeat():
                st.space = True
            return
        if typing:
            return super().keyPressEvent(e)
        # (a key whose control is on a tab shows that tab first, so you see what it changed: Undo and Redo are 2
        # Trace's, the arrows move a line of 1 Axes. They acted on a hidden tab, 2026-11-10. Ctrl+V, F, + and - are
        # the picture's own: no tab changes)
        ctrl = bool(mods & Qt.ControlModifier)
        if ctrl and key in (Qt.Key_Z, Qt.Key_Y):
            if self.t.has_image:
                self.show_tab(1)
            self.redo() if key == Qt.Key_Y or mods & Qt.ShiftModifier else self.undo()
            return
        if ctrl and key == Qt.Key_V:
            self.paste()
            return
        if ctrl or mods & Qt.AltModifier:
            return super().keyPressEvent(e)
        if st.sel_line and key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            d = (10 if mods & Qt.ShiftModifier else 1) / max(1, st.view["s"]) * (-1 if key in (Qt.Key_Up, Qt.Key_Left) else 1)
            if (st.sel_line[0] == "y") == (key in (Qt.Key_Up, Qt.Key_Down)):
                self.show_tab(0)  # (the line's values are 1 Axes')
                self.t.cal[st.sel_line] += d
                self.t.moved["d" if st.sel_line[0] == "y" else "f"] = True
                self.fit_and_show()
            return
        acts = {Qt.Key_T: lambda: self.set_tool("trace"), Qt.Key_D: lambda: self.set_tool("draw"),
                Qt.Key_E: lambda: self.set_tool("erase"), Qt.Key_H: lambda: self.set_tool("pan"),
                Qt.Key_A: self.auto_trace, Qt.Key_S: self.smooth, Qt.Key_F: st.fit_now,
                Qt.Key_Plus: lambda: st.zoom(1.25), Qt.Key_Equal: lambda: st.zoom(1.25), Qt.Key_Minus: lambda: st.zoom(0.8),
                Qt.Key_Backspace: self.clear, Qt.Key_Delete: self.clear}
        if key in acts and self.t.has_image:
            if key not in (Qt.Key_F, Qt.Key_Plus, Qt.Key_Equal, Qt.Key_Minus):
                self.show_tab(1)  # (a key of the Trace step: its card shown, where the curves change)
            acts[key]()
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self.stage.space = False
        super().keyReleaseEvent(e)
