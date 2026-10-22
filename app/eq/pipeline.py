"""Loading the curves and running the EQ methods (for service.py, the app's one way in to the EQ part).

load()      the measurement files and the target, read and averaged the way squiglink does (engines.load_curves),
            with the target converted to the measurement's rig when they differ (rigconv.py)
run_mode()  one EQ method over those curves: its results, the one picked and the lowest-error one. The site's runs
            and Best fit's fits use a pool of worker processes (workers()).
"""
import copy
import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import engines
from . import exports
from . import inputs
from . import layouts
from . import rigconv
from . import settings

MODES = settings.MODES


def rig_status(cfg, target_path, meas_paths):
    """The measurement's and the target's rigs, and the conversion between them if there is one (never fails)."""
    try:
        return rigconv.status(cfg, target_path, meas_paths)
    except Exception as e:  # noqa: BLE001 - a rig lookup problem mustn't stop the curves loading
        return {"state": "unknown", "applied": False, "error": str(e)}


def load(cfg, target_path, meas_paths):
    """(curves, measurement texts, target text). curves: {"f", "meas", "target", "channels", "rig", …} (numpy arrays
    on the site's frequency grid); the target text is the converted one when the rig conversion applies."""
    meas_texts = [inputs.read_text(p) for p in meas_paths]
    target_text = inputs.read_text(target_path)
    rig = rig_status(cfg, target_path, meas_paths)
    if rig.get("applied"):  # the target converted to the measurement's rig: every method and score uses it
        target_text = rigconv.convert_text(target_text, rig["conversion"])
    curves = engines.load_curves(cfg, meas_texts, target_text)
    curves["rig"] = rig
    _LAST_TEXTS.update(key=_files_key(cfg, target_path, meas_paths), texts=(meas_texts, target_text))
    return curves, meas_texts, target_text


# The texts load() read last, by the files, their times and the rig conversion switch: sweep_cached() is asked for
# every time estimate (several per change of settings) and uses them instead of reading every file again
_LAST_TEXTS = {}


def _files_key(cfg, target_path, meas_paths):
    return (bool(cfg["rig_convert"]["enabled"]), target_path, os.path.getmtime(target_path),
            tuple((p, os.path.getmtime(p)) for p in meas_paths))


# ---------------------------------------------------------------- worker processes
def cpu_threads():
    """CPU threads this process may use (Python 3.13+: as Windows allows it, e.g. under an affinity limit)."""
    count = getattr(os, "process_cpu_count", None) or os.cpu_count
    return count() or 1


def free_memory():
    """Bytes of RAM free right now (Windows), or None."""
    try:
        import ctypes

        class Status(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + \
                       [(n, ctypes.c_ulonglong) for n in ("total", "avail", "total_page", "avail_page", "total_virtual",
                                                          "avail_virtual", "avail_ext")]
        s = Status(); s.dwLength = ctypes.sizeof(Status)
        return s.avail if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)) else None
    except (AttributeError, OSError, ImportError):
        return None


WORKER_RAM = 160 * 2**20  # about what a worker process uses (Python, numpy, scipy and V8 for the site's maths)
MAX_WORKERS = 61          # Windows' limit for a process pool


