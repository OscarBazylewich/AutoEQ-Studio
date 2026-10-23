"""The tracer's workings, without its window (AutoEQ Local's trace.js, natively; the window is ui/trace_window.py):
a picture of a frequency-response graph becomes a curve file.

1. The picture's gridlines are found and the frequencies of the vertical ones worked out from the spacing of a log
   axis (20, 30, 40 … 100, 200 …); four calibration lines (two red: dB, two blue: Hz) are placed on gridlines.
   The axis labels are read (ui/ocr.py: Windows' text reader) to fill in their values.
2. A click on a curve follows pixels of its colour column by column (skipping gridlines; dashed curves bridged); Auto
   trace finds one by itself. Draw, erase, smooth, undo and redo fix the result. Several curves (L and R) make one
   device.
3. The trace is resampled at so many points per octave and saved (a graph drawn relative to a target gets it added
   back).
Automatic settings fit the colour tolerance, points per octave and the range to save to the picture; a value you
change is yours until handed back. It always works carefully (care(): a speed-accuracy slider until 1.0.13).
The workflow follows UsyTrace (usyless.uk/trace); the code is AutoEQ Local's own.

Everything is in picture pixels: x a column, y a row. A trace is a float per column (NaN: none there).
"""
import math
import re
import time

import numpy as np

INK = 60          # how far from the background colour a pixel must be to count as drawn
FAINT = 16        # (pale gridlines that run unbroken across most of the picture still count)
MAX_PIXELS = 16e6  # bigger pictures are scaled down
GREY = 20  # a pixel whose channels differ by less than this is grey (measured on the sample graph as a JPEG of quality
# 50 and 75: 99% of the grey target's pixels under 14, 1% of the orange and green lines' under 33). A curve's colour
# picked from a JPEG may be tinted more: under GREY + 25 it's a grey curve, matched as plain grey
LABELS = ["L", "R", "L2", "R2", "L3", "R3"]
MAX_CURVES = len(LABELS)
NICE = [math.log10(v) for v in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10)]
LOG_DIGITS = np.log10(np.arange(1, 11))
NAMES = {"tol": "Colour tolerance", "ppo": "Points per octave", "fmin": "Save from", "fmax": "Save to", "dashed": "Dashed line"}


def _p3(v):
    """JavaScript's +v.toPrecision(3)."""
    return float(f"{v:.3g}")


def fmt_hz(f):
    return f"{_p3(f / 1000):g} kHz" if f >= 1000 else f"{_p3(f):g} Hz"


def fmt_db(v):
    return ("+" if v > 0 else "") + f"{v:g}"


def _js_round(v):
    return math.floor(v + 0.5)


def longest_runs(b):
    """The longest run of True in each row of a 2-D boolean array."""
    n, length = b.shape
    p = np.zeros((n, length + 2), np.int8)
    p[:, 1:-1] = b
    d = np.diff(p, axis=1)
    sr, sc = np.nonzero(d == 1)
    _er, ec = np.nonzero(d == -1)
    out = np.zeros(n, np.int64)
    if len(sr):
        np.maximum.at(out, sr, ec - sc)
    return out


# ---------------------------------------------------------------- the frequency axis
def nice_log(u, tol):
    """The nearest round gridline value (log10, within a decade), if close enough to trust."""
    k = math.floor(u)
    fr = u - k
    best, bd = None, tol
    for m in NICE:
        if abs(fr - m) <= bd:
            bd = abs(fr - m)
            best = k + m
    return best


def sequence_axis(xs):
    """Axes with gridlines at 2, 3 … 9 in each decade, even when drawn unevenly (common in makers' sheets): a decade
    line (100, 1k …) is followed by a much bigger gap than the one before it. Lines in a whole decade are counted;
    lines past the first/last decade line are counted too if that fits the neighbouring decade's length, else
    measured with it."""
    n = len(xs)
    if n < 6:
        return None
    g = [xs[i + 1] - xs[i] for i in range(n - 1)]
    dec = [i for i in range(1, n - 1) if g[i] > 2.2 * g[i - 1]]
    if not dec:
        return None
    u = [None] * n
    lengths = []
    for k, i in enumerate(dec):
        u[i] = k
    for k in range(len(dec) - 1):
        a, b = dec[k], dec[k + 1]
        c = b - a - 1
        lengths.append(xs[b] - xs[a])
        for i in range(a + 1, b):
            u[i] = k + math.log10(i - a + 1) if c == 8 else nice_log(k + (xs[i] - xs[a]) / (xs[b] - xs[a]), 0.015)
    for first in (True, False):
        d = dec[0] if first else dec[-1]
        k = 0 if first else len(dec) - 1
        idx = list(range(d - 1, -1, -1)) if first else list(range(d + 1, n))
        if not idx:
            continue
        ladj = (lengths[0] if first else lengths[-1]) if lengths else None
        ok = len(idx) <= 8  # (more lines than a decade holds: measured, not counted; 9 - r would reach 0)
        rank = [k - 1 + math.log10(9 - r) if first else k + math.log10(r + 2) for r in range(len(idx))] if ok else []
        if ok and ladj:
            span = abs(xs[idx[-1]] - xs[d])
            lr = span / abs(rank[-1] - k)
            ok = ladj * 0.7 < lr < ladj * 1.3
        for r, i in enumerate(idx):
            u[i] = rank[r] if ok else nice_log(k + (xs[i] - xs[d]) / ladj, 0.015) if ladj else None
    last = -math.inf
    for i in range(n):
        if u[i] is not None:
            if u[i] <= last:
                u[i] = None
            else:
                last = u[i]
    return u if sum(v is not None for v in u) >= 4 else None


def uniform_axis(xs):
    """Evenly drawn log axes with any gridline pattern (1-2-5 …): the decade length and offset that put the most
    lines on 1, 2 … 9 × 10^n."""
    if len(xs) < 4:
        return None
    x = np.asarray(xs, float)
    span = x[-1] - x[0]
    combos = [(ma, mb, k) for ma in range(1, 10) for mb in range(1, 11) for k in (0, 1)]
    dl = np.array([math.log10(mb / ma) + k for ma, mb, k in combos])
    lma = np.array([math.log10(ma) for ma, _mb, _k in combos])
    best = None
    for i in range(len(xs)):
        for j in range(i + 1, min(len(xs), i + 4)):
            with np.errstate(divide="ignore"):
                D = (x[j] - x[i]) / dl
            keep = (dl > 0.03) & (D >= span / 8) & (D <= span * 3)
            if not keep.any():
                continue
            Dk, phase = D[keep], x[i] - lma[keep] * D[keep]
            tol = np.maximum(1.5, Dk * 0.006)
            u = (x[None, :] - phase[:, None]) / Dk[:, None]
            fr = u - np.floor(u)
            dm = np.minimum(np.abs(fr[..., None] - LOG_DIGITS), np.abs(fr[..., None] - LOG_DIGITS + 1)).min(-1) * Dk[:, None]
            hit = dm <= tol[:, None]
            hits, err = hit.sum(1), np.where(hit, dm, 0).sum(1)
            for c in range(len(Dk)):  # (in the same order as trace.js: the first best stays)
                if best is None or hits[c] > best[0] or (hits[c] == best[0] and err[c] < best[1]):
                    best = (int(hits[c]), float(err[c]), float(Dk[c]), float(phase[c]))
    if best is None or best[0] < max(4, len(xs) * 0.7):
        return None
    _h, _e, D, phase = best
    out = []
    for xv in xs:
        u = (xv - phase) / D
        k = math.floor(u)
        m = _js_round(10 ** (u - k))
        out.append(k + math.log10(m) if m > 0 and abs(u - k - math.log10(m)) * D <= max(1.5, D * 0.006) else None)
    return out


