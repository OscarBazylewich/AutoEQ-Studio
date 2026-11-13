"""A drawn look-alike of a graph from a CrinGraph website (graph.hangout.audio and the like), for the tests of the
tracer's automatic read (ui\\trace_auto.py). No picture of a real website is kept in the repository: this draws one
in memory. Cream background (or another color: background), a faint grid with the ticks 2, 3, 4, 5, 6, 8, 10, 15 in
each decade, the labels inside the plot (dB) and below it (Hz) in Consolas (zeros with a line through them), a
logo-like shape and a line of large gray text in the plot, small gray text at the top right, two near curves of one
color (the left and right channel), their names in the curve's color, and, when asked, a gray target line and a page
around the graph. The true curves come back with the picture.

website_graph(plot_w=1000, target=None, page=False, decade=0, labels=True, one_curve=False, offset_db=0.0,
              colours=("#1a48a0", "#0d357d"), db_range=(40, 80), db_step=5, legend_xy=(500, 285), extra=(),
              target_fn=None, db_words=None, target_dash=None, chan_fns=None, clip_db=False, top_logo=False,
              curves=True, target_colour="#9e9ea3", target_width=2.3, target_look=False, bands=None,
              target_gaps=(), grey_rows=None, background=CREAM) -> (QImage, truth)
target_graph(plot_w=1200, **kw) -> (QImage, truth): the look of a website's graph of a target alone (a dB axis of
-20 to 20 dB, a dashed gray line, no measurement)
STEEP_END: (left, right) channels with the forms of a real screen copy (steep peaks, out of the grid near 20 kHz)
truth: "plot" {x0, x1, y0, y1} (the grid's edges), "avg" f(Hz) -> dB (the true average of the channels), "chans"
[f, f], "tgt" f or None, "x" f(Hz) -> column, "y" f(dB) -> row, "hz" f(column) -> Hz, "db" f(row) -> dB, "words"
[{text, x0, y0, x1, y1}] (the true labels with their boxes), "db_rows" (the rows of the dB grid lines, top first),
"scale". All positions are in pixel index coordinates (the center of pixel i is at i: the painter's coordinate minus
0.5), as the tracer's. Qt must have an application (QGuiApplication.instance(): in a test, the qapp fixture) and find
Consolas (QT_QPA_FONTDIR with the offscreen platform): else RuntimeError.
as_rgb(qimage, jpeg=None) -> H x W x 3 uint8 (through a JPEG of that quality in memory when jpeg is a number)
truth_reader(truth) -> a stand-in for trace_auto.read_strip: the true words whose middle is in the part asked for
"""
import math

import numpy as np
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontInfo, QFontMetricsF, QGuiApplication, QImage, QLinearGradient,
                           QPainter, QPainterPath, QPen)

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


def _smooth(points):
    """A smooth curve f(Hz) -> dB through [(Hz, dB)] (monotone cubic on log10 of the frequency: no overshoot between
    the points, so each peak and dip is where its point is). Past the last point: the slope of the last part. (SciPy
    is imported at the first call only.)"""
    made = []

    def fn(f):
        if not made:
            from scipy.interpolate import PchipInterpolator
            made.append(PchipInterpolator(np.log10([p[0] for p in points]), [p[1] for p in points], extrapolate=True))
        return float(made[0](math.log10(f)))
    return fn


# A made-up IEM with the forms of a real screen copy of the website (2026-11-11): the two channels 1 to 2 dB apart
# below 8 kHz; from 8 to 16 kHz steep, narrow peaks and dips, the channels 5 to 13 dB apart for short parts and across
# each other; the right channel (the lighter one) falls out of the grid at the bottom (below 40 dB) at about 18.7 kHz,
# the left one at about 19.8 kHz. For website_graph(chan_fns=STEEP_END, clip_db=True).
_STEEP_L = [(20, 66.0), (40, 64.6), (100, 60.3), (150, 58.6), (190, 60.3), (300, 58.0), (400, 56.8), (500, 58.4),
            (700, 59.6), (1000, 61.4), (2000, 68.0), (2900, 70.9), (4000, 69.0), (5000, 68.6), (6500, 68.1),
            (7600, 64.0), (9000, 56.5), (10600, 51.8), (12100, 64.0), (12800, 61.0), (15000, 51.5), (16700, 58.0),
            (18000, 53.0), (19000, 46.0), (19800, 40.0), (20000, 38.5)]