def workers(cfg):
    """Worker processes for a run: the setting, else one less than the CPU threads; never more than the free RAM
    holds (a PC with little memory would otherwise start swapping) or Windows allows. AUTOEQSTUDIO_MAX_WORKERS (the
    tests) caps it."""
    n = cfg["performance"].get("cores") or 0
    n = n if n > 0 else cpu_threads() - 1
    ram = free_memory()
    if ram:
        n = min(n, max(1, int(ram * 0.8 // WORKER_RAM)))
    cap = os.environ.get("AUTOEQSTUDIO_MAX_WORKERS", "")  # (the tests' cap: several test runs side by side)
    if cap.isdigit() and int(cap) > 0:
        n = min(n, int(cap))
    return max(1, min(n, MAX_WORKERS))


# ---------------------------------------------------------------- running
def band_problem(curves, band):
    """Why the scored range can't be used (it has no curve points), or None."""
    f = curves["f"]
    if ((f >= band[0]) & (f <= band[1])).sum() >= 2:
        return None
    return (f"The scored range ({band[0]:g}–{band[1]:g} Hz) has no data: the curves run from 20 Hz to 20 kHz. "
            f"Change “Score from” or “Score to”.")


def check_run(mode, cfg, curves):
    """A clear message for settings a run can't use, instead of an error from deep inside the method."""
    problem = band_problem(curves, cfg["scoring"]["band_hz"])
    if problem:
        raise ValueError(problem)
    used = {mode, "scoring"}
    for lo, hi, strict in settings.LIMIT_PAIRS:
        if lo.split(".")[0] not in used:
            continue
        if settings.pair_wrong(cfg, lo, hi, strict):
            a, b = settings.get_path(cfg, lo), settings.get_path(cfg, hi)
            b = min(b) if isinstance(b, list) else b
            raise ValueError(f"{settings.PAIR_NAMES.get(lo, lo)}: “from” ({a:g}) must be {'below' if strict else 'at most'} "
                             f"“to” ({b:g}).")
    if "site_sweep" in used and engines.sweep_size(cfg["site_sweep"]) > engines.MAX_SITE_RUNS:
        raise ValueError(f"These settings make {engines.sweep_size(cfg['site_sweep']):,} website runs (filter rows × "
                         f"frequency “to” values × gain ranges × Q limits); at most {engines.MAX_SITE_RUNS:,}. "
                         f"Use fewer values in those boxes.")
    fixed = mode == "best_fit" and layouts.is_fixed(cfg["best_fit"]["layout"])
    if fixed:
        freqs = layouts.bands(cfg["best_fit"])[0]
        if not freqs:
            raise ValueError("Your own bands: enter at least one band frequency.")
        return
    if mode != "best_fit":
        return
    bf = cfg["best_fit"]
    n_mine = len(exports.parse_filters(bf.get("start_filters", "")))  # (says which line it can't read)
    if engines.fit_count(bf, n_mine) > engines.MAX_FITS:
        raise ValueError(f"These settings make {engines.fit_count(bf, n_mine):,} fits (filter counts × max boosts × "
                         f"Q limits); at most {engines.MAX_FITS:,}. Use fewer values in those boxes.")
    room = layouts.capacity(bf["layout"])
    if room is not None and n_mine > room:  # (more than the device holds whatever is added)
        raise ValueError(f"Your {n_mine} filters are more than {layouts.name(bf['layout'])} holds ({room}): remove some "
                         f"in Best fit's “Start from your own filters”.")


# The last few site sweeps' results, by their inputs and settings. The site's AutoEQ gives the same result for the
# same curves and settings every time, so a sweep that was just run isn't run again: running the same sweep again is
# instant. (Best fit took its starting points from a sweep until 1.0.9: it starts from none now.)
_SWEEPS = {}
_SWEEPS_KEPT = 4


def _sweep_key(cfg, meas_texts, target_text):
    blob = json.dumps([meas_texts, target_text, cfg["site"], cfg.get("target_adjust"), cfg["site_sweep"], cfg["scoring"]],
                      sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8", "replace")).hexdigest()


def _remember_sweep(key, results):
    _SWEEPS.pop(key, None)
    _SWEEPS[key] = copy.deepcopy(results)
    while len(_SWEEPS) > _SWEEPS_KEPT:
        _SWEEPS.pop(next(iter(_SWEEPS)))


def sweep_cached(cfg):
    """Has the site sweep for the selected files and these settings been run recently (so a run needn't repeat it)?"""
    if not _SWEEPS:
        return False
    try:
        target, meas = inputs.selected(cfg)
        if _LAST_TEXTS.get("key") == _files_key(cfg, target, meas):
            meas_texts, target_text = _LAST_TEXTS["texts"]  # (the target converted as the run converts it)
        else:
            meas_texts, target_text = [inputs.read_text(p) for p in meas], inputs.read_text(target)
        return _sweep_key(cfg, meas_texts, target_text) in _SWEEPS
    except (OSError, ValueError, KeyError):
        return False


def run_mode(mode, cfg, curves, meas_texts, target_text, progress=None, cancel=None, seeds=()):
    """Run one EQ method. progress(done, total, message) reports as it goes; cancel (an Event) stops it (raises
    engines.Cancelled). seeds: site results for Best fit to start from (none since 1.0.9: none are run for it).
    Returns {"results": [...], "pick": the one picked, "best": the lowest error, "reused_sweep": site runs reused}."""
    say = progress or (lambda *a: None)
    check_run(mode, cfg, curves)
    reused = False
    if mode == "site_single":
        say(0, 1, "Running squiglink AutoEQ")
        results = engines.site_single(cfg, curves, meas_texts, target_text)
    elif mode == "site_sweep":
        results, reused = _site_sweep(cfg, curves, meas_texts, target_text, say, cancel)
    elif mode == "best_fit" and layouts.is_fixed(cfg["best_fit"]["layout"]):
        say(0, 1, f"Fitting the gains of the {layouts.name(cfg['best_fit']['layout'])}")
        results = engines.graphic_run(cfg, curves)
    elif mode == "best_fit":
        cfg = copy.deepcopy(cfg)  # (a device layout: Best fit's settings within the device's)
        bf = cfg["best_fit"]
        # (your own filters, kept or adjusted, are in every result: they take room from the device's)
        cfg["best_fit"] = layouts.device_settings(bf, len(exports.parse_filters(bf.get("start_filters", ""))))
        results, reused = _best_fit(cfg, curves, meas_texts, target_text, say, cancel, seeds)
    else:
        raise ValueError(f"Unknown mode {mode}")
    # parallel runs finish in any order: sort by settings so ids and ties are repeatable (the fighting-filter penalty
    # too: the two penalties' results swapped ids from run to run)
    results.sort(key=lambda r: tuple(r.get(k) or 0 for k in ("rows", "freq_high", "gain_min", "gain_max", "q_max",
                                                              "fight")))
    for i, r in enumerate(results):
        r["id"] = i
        r["mode"] = mode
    chosen, best, case = engines.pick(results, cfg["scoring"], curves, cfg["scoring"]["band_hz"])
    return {"results": results, "pick": chosen, "best": best, "pick_case": case, "reused_sweep": reused}


def _site_sweep(cfg, curves, meas_texts, target_text, say, cancel):
    """(results, reused): the site's AutoEQ for every combination of the sweep's settings."""
    key = _sweep_key(cfg, meas_texts, target_text)
    if key in _SWEEPS:
        say(1, 1, "The same squiglink AutoEQ runs as a moment ago: using their results")
        return copy.deepcopy(_SWEEPS[key]), True
    combos = engines.site_combos(cfg["site_sweep"])
    say(0, len(combos), f"Starting {len(combos)} squiglink AutoEQ runs")
    with ProcessPoolExecutor(workers(cfg), initializer=engines.site_worker_init,
                             initargs=(cfg, meas_texts, target_text)) as pool:
        results = engines.site_sweep(pool, cfg, curves, lambda d, t: say(d, t, f"squiglink AutoEQ runs: {d}/{t}"), cancel)
    _remember_sweep(key, results)
    return results, False


def _best_fit(cfg, curves, meas_texts, target_text, say, cancel, seeds):
    """(results, reused): Best fit's fits in a pool of worker processes (seeds: site results to start from, when a
    caller gives them; the "Seed with site results" setting went in 1.0.9: it changed nothing measurable)."""
    bf = cfg["best_fit"]
    # (each task sets its own fighting-filter penalty: the workers start with the first)
    penalties = {"gain_penalty": bf["gain_penalty"], "fight_penalty": engines.fights(bf)[0],
                 "treble_guard": bf["treble_guard"]}
    shared = engines.grow_shared() if engines.grows(bf) else None  # (growing fits stop where another reached the target)
    bf_args = (curves, cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"], penalties, shared)
    with ProcessPoolExecutor(workers(cfg), initializer=engines.bestfit_worker_init, initargs=bf_args) as pool:
        msg = "Adding filters one at a time" if shared else "Fits"
        results = engines.bestfit(pool, cfg, curves, seeds, lambda d, t: say(d, t, f"{msg}: {d}/{t}"), cancel, shared)
    return results, False


def result_summary(r):
    """JSON-safe view of a result (no curves)."""
    keys = ["id", "mode", "engine", "rows", "freq_low", "freq_high", "gain_min", "gain_max", "q_min", "q_max",
            "q_max_effective", "layout", "step", "low_shelf", "high_shelf", "filters", "preamp", "rms", "n_filters",
            "max_q", "max_boost", "yours", "keep", "ear", "ear_at"]
    return {k: (float(r[k]) if isinstance(r.get(k), (np.floating,)) else r[k]) for k in keys if k in r}
