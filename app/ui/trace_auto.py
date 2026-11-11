"""The tracer's automatic read of a picture of a graph from a CrinGraph website (graph.hangout.audio and the like),
with no help from the user: no Qt here (NumPy and SciPy), so it runs in any thread. trace_core.auto_read() imports
this module the first time it is used (the app's start and the tray stay light).

auto_read(rgb, ocr_words=None, jpeg=False, name="Traced graph") does it all:
1. find_plot: the grid of the graph in the picture (the whole page or the graph only). The website's 25 frequency
   grid lines (2, 3, 4, 5, 6, 8, 10, 15 in each decade, and 20 kHz) are found by their pattern; the dB grid lines by
   their constant distance.
2. The labels are read with Windows' text reader (ocr_words: ui.ocr.words), each part enlarged a few ways. The labels
   vote: they give the values (the power of ten of the frequency axis, the dB of each grid line), the grid gives the
   positions.
3. A new Tracer on the part of the picture with the graph (a crop), with the grid and the axis values put in.
4. The measurement: the strong color with the most pixels. Its left and right channels make a band; the curve is the
   middle of the band at each column (one line: the line itself).
5. A line in another color (the target line, gray, solid or dashed): a second curve "Target", marked "target": True.
6. Checks: each one passes or fails, with a reason the user reads (in STE). The names start with "axes_" or "trace_"
   (the window opens the tab where the user can correct it).

Every limit here was measured (2026-11-10 and 2026-11-11) on three real pictures and on a drawn look-alike
(tests\\helpers\\website_graph.py; the reviews' 6,592 look-alikes of 420 to 2000 px, PNG and JPEG 85 to 20, with the
stand-in for the text reader): see .claude\\notes\\benchmarks\\BENCHMARKS.md.

Known limits (the picture alone cannot tell; ok can be True with a curve that is not correct). "N dB at P points": the
largest difference from the true average, and the count of points (of about 470) more than 0.5 dB off. "Of K": the
largest of the K look-alikes of that kind:
- A second measurement in the color of the first, or in a near color that touches the band (for example #1a48a0,
  #0d357d, #1a88a0, #3a48c0, #1f4faa, #2a58b0, #1a68a0, #104090, #5a48c0, #4a40b8, #2040a8, #1a48c0, #1a3890, 3 dB
  from the first or crossing it), is read as a part of the band: the curve is the middle of all of them, 1.0 to 1.7 dB
  off (of 432, 404 with ok=True; the largest: 1.68 dB at 474 points, #1a3890, 1000 px, JPEG 60; #5a48c0, 1000 px,
  JPEG 60: 1.56 dB at 274 points). trace_band fails only when they are more than MAX_BAND_DB apart; where its pieces
  are apart from the band, trace_single fails.
- Text in the curve's color on the curve (the legend over the curve) can move the curve there: band() keeps only the
  rows that continue the band, leaves out the columns where level text touches a steep part, and trace_steps fails
  for a large step, but text that lies along the line cannot be told from it. Of 120 legend places for each size,
  PNG, ok=True: 500 px 1.98 dB at 11 points (7 places above 0.5 dB), 700 px 1.56 dB at 6 points (9), 900 px 1.17 dB at
  4 points (14), 1200 px 1.12 dB at 3 points (6), 1600 px 1.10 dB at 1 point (6). With the channels 2 to 4 dB apart
  (of 648, 500 to 1600 px, PNG, JPEG 60 and 50): 1.85 dB at 4 points (900 px, 2 dB apart, PNG), 1.63 dB at 6 points
  (700 px, 3 dB apart, PNG). An orange or pink legend (of 144, 600 and 1000 px): 0.96 dB at 2 points; 1000 px, JPEG 85
  (of 54): 0.89 dB at 4 points.
- Three or more dB labels that the text reader reads wrongly agree with each other when they still give equal steps:
  wrong by the same amount (60, 65, 70 read as 80, 85, 90: 20.03 dB at all points), or with a wrong step (60, 65, 70
  read as 60, 70, 80: 11.67 dB at 441 points). A test of the curve's level would also fail the graphs that other
  websites set to other levels.
- A JPEG moves the curve by a few tenths of a dB at single points (no target and no legend on the curve; of 3,000
  look-alikes of 500 to 1800 px with the channels 1 to 6 dB apart): PNG 0.44 dB or less (of 240), JPEG 85 0.75 dB at
  1 point (of 480; 500 px), JPEG 70 0.35 dB (of 120), JPEG 60 0.68 dB at 3 points (of 320; 1000 px), JPEG 50 0.92 dB
  at 2 points (of 480; 600 px), JPEG 40 0.73 dB at 2 points (of 440; 1400 px), JPEG 30 0.89 dB at 3 points (of 800;
  700 px; also 0.81 dB at 13 points, 1200 px, and 0.77 dB at 16 points, 700 px), JPEG 20 0.76 dB at 4 points (of 120;
  1400 px). A dark background (of 72), JPEG 60: 0.85 dB at 2 points (600 px).
- A target line that touches or comes near the band in a JPEG can move the curve there (of 1,026 look-alikes with a
  target line): 1.25 dB at 5 points (a dashed target 2 dB under the curve, a dB axis of 32 to 72 dB, 700 px, JPEG 30),
  1.04 dB at 48 points (a level target at 47.5 dB, 1 to 9 dB under the curve from 9 to 18 kHz, 1400 px, JPEG 30), 1.00
  dB at 4 points (a solid target 2 dB under the curve, 600 px, JPEG 40), 0.96 dB at 4 points (dashed, 2 dB under, 700
  px, JPEG 30), 0.78 dB at 2 points (a solid target that crosses the curve, 700 px, JPEG 50).
- A level target line across all of the grid can be read as the last dB grid line (the dB axis then ends at the
  line): 0.78 dB at 110 points (a solid target at 72.5 dB, 1400 px, JPEG 20), 0.64 dB at 111 points (67.5 dB, 1200 px,
  JPEG 50). Of 268 look-alikes with a level target: PNG 0.49 dB or less.
- The target line has no points where the band hides it, beside that, at the ends of each traced part and on a short
  traced part. The largest error of a target point (of 882 look-alikes with a target near the curve, across it or
  level, the 144 below not counted): 0.89 dB (72.5 dB, 1400 px, JPEG 20). A target line along gray text or 1 dB from
  its own name ("Sample Target", in its color) goes onto the words for a part (of 144): 1.39 dB at 17 points (a dashed
  target at 48.6 dB, 1000 px, PNG); 7 of the 144 above 1 dB. With few points left it is None (65 of 176 targets near
  or across the curve; 176 of 459 with ok=True in a second set of 512): the user adds the target by hand.
- A noisy picture (random noise with a standard deviation of 6 or 10 levels, 1000 px, PNG; 2 look-alikes) fails
  trace_single, which is not the true cause.
- Some correct JPEG pictures fail trace_curve or trace_gaps (lost_channel, the text rule): of 2,040 JPEG look-alikes
  with the channels 1 to 6 dB apart, 897 give a correct curve with ok=True. The user traces the others by hand.
"""
import collections
import math
import re
import time

import numpy as np
from scipy import ndimage

from ui import ocr
from ui.trace_core import INK, Tracer, db_num, fmt_hz, hz_num, join_words

# The frequency ticks of a CrinGraph graph (its graphtool.js: 2, 3, 4, 5, 6, 8, 10, 15 in each decade, and 20 kHz)
TICKS = [20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 400, 500, 600, 800, 1000, 1500, 2000, 3000, 4000, 5000, 6000,
         8000, 10000, 15000, 20000]
LOGT = np.log10(np.array(TICKS, float) / 20.0)  # 0 .. 3
MIN_TRACED = 0.97   # of the grid's width: the curve must be on this much of it
MAX_GAP = 0.01      # of the grid's width: the longest part with no curve
MAX_BAND_DB = 6.0   # the difference between the two channels that 9 of 10 columns must stay under
STEP_TEXT = 4.0     # a short rise of the band's height, in line widths (height_steps; real pictures: under 3)
STEP_LINE = 2.5     # two lines this far apart, in line widths, that become one line suddenly (height_steps)
# A near piece of the band's color that band() keeps (the other channel, cut from the band by a JPEG break): at least
# this many pixels wide, one run of rows in this share of its columns (under NEAR_LONG_PX wide, and from there), and
# each column at most this many line widths high (less its slope); and the widest piece one run of rows in this share
# of the piece's columns (it lost the channel there). The legend's words of a 600 px graph are pieces of 16 to 19
# pixels with one run in 62 to 81 % of their columns (at 800 px and more each letter is a piece); the channels' pieces
# were 22 pixels or more with 83 to 100 % at 1000 px, but 46 to 84 % for pieces of 97 to 244 pixels at 1000 and
# 1400 px, JPEG 60 and 75 (a JPEG breaks a line of 4 pixels into two runs); the widest piece had one run in 94 to
# 100 % of their columns (a second measurement in a near color: 0 to 68 % for most of its pieces). Measured on the
# look-alike, JPEG 8 to PNG (the piece of 22 pixels, JPEG 8, is left out)
NEAR_PIECE_PX = 24
NEAR_LONG_PX = 72
NEAR_ONE_RUN = (0.85, 0.4)
NEAR_THICK = 4.0
NEAR_ALONE = 0.8
# Two lines of the band this far apart, in dB, that become one line: lost_channel() leaves those columns out (nearer
# lines: the error of the middle is under half of that); with no dB axis, this share of the grid's width (about
# 0.8 dB on a website's usual 40 dB axis). And at least 1.5 line widths (two lines, not one line's edge)
LOST_DB = 1.0
LOST_APART = 0.008
# The ends of each part of the target line that find_target leaves out: this share of the grid's width, and at least
# 3 columns (target_ends)
TARGET_END = 0.003
MAX_PEAKS = 150     # (more line positions than this: not a graph; the fit's time grows with the cube of the count)
# The ways a part of the picture is given to the text reader, in turn: (enlarged so many times, as dark text on white)
TREATMENTS = [(4, False), (6, True), (8, False), (3, True), (5, False), (8, True)]
# The same for each dB label by itself, when the strip of all dB labels did not give sufficient labels: 3 copies of
# the label side by side (measured on the real pictures: the most labels read, and no label read wrongly)
LABEL_TREATMENTS = [(10, True), (8, True), (7, True), (4, False)]
LABEL_COPIES = 3
MIN_LABELS = 3      # labels that agree, for each axis (and at most one against for each 3 that agree)
DB_STEPS = (-5, -10, -2.5, -2, -1)  # dB between grid lines (the first one wins when two fit equally)
# A usual dB axis of a graph of an IEM or headphone (SPL): its smallest span, and the lowest and highest values on it
# (CrinGraph's graphs show about 40 to 80 dB; a scale of 10 dB to 130 dB holds all usual levels, so the span is
# also at most 120 dB)
DB_MIN_SPAN = 15
DB_LOWEST, DB_HIGHEST = 10, 130
# Letters that the text reader gives for digits of the website's font (a zero with a line through it, and 5, 1, 8)
LOOSE = str.maketrans({"e": "0", "o": "0", "O": "0", "Q": "0", "@": "0", "ø": "0", "Ø": "0", "s": "5",
                       "S": "5", "t": "1", "l": "1", "I": "1", "i": "1", "|": "1", "B": "8"})