_STEEP_R = [(20, 65.8), (40, 64.4), (100, 60.0), (150, 58.2), (190, 59.2), (300, 56.6), (350, 55.8), (400, 57.0),
            (500, 58.3), (700, 59.0), (1000, 60.9), (2000, 68.0), (3000, 70.2), (3500, 70.4), (4400, 71.6),
            (5000, 68.6), (6000, 65.2), (6600, 65.0), (7200, 65.4), (7800, 63.5), (9000, 57.5), (10500, 55.3),
            (11700, 65.0), (12900, 62.5), (14000, 65.3), (16600, 46.0), (18000, 50.5), (18700, 38.0), (20000, 20.0)]
STEEP_END = (_smooth(_STEEP_L), _smooth(_STEEP_R))


def label_of(f, first=False, last=False):
    t = f"{f / 1000:g}k" if f >= 1000 else f"{f:g}"
    return t + "Hz" if first or last else t


def website_graph(plot_w=1000, target=None, page=False, decade=0, labels=True, one_curve=False, offset_db=0.0,
                  colours=("#1a48a0", "#0d357d"), db_range=(40, 80), db_step=5, legend_xy=(500, 285), extra=(),
                  target_fn=None, db_words=None, target_dash=None, chan_fns=None, clip_db=False, top_logo=False,
                  curves=True, target_colour="#9e9ea3", target_width=2.3, target_look=False, bands=None,
                  target_gaps=(), grey_rows=None, background=CREAM):
    """plot_w: the grid's width in pixels. target: None, "solid" or "dashed". page: a page around the graph.
    decade: the labels' power of ten against 20 Hz .. 20 kHz (0: correct labels; 1: every label ten times too high).
    labels False: no labels at all. one_curve: only the left channel. offset_db: added to the right channel (two
    channels far apart). colours: the left and right channel's colors (the legend's too). db_range (bottom, top) and
    db_step: the dB axis (the span a multiple of the step; a curve outside it is drawn past the grid's last line).
    legend_xy: the place of the legend's first line, in the graph's units (the left channel's name; the right one 15
    units lower). extra: [(f(Hz) -> dB, color)], more measurements drawn after the channels. target_fn: the target
    line's curve in place of the default one. db_words: {true dB value: text} in place of the dB labels' own text
    in truth["words"] (the picture does not change: a stand-in for a text reader that reads wrongly; "": the label
    is not in truth["words"], not read). target_dash: the dashed target's dash and gap lengths in the graph's units
    (None: (6, 3)). chan_fns: (left, right) f(Hz) -> dB in place of the default channels (offset_db is added to the
    right one; STEEP_END: the forms of a real screen copy). clip_db: the curves are not drawn out of the dB axis (above
    its top grid line or below its bottom one), as on the website; False: they go on to the edge of the graph.
    top_logo: a pale blue logo at the top right (as a rig maker's logo), and the small gray text left of it.
    curves False: no channels and no names of the channels (a graph with only the target line: truth "avg" is None,
    "chans" []). target_colour, target_width: the target line's color (also of its name) and its width in the graph's
    units. target_look: the look of a website's graph of a target (target_graph): the dB grid lines as wide, soft
    bands, the drawing in gray with a pale orange part, the watermark in the target line's gray, and the target's
    name with its settings in a bold gray-green at the bottom right. bands: with target_look, [(width in the
    graph's units, color)] of each dB band, drawn in sequence (None: the soft bands of a real picture). target_gaps:
    [(Hz, Hz)] parts with no target line (not drawn there). grey_rows: (color, width in the graph's units[, over]) of
    a line drawn on each dB grid line over the grid (a website with dB grid lines in the gray of a target), and with
    over True, also over the curves; or None. background: the color of the page under the graph (CREAM, the
    website's; for example "#ffffff", a white page, or a neutral gray)."""
    if QGuiApplication.instance() is None:  # (with no application, Qt's fonts stop the process with no error)
        raise RuntimeError("website_graph draws with Qt: make a QGuiApplication first (in a test: the qapp fixture).")
    s = plot_w / 770.0  # (a CrinGraph graph is 800 x 346 units: the plot from 15 to 785, the grid lines from 10 to 327)
    gw, gh = round(800 * s), round(346 * s)
    ox, oy = (round(275 * s), round(105 * s)) if page else (0, 0)
    Wd, Hd = (round(1090 * s), round(600 * s)) if page else (gw, gh)
    img = QImage(Wd, Hd, QImage.Format_RGB888)
    img.fill(QColor(background))
    g = QPainter(img)
    g.setRenderHint(QPainter.Antialiasing)
    g.setRenderHint(QPainter.TextAntialiasing)
    words = []
    vb, vt = db_range

    def font(px, bold=False, family="Consolas"):
        f = QFont(family)
        f.setPixelSize(max(5, round(px * s)))
        f.setBold(bold)
        if QFontInfo(f).family() != family:
            g.end()
            raise RuntimeError(f"Qt did not find the font {family}. Set QT_QPA_FONTDIR to C:\\Windows\\Fonts (the tests "
                               "do this in helpers\\session.py).")
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
    Y = lambda v: oy + (20.9 + (vt - v) / (vt - vb) * 302.1) * s
    top, bot = oy + 10 * s, oy + 327 * s
    g.setClipRect(QRectF(ox, oy, gw, gh))

    # the grid (thin lines, the decade's 2 the thickest), drawn with antialiasing: faint
    def vwidth(f):
        m = f / 10 ** math.floor(math.log10(f))
        return 1.5 if abs(m - 2) < 1e-6 else 0.9 if m in (1, 5) else 0.4

    def vlines():  # (target_look: the brown of a real picture, #b6987c)
        for f in TICKS:
            g.setPen(QPen(QColor("#b6987c" if target_look else "#9a8f7c"), vwidth(f) * s))
            g.drawLine(QPointF(X(f), top), QPointF(X(f), bot))
    if not target_look:
        vlines()
    db_values = [vb + i * db_step for i in range(int(round((vt - vb) / db_step)) + 1)]
    for v in db_values:
        if target_look:  # (a wide, soft band of light brown: 13 px with its middle #ede2d0 on a real picture)
            for wd, col in bands or ((4.3, "#faf0e2"), (3.0, "#f3e9da"), (1.6, "#ede2d0")):
                g.setPen(QPen(QColor(col), wd * s))
                g.drawLine(QPointF(X(20), Y(v)), QPointF(X(20000), Y(v)))
            continue
        g.setPen(QPen(QColor("#cdbfa6"), 1.6 * s))
        g.drawLine(QPointF(X(20), Y(v)), QPointF(X(20000), Y(v)))
    if target_look:  # (the frequency grid lines over the bands, as on the real picture)
        vlines()

    rows_over = bool(grey_rows) and len(grey_rows) > 2 and grey_rows[2]

    def grey_lines():
        g.setPen(QPen(QColor(grey_rows[0]), grey_rows[1] * s))
        for v in db_values:
            g.drawLine(QPointF(X(20), Y(v)), QPointF(X(20000), Y(v)))
    if grey_rows and not rows_over:
        grey_lines()

    # a logo-like shape and a line of large gray text (the watermark), then small gray text at the top right
    g.setPen(QPen(QColor("#b9b4ab" if target_look else "#d9c3a3"), 3 * s))
    g.setBrush(Qt.NoBrush)
    c = QPointF(ox + 120 * s, oy + 262 * s)
    g.drawEllipse(c, 46 * s, 46 * s)
    g.drawEllipse(c, 30 * s, 34 * s)
    for a in range(0, 360, 40):
        r = math.radians(a)
        g.drawLine(c + QPointF(math.cos(r), math.sin(r)) * 12 * s, c + QPointF(math.cos(r), math.sin(r)) * 26 * s)
    if target_look:  # (a pale orange part of the drawing, and the watermark in the gray of the target line)
        g.setPen(Qt.NoPen)
        g.setBrush(QColor("#fcd9b2"))
        g.drawEllipse(c + QPointF(-34 * s, 0), 4 * s, 9 * s)
        g.drawEllipse(c + QPointF(34 * s, 0), 4 * s, 9 * s)
        text(ox + 170 * s, oy + 312 * s, "graph.sample.audio", target_colour, font(32, True, "Arial"))
    else:
        text(ox + 172 * s, oy + 300 * s, "graph.sample.audio", "#aaa091", font(28, True))
    for i, t in enumerate(("Sample data made for a test:", '"000" Coupler', "ABC 12345-6")):
        text(ox + (690 if top_logo else 762) * s, oy + (27 + i * 14) * s, t, "#9c958a", font(12), "right")
    if top_logo:  # (a circle with lines across it and two letters, pale blue, and a name in gray under it)
        c = QPointF(ox + 738 * s, oy + 38 * s)
        g.setPen(QPen(QColor("#7aa7d4"), 1.2 * s))
        g.setBrush(Qt.NoBrush)
        g.drawEllipse(c, 16 * s, 16 * s)
        g.drawEllipse(c, 7 * s, 16 * s)
        for k in (-10, -5, 0, 5, 10):
            g.drawLine(c + QPointF(-15 * s, k * s), c + QPointF(15 * s, k * s))
        g.setPen(QPen(QColor("#7aa7d4"), 2.2 * s))
        g.drawLine(c + QPointF(-30 * s, -3 * s), c + QPointF(30 * s, -3 * s))
        text(ox + 712 * s, oy + 35 * s, "S", "#7aa7d4", font(9, True, "Arial"))
        text(ox + 758 * s, oy + 35 * s, "A", "#7aa7d4", font(9, True, "Arial"))
        text(c.x(), oy + 68 * s, "Sample & Co", "#a19c95", font(9, True, "Arial"), "mid")
    g.setPen(Qt.NoPen)
    g.setBrush(QColor("#b98f62"))
    g.drawRoundedRect(QRectF(ox + 4 * s, Y((vb + vt) / 2) - 12 * s, 10 * s, 24 * s), 4 * s, 4 * s)  # (the axis' handle)

    # the labels: dB inside the plot at the left, just above its line; Hz under the plot, at its tick
    if labels:
        k = 10 ** decade
        f9 = font(9.5)
        for v in db_values:
            text(X(20) + 3 * s, Y(v) - 2 * s, f"{v:g}", "#3a332b", f9, keep=True)
            if db_words and v in db_words:
                if db_words[v]:
                    words[-1]["text"] = db_words[v]
                else:
                    words.pop()  # ("": the label is not read)
        faint = {30, 40, 60, 80, 150}
        for i, f in enumerate(TICKS):
            t = label_of(f * k, i == 0, i == len(TICKS) - 1)
            al = "left" if i == 0 else "right" if i == len(TICKS) - 1 else "mid"
            xx = X(f) + (-8 * s if i == 0 else 9 * s if al == "right" else 0)
            text(xx, oy + 340 * s, t, "#a59d90" if f in faint else "#3a332b", f9, al, keep=True)

    # the curves: the target under the two channels; both channels in near blues, their ends faded
    fq = [20 * 1000 ** (i / 1199) for i in range(1200)]

    def path(fn, col, w, dash=None, fade=True, gaps=()):
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
        up = False  # (in a part of gaps: no line)
        for f in fq[1:]:
            if any(a <= f <= b for a, b in gaps):
                up = True
            elif up:
                pp.moveTo(QPointF(X(f), Y(fn(f))))
                up = False
            else:
                pp.lineTo(QPointF(X(f), Y(fn(f))))
        g.drawPath(pp)
    tfn = target_fn or _target
    if clip_db:  # (the curves only: from the top dB grid line to the bottom one)
        g.setClipRect(QRectF(ox, Y(vt), gw, Y(vb) - Y(vt)))
    if target:
        path(tfn, target_colour, target_width, list(target_dash or (6, 3)) if target == "dashed" else None,
             gaps=target_gaps)
    left, right0 = chan_fns or (_left, _right)
    right = (lambda f: right0(f) + offset_db) if offset_db else right0
    chans = [] if not curves else [left] if one_curve else [left, right]
    for fn, col in zip(chans, colours):
        path(fn, col, 2.3)
    for fn, col in extra:
        path(fn, col, 2.3)
    if rows_over:
        grey_lines()
    if clip_db:
        g.setClipRect(QRectF(ox, oy, gw, gh))
    fb = font(9.5, True)
    lx, ly = legend_xy
    if curves:
        text(ox + lx * s, oy + ly * s, "Sample IEM (L)", colours[0], fb)
    if curves and not one_curve:
        text(ox + lx * s, oy + (ly + 15) * s, "Sample IEM (R)", colours[1], fb)
    if target and target_look:  # (the target's name and its settings, bold, gray-green, at the bottom right)
        text(ox + 500 * s, oy + 314 * s, "Sample Target (Tilt: -1dB/Oct, Bass: 6dB)", "#a3a89c",
             font(10, True, "Arial"))
    elif target:
        text(ox + 500 * s, oy + 270 * s, "Sample Target", target_colour, fb)
    g.end()
    avg = None if not curves else left if one_curve else (lambda f: (left(f) + right(f)) / 2)
    xi = lambda f: X(f) - 0.5
    yi = lambda v: Y(v) - 0.5
    return img, {"plot": {"x0": xi(20), "x1": xi(20000), "y0": top - 0.5, "y1": bot - 0.5}, "avg": avg,
                 "chans": chans, "tgt": tfn if target else None, "x": xi, "y": yi,
                 "hz": lambda x: 20 * 10 ** ((x - xi(20)) / (xi(20000) - xi(20)) * 3),
                 "db": lambda y: vt - (y - yi(vt)) / (yi(vb) - yi(vt)) * (vt - vb), "words": words, "scale": s,
                 "db_rows": [yi(v) for v in db_values[::-1]]}


