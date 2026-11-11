"""A drawn look-alike of a graph from a CrinGraph website (graph.hangout.audio and the like), for the tests of the
tracer's automatic read (ui\\trace_auto.py). No picture of a real website is kept in the repository: this draws one
in memory. Cream background, a faint grid with the ticks 2, 3, 4, 5, 6, 8, 10, 15 in each decade, the labels inside
the plot (dB) and below it (Hz) in Consolas (zeros with a line through them), a logo-like shape and a line of large
gray text in the plot, small gray text at the top right, two near curves of one color (the left and right channel),
their names in the curve's color, and, when asked, a gray target line and a page around the graph. The true curves
come back with the picture.

website_graph(plot_w=1000, target=None, page=False, decade=0, labels=True, one_curve=False, offset_db=0.0)
    -> (QImage, truth)
truth: "plot" {x0, x1, y0, y1} (the grid's edges), "avg" f(Hz) -> dB (the true average of the channels), "chans"
[f, f], "tgt" f or None, "x" f(Hz) -> column, "y" f(dB) -> row, "hz" f(column) -> Hz, "db" f(row) -> dB, "words"
[{text, x0, y0, x1, y1}] (the true labels with their boxes), "scale". All positions are in pixel index coordinates
(the center of pixel i is at i: the painter's coordinate minus 0.5), as the tracer's.
as_rgb(qimage, jpeg=None) -> H x W x 3 uint8 (through a JPEG of that quality in memory when jpeg is a number)
truth_reader(truth) -> a stand-in for trace_auto.read_strip: the true words whose middle is in the part asked for
"""
import math

import numpy as np
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath, QPen

TICKS = [m * d for d in (10, 100, 1000) for m in (2, 3, 4, 5, 6, 8, 10, 15)] + [20000]
CREAM = "#fff7ea"
L2 = math.log2


def _iem(f):
    return (61 + 2.2 / (1 + (f / 180) ** 2) - 2.5 * math.exp(-(L2(f / 900) ** 2) / 0.8)
            + 11 * math.exp(-(L2(f / 2600) ** 2) / 0.45) + 7 * math.exp(-(L2(f / 5800) ** 2) / 0.07)
            + 6 * math.exp(-(L2(f / 7600) ** 2) / 0.03) - 9 * math.exp(-(L2(f / 10500) ** 2) / 0.05)
            + 3 * math.exp(-(L2(f / 16500) ** 2) / 0.02) - 9 * max(0.0, L2(f / 8000)) ** 1.2)


def _left(f):
    return _iem(f) + 0.25 + 0.5 * math.exp(-(L2(f / 9000) ** 2) / 0.5) * math.sin(L2(f) * 9)


def _right(f):
    return _iem(f) - 0.25 - 1.6 * math.exp(-(L2(f / 12000) ** 2) / 0.3) + 0.4 * math.sin(L2(f) * 2.1)


def _target(f):
    return 58.5 + 4.5 / (1 + (f / 110) ** 2) + 8.5 * math.exp(-(L2(f / 3000) ** 2) / 1.2) - 4 * max(0.0, L2(f / 9000))


def label_of(f, first=False, last=False):
    t = f"{f / 1000:g}k" if f >= 1000 else f"{f:g}"
    return t + "Hz" if first or last else t