Check = collections.namedtuple("Check", "name ok reason")
AutoRead = collections.namedtuple("AutoRead", "ok tracer checks curve target points target_points plot seconds")


# ---------------------------------------------------------------- small parts
def background(rgb):
    """The most common color (16 levels on each channel, every second pixel), as the average of its pixels."""
    s = rgb[::2, ::2].reshape(-1, 3).astype(np.int64)
    keys = (s[:, 0] >> 4) << 8 | (s[:, 1] >> 4) << 4 | s[:, 2] >> 4
    k = np.bincount(keys).argmax()
    return s[keys == k].mean(0)


def distance(rgb, c):
    return np.sqrt(((rgb.astype(np.float32) - np.asarray(c, np.float32)) ** 2).sum(-1))


def ridge(d, axis, r=2):
    """How much a pixel stands out from both neighbors r pixels away across a thin line (axis 1: a vertical line)."""
    a = np.roll(d, r, axis)
    b = np.roll(d, -r, axis)
    return d - np.maximum(a, b)


def runs(mask):
    """(start, end) of each run of True in a 1-D array (end not included)."""
    m = np.concatenate(([0], mask.astype(np.int8), [0]))
    e = np.flatnonzero(np.diff(m))
    return list(zip(e[::2], e[1::2]))


def peaks(p, thr, half=2):
    """Local maxima of a profile over thr, as positions between pixels (the centroid of the part over the base)."""
    out = []
    n = len(p)
    for i in range(1, n - 1):
        if p[i] >= thr and p[i] >= p[i - 1] and p[i] > p[i + 1]:
            a, b = max(0, i - half), min(n, i + half + 1)
            w = np.clip(p[a:b], 0, None)
            out.append((float((w * np.arange(a, b)).sum() / w.sum()), float(p[i])))
    return out


def strong_peaks(p, floor):
    """The peaks of a profile that are grid lines: over the noise, and at least a quarter of the 8th highest."""
    noise = float(np.median(np.abs(p))) * 1.4826
    px = peaks(p, max(floor, 4 * noise))
    hs = sorted((q[1] for q in px), reverse=True)
    if len(hs) >= 8:
        px = [q for q in px if q[1] >= 0.25 * hs[7]]
    return px, noise


def tick_fit(xs, min_span):
    """The frequency ticks of a CrinGraph graph among line positions xs: x = a + b * log10(f / 20). Returns
    {"a", "b", "hits", "extra", "err", "resid"} or None (fewer than 15 ticks)."""
    xs = np.asarray(sorted(xs), float)
    best = None
    for i in range(len(xs)):
        for j in range(len(xs) - 1, i, -1):
            span = xs[j] - xs[i]
            if span < min_span:
                break
            tol = max(1.5, span * 0.004)
            pred = xs[i] + span / 3 * LOGT
            dist = np.abs(pred[:, None] - xs[None, :]).min(1)
            hits = int((dist <= tol).sum())
            inside = int(((xs > xs[i] + tol) & (xs < xs[j] - tol)).sum())
            extra = inside - (hits - 2)  # lines between the ends that are no tick
            score = hits - 0.5 * max(0, extra)
            if best is None or score > best["score"]:
                best = {"score": score, "i": i, "j": j, "hits": hits, "extra": extra}
    if not best or best["hits"] < 15:
        return None
    # least squares over the ticks found
    a, b = xs[best["i"]], (xs[best["j"]] - xs[best["i"]]) / 3
    for _ in range(2):
        pred = a + b * LOGT
        k = np.abs(pred[:, None] - xs[None, :]).argmin(1)
        ok = np.abs(pred - xs[k]) <= max(1.5, b * 0.012)
        if ok.sum() < 2:
            return None
        A = np.stack([np.ones(ok.sum()), LOGT[ok]], 1)
        (a, b), *_ = np.linalg.lstsq(A, xs[k][ok], rcond=None)
    resid = np.abs(a + b * LOGT[ok] - xs[k][ok])
    return {"a": float(a), "b": float(b), "hits": int(ok.sum()), "extra": best["extra"], "err": float(resid.max()),
            "resid": [float(v) for v in resid]}


def uniform_rows(py):
    """The dB grid lines among row peaks: the strong ones at one constant distance. Returns [(row, height)] with the
    rows from a straight-line fit, or [] when there is no such set."""
    hs = sorted((q[1] for q in py), reverse=True)
    if len(hs) < 3:
        return []
    st = sorted(q for q in py if q[1] >= 0.4 * hs[2])
    gap = float(np.median(np.diff([q[0] for q in st])))
    if gap < 4:
        return []
    for _ in range(2):
        idx = np.array([round((q[0] - st[0][0]) / gap) for q in st], float)
        if len(set(idx)) < 2:
            return []
        k, p0 = np.polyfit(idx, [q[0] for q in st], 1)
        gap = float(k)
    if gap < 4:
        return []
    keep = [(q, i) for q, i in zip(st, idx) if abs(p0 + gap * i - q[0]) <= max(1.0, 0.1 * gap)]
    if len(keep) < 3:
        return []
    return [(float(p0 + gap * i), q[1]) for q, i in keep]