def _relative_target(f):
    """A made-up target around 0 dB, as a website shows a target alone: a bass shelf of about 10 dB that ends at
    about 300 Hz, then a small tilt down (about -1.3 dB at 20 kHz)."""
    return 10.0 / (1 + (f / 120) ** 2.2) + 0.3 - 0.25 * max(0.0, math.log2(f / 1000))


def target_graph(plot_w=1200, **kw):
    """website_graph with the look of a website's graph of a target alone (measured on a real picture of
    2026-11-12, kept only as scratch data): a dB axis of -20 to 20 dB (labels 20 to -20), no measurement, a dashed
    gray target line (#9ca29a, 2.3 units wide: 7 px at a grid of 2310 px; dashes of 6 and gaps of 3 units), the
    soft dB bands, the gray watermark in the line's gray, the pale blue logo and the gray text at the top right, and
    the gray-green name of the target. kw: more website_graph options (they win)."""
    opts = dict(target="dashed", curves=False, db_range=(-20, 20), db_step=5, target_fn=_relative_target,
                target_colour="#9ca29a", target_look=True, top_logo=True)
    opts.update(kw)
    return website_graph(plot_w=plot_w, **opts)


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
    def read_strip(rgb, ocr_words, x0, y0, x1, y1, k, gray, copies=1):
        return [dict(w, copy=i) if copies > 1 else dict(w) for i in range(copies) for w in truth["words"]
                if x0 <= (w["x0"] + w["x1"]) / 2 <= x1 and y0 <= (w["y0"] + w["y1"]) / 2 <= y1]
    return read_strip
