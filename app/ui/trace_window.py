"""Trace a graph image (AutoEQ Local's tracer window, natively; the workings are ui/trace_core.py): a picture of a
frequency-response graph (a maker's sheet, a review's screenshot) becomes a measurement or a target.

- the picture (open, drop or paste it): the four calibration lines (red: dB, blue: Hz) dragged onto gridlines, the
  traces drawn over it, zoom (wheel, + / -, Fit) and move (Move, Space or the right button); the Hz and dB under the
  pointer
- the side: Automatic settings (switch, Why these settings), 1 Axes (the four values, Snap to
  gridlines, Follow every gridline, Find axes again, Read labels), 2 Trace (Click curve, Draw, Erase, Move; the curves
  with their names; Another curve; Auto trace; colour tolerance; dashed lines; Smooth, Undo, Redo, Clear), 3 Save
  (name, points per octave, what the graph shows, the range; Add as measurement, Add as target, Save .txt…)
- keys: T D E H tools, A Auto trace, S Smooth, F fit, + - zoom, Delete clears, Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y,
  arrows move a selected line (Shift: 10 px), Ctrl+V pastes a picture
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
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
                               QSlider, QToolButton, QVBoxLayout, QWidget)

import textfile
from ui import help_window, icons, tasks, theme
from ui.forms import Fold, Limits, help_of
from ui import trace_core as tc
from ui.search_combo import SearchCombo

RED, BLUE, GREEN = "#d93025", "#1a73e8", "#16a34a"
STROKES = ["#ff00d4", "#00a8e8", "#ff8a00", "#8e44ff", "#00b35f", "#e6b800"]
TOOLS = [("trace", "Click curve", "Click a curve to follow it (T)"), ("draw", "Draw", "Drag along the curve to draw it (D)"),
         ("erase", "Erase", "Drag a box over the trace to remove it (E)"),
         ("pan", "Move", "Drag to move the picture; or hold Space, or drag with the right mouse button (H)")]
TOOL_SYMBOLS = {"trace": "trace", "draw": "pen", "erase": "erase", "pan": "move"}  # (icons.GLYPHS' names)
SIDE = 500  # (the settings' width: room for 10.5 pt text, "the actual response (not compensated)" whole, symbols)
RADIUS = 8  # (the picture's card: a card's corners, as theme_sheet's)
HINTS = {"trace": "Click a curve to follow it.", "draw": "Drag along the curve to draw it by hand.",
         "erase": "Drag a box around the part of the trace to remove.", "pan": "Drag to move the picture."}
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


def _curve_names(pick, delete, label, i):
    """A curve's dot and ✕ named with the curve's name for a screen reader ("Select curve L", "Delete curve L"), again
    when it's renamed: every row's were read alike ("Trace into this curve", "Delete this curve"), 2026-10-23."""
    name = label or str(i + 1)
    pick.setAccessibleName(f"Select curve {name}")
    delete.setAccessibleName(f"Delete curve {name}")


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
        head = QLabel("Drop a frequency response graph here")
        head.setObjectName("trDropHead")
        head.setAlignment(Qt.AlignCenter)
        ev.addWidget(head)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(QLabel("or paste it with Ctrl+V, or"))
        self.choose_btn = choose = QPushButton("Choose an image file…")
        theme.mark(choose, primary=True)  # (the one thing to do here)
        icons.put(choose, "open")
        choose.clicked.connect(win.choose_image)
        row.addWidget(choose)
        row.addStretch(1)
        ev.addLayout(row)
        sub = _label("Screenshots of maker or review graphs work (PNG, JPG, WebP).", "muted")
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
                                   ("fit", "Fit", "Fit the picture (F)", self.fit_now),
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
            f, v = k.f(mx), k.db(my)
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
            t.push()
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
        self.setWindowTitle("Trace a graph image")
        self.resize(1320, 860)
        self.setAcceptDrops(True)
        self.t = tc.Tracer()
        st = page.sw.s.get("trace") or {}
        if isinstance(st.get("enabled"), bool):
            self.t.ta["enabled"] = st["enabled"]
        self.tool = "trace"
        self.limits = Limits((page.meta or {}).get("limits", {}), [])
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 14)
        v.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(8)
        title = QLabel("Trace a graph image")
        title.setObjectName("trTitle")
        head.addWidget(title)
        self.file_lab = _label("", "muted", wrap=False)
        head.addWidget(self.file_lab, 1)
        self.remove_btn = QPushButton("Remove image")
        self.remove_btn.setToolTip("Remove this picture (e.g. the wrong one) and the curves traced on it")
        self.remove_btn.clicked.connect(self.remove_image)
        icons.put(self.remove_btn, "remove")
        head.addWidget(self.remove_btn)
        self.guide_btn = QPushButton("Guide")  # (Windows 11's symbol where "? " was, as the top bar's Guide)
        self.guide_btn.setToolTip("A tour of the tracer (on a sample graph when no picture is open)")
        self.guide_btn.clicked.connect(self.start_guide)
        icons.put(self.guide_btn, "guide")
        head.addWidget(self.guide_btn)
        self.open_btn = opn = QPushButton("Open image…")
        opn.setToolTip("Open another picture (or drop / paste one)")
        opn.clicked.connect(self.choose_image)
        icons.put(opn, "open")
        head.addWidget(opn)
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
        sv.addWidget(self._axes_box())
        sv.addWidget(self._trace_box())
        sv.addWidget(self._save_box())
        sv.addStretch(1)
        side_scroll.setWidget(side)
        _no_focus(side)
        body.addWidget(side_scroll)
        v.addLayout(body, 1)
        for w, key in ((self.auto_on, "#tr-auto-on"), (self.snap, "#tr-snap"), (self.every, "#tr-every"),
                       (self.tol, "#tr-tol"), (self.ppo, "#tr-ppo"), (self.fmin, "#tr-fmin"), (self.fmax, "#tr-fmin"),
                       (self.name, "#tr-name"), (self.dashed, "#tr-dashed"), (self.comp, "#tr-comp"),
                       *((self.boxes[k], "#tr-" + k) for k in ("d1", "d2", "f1", "f2"))):
            help_window.tag(w, key)
        self.set_tool("trace")
        self.show_values()
        self.render_ta()
        self.update_ui()

    # ---------------------------------------------------------------- the side
    def _tag(self, key):
        b = QToolButton()
        theme.mark(b, tag=True)
        b.clicked.connect(lambda: self.hand_back(key))
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
        why = Fold("Why these settings")
        why.setObjectName("trWhy")  # (flat inside this card: no card in a card)
        why.layout().setContentsMargins(0, 0, 0, 0)
        self.why = why
        self.auto_notes = _label("")
        self.auto_notes.setTextFormat(Qt.RichText)
        why.body_lay.addWidget(self.auto_notes)
        why.body_lay.addWidget(_label("In effect:", "muted"))
        self.auto_eff = _label("")
        self.auto_eff.setTextFormat(Qt.RichText)
        why.body_lay.addWidget(self.auto_eff)
        self.auto_manual = _label("")
        self.auto_manual.setTextFormat(Qt.RichText)
        self.auto_manual.linkActivated.connect(lambda k: self.hand_back(None if k == "*" else k))
        why.body_lay.addWidget(self.auto_manual)
        why.body_lay.addWidget(_label("Settings follow the picture; one you change is marked “yours” and kept.", "muted"))
        v.addWidget(why)
        return box

    def _axes_box(self):
        box = QGroupBox("1  Axes")
        v = QVBoxLayout(box)
        v.addWidget(_label("Drag the red lines onto two dB gridlines and the blue ones onto two frequency gridlines; "
                           "type their values.", "muted"))
        g = QGridLayout()
        self.boxes = {}
        for i, (key, text, lim) in enumerate((("d1", "Top red line (dB)", "trace.db"), ("d2", "Bottom red line (dB)", "trace.db"),
                                              ("f1", "Left blue line (Hz)", "trace.hz"), ("f2", "Right blue line (Hz)", "trace.hz"))):
            g.addWidget(_label(text, wrap=False), i // 2 * 2, i % 2)
            b = QLineEdit()
            b.setAccessibleName(text)
            b.setToolTip(help_of(f"#tr-{key}") + f"\nAllowed: {self.limits.text(lim)}.")
            b.textEdited.connect(lambda _t, k=key, lim=lim: self.value_typed(k, lim))
            b.editingFinished.connect(lambda k=key, lim=lim: self.value_left(k, lim))
            g.addWidget(b, i // 2 * 2 + 1, i % 2)
            self.boxes[key] = b
        v.addLayout(g)
        checks = QHBoxLayout()
        self.snap = QCheckBox("Snap to gridlines")
        self.snap.setToolTip(help_of("#tr-snap"))
        self.snap.setChecked(True)
        self.snap.toggled.connect(lambda on: self.t.v.__setitem__("snap", on))
        self.every = QCheckBox("Follow every gridline")
        self.every.setToolTip(help_of("#tr-every"))
        self.every.setChecked(True)
        self.every.toggled.connect(self.every_changed)
        checks.addWidget(self.snap)
        checks.addWidget(self.every)
        checks.addStretch(1)
        v.addLayout(checks)
        btns = QHBoxLayout()
        self.detect_btn = detect = QPushButton("Find axes again")
        detect.setToolTip("Find the gridlines and place the lines again")
        detect.clicked.connect(self.detect_again)
        self.ocr_btn = QPushButton("Read labels")
        self.ocr_btn.setToolTip("Read the numbers on the axes again and fill in the values")
        self.ocr_btn.clicked.connect(self.read_again)
        btns.addWidget(detect)
        btns.addWidget(self.ocr_btn)
        btns.addStretch(1)
        v.addLayout(btns)
        self.axis_note = _Note()
        v.addWidget(self.axis_note)
        return box

    def _trace_box(self):
        box = QGroupBox("2  Trace")
        v = QVBoxLayout(box)
        tools = QHBoxLayout()
        tools.setSpacing(0)  # (one group: theme_sheet's tracer part rounds only its two ends)
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
        self.curves_box = QWidget()
        self.curves_lay = QVBoxLayout(self.curves_box)
        self.curves_lay.setContentsMargins(0, 0, 0, 0)
        self.curves_lay.setSpacing(2)
        v.addWidget(self.curves_box)
        row = QHBoxLayout()
        self.add_btn = QPushButton("Another curve")  # (Windows 11's + beside the words, where "+ " was)
        self.add_btn.setToolTip("Trace another curve on the same graph, e.g. the other channel")
        self.add_btn.clicked.connect(self.add_curve)
        icons.put(self.add_btn, "add")
        row.addWidget(self.add_btn)
        self.curves_note = _label("", "muted")
        row.addWidget(self.curves_note, 1)
        v.addLayout(row)
        # Auto trace with the colour it traced beside it; the tolerance on a row of its own (the slider's room at
        # 10.5 pt text)
        row = QHBoxLayout()
        self.auto_btn = QPushButton("Auto trace")
        theme.mark(self.auto_btn, primary=True)
        self.auto_btn.setToolTip("Find and follow a curve by itself; press again for the next curve (A)")
        self.auto_btn.clicked.connect(self.auto_trace)
        icons.put(self.auto_btn, "run")
        row.addWidget(self.auto_btn)
        self.swatch = QLabel()
        self.swatch.setObjectName("trSwatch")  # (its frame: theme_sheet's tracer part; its colour: the traced one)
        self.swatch.setFixedSize(18, 18)
        self.swatch.setToolTip("Colour being traced")
        row.addWidget(self.swatch)
        row.addStretch(1)
        v.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(_label("Colour tolerance", wrap=False))
        self.tol = QSlider(Qt.Horizontal)
        self.tol.setAccessibleName("Colour tolerance")
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
        row = QHBoxLayout()
        self.edit_btns = {}
        for key, text, tip, fn in (("smooth", "Smooth", "Smooth out pixel steps (S)", self.smooth),
                                   ("undo", "Undo", "Undo (Ctrl+Z)", self.undo), ("redo", "Redo", "Redo (Ctrl+Shift+Z)", self.redo),
                                   ("clear", "Clear", "Remove the whole trace (Delete)", self.clear)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            if key in ("undo", "redo"):
                icons.put(b, key)
            row.addWidget(b)
            self.edit_btns[key] = b
        row.addStretch(1)
        v.addLayout(row)
        self.status = _label("", "muted")
        v.addWidget(self.status)
        return box

    def _save_box(self):
        box = QGroupBox("3  Save")
        g = QGridLayout(box)
        g.addWidget(_label("Name", wrap=False), 0, 0)
        self.name = QLineEdit()
        self.name.setToolTip(help_of("#tr-name"))
        self.name.textEdited.connect(lambda s: self.t.v.__setitem__("name", s))
        g.addWidget(self.name, 0, 1, 1, 3)
        g.addWidget(_label("Points per octave", wrap=False), 1, 0)
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
            b.setToolTip(help_of("#tr-fmin") + f"\nAllowed: {self.limits.text('trace.save')}.")
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
        self.download_btn = QPushButton("Save .txt…")
        self.download_btn.clicked.connect(self.download)
        icons.put(self.download_btn, "save")
        for b in (self.save_meas, self.save_tgt, self.download_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        g.addLayout(btns, 4, 0, 1, 4)
        self.save_note = _Note()
        g.addWidget(self.save_note, 5, 0, 1, 4)
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

    def render_ta(self):
        t, ta = self.t, self.t.ta
        on = ta["enabled"]
        self.auto_on.blockSignals(True)
        self.auto_on.setChecked(on)
        self.auto_on.blockSignals(False)
        self.auto_state.setText("off" if not on else "fitted to this picture" if t.has_image else "waiting for a picture")
        esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
        notes = [(k, x) for k, x in ta["notes"].items() if x]
        if on:
            items = "".join(f"<li><i>yours</i> Automatic: {esc(x)} Your value is used.</li>" if t.own(k) else f"<li>{esc(x)}</li>"
                            for k, x in notes) or "<li>Open a picture to fit the settings to.</li>"
        else:
            items = "<li>Automatic settings are off.</li>"
        self.auto_notes.setText(f"<ul style='margin-left: -24px'>{items}</ul>")
        tv = t.v
        eff = [("Colour tolerance", tv["tol"], "tol"), ("Points per octave", tv["ppo"], "ppo"),
               ("Save", f"{tv['fmin']}–{tv['fmax']} Hz", "fmin"), ("Dashed line", "yes" if tv["dashed"] else "no", "dashed")]
        self.auto_eff.setText("<br>".join(f"{a}: <b>{esc(str(b))}</b>" + (f" <i>{'yours' if t.own(k) else 'auto'}</i>" if on and k else "")
                                          for a, b, k in eff))
        mine = sorted(ta["manual"])
        self.auto_manual.setVisible(on and bool(mine))
        self.auto_manual.setText("Set by you (kept as they are): " + ", ".join(
            f"{tc.NAMES[k]} <a href='{k}'>↺</a>" for k in mine) + " · <a href='*'>Hand all back</a>")
        for k, b in self.tags.items():
            yours = t.own(k)
            b.setVisible(on)
            b.setEnabled(yours)
            b.setText("yours ↺" if yours else "auto")
            b.setToolTip("You set this. Click to hand it back to the automatic settings." if yours else
                         "Set by the automatic settings. Change it to use your own value.")

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
        for b in (self.add_btn, self.auto_btn, self.save_meas, self.save_tgt, self.download_btn, self.ocr_btn):
            b.setEnabled(img and (b is not self.ocr_btn or not getattr(self, "reading", False)))
        self.remove_btn.setVisible(img)
        need = "" if not img else "Type the dB values of the red lines (and check the blue Hz values) to save." \
            if not t.calib() else "Trace a curve to save it." if not anything else None
        if need or not getattr(self, "saved_note", False):  # ("Saved as …" stays until something is needed)
            self.saved_note = False
            self.save_note.setText(need or "")
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
            name.setToolTip("Curve name (the files are named with it, e.g. L and R)")
            name.installEventFilter(self)
            name.setProperty("curve", i)
            h.addWidget(name, 1)
            n = int(np.isfinite(c["ys"]).sum())
            h.addWidget(_label(f"{n} px" if n else "empty", "muted", wrap=False))
            x = QPushButton("✕")
            x.setToolTip("Delete this curve")
            theme.mark(x, quiet=True, trCompact=True)
            x.clicked.connect(lambda _=False, i=i: self.delete_curve(i))
            h.addWidget(x)
            _curve_names(pick, x, c["label"], i)

            def renamed(s, c=c, pick=pick, x=x, i=i):
                c["label"] = s.strip()
                _curve_names(pick, x, c["label"], i)
            name.textEdited.connect(renamed)
            lay.addWidget(row)
        _no_focus(self.curves_box)
        self.curves_note.setText("Saved together as one device, one file per curve (named with the labels, e.g. L and R)."
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
        self.render_ta()
        self.update_ui()

    def fit_and_show(self):
        self.t.fit_settings()
        self.show_values()
        self.render_ta()
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

    def open_file(self, path):
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, "Trace", "That isn't a picture this app can read (PNG, JPG, WebP, BMP, GIF, TIFF).")
            return
        name = os.path.splitext(os.path.basename(path))[0]
        self.load_image(img, name, os.path.splitext(path)[1].lower() in (".jpg", ".jpeg", ".jfif"))

    def load_image(self, qimg, name="Traced graph", jpeg=False):
        self.sample_open = False  # (a picture of yours: the Guide's sample, set again by the Guide, isn't on any more)
        rgb = rgb_of(qimg)
        try:
            self.t.load(rgb, name, jpeg)
        except Exception as e:  # noqa: BLE001 - a picture whose axes trip the reader: said, the tracer left empty
            import traceback
            traceback.print_exc()
            self.t.unload()
            self.stage.clear_image()
            self.file_lab.setText("")
            self.changed()
            QMessageBox.warning(self, "Trace", f"Couldn't read the axes of this picture ({e}). Please send it with "
                                "data\\app.log, so it can be fixed.")
            return
        h, w = rgb.shape[:2]
        self.file_lab.setText(f"{name} · {w}×{h}" if name != "Traced graph" else f"{w}×{h}")
        self.stage.set_image(rgb)
        self.saved_note = False
        self.status.setText(HINTS[self.tool])
        self.fill_comp()
        self.show_values()
        self.changed()
        self.read_labels()

    def remove_image(self):
        t = self.t
        if not t.has_image:
            return
        if any(map(t.has_data, t.curves)) and QMessageBox.question(
                self, "Remove image", "Remove this picture and the curves traced on it?") != QMessageBox.Yes:
            return
        t.unload()
        t.v.update(d1="", d2="", f1="", f2="", name="")
        t.typed = {"d": False, "f": False}
        t.ta.update(notes={}, dashed_found=False, last_ocr=None, last_trace=None)
        if t.ta["enabled"] and not t.own("dashed"):
            t.v["dashed"] = False
        self.reading = False
        self.stage.clear_image()
        self.file_lab.setText("")
        self.saved_note = False
        self.save_note.setText("")
        self.show_values()
        self.changed()
        self.status.setText("Picture removed: open, drop or paste another one.")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() or e.mimeData().hasImage():
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        for u in md.urls():
            if u.isLocalFile():
                self.open_file(u.toLocalFile())
                return
        if md.hasImage():
            self.load_image(QImage(md.imageData()))

    def paste(self):
        img = QApplication.clipboard().image()
        if img.isNull():
            self.say("No picture on the clipboard: copy a graph's picture first.")
            return
        self.load_image(img)

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
            b.setToolTip(bad[1] if bad else help_of(f"#tr-{key if key[0] in 'df' else 'fmin'}") + f"\nAllowed: {self.limits.text(lim)}.")
            if bad:
                return
            t.v[key] = text
        if key in ("d1", "d2", "f1", "f2"):
            t.typed[key[0]] = True
            t.fit_settings()
        else:
            t.touched(key)
        self.show_values()  # (points per octave and the range follow the axes' values; the box typed in is left be)
        self.render_ta()
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
            self.say(f"Changed to {y:g}: allowed {self.limits.text(lim)}.")

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
            QMessageBox.warning(self, "Trace", f"Couldn't find the axes again ({e}).")
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
        self.axis_note.setText(before + " Reading the axis labels…")
        t.moved = {"d": False, "f": False}
        t.label_token += 1
        self.reading = True
        self.update_ui()

        def done(res, err):
            if t.label_token != token:  # (another picture, or read again, meanwhile)
                return
            self.reading = False
            if err is not None:
                t.axis_note = before + f" (Couldn't read the labels: {err}. Type the values instead.)"
            else:
                t.use_labels(res, before)
            self.show_values()
            self.render_ta()
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

    def delete_curve(self, i):
        self.t.delete_curve(i)
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
        self.t.touched("tol")
        self.render_ta()

    def dashed_changed(self, on):
        self.t.v["dashed"] = on
        self.t.touched("dashed")
        self.render_ta()

    def ppo_changed(self, _i):
        self.t.v["ppo"] = self.ppo.currentData()
        self.t.touched("ppo")
        self.render_ta()

    # ---------------------------------------------------------------- automatic settings
    def _keep(self):
        """The automatic settings' switch into the app's settings, written half a second after the last change,
        without redrawing the other screens (as Listen's)."""
        ta, sw = self.t.ta, self.page.sw
        sw.s["trace"] = {"enabled": ta["enabled"]}
        if not hasattr(self, "_keep_timer"):
            self._keep_timer = QTimer(self, singleShot=True, interval=500, timeout=sw.save)
            QApplication.instance().aboutToQuit.connect(sw.save)
        self._keep_timer.start()

    def auto_switched(self, on):
        self.t.ta["enabled"] = on
        self._keep()
        self.fit_and_show() if on else self.render_ta()

    def hand_back(self, k):
        self.t.hand_back(k)
        self.fit_and_show()

    # ---------------------------------------------------------------- save
    def fill_comp(self):
        """The targets a graph may have been drawn relative to."""
        was = self.comp.currentData()
        self.comp.clear()
        self.comp.addItem("the actual response (not compensated)", "")
        for n in (getattr(self.page, "inputs", None) or {}).get("targets", []):
            self.comp.addItem(f"relative to {os.path.splitext(n)[0]}", n)
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
            f" (graph relative to {os.path.splitext(name)[0]}, added back)"

    def outputs(self, only_current=False):
        comp, note = self.compensation()
        return self.t.outputs(only_current, comp, note)

    def save(self, kind):
        """Into the app: a measurement (the traced curves as one device, made the one in use) or a target."""
        page = self.page
        try:
            outs = self.outputs(kind == "target")
        except (ValueError, ArithmeticError) as e:
            QMessageBox.warning(self, "Trace", str(e))
            return
        # (all channels in one go: one number for the set when names are taken, so they stay one device)
        r = page.svc.call("/api/files/add", {"kind": kind, "files": [{"name": o["file"], "content": o["text"]}
                                                                     for o in outs], "settings": page.S})
        if r.get("error"):
            QMessageBox.warning(self, "Not added", r["error"])
            return
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
        self.save_note.setText(f"Saved as {what} “{shown}”. Close this window to see it on the graph, or trace more."
                               + (" (A target is one curve, so only the selected one was saved.)"
                                  if kind == "target" and sum(map(self.t.has_data, self.t.curves)) > 1 else ""))
        gaps = self.t.gaps_text(outs)
        if gaps:
            QMessageBox.information(self, "Trace", gaps)

    def download(self):
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
            if there and QMessageBox.question(self, "Replace?", "Already in that folder:\n\n" + "\n".join(there)
                                              + "\n\nReplace them?") != QMessageBox.Yes:
                return
        for path, o in zip(paths, outs):
            try:
                textfile.write_atomic(path, o["text"])
            except OSError as e:  # (a folder you can't write to, a file another program holds: said, not silent)
                QMessageBox.warning(self, "Trace", f"Couldn't save {os.path.basename(path)}: {e}")
                return
        if paths:
            self.page.status(f"Saved {', '.join(os.path.basename(p) for p in paths)}.", 6000)
            gaps = self.t.gaps_text(outs)
            if gaps:
                QMessageBox.information(self, "Trace", gaps)

    # ---------------------------------------------------------------- keys
    def keyPressEvent(self, e):
        st = self.stage
        typing = isinstance(QApplication.focusWidget(), (QLineEdit, QComboBox))
        key, mods = e.key(), e.modifiers()
        if key == Qt.Key_Space and not typing:
            if not e.isAutoRepeat():
                st.space = True
            return
        if typing:
            return super().keyPressEvent(e)
        ctrl = bool(mods & Qt.ControlModifier)
        if ctrl and key == Qt.Key_Z:
            self.redo() if mods & Qt.ShiftModifier else self.undo()
            return
        if ctrl and key == Qt.Key_Y:
            self.redo()
            return
        if ctrl and key == Qt.Key_V:
            self.paste()
            return
        if ctrl or mods & Qt.AltModifier:
            return super().keyPressEvent(e)
        if st.sel_line and key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            d = (10 if mods & Qt.ShiftModifier else 1) / max(1, st.view["s"]) * (-1 if key in (Qt.Key_Up, Qt.Key_Left) else 1)
            if (st.sel_line[0] == "y") == (key in (Qt.Key_Up, Qt.Key_Down)):
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
            acts[key]()
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self.stage.space = False
        super().keyReleaseEvent(e)