def freq_values(xs):
    """Hz for each vertical gridline (None: unknown), choosing the power of ten that puts the axis nearest 20 Hz-20 kHz."""
    u = sequence_axis(xs) or uniform_axis(xs)
    if not u:
        return None
    known = [v for v in u if v is not None]
    e, score = 0, math.inf
    for t in range(-3, 7):
        s = abs(known[0] + t - math.log10(20)) + abs(known[-1] + t - math.log10(20000))
        if s < score:
            score, e = s, t
    return [None if v is None else _p3(10 ** (v + e)) for v in u]


# ---------------------------------------------------------------- calibration
class Piecewise:
    """Values between anchors (pixel position p, value v), interpolated in T's scale (log for Hz) segment by segment."""

    def __init__(self, a, T, Ti):
        self.a, self.T, self.Ti = a, T, Ti
        self.dir = math.copysign(1, a[-1]["u"] - a[0]["u"])

    @classmethod
    def make(cls, anchors, T, Ti):
        a = sorted(({"p": x["p"], "u": T(x["v"]), "v": x["v"]} for x in anchors), key=lambda m: m["p"])
        d = math.copysign(1, a[-1]["u"] - a[0]["u"]) if a[-1]["u"] != a[0]["u"] else 0
        for i in range(len(a) - 1):
            step = a[i + 1]["u"] - a[i]["u"]
            if (math.copysign(1, step) if step else 0) != d or a[i + 1]["p"] - a[i]["p"] < 0.5:
                return None
        return cls(a, T, Ti)

    def val(self, p):
        a, i = self.a, 0
        while i < len(a) - 2 and p > a[i + 1]["p"]:
            i += 1
        return self.Ti(a[i]["u"] + (p - a[i]["p"]) / (a[i + 1]["p"] - a[i]["p"]) * (a[i + 1]["u"] - a[i]["u"]))

    def pos(self, v):
        a, u, i = self.a, self.T(v), 0
        while i < len(a) - 2 and (u - a[i + 1]["u"]) * self.dir > 0:
            i += 1
        return a[i]["p"] + (u - a[i]["u"]) / (a[i + 1]["u"] - a[i]["u"]) * (a[i + 1]["p"] - a[i]["p"])


class Calib:
    def __init__(self, fx, dy):
        self.fx, self.dy = fx, dy
        self.ax, self.ay = fx.a, dy.a

    def f(self, p):
        return self.fx.val(p)

    def x(self, f):
        return self.fx.pos(f)

    def db(self, p):
        return self.dy.val(p)


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


# ---------------------------------------------------------------- reading the labels
def join_words(ws):
    """Pieces of one label ("-" "10") that sit side by side, joined."""
    ws = sorted(ws, key=lambda w: (w["y0"] + w["y1"], w["x0"]))
    out = []
    for w in ws:
        p, h = (out[-1] if out else None), w["y1"] - w["y0"]
        if p and abs((p["y0"] + p["y1"]) / 2 - (w["y0"] + w["y1"]) / 2) < h * 0.5 and w["x0"] - p["x1"] < h * 0.8 \
                and w["x0"] >= p["x0"]:
            p.update(text=p["text"] + w["text"], x1=max(p["x1"], w["x1"]), y0=min(p["y0"], w["y0"]), y1=max(p["y1"], w["y1"]))
        else:
            out.append(dict(w))
    return out


def db_num(s):
    s = re.sub(r"d?B$", "", re.sub("[−–—]", "-", s), flags=re.IGNORECASE)
    return float(s) if re.fullmatch(r"[+-]?\d+(\.\d+)?", s) else None


def hz_num(s):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([kK]?)", re.sub(r"Hz$", "", s, flags=re.IGNORECASE))
    return float(m.group(1)) * (1000 if m.group(2) else 1) if m else None


def straight(pairs):
    """The largest set of (position, value) pairs on one straight line."""
    if len(pairs) < 2:
        return None
    gaps = [abs(pairs[n + 1]["p"] - pairs[n]["p"]) or math.inf for n in range(len(pairs) - 1)]
    best = None
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            a, b = pairs[i], pairs[j]
            if a["v"] == b["v"] or a["p"] == b["p"]:
                continue
            k = (b["v"] - a["v"]) / (b["p"] - a["p"])
            step = abs(k) * min(gaps)
            tol = max(0.05, 0.2 * (step if math.isfinite(step) else abs(b["v"] - a["v"])))
            inl = [p for p in pairs if abs(a["v"] + k * (p["p"] - a["p"]) - p["v"]) <= tol]
            if best is None or len(inl) > len(best):
                best = inl
    return best if best and len(best) >= 2 else None


