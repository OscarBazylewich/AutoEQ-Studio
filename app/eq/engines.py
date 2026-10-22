"""EQ engines.

site_single / site_sweep - squiglink's own equalizer.js (vendor/squiglink) in an embedded V8, run exactly as
                           the AutoEQ button on listener800.github.io runs it.
bestfit                  - filters fitted directly to the scoring band with scipy least squares: grown one filter
                           at a time (_grow_run), or each count from random starts and AutoEq's optimizer when your
                           own filters are adjusted (_bf_worker_run).
graphic_run              - Best fit for fixed bands (a graphic EQ): only the gains, in the sliders' steps.
"""
import json
import multiprocessing.queues
import os
import sys
import threading
import warnings
from concurrent.futures import FIRST_COMPLETED, wait

from . import paths  # noqa: F401 - first: it sets the maths libraries' thread counts before numpy loads
import numpy as np  # noqa: E402

from . import settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
JS_FILES = [os.path.join(HERE, "vendor", "squiglink", "equalizer.js"),
            os.path.join(HERE, "vendor", "squiglink", "graphtool_parts.js")]
sys.path.insert(0, os.path.join(HERE, "vendor"))

SHELF_Q = (0.4, 0.7)  # AutoEq: shelves overshoot outside this Q range
# The curves' range ends at 20 kHz. The site's frequency grid has one more point (~20.2 kHz), past every file's data
# (the last value held): the guards above the scored range don't count it. Else, scored to 20 kHz, it was the only
# point "above": a fit that had to boost the top edge (a measurement falling off there) spent a filter cutting that
# one point back to 0 dB, and the graph showed a cliff at its right edge.
GUARD_TOP = float(settings.LIMITS["scoring.band_hz.1"]["max"])


class Cancelled(Exception):
    pass


# ---------------------------------------------------------------- filter maths (equalizer.js, vectorised)
def _response(phi, a1, a2, b0, b1, b2):
    # one logarithm of the ratio (the same value as the difference of two, at half the cost)
    return 10 * np.log10(((b0 + b1 + b2) ** 2 + (b0 * b2 * phi - (b1 * (b0 + b2) + 4 * b0 * b2)) * phi)
                         / ((1 + a1 + a2) ** 2 + (a2 * phi - (a1 * (1 + a2) + 4 * a2)) * phi))


def _phi(freqs, fs):
    return 4 * np.sin(np.pi * freqs / fs) ** 2


def filter_db(ftype, freqs, fc, gain, q, fs):
    """Equalizer.peaking/lowshelf/highshelf + calc_gains. Parameters may be arrays for broadcasting."""
    return _filter_phi(ftype, _phi(freqs, fs), fc, gain, q, fs)


def _filter_phi(ftype, phi, fc, gain, q, fs):
    """filter_db with the frequencies given as phi = 4 sin²(πf/fs) (worked out once for the fits)."""
    return _response(phi, *biquad(ftype, fc, gain, q, fs))


def biquad(ftype, fc, gain, q, fs):
    """A filter's coefficients as equalizer.js works them out: (a1, a2, b0, b1, b2), divided by a0."""
    w0 = 2 * np.pi * fc / fs
    a = 10 ** (gain / 40)
    alpha = np.sin(w0) / (2 * q)
    cos = np.cos(w0)
    if ftype == "PK":
        a0 = 1 + alpha / a
        return -2 * cos / a0, (1 - alpha / a) / a0, (1 + alpha * a) / a0, -2 * cos / a0, (1 - alpha * a) / a0
    am = 2 * np.sqrt(a) * alpha
    if ftype == "LSQ":
        a0 = (a + 1) + (a - 1) * cos + am
        return (-2 * ((a - 1) + (a + 1) * cos) / a0, ((a + 1) + (a - 1) * cos - am) / a0,
                a * ((a + 1) - (a - 1) * cos + am) / a0, 2 * a * ((a - 1) - (a + 1) * cos) / a0,
                a * ((a + 1) - (a - 1) * cos - am) / a0)
    if ftype == "HSQ":
        a0 = (a + 1) - (a - 1) * cos + am
        return (2 * ((a - 1) - (a + 1) * cos) / a0, ((a + 1) - (a - 1) * cos - am) / a0,
                a * ((a + 1) + (a - 1) * cos + am) / a0, -2 * a * ((a - 1) + (a + 1) * cos) / a0,
                a * ((a + 1) + (a - 1) * cos - am) / a0)
    raise ValueError(ftype)


def eq_gain(freqs, filters, fs):
    g = np.zeros_like(freqs, dtype=float)
    for f in filters:
        if f.get("enabled", True) and f["freq"] and f["gain"] and f["q"]:
            g += filter_db(f.get("type", "PK"), freqs, f["freq"], f["gain"], f["q"], fs)
    return g


def rms_error(freqs, eq_curve, target, band):
    m = (freqs >= band[0]) & (freqs <= band[1])
    if not m.any():  # (else NaN: "nan dB" on a report, and pick() can't compare results)
        raise ValueError(f"The scored range ({band[0]:g}–{band[1]:g} Hz) has no curve points: change “Score from” or "
                         f"“Score to”.")
    return float(np.sqrt(np.mean((eq_curve[m] - target[m]) ** 2)))


def ear_smooth(f, d):
    """d averaged over 1 ERB around each frequency (Glasberg and Moore: the ear's frequency resolution), so a broad
    difference counts in full and a narrow wiggle, which the ear blends with its neighbours, mostly doesn't."""
    f, d = np.asarray(f, float), np.asarray(d, float)
    erb = 24.7 * (4.37 * f / 1000 + 1)
    lo, hi = np.searchsorted(f, f - erb / 2), np.searchsorted(f, f + erb / 2, side="right")
    c = np.concatenate([[0.0], np.cumsum(d)])
    return (c[hi] - c[lo]) / np.maximum(1, hi - lo)


def ear_error(f, d, band):
    """How far apart two curves sound: their difference d (dB) in the scored range, the overall level taken off
    (that's volume, not tone: the pre-amp changes it anyway), smoothed to the ear's resolution within the range (above
    it the measurement is left uncorrected on purpose: it mustn't leak in); (the largest of it, the frequency where)."""
    f = np.asarray(f, float)
    m = (f >= band[0]) & (f <= band[1])
    if not m.any():
        return 0.0, None
    fi, di = f[m], np.asarray(d, float)[m]
    s = np.abs(ear_smooth(fi, di - float(np.mean(di))))
    i = int(np.argmax(s))
    return float(s[i]), float(fi[i])