def website_graph(plot_w=1000, target=None, page=False, decade=0, labels=True, one_curve=False, offset_db=0.0):
    """plot_w: the grid's width in pixels. target: None, "solid" or "dashed". page: a page around the graph.
    decade: the labels' power of ten against 20 Hz .. 20 kHz (0: correct labels; 1: every label ten times too high).
    labels False: no labels at all. one_curve: only the left channel. offset_db: added to the right channel (two
    channels far apart)."""
    s = plot_w / 770.0  # (a CrinGraph graph is 800 x 346 units: the plot from 15 to 785, the grid lines from 10 to 327)
    gw, gh = round(800 * s), round(346 * s)
    ox, oy = (round(275 * s), round(105 * s)) if page else (0, 0)
    Wd, Hd = (round(1090 * s), round(600 * s)) if page else (gw, gh)
    img = QImage(Wd, Hd, QImage.Format_RGB888)
    img.fill(QColor(CREAM))
    g = QPainter(img)
    g.setRenderHint(QPainter.Antialiasing)
    g.setRenderHint(QPainter.TextAntialiasing)
    words = []

    def font(px, bold=False, family="Consolas"):
        f = QFont(family)
        f.setPixelSize(max(5, round(px * s)))
        f.setBold(bold)
        return f

    def text(x, y, t, col, f, align="left", keep=False):
        """Text with its baseline at y; x is its left, middle or right. Keeps its box (index coordinates)."""
        g.setFont(f)
        g.setPen(QColor(col))
        m = QFontMetricsF(f)
        w = m.horizontalAdvance(t)
        x = x - (w / 2 if align == "mid" else w if align == "right" else 0)
        g.drawText(QPointF(x, y), t)
        if keep:
            words.append({"text": t, "x0": x - 0.5, "x1": x + w - 0.5, "y0": y - m.capHeight() - 0.5, "y1": y - 0.5})

    if page:  # a page around the graph: a bar at the top, a list at the left, buttons, text under the graph
        g.fillRect(QRectF(0, 0, Wd, 50 * s), QColor("#7a4a26"))
        text(70 * s, 32 * s, "Sample.Audio", "#ffffff", font(17, True, "Arial"))
        g.setPen(QPen(QColor("#b9966f"), max(1.0, s)))
        g.drawLine(QPointF(262 * s, 50 * s), QPointF(262 * s, Hd))
        for i in range(12):
            y = (150 + i * 36) * s
            text(70 * s, y, f"Sample IEM {i + 1}", "#5b3a1e", font(12, False, "Arial"))
            text(240 * s, y, "+", "#5b3a1e", font(16, False, "Arial"))
        g.fillRect(QRectF(60 * s, 96 * s, 195 * s, 30 * s), QColor("#8a5a2e"))
        for i, t in enumerate(("Copy URL", "Screenshot", "40dB", "dB 60")):
            r = QRectF((285 + i * 105) * s, 62 * s, 95 * s, 30 * s)
            g.setPen(QPen(QColor("#b9966f"), max(1.0, s)))
            g.setBrush(Qt.NoBrush)
            g.drawRoundedRect(r, 5 * s, 5 * s)
            text(r.center().x(), r.center().y() + 4 * s, t, "#5b3a1e", font(11, False, "Arial"), "mid")
        for i, t in enumerate(("Sub bass", "Mid bass", "Lower midrange", "Upper midrange", "Treble", "Air")):
            text((320 + i * 125) * s, (oy / s + 346 + 40) * s, t, "#3b2a1a", font(11, False, "Arial"))
        g.setPen(QPen(QColor("#b9966f"), max(1.0, s)))
        g.drawLine(QPointF(275 * s, (oy / s + 346 + 62) * s), QPointF(Wd, (oy / s + 346 + 62) * s))

    X = lambda f: ox + (15 + 770 * math.log10(f / 20) / 3) * s
    Y = lambda v: oy + (20.9 + (80 - v) / 40 * 302.1) * s
    top, bot = oy + 10 * s, oy + 327 * s
    g.setClipRect(QRectF(ox, oy, gw, gh))

    # the grid (thin lines, the decade's 2 the thickest), drawn with antialiasing: faint
    def vwidth(f):
        m = f / 10 ** math.floor(math.log10(f))
        return 1.5 if abs(m - 2) < 1e-6 else 0.9 if m in (1, 5) else 0.4
    for f in TICKS:
        g.setPen(QPen(QColor("#9a8f7c"), vwidth(f) * s))
        g.drawLine(QPointF(X(f), top), QPointF(X(f), bot))
    for v in range(40, 81, 5):
        g.setPen(QPen(QColor("#cdbfa6"), 1.6 * s))
        g.drawLine(QPointF(X(20), Y(v)), QPointF(X(20000), Y(v)))

    # a logo-like shape and a line of large gray text (the watermark), then small gray text at the top right
    g.setPen(QPen(QColor("#d9c3a3"), 3 * s))
    g.setBrush(Qt.NoBrush)
    c = QPointF(ox + 120 * s, oy + 262 * s)
    g.drawEllipse(c, 46 * s, 46 * s)
    g.drawEllipse(c, 30 * s, 34 * s)
    for a in range(0, 360, 40):
        r = math.radians(a)
        g.drawLine(c + QPointF(math.cos(r), math.sin(r)) * 12 * s, c + QPointF(math.cos(r), math.sin(r)) * 26 * s)
    text(ox + 172 * s, oy + 300 * s, "graph.sample.audio", "#aaa091", font(28, True))
    for i, t in enumerate(("Sample data made for a test:", '"000" Coupler', "ABC 12345-6")):
        text(ox + 762 * s, oy + (27 + i * 14) * s, t, "#9c958a", font(12), "right")
    g.setPen(Qt.NoPen)
    g.setBrush(QColor("#b98f62"))
    g.drawRoundedRect(QRectF(ox + 4 * s, Y(60) - 12 * s, 10 * s, 24 * s), 4 * s, 4 * s)  # (the handle on the axis)

    # the labels: dB inside the plot at the left, just above its line; Hz under the plot, at its tick
    if labels:
        k = 10 ** decade
        f9 = font(9.5)
        for v in range(40, 81, 5):
            text(X(20) + 3 * s, Y(v) - 2 * s, str(v), "#3a332b", f9, keep=True)
        faint = {30, 40, 60, 80, 150}
        for i, f in enumerate(TICKS):
            t = label_of(f * k, i == 0, i == len(TICKS) - 1)
            al = "left" if i == 0 else "right" if i == len(TICKS) - 1 else "mid"
            xx = X(f) + (-8 * s if i == 0 else 9 * s if al == "right" else 0)
            text(xx, oy + 340 * s, t, "#a59d90" if f in faint else "#3a332b", f9, al, keep=True)

    # the curves: the target under the two channels; both channels in near blues, their ends faded
    fq = [20 * 1000 ** (i / 1199) for i in range(1200)]

    def path(fn, col, w, dash=None, fade=True):
        pen = QPen(QColor(col), w * s)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.FlatCap)
        if dash:
            pen.setDashPattern([d / w for d in dash])
        if fade:  # (the page fades about 7 units at both ends of a curve)
            gr = QLinearGradient(QPointF(X(20), 0), QPointF(X(20000), 0))
            c0 = QColor(col)
            c0.setAlpha(0)
            e = 7 / 770
            gr.setColorAt(0, c0)
            gr.setColorAt(e, QColor(col))
            gr.setColorAt(1 - e, QColor(col))
            gr.setColorAt(1, c0)
            pen.setBrush(QBrush(gr))
        g.setPen(pen)
        g.setBrush(Qt.NoBrush)
        pp = QPainterPath(QPointF(X(fq[0]), Y(fn(fq[0]))))
        for f in fq[1:]:
            pp.lineTo(QPointF(X(f), Y(fn(f))))
        g.drawPath(pp)
    if target:
        path(_target, "#9e9ea3", 2.3, [6, 3] if target == "dashed" else None)
    right = (lambda f: _right(f) + offset_db) if offset_db else _right
    chans = [_left] if one_curve else [_left, right]
    for fn, col in zip(chans, ("#1a48a0", "#0d357d")):
        path(fn, col, 2.3)
    fb = font(9.5, True)
    text(ox + 500 * s, oy + 285 * s, "Sample IEM (L)", "#1a48a0", fb)
    if not one_curve:
        text(ox + 500 * s, oy + 300 * s, "Sample IEM (R)", "#0d357d", fb)
    if target:
        text(ox + 500 * s, oy + 270 * s, "Sample Target", "#9e9ea3", fb)
    g.end()
    avg = _left if one_curve else (lambda f: (_left(f) + right(f)) / 2)
    xi = lambda f: X(f) - 0.5
    yi = lambda v: Y(v) - 0.5
    return img, {"plot": {"x0": xi(20), "x1": xi(20000), "y0": top - 0.5, "y1": bot - 0.5}, "avg": avg,
                 "chans": chans, "tgt": _target if target else None, "x": xi, "y": yi,
                 "hz": lambda x: 20 * 10 ** ((x - xi(20)) / (xi(20000) - xi(20)) * 3),
                 "db": lambda y: 80 - (y - yi(80)) / (yi(40) - yi(80)) * 40, "words": words, "scale": s}


def as_rgb(img, jpeg=None):
    """The picture as an H x W x 3 uint8 array; through a JPEG of that quality (in memory, no file) when jpeg is a
    number."""
    if jpeg:
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "JPG", int(jpeg))
        buf.close()
        del buf
        img = QImage.fromData(ba, "JPG")
    img = img.convertToFormat(QImage.Format_RGB888)
    w, h = img.width(), img.height()
    a = np.frombuffer(img.constBits(), np.uint8, count=img.bytesPerLine() * h).reshape(h, img.bytesPerLine())
    return a[:, :w * 3].reshape(h, w, 3).copy()


def truth_reader(truth):
    """A stand-in for trace_auto.read_strip (the same arguments): the true words whose middle is in the part asked
    for, so that a test does not depend on the text reader of the PC."""
    def read_strip(rgb, ocr_words, x0, y0, x1, y1, k, gray):
        return [dict(w) for w in truth["words"]
                if x0 <= (w["x0"] + w["x1"]) / 2 <= x1 and y0 <= (w["y0"] + w["y1"]) / 2 <= y1]
    return read_strip