# ---------------------------------------------------------------- the graph in the picture
def find_plot(rgb):
    """The grid of a CrinGraph graph in a picture (the whole page, or the graph only). Returns {"ok": True, "x0",
    "x1" (the columns of 20 Hz and 20 kHz), "y0", "y1" (the rows where the frequency grid lines start and end),
    "fit" {"a", "b", "hits", "err", ...}, "vx" (the column peaks), "hy" [(row, height)] (the dB grid lines), "bg",
    "noise", "d" (each pixel's distance from the background)}, or {"ok": False, "why": "grid" | "ticks"}. It never
    raises, for a picture of any size."""
    if getattr(rgb, "ndim", 0) != 3 or rgb.shape[2] < 3:  # (also None, or a list: not an array)
        return {"ok": False, "why": "grid", "n": 0}
    H, W = rgb.shape[:2]
    min_len = max(40, int(H * 0.15))
    if H < min_len or W < 40:
        return {"ok": False, "why": "grid", "n": 0}
    rgb = rgb[..., :3]
    bg = background(rgb)
    d = distance(rgb, bg)
    rv = ridge(d, 1)
    smooth = 21
    m = ndimage.uniform_filter1d(rv, smooth, axis=0, mode="nearest")
    noise = float(np.median(np.abs(m - np.median(m)))) * 1.4826
    on = m > max(1.2, 4 * noise)
    cols = [x for x in range(2, W - 2)
            if on[:, x].sum() >= min_len and max(b - a for a, b in runs(on[:, x])) >= min_len]
    if len(cols) < 8:
        return {"ok": False, "why": "grid", "n": len(cols)}
    count = on[:, cols].sum(1)
    rows = runs(count >= max(6, 0.5 * count.max()))
    if not rows:
        return {"ok": False, "why": "grid", "n": len(cols)}
    ya, yb = max(rows, key=lambda r: r[1] - r[0])
    if yb - ya < min_len:
        return {"ok": False, "why": "grid", "n": len(cols)}
    G = [x for x in cols if on[ya:yb, x].mean() >= 0.6]
    if len(G) < 8:
        return {"ok": False, "why": "grid", "n": len(G)}
    # the frequency grid lines, from the median of each column over the rows where the grid surely is
    mg = max(2, (yb - ya) // 20)
    prof = np.median(d[ya + mg:yb - mg], axis=0)
    p = prof - ndimage.median_filter(prof, 31, mode="nearest")
    px, noise = strong_peaks(p, 1.0)
    if len(px) > MAX_PEAKS:
        px = sorted(sorted(px, key=lambda q: -q[1])[:MAX_PEAKS])
    fit = tick_fit([q[0] for q in px], W * 0.3)
    if not fit:
        return {"ok": False, "why": "ticks", "n": len(px), "y0": ya, "y1": yb}
    # the lines' ends: row by row, the share of the 25 tick columns where the line is there (a break of a few rows
    # allowed: a dB grid line or large text across the lines hides them)
    tc = np.clip(np.round(fit["a"] + fit["b"] * LOGT).astype(int), 2, W - 3)
    r = np.maximum(rv[:, tc], np.maximum(rv[:, tc - 1], rv[:, tc + 1]))
    med = np.median(r[ya:yb], axis=0)
    use = med > max(1.0, 2 * noise)
    if use.sum() < 6:
        use = med >= np.sort(med)[-6]
    # (not much stronger than the line either: the labels below the lines are darker than the lines, and the zeros
    # of the labels have a line through them, at the tick's column)
    over = ((r[:, use] > 0.35 * med[use]) & (r[:, use] < 2.5 * med[use] + 3)).mean(1) >= 0.5
    brk = max(2, int(math.ceil(0.012 * fit["b"])))  # (under the space between the lines' ends and the labels)
    y0 = min(ya + smooth, H - 1)
    while y0 > 0 and over[max(0, y0 - brk):y0].any():
        y0 -= 1
    y1 = max(yb - smooth, 0)
    while y1 < H - 1 and over[y1 + 1:y1 + 1 + brk].any():
        y1 += 1
    if y1 - y0 < 8:
        return {"ok": False, "why": "grid", "n": len(cols)}
    x0, x1 = fit["a"], fit["a"] + 3 * fit["b"]
    # the dB grid lines: rows between the lines' ends, from the median of each row between 20 Hz and 20 kHz
    xa, xb = max(0, int(round(x0)) + 3), min(W, int(round(x1)) - 3)
    if xb - xa < 8:
        return {"ok": False, "why": "ticks", "n": len(px), "y0": ya, "y1": yb}
    rp = np.median(d[y0:y1 + 1, xa:xb], axis=1)
    r = rp - ndimage.median_filter(rp, 31, mode="nearest")
    py, _ = strong_peaks(r, 1.0)
    py = uniform_rows([(q[0] + y0, q[1]) for q in py])
    return {"ok": True, "bg": bg, "d": d, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "fit": fit, "vx": px, "hy": py,
            "noise": noise}


# ---------------------------------------------------------------- the labels
def hz_loose(s):
    """hz_num, and when that fails the same with the letters that the text reader gives for the website's digits put
    back as digits ("Ht" or "H2" at the end: "Hz"). Returns (value, strict)."""
    v = hz_num(s)
    if v:
        return v, True
    m = re.fullmatch(r"(.+?)([kK]?)((?:H[zZt2])?)", s)
    if not m or not m.group(1):
        return None, False
    v = hz_num(m.group(1).translate(LOOSE) + m.group(2))
    return (v, False) if v else (None, False)


def db_loose(s):
    v = db_num(s)
    if v is not None:
        return v
    return db_num(s.translate(LOOSE))


def read_strip(rgb, ocr_words, x0, y0, x1, y1, k, gray, copies=1):
    """The words in a part of the picture, in picture coordinates: the part enlarged k times (cubic), as dark text on
    white when gray, with 24 px of edge, given to ocr_words. copies > 1: that many copies of the part side by side,
    with the background's color between them and around them (the text reader often reads no word of two digits
    alone, but reads a line of them); the words of each copy come back at the part's own place, a word across two
    copies is left out. (The tests replace this function.)"""
    H, W = rgb.shape[:2]
    x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(W, int(math.ceil(x1))), min(H, int(math.ceil(y1)))
    if x1 - x0 < 8 or y1 - y0 < 4:
        return []
    a = rgb[y0:y1, x0:x1].astype(np.float32)
    k = max(1.0, min(k, 6000 / max(x1 - x0, y1 - y0) / max(1, copies)))
    bgc = np.median(a.reshape(-1, 3), axis=0)
    # one 2-D zoom for each channel (a 3-D zoom with the factor 1 on the colors was 7 times slower)
    if gray:
        dd = np.sqrt(((a - bgc) ** 2).sum(2))
        dd = np.clip(dd / max(40.0, float(np.percentile(dd, 99.5))), 0, 1)
        one = np.clip(ndimage.zoom(255 * (1 - dd), k, order=3), 0, 255).astype(np.uint8)
        big = np.repeat(one[..., None], 3, axis=2)
        fill = np.full(3, 255, np.uint8)
    else:
        big = np.stack([np.clip(ndimage.zoom(a[..., c], k, order=3), 0, 255).astype(np.uint8) for c in range(3)],
                       axis=2)
        fill = np.clip(np.round(bgc), 0, 255).astype(np.uint8)
    pad = 24
    if copies <= 1:
        big = np.pad(big, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
        return [dict(w, x0=x0 + (w["x0"] - pad) / k, x1=x0 + (w["x1"] - pad) / k,
                     y0=y0 + (w["y0"] - pad) / k, y1=y0 + (w["y1"] - pad) / k) for w in ocr_words(big)]
    h, cw = big.shape[:2]
    step = cw + max(8, h // 2)  # (from one copy to the next, in the enlarged picture)
    out = np.empty((h + 2 * pad, step * (copies - 1) + cw + 2 * pad, 3), np.uint8)
    out[:] = fill
    for i in range(copies):
        out[pad:pad + h, pad + i * step:pad + i * step + cw] = big
    words = []
    for w in ocr_words(out):
        i = int(((w["x0"] + w["x1"]) / 2 - pad) // step)
        dx = pad + i * step
        if not 0 <= i < copies or w["x0"] < dx - 2 or w["x1"] > dx + cw + 2:
            continue  # (outside the copies, or across two of them)
        words.append(dict(w, x0=x0 + (w["x0"] - dx) / k, x1=x0 + (w["x1"] - dx) / k,
                          y0=y0 + (w["y0"] - pad) / k, y1=y0 + (w["y1"] - pad) / k, copy=i))
    return words


def join_copies(ws):
    """join_words for each copy of a part by itself (read_strip's "copy": the copies are at one place)."""
    out = []
    for i in sorted({w.get("copy", 0) for w in ws}):
        out += join_words([w for w in ws if w.get("copy", 0) == i])
    return out


def votes(seen, a, b):
    """The frequency labels against the ticks: each label near a tick votes for the power of ten that its value gives
    against that tick. Returns {"shift", "agree" (the ticks of the winner), "against", "words", "other"}."""
    agree, other = {}, []
    tol_px = max(3.0, 0.012 * 3 * b)
    for s in seen.values():
        # the tick nearest the label's center ("20Hz" and "20kHz" sit inside the grid's ends: their own tolerance)
        lf = (s["x"] - a) / b
        i = int(np.abs(LOGT - lf).argmin())
        off = abs(lf - LOGT[i]) * b
        lim = tol_px * (4 if i in (0, len(TICKS) - 1) else 1)
        ratio = math.log10(s["v"] / TICKS[i])
        if off <= lim and abs(ratio - round(ratio)) < 0.02:
            agree.setdefault(round(ratio), []).append(dict(s, tick=TICKS[i]))
        else:
            other.append(s)
    if not agree:
        return {"shift": None, "agree": [], "against": 0, "words": [], "other": other}
    n = max(agree, key=lambda k: len({q["tick"] for q in agree[k]}))
    return {"shift": n, "agree": sorted({q["tick"] for q in agree[n]}), "other": other,
            "against": sum(len({q["tick"] for q in v}) for k, v in agree.items() if k != n), "words": agree[n]}


def read_hz(rgb, ocr_words, plot):
    """The frequency labels under the grid, compared with the ticks (see votes)."""
    a, b = plot["fit"]["a"], plot["fit"]["b"]
    h = max(16, 0.07 * 3 * b)
    seen = {}
    good = votes(seen, a, b)
    for tries, (k, gray) in enumerate(TREATMENTS, 1):
        k = k * 600.0 / max(600.0, 3 * b)  # (a large picture needs less enlargement)
        for w in join_words(read_strip(rgb, ocr_words, a - 0.12 * b, plot["y1"] + 1, a + 3.12 * b, plot["y1"] + h,
                                       max(1.0, k), gray)):
            v, strict = hz_loose(w["text"])
            if not v:
                continue
            xc = (w["x0"] + w["x1"]) / 2
            seen.setdefault((round(xc / 4), v), {"v": v, "x": xc, "n": 0, "w": w, "strict": strict})["n"] += 1
        good = votes(seen, a, b)
        good["tries"] = tries
        if len(good["agree"]) >= 4:
            break
    return good


def labels_ok(agree, against):
    """The rule for the labels of one axis: 3 or more agree, and at most one for each 3 that agree does not."""
    return agree >= MIN_LABELS and against <= agree / 3


def row_votes(cands):
    """The vote of each dB grid row: the values read there the most times (a strict reading before a loose one with
    the same count). {row: [readings]}; two or more readings when the vote is equal."""
    rows = {}
    for q in cands:
        rows.setdefault(round(q["p"]), []).append(q)
    out = {}
    for r, qs in rows.items():
        top = max(q["n"] for q in qs)
        win = [q for q in qs if q["n"] == top]
        if len(win) > 1 and any(q["strict"] for q in win):
            win = [q for q in win if q["strict"]]
        out[r] = win
    return out


def db_fit(cands, gap):
    """dB = v0 + step * (rows from a label): the step (DB_STEPS: always falling downwards, a label read wrongly must
    not make a rising axis) and start that the most grid rows agree with. Each row has one vote (row_votes): it
    agrees when all of its vote agrees, it is against when its vote has a strict reading that does not agree (a
    reading that only the loose letters make a number is never against: the reader gave "oos" for "65"). Returns
    {"pairs" (one reading for each row that agrees), "against", "rows", "step", "k", "v0", "wrong"}; with fewer than
    2 rows that agree, "pairs" is [] and "single" is the reading of the one row that was read (None for 0 rows or
    for rows that do not agree with each other)."""
    rows = row_votes(cands)
    best = None
    for win in rows.values():
        for c in win:
            for step in DB_STEPS:
                f = lambda p, c=c, step=step: c["v"] + step * (p - c["p"]) / gap
                agree, against = [], 0
                for qs in rows.values():
                    ok = [q for q in qs if abs(f(q["p"]) - q["v"]) < 0.26 * abs(step)]
                    if len(ok) == len(qs):
                        agree.append(max(ok, key=lambda q: q["n"]))
                    elif any(q["strict"] for q in qs if q not in ok):
                        against += 1
                if best is None or (len(agree), -against) > (len(best["pairs"]), -best["against"]):
                    best = {"pairs": sorted(agree, key=lambda q: q["p"]), "step": step, "against": against}
    if not best or len(best["pairs"]) < 2:
        one = list(rows.values())[0] if len(rows) == 1 else []
        return {"pairs": [], "single": one[0] if len(one) == 1 else None, "against": 0, "rows": len(rows),
                "wrong": cands}
    pr = best["pairs"]
    # least squares of dB against the row over the labels that agree
    k, v0 = np.polyfit(np.array([q["p"] for q in pr]), np.array([q["v"] for q in pr]), 1)
    best.update(k=float(k), v0=float(v0), rows=len(rows), wrong=[q for q in cands if q not in pr])
    return best


def read_db(rgb, ocr_words, plot):
    """The dB labels inside the grid at its left edge (each one just above its grid line). First the strip of all
    labels (TREATMENTS); when that does not give labels that pass (labels_ok), each label's part by itself
    (LABEL_TREATMENTS, LABEL_COPIES copies side by side). All readings vote, for each grid row (db_fit). Returns
    db_fit's result with "tries", or None when the grid has fewer than 3 dB grid lines."""
    lines = sorted(q[0] for q in plot["hy"])
    if len(lines) < 3:
        return None
    gap = float(np.median(np.diff(lines)))
    x0, x1 = plot["x0"], plot["x1"]
    xb = x0 + 0.07 * (x1 - x0)
    seen = {}

    def take(ws):
        """One reading of the text reader: each value read at a row counts once."""
        got = {}
        for w in join_copies(ws):
            v = db_loose(w["text"])
            if v is None:
                continue
            yc = (w["y0"] + w["y1"]) / 2
            below = [r for r in lines if -0.2 * gap < r - yc < 0.6 * gap]
            if not below:
                continue
            r = min(below, key=lambda r: abs(r - yc))
            q = got.setdefault((round(r), v), {"p": r, "v": v, "w": w, "strict": False})
            q["strict"] = q["strict"] or db_num(w["text"]) is not None
        for key, q in got.items():
            s = seen.setdefault(key, dict(q, n=0))
            s["n"] += 1
            s["strict"] = s["strict"] or q["strict"]

    def done(best):
        return labels_ok(len(best["pairs"]), best["against"])

    best, tries = None, 0
    for k, gray in TREATMENTS:
        tries += 1
        k = k * 600.0 / max(600.0, x1 - x0)
        take(read_strip(rgb, ocr_words, x0 + 1, plot["y0"], xb, plot["y1"], max(1.0, k), gray))
        best = db_fit(list(seen.values()), gap)
        if done(best):
            break
    else:
        # (each label by itself: the reader reads more of the small labels so, measured on the real pictures)
        for k, gray in LABEL_TREATMENTS:
            tries += 1
            k = k * 600.0 / max(600.0, x1 - x0)
            for r in lines:
                take(read_strip(rgb, ocr_words, x0 + 1, r - 0.7 * gap, xb, r, max(1.0, k), gray, LABEL_COPIES))
            best = db_fit(list(seen.values()), gap)
            if done(best):
                break
    best["tries"] = tries
    return best


# ---------------------------------------------------------------- the curves
def measurement_colour(rgb, plot):
    """The color of the measurement: the hue (twelve bins, with the two beside it) with a strong color in the most
    pixels of the grid, when that is on half of its columns or more. Returns {"colour", "share", "hue", "second"}
    (second: the share of the columns of the strongest other hue, far from the first) or None."""
    x0, x1, y0, y1 = int(plot["x0"]) + 2, int(plot["x1"]) - 1, int(plot["y0"]) + 2, int(plot["y1"]) - 1
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    p = rgb[y0:y1, x0:x1].astype(np.int32)
    chroma = p.max(-1) - p.min(-1)
    strong = (chroma >= 50) & (plot["d"][y0:y1, x0:x1] >= INK)
    if strong.sum() < 20:
        return None
    hb = Tracer.hue_bins(p)
    # (a hue with the two beside it: two near colors, and a JPEG moves a thin line's hue across a bin's edge)
    near = lambda h: strong & ((hb == h) | (hb == (h + 1) % 12) | (hb == (h - 1) % 12))
    own = [int((strong & (hb == h)).sum()) for h in range(12)]
    h = int(np.argmax(own))
    m = near(h)
    share = int(m.any(0).sum()) / (x1 - x0)
    if share < 0.5:
        return None
    # a second measurement: the strongest hue that shares no bin with the first hue's group, and its own group
    far = lambda k: min((k - h) % 12, (h - k) % 12)
    rest = [k for k in range(12) if far(k) >= 3]
    h2 = max(rest, key=lambda k: own[k])
    m2 = strong & np.isin(hb, [k for k in ((h2 - 1) % 12, h2, (h2 + 1) % 12) if far(k) >= 2])
    second = int(m2.any(0).sum()) / (x1 - x0)
    dd = plot["d"][y0:y1, x0:x1][m]
    px = p[m][dd >= np.percentile(dd, 60)]
    return {"colour": tuple(float(v) for v in np.median(px, axis=0)), "share": share, "hue": h, "second": second}


def _piece_rows(lab, sl, i):
    """{column (in the part): (first row, last row)} of piece i (lab's label i + 1)."""
    s = sl[i]
    m = lab[s] == i + 1
    out = {}
    for j in range(m.shape[1]):
        r = np.flatnonzero(m[:, j])
        if len(r):
            out[s[1].start + j] = (int(r[0]) + s[0].start, int(r[-1]) + s[0].start)
    return out


def _gap_to(rows, ref):
    """The rows between a piece and the reference rows, in the columns of both: a list (0 where they overlap)."""
    return [max(0, ref[x][0] - b, a - ref[x][1]) for x, (a, b) in rows.items() if x in ref]


def _piece_cols(lab, sl, i):
    """{column (in the part): (runs of rows, height less the move of its middle from the column before, height of
    the first run)} of piece i (lab's label i + 1)."""
    m = lab[sl[i]] == i + 1
    out, last = {}, None
    for j in range(m.shape[1]):
        rs = runs(m[:, j])
        if not rs:
            last = None
            continue
        h, c = rs[-1][1] - rs[0][0], (rs[-1][1] + rs[0][0]) / 2
        out[sl[i][1].start + j] = (len(rs), h - (abs(c - last) if last is not None else 0.0), rs[0][1] - rs[0][0])
        last = c
    return out


def _piece_form(cols):
    """The form of a piece from _piece_cols: (the share of its columns that have one run of rows, the 90th percentile
    of the columns' height less their slope, the 10th percentile of the height of the first run). A line has one run
    in almost each column, as high as the line's width and its slope; a word has two or three runs in many columns
    (the strokes of its letters)."""
    if len(cols) < 2:
        return 0.0, math.inf, 1.0
    v = np.array(list(cols.values()), float)
    return float(np.mean(v[:, 0] == 1)), float(np.percentile(v[:, 1], 90)), float(np.percentile(v[:, 2], 10))


def _continued(solid, memory, long):
    """The solid rows of each column that continue the band: a run of rows stays when it overlaps the rows of the
    band in the last `memory` columns before it (moved by the band's slope, plus 2 rows and half the slope), and only
    its part within them; at the first column, and after a column with no run that continues, all runs stay. A run
    that does not continue the band but continues itself (in each next column) for `long` columns is a line too (the
    other channel, after a faded end or a break): it stays from its first column. Done from the left and from the
    right: a row stays when it stays both ways. Text that touches the curve starts a new run in a column beside the
    band, or makes a run longer than the band's rows, for a letter's width only: it goes."""
    H, W = solid.shape
    both = np.ones_like(solid)
    for way, order in ((1, range(W)), (-1, range(W - 1, -1, -1))):
        ok = np.zeros_like(solid)
        last = []  # [(column, first row, last row)] of the columns kept just before
        tracks = []  # runs that do not continue the band, each [(column, start, end)] in sequence
        for x in order:
            rs = runs(solid[:, x])
            tracks = [tr for tr in tracks if tr[-1][0] == x - way]
            if not rs:
                continue
            last = [q for q in last if abs(x - q[0]) <= memory]
            if len(last) >= 2:
                # the slope (rows for each column to the right): of the edge that moved less (a line that goes or
                # comes back moves the other edge)
                (xa, aa, ba), (xb, ab, bb) = last[-2], last[-1]
                s = min((ab - aa) / (xb - xa), (bb - ba) / (xb - xa), key=abs)
            else:
                s = 0.0
            g = 2 + 0.5 * abs(s)
            if last:
                step = s * way  # (the rows that the middle moves from one column to the next, on this way)
                lo = min(a + s * (x - q) for q, a, _ in last) + min(0.0, step) - g
                hi = max(b + s * (x - q) for q, _, b in last) + max(0.0, step) + g
                keep = [(max(a, int(math.ceil(lo))), min(b - 1, int(math.floor(hi))) + 1) for a, b in rs
                        if b - 1 >= lo and a <= hi]
                keep = [(a, b) for a, b in keep if b > a]
            else:
                keep = []
            if not keep:
                keep = rs
            for a, b in keep:
                ok[a:b, x] = True
            # the runs (or parts) left out: each continues a track of the column before, or starts one
            for a, b in rs:
                part = [(a, b)] if not any(ka < b and a < kb for ka, kb in keep) else \
                    [(p, q) for p, q in ((a, keep[0][0]), (keep[-1][1], b)) if q - p > 0 and a <= p and q <= b]
                for p, q in part:
                    tr = next((tr for tr in tracks if tr[-1][0] == x - way and tr[-1][1] - 1 <= q and p <= tr[-1][2] + 1
                               and len(tr) < long), None)
                    if tr is None:
                        tracks.append([(x, p, q)])
                    else:
                        tr.append((x, p, q))
                        if len(tr) >= long:
                            for tx, tp, tq in tr:
                                ok[tp:tq, tx] = True
                            keep = keep + [(p, q)]
            keep.sort()
            tracks = [tr for tr in tracks if len(tr) < long]
            last.append((x, keep[0][0], keep[-1][1] - 1))
        both &= ok
    return both


def lost_channel(top, bot, nruns, c1, c2, lw, px_db=None):
    """The columns where the band lost one of its two channels (a JPEG break at a steep part): lost_channel_run on
    each part of the columns with a curve, the parts cut at the gaps longer than MAX_GAP of the width (a shorter gap
    is closed: a channel lost after a short gap, or after the columns that the text rule left out, is found). Returns
    a bool array (band() leaves these columns out: a gap is better than the middle of one channel)."""
    n = len(nruns)
    fin = np.isfinite(c1) & np.isfinite(top) & np.isfinite(bot)
    out = np.zeros(n, bool)
    idx = np.flatnonzero(fin)
    limit = max(3, int(MAX_GAP * n)) + 1
    cuts = [0] + [int(k) + 1 for k in np.flatnonzero(np.diff(idx) > limit)] + [len(idx)]
    for a, b in zip(cuts, cuts[1:]):
        part = idx[a:b]
        if len(part) >= 4:
            got = lost_channel_run(top[part], bot[part], nruns[part], c1[part], c2[part], lw, px_db, n, part)
            out[part[got]] = True
    return out


def lost_channel_run(top, bot, nruns, c1, c2, lw, px_db=None, full=None, cols=None):
    """lost_channel on one part with no long gap (cols: the columns of the part in the band; full: the band's width):
    the band was two lines apart for 3 columns (1.5 line widths, and LOST_DB with px_db pixels for each dB, else
    LOST_APART of the width, or more: nearer lines give a small error), and in the next column the two lines are not
    there (one line, or two runs of one line nearer than 0.6 times as far apart), with the band's middle not in the
    middle of the two lines (two lines that join at a steep part make one high run with its middle between them) and
    the band only as high as one line; from there until the two lines are there again (in 3 columns, two runs 1.5
    line widths or 0.6 times as far apart: a text or a junk run can start it, with lines that are nearer after it), or
    to the end of the part. Done from the left and from the right. Returns a bool array over the part."""
    n = len(nruns)
    cols = np.arange(n) if cols is None else np.asarray(cols)
    fin = np.isfinite(c1) & np.isfinite(top) & np.isfinite(bot)
    two = fin & (nruns >= 2) & (c2 - c1 >= max(1.5 * lw, LOST_DB * px_db if px_db else LOST_APART * (full or n)))
    out = np.zeros(n, bool)
    for way in (1, -1):
        order = list(range(n)) if way == 1 else list(range(n - 1, -1, -1))
        i = 3
        while i < n:
            x = order[i]
            p = [order[i - 3], order[i - 2], order[i - 1]]  # (the 3 columns before, on this way)
            if not (fin[x] and two[p].all()):
                i += 1
                continue
            sep = float(np.median((c2 - c1)[p]))
            one_line = float(np.median((bot - top)[p])) - sep  # (the height of one of the two lines)
            # (two lines again: two runs 0.6 times as far apart, or 1.5 line widths and one line's height: a JPEG
            # splits one steep line into two runs nearer than its height)
            apart = min(0.6 * sep, max(1.5 * lw, one_line))
            back = lambda j, order=order, apart=apart: j < n and fin[order[j]] and nruns[order[j]] >= 2 and \
                c2[order[j]] - c1[order[j]] >= apart  # noqa: E731
            # the middle of the two lines at x: the median of the 3 columns' middles, each moved by the slope, the
            # median of the slopes of the 4 edges (a junk run in one column moves one edge only)
            slope = float(np.median([a_[p[2]] - a_[p[0]] for a_ in (top, bot, c1, c2)])) / (cols[p[2]] - cols[p[0]])
            middle = float(np.median((c1[p] + c2[p]) / 2 + slope * (cols[x] - cols[p])))
            if back(i) or abs((top[x] + bot[x]) / 2 - middle) < 0.3 * sep or bot[x] - top[x] >= one_line + 0.5 * sep:
                i += 1
                continue
            e = i
            while e < n and fin[order[e]] and not (back(e) and back(e + 1) and back(e + 2)):
                e += 1  # (until 3 columns with both lines: a fading line comes and goes)
            for j in range(i, e):
                out[order[j]] = True
            i = e + 1
    return out


def flat_beside_steep(top, bot, lw):
    """The columns where one edge of the band is flat (it moves 1 row or less in 3 columns) and the other moves 2 line
    widths or more for each column (in the 9 columns around them): the flat edge is a line of text (the legend's
    words are level) that touches the curve at a steep part; the two channels of a measurement are almost parallel,
    so both of their edges move. With 3 columns on each side (where the text's end touches the line). Returns a bool
    array (band() leaves these columns out). (The slope of 9 columns: a JPEG break can make an edge flat for 3
    columns where the curve moves 1.2 line widths for each column.)"""
    n = len(top)
    out = np.zeros(n, bool)
    for x in range(4, n - 4):
        t, b = top[x - 1:x + 2], bot[x - 1:x + 2]
        if not (np.isfinite(t).all() and np.isfinite(b).all()):
            continue
        kt, kb = abs(top[x + 4] - top[x - 4]) / 8, abs(bot[x + 4] - bot[x - 4]) / 8  # (NaN: not compared)
        if (np.ptp(t) <= 1 and kb >= 2 * lw) or (np.ptp(b) <= 1 and kt >= 2 * lw):
            out[max(0, x - 3):x + 4] = True
    return out


def faded_ends(top, nruns, c1, c2, lw, px_db=None):
    """The columns at the faded ends of the band that are one line: where the two channels are apart and one is faded
    more than the other, the band there is one line. Where the band just inside the end zone (3 % of the width) is two
    lines apart (2 line widths; with px_db pixels for each dB, LOST_DB as lost_channel if that is nearer, and at least
    1.5 line widths), from the end to the first column with both lines (their middles at least half as far apart as
    there). Returns a bool array (band() leaves these columns out)."""
    n = len(top)
    fin = np.isfinite(top)
    out = np.zeros(n, bool)
    n_end = max(3, int(0.03 * n))
    for direction in (1, -1):
        idx = np.flatnonzero(fin)[::direction]
        ref = idx[n_end:n_end + 10]
        if len(ref) < 4 or np.median(nruns[ref]) < 2:
            continue
        sep = float(np.median((c2 - c1)[ref]))
        if sep < (min(2 * lw, max(1.5 * lw, LOST_DB * px_db)) if px_db else 2 * lw):
            continue
        for x in idx[:n_end]:
            if nruns[x] >= 2 and c2[x] - c1[x] >= 0.5 * sep:
                break
            out[x], fin[x] = True, False
    return out


def short_parts(top):
    """The columns of each part of the curve of 1 or 2 columns with no curve on its two sides, or at an end of the band
    (top: NaN where there is no curve): not a part that the app can trust (between two cuts; measured at the grid's
    edge: one column between two gaps of 10 made a gap of 21 two gaps of 10, and the curve 0.5 dB off there). Returns
    a bool array."""
    out = np.zeros(len(top), bool)
    for a, b in runs(np.isfinite(top)):
        if b - a <= 2:
            out[a:b] = True
    return out


def band(rgb, plot, bg, colour, px_db=None):
    """The measurement curve(s) of one color as a band: at each column its top and bottom edge (between pixels: a
    pixel's center is its index) and the middle. Returns {"x0", "top", "bot", "mid", "first", "c1", "c2", "runs",
    "lw", "cut", "full_top", "full_bot", "cover", "pieces"} or None: arrays over the grid's columns from x0, NaN where
    there is no curve (first: the bottom edge of the first line; c1, c2: the middles of the first and the last line;
    runs: the count of lines in the column; lw: the line's width; cut: {"edge", "ends", "lost", "text", "alone",
    "clipped"}, the count of columns left out for each reason, and of the columns where rows were cut off (clipped:
    text that touches the curve, _continued); full_top, full_bot: the edges before the columns were left out (where
    the band hides a target line); cover: each pixel's share of the color; pieces: the count of pieces kept). Columns
    are left out where the band is one line near the grid's top or bottom row (a channel can go past it: edge), at the
    faded ends until both lines are there (faded_ends: ends), where text touches the curve at a steep part
    (flat_beside_steep: text), where one channel is lost on a stretch (lost_channel: lost), and each part of 1 or 2
    columns between columns with no curve (alone). px_db: the pixels for each dB (from the dB labels), or None."""
    x0, x1, y0, y1 = int(math.floor(plot["x0"])), int(math.ceil(plot["x1"])) + 1, int(plot["y0"]), int(plot["y1"]) + 1
    x0, x1 = max(0, x0), min(rgb.shape[1], x1)
    part = rgb[y0:y1, x0:x1].astype(np.float32)
    v = np.asarray(colour, np.float32) - np.asarray(bg, np.float32)
    vv = float((v * v).sum())
    if part.size == 0 or vv < 1:
        return None
    rel = part - np.asarray(bg, np.float32)
    alpha = (rel * v).sum(2) / vv  # how far from the background towards the color (0 .. 1)
    off = np.sqrt(((rel - alpha[..., None] * v) ** 2).sum(2))  # and how far beside that line of colors
    lim = 10 + 0.14 * math.sqrt(vv) * np.clip(alpha, 0, 1.3)
    cover = np.where(off <= lim, np.clip(alpha, 0, 1), 0.0)
    solid = cover > 0.5
    lab, n = ndimage.label(solid, structure=np.ones((3, 3), int))
    if not n:
        return None
    sl = ndimage.find_objects(lab)
    spans = [s[1].stop - s[1].start for s in sl]
    wide = x1 - x0
    # the widest piece, the wide pieces, the pieces that continue it at the left and right (a faded end, a break at a
    # JPEG block), and the near pieces that have the form of a line (the other channel, cut from it by a break); this
    # leaves out the legend's text (each letter is a piece under 1 % wide; a word of a small picture can be one piece
    # of 2 to 3 %, but not of NEAR_PIECE_PX and with one run in most columns) and the logo
    order = np.argsort(spans)[::-1]
    keep = np.zeros(n + 1, bool)
    main = order[0]
    keep[main + 1] = True
    mrows = _piece_rows(lab, sl, main)
    near = 0.15 * (y1 - y0)
    mcols = lw_main = None
    wide_rows = []  # (the rows of each wide piece kept)
    for i in order[1:]:
        if spans[i] < 0.02 * wide:
            break
        if spans[i] >= 0.25 * wide:
            keep[i + 1] = True
            wide_rows.append(_piece_rows(lab, sl, i))
            continue
        if sl[i][1].start >= sl[main][1].stop - 2 or sl[i][1].stop <= sl[main][1].start + 2:
            # beside the widest piece, but in the columns of a wide piece: only near that piece (a JPEG cuts the
            # lighter channel into pieces, and a word of the legend far below the curve was a part of the band:
            # 10.9 dB off at 11 points, 800 px, JPEG 30)
            gaps = [g for wr in wide_rows for g in _gap_to(_piece_rows(lab, sl, i), wr)]
            if not gaps or float(np.median(gaps)) <= near:
                keep[i + 1] = True
            continue
        if spans[i] < NEAR_PIECE_PX:
            continue
        gaps = _gap_to(_piece_rows(lab, sl, i), mrows)
        if not (len(gaps) >= 0.5 * spans[i] and float(np.median(gaps)) <= near):
            continue
        if mcols is None:
            mcols = _piece_cols(lab, sl, main)
            lw_main = max(1.0, _piece_form(mcols)[2])
        cols = _piece_cols(lab, sl, i)
        one, thick, _first = _piece_form(cols)
        # (and where the widest piece is one run of rows: where it has two, the two channels are there, and a third
        # line near them is a second measurement in a near color, not a channel; the columns of both are never none:
        # the test of the gaps above needs them)
        alone = [mcols[x][0] == 1 for x in cols if x in mcols]
        least = NEAR_ONE_RUN[0] if spans[i] < NEAR_LONG_PX else NEAR_ONE_RUN[1]
        if one >= least and thick <= NEAR_THICK * lw_main and np.mean(alone) >= NEAR_ALONE:
            keep[i + 1] = True
    own = keep[lab]
    own = ndimage.binary_dilation(own, np.ones((3, 3), bool)) & (cover > 0.08)  # with its soft edge pixels
    c = np.where(own, cover, 0.0)
    # in each column only the rows that continue the band of the columns beside it (text in the curve's color that
    # touches the curve is a part of its piece: here it goes); with the soft pixels next to the rows that stay
    solid = c > 0.5
    stay = _continued(solid, max(4, int(0.006 * wide)), max(6, int(0.015 * wide)))
    near_stay = ndimage.binary_dilation(stay, np.ones((7, 1), bool))
    clipped = int((solid.any(0) & (solid & ~stay).any(0)).sum())
    c = np.where(stay | (~solid & near_stay), c, 0.0)
    nan = lambda: np.full(c.shape[1], np.nan)
    top, bot, first, c1, c2 = nan(), nan(), nan(), nan(), nan()
    nruns = np.zeros(c.shape[1], int)
    rows = np.arange(c.shape[0], dtype=float)
    for x in range(c.shape[1]):
        col = c[:, x]
        nz = np.flatnonzero(col > 0.5)
        if not len(nz):
            continue
        a, b = nz[0], nz[-1]
        # the edge between pixels: from the first solid pixel and the two outside it, by how much of each is covered
        top[x] = a + 0.5 - float(col[max(0, a - 2):a + 1].sum()) + y0
        bot[x] = b - 0.5 + float(col[b:b + 3].sum()) + y0
        # the lines (two channels apart: the band is two lines): the bottom edge of the first one, and the middle of
        # the first and the last one (with their soft edges, up to the next line)
        brk = np.flatnonzero(np.diff(nz) > 1)
        e, nxt = (nz[brk[0]], nz[brk[0] + 1]) if len(brk) else (b, b + 3)
        first[x] = e - 0.5 + float(col[e:min(e + 3, nxt)].sum()) + y0
        nruns[x] = len(brk) + 1
        s0, s1 = max(0, a - 2), (min(e + 3, nxt) if len(brk) else b + 3)
        c1[x] = float((col[s0:s1] * rows[s0:s1]).sum() / col[s0:s1].sum()) + y0
        if len(brk):
            la = nz[brk[-1] + 1]
            s0, s1 = max(nz[brk[-1]] + 1, la - 2), b + 3
            c2[x] = float((col[s0:s1] * rows[s0:s1]).sum() / col[s0:s1].sum()) + y0
        else:
            c2[x] = c1[x]
    traced = np.isfinite(top)
    lw = float(np.percentile((first - top)[traced], 10)) if traced.any() else 1.0
    cut = {"edge": 0, "ends": 0, "lost": 0, "text": 0, "alone": 0, "clipped": clipped}
    full_top, full_bot = top.copy(), bot.copy()  # (before the cuts: where the band hides a target line)

    def drop(m, why):
        m = m & np.isfinite(top)
        cut[why] += int(m.sum())
        for a_ in (top, bot, first, c1, c2):
            a_[m] = np.nan
        nruns[m] = 0
    # at the grid's first or last row a part of the band can be past it (a channel that goes out of the grid): near
    # those columns, one line where the other channel (as far away as the lines are apart beside it) would be past the
    # grid's edge is left out (the other channel is out of the grid there). (The columns at the row themselves stay:
    # measured on 492 look-alikes, leaving them out made 23 correct curves fail and no wrong curve fail.)
    at_edge = (top < y0 - 0.5 + lw) | (bot > y1 - 0.5 - lw)
    zone = max(4, int(0.05 * wide))
    edge_cols = np.flatnonzero(at_edge)
    if len(edge_cols):
        two = np.flatnonzero(nruns >= 2)
        out = np.zeros(c.shape[1], bool)
        for x in np.flatnonzero(np.isfinite(top) & (nruns == 1)):
            if not len(two) or np.abs(edge_cols - x).min() > zone:
                continue
            near_two = two[np.abs(two - x) <= zone]
            if not len(near_two):
                continue
            sep = float(np.median((c2 - c1)[near_two]))
            room = min(c1[x] - (y0 - 0.5), (y1 - 0.5) - c1[x])  # (from the line to the nearer edge)
            out[x] = room < sep + lw
        drop(out, "edge")
    drop(faded_ends(top, nruns, c1, c2, lw, px_db), "ends")
    # lost_channel before and after the text rule's cut, both: before it, it finds a channel lost in the text's
    # columns (orange, 1000 px, JPEG 30: 2.02 dB at 29 points with the second only); after it, a channel lost after
    # those columns where they were one high run (cyan, 1800 px, JPEG 20: 1.87 dB at 16 points with the first only)
    text, lost = flat_beside_steep(top, bot, lw), lost_channel(top, bot, nruns, c1, c2, lw, px_db)
    drop(text, "text")
    drop(lost | lost_channel(top, bot, nruns, c1, c2, lw, px_db), "lost")
    drop(short_parts(top), "alone")
    return {"x0": x0, "top": top, "bot": bot, "mid": (top + bot) / 2, "first": first, "c1": c1, "c2": c2,
            "runs": nruns, "lw": lw, "cut": cut, "full_top": full_top, "full_bot": full_bot, "cover": c,
            "pieces": int(keep.sum())}


def height_steps(b):
    """Sudden steps of the band's height that are left after band() (b: its result): [(column of the picture,
    kind)]. "text": a run of 2 to L columns (L: 1.2 % of the width) higher than the columns on both sides of it by
    STEP_TEXT line widths or more (text that touches the curve; the curves of the real pictures stay under 3 line
    widths). "line": where the band was two lines STEP_LINE line widths or more apart, one line only from the next
    column or the one after it, for L columns or more, in the place of one of the two lines, and the band's height
    falls (a channel that is lost; two lines that meet come nearer to each other first, two lines that join at a steep
    part keep the height)."""
    top, bot, runs, c1, c2, lw = b["top"], b["bot"], b["runs"], b["c1"], b["c2"], b["lw"]
    h = bot - top
    n = len(h)
    L = max(3, int(0.012 * n))
    ok = np.isfinite(h)
    out = []
    for a in range(1, n - 2):
        if not (ok[a - 1] and ok[a]):
            continue
        for k in range(2, L + 1):
            e = a + k
            if e >= n or not (ok[e - 1] and ok[e]):
                break
            if h[a:e].min() - max(h[a - 1], h[e]) >= STEP_TEXT * lw:
                out.append((a + b["x0"], "text"))
                break
    for x in range(3, n - L):
        before = range(x - 3, x)
        if not all(ok[j] and runs[j] >= 2 and c2[j] - c1[j] >= STEP_LINE * lw for j in before):
            continue
        for s in (x, x + 1):
            after = range(s, s + L)
            # (the band's height falls by half the distance between the lines, or more: where two lines join at a
            # steep part of the curve, it does not)
            if s + L <= n and all(ok[j] and runs[j] == 1 for j in after) and \
                    h[s] <= h[x - 1] - 0.5 * (c2[x - 1] - c1[x - 1]) and \
                    min(abs(c1[s] - c1[x - 1]), abs(c1[s] - c2[x - 1])) <= lw:
                out.append((s + b["x0"], "line"))
                break
    return out


def target_seeds(t, top, bot, lw):
    """Places where a thin line that is not the measurement and not a grid line crosses a column near the middle:
    [(x, y)], the nearest to the middle first."""
    box = t.box
    width = box["x1"] - box["x0"]
    mid = (box["x0"] + box["x1"]) >> 1
    ticks = [g["p"] for g in t.grid_x]
    rows = [line["pos"] for line in t.h_lines]
    out = []
    for k in range(80):
        x = mid + (1 if k % 2 else -1) * math.ceil(k / 2) * max(1, round(width / 100))
        if x < box["x0"] + 3 or x > box["x1"] - 3 or any(abs(x - p) < 3 for p in ticks):
            continue
        col = t.dbg[box["y0"]:box["y1"] + 1, x] > INK * INK
        e = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
        for a, b in zip(np.flatnonzero(e == 1) + box["y0"], np.flatnonzero(e == -1) - 1 + box["y0"]):
            a, b = int(a), int(b)
            y = (a + b) / 2
            if not (1 <= b - a + 1 <= max(4, 4 * lw)):
                continue
            if np.isfinite(top[x]) and top[x] - 2 <= y <= bot[x] + 2:
                continue  # (the measurement)
            if any(abs(y - r) <= 1.5 for r in rows) and b - a + 1 <= 2:
                continue  # (a dB grid line)
            out.append((x, y))
    return out


def _smooth_parts(xs, ys, lw, width, top=None, bot=None):
    """The points (columns xs, rows ys, in sequence) of a smooth line, without the parts that jump off it: cut where
    two points next to each other are more than 2 + 2 line widths + 0.3 of their distance apart in rows, or more than
    2 % of the width apart in columns; the longest part stays, then each other part (the longest first) whose end is
    near the line of the 10 nearest points that stay (3 rows + a line width + 15 % of the distance), and that is near
    them (2 % of the width) or long itself (3 % of the width: a short part far away, such as a label, is not the
    line). A long part far away also comes out from under the band (top, bot: the band's edges at each column, NaN
    where there is none): its end is 2 % of the width or less from the band, in rows and in columns (the line went
    under the band between the two parts; text far from the band is not the line: measured on the look-alikes, the
    line's parts 0 to 8 rows from the band, gray text 65 rows). Returns (xs, ys)."""
    if len(xs) < 3:
        return xs, ys
    room = max(8, 0.02 * width)

    def from_band(x, y):
        if top is None:
            return True
        cs = np.arange(max(0, int(x - room)), min(len(top), int(x + room) + 1))
        cs = cs[np.isfinite(top[cs])]
        return bool(len(cs)) and float(np.min(np.maximum(0, np.maximum(top[cs] - y, y - bot[cs])))) <= room
    jump = (np.abs(np.diff(ys)) > 2 + 2 * lw + 0.3 * np.diff(xs)) | (np.diff(xs) > room)
    cut = np.flatnonzero(jump) + 1
    parts = [(int(a), int(b)) for a, b in zip(np.concatenate(([0], cut)), np.concatenate((cut, [len(xs)])))]
    parts.sort(key=lambda p: xs[p[0]] - xs[p[1] - 1])
    keep = [parts[0]]
    for a, b in parts[1:]:
        ix = np.concatenate([np.arange(p, q) for p, q in keep])
        kx, ky = xs[ix], ys[ix]
        end = min((a, b - 1), key=lambda e: float(np.min(np.abs(kx - xs[e]))))  # (the end next to the line)
        near = np.argsort(np.abs(kx - xs[end]))[:10]
        if np.ptp(kx[near]) > 0:
            k1, k0 = np.polyfit(kx[near], ky[near], 1)
            pred = k1 * xs[end] + k0
        else:
            pred = float(np.mean(ky[near]))
        dist = float(np.min(np.abs(kx[near] - xs[end])))
        if abs(ys[end] - pred) <= 3 + lw + 0.15 * dist and (dist <= room or (
                xs[b - 1] - xs[a] >= max(10, 0.03 * width) and from_band(xs[end], ys[end]))):
            keep.append((a, b))
    ix = np.sort(np.concatenate([np.arange(p, q) for p, q in keep]))
    return xs[ix], ys[ix]


def target_ends(ys, width):
    """The columns of the target's points ({column: row}) at the ends of each traced part (the parts apart by more
    than 1 % of the width): the first and last TARGET_END of the width, at least 3 columns (follow() goes on past
    where the line goes under the band or ends, onto the band's soft pixels or a word: measured 3.3 dB off at one
    point, 500 px, JPEG 50; 1.3 dB at 4 points, 1200 px, JPEG 30), and all the columns of a part shorter than 4 times
    that or 2 % of the width. find_target leaves them out. Returns a sorted list."""
    kx = sorted(ys)
    trim = max(3, int(math.ceil(TARGET_END * width)))
    out = []
    for part in np.split(np.array(kx, int), np.flatnonzero(np.diff(kx) > max(8, 0.01 * width)) + 1) if kx else []:
        # (a short part is not the line: follow() went onto gray text near the band, 14 dB off at 1 point, 700 px)
        short = part[-1] - part[0] + 1 < max(4 * trim, 0.02 * width)
        out += [int(x) for x in part if short or x - part[0] < trim or part[-1] - x < trim]
    return out


def find_target(t, top, bot, lw):
    """A second line: followed with the Tracer's own follow() (as a dashed line: it continues where the measurement
    hides it), with a color tolerance under its distance from the grid's color. Returns {"ys": {column: y},
    "hidden" (the columns with no point: where the band hides the line, 1.5 line widths beside those, the grid's
    faded ends, each part of 2 % of the width or more on a dB grid row, the ends of each traced part (target_ends),
    and each part of 2 % or more with no line),
    "colour" (the median of the line's pixels), "strong" (a strong color: a second measurement, not a target)} or
    None.
    (Tracer.trace_at is not usable here: it took the color of the measurement near the target line.)"""
    box = t.box
    width = box["x1"] - box["x0"]
    if not t.grid_x or width < 10:
        return None
    rows = [line["pos"] for line in t.h_lines]
    # the grid's color: the median at the frequency grid lines
    gc = np.median(np.concatenate([t.px[box["y0"]:box["y1"], int(round(g["p"]))] for g in t.grid_x]), axis=0)
    tried = []
    for x, y in target_seeds(t, top, bot, lw)[:80]:
        if any(x in g and abs(g[x] - y) <= 3 for g in tried):
            continue
        if len(tried) >= 8:
            break
        ya, yb = max(0, int(math.floor(y - 2))), int(math.ceil(y + 2)) + 1
        col = t.px[ya:yb, x].astype(np.float32)
        c = col[int(np.argmax(((col - np.asarray(t.bg, np.float32)) ** 2).sum(1)))]
        dg = float(np.sqrt(((c - gc) ** 2).sum()))
        if dg < 25:
            continue  # (the grid's own color: a piece of a grid line, or text in that color)
        tol = max(20.0, min(float(t.v["tol"]), 0.6 * dg))
        g = t.follow(x, round(y), tuple(int(v) for v in c), dashed=True, tol=tol)
        if not g or len(g) < 3:
            continue
        tried.append(g)
        cols = np.array(sorted(g))
        gy = np.array([g[k] for k in cols])
        inside = np.isfinite(top[cols]) & (gy >= top[cols] - 1.5) & (gy <= bot[cols] + 1.5)
        if cols[-1] - cols[0] >= 0.85 * width and len(cols) >= 0.35 * width and inside.mean() <= 0.5:
            # the line's color: the median of its pixels (not the seed's pixel only)
            yi = np.clip(np.round(gy).astype(int), 0, t.H - 1)
            pix = t.px[yi, cols].astype(np.float32)
            colour = np.median(pix, axis=0)
            strong = float(colour.max() - colour.min()) >= 50
            # the columns where the line is: its color (the median) within follow()'s tolerance in the pixel or the one
            # above or below; then the parts of the line between its jumps: the longest one, and the ones that
            # continue it (follow() can go onto the labels' or the grid's soft pixels, or onto the measurement where
            # the line is under it; the line itself is smooth)
            best = np.min([np.sqrt(((t.px[np.clip(yi + d, 0, t.H - 1), cols].astype(np.float32) - colour) ** 2).sum(1))
                           for d in (-1, 0, 1)], axis=0)
            good = best <= tol
            # where the band hides the line (the line in the band, or between two columns on the two sides of it),
            # and across a long part with no line: no points there (points() would join the two sides straight)
            m = max(1.5, lw)
            # (the band's faded ends hide the line too: there the band's first and last columns stand for it)
            bt, bb = top.copy(), bot.copy()
            fin = np.flatnonzero(np.isfinite(top))
            fade = max(3, int(0.015 * width))
            if len(fin):
                bt[max(0, fin[0] - fade):fin[0]], bb[max(0, fin[0] - fade):fin[0]] = top[fin[0]], bot[fin[0]]
                bt[fin[-1] + 1:fin[-1] + 1 + fade], bb[fin[-1] + 1:fin[-1] + 1 + fade] = top[fin[-1]], bot[fin[-1]]
            near = lambda x, y, bt=bt, bb=bb, m=m: np.isfinite(bt[x]) and bt[x] - m <= y <= bb[x] + m
            in_band = np.array([near(x, y) for x, y in zip(cols, gy)], bool)
            hidden = {int(x) for x in cols[good & in_band]}
            vx, vy = _smooth_parts(cols[good & ~in_band], gy[good & ~in_band], lw, width, bt, bb)
            for (xa, ya), (xb, yb) in zip(zip(vx[:-1], vy[:-1]), zip(vx[1:], vy[1:])):
                for x in range(int(xa) + 1, int(xb)):
                    if near(x, ya + (yb - ya) * (x - xa) / (xb - xa)):
                        hidden.add(x)
            # beside the hidden columns (where the line comes out from under the band, follow() can stay on the band's
            # soft pixels: measured 1.4 dB off at 2.4 line widths from the band) and at the grid's faded ends (the
            # line is faded there too: measured 1.2 dB off at 21 Hz): no points either
            side = max(2, int(math.ceil(1.5 * lw)))
            hx = np.array(sorted(hidden), int)
            for x in vx:
                x = int(x)
                if (len(hx) and np.abs(hx - x).min() <= side) or not box["x0"] + fade <= x <= box["x1"] - fade:
                    hidden.add(x)
            ys = {int(x): float(y) for x, y in zip(vx, vy) if int(x) not in hidden}
            # a part on a dB grid row for 2 % of the width or more is the grid's line, not the line: follow() can go
            # onto it, or onto its soft edge in a JPEG, where the band hides the target line (measured: a level target
            # in the band's edge, 800 px, JPEG 60: the whole target 2.4 px from a grid row, 3.5 dB off), or from a pale
            # pixel of text (orange channels, 1000 px: a grid line was a target)
            long_gap = max(12, int(0.02 * width))
            on = [x for x in sorted(ys) if rows and min(abs(ys[x] - r) for r in rows) <= max(1.0, 1.5 * lw)]
            for part in np.split(np.array(on, int), np.flatnonzero(np.diff(on) > 3) + 1) if on else []:
                if part[-1] - part[0] >= long_gap:
                    for x in part:
                        del ys[int(x)]
                        hidden.add(int(x))
            for x in target_ends(ys, width):
                del ys[x]
                hidden.add(x)
            # then each long part with no point (2 % of the width)
            kx = sorted(ys)
            for xa, xb in zip(kx, kx[1:]):
                if xb - xa > long_gap:
                    hidden.update(range(xa + 1, xb))
            if strong or len(ys) >= 0.2 * width:
                return {"ys": ys, "hidden": hidden, "colour": tuple(int(round(v)) for v in colour),
                        "strong": strong}
    return None


# ---------------------------------------------------------------- the words of the checks (STE)
def _count(n, one, more):
    return f"{n} {one if n == 1 else more}"


def _agree_words(n, m, what, more="", ok=True):
    """'3 frequency labels agree with the grid lines, and 1 does not.' (a count of one in the singular; more: words
    after "the grid lines"). Not ok (labels_ok): 'Only 2 ... The app must have 3 or more labels that agree.', or
    with too many against, '... Too many labels do not agree.'"""
    s = _count(n, f"{what} label agrees", f"{what} labels agree") + " with the grid lines" + more
    s += f", and {m} {'does' if m == 1 else 'do'} not." if m else "."
    if ok:
        return s
    if n < MIN_LABELS:
        return f"Only {s} The app must have {MIN_LABELS} or more labels that agree."
    return s + " Too many labels do not agree."


def _read_labels(fn, rgb, ocr_words, plot):
    """fn(rgb, ocr_words, plot) (read_hz or read_db), with the text reader's errors caught. Returns (result, why_not):
    why_not None when the labels were read; else the words after "The app did not read the ... labels." ("" with no
    text reader; the user text of ocr.Unavailable as a sentence of its own; a fixed sentence for other errors)."""
    if ocr_words is None:
        return None, ""
    try:
        return fn(rgb, ocr_words, plot), None
    except ocr.Unavailable as e:
        why = str(e).strip()
        return None, (" " + why[:1].upper() + why[1:] + ("" if why.endswith((".", "!", "?")) else ".")) if why else ""
    except Exception:  # noqa: BLE001 - any other error of the text reader: a fixed reason, no error
        return None, " The text reader of Windows gave an error."


# ---------------------------------------------------------------- all of it
def auto_read(rgb, ocr_words=None, jpeg=False, name="Traced graph"):
    """A picture of a graph from a CrinGraph website (the whole page or the graph only; H x W x 3 uint8, already
    scaled to trace_core.MAX_PIXELS) read with no help: see the module's docstring. ocr_words: ui.ocr.words, or None
    (no label is read); an error from it (ocr.Unavailable) becomes a reason. The caller's array is not changed.
    Never raises for a picture that is not a graph (also None, or an array of 1, 2 or 4 dimensions): the check
    "axes_plot" fails, and the Tracer has the whole picture,
    loaded as Tracer.load does. Returns AutoRead(ok, tracer, checks, curve, target, points, target_points, plot,
    seconds): ok when every check passes; tracer: a new Tracer (never None); checks: [Check(name, ok, reason)];
    curve: tracer.curves[0] when it has data; target: the curve marked "target" or None; points and target_points:
    [(Hz, dB)] or None (the dB axis is not known); plot: the crop's box in the picture {"x0", "y0", "x1", "y1"} or
    None. Runs in the caller's thread and touches no window."""
    t0 = time.perf_counter()
    try:
        rgb = np.asarray(rgb)
        if rgb.ndim == 3 and rgb.shape[2] > 3:
            rgb = rgb[..., :3]  # (RGBA: the color channels)
        rgb = np.ascontiguousarray(rgb, np.uint8)
    except (TypeError, ValueError):
        rgb = np.zeros((0, 0, 3), np.uint8)  # (None, or no array of numbers: not a picture)
    checks = []

    def add(key, ok, text):
        checks.append(Check(key, bool(ok), text))

    def result(t, curve=None, target=None, points=None, target_points=None, crop=None):
        return AutoRead(all(c.ok for c in checks), t, checks, curve, target, points, target_points, crop,
                        time.perf_counter() - t0)

    plot = find_plot(rgb)
    if not plot["ok"]:
        add("axes_plot", False, "The app did not find the grid of a graph in this picture." if plot["why"] == "grid"
            else "The app found grid lines, but their positions are not the positions of a graph from the website.")
        t = Tracer()
        if rgb.ndim == 3 and rgb.shape[2] == 3 and rgb.shape[0] and rgb.shape[1]:
            t.load(rgb.copy(), name, jpeg)
        return result(t)
    H, W = rgb.shape[:2]
    fit = plot["fit"]
    pw = plot["x1"] - plot["x0"]
    # the part of the picture to keep: the grid, with its labels below and a small margin
    mx, below = 0.05 * pw, max(18.0, 0.07 * pw)
    cx0, cy0 = max(0, int(plot["x0"] - mx)), max(0, int(plot["y0"] - 0.04 * pw))
    cx1, cy1 = min(W, int(math.ceil(plot["x1"] + mx)) + 1), min(H, int(math.ceil(plot["y1"] + below)) + 1)
    crop_box = {"x0": cx0, "y0": cy0, "x1": cx1, "y1": cy1}
    add("axes_plot", True, f"The app found the graph in the picture. Its grid is {round(pw)} pixels wide.")
    lim = max(1.0, 0.002 * pw)
    good_lines = sum(1 for e in fit["resid"] if e <= lim)
    grid_ok = fit["hits"] >= 22 and fit["err"] <= lim
    add("axes_grid", grid_ok,
        f"{fit['hits']} of 25 frequency grid lines are in the positions of a graph from the website." if grid_ok
        else f"The app found only {good_lines} of the 25 frequency grid lines of a graph from the website.")

    # the labels (on the whole picture: the positions are those of find_plot), each axis in its own try: an error at
    # the dB labels does not lose the frequency labels
    hz, hz_not = _read_labels(read_hz, rgb, ocr_words, plot)
    db, db_not = _read_labels(read_db, rgb, ocr_words, plot)
    shift = hz["shift"] if hz else None
    n_agree = len(hz["agree"]) if hz and shift is not None else 0
    n_against = hz["against"] if hz and shift is not None else 0
    hz_ok = labels_ok(n_agree, n_against)
    if hz_not is not None:
        add("axes_hz_labels", False, "The app did not read the frequency labels." + hz_not)
    elif not n_agree:
        add("axes_hz_labels", False, "The app cannot read the frequency labels. A larger picture can help.")
    else:
        add("axes_hz_labels", hz_ok, _agree_words(n_agree, n_against, "frequency", ok=hz_ok))
    k10 = 10.0 ** shift if hz_ok else 1.0
    f1, f2 = 20 * k10, 20000 * k10
    if not hz_ok:
        add("axes_hz_range", False, "The app cannot make sure that the frequency axis is correct. It set 20 Hz to "
            "20 kHz from the grid lines only.")
    elif shift == 0:
        add("axes_hz_range", True, "The frequency axis is 20 Hz to 20 kHz.")
    else:
        add("axes_hz_range", False, f"The labels give a frequency axis of {fmt_hz(f1)} to {fmt_hz(f2)}. A graph of an "
            "IEM or headphone has 20 Hz to 20 kHz.")

    rows = sorted(q[0] for q in plot["hy"])
    d_at, db_slope, db_words = None, None, []
    if db and len(db["pairs"]) >= 2:
        pr = db["pairs"]
        v0, db_slope = db["v0"], db["k"]
        d_at = lambda p: v0 + db_slope * p
        db_words = [q["w"] for q in pr]
        db_ok = labels_ok(len(pr), db["against"])
        add("axes_db_labels", db_ok,
            _agree_words(len(pr), db["against"], "dB", f" ({abs(db['step']):g} dB between grid lines)", db_ok))
    elif db and db.get("single") and len(rows) >= 2:
        q, gap = db["single"], float(np.median(np.diff(rows)))
        db_slope = -5 / gap
        d_at = lambda p: q["v"] + db_slope * (p - q["p"])
        db_words = [q["w"]]
        add("axes_db_labels", False, "The app read only one dB label. It set 5 dB between grid lines.")
    elif db and db.get("rows", 0) >= 2:
        add("axes_db_labels", False, "The dB labels that the app read do not agree with each other.")
    elif db_not is not None:
        add("axes_db_labels", False, "The app did not read the dB labels." + db_not)
    else:
        add("axes_db_labels", False, "The app cannot read the dB labels. A larger picture can help.")
    if d_at and len(rows) >= 2:
        lo, hi = round(d_at(rows[-1]), 2) + 0.0, round(d_at(rows[0]), 2) + 0.0  # (+ 0.0: no "-0")
        usual = DB_MIN_SPAN <= hi - lo and DB_LOWEST <= lo and hi <= DB_HIGHEST
        add("axes_db_range", usual, f"The dB axis is {lo:g} dB to {hi:g} dB." + (
            "" if usual else " This range is not usual for a graph of an IEM or headphone."))
    else:
        d_at = None
        add("axes_db_range", False, "The app does not know the dB axis.")

    # the Tracer's state, on the part of the picture with the graph
    t = Tracer()
    t.load(np.array(rgb[cy0:cy1, cx0:cx1], np.uint8, copy=True), name, jpeg)
    lx, ly = (lambda x: x - cx0), (lambda y: y - cy0)
    tick_px = [lx(fit["a"] + fit["b"] * v) for v in LOGT]
    line = lambda p: {"pos": float(p), "a": int(math.floor(p)), "b": int(math.ceil(p))}
    t.v_lines = [line(p) for p in tick_px]
    t.h_lines = [line(ly(r)) for r in rows]
    t.grid_x = [{"p": float(p), "v": f * k10} for p, f in zip(tick_px, TICKS)]
    t.box = {"x0": int(round(tick_px[0])), "x1": int(round(tick_px[-1])), "y0": int(ly(plot["y0"])),
             "y1": int(ly(plot["y1"]))}
    t.cal.update(x1=tick_px[0], x2=tick_px[-1])
    t.v.update(f1=f"{f1:g}", f2=f"{f2:g}", every=True)
    if len(rows) >= 2:
        t.cal.update(y1=ly(rows[0]), y2=ly(rows[-1]))
        if d_at:
            t.v.update(d1=f"{round(d_at(rows[0]), 2):g}", d2=f"{round(d_at(rows[-1]), 2):g}")
    # (the green boxes of the window: the labels that the app used, in the crop's coordinates)
    used = [q["w"] for q in (hz or {}).get("words", [])] + db_words
    t.label_words = [dict(w, x0=lx(w["x0"]), x1=lx(w["x1"]), y0=ly(w["y0"]), y1=ly(w["y1"])) for w in used]
    t.axis_note = t.detect_note = " ".join(c.reason for c in checks if c.name in ("axes_hz_range", "axes_db_range"))
    t.fit_settings()

    # the measurement: the band of its color, and the middle of the band
    mc = measurement_colour(rgb, plot)
    b = band(rgb, plot, plot["bg"], mc["colour"], 1 / abs(db_slope) if d_at and db_slope else None) if mc else None
    if not b or not np.isfinite(b["top"]).any():
        add("trace_curve", False, "The app did not find a curve in a strong color.")
        return result(t, crop=crop_box)
    xs = np.arange(len(b["mid"])) + b["x0"] - cx0
    keep = (xs >= 0) & (xs < t.W)

    def crop_cols(a, dy=-cy0):
        out = np.full(t.W, np.nan)
        out[xs[keep]] = a[keep] + dy
        return out
    top, bot, c1, c2 = crop_cols(b["top"]), crop_cols(b["bot"]), crop_cols(b["c1"]), crop_cols(b["c2"])
    runs = crop_cols(b["runs"].astype(float), 0)
    lw = b["lw"]
    curve = t.curves[0]
    curve["ys"][:] = (top + bot) / 2
    curve["colour"] = tuple(int(round(v)) for v in mc["colour"])
    curve["label"] = "Average"
    # traced columns between the first and the last tick
    ca, cb = int(math.ceil(tick_px[0])), int(math.floor(tick_px[-1]))
    inside = np.isfinite(top[max(0, ca):min(t.W, cb + 1)])
    got = float(inside.mean()) if len(inside) else 0.0
    pct = min(100, int(got * 100))
    add("trace_curve", got >= MIN_TRACED, f"The curve is on {pct} % of the width of the grid." if got >= MIN_TRACED
        else f"The curve is on only {pct} % of the width of the grid.")
    cols = np.flatnonzero(inside)
    gap = int(np.diff(cols).max()) - 1 if len(cols) > 1 else 0
    add("trace_gaps", gap <= MAX_GAP * pw, "All of the curve is traced." if gap <= MAX_GAP * pw else
        f"A part of the curve that is {_count(gap, 'pixel', 'pixels')} wide is not traced.")
    traced = np.flatnonzero(np.isfinite(top))
    # the difference between the channels at each column: where they are apart (two lines), the distance between the
    # middles of the two lines (the same for either channel the higher one: the edges of a lighter line are thinner);
    # where they touch (one line), the band's height over one line's width (lw: the 10th percentile of the first
    # line's width, from band)
    apart = np.where(runs[traced] >= 2, c2[traced] - c1[traced], np.clip((bot - top)[traced] - lw, 0, None))
    if d_at:
        e90 = round(float(np.percentile(apart, 90)) * abs(db_slope), 1)
        add("trace_band", e90 <= MAX_BAND_DB,
            f"The difference between the left and right channels is {e90:.1f} dB or less on most of the curve."
            if e90 <= MAX_BAND_DB
            else f"The band of curves is {e90:.1f} dB wide. It can contain more than one measurement.")
    else:
        add("trace_band", False, "The app cannot measure the difference between the channels, because it does not "
            "know the dB axis.")
    steps = height_steps(b)
    if steps:
        at = fmt_hz(20 * k10 * 10 ** ((steps[0][0] - fit["a"]) / fit["b"]))
        add("trace_steps", False, f"The height of the band of curves changes suddenly at {at}. Text in the color of "
            "the curve, or a channel that the app did not find, can cause this.")
    else:
        add("trace_steps", True, "The height of the band of curves has no sudden steps.")
    # a second line: the target line (gray), or one more measurement (a strong color: not one device)
    tg = find_target(t, crop_cols(b["full_top"]), crop_cols(b["full_bot"]), lw)
    target = None
    if tg and not tg["strong"]:
        target = t.new_curve(1)
        target.update(label="Target", colour=tg["colour"], target=True)
        for gx, gy in tg["ys"].items():
            target["ys"][gx] = gy
        t.curves.append(target)
    single = mc["second"] < 0.5 and not (tg and tg["strong"])
    add("trace_single", single, "The picture has one measurement." if single else
        "The picture has more than one measurement. The app used the measurement with the most pixels.")
    points = target_points = None
    if t.calib():
        try:
            points = t.points(curve["ys"])[0]
        except ValueError as e:
            add("trace_points", False, str(e))
        if target is not None:
            try:
                # (no points where the band hides the target line: points() would join its two sides with a straight
                # line there)
                k = t.calib()
                target_points = [(f, v) for f, v in t.points(target["ys"])[0]
                                 if int(round(k.x_at(f))) not in tg["hidden"]] or None
            except ValueError:
                target_points = None  # (the target is not a part of the checks)
    return result(t, curve if Tracer.has_data(curve) else None, target, points, target_points, crop_box)