def finish(result, curves, band, fs):
    """Add EQ'd curve, pre-amp, error and simplicity stats to a result dict (ear: how far it sounds from the target,
    ear_at: where)."""
    filters = result["filters"]
    g = eq_gain(curves["f"], filters, fs)
    result["eq"] = curves["meas"] + g
    result.setdefault("preamp", -float(np.max(g)) if len(filters) else 0.0)
    result["rms"] = rms_error(curves["f"], result["eq"], curves["target"], band)
    result["ear"], result["ear_at"] = ear_error(curves["f"], result["eq"] - curves["target"], band)
    result["n_filters"] = len(filters)
    result["max_q"] = max((f["q"] for f in filters), default=0.0)
    result["max_boost"] = max([0.0] + [f["gain"] for f in filters])
    return result


# ---------------------------------------------------------------- parallel helper
_feeder_error = multiprocessing.queues.Queue._on_queue_feeder_error


_stopping = {"on": False}  # (set while run_tasks stops a pool's workers)


def _quiet_feeder_error(e, obj):
    # after Cancel stops the workers, the pool's queue can no longer reach them: that's expected, not an error (any
    # other time it is one, and goes to the log)
    if not (_stopping["on"] and isinstance(e, OSError)):
        _feeder_error(e, obj)


multiprocessing.queues.Queue._on_queue_feeder_error = staticmethod(_quiet_feeder_error)


def run_tasks(pool, fn, tasks, progress=None, cancel=None):
    """Map fn over tasks on a process pool, reporting progress and honouring a cancel Event."""
    _stopping["on"] = False
    futures = [pool.submit(fn, t) for t in tasks]
    done_count, out = 0, []
    pending = set(futures)
    while pending:
        done, pending = wait(pending, timeout=0.25, return_when=FIRST_COMPLETED)
        for fut in done:
            try:
                out.append(fut.result())
            except BaseException:  # (the run has failed: the others' results aren't wanted, so don't wait for them)
                _stop(pool)
                raise
            done_count += 1
        if progress:
            progress(done_count, len(tasks))
        if cancel is not None and cancel.is_set():
            # stop at once: a big fit can take a while, and its result isn't wanted any more
            _stop(pool)
            raise Cancelled()
    return out


def _stop(pool):
    """The pool's workers stopped at once, its waiting tasks dropped."""
    _stopping["on"] = True
    stop = getattr(pool, "terminate_workers", None)  # Python 3.14+
    if stop:
        stop()
    else:  # (older Pythons, the testers' zip: shutdown can't stop a running fit, up to ~80 s of every core after
        # Cancel; the pool's own processes are ended, as terminate_workers does)
        pool.shutdown(wait=False, cancel_futures=True)
        for p in list((getattr(pool, "_processes", None) or {}).values()):
            try:
                p.terminate()
            except (OSError, AttributeError):
                pass


# ---------------------------------------------------------------- site engine (V8)
_ctx = None  # a worker process's own V8 with the curves loaded (site_worker_init)
# V8 must not be started from several threads at once (service.py answers requests from several threads)
_V8_LOCK = threading.Lock()


def _racer():
    from py_mini_racer import MiniRacer
    with _V8_LOCK:
        return MiniRacer()


def js_site_cfg(cfg):
    s = cfg["site"]
    return {"scale_smoothing": s["scale_smoothing"], "smooth_level": s["smooth_level"], "norm_hz": s["norm_hz"],
            "normalization": s["normalization"], "norm_db": s["norm_db"], "phon_table": s["phon_table"],
            "treble_start_from": s["treble_start_from"], "sample_rate": s["sample_rate"]}


def js_context(cfg, meas_texts=None, target_text=None):
    ctx = _racer()
    for path in JS_FILES:
        with open(path, encoding="utf-8") as fh:
            ctx.eval(fh.read())
    ctx.eval("setSiteConfig(" + json.dumps(js_site_cfg(cfg)) + ")")
    curves = None
    if meas_texts is not None:
        curves = ctx.call("loadCurves", meas_texts, target_text, cfg.get("target_adjust"))
    return ctx, curves


def load_curves(cfg, meas_texts, target_text):
    """Parse, interpolate, adjust, smooth-normalise and average the files the way the site does."""
    _, c = js_context(cfg, meas_texts, target_text)
    for key, what in (("meas", "measurement"), ("target", "target")):
        if any(v is None for v in c[key]):  # (the site's levelling overflows: V8's Infinity/NaN arrive as null)
            raise ValueError(f"The {what} has values the app can't use (dB values far outside ±250?). "
                             f"Check the file: it should hold frequency and dB pairs.")
    return {"f": np.array(c["f"]), "meas": np.array(c["meas"]), "target": np.array(c["target"]),
            "channels": [np.array(ch) for ch in c["channels"]],
            "p_norm": c["pNorm"], "t_norm": c["tNorm"], "n_files": c["nch"]}


def preview_curve(cfg, texts):
    """One device's (or target's) levelled, averaged curve on the site's frequency grid."""
    ctx = _thread_ctx(json.dumps(js_site_cfg(cfg), sort_keys=True), lambda: js_context(cfg)[0])  # (a comparison: dozens)
    return ctx.call("previewCurve", texts)


_kept = threading.local()  # this thread's V8s for counting points and the GraphicEQ text (starting one takes a while)


def _thread_ctx(key, make):
    ctxs = _kept.__dict__.setdefault("ctxs", {})
    if key not in ctxs:
        if len(ctxs) > 4:  # (the GraphicEQ one per site settings: a few at most)
            ctxs.clear()
        ctxs[key] = make()
    return ctxs[key]


def _points_ctx():
    ctx = _racer()
    with open(JS_FILES[1], encoding="utf-8") as fh:
        ctx.eval(fh.read())
    return ctx


def count_points(text):
    return _thread_ctx("points", _points_ctx).call("countPoints", text)


def graphic_eq_text(cfg, filters):
    ctx = _thread_ctx(json.dumps(js_site_cfg(cfg), sort_keys=True), lambda: js_context(cfg)[0])
    return ctx.call("graphicEQText", [{"type": f.get("type", "PK"), "freq": f["freq"], "gain": f["gain"],
                                       "q": f["q"]} for f in filters if f.get("enabled", True)])


