"""Automatic settings: fitted to the measurement, the target and the EQ method. One search (1.0.8, the user's ask
2026-10-13: Quick, Standard and Thorough all took seconds once Best fit grew its EQs, and one search trying every
limit the three tried found the fewest filters for every IEM tested: the benchmarks in BENCHMARKS.md). Before: a speed-
accuracy slider (to 1.0.5), then Quick, Standard or Thorough (1.0.6-1.0.7). The website's sweep searches as
Standard did (the slider's middle: SEARCH).

analyse()       looks at the curves once (after they load): how far the scored range can reasonably go, how much
                boost and cut the correction needs, how many peaks and dips it has and how narrow they are, and
                whether the bass or treble is off as a whole (shelves).
plan()          turns that into values for the current method: the filter counts up to where fits stop improving
                (32 filters; the website's 20 rows), the boost, cut and Q limits the curves need, shelves; the pick
                (picking()). What the measurement says (range, boost, Q, shelves) sets them.

Rules for manual changes: a setting the user changed is listed in auto.manual and keeps its value through new
measurements or targets, until it is handed back ("↺"). With auto.enabled off nothing changes by itself.
Every value made here stays within the setting's floor and ceiling (settings.LIMITS).
"""
import copy
import hashlib
import json
import math
import os
import re

import numpy as np

from . import layouts
from . import paths
from . import pipeline
from . import settings
import textfile

SEARCH = 0.5      # how widely the website's sweep (and Best fit fitting each count on its own) searches: the old
# slider's middle (Standard), 0-1. Best fit growing tries what 0.5 and 1 did together (_Plan.best_fit)
N_ACCURACY = 16   # the most the filter-need estimate says (it sets Website AutoEQ one run's rows; the benchmarks'
# filter-count results were made with it). Not a cap on the result's filters.
EAR_DB = 0.25     # dB: the audible limit (picking())
BAND_OPTS = (8000, 10000, 12000, 16000, 20000)
SITE_FH_OPTS = (6000, 8000, 10000, 12000, 16000, 20000)


def _lim(path):
    lim = settings.LIMITS.get(path) or settings.LIMITS.get(path.rsplit(".", 1)[0]) or {}
    return lim.get("min", -math.inf), lim.get("max", math.inf)


def _fit(path, v, step=1):
    """v rounded to a step (whole numbers by default) and kept within the setting's floor and ceiling."""
    lo, hi = _lim(path)
    r = min(max(round(v / step) * step, lo), hi)
    return int(r) if step == 1 else round(r, 3)


def _past(path, a, up):
    """A round value just above (up) or below a, within the setting's floor and ceiling: frequencies a quarter
    further (in round hundreds or thousands), gains 1 dB, Q 0.5."""
    lo, hi = _lim(path)
    unit = (settings.LIMITS.get(path) or {}).get("unit")
    if unit == "Hz":
        step = 1000 if a >= 2000 else 100 if a >= 200 else 10
        x = math.ceil(a * 1.25 / step) * step if up else math.floor(a / 1.25 / step) * step
    elif unit == "dB":
        x = math.floor(a) + 1 if up else math.ceil(a) - 1
    else:
        x = math.floor(a * 2) / 2 + 0.5 if up else math.ceil(a * 2) / 2 - 0.5
    return min(max(x, lo), hi)


def _consistent(cfg, v, notes):
    """An automatic value next to a "from" or "to" value the user set stays on its side of it (e.g. "Score from"
    set to 12 kHz while the automatic "to" would be 10 kHz: "to" moves up to 15 kHz), so every pair stays in order."""
    manual = set(cfg["auto"].get("manual") or [])
    auto = lambda p: p in v and p not in manual
    get = lambda p: v[p] if auto(p) else settings.get_path(cfg, p)
    for lo, hi, strict in settings.LIMIT_PAIRS:
        a, b = get(lo), get(hi)
        if a is None or b is None or auto(lo) == auto(hi):
            continue
        ok = lambda x, y, strict=strict: x < y or (not strict and x == y)
        if auto(hi):
            new = ([x for x in b if ok(a, x)] or [_past(hi, a, True)]) if isinstance(b, list) else \
                b if ok(a, b) else _past(hi, a, True)
            if new != b and ok(a, min(new) if isinstance(new, list) else new):
                v[hi] = new
                notes.append((hi, f"Kept above your “from” value ({a:g})."))
        else:
            bm = min(b) if isinstance(b, list) else b
            if not ok(a, bm) and ok(_past(lo, bm, False), bm):
                v[lo] = _past(lo, bm, False)
                notes.append((lo, f"Kept below your “to” value ({bm:g})."))


