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

Every limit here was measured (2026-11-10) on three real pictures and on a drawn look-alike
(tests\\helpers\\website_graph.py): see .claude\\notes\\benchmarks\\BENCHMARKS.md.
"""
import collections
import math
import re
import time

import numpy as np
from scipy import ndimage

from ui.trace_core import INK, Tracer, db_num, fmt_hz, hz_num, join_words

# The frequency ticks of a CrinGraph graph (its graphtool.js: 2, 3, 4, 5, 6, 8, 10, 15 in each decade, and 20 kHz)
TICKS = [20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 400, 500, 600, 800, 1000, 1500, 2000, 3000, 4000, 5000, 6000,
         8000, 10000, 15000, 20000]
LOGT = np.log10(np.array(TICKS, float) / 20.0)  # 0 .. 3
MIN_TRACED = 0.97   # of the grid's width: the curve must be on this much of it
MAX_GAP = 0.01      # of the grid's width: the longest part with no curve
MAX_BAND_DB = 6.0   # the difference between the two channels that 9 of 10 columns must stay under
MAX_PEAKS = 150     # (more line positions than this: not a graph; the fit's time grows with the cube of the count)
# The ways a part of the picture is given to the text reader, in turn: (enlarged so many times, as dark text on white)
TREATMENTS = [(4, False), (6, True), (8, False), (3, True), (5, False), (8, True)]
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
    H, W = rgb.shape[:2]
    min_len = max(40, int(H * 0.15))
    if H < min_len or W < 40 or rgb.ndim != 3 or rgb.shape[2] < 3:
        return {"ok": False, "why": "grid", "n": 0}
    rgb = rgb[..., :3]
    bg = background(rgb)
    d = distance(rgb, bg)
    rv = ridge(d, 1)
    smooth = 21
    m = ndimage.uniform_filter1d(rv, smooth, axis=0, mode="nearest")
    noise = float(np.median(np.abs(m - np.median(m)))) * 1.4826
    on = m > max(1.2, 4 * noise)
    cols = [x for x in range(2, W - 2) if on[:, x].sum() >= min_len and max(b - a for a, b in runs(on[:, x])) >= min_len]
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


def read_strip(rgb, ocr_words, x0, y0, x1, y1, k, gray):
    """The words in a part of the picture, in picture coordinates: the part enlarged k times (cubic), as dark text on
    white when gray, with 24 px of edge, given to ocr_words. (The tests replace this function.)"""
    H, W = rgb.shape[:2]
    x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(W, int(math.ceil(x1))), min(H, int(math.ceil(y1)))
    if x1 - x0 < 8 or y1 - y0 < 4:
        return []
    a = rgb[y0:y1, x0:x1].astype(np.float32)
    k = max(1.0, min(k, 6000 / max(x1 - x0, y1 - y0)))
    # one 2-D zoom for each channel (a 3-D zoom with the factor 1 on the colors was 7 times slower)
    if gray:
        bgc = np.median(a.reshape(-1, 3), axis=0)
        dd = np.sqrt(((a - bgc) ** 2).sum(2))
        dd = np.clip(dd / max(40.0, float(np.percentile(dd, 99.5))), 0, 1)
        one = np.clip(ndimage.zoom(255 * (1 - dd), k, order=3), 0, 255).astype(np.uint8)
        big = np.repeat(one[..., None], 3, axis=2)
    else:
        big = np.stack([np.clip(ndimage.zoom(a[..., c], k, order=3), 0, 255).astype(np.uint8) for c in range(3)], axis=2)
    pad = 24
    big = np.pad(big, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
    return [dict(w, x0=x0 + (w["x0"] - pad) / k, x1=x0 + (w["x1"] - pad) / k,
                 y0=y0 + (w["y0"] - pad) / k, y1=y0 + (w["y1"] - pad) / k) for w in ocr_words(big)]


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


def db_fit(cands, gap):
    """dB = v0 + step * (rows from a label): the step (5, 10, 2.5, 2 or 1 dB between grid lines, always falling
    downwards: a label read wrongly must not make a rising axis) and start that most labels agree with."""
    best = None
    for c in cands:
        for step in (-5, -10, -2.5, -2, -1):
            f = lambda p, c=c, step=step: c["v"] + step * (p - c["p"]) / gap
            inl = {}
            for q in cands:
                if abs(f(q["p"]) - q["v"]) < 0.26 * abs(step):
                    if round(q["p"]) not in inl or q["n"] > inl[round(q["p"])]["n"]:
                        inl[round(q["p"])] = q
            if best is None or len(inl) > len(best["pairs"]):
                best = {"pairs": sorted(inl.values(), key=lambda q: q["p"]), "step": step, "c": c}
    if not best or len(best["pairs"]) < 2:
        return {"pairs": [], "single": max(cands, key=lambda q: q["n"]) if cands else None, "wrong": cands}
    pr = best["pairs"]
    # least squares of dB against the row over the labels that agree
    k, v0 = np.polyfit(np.array([q["p"] for q in pr]), np.array([q["v"] for q in pr]), 1)
    best.update(k=float(k), v0=float(v0), wrong=[q for q in cands if q not in pr])
    return best


def read_db(rgb, ocr_words, plot):
    """The dB labels inside the grid at its left edge (each one just above its grid line). Returns db_fit's result
    with "tries", or None when the grid has fewer than 3 dB grid lines."""
    lines = sorted(q[0] for q in plot["hy"])
    if len(lines) < 3:
        return None
    gap = float(np.median(np.diff(lines)))
    x0, x1 = plot["x0"], plot["x1"]
    seen = {}
    best = None
    for tries, (k, gray) in enumerate(TREATMENTS, 1):
        k = k * 600.0 / max(600.0, x1 - x0)
        ws = read_strip(rgb, ocr_words, x0 + 1, plot["y0"], x0 + 0.07 * (x1 - x0), plot["y1"], max(1.0, k), gray)
        for w in join_words(ws):
            v = db_loose(w["text"])
            if v is None:
                continue
            yc = (w["y0"] + w["y1"]) / 2
            below = [r for r in lines if -0.2 * gap < r - yc < 0.6 * gap]
            if not below:
                continue
            r = min(below, key=lambda r: abs(r - yc))
            seen.setdefault((round(r), v), {"p": r, "v": v, "n": 0, "w": w, "strict": db_num(w["text"]) is not None})["n"] += 1
        best = db_fit(list(seen.values()), gap)
        best["tries"] = tries
        if len(best["pairs"]) >= 3:
            break
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


def band(rgb, plot, bg, colour):
    """The measurement curve(s) of one color as a band: at each column its top and bottom edge (between pixels: a
    pixel's center is its index) and the middle. Returns {"x0", "top", "bot", "mid", "cover", "pieces"} (arrays over
    the grid's columns from x0, NaN where there is no curve) or None."""
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
    # the widest piece, the wide pieces, and the pieces that continue it at the left and right (a faded end, a break
    # at a JPEG block); this leaves out the legend's text and the logo
    order = np.argsort(spans)[::-1]
    keep = np.zeros(n + 1, bool)
    main = order[0]
    keep[main + 1] = True
    for i in order[1:]:
        if spans[i] >= 0.25 * (x1 - x0) or spans[i] >= 0.02 * (x1 - x0) and (
                sl[i][1].start >= sl[main][1].stop - 2 or sl[i][1].stop <= sl[main][1].start + 2):
            keep[i + 1] = True
    own = keep[lab]
    own = ndimage.binary_dilation(own, np.ones((3, 3), bool)) & (cover > 0.08)  # with its soft edge pixels
    c = np.where(own, cover, 0.0)
    top = np.full(c.shape[1], np.nan)
    bot = np.full(c.shape[1], np.nan)
    first = np.full(c.shape[1], np.nan)
    for x in range(c.shape[1]):
        col = c[:, x]
        nz = np.flatnonzero(col > 0.5)
        if not len(nz):
            continue
        a, b = nz[0], nz[-1]
        # the edge between pixels: from the first solid pixel and the two outside it, by how much of each is covered
        top[x] = a + 0.5 - float(col[max(0, a - 2):a + 1].sum()) + y0
        bot[x] = b - 0.5 + float(col[b:b + 3].sum()) + y0
        # the bottom edge of the first solid run (two channels apart: the band is two lines, this is one of them)
        brk = np.flatnonzero(np.diff(nz) > 1)
        e, nxt = (nz[brk[0]], nz[brk[0] + 1]) if len(brk) else (b, b + 3)
        first[x] = e - 0.5 + float(col[e:min(e + 3, nxt)].sum()) + y0
    return {"x0": x0, "top": top, "bot": bot, "mid": (top + bot) / 2, "first": first, "cover": c,
            "pieces": int(keep.sum())}


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


def find_target(t, top, bot, lw):
    """A second line: followed with the Tracer's own follow() (as a dashed line: it continues where the measurement
    hides it), with a color tolerance under its distance from the grid's color. Returns {"ys": {column: y},
    "colour", "strong" (a strong color: a second measurement, not a target)} or None. (Tracer.trace_at is not usable
    here: it took the color of the measurement near the target line.)"""
    box = t.box
    width = box["x1"] - box["x0"]
    if not t.grid_x or width < 10:
        return None
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
            return {"ys": g, "colour": tuple(int(v) for v in c), "strong": float(c.max() - c.min()) >= 50}
    return None


# ---------------------------------------------------------------- the words of the checks (STE)
def _count(n, one, more):
    return f"{n} {one if n == 1 else more}"


def _agree_words(n, m, what, more=""):
    """'3 frequency labels agree with the grid lines, and 1 does not.' (a count of one in the singular; more: words
    after "the grid lines")"""
    s = _count(n, f"{what} label agrees", f"{what} labels agree") + " with the grid lines" + more
    return s + (f", and {m} {'does' if m == 1 else 'do'} not." if m else ".")


# ---------------------------------------------------------------- all of it
def auto_read(rgb, ocr_words=None, jpeg=False, name="Traced graph"):
    """A picture of a graph from a CrinGraph website (the whole page or the graph only; H x W x 3 uint8, already
    scaled to trace_core.MAX_PIXELS) read with no help: see the module's docstring. ocr_words: ui.ocr.words, or None
    (no label is read); an error from it (ocr.Unavailable) becomes a reason. The caller's array is not changed.
    Never raises for a picture that is not a graph: the check "axes_plot" fails, and the Tracer has the whole picture,
    loaded as Tracer.load does. Returns AutoRead(ok, tracer, checks, curve, target, points, target_points, plot,
    seconds): ok when every check passes; tracer: a new Tracer (never None); checks: [Check(name, ok, reason)];
    curve: tracer.curves[0] when it has data; target: the curve marked "target" or None; points and target_points:
    [(Hz, dB)] or None (the dB axis is not known); plot: the crop's box in the picture {"x0", "y0", "x1", "y1"} or
    None. Runs in the caller's thread and touches no window."""
    t0 = time.perf_counter()
    rgb = np.ascontiguousarray(rgb, np.uint8)
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
        if rgb.ndim == 3 and rgb.shape[0] and rgb.shape[1]:
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
    add("axes_grid", grid_ok, f"{fit['hits']} of 25 frequency grid lines are in the positions of a graph from the website."
        if grid_ok else f"The app found only {good_lines} of the 25 frequency grid lines of a graph from the website.")

    # the labels (on the whole picture: the positions are those of find_plot)
    hz = db = None
    why_not = None  # (the labels were not read: "" with no cause, else the cause)
    if ocr_words is None:
        why_not = ""
    else:
        try:
            hz = read_hz(rgb, ocr_words, plot)
            db = read_db(rgb, ocr_words, plot)
        except Exception as e:  # noqa: BLE001 - ocr.Unavailable, or any error of the text reader: a reason, no error
            why_not = str(e).strip()
    cause = f" ({why_not})" if why_not else ""
    shift = hz["shift"] if hz else None
    n_agree = len(hz["agree"]) if hz and shift is not None else 0
    n_against = hz["against"] if hz and shift is not None else 0
    hz_ok = n_agree >= 3 and n_against <= n_agree / 3
    if why_not is not None:
        add("axes_hz_labels", False, "The app did not read the frequency labels." + cause)
    elif not n_agree:
        add("axes_hz_labels", False, "The app cannot read the frequency labels. A larger picture can help.")
    else:
        add("axes_hz_labels", hz_ok, _agree_words(n_agree, n_against, "frequency"))
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
        # (a label that only the loose letters make a number counts when it agrees, never against)
        against = len({round(q["p"]) for q in db["wrong"] if q["strict"]} - {round(q["p"]) for q in pr})
        v0, db_slope = db["v0"], db["k"]
        d_at = lambda p: v0 + db_slope * p
        db_words = [q["w"] for q in pr]
        add("axes_db_labels", len(pr) > against,
            _agree_words(len(pr), against, "dB", f" ({abs(db['step']):g} dB between grid lines)"))
    elif db and db.get("single") and len(rows) >= 2:
        q, gap = db["single"], float(np.median(np.diff(rows)))
        db_slope = -5 / gap
        d_at = lambda p: q["v"] + db_slope * (p - q["p"])
        db_words = [q["w"]]
        add("axes_db_labels", False, "The app read only one dB label. It set 5 dB between grid lines.")
    elif why_not is not None:
        add("axes_db_labels", False, "The app did not read the dB labels." + cause)
    else:
        add("axes_db_labels", False, "The app cannot read the dB labels. A larger picture can help.")
    if d_at and len(rows) >= 2:
        lo, hi = round(d_at(rows[-1]), 2), round(d_at(rows[0]), 2)
        span = abs(hi - lo)
        add("axes_db_range", 15 <= span <= 120, f"The dB axis is {lo:g} dB to {hi:g} dB." + (
            "" if 15 <= span <= 120 else " This range is not usual for a graph of an IEM or headphone."))
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
    b = band(rgb, plot, plot["bg"], mc["colour"]) if mc else None
    if not b or not np.isfinite(b["top"]).any():
        add("trace_curve", False, "The app did not find a curve in a strong color.")
        return result(t, crop=crop_box)
    top = np.full(t.W, np.nan)
    bot = np.full(t.W, np.nan)
    xs = np.arange(len(b["mid"])) + b["x0"] - cx0
    keep = (xs >= 0) & (xs < t.W)
    top[xs[keep]], bot[xs[keep]] = b["top"][keep] - cy0, b["bot"][keep] - cy0
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
    thick = (bot - top)[traced]
    # the line's width: the 10th percentile of the first line's width (where the channels touch, the band's width;
    # where they are apart, one channel's line: with two channels apart everywhere the band's width would be all
    # of the difference)
    one = np.full(t.W, np.nan)
    one[xs[keep]] = b["first"][keep] - b["top"][keep]
    lw = float(np.percentile(one[traced], 10))
    if d_at:
        extra = np.clip(thick - lw, 0, None)
        e90 = round(float(np.percentile(extra, 90)) * abs(db_slope), 1)
        add("trace_band", e90 <= MAX_BAND_DB,
            f"The difference between the left and right channels is {e90:.1f} dB or less on most of the curve."
            if e90 <= MAX_BAND_DB else f"The band of curves is {e90:.1f} dB wide. It can contain more than one measurement.")
    else:
        add("trace_band", False, "The app cannot measure the difference between the channels, because it does not "
            "know the dB axis.")
    # a second line: the target line (gray), or one more measurement (a strong color: not one device)
    tg = find_target(t, top, bot, lw)
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
                target_points = t.points(target["ys"])[0]
            except ValueError:
                target_points = None  # (the target is not a part of the checks)
    return result(t, curve if Tracer.has_data(curve) else None, target, points, target_points, crop_box)