def site_worker_init(cfg, meas_texts, target_text):
    """A worker process for the site's runs: its own V8 with the curves loaded."""
    global _ctx
    _ctx, _ = js_context(cfg, meas_texts, target_text)


def _site_worker_run(combo):
    r = _ctx.call("runAutoEQ", *combo)
    filters = [{"type": "PK", "freq": f["freq"], "gain": f["gain"], "q": f["q"]} for f in r["filters"]]
    return combo, filters, r["preamp"], r["effective"]


def _site_result(combo, filters, preamp, eff):
    rows, lo, hi, gmin, gmax, qmin, qmax = combo
    return {"engine": "site", "rows": rows, "freq_low": lo, "freq_high": hi, "gain_min": gmin, "gain_max": gmax,
            "q_min": qmin, "q_max": qmax, "q_max_effective": eff[5], "filters": filters, "preamp": preamp}


def site_single(cfg, curves, meas_texts, target_text):
    site_worker_init(cfg, meas_texts, target_text)
    s = cfg["site_single"]
    combo = (s["rows"], s["freq_low"], s["freq_high"], s["gain_min"], s["gain_max"], s["q_min"], s["q_max"])
    r = _site_result(*_site_worker_run(combo))
    return [finish(r, curves, cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"])]


# The most runs one EQ job may ask for. The lists multiply, so a few long hand-typed lists could mean millions of
# runs (hours, and gigabytes just to list them); the automatic settings use at most about 324 website runs and 216 fits.
MAX_SITE_RUNS = 20000
MAX_FITS = 2000


def sweep_size(sweep):
    """How many website runs a sweep's lists make (before duplicates are dropped): instant, unlike site_combos."""
    return len(sweep["filter_rows"]) * len(sweep["freq_high"]) * len(sweep["gain_ranges"]) * len(sweep["q_max"])


def fit_count(bf, n_mine=0):
    """How many fits a Best fit run makes, as bestfit() builds them: one per filter count × boost limit × Q limit, and
    with n_mine filters of your own one more of yours alone (kept as they are) or one per limit (adjusted); only
    those when nothing is added (start_add off)."""
    limits = len(bf["gain_max"]) * len(bf["q_max"]) * len(fights(bf))
    if grows(bf, n_mine):  # (growing: one task per limit makes every count; yours alone, kept, one more)
        return limits + (1 if n_mine else 0)
    added = len(bf["filter_counts"]) if not n_mine or bf.get("start_add", True) else 0
    return added * limits + ((1 if bf.get("start_keep", True) else limits) if n_mine else 0)


def site_combos(sweep):
    """All panel settings, deduplicated after the panel's own clamping (e.g. Q max above 5 acts as 5)."""
    seen, out = set(), []
    for rows in sweep["filter_rows"]:
        for hi in sweep["freq_high"]:
            for gmin, gmax in sweep["gain_ranges"]:
                for qmax in sweep["q_max"]:
                    combo = (rows, sweep["freq_low"], hi, gmin, gmax, sweep["q_min"], qmax)
                    key = (rows, max(sweep["freq_low"], 20), hi, int(gmin), int(gmax), sweep["q_min"], min(qmax, 5))
                    if key not in seen:
                        seen.add(key)
                        out.append(combo)
    return out


def site_sweep(pool, cfg, curves, progress=None, cancel=None):
    band, fs = cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"]
    # slowest runs (most filters, widest ranges) first so no core sits idle at the end
    combos = sorted(site_combos(cfg["site_sweep"]), key=lambda c: (-c[0], -c[2], c[3] - c[4], -c[6]))
    out = run_tasks(pool, _site_worker_run, combos, progress, cancel)
    return [finish(_site_result(*o), curves, band, fs) for o in out]


# ---------------------------------------------------------------- best-fit engine
_bf = None  # a worker process's fitting data (bestfit_worker_init)


def bestfit_worker_init(curves, band, fs, penalties, shared=None):
    """A worker process for Best fit: the scored band's curves and the penalties, ready for every fit. shared: the
    run's grow_shared() values (growing fits tell each other where they reached the target)."""
    global _bf
    f = curves["f"]
    m = (f >= band[0]) & (f <= band[1])
    fb, fa = f[m], f[(f > band[1]) & (f <= GUARD_TOP)]
    # the scored band's frequencies, then those above it: every filter is worked out on both in one go
    _bf = {"fb": fb, "fa": fa, "phi": _phi(np.concatenate([fb, fa]), fs)[None, :], "mb": curves["meas"][m],
           "tb": curves["target"][m], "nb": int(m.sum()), "fs": fs, "lam": penalties["gain_penalty"],
           "mu": penalties["fight_penalty"], "tg": penalties["treble_guard"], "last": None, "shared": shared}


_GROUPS = {}


def _gains(types, p):
    """dB response of each filter (rows of p: log10 fc, gain, ln Q) on the fit's frequencies."""
    fc, g, q = 10 ** p[:, :1], p[:, 1:2], np.exp(p[:, 2:3])
    phi, fs = _bf["phi"], _bf["fs"]
    groups = _GROUPS.get(types)
    if groups is None:
        groups = _GROUPS[types] = [(t, np.array([i for i, x in enumerate(types) if x == t])) for t in dict.fromkeys(types)]
    if len(groups) == 1:
        return _filter_phi(types[0], phi, fc, g, q, fs)
    out = np.empty((len(types), phi.shape[1]))
    for t, idx in groups:
        out[idx] = _filter_phi(t, phi, fc[idx], g[idx], q[idx], fs)
    return out


def _residual(x, types):
    b = _bf
    p = x.reshape(len(types), 3)
    g_all = _gains(types, p)
    b["last"] = (x.copy(), g_all)  # the Jacobian is usually asked for at this same point next
    gains = g_all[:, :b["nb"]]
    total = gains.sum(axis=0)
    parts = [b["mb"] - b["tb"] + total,
             # discourage needlessly large gains
             np.sqrt(b["nb"] * b["lam"]) * p[:, 1],
             # filters cancelling each other (boost and cut on top of each other): dB of EQ that sums to nothing
             np.sqrt(b["mu"]) * (np.abs(gains).sum(axis=0) - np.abs(total))]
    if len(b["fa"]):
        # above the scored band only the average matters: keep the EQ's average effect there near 0 dB (your own
        # filters kept as they are count too: "ga")
        parts.append([np.sqrt(b["nb"] * b["tg"]) * (g_all[:, b["nb"]:].sum(axis=0).mean() + b.get("ga", 0.0))])
    return np.concatenate(parts)


def _jacobian(x, types):
    """d(_residual)/dx. Each filter's gains depend only on its own 3 parameters, so one vectorised
    finite-difference step per parameter kind covers every filter: the three steps of every filter are worked
    out together (one evaluation instead of 3N+1 full residuals). Steps match scipy's default "2-point" scheme."""
    b = _bf
    n_f, nb = len(types), b["nb"]
    p = x.reshape(n_f, 3)
    last = b["last"]
    g_all = last[1] if last is not None and np.array_equal(last[0], x) else _gains(types, p)
    gb = g_all[:, :nb]
    total = gb.sum(axis=0)
    has_a = len(b["fa"]) > 0
    jac = np.zeros((nb + n_f + nb + (1 if has_a else 0), 3 * n_f))
    fight = np.sqrt(b["mu"]) * (np.sign(gb) - np.sign(total)[None, :])
    h = np.sqrt(np.finfo(float).eps) * np.maximum(1.0, np.abs(p))
    steps = np.concatenate([p + h * np.eye(3)[k] for k in range(3)])
    g_steps = _gains(types * 3, steps)
    for k in range(3):
        cols = np.arange(n_f) * 3 + k
        d = (g_steps[k * n_f:(k + 1) * n_f] - g_all) / h[:, k:k + 1]
        db = d[:, :nb]
        jac[:nb, cols] = db.T
        jac[nb + n_f:2 * nb + n_f, cols] = (fight * db).T
        if has_a:
            jac[-1, cols] = np.sqrt(b["nb"] * b["tg"]) * d[:, nb:].mean(axis=1)
    jac[nb + np.arange(n_f), np.arange(n_f) * 3 + 1] = np.sqrt(b["nb"] * b["lam"])
    return jac


def _autoeq_seed(n, lo, hi, gmin, gmax, qmin, qmax):
    """AutoEq's own PEQ optimizer, used as one starting point (peaking filters only)."""
    from autoeq.peq import PEQ
    b = _bf
    cfg = {"optimizer": {"min_std": 0.002},
           "filters": [{"type": "PEAKING", "min_fc": lo, "max_fc": min(hi, 10000), "min_q": qmin, "max_q": qmax,
                        "min_gain": gmin, "max_gain": gmax} for _ in range(n)]}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        peq = PEQ.from_dict(cfg, b["fb"], b["fs"], target=b["tb"] - b["mb"])
        peq.optimize()
    return [(float(x.fc), float(x.gain), float(x.q)) for x in peq.filters]


def shelf_q(t):
    """A shelf's Q range: AutoEq's (SHELF_Q) within the device's (an EQ app's Q 0.5-6 took shelves at 0.44: review 2)."""
    lo, hi = max(SHELF_Q[0], t["q_min"]), min(SHELF_Q[1], t["q_max"])
    if lo >= hi:  # (no overlap: the device's nearest Q)
        lo = min(max(SHELF_Q[0], t["q_min"]), t["q_max"])
        hi = lo * 1.001
    return lo, hi


def _bounds(types, t):
    """Lower and upper bounds and scales of the fit's parameters (per filter: log10 fc, gain, ln Q)."""
    lb, ub, scale = [], [], []
    for ft in types:
        if ft == "PK":
            lb += [np.log10(t["freq_low"]), t["gain_min"], np.log(t["q_min"])]
            ub += [np.log10(t["freq_high"]), t["gain_max"], np.log(t["q_max"])]
        else:
            flo, fhi = t["shelves"]["low_freq"] if ft == "LSQ" else t["shelves"]["high_freq"]
            qlo, qhi = shelf_q(t)
            lb += [np.log10(flo), t["gain_min"], np.log(qlo)]
            ub += [np.log10(fhi), t["gain_max"], np.log(qhi)]
        scale += [0.1, 1.0, 0.3]
    return np.array(lb), np.array(ub), np.array(scale)


def _starting_points(t):
    """The peaking filters [(fc, gain, q)] each fit starts from: up to 3 site results with the closest filter count
    (not more than n, padded to n), AutoEq's optimizer, then random starts (seeded, so a fit is repeatable)."""
    n, qmin, qmax = t["n"], t["q_min"], t["q_max"]
    # where starting filters go: the filter range up to 12 kHz (all of it when it starts above that)
    lo = t["freq_low"]
    top = min(t["freq_high"], 12000) if lo < 12000 else t["freq_high"]
    starts = []
    close = sorted((s for s in t["seeds"] if len(s["filters"]) <= n), key=lambda s: (n - len(s["filters"]), s["rms"]))[:3]
    for s in close:
        s = list(s["filters"])  # (padded to n with 0 dB filters spread over that range, not piled at its top)
        s += [(float(f), 0.0, 1.0) for f in np.geomspace(lo, top, n - len(s) + 2)[1:-1]]
        starts.append(s)
    try:
        starts.append(_autoeq_seed(n, t["freq_low"], t["freq_high"], t["gain_min"], t["gain_max"], qmin, qmax))
    except Exception:  # noqa: BLE001 - one starting point less
        pass
    rng = np.random.default_rng(n * 1000 + int(qmax * 10) + int(t["gain_max"]))
    for _ in range(t["starts"]):
        starts.append([(10 ** rng.uniform(np.log10(lo), np.log10(top)),
                        rng.uniform(-3, 3), np.exp(rng.uniform(np.log(qmin), np.log(qmax)))) for _ in range(n)])
    return starts


def _tidy(types, x, lb=None, ub=None):
    """The fitted parameters as filters, by frequency: near-identical peaking filters merged (the optimizer sometimes
    splits one filter in two), values rounded, filters under 0.1 dB left out. lb/ub: the fit's bounds; a merge stays
    within both filters' gain limits (at a limit, two filters at one spot are how the fit got past it: kept as two)."""
    n = len(types)
    glo = lb[1::3] if lb is not None else np.full(n, -np.inf)
    ghi = ub[1::3] if ub is not None else np.full(n, np.inf)
    raw = sorted(((ft, 10 ** lf, float(g), float(np.exp(lq)), a, b)
                  for ft, (lf, g, lq), a, b in zip(types, x.reshape(-1, 3), glo, ghi)), key=lambda r: r[1])
    merged = []
    for ft, fc, g, q, a, b in raw:
        m = merged[-1] if merged else None
        if (m and ft == "PK" == m[0] and abs(np.log2(fc / m[1])) < 0.02 and abs(np.log(q / m[3])) < 0.05
                and max(a, m[4]) <= m[2] + g <= min(b, m[5])):
            m[2] += g
            m[4], m[5] = max(a, m[4]), min(b, m[5])
        else:
            merged.append([ft, fc, g, q, a, b])
    filters = []
    for ft, fc, g, q, _, _ in merged:
        f = {"type": ft, "freq": int(round(fc)), "gain": round(g, 1), "q": round(q, 2)}
        if abs(f["gain"]) >= 0.1:
            filters.append(f)
    return filters


def _mine_params(mine):
    """Your own filters as the fit's parameters (log10 fc, gain, ln Q) and their types."""
    return (tuple(f["type"] for f in mine),
            np.array([[np.log10(f["freq"]), f["gain"], np.log(f["q"])] for f in mine]).reshape(-1, 3))


FREQ_LO, FREQ_HI = (float(settings.UI_LIMITS["edit.freq"][k]) for k in ("min", "max"))  # (a filter's frequency range)


def _mine_bounds(mine, t):
    """Bounds for your filters when the fit may adjust them: the fit's own limits, widened to take in your values;
    frequency within an octave of yours and within the device's range (widened to take in yours too)."""
    lb, ub = [], []
    for f in mine:
        qlo, qhi = (t["q_min"], t["q_max"]) if f["type"] == "PK" else shelf_q(t)
        flo = min(max(FREQ_LO, t.get("freq_low", FREQ_LO)), f["freq"])
        fhi = max(min(FREQ_HI, t.get("freq_high", FREQ_HI)), f["freq"])
        lb += [np.log10(max(flo, f["freq"] / 2)), min(t["gain_min"], f["gain"]), np.log(min(qlo, f["q"]))]
        ub += [np.log10(min(fhi, f["freq"] * 2)), max(t["gain_max"], f["gain"]), np.log(max(qhi, f["q"]))]
    return np.array(lb), np.array(ub), np.tile([0.1, 1.0, 0.3], len(mine))


def _bf_worker_run(task):
    """One Best fit task (a filter count within one set of limits): the best of all its starting points.
    With your own filters (task["mine"]): kept as they are, they're part of the measurement the fit works on and
    it adds task["n"] filters (n 0: your filters alone, scored); else they're fitted too, starting from your values.
    Returns (the task without its seeds, filters)."""
    from scipy.optimize import least_squares  # loaded here so the app and website-mode workers start faster
    b, mine, keep = _bf, task.get("mine") or [], task.get("keep", True)
    b["mu"] = task.get("fight", b["mu"])  # (this task's fighting-filter penalty)
    shelves = task["shelves"]
    added = tuple((["LSQ"] if shelves["low"] else []) + ["PK"] * task["n"] + (["HSQ"] if shelves["high"] else []))
    done = {k: v for k, v in task.items() if k != "seeds"}
    mine_types, mine_p = _mine_params(mine)
    fitted_mine = mine and not keep
    types = (mine_types if fitted_mine else ()) + added
    if not types:  # your filters alone, as they are
        return done, [dict(f) for f in mine]
    lb, ub, scale = _bounds(added, task)
    if fitted_mine:
        mlb, mub, mscale = _mine_bounds(mine, task)
        lb, ub, scale = np.concatenate([mlb, lb]), np.concatenate([mub, ub]), np.concatenate([mscale, scale])

    def with_shelves(peaking):  # a start's peaking filters, with the shelves' own starting values in place
        it = iter(peaking)
        return [next(it) if ft == "PK" else (105.0, 0.0, 0.7) if ft == "LSQ" else (10000.0, 0.0, 0.7) for ft in added]

    saved = b["mb"], b.get("ga", 0.0)
    if mine and keep:  # (the measurement with your filters on; the AutoEq starting point fits what's left too)
        g = _gains(mine_types, mine_p)
        b["mb"], b["ga"] = b["mb"] + g[:, :b["nb"]].sum(axis=0), float(g[:, b["nb"]:].sum(axis=0).mean()) if len(b["fa"]) else 0.0
    best = None
    try:
        for start in _starting_points(task):
            x0 = np.array([[np.log10(fc), g, np.log(q)] for fc, g, q in with_shelves(start)]).ravel()
            if fitted_mine:
                x0 = np.concatenate([mine_p.ravel(), x0])
            x0 = np.clip(x0, lb + 1e-9, ub - 1e-9)
            try:
                sol = least_squares(_residual, x0, jac=_jacobian, args=(types,), bounds=(lb, ub), x_scale=scale,
                                    max_nfev=3000)
            except (np.linalg.LinAlgError, ValueError):
                continue  # a start that ran into numerical trouble (e.g. "SVD did not converge"): the others still count
            if np.isfinite(sol.cost) and (best is None or sol.cost < best.cost):
                best = sol
            if not added:  # (only your filters to adjust: one start is enough)
                break
    finally:
        b["mb"], b["ga"] = saved
        b["last"] = None
    filters = _tidy(types, best.x, lb, ub) if best is not None else []
    return done, ([dict(f) for f in mine] + filters if mine and keep else filters)


RANDOM_STARTS = 13  # starting points when each count is fitted on its own (your own filters adjusted): Standard's,
# tools/starts_benchmark.py (16 within 0.02 dB of the best in 90% of fits; past 16 almost nothing more)
GROW_TRIES = 2     # places tried for each new filter (the method test's)
GROW_NFEV = 600    # the fit's steps after each new filter (it starts close: the filters before are fitted already)
NO_BEST = 10 ** 6  # (the shared "fewest filters that reached the target" before any did)
# When the target is out of reach: a growing fit stops once more filters stop helping (its lowest ear error not
# 0.02 dB lower over the last 6 counts, from 8 filters). Simulated on the method test's candidates: the same pick for
# all 15 pairs, about a fifth less work (the pair out of reach: most of it)
PLATEAU_COUNTS, PLATEAU_DB, PLATEAU_FROM = 6, 0.02, 8


def grows(bf, n_mine=None):
    """Does a Best fit run with these settings grow its EQs? Not when your own filters are adjusted by the fit or
    nothing is added to them: those fit every count from scratch. n_mine: how many filters of your own (when the caller
    has counted them already; else they're read from the settings). bf["build"] "scratch": every count from scratch
    (not a setting since 1.0.9: the benchmarks' way to compare)."""
    from . import exports
    if bf.get("build", "grow") != "grow" or not bf.get("start_add", True):
        return False
    if n_mine is None:
        try:
            n_mine = len(exports.parse_filters(bf.get("start_filters", "")))
        except ValueError:
            n_mine = 0
    return not n_mine or bf.get("start_keep", True)


def fights(bf):
    """The fighting-filter penalties a run tries (best_fit.fight_penalty: a list; one number in older settings)."""
    v = bf.get("fight_penalty", 0.01)
    return list(v) if isinstance(v, (list, tuple)) and v else [v if isinstance(v, (int, float)) else 0.01]


def grow_shared():
    """What a run's growing fits share (their worker processes get it when they start): the fewest filters any of them
    reached the target with (the others stop there: they can't be simpler), and the steps done (the progress)."""
    import multiprocessing
    return multiprocessing.Value("i", NO_BEST), multiprocessing.Value("i", 0)


def _third_octave(fb):
    """Rows average over a third of an octave around each frequency (where the error is largest, as a filter sees it)."""
    m = np.abs(np.log2(fb[None, :] / fb[:, None])) <= 1 / 6
    return m / m.sum(axis=1, keepdims=True)


def _grow_run(task):
    """One Best fit task grown (best_fit.build "grow"): within one boost and Q limit, the EQ grown one filter at a time
    from 1 to the most filters, each new filter put where the error (a third of an octave smoothed) is largest, the
    GROW_TRIES largest places tried, every filter fitted again from where it is. Each count in task["counts"] is a
    result. task["stop_ear"]: the audible pick's limit: the first count that sounds the same as the target ends this
    task, and through the run's shared values every other task at that count (a later count can't be simpler);
    a task that doesn't get there stops once more filters stop helping (PLATEAU_*).
    The method test (BENCHMARKS.md, 15 IEMs and headphones at Thorough): as many reached the target as
    fitting every count from scratch, with 12.7 filters instead of 16.1 (never more), in a twelfth of the time.
    Your own filters kept as they are: in the measurement, the fit adds filters on top (as _bf_worker_run).
    Returns (the task, {count: filters})."""
    from scipy.optimize import least_squares
    b, mine = _bf, task.get("mine") or []
    b["mu"] = task.get("fight", b["mu"])  # (this task's fighting-filter penalty)
    best_n, steps = b.get("shared") or (None, None)
    sh = task["shelves"]
    lo_t, hi_t = (["LSQ"] if sh["low"] else []), (["HSQ"] if sh["high"] else [])
    fb, nb = b["fb"], b["nb"]
    keep, top, stop_ear = set(task["counts"]), max(task["counts"]), task.get("stop_ear")
    # where a new filter may go: the filter range within the scored range, up to 16 kHz (all of the scored range
    # when they don't meet)
    where = (fb >= task["freq_low"]) & (fb <= min(task["freq_high"], 16000))
    if not where.any():
        where = np.ones(nb, bool)
    third = _third_octave(fb)
    lows = [(np.log10(105.0), 0.0, np.log(0.7))] if lo_t else []
    highs = [(np.log10(10000.0), 0.0, np.log(0.7))] if hi_t else []
    peaks, out, lowest = [], {}, []
    saved = b["mb"], b.get("ga", 0.0)
    if mine:  # (the measurement with your filters on, as _bf_worker_run)
        mine_types, mine_p = _mine_params(mine)
        g = _gains(mine_types, mine_p)
        b["mb"], b["ga"] = b["mb"] + g[:, :nb].sum(axis=0), float(g[:, nb:].sum(axis=0).mean()) if len(b["fa"]) else 0.0
    counted = 0
    try:
        for n in range(1, top + 1):
            if best_n is not None and best_n.value < n:
                break  # (another task reached the target with fewer filters)
            types = tuple(lo_t + ["PK"] * n + hi_t)
            lb, ub, scale = _bounds(types, task)
            before = lows + peaks + highs
            err = (_residual(np.array(before, float).ravel(), tuple(lo_t + ["PK"] * (n - 1) + hi_t))[:nb] if before
                   else b["mb"] - b["tb"])
            sm = third @ err
            places = []
            for i in np.argsort(-np.abs(np.where(where, sm, 0))):
                if len(places) >= GROW_TRIES:
                    break
                if where[i] and all(abs(np.log2(fb[i] / fb[j])) > 0.5 for j in places):  # (half an octave apart)
                    places.append(int(i))
            sol = None
            for i in places:
                # the new filter: the error's size there, as wide as the error is above half of it
                half = (np.abs(sm) > abs(sm[i]) / 2) & (np.sign(sm) == np.sign(sm[i]))
                a = c = i
                while a > 0 and half[a - 1]:
                    a -= 1
                while c < nb - 1 and half[c + 1]:
                    c += 1
                bw = 2 ** max(0.2, float(np.log2(fb[c] / fb[a])))
                q = min(task["q_max"], max(task["q_min"], np.sqrt(bw) / (bw - 1)))
                g = min(task["gain_max"], max(task["gain_min"], -float(sm[i])))
                x0 = np.clip(np.array(lows + peaks + [(np.log10(fb[i]), g, np.log(q))] + highs, float).ravel(),
                             lb + 1e-9, ub - 1e-9)
                try:
                    s = least_squares(_residual, x0, jac=_jacobian, args=(types,), bounds=(lb, ub), x_scale=scale,
                                      max_nfev=GROW_NFEV)
                except (np.linalg.LinAlgError, ValueError):
                    continue  # (numerical trouble at this place: the other place still counts)
                if np.isfinite(s.cost) and (sol is None or s.cost < sol.cost):
                    sol = s
            b["last"] = None
            if sol is None:
                break
            p = [tuple(r) for r in sol.x.reshape(-1, 3)]
            lows, peaks, highs = p[:len(lows)], p[len(lows):len(lows) + n], p[len(lows) + n:]
            if steps is not None:
                with steps.get_lock():
                    steps.value += 1
                counted += 1
            if n not in keep:
                continue
            filters = _tidy(types, sol.x, lb, ub)
            out[n] = [dict(f) for f in mine] + filters
            if stop_ear is not None:
                # (as finish() will judge it: the filters as they're saved, on the scored range)
                ear = ear_error(fb, b["mb"] + eq_gain(fb, filters, b["fs"]) - b["tb"], (fb[0], fb[-1]))[0]
                if ear <= stop_ear:
                    if best_n is not None:
                        with best_n.get_lock():
                            best_n.value = min(best_n.value, n)
                    break
                lowest.append(min(ear, lowest[-1]) if lowest else ear)
                stalled = len(lowest) > PLATEAU_COUNTS and lowest[-1 - PLATEAU_COUNTS] - lowest[-1] < PLATEAU_DB
                if n >= PLATEAU_FROM and stalled:
                    break
    finally:
        b["mb"], b["ga"] = saved
        b["last"] = None
        if steps is not None:  # (stopped early, at a plateau or with no place left: its steps still to come counted done,
            # so the bar reaches the end; it sat at half on targets out of reach)
            reach = min(top, best_n.value) if best_n is not None else top
            with steps.get_lock():
                steps.value += max(0, reach - counted)
    return task, out


def _seeds_within(site_results, gain_min, gain_max, q_max):
    """Site results whose filters fit inside these limits, best first, each set of filters once."""
    seeds, seen = [], set()
    for r in sorted(site_results, key=lambda r: r["rms"]):
        key = tuple((f["freq"], f["gain"], f["q"]) for f in r["filters"])
        if (key and key not in seen and r["max_q"] <= q_max and r["max_boost"] <= gain_max
                and min(f["gain"] for f in r["filters"]) >= gain_min):
            seen.add(key)
            seeds.append({"filters": list(key), "rms": r["rms"]})
    return seeds


def bestfit(pool, cfg, curves, site_results=(), progress=None, cancel=None, shared=None):
    """Best fit: one fit per filter count × boost limit × Q limit, in the pool's worker processes; or, growing
    (grows()), one task per boost limit × Q limit that makes every count (_grow_run; shared: the pool's
    grow_shared() values). With your own filters (best_fit.start_filters) the counts are filters added to yours, and
    one more result is yours alone (as they are, or adjusted by the fit)."""
    from . import exports  # (reads the filters you typed or brought in)
    bf, band, fs = cfg["best_fit"], cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"]
    lo, hi = bf["freq_range"]
    mine, keep = exports.parse_filters(bf.get("start_filters", "")), bf.get("start_keep", True)
    shelves = {"low": bf.get("low_shelf", False), "high": bf.get("high_shelf", False),
               "low_freq": bf.get("low_shelf_freq", [20, 400]), "high_freq": bf.get("high_shelf_freq", [1000, 16000])}
    if grows(bf, len(mine)):
        return _bestfit_grown(pool, cfg, curves, mine, shelves, progress, cancel, shared)
    no_shelves = dict(shelves, low=False, high=False)
    tasks = []
    for gmax in bf["gain_max"]:
        for qmax in bf["q_max"]:
            seeds = _seeds_within(site_results, bf["gain_min"], gmax, qmax)
            added = list(bf["filter_counts"]) if not mine or bf.get("start_add", True) else []  # (else: yours only)
            for fp in fights(bf):
                for n in ([0] if mine else []) + added:
                    tasks.append({"n": n, "freq_low": lo, "freq_high": hi, "gain_min": bf["gain_min"],
                                  "gain_max": gmax, "q_min": bf["q_min"], "q_max": qmax,
                                  "shelves": shelves if n else no_shelves, "starts": RANDOM_STARTS,
                                  "seeds": seeds, "mine": mine, "keep": keep, "fight": fp})
    if mine and keep:  # your filters as they are don't depend on the limits: scored once
        alone = [t for t in tasks if t["n"] == 0]
        tasks = [t for t in tasks if t["n"]] + alone[:1]
    tasks.sort(key=lambda t: -(t["n"] + (0 if keep else len(mine))))  # biggest fits first so the cores stay busy
    if progress:  # (the real count: your own filters' fit is one more, and some counts aren't run with them)
        progress(0, len(tasks))
    out = run_tasks(pool, _bf_worker_run, tasks, progress, cancel)
    results = []
    for t, filters in out:
        results.append(finish({"engine": "bestfit", "rows": t["n"], "freq_low": t["freq_low"], "freq_high": t["freq_high"],
                               "gain_min": t["gain_min"], "gain_max": t["gain_max"], "q_min": t["q_min"],
                               "q_max": t["q_max"], "low_shelf": t["shelves"]["low"], "high_shelf": t["shelves"]["high"],
                               "yours": len(mine), "keep": keep, "layout": cfg["best_fit"].get("layout", "any"),
                               "fight": t.get("fight"), "filters": filters}, curves, band, fs))
    return results


def _bestfit_grown(pool, cfg, curves, mine, shelves, progress, cancel, shared):
    """bestfit() growing: one _grow_run per boost limit × Q limit; with your own filters (kept), one more result is
    yours alone. The progress: the filters added so far of the most every task can still add."""
    bf, band, fs, sc = cfg["best_fit"], cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"], cfg["scoring"]
    lo, hi = bf["freq_range"]
    stop = float(sc.get("ear_db", 0.25)) if sc.get("pick") == "audible" else None
    counts = sorted(set(bf["filter_counts"]))
    # (the widest limits first: they reach the target with the fewest filters, so the others can stop there sooner)
    tasks = [{"counts": counts, "freq_low": lo, "freq_high": hi, "gain_min": bf["gain_min"], "gain_max": gmax,
              "q_min": bf["q_min"], "q_max": qmax, "shelves": shelves, "mine": mine, "stop_ear": stop, "fight": fp}
             for gmax in sorted(bf["gain_max"], reverse=True) for qmax in sorted(bf["q_max"], reverse=True)
             for fp in fights(bf)]
    best_n, steps = shared or (None, None)
    say = None
    if progress:
        def say(_done, _total):
            reach = min(max(counts), best_n.value) if best_n is not None else max(counts)
            total = len(tasks) * reach
            progress(min(steps.value, total) if steps is not None else 0, total)
        say(0, 0)
    out = run_tasks(pool, _grow_run, tasks, say, cancel)
    results = []

    def add(t, n, filters):
        results.append(finish({"engine": "bestfit", "rows": n, "freq_low": lo, "freq_high": hi, "gain_min": bf["gain_min"],
                               "gain_max": t["gain_max"], "q_min": bf["q_min"], "q_max": t["q_max"],
                               "low_shelf": shelves["low"], "high_shelf": shelves["high"], "yours": len(mine),
                               "keep": True, "layout": bf.get("layout", "any"), "fight": t.get("fight"),
                               "filters": filters}, curves, band, fs))
    for t, by_count in out:
        for n, filters in sorted(by_count.items()):
            add(t, n, filters)
    if mine:  # (your filters as they are: one result, scored)
        add(tasks[0] if tasks else {"gain_max": max(bf["gain_max"]), "q_max": max(bf["q_max"])}, 0,
            [dict(f) for f in mine])
    if not results:  # (no task could place a filter: an EQ with none, so there's still a result to show)
        add(tasks[0], 0, [])
    return results


# ---------------------------------------------------------------- fixed bands (a graphic EQ)
def graphic_run(cfg, curves):
    """Best fit for a fixed-band layout (layouts.py): the bands stay where they are and only the gains are fitted,
    within the sliders' range and each a multiple of their step. The fit is continuous first, then every gain is set
    to the nearest step and moved a step up or down while that lowers the error, so what you set on the sliders is
    exactly what was scored."""
    from scipy.optimize import least_squares
    from . import layouts
    bf, band, fs = cfg["best_fit"], cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"]
    freqs, q = layouts.bands(bf)
    freqs = [fc for fc in freqs if fc < 0.49 * fs]  # (a band above what the sample rate holds can't be made)
    lo, hi, step = layouts.sliders(bf)  # (a graphic EQ app's own range and steps kept)
    f = curves["f"]
    m = (f >= band[0]) & (f <= band[1])
    above = (f > band[1]) & (f <= GUARD_TOP)
    fs_all = np.concatenate([f[m], f[above]])
    nb, need = int(m.sum()), (curves["target"] - curves["meas"])[m]
    fc = np.array(freqs)[:, None]
    lam = np.sqrt(nb * 5e-5)  # (Best fit's gain penalty: a band that does nothing stays at 0 dB)
    # above the scored range the measurement isn't trusted: the EQ stays near 0 dB there (else a band up there, e.g.
    # 16 kHz when scoring to 10 kHz, goes to the sliders' end just to lift the range's top edge a little). Tried on
    # the sample (scored to 10 kHz): 0.1 / 0.2 / 0.3 gave 10 bands 0.93 / 0.94 / 0.94 dB, 31 bands 0.25 / 0.31 /
    # 0.40 dB, with at most +7.0 / +5.7 / +4.4 dB above the range (none: 0.85 and 0.24 dB, but +12 dB at 16 kHz)
    guard = 0.2 * np.sqrt(nb / max(1, int(above.sum())))

    def residual(gains):
        eq = filter_db("PK", fs_all[None, :], fc, np.asarray(gains)[:, None], q, fs).sum(axis=0)
        return np.concatenate([eq[:nb] - need, guard * eq[nb:], lam * np.asarray(gains)])

    def cost(gains):
        return float(np.sum(residual(gains) ** 2))

    sol = least_squares(residual, np.zeros(len(freqs)), bounds=(np.full(len(freqs), lo), np.full(len(freqs), hi)))
    stepped_lo, stepped_hi = np.ceil(lo / step - 1e-9) * step, np.floor(hi / step + 1e-9) * step
    gains = np.clip(np.round(sol.x / step) * step, stepped_lo, stepped_hi)
    best = cost(gains)
    for _ in range(50):  # a step up or down on each band, while that helps
        better = False
        for i in range(len(gains)):
            for d in (step, -step):
                trial = gains.copy()
                trial[i] = min(max(trial[i] + d, stepped_lo), stepped_hi)
                c = cost(trial)
                if c < best - 1e-12:
                    gains, best, better = trial, c, True
        if not better:
            break
    filters = [{"type": "PK", "freq": float(x) if x != int(x) else int(x), "gain": round(float(v), 2) + 0.0, "q": q}
               for x, v in zip(freqs, gains)]
    return [finish({"engine": "graphic", "layout": bf["layout"], "rows": len(freqs), "step": step, "gain_min": lo,
                    "gain_max": hi, "q_min": q, "q_max": q, "filters": filters}, curves, band, fs)]


# ---------------------------------------------------------------- selection
PRIORITY_KEYS = {"n_filters": "fewest filters", "max_q": "lowest max Q", "max_boost": "smallest max boost"}


def pick(results, scoring, curves=None, band=None):
    """'lowest': lowest error. 'audible' (the user's ask, 2026-10-12: as close to the target as possible without an
    audible difference; the only other choice since 1.0.9, when "simplest within 0.1 dB average error" went): the
    simplest whose sound is within the audible limit (scoring.ear_db) of the target (ear_error); when none can get
    that close, the simplest within the limit of the sound of the result that sounds closest (the lowest ear error),
    as close as the limits allow. Returns (chosen, lowest error, the audible pick's case: "target", "best" or None)."""
    best = min(results, key=lambda r: r["rms"])
    if scoring.get("pick", "audible") == "lowest" or curves is None or band is None or \
            not all("eq" in r for r in results):
        return best, best, None
    prio = scoring.get("priority", list(PRIORITY_KEYS))
    simpler = lambda r: tuple(x for k in prio for x in ((r[k], r["rows"]) if k == "n_filters" else (r[k],))) + (
        r["rms"], r.get("gain_max") or 0, r.get("q_max") or 0, r.get("freq_high") or 0, -(r.get("gain_min") or 0))
    limit = float(scoring.get("ear_db", 0.25))
    reach = [r for r in results if r.get("ear", float("inf")) <= limit]
    if reach:
        return min(reach, key=simpler), best, "target"
    near = min(results, key=lambda r: r.get("ear", float("inf")))
    ok = [r for r in results if ear_error(curves["f"], r["eq"] - near["eq"], band)[0] <= limit]
    return min(ok or [near], key=simpler), best, "best"