# ---------------------------------------------------------------- looking at the curves
def _smooth(y, octaves):
    """Moving average over a width in octaves on squiglink's 1/48-octave grid."""
    n = max(1, int(round(48 * octaves / 2)))
    return np.convolve(np.pad(y, n, mode="edge"), np.ones(2 * n + 1) / (2 * n + 1), mode="valid")


def _file_top(text):
    """Highest frequency with data in a measurement file."""
    top = 0.0
    for m in re.finditer(r"^\s*([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?\d+)?)[\s,;]+[-+0-9.]", text, re.M):
        top = max(top, float(m.group(1)))
    return top or 20000.0


def _octaves_to_q(n):
    n = max(n, 1e-3)
    return math.sqrt(2 ** n) / (2 ** n - 1)


def analysis_key(cfg, meas_texts, target_text):
    """What analyse() depends on, as one string: the curves' texts, the settings that shape them, and the scored
    range where it counts (its start; its end when you set it or automatic settings are off)."""
    auto = cfg.get("auto") or {}
    band = cfg["scoring"]["band_hz"]
    own_top = not auto.get("enabled", True) or "scoring.band_hz.1" in (auto.get("manual") or [])
    blob = json.dumps([meas_texts, target_text, cfg["site"], cfg.get("target_adjust"), band[0],
                       band[1] if own_top else None, bool(auto.get("enabled", True))], sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8", "replace")).hexdigest()


def analyse(cfg, curves, meas_texts):
    """JSON-safe description of what the EQ has to do."""
    from scipy.signal import find_peaks, peak_widths
    f, meas, tgt = curves["f"], curves["meas"], curves["target"]
    ch = [np.asarray(c) for c in curves["channels"]]
    out = {"n_files": len(ch), "data_top": round(min(_file_top(t) for t in meas_texts))}

    # where the seatings/channels stop agreeing (each levelled over 300 Hz–3 kHz first)
    spread = None
    if len(ch) >= 2:
        mid = (f >= 300) & (f <= 3000)
        m = np.array([c - (c[mid].mean() - ch[0][mid].mean()) for c in ch])
        spread = _smooth(m.std(axis=0), 1 / 3)
        hi = f >= 5000
        bad = hi & (spread > 2.0)
        out["unstable_from"] = round(float(f[np.argmax(bad)])) if bad.any() else None
        out["agree_to"] = max([b for b in BAND_OPTS if (spread[(f >= 5000) & (f <= b)] <= 1.5).all()] or [0]) or None
    else:
        out["unstable_from"] = out["agree_to"] = None

    # the scored range
    top, why = 10000, "default"
    if out["agree_to"] and len(ch) >= 4 and out["agree_to"] >= 12000:
        top, why = min(out["agree_to"], 16000), "agree"
    if out["unstable_from"] and out["unstable_from"] < top:
        top, why = max([b for b in BAND_OPTS if b <= out["unstable_from"]] or [8000]), "unstable"
    if out["data_top"] < top * 0.98:
        top, why = max([b for b in BAND_OPTS if b <= out["data_top"] * 1.02] or [max(2000, int(out["data_top"] // 1000) * 1000)]), "data"
    out["band_top"], out["band_why"] = int(top), why
    # the range actually scored: the user's own "Score to" when they set it (or automatic settings are off)
    auto = cfg.get("auto") or {}
    lo = float(cfg["scoring"]["band_hz"][0])
    if not auto.get("enabled", True) or "scoring.band_hz.1" in (auto.get("manual") or []):
        top = float(cfg["scoring"]["band_hz"][1])
    elif top <= lo:  # the user's "Score from" is above the automatic "to": plan() moves "to" up the same way
        top = _past("scoring.band_hz.1", lo, True)
    out["score_top"] = int(top)

    # the correction: target minus measurement over the scored range (all of it if that range has no data)
    band = (f >= lo) & (f <= top)
    if band.sum() < 3:
        band = np.ones_like(f, dtype=bool)
    dev = _smooth(tgt - meas, 1 / 12)
    d = dev[band]
    fb = f[band]
    i_up, i_dn = int(np.argmax(d)), int(np.argmin(d))
    out["need_boost"] = round(max(0.0, float(d[i_up])), 2)
    out["boost_at"] = round(float(fb[i_up]))
    out["need_cut"] = round(min(0.0, float(d[i_dn])), 2)
    out["cut_at"] = round(float(fb[i_dn]))
    feats, qs = [], []
    for sign in (1, -1):
        pk, pr = find_peaks(sign * d, prominence=1.0)
        feats += list(pk)
        big = pk[pr["prominences"] >= 2.0]
        if len(big):
            w = peak_widths(sign * d, big, rel_height=0.5)[0]
            qs += [(_octaves_to_q(wi / 48), float(fb[p])) for wi, p in zip(w, big)]
    out["features"] = len(feats)
    q, qf = max(qs) if qs else (1.0, None)
    out["q_need"], out["q_at"] = round(q, 2), (round(qf) if qf else None)

    # broad offsets: bass (below ~100 Hz) and treble (top third of the range) against the midrange
    def mean(a, b):
        m = (f >= a) & (f <= b)
        return float((tgt - meas)[m].mean())
    mids = mean(300, 1000)
    out["bass_step"] = round(mean(20, 100) - mids, 2)
    out["treble_step"] = round(mean(top * 0.6, top) - mean(1000, 3000), 2) if top >= 12000 else 0.0
    out["no_eq_rms"] = round(float(np.sqrt(np.mean((meas[band] - tgt[band]) ** 2))), 3)
    return out


# ---------------------------------------------------------------- settings from the analysis
def _take(ladder, k, top):
    out = []
    for v in ladder:
        if v <= top + 1e-9 and v not in out:
            out.append(v)
        if len(out) >= k:
            break
    return sorted(out)


def _r(x):
    """Round halves up (Python's round() rounds halves to even)."""
    return int(math.floor(x + 0.5))


def _fmt_hz(v):
    return f"{round(v / 1000, 1):g} kHz" if v >= 1000 else f"{round(v):g} Hz"


class _Plan:
    """The automatic values for one EQ method, each with its reason (plan() below)."""

    def __init__(self, cfg, an):
        self.cfg, self.an = cfg, an
        self.L = SEARCH  # (how widely: 0 was Quick, 0.5 Standard, 1 Thorough)
        self.values, self.notes = {}, []
        self.span = an.get("score_top", an["band_top"])  # the range actually scored (the user's own, if they set it)
        # How many filters the correction needs: calibrated on best fits of real measurements (the count that gets
        # within 0.1 dB of the best error was about 1.6 × the peaks and dips + 2, more when the curve is far off).
        self.n_need = int(min(N_ACCURACY, max(6, _r(1.6 * an["features"] + 2 + an["no_eq_rms"] / 3))))

    def note(self, path, text):
        self.notes.append((path, text))

    # ---- limits from the analysis
    def counts(self, Ls, path):
        """The filter counts (or website rows) to try at search width Ls (SEARCH; the old Quick 0, Standard 0.5,
        Thorough 1): up to the setting's ceiling (where fits stop improving, or the website's rows); every one from
        0.67, every one to 16 then every other to 24 from 0.34, else every other to 12 then every 4th (the fits with
        many filters take longest)."""
        top = int(_lim(path)[1])
        # Best fit: every count where the audible pick lands (11-21 filters in the tests: a count skipped there made
        # it take a bigger one, once 32) at every level, and every count when the EQs are grown (each count is made on
        # the way to the next anyway); the website's rows as before
        from . import engines
        dense = path.startswith("best_fit")
        if dense and engines.grows(self.cfg["best_fit"]) or Ls >= 0.67:
            c = range(1, top + 1)
        elif Ls >= 0.34:
            c = [*range(1, 25), *range(28, top + 1, 4)] if dense else [*range(1, 17), *range(18, 25, 2), *range(28, top + 1, 4)]
        else:
            c = [*range(2, 13, 2), *range(13, 23), *range(24, top + 1, 4)] if dense else [*range(2, 13, 2), *range(16, top + 1, 4)]
        return sorted({n for n in c if n <= top} | {top})

    def gain_top(self, path):  # boost: what the target needs + 2 dB (at least 4)
        return _fit(path, math.ceil(max(4.0, self.an["need_boost"] + 2)))

    def cut_floor(self, path):  # cut: what it needs + 2 dB (at least 6)
        return _fit(path, -math.ceil(max(6.0, -self.an["need_cut"] + 2)))

    def q_top(self, path):  # Q: the narrowest peak or dip's, plus a quarter (at least 2)
        return _fit(path, max(2.0, self.an["q_need"] * 1.25), 0.5)

    def q_list(self, qt, Ls, path, k):
        """The Q limits to try. Tested on real measurements: with few filters Q 2 does best; with 8-16 filters
        Q 3-5 match closer (on other units and seatings too), while Q 8-16 do worse again. So the wider the search
        the ladder reaches Q 3 (from 0.34) and 5 (from 0.67) whatever the narrowest peak is."""
        hi = qt if Ls < 0.34 else _fit(path, max(qt, 3.0 if Ls < 0.67 else 5.0), 0.5)
        ladder = [qt, 2, 1, 3, 1.5] if Ls < 0.34 else [hi, qt, 2, 1, 1.5] if Ls < 0.67 else [hi, 3, 4, qt, 2]
        return _take([_fit(path, q, 0.5) for q in ladder], k, hi), hi

    # ---- the reasons
    def note_filters(self, n, path, single=False):
        # (each note says the value and the fact about your curves it comes from; why the app works this way is
        # on the Help page: wiki.js "q-auto-why")
        an = self.an
        need = f"{an['features']} peaks and dips to correct" if an["features"] else "no peaks or dips, only the overall shape"
        self.note(path, f"{n} filters: {need}." if single else f"Up to {n} filters: {need}.")

    def note_boost(self, gt, path):
        boost = self.an["need_boost"]
        self.note(path, f"Boosts up to +{gt} dB: the target needs up to +{boost:.1f} dB.")

    def note_q(self, qt, path, hi=None):
        an = self.an
        self.note(path, (f"Q up to {qt:g}: the narrowest peak or dip is about Q {an['q_need']:.1f}"
                         if an["q_at"] else f"Q up to {qt:g}: no narrow peaks or dips")
                  + (f" (Q {hi:g} is tried too)" if hi and hi > qt else "") + ".")

    # ---- each part
    def scored_range(self):
        an, top, n_files = self.an, self.an["band_top"], self.an["n_files"]
        self.values["scoring.band_hz.1"] = _fit("scoring.band_hz.1", top)
        why = an["band_why"]
        if why == "agree":
            text = f"Scored to {_fmt_hz(top)}: your {n_files} files agree up to there."
        elif why == "data":
            text = f"Scored to {_fmt_hz(top)}: the measurement ends at {_fmt_hz(an['data_top'])}."
        elif an["unstable_from"]:
            text = f"Scored to {_fmt_hz(top)}: your {n_files} files differ above {_fmt_hz(an['unstable_from'])}."
        else:
            text = f"Scored to {_fmt_hz(top)}."
        self.note("scoring.band_hz.1", text)

    def site_sweep_values(self, Ls):
        """(values, boost limit, Q limit, most rows, highest Q) for the website sweep at search width Ls."""
        rows = self.counts(Ls, "site_sweep.filter_rows")
        rows_top = max(rows)
        fh_base = max([o for o in SITE_FH_OPTS if o <= self.span] or [6000])
        i = SITE_FH_OPTS.index(fh_base)
        fh_ladder = [fh_base] + [SITE_FH_OPTS[j] for j in (i - 1, i + 1, i - 2, i + 2) if 0 <= j < len(SITE_FH_OPTS)]
        fh = sorted(fh_ladder[:1 + _r(3 * Ls)])
        gt, gf = self.gain_top("site_single.gain_max"), self.cut_floor("site_single.gain_min")
        gr = []
        lo_g, hi_g = _lim("site_sweep.gain_ranges")
        for r in ([gf, gt], [-12, 6], [int(lo_g), int(hi_g)]):
            if r not in gr:
                gr.append(r)
        gr = gr[:1 + _r(2 * Ls)]
        qt = self.q_top("site_sweep.q_max")
        qm, qhi = self.q_list(qt, Ls, "site_sweep.q_max", 2 + _r(2 * Ls))
        return {"site_sweep.filter_rows": sorted(set(rows)), "site_sweep.freq_high": fh, "site_sweep.gain_ranges": gr,
                "site_sweep.q_max": qm}, gt, qt, rows_top, qhi

    def site_single(self):
        rows = _fit("site_single.rows", self.n_need)  # (one run: the count the curve needs, found within 0.1 dB of the best)
        gt, qt = self.gain_top("site_single.gain_max"), self.q_top("site_single.q_max")
        self.values.update({"site_single.rows": rows, "site_single.freq_high": _fit("site_single.freq_high", self.span),
                            "site_single.gain_min": self.cut_floor("site_single.gain_min"), "site_single.gain_max": gt,
                            "site_single.q_max": qt})
        self.note_filters(rows, "site_single.rows", single=True)
        self.note_boost(gt, "site_single.gain_max")
        self.note_q(qt, "site_single.q_max")

    def site_sweep(self):
        vals, gt, qt, rows_top, qhi = self.site_sweep_values(self.L)
        self.values.update(vals)
        self.note_filters(rows_top, "site_sweep.filter_rows")
        self.note_boost(gt, "site_sweep.gain_ranges")
        self.note_q(qt, "site_sweep.q_max", qhi)

    def best_fit(self):
        an, L = self.an, self.L
        lay = self.cfg["best_fit"].get("layout", "any")
        if layouts.is_fixed(lay):  # (only the bands' gains: none of the settings below are used)
            self.note("best_fit.layout", f"{layouts.name(lay)}: only the bands' gains are fitted.")
            return
        from . import engines
        grows = engines.grows(self.cfg["best_fit"])
        counts = self.counts(L, "best_fit.filter_counts")
        nmax = max(counts)
        gt, qt = self.gain_top("best_fit.gain_max"), self.q_top("best_fit.q_max")
        if grows:
            # One search (2026-10-13, 15 IEMs and headphones): every boost and Q limit Standard and Thorough tried
            # (Quick's are among Standard's), each with both fighting-filter penalties: the fewest filters any of the
            # three found for every pair (the HD600: 15, Thorough alone 19), as close as Thorough where the target
            # was out of reach; 8 s typical, 64-90 s at most on 24 workers. The penalties mattered: 13 picks came
            # from 0.003, two from 0.01. Every limit at both penalties picked the same as Standard's at 0.01 with
            # Thorough's at 0.003, at 1.5x the time, but is one rule.
            q_std, _ = self.q_list(qt, 0.5, "best_fit.q_max", 4)
            q_tho, _ = self.q_list(qt, 1.0, "best_fit.q_max", 5)
            qm = sorted(set(q_std) | set(q_tho))
            gains, fights = _take([gt, 6, 9, 3], 3, gt), [0.003, 0.01]
        else:  # (each count on its own, from random starts: as Standard, its tested middle)
            qm, _ = self.q_list(qt, L, "best_fit.q_max", 2 + _r(3 * L))
            gains, fights = _take([gt, 6, 9, 3], 1 + _r(2 * L), gt), [0.01]
        qhi = max(qm)
        self.values.update({
            "best_fit.filter_counts": counts, "best_fit.freq_range.1": 16000 if self.span <= 12000 else 20000,
            "best_fit.gain_min": self.cut_floor("best_fit.gain_min"), "best_fit.gain_max": gains,
            "best_fit.q_max": qm,
            "best_fit.low_shelf": abs(an["bass_step"]) >= 3,
            # High shelf: tested on/off on five measurement/target pairs, scored to 10 and to 20 kHz: it helped
            # about as often as it hurt (up to 55% more error: the fit settles worse with it), and how far off
            # the treble is didn't predict which. The peaking filters cover the treble, so it stays off.
            "best_fit.high_shelf": False,
            # Fighting filters (boost on top of cut): fitting each count on its own with 12-16 filters, easing the
            # penalty from 0.01 to 0.003 matched 0.04 dB closer (and closer on other units) at 1.2x the time,
            # without more boost; 0 gained nothing more at 2.4x the time and +0.5 dB boost. Stronger ones only made
            # fits worse. Growing: both, above
            "best_fit.fight_penalty": fights})
        if lay in layouts.DEVICES:  # (the notes say what the run uses: the device's limits apply to these values)
            dev = device_settings(apply(copy.deepcopy(self.cfg), self.values)["best_fit"])
            nmax, gt = min(nmax, max(dev["filter_counts"])), min(gt, max(dev["gain_max"]))
            qt, qhi = min(qt, max(dev["q_max"])), min(qhi, max(dev["q_max"]))
        self.note_filters(nmax, "best_fit.filter_counts")
        self.note_boost(gt, "best_fit.gain_max")
        self.note_q(qt, "best_fit.q_max", qhi)
        if len(fights) > 1:
            self.note("best_fit.fight_penalty", "Fighting-filter penalties " + " and ".join(f"{x:g}" for x in fights)
                      + ": every limit with each.")
        if self.values["best_fit.low_shelf"]:
            self.note("best_fit.low_shelf", f"Low shelf on: the bass is {abs(an['bass_step']):.1f} dB "
                                            f"{'under' if an['bass_step'] > 0 else 'over'} the target.")
        if lay in layouts.DEVICES:
            self.note("best_fit.layout", layouts.summary(lay))

    def picking(self):
        """The pick (the user's ask, 2026-10-12: as close to the target as possible without an audible difference):
        the simplest result that sounds the same as the target (within EAR_DB everywhere, ear-smoothed:
        engines.ear_error); when none can, the simplest that sounds the same as the closest result. Until then the
        simplest within 0.1 dB average error of the best (a choice until 1.0.9): on 15 IEMs and
        headphones it took 12 filters but differed from the closest result by up to 0.87 dB in some band, more than
        0.25 dB in 14 of 15 (an average hides a broad difference). 0.25 dB: about the smallest broad change listeners
        noticed in pink noise (Toole and Olive 1988). BENCHMARKS.md has the tests."""
        self.values["scoring.pick"] = "audible"
        self.values["scoring.ear_db"] = EAR_DB
        self.note("scoring.pick", f"Picks the simplest that sounds the same as the target (within {EAR_DB:g} dB).")


def plan(cfg, an, mode=None):
    """{"values": {path: value}, "notes": [{"path", "text"}]} for a method (default: the one chosen)."""
    mode = mode or cfg["mode"]
    p = _Plan(cfg, an)
    p.scored_range()
    if mode in ("site_single", "site_sweep", "best_fit"):
        getattr(p, mode)()
    if mode == "site_sweep" or mode == "best_fit" and not layouts.is_fixed(cfg["best_fit"].get("layout", "any")):
        p.picking()
    _consistent(cfg, p.values, p.notes)
    return {"values": p.values, "notes": [{"path": path, "text": t} for path, t in p.notes]}


def describe(cfg, mode=None):
    """What a run with these settings will try, in words."""
    from . import engines
    mode = mode or cfg["mode"]
    if mode == "site_single":
        return f"1 website run with {cfg['site_single']['rows']} filter rows"
    sw = cfg["site_sweep"]
    n_site = len(engines.site_combos(sw))
    if mode == "site_sweep":
        return (f"{n_site} website runs: {len(sw['filter_rows'])} row counts × {len(sw['freq_high'])} frequency limits × "
                f"{len(sw['gain_ranges'])} gain ranges × {len(sw['q_max'])} Q limits")
    if mode == "best_fit":
        bf = cfg["best_fit"]
        if layouts.is_fixed(bf["layout"]):
            lo, hi, step = layouts.sliders(bf)  # (a graphic EQ app's own range and steps kept)
            return (f"{len(layouts.bands(bf)[0])} bands' gains ({layouts.name(bf['layout'])}), {lo:g} to "
                    f"+{hi:g} dB in {step:g} dB steps")
        bf = device_settings(bf)
        nfit = engines.fit_count(bf, _count_mine(bf))  # (with your own filters: theirs too)
        fp = len(engines.fights(bf))
        times = f" × {fp} fighting-filter penalties" if fp > 1 else ""
        n_mine = _count_mine(bf)
        if n_mine and bf.get("start_add") is False:  # (your filters fill the device: nothing is added)
            if bf.get("start_keep", True):
                return f"your {n_mine} filters only, as they are (they fill {layouts.name(bf['layout'])}), scored"
            return (f"your {n_mine} filters only (they fill {layouts.name(bf['layout'])}), adjusted once per limit: "
                    f"{len(bf['gain_max'])} boost limits × {len(bf['q_max'])} Q limits{times}")
        if engines.grows(bf, n_mine):
            limits = len(bf["gain_max"]) * len(bf["q_max"]) * fp
            stops = cfg["scoring"].get("pick") == "audible"
            return (f"{limits} fits adding filters one at a time, up to {max(bf['filter_counts'])} "
                    f"({len(bf['gain_max'])} boost limits × {len(bf['q_max'])} Q limits{times})"
                    + (", stopping at the first that sounds the same as the target" if stops else "")
                    + (f"; added to your {n_mine} filters" if (n_mine := _count_mine(bf)) else "")
                    + (f"; within {layouts.name(bf['layout'])}'s limits" if bf["layout"] in layouts.DEVICES else ""))
        return (f"{nfit} fits ({len(bf['filter_counts'])} filter counts × {len(bf['gain_max'])} boost limits × "
                f"{len(bf['q_max'])} Q limits{times}), {engines.RANDOM_STARTS} random starts each"
                + (f"; added to your {n_mine} filters" + ("" if bf.get("start_keep", True) else ", which may be adjusted")
                   if (n_mine := _count_mine(bf)) else "")
                + (f"; within {layouts.name(bf['layout'])}'s limits" if bf["layout"] in layouts.DEVICES else ""))
    return mode


def device_settings(bf):
    """Best fit's settings kept within its device layout's (your own filters, kept or adjusted, take some of its)."""
    return layouts.device_settings(bf, _count_mine(bf))


def _count_mine(bf):
    """How many filters of your own Best fit starts from (0 while the box can't be read: the run says why)."""
    from . import exports
    try:
        return len(exports.parse_filters(bf.get("start_filters", "")))
    except ValueError:
        return 0


def apply(cfg, values):
    """Write the automatic values into cfg, except the settings the user set themselves."""
    manual = set(cfg["auto"].get("manual") or [])
    for p, val in values.items():
        if p not in manual:
            settings.set_path(cfg, p, val)
    return cfg


# ---------------------------------------------------------------- time estimate (measured per-task costs)
# The work is counted in single-task seconds (measured one at a time on this PC: a website run ~0.5 s, a fit
# ~0.02 s + 0.012 s per filter for each start, more above ~12 filters) and turned into wall time with a factor per
# kind of work. Many tasks at once slow each other down (shared cores and memory), so the factors are well above 1,
# and a little more so the bigger the run (_crowd(): fitted on 8 Best fit runs of 6 s to 3.7 min, three
# measurements; within about 20%, as other work on the PC changes run times too). They start from runs measured
# here and follow this PC's real run times after every run (learn()). ("fit_k" replaced "fit" when the fits got faster: an old "fit" value is ignored.)
TIMING_PATH = os.path.join(paths.CACHE, "timing.json")
DEFAULT_K = {"site": 2.1, "fit_k": 3.4, "grow_k": 1.5}
# Growing (engines._grow_run): one fit grown to n filters took on one core about GROW_C × n³ seconds (2026-10-13,
# grow_timing.py: 4 pairs, both penalties, 6 to 79 s to 32 filters, 37 on average; each step's time varies a lot);
# with the audible pick most stop at 8-19 filters (the others at the same count): GROW_STOP is the estimate's
GROW_C, GROW_STOP = 0.00113, 16


def _factors():
    saved = textfile.read_json(TIMING_PATH, {})
    if not isinstance(saved, dict):
        return dict(DEFAULT_K)
    return {k: float(saved[k]) if isinstance(saved.get(k), (int, float)) else v for k, v in DEFAULT_K.items()}


def _crowd(fit):
    """How much more a bigger Best fit run slows itself down (its fitting work in single-task seconds)."""
    return 1 + 0.1 * math.log(max(fit, 1.4) / 1.4)


def _slower(fight):
    """How much longer a fit takes with this fighting-filter penalty than with 0.01 (measured: 0.003 1.2×, 0.001 1.5×,
    0 2.4×)."""
    return min(2.5, (0.01 / max(fight, 1e-4)) ** 0.17)


def _fit_key(cfg, mode):
    """Which factor turns the fitting work into seconds: growing's own (its work is counted differently)."""
    from . import engines
    bf = cfg["best_fit"]
    # (within the device's limits, as the run: a device your filters fill adds nothing, so nothing grows)
    grown = mode == "best_fit" and not layouts.is_fixed(bf["layout"]) and engines.grows(device_settings(bf), _count_mine(bf))
    return "grow_k" if grown else "fit_k"


def _parts(cfg, mode, cached=True):
    """(fixed seconds, website work, fitting work) of a run (cached: site runs done a moment ago are reused)."""
    from . import engines
    w = pipeline.workers(cfg)
    if _fit_key(cfg, mode) == "grow_k":  # (one fit per limit, all at once while there are workers for them)
        bf = device_settings(cfg["best_fit"])
        top = max(bf["filter_counts"]) + bool(bf.get("low_shelf")) + bool(bf.get("high_shelf"))
        stop = min(top, GROW_STOP) if cfg["scoring"].get("pick") == "audible" else top
        fp = engines.fights(bf)
        tasks = len(bf["gain_max"]) * len(bf["q_max"]) * len(fp)
        slower = sum(_slower(x) for x in fp) / len(fp)
        return 1.2, 0.0, math.ceil(tasks / w) * GROW_C * stop ** 3 * slower
    site_t = lambda rows: min(1.0, 0.05 + 0.06 * rows)
    if mode == "site_single":
        return 0.6 + site_t(cfg["site_single"]["rows"]), 0.0, 0.0
    if mode == "best_fit" and layouts.is_fixed(cfg["best_fit"]["layout"]):  # (one fit of the gains: well under a second)
        return 0.6, 0.0, 0.0
    sweep = cfg["site_sweep"]
    if engines.sweep_size(sweep) <= engines.MAX_SITE_RUNS:
        combos = engines.site_combos(sweep)
        n_runs = len(combos)
        site = sum(site_t(c[0]) for c in combos) / w * 1.15
    else:  # (too many to list: counted from the lists, so the estimate stays instant; the run itself is refused)
        n_runs = engines.sweep_size(sweep)
        site = n_runs / len(sweep["filter_rows"]) * sum(map(site_t, sweep["filter_rows"])) / w * 1.15
    reuse = cached and mode == "site_sweep" and pipeline.sweep_cached(cfg)
    if mode == "site_sweep":
        return (0.3, 0.0, 0.0) if reuse else (1.5, site, 0.0)
    bf = device_settings(cfg["best_fit"])
    # (your own filters, when the fit may adjust them, are that many more filters in every fit)
    shelves = bool(bf.get("low_shelf")) + bool(bf.get("high_shelf")) + (0 if bf.get("start_keep", True) else _count_mine(bf))
    # measured per start: 0.15 s at 10 filters, 0.2 s at 12, 0.4 s at 14-16 (a few starts take many more steps)
    tasks = [0.0015 * n ** 2 + (engines.RANDOM_STARTS + 1) * (0.02 + 0.012 * (n + shelves) + 0.00003 * (n + shelves) ** 3)
             for n in bf["filter_counts"]]
    # a lighter fighting-filter penalty takes longer (measured: 0.003 → 1.2×, 0.001 → 1.5×, 0 → 2.4×)
    n_mine, limits = _count_mine(bf), len(bf["q_max"]) * len(bf["gain_max"])
    if n_mine and not bf.get("start_add", True):
        tasks = []
    if n_mine and not bf.get("start_keep", True):  # (yours alone, adjusted, once per limit: one start each)
        tasks += [0.02 + 0.012 * n_mine + 0.00003 * n_mine ** 3]  # (times the limits below)
    fits = sum(tasks) * limits * sum(_slower(x) for x in engines.fights(bf))
    fit = max(fits / w * 1.15, max(tasks) if tasks else 0)
    return 1.2, 0.0, fit


def estimate(cfg, mode=None):
    """Rough seconds for a run with these settings on this PC."""
    mode = mode or cfg["mode"]
    fixed, site, fit = _parts(cfg, mode)
    k = _factors()
    return fixed + k["site"] * site + k[_fit_key(cfg, mode)] * _crowd(fit) * fit


def learn(cfg, mode, seconds):
    """After a real run: move the factors toward what this PC actually took."""
    fixed, site, fit = _parts(cfg, mode, cached=False)  # (the run did all its work: service.py doesn't ask otherwise)
    k = _factors()
    clip = lambda x: min(max(x, 0.3), 60.0)
    if mode == "site_sweep" and site > 0.3:
        k["site"] = 0.6 * k["site"] + 0.4 * clip((seconds - fixed) / site)
    elif mode == "best_fit" and fit > 1.0:  # a short run is mostly start-up time: it says little about the fits
        key = _fit_key(cfg, mode)
        k[key] = 0.6 * k[key] + 0.4 * clip((seconds - fixed - k["site"] * site) / (_crowd(fit) * fit))
    else:
        return
    textfile.write_json(TIMING_PATH, {x: round(v, 3) for x, v in k.items()})


def fmt_time(s):
    return ("about a second" if s < 1.5 else f"about {round(s)} s" if s < 90 else f"about {s / 60:.1f} min" if s < 5400
            else f"about {s / 3600:.1f} h")


def auto_result(cfg, an):
    """What /api/auto returns: the values (when automatic), the notes, the effective search and its time."""
    out = {"enabled": cfg["auto"]["enabled"]}
    eff = cfg
    if an and cfg["auto"]["enabled"]:
        p = plan(cfg, an)
        eff = apply(copy.deepcopy(cfg), p["values"])
        manual = set(cfg["auto"].get("manual") or [])
        out.update(values=p["values"], notes=p["notes"],
                   manual=[k for k in p["values"] if k in manual])
    else:
        out.update(values={}, notes=[], manual=[])
    s = estimate(eff)
    out["seconds"], out["time"], out["search"] = round(s, 1), fmt_time(s), describe(eff)
    out["analysis"] = an
    return out