# ---------------------------------------------------------------- the tracer
class Tracer:
    """One picture and what's traced on it. The window shows it and passes clicks in; tests drive it directly."""

    def __init__(self):
        self.ta = {"enabled": True, "manual": set(), "notes": {}, "noise": 0.0, "jpeg": False,
                   "px_oct": 0.0, "last_ocr": None, "last_trace": None, "dashed_found": False}
        self.v = {"d1": "", "d2": "", "f1": "", "f2": "", "tol": 64, "ppo": 48, "fmin": 20, "fmax": 20000,
                  "dashed": False, "snap": True, "every": True, "name": ""}
        self.typed = {"d": False, "f": False}  # values typed by hand aren't overwritten by the label reader
        self.moved = {"d": False, "f": False}  # nor lines dragged while it was reading
        self.unload()

    # ---------------------------------------------------------------- the picture
    def unload(self):
        self.px = None
        self.W = self.H = 0
        self.h_lines, self.v_lines, self.grid_x, self.box, self.label_words = [], [], [], None, []
        self.src_name = ""
        self.curves, self.cur = [], 0
        self.undo_stack, self.redo_stack = [], []
        self.cal = {"y1": 0.0, "y2": 0.0, "x1": 0.0, "x2": 0.0}
        self.bg = (255, 255, 255)
        self.dbg = None
        self._match = {}
        self.label_token = getattr(self, "label_token", 0) + 1  # (a label reading still running is ignored)

    @property
    def has_image(self):
        return self.px is not None

    @property
    def ys(self):
        return self.curves[self.cur]["ys"] if self.curves else None

    def load(self, rgb, name="Traced graph", jpeg=False):
        """A picture (H x W x 3 uint8, already scaled to MAX_PIXELS at most). Returns the axis note."""
        self.unload()
        self.px = np.ascontiguousarray(rgb, np.uint8)
        self.H, self.W = self.px.shape[:2]
        self.src_name = name or "Traced graph"
        self.v["name"] = self.src_name
        ta = self.ta
        ta.update(jpeg=bool(jpeg), notes={}, dashed_found=False)
        ta["manual"].clear()
        self.curves, self.cur = [self.new_curve(0)], 0
        self.typed = {"d": False, "f": False}
        note = self.detect()
        ta["noise"] = self.colour_noise()
        if ta["enabled"]:
            self.v["dashed"] = False
        self.fit_settings()
        return note

    def d2(self, ys, xs, c):
        """Squared colour distance of pixels (arrays of rows and columns, or slices) from colour c."""
        p = self.px[ys, xs].astype(np.int32)
        return ((p - np.asarray(c, np.int32)) ** 2).sum(-1)

    def background(self):
        """The most common colour (in coarse bins), as the average of the pixels in that bin (not the bin's middle:
        white would be read as 248 grey, and every picture as noisier than it is)."""
        step = max(1, int(math.sqrt(self.W * self.H / 250000)))
        s = self.px[::step, ::step].reshape(-1, 3).astype(np.int64)
        if not len(s):
            return (255, 255, 255)
        keys = (s[:, 0] >> 4) << 8 | (s[:, 1] >> 4) << 4 | s[:, 2] >> 4
        k = np.bincount(keys).argmax()
        return tuple(int(_js_round(v)) for v in s[keys == k].mean(0))

    def lines(self, horizontal):
        """Rows (or columns) mostly covered by drawn pixels, grouped into lines; also pale ones that run unbroken
        across most of the picture (soft, blurred gridlines are too pale to count as drawn)."""
        ink, faint = self.dbg > INK * INK, self.dbg > FAINT * FAINT
        if not horizontal:
            ink, faint = ink.T, faint.T
        n, length = ink.shape
        cover = np.where(longest_runs(faint) >= length * 0.5, 1.0, ink.sum(1) / length)
        out, a = [], 0
        while a < n:
            if cover[a] < 0.3:
                a += 1
                continue
            b = a
            while b + 1 < n and cover[b + 1] >= 0.3:
                b += 1
            if b - a < 12:  # (thicker is a filled area, not a line)
                out.append({"pos": (a + b) / 2, "a": a, "b": b})
            a = b + 1
        return out

    def detect(self):
        """Gridlines, the plot's frame, the calibration lines on gridlines and the gridlines' frequencies."""
        W, H = self.W, self.H
        self.bg = self.background()
        self.dbg = self.d2(slice(None), slice(None), self.bg)
        self._match = {}
        self.h_lines, self.v_lines = self.lines(True), self.lines(False)
        hl, vl = self.h_lines, self.v_lines
        box = {"x0": math.ceil(vl[0]["b"] + 1), "x1": math.floor(vl[-1]["a"] - 1), "y0": math.ceil(hl[0]["b"] + 1),
               "y1": math.floor(hl[-1]["a"] - 1)} if len(hl) >= 2 and len(vl) >= 2 else {"x0": 0, "x1": W - 1, "y0": 0, "y1": H - 1}
        if box["x1"] - box["x0"] < W * 0.2 or box["y1"] - box["y0"] < H * 0.2:
            box = {"x0": 0, "x1": W - 1, "y0": 0, "y1": H - 1}
        self.box = box
        # the dB lines: the top and bottom gridlines (their values are read or typed)
        self.cal["y1"] = hl[0]["pos"] if len(hl) >= 2 else H * 0.1
        self.cal["y2"] = hl[-1]["pos"] if len(hl) >= 2 else H * 0.9
        vals = freq_values([l["pos"] for l in vl])
        self.grid_x = [{"p": l["pos"], "v": vals[i]} for i, l in enumerate(vl) if vals[i] is not None] if vals else []
        gx = self.grid_x
        if len(gx) >= 2:
            a, b = gx[0], gx[-1]
            self.cal.update(x1=a["p"], x2=b["p"])
            self.v["f1"], self.v["f2"] = f"{a['v']:g}", f"{b['v']:g}"
            even = all(abs(math.log10(g["v"]) - (math.log10(a["v"]) + (g["p"] - a["p"]) / (b["p"] - a["p"])
                                                  * math.log10(b["v"] / a["v"]))) < 0.01 for g in gx)
            note = (f"Read {len(gx)} frequency gridlines as {fmt_hz(a['v'])} to {fmt_hz(b['v'])}"
                    + ("." if even else ". This axis is drawn unevenly, so every gridline is used (keep “Follow every "
                       "gridline” ticked).") + " Check them against the picture's labels.")
        else:
            self.cal["x1"] = vl[0]["pos"] if len(vl) >= 2 else W * 0.1
            self.cal["x2"] = vl[-1]["pos"] if len(vl) >= 2 else W * 0.9
            self.v["f1"] = self.v["f1"] or "20"
            self.v["f2"] = self.v["f2"] or "20000"
            note = "Couldn't read the frequency axis: drag the blue lines onto two labelled gridlines and type their Hz."
        self.v["d1"] = self.v["d2"] = ""
        self.label_words = []
        self.axis_note = self.detect_note = note  # (detect_note: each label reading's note starts from it, not the last)
        return note

    # ---------------------------------------------------------------- calibration
    def anchors_x(self, f1, f2):
        """The two blue lines, plus (with "Follow every gridline") every gridline with a known frequency between them:
        values in between are interpolated from the nearest gridlines, so unevenly drawn axes are read correctly."""
        cal, gx = self.cal, self.grid_x
        base = [{"p": cal["x1"], "v": f1}, {"p": cal["x2"], "v": f2}]
        if not self.v["every"] or len(gx) < 3:
            return base
        at = lambda p: next((a for a in gx if abs(a["p"] - p) < 1.5), None)
        a1, a2 = at(cal["x1"]), at(cal["x2"])
        if not a1 or not a2:
            return base
        k = f1 / a1["v"]  # (the typed values may use another power of ten than the guess)
        if abs(f2 / (a2["v"] * k) - 1) > 0.01:
            return base
        lo, hi = min(cal["x1"], cal["x2"]) + 1.5, max(cal["x1"], cal["x2"]) - 1.5
        return base + [{"p": a["p"], "v": a["v"] * k} for a in gx if lo < a["p"] < hi]

    def anchors_y(self, d1, d2v):
        cal = self.cal
        base = [{"p": cal["y1"], "v": d1}, {"p": cal["y2"], "v": d2v}]
        if not self.v["every"]:
            return base
        lo, hi = min(cal["y1"], cal["y2"]), max(cal["y1"], cal["y2"])
        mid = sorted(l["pos"] for l in self.h_lines if lo + 2 < l["pos"] < hi - 2)
        if not mid:
            return base
        n = len(mid) + 1
        gap = (hi - lo) / n
        if any(abs(p - (lo + (i + 1) * gap)) > gap * 0.25 for i, p in enumerate(mid)):
            return base  # (not evenly spaced values)
        top, bot = (d1, d2v) if cal["y1"] < cal["y2"] else (d2v, d1)
        return base + [{"p": p, "v": top + (bot - top) * (i + 1) / n} for i, p in enumerate(mid)]

    def calib(self):
        """Pixel <-> Hz and dB, or None while a value is missing."""
        v, cal = self.v, self.cal
        d1, d2v, f1, f2 = (_num(v[k]) for k in ("d1", "d2", "f1", "f2"))
        ok = None not in (d1, d2v, f1, f2) and f1 > 0 and f2 > 0 and f1 != f2 and d1 != d2v \
            and abs(cal["x2"] - cal["x1"]) > 2 and abs(cal["y2"] - cal["y1"]) > 2
        if not ok:
            return None
        lin = lambda x: x
        exp = lambda u: math.exp(min(u, 700.0))  # (as JS's Math.exp: huge, never an OverflowError)
        fx = Piecewise.make(self.anchors_x(f1, f2), math.log, exp) or \
            Piecewise.make([{"p": cal["x1"], "v": f1}, {"p": cal["x2"], "v": f2}], math.log, exp)
        dy = Piecewise.make(self.anchors_y(d1, d2v), lin, lin) or \
            Piecewise.make([{"p": cal["y1"], "v": d1}, {"p": cal["y2"], "v": d2v}], lin, lin)
        return Calib(fx, dy) if fx and dy else None

    def snap_to(self, lines, v, scale):
        if not self.v["snap"]:
            return v
        best, dist = v, 8 / scale
        for l in lines:
            if abs(l["pos"] - v) < dist:
                dist, best = abs(l["pos"] - v), l["pos"]
        return best

    def move_line(self, key, value, scale=1.0):
        """A calibration line dragged (snapped onto gridlines); a blue one dropped on a gridline with a known
        frequency takes its value."""
        if key[0] == "y":
            self.cal[key] = self.snap_to(self.h_lines, min(max(value, 0), self.H), scale)
            self.moved["d"] = True
        else:
            self.cal[key] = self.snap_to(self.v_lines, min(max(value, 0), self.W), scale)
            self.moved["f"] = True
            g = next((a for a in self.grid_x if abs(a["p"] - self.cal[key]) < 1.5), None)
            if g and self.v["every"]:
                self.v["f1" if key == "x1" else "f2"] = f"{g['v']:g}"

    # ---------------------------------------------------------------- tracing
    def pick_colour(self, x, y, hue=None):
        """The strongest drawn colour within 4 px of a click (None: nothing drawn there); hue: only pixels of that hue
        (Auto trace: where its curve crosses another, the other's colour may be the stronger one there)."""
        x0, x1, y0, y1 = max(0, x - 4), min(self.W, x + 5), max(0, y - 4), min(self.H, y + 5)
        if x0 >= x1 or y0 >= y1:
            return None
        win = self.dbg[y0:y1, x0:x1]
        if hue is not None:
            p = self.px[y0:y1, x0:x1].astype(np.int32)
            keep = (p.max(-1) - p.min(-1) >= 70) & (self.hue_bins(p) == hue)
            win = np.where(keep, win, 0)
        # (the first strongest in reading order: trace.js's loops, dy outer)
        i = int(np.argmax(win))
        if win.flat[i] <= INK * INK:
            return None
        yy, xx = divmod(i, x1 - x0)
        return tuple(int(c) for c in self.px[y0 + yy, x0 + xx])

    def _matcher(self, c, tol2):
        """For colour c: each column's runs of matching pixels inside the plot (worked out once per colour)."""
        key = (tuple(c), tol2)
        m = self._match.get(key)
        if m is None:
            b = self.box
            ys, xs = slice(b["y0"], b["y1"] + 1), slice(b["x0"], b["x1"] + 1)
            grey = max(c) - min(c) < GREY + 25
            if grey:  # (a grey curve picked a little tinted from a JPEG: matched as the plain grey it is)
                c = (round(sum(c) / 3),) * 3
            ok = self.d2(ys, xs, c) <= tol2
            if grey:
                # a grey curve (most targets): only greyish pixels are it. The soft edge of an orange or green curve,
                # or a JPEG's smeared colour around one, is close to grey in levels and still tinted; where a curve
                # crossed or neared a dashed grey target, the trace went off along it (7 dB at a dip; 2026-10-13)
                # (a JPEG's grey curve can be picked a little tinted: its own tint and some more allowed)
                p = self.px[ys, xs].astype(np.int16)
                ok &= (p.max(-1) - p.min(-1)) < GREY
            m = {"ok": ok, "cols": {}}
            if len(self._match) > 60:
                self._match.clear()
            self._match[key] = m
        return m

    def _col_runs(self, m, x):
        r = m["cols"].get(x)
        if r is None:
            col = m["ok"][:, x - self.box["x0"]].astype(np.int8)
            d = np.diff(np.concatenate(([0], col, [0])))
            y0 = self.box["y0"]
            r = (np.flatnonzero(d == 1) + y0, np.flatnonzero(d == -1) - 1 + y0)
            m["cols"][x] = r
        return r

    def runs(self, x, lo, hi, c, tol2):
        """Runs of matching pixels in column x that reach into [lo, hi], each to its full length."""
        b = self.box
        lo, hi = max(b["y0"], math.floor(lo)), min(b["y1"], math.ceil(hi))
        if lo > hi:
            return []
        a, e = self._col_runs(self._matcher(c, tol2), x)
        i, j = np.searchsorted(e, lo), np.searchsorted(a, hi, side="right")
        return [(int(a[k]), int(e[k])) for k in range(i, j)]

    @staticmethod
    def trim(r, t, ls):
        """Gridline rows dropped from the ends of a run (a curve crossing or running along a gridline)."""
        a, b = r
        for l in ls:
            if b - a + 1 <= t:
                break
            if l["a"] <= a <= l["b"] < b:
                a = l["b"] + 1
            if l["a"] <= b <= l["b"] and l["a"] > a:
                b = l["a"] - 1
        return a, b

    @staticmethod
    def on_grid_only(r, t, ls):
        return any(r[0] >= l["a"] - 1 and r[1] <= l["b"] + 1 and (r[1] - r[0] + 1) < t for l in ls)

    def between_lines(self, x, r):
        """Whether a run has drawn pixels right above and below it (pixels of two other lines blending into each
        other there; a curve's own pixels are edged by the background)."""
        a, b = r[0] - 1, r[1] + 1
        return a >= 0 and b < self.H and self.dbg[a, x] > INK * INK and self.dbg[b, x] > INK * INK

    def centre(self, x, r, c):
        """The middle of a run weighted by how close each pixel's colour is to the curve's (anti-aliased edges count
        part-way)."""
        bg = self.bg
        dc = math.sqrt(max(1, sum((bg[i] - c[i]) ** 2 for i in range(3))))
        lo, hi = max(self.box["y0"], r[0] - 1), min(self.box["y1"], r[1] + 1)
        yy = np.arange(lo, hi + 1)
        k = np.maximum(0, 1 - np.sqrt(self.d2(slice(lo, hi + 1), x, c)) / dc)
        w = k.sum()
        return float((yy * k).sum() / w) if w else (r[0] + r[1]) / 2

    def care(self):
        """How carefully it works: labels read at 4× size with a second try, the trace between pixels, a trace that
        stops early tried again as dashed and then with more colour tolerance; up to 48 points per octave (the app's
        own curves are on squiglink's 1/48-octave grid: more would add nothing once loaded). Until 1.0.13
        a speed-accuracy slider chose; tested on the sample graph clean and degraded (benchmarks: trace_test.py) every
        way took under about a second, the middle and this the same but for one picture, and the quick end missed
        dashed targets: the slider went (the user's ask)."""
        return {"ocr_scale": 4, "ocr_retry": True, "subpixel": True, "retries": 2}

    def follow(self, x0, y0, c, dashed=None, subpixel=None, tol=None):
        """The curve of colour c through (x0, y0), followed both ways: {column: y}."""
        dashed = self.v["dashed"] if dashed is None else dashed
        sub = self.care()["subpixel"] if subpixel is None else subpixel
        tol2 = (self.v["tol"] if tol is None else tol) ** 2
        box = self.box
        box_h = box["y1"] - box["y0"]
        start = [r for r in self.runs(x0, y0 - 6, y0 + 6, c, tol2) if r[1] - r[0] < box_h * 0.5]
        if not start:
            return None
        start.sort(key=lambda r: abs((r[0] + r[1]) / 2 - y0))
        t = min(12, max(1, start[0][1] - start[0][0] + 1))  # (the line's thickness)
        got = {x0: self.centre(x0, start[0], c) if sub else (start[0][0] + start[0][1]) / 2}
        width = box["x1"] - box["x0"]
        max_gap = max(40, round(width * 0.06)) if dashed else max(12, round(width * 0.025))
        # the gridlines drawn in the curve's own colour: only a run on one of them can be just the gridline (a curve
        # lying on a pale gridline of another colour was skipped there: a cut in the trace); in the gridlines' own
        # colour, a run that's only a gridline is never the curve (in a dashed curve's gaps the trace otherwise slid
        # along the gridline)
        step = max(1, width >> 6)
        gxs = np.arange(box["x0"], box["x1"] + 1, step)
        same = [l for l in self.h_lines
                if int((self.d2(_js_round(l["pos"]), gxs, c) <= tol2).sum()) > 40]
        grid_same = bool(same)
        on_v = np.zeros(self.W + 2, bool)
        for l in self.v_lines:
            on_v[max(0, l["a"] - 1):l["b"] + 2] = True
        # the curves already traced (the other ones): a run on one of them is that curve's, not this one's. Where a dashed
        # grey target crossed or neared them, their softened or smeared edges passed for grey and the trace went off
        # along them; now it's a gap there, bridged
        # (only for a grey curve: coloured ones are kept apart by their colours, and the right channel running beside
        # the left was cut where they touched)
        others = [o["ys"] for i, o in enumerate(self.curves) if i != self.cur and self.has_data(o)] \
            if max(c) - min(c) < GREY + 25 else []
        mine_at = lambda x, r: not any(r[0] - t - 1 <= o[x] <= r[1] + t + 1 for o in others)
        for direction in (-1, 1):
            y_prev, x_prev, slope, gap = got[x0], x0, 0.0, 0
            x = x0 + direction
            while box["x0"] <= x <= box["x1"]:
                pred = y_prev + slope * (x - x_prev)
                # (a dashed curve's long gaps: it may bend a lot before the next dash, so the window grows with the gap)
                win = 4 + t * 2 + ((min(gap, 12) + min(30, gap * gap * 0.015)) if dashed else gap * 2) \
                    + abs(slope) * (3 if dashed else 2)
                if on_v[x]:  # a vertical gridline: stepped over (a curve crossing it can cut it in two)
                    gap += 1
                    x += direction
                    continue
                cand = self.runs(x, pred - win, pred + win, c, tol2)
                if any(r[1] - r[0] > box_h * 0.5 for r in cand):  # (one not found as a gridline)
                    gap += 1
                    x += direction
                    continue
                best, bd = None, math.inf
                for r0 in cand:
                    if others and not mine_at(x, r0):
                        continue  # (another curve's)
                    if (t > 2 or grid_same) and self.on_grid_only(r0, math.inf if grid_same else t, same):
                        continue  # just the gridline: the curve is elsewhere
                    if t >= 2 and r0[1] == r0[0] and self.between_lines(x, r0):
                        continue  # (a blend of two other lines that touch: it can look like this curve's colour)
                    r = self.trim(r0, t, same)
                    d = r[0] - pred if pred < r[0] else pred - r[1] if pred > r[1] else 0
                    if d < bd:
                        bd, best = d, r
                if best is None or bd > win:
                    gap += 1
                    if gap > max_gap:
                        break
                    x += direction
                    continue
                y = self.centre(x, best, c) if sub else (best[0] + best[1]) / 2
                slope = max(-8.0, min(8.0, (0.8 if dashed else 0.6) * slope + (0.2 if dashed else 0.4) * (y - y_prev) / (x - x_prev)))
                got[x] = y
                y_prev, x_prev, gap = y, x, 0
                x += direction
        return got

    def trace_at(self, x, y, hue=None):
        """A click on the curve: followed and added to the selected curve (hue: Auto trace's colour). Returns the
        message for the status line."""
        x, y = _js_round(x), _js_round(y)
        box = self.box
        if not self.has_image or x < box["x0"] or x > box["x1"] or y < box["y0"] - 6 or y > box["y1"] + 6:
            return "Click on a curve inside the graph."
        c = self.pick_colour(x, y, hue)
        if not c:
            return "No curve there: click right on the line (zoom in with the mouse wheel if it's thin)."
        # start from the nearest pixel of that colour: a click on a dash's pale end or in a gap between dashes has none
        # in its own column
        tol2 = self.v["tol"] ** 2
        sd, sx, sy = math.inf, x, y
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                xx, yy = x + dx, y + dy
                if xx < box["x0"] or xx > box["x1"] or yy < box["y0"] or yy > box["y1"]:
                    continue
                if int(self.d2(yy, xx, c)) > tol2:
                    continue
                if dx * dx + dy * dy < sd:
                    sd, sx, sy = dx * dx + dy * dy, xx, yy
        x, y = sx, sy
        t0 = time.perf_counter()
        y0 = min(max(y, box["y0"]), box["y1"])
        got = self.follow(x, y0, c)
        span = lambda g: (max(g) - min(g)) if g else 0
        full = (box["x1"] - box["x0"]) * 0.6
        retried = ""
        ta = self.ta
        # a trace that stops early: tried again as a dashed line, then (accuracy) with more colour tolerance
        if ta["enabled"] and got and span(got) < full:
            n, dashed_now, tries = self.care()["retries"], self.v["dashed"], []
            if n >= 1 and not dashed_now and not self.own("dashed"):
                tries.append({"dashed": True, "why": "dashed"})
            if n >= 2 and not self.own("tol"):
                tries.append({"dashed": dashed_now or not self.own("dashed"),
                              "tol": min(128, _js_round(self.v["tol"] * 1.4 / 5) * 5), "why": "tol"})
            for o in tries:
                g = self.follow(x, y0, c, dashed=o["dashed"], tol=o.get("tol"))
                if g and span(g) > span(got) * 1.3:
                    got, retried = g, o["why"]
                    if o["dashed"] and not dashed_now:
                        self.v["dashed"] = True
                        ta["dashed_found"] = True
                        ta["notes"]["dashed"] = "Dashed line: the trace stopped at gaps in the line, so it now bridges them."
                    if o.get("tol"):
                        self.v["tol"] = o["tol"]
                        ta["notes"]["tol"] = (f"Colour tolerance raised to {o['tol']}: the curve's colour varies more "
                                              "than the picture's noise suggested.")
                    if span(got) >= full:
                        break
        ta["last_trace"] = time.perf_counter() - t0
        if not got or len(got) < 3:
            return "Couldn't follow a line from there. Try clicking the middle of the curve, or raise the colour tolerance."
        self.push()
        ys = self.ys
        for gx, gy in got.items():
            ys[gx] = gy
        self.curves[self.cur]["colour"] = c
        short = span(got) < (box["x1"] - box["x0"]) * 0.6 and not self.v["dashed"]
        return (f"Traced {len(got)} px of the curve"
                + ((" (as a dashed line)" if retried == "dashed" else " (with more colour tolerance)") if retried else "")
                + "." + (" It stopped early: if the line is dashed or dotted, tick “Dashed or dotted line” and click it "
                         "again; otherwise click the rest of it." if short else
                         " Click another part to add to it, or use Draw / Erase to fix spots."))

    @staticmethod
    def hue_bin(r, g, b):
        """A colour's hue in twelve bins of 30° (0-11, round the circle)."""
        return (_js_round(math.atan2(math.sqrt(3) * (g - b), 2 * r - g - b) / (math.pi / 6)) % 12 + 12) % 12

    @staticmethod
    def hue_bins(p):
        """hue_bin of every pixel in an array (..., 3) of int."""
        r, g, b = p[..., 0], p[..., 1], p[..., 2]
        return np.floor(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b) / (np.pi / 6) + 0.5).astype(int) % 12

    def auto_seed(self, skip=None):
        """A place to start Auto trace: the most common strong colour, or else the drawn line near the middle that
        crosses the most of the graph (skip: the curve being traced into; -1 when a new one is to be added)."""
        skip = self.cur if skip is None else skip
        box = self.box
        mid = (box["x0"] + box["x1"]) >> 1
        others = [c for i, c in enumerate(self.curves) if i != skip and self.has_data(c)]
        taken = lambda x, y: any(abs(c["ys"][x] - y) < 6 for c in others)
        taken_hue = [self.hue_bin(*c["colour"]) for c in others if c["colour"]]
        ys_, xs_ = np.arange(box["y0"], box["y1"] + 1, 2), np.arange(box["x0"], box["x1"] + 1, 2)
        sub = self.px[box["y0"]:box["y1"] + 1:2, box["x0"]:box["x1"] + 1:2].astype(np.int32)
        strong = (sub.max(-1) - sub.min(-1) >= 70) & (self.dbg[box["y0"]:box["y1"] + 1:2, box["x0"]:box["x1"] + 1:2] >= INK * INK)
        iy, ix = np.nonzero(strong)
        width = box["x1"] - box["x0"]
        if len(iy):
            h = self.hue_bins(sub[iy, ix])
            best = None
            # (a curve already traced: its hue and the ones beside it, as a JPEG shifts a line's hue a little; and its
            # pixels: a stretch of it seen as another hue was taken for a new curve and traced again)
            near_taken = {(hb + d) % 12 for hb in taken_hue for d in (-1, 0, 1)}
            free = np.array([not taken(int(xs_[ix[k]]), int(ys_[iy[k]])) for k in range(len(iy))], bool)
            for hb in range(12):
                sel = np.flatnonzero((h == hb) & free)
                if not len(sel) or hb in near_taken:
                    continue
                cols = len(np.unique(xs_[ix[sel]] >> 3))
                # (a curve's colour spreads across the graph: a logo or a label in a strong colour doesn't)
                if cols * 8 > width * 0.3 and (best is None or len(sel) > best[0]):
                    best = (len(sel), sel[:400], hb)
            if best and best[0] > width * 0.3:
                pts = sorted(((int(xs_[ix[k]]), int(ys_[iy[k]])) for k in best[1]), key=lambda p: abs(p[0] - mid))
                return pts[0] + (best[2],)
        # no curve in a strong colour: drawn runs near the middle, each followed; the one that crosses the most of the
        # graph wins (the thickest one was often a watermark's or a title's letters)
        T2, box_h, cand = INK * INK, box["y1"] - box["y0"], []
        for k in range(60):
            x = mid + (1 if k % 2 else -1) * math.ceil(k / 2) * max(1, _js_round(width / 80))
            if x < box["x0"] or x > box["x1"]:
                continue
            col = self.dbg[box["y0"]:box["y1"] + 1, x] > T2
            d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
            for a, e in zip(np.flatnonzero(d == 1) + box["y0"], np.flatnonzero(d == -1) - 1 + box["y0"]):
                a, e = int(a), int(e)
                ln = e - a + 1
                if 2 <= ln < box_h * 0.5 and not any(a >= l["a"] - 1 and e <= l["b"] + 1 for l in self.h_lines) \
                        and not taken(x, (a + e) / 2):
                    cand.append({"x": x, "y": (a + e) / 2, "len": ln})
        cand.sort(key=lambda s: -s["len"])
        best, tries, seen = None, 0, []  # seen: lines already followed (a run on one is the same line again)
        for s in cand:
            if tries >= 40:
                break
            if any(s["x"] in g and abs(g[s["x"]] - s["y"]) <= s["len"] / 2 + 3 for g in seen):
                continue
            tries += 1
            c = self.pick_colour(s["x"], _js_round(s["y"]))
            g = c and self.follow(s["x"], s["y"], c, dashed=True)
            if not g or len(g) < 3:
                continue
            seen.append(g)
            # its width: only the unbroken stretch from the seed (a trace that jumped from a title's letters onto a
            # curve of a similar colour isn't the title's)
            xs = sorted(g)
            at = xs.index(s["x"]) if s["x"] in g else -1
            joined = lambda i, j, g=g, xs=xs: abs(g[xs[j]] - g[xs[i]]) <= 12 + abs(xs[j] - xs[i])
            lo = hi = at
            while lo > 0 and joined(lo, lo - 1):
                lo -= 1
            while 0 <= hi < len(xs) - 1 and joined(hi, hi + 1):
                hi += 1
            span = 0 if at < 0 else xs[hi] - xs[lo]
            mine = sum(1 for gx, gy in g.items() if not taken(gx, gy)) / len(g)  # (not another curve again)
            # (as wide as the best so far: the stronger colour wins, not a pale halo of it or a gridline's grey)
            ink = sum((c[i] - self.bg[i]) ** 2 for i in range(3))
            if mine > 0.5 and (best is None or span > best["span"] * 1.1 or (span > best["span"] * 0.9 and ink > best["ink"])):
                best = dict(s, span=span, ink=ink)
        return (best["x"], best["y"], None) if best else None

    def auto_trace(self):
        """Find a curve and follow it; again for the next one (in a new curve). Returns the status line."""
        if not self.has_image:
            return ""
        more = self.has_data(self.curves[self.cur])
        if more and len(self.curves) >= MAX_CURVES:
            return "That's as many curves as fit here."
        s = self.auto_seed(-1 if more else self.cur)
        if not s:
            return ("No other curve found: click on the one you want." if any(map(self.has_data, self.curves))
                    else "Couldn't find a curve by itself: click on the one you want.")
        if more:
            self.add_curve()
        return self.trace_at(s[0], s[1], hue=s[2])

    # ---------------------------------------------------------------- several curves (e.g. left and right)
    def new_curve(self, i):
        return {"label": LABELS[i] if i < len(LABELS) else str(i + 1), "colour": None, "ys": np.full(self.W, np.nan)}

    @staticmethod
    def has_data(c):
        return bool(np.isfinite(c["ys"]).any())

    def add_curve(self):
        self.push()
        used = {c["label"] for c in self.curves}
        c = self.new_curve(len(self.curves))
        c["label"] = next((l for l in LABELS if l not in used), str(len(self.curves) + 1))
        self.curves.append(c)
        self.cur = len(self.curves) - 1
        return f"New curve “{c['label']}”: click it on the picture, or press Auto trace."

    def delete_curve(self, i):
        self.push()
        if len(self.curves) == 1:
            self.curves[0]["ys"][:] = np.nan
            self.curves[0]["colour"] = None
        else:
            del self.curves[i]
            if i < self.cur:
                self.cur -= 1  # (one before the selected: the selected moves up one)
        self.cur = min(self.cur, len(self.curves) - 1)

    # ---------------------------------------------------------------- the labels (read off the window's thread)
    def read_region(self, ocr_words, x0, y0, x1, y1, scale):
        """Words in part of the picture, in picture pixels (enlarged first: small labels read better)."""
        from scipy import ndimage
        x0, y0 = max(0, math.floor(x0)), max(0, math.floor(y0))
        x1, y1 = min(self.W, math.ceil(x1)), min(self.H, math.ceil(y1))
        if x1 - x0 < 8 or y1 - y0 < 8:
            return []
        k = max(1.0, min(scale, 4000 / max(x1 - x0, y1 - y0)))
        part = self.px[y0:y1, x0:x1]
        big = ndimage.zoom(part, (k, k, 1), order=1) if k > 1 else part
        ky, kx = big.shape[0] / (y1 - y0), big.shape[1] / (x1 - x0)
        return [dict(w, x0=x0 + w["x0"] / kx, x1=x0 + w["x1"] / kx, y0=y0 + w["y0"] / ky, y1=y0 + w["y1"] / ky)
                for w in ocr_words(big)]

    def db_pairs(self, words, left):
        """The dB labels beside the plot, matched to horizontal gridlines, keeping the largest set on one straight line."""
        labs = [dict(w, v=db_num(w["text"]), yc=(w["y0"] + w["y1"]) / 2) for w in join_words(words)]
        labs = [w for w in labs if w["v"] is not None]
        hl, box = self.h_lines, self.box
        gaps = sorted(hl[i + 1]["pos"] - hl[i]["pos"] for i in range(len(hl) - 1))
        gap = gaps[len(gaps) >> 1] if gaps else (box["y1"] - box["y0"]) / 5
        pairs = []
        if len(hl) >= 2:
            for l in hl:
                c = [w for w in labs if abs(w["yc"] - l["pos"]) < gap * 0.4]
                if not c:
                    continue
                c.sort(key=lambda w: box["x0"] - w["x1"] if left else w["x0"] - box["x1"])
                pairs.append({"p": l["pos"], "v": c[0]["v"], "w": c[0]})
        else:
            pairs = [{"p": w["yc"], "v": w["v"], "w": w} for w in labs]
        return straight(pairs)

    def hz_pairs(self, words):
        """The frequency labels under the plot, matched to vertical gridlines (by centre, or by an end for labels
        shifted inwards at the frame), keeping the longest run that increases left to right."""
        labs = [dict(w, v=hz_num(w["text"]), xc=(w["x0"] + w["x1"]) / 2) for w in join_words(words)]
        labs = [w for w in labs if w["v"] and w["v"] > 0]
        vl, pairs = self.v_lines, []
        if len(vl) >= 3:
            near = lambda x: min(vl, key=lambda l: abs(l["pos"] - x))
            for w in labs:
                l = near(w["xc"])
                if abs(l["pos"] - w["xc"]) > max(6, (w["x1"] - w["x0"]) * 0.35):
                    a, b = near(w["x0"]), near(w["x1"])
                    l = a if abs(a["pos"] - w["x0"]) < 6 else b if abs(b["pos"] - w["x1"]) < 6 else None
                if l and not any(p["p"] == l["pos"] for p in pairs):
                    pairs.append({"p": l["pos"], "v": w["v"], "w": w})
        else:
            pairs = [{"p": w["xc"], "v": w["v"], "w": w} for w in labs]
        pairs.sort(key=lambda p: p["p"])
        n = len(pairs)
        ln, prev = [1] * n, [-1] * n  # (the longest increasing run of values)
        for i in range(n):
            for j in range(i):
                if pairs[j]["v"] < pairs[i]["v"] and ln[j] + 1 > ln[i]:
                    ln[i], prev[i] = ln[j] + 1, j
        i = ln.index(max(ln)) if n else -1
        run = []
        while i >= 0:
            run.insert(0, pairs[i])
            i = prev[i]
        return run if len(run) >= 2 else None

    def read_labels(self, ocr_words):
        """The axis labels read (blocking: run it off the window's thread). Returns {token, hz, db, seconds}; apply it
        with use_labels() on the window's thread."""
        token, cr, box, W, H = self.label_token, self.care(), self.box, self.W, self.H
        t0 = time.perf_counter()
        pad = _js_round(min(W, H) * 0.03)

        def read(scale):
            left = self.read_region(ocr_words, 0, box["y0"] - pad, box["x0"] - 2, box["y1"] + pad, scale)
            right = self.read_region(ocr_words, box["x1"] + 2, box["y0"] - pad, W, box["y1"] + pad, scale)
            below = self.read_region(ocr_words, box["x0"] - pad * 3, box["y1"] + 2, box["x1"] + pad * 3, H, scale)
            # the row of labels nearest the plot (not a title further down)
            rows = [w for w in join_words(below) if hz_num(w["text"])]
            top = min((w["y0"] for w in rows), default=0)
            row_h = max((w["y1"] - w["y0"] for w in rows), default=0)
            db = self.db_pairs(left, True) or self.db_pairs(right, False)
            if not db:  # labels printed just inside the plot, along its left edge
                inside = self.read_region(ocr_words, box["x0"], box["y0"] - pad, box["x0"] + _js_round((box["x1"] - box["x0"]) * 0.06),
                                          box["y1"] + pad, scale)
                db = self.db_pairs(inside, False)
            return self.hz_pairs([w for w in rows if w["y0"] < top + row_h * 1.2]), db
        try:
            hz, db = read(cr["ocr_scale"])
            if cr["ocr_retry"] and (not hz or not db) and token == self.label_token:  # accuracy: a second try
                hz2, db2 = read(2 if cr["ocr_scale"] == 4 else 4)
                hz, db = hz or hz2, db or db2
        except Exception:
            if token != self.label_token:  # (the picture was removed or replaced while reading: nothing to say)
                hz = db = None
            else:
                raise
        return {"token": token, "hz": hz, "db": db, "seconds": time.perf_counter() - t0, "scale": cr["ocr_scale"]}

    def use_labels(self, res, before):
        """What was read, into the lines and values (unless typed or dragged meanwhile). Returns the axis note, or
        None when the picture changed while reading."""
        if res["token"] != self.label_token:
            return None
        hz, db = res["hz"], res["db"]
        self.ta["last_ocr"] = {"seconds": res["seconds"], "scale": res["scale"]}
        self.label_words = [p["w"] for p in (db or []) + (hz or [])]
        parts = []
        if db and not self.typed["d"] and not self.moved["d"]:
            a, b = db[0], db[-1]
            self.cal["y1"], self.cal["y2"] = a["p"], b["p"]
            self.v["d1"], self.v["d2"] = f"{a['v']:g}", f"{b['v']:g}"
            parts.append(f"dB labels {fmt_db(a['v'])} to {fmt_db(b['v'])}")
        if hz and not self.typed["f"] and not self.moved["f"]:
            parts.append(self.use_hz_labels(hz))
        self.fit_settings()
        if parts:
            self.axis_note = (f"Read the labels: {'; '.join(parts)}. The green boxes show which labels were used; check "
                              "them against the picture.")
        else:
            self.axis_note = before + ("" if db or hz else " Couldn't read the axis labels: type the values of the coloured lines.")
        return self.axis_note

    def use_hz_labels(self, hz):
        """Labels confirm the gridlines' frequencies (and fix the power of ten if the guess was off), or replace them."""
        ratios = []
        for pr in hz:
            g = next((a for a in self.grid_x if abs(a["p"] - pr["p"]) < 1.5), None)
            if g:
                ratios.append(pr["v"] / g["v"])
        if len(self.grid_x) >= 2 and ratios:
            r = sorted(ratios)[len(ratios) >> 1]
            agree = sum(1 for x in ratios if abs(math.log10(x / r)) < 0.01)
            if agree >= max(2, len(ratios) * 0.6):
                if abs(math.log10(r)) > 0.004:
                    self.grid_x = [dict(a, v=_p3(a["v"] * r)) for a in self.grid_x]
                a = next((g for g in self.grid_x if abs(g["p"] - self.cal["x1"]) < 1.5), None)
                b = next((g for g in self.grid_x if abs(g["p"] - self.cal["x2"]) < 1.5), None)
                if a:
                    self.v["f1"] = f"{a['v']:g}"
                if b:
                    self.v["f2"] = f"{b['v']:g}"
                return f"{agree} frequency labels match the gridlines"
        self.grid_x = [{"p": pr["p"], "v": pr["v"]} for pr in hz]
        a, b = self.grid_x[0], self.grid_x[-1]
        self.cal.update(x1=a["p"], x2=b["p"])
        self.v["f1"], self.v["f2"] = f"{a['v']:g}", f"{b['v']:g}"
        return f"frequency labels {fmt_hz(a['v'])} to {fmt_hz(b['v'])}"

    # ---------------------------------------------------------------- editing
    def snapshot(self):
        return {"cur": self.cur, "curves": [dict(c, ys=c["ys"].copy()) for c in self.curves]}

    def restore(self, s):
        self.curves = s["curves"]
        self.cur = min(s["cur"], len(self.curves) - 1)

    def push(self):
        self.undo_stack.append(self.snapshot())
        if len(self.undo_stack) > 80:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.snapshot())
            self.restore(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.snapshot())
            self.restore(self.redo_stack.pop())

    def clear(self):
        if not self.curves or not self.has_data(self.curves[self.cur]):
            return ""
        self.push()
        self.ys[:] = np.nan
        return "Cleared this curve (Undo brings it back)."

    def smooth(self):
        """Pixel steps smoothed out (a small Gaussian over the traced columns)."""
        if self.ys is None:
            return
        self.push()
        ys = self.ys
        w = np.exp(-(np.arange(-3, 4) ** 2) / (2 * 1.5 * 1.5))
        ok = np.isfinite(ys)
        s = np.convolve(np.where(ok, ys, 0), w, "same")
        n = np.convolve(ok.astype(float), w, "same")
        out = ys.copy()
        out[ok] = s[ok] / n[ok]
        self.curves[self.cur]["ys"] = out

    def draw_segment(self, xa, ya, xb, yb):
        if xa > xb:
            xa, ya, xb, yb = xb, yb, xa, ya
        ys = self.ys
        for x in range(max(0, _js_round(xa)), min(self.W - 1, _js_round(xb)) + 1):
            ys[x] = yb if xb == xa else ya + (yb - ya) * (x - xa) / (xb - xa)

    def erase(self, x0, y0, x1, y1):
        """The trace inside a box removed. Returns how many columns."""
        a, b = max(0, _js_round(min(x0, x1))), min(self.W - 1, _js_round(max(x0, x1)))
        if b < a:  # (a box beside the picture: nothing; a negative end would slice nearly the whole trace)
            return 0
        lo, hi = min(y0, y1), max(y0, y1)
        ys = self.ys
        with np.errstate(invalid="ignore"):
            hit = np.flatnonzero((ys[a:b + 1] >= lo) & (ys[a:b + 1] <= hi)) + a
        if len(hit):
            self.push()
            self.ys[hit] = np.nan
        return len(hit)

    # ---------------------------------------------------------------- saving
    def points(self, ys, comp=None):
        """The trace as [(Hz, dB)] at the points per octave, within the range to save; .gaps: parts over 40 px untraced."""
        k = self.calib()
        if not k:
            raise ValueError("Type the values of the four lines first (two dB values and two frequencies).")
        valid = np.flatnonzero(np.isfinite(ys))
        if len(valid) < 20:
            raise ValueError("Trace a curve first.")
        ppo = int(self.v["ppo"])
        fa, fb = k.f(valid[0]), k.f(valid[-1])
        lo = max(_num(self.v["fmin"]) or 20, min(fa, fb))
        hi = min(_num(self.v["fmax"]) or 20000, max(fa, fb))
        if not hi > lo:
            raise ValueError("The traced part is outside the frequency range to save.")
        vx, vy = valid.astype(float), ys[valid]
        out = []
        n = math.ceil(ppo * math.log2(lo / 1000) - 1e-9)
        while True:
            f = 1000 * 2 ** (n / ppo)
            if f > hi * (1 + 1e-9):
                break
            x = k.x(f)
            y = float(np.interp(x, vx, vy))  # (a straight line between the nearest traced columns)
            out.append((f, k.db(y) + (comp(f) if comp else 0)))
            n += 1
        if len(out) < 32:
            raise ValueError(f"Only {len(out)} points: trace more of the curve or raise the points per octave.")
        gaps = []  # (the drawing shows a break there; the file can only bridge it with a straight line)
        for i in np.flatnonzero(np.diff(valid) > 40):
            f1, f2 = k.f(valid[i]), k.f(valid[i + 1])
            if max(f1, f2) > lo and min(f1, f2) < hi:
                gaps.append((min(f1, f2), max(f1, f2)))
        return out, gaps

    def file_text(self, pts, note=""):
        return f"* Traced from {self.src_name} with AutoEQ Studio{note}\n" + \
            "\n".join(f"{f:.{3 if f < 100 else 2}f}\t{v:.3f}" for f, v in pts) + "\n"

    def outputs(self, only_current=False, comp=None, comp_note=""):
        """What to save: [{file, text, label, gaps}], every curve with data as "<name> <label>", or "<name>" for one."""
        safe = lambda s: re.sub(r'[<>:"/\\|?*]', "_", s).strip()
        name = safe(self.v["name"] or self.src_name) or "Traced graph"
        lst = [self.curves[self.cur]] if only_current else [c for c in self.curves if self.has_data(c)]
        if not lst or not any(map(self.has_data, lst)):
            raise ValueError("Trace a curve first.")
        outs = []
        for i, c in enumerate(lst):
            try:
                pts, gaps = self.points(c["ys"], comp)
            except ValueError as e:  # (which of several curves: a stray bit on a third one stopped L and R)
                if len(lst) == 1:
                    raise
                raise ValueError(f"Curve “{c['label'] or i + 1}”: {e} (or delete that curve)") from None
            outs.append({"file": f"{name} {safe(c['label']) or i + 1}.txt" if len(lst) > 1 else f"{name}.txt",
                         "text": self.file_text(pts, comp_note), "label": c["label"], "gaps": gaps})
        seen = set()  # (each curve its own file name: the same name twice was saved as another device)
        for o in outs:
            if o["file"].lower() in seen:
                raise ValueError(f"Two curves are named “{o['label']}”: give each its own name (e.g. L and R).")
            seen.add(o["file"].lower())
        return outs

    @staticmethod
    def gaps_text(outs):
        g = [x for o in outs for x in o["gaps"]]
        if not g:
            return ""
        return (f"Saved with a straight line across the untraced part{'s' if len(g) > 1 else ''} at "
                + ", ".join(f"{fmt_hz(a)}–{fmt_hz(b)}" for a, b in g) + ": trace or draw it there for its real shape.")

    # ---------------------------------------------------------------- automatic settings
    def own(self, k):
        return k in self.ta["manual"]

    def set_ctl(self, k, v, why):
        self.ta["notes"][k] = why
        if self.ta["enabled"] and not self.own(k):
            self.v[k] = v

    def colour_noise(self):
        """The average distance of background pixels from the background colour."""
        step = max(1, int(math.sqrt(self.W * self.H / 60000)))
        d = self.dbg[::step, ::step]
        d = d[d < INK * INK]
        return float(np.sqrt(d).mean()) if d.size else 0.0

    def fit_settings(self):
        """Colour tolerance (from the picture's colour noise), points per octave (from its resolution) and the range
        to save (from its axis)."""
        if not self.has_image:
            return
        ta = self.ta
        tol = max(40, min(110, _js_round((45 + 3 * ta["noise"] + (10 if ta["jpeg"] else 0)) / 5) * 5))
        self.set_ctl("tol", tol, f"Colour tolerance {tol}: " + (
            "the picture's colours are clean" if ta["noise"] < 3 else
            f"the picture has some colour noise ({ta['noise']:.1f} on average{', a JPEG' if ta['jpeg'] else ''})")
            + ", so pixels up to that far from the curve's colour still count.")
        k = self.calib()
        if k:
            ta["px_oct"] = abs(k.x(2000) - k.x(1000))
            po = ta["px_oct"]
            ppo = 48 if po >= 48 else 24 if po >= 24 else 12
            self.set_ctl("ppo", ppo, f"{ppo} points per octave: the graph is drawn with {_js_round(po)} pixels per octave"
                         + (", enough for squiglink's own resolution." if ppo == 48 else
                            ", so more points wouldn't add detail."))
            fa, fb = k.f(self.box["x0"]), k.f(self.box["x1"])
            lo, hi = min(fa, fb), max(fa, fb)
            # (a frame drawn a hair inside 20 Hz or 20 kHz still means the whole range)
            fmin = 20 if lo < 21.5 else _js_round(min(lo, 19000))
            fmax = 20000 if hi > 18500 else _js_round(max(hi, fmin + 100))
            self.set_ctl("fmin", fmin, f"Saving {fmt_hz(fmin)} to {fmt_hz(fmax)}: " + (
                "the part of the axis the graph covers." if lo > 21 or hi < 19900 else "the audible range the graph covers."))
            self.set_ctl("fmax", fmax, None)

    def touched(self, k):
        """A control the user changed: theirs (with automatic settings on)."""
        if self.ta["enabled"] and not self.own(k):
            self.ta["manual"].add(k)

    def hand_back(self, k=None):
        if k:
            self.ta["manual"].discard(k)
        else:
            self.ta["manual"].clear()
        if (not k or k == "dashed") and self.ta["enabled"]:
            self.v["dashed"] = bool(self.ta["dashed_found"])
        self.fit_settings()
