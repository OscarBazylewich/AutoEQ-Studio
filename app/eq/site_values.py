"""The Website values of each graph website (More settings › Website): its 7 values (smoothing, normalization,
loudness table, AutoEQ treble start) and the facts of its AutoEQ panel (does it have gain and Q boxes, its fixed
ranges, its most filter rows), so that the two Website methods give what the website gives.

Measured 2026-11-24 on the 155 graph websites that the app knows: 19 different sets of the 7 values, so one preset
cannot be right for all of them; 101 websites have no Q boxes and 104 no gain boxes on their AutoEQ panel, so their
Q and gain ranges are fixed in their own equalizer.js (app\\tools\\site_values_survey.py made the table, BENCHMARKS.md
has the counts).

- The table: site_values.json beside this module (shipped, read on its "read" date) and the cache
  (cache\\site_values.json: a website read again, Online, by refresh). table_entry(url) gives the newer of the two.
- parse(texts): a website's values and panel from the texts of its page, config*.js, graphtool*.js and
  equalizer*.js (comments taken out first). A value that is not there, or out of the settings' limits, is missing:
  never guessed.
- Which values (resolve): "Other" ("custom") changes nothing. "The database of the measurement" ("auto") and a
  website by name ("site:<url>") give that website's values to the two Website methods only; Best fit (and a manual
  EQ) keep the app's own values (APP_VALUES: what every Best fit test used). With no website (a file, your own
  image, several databases) the Website methods use USUAL (the set of 80 of 144 websites). A missing value is taken
  from USUAL. Only with Automatic settings on, and never over a value that you typed (auto.manual).
- The fixed values (lock): a website with the classic AutoEQ panel but no gain boxes or no Q boxes always uses its
  own ranges, so a Website run uses them too, whatever the boxes hold; the boxes show them, off (ui\\eq_settings).
  The panel's own clamps (gain 20 dB, Q 5 on every website with those boxes) and its most filter rows apply too.
  A website with another panel (modernGraphTool, squig.link's own "EQ constraints") has no fixed values.
- refresh(url): Online only, at most every 30 days for a website, a failed try again after a day, a refusal (HTTP
  401 or 403) after 7 days; 5 s at most for each file; any error kept quiet (the older values stay). refresh_soon
  runs it in a thread of its own, so Use never waits for it.
No Qt and no numpy here: /api/auto, on the window's thread, uses lock() and notes().
"""
import copy
import datetime
import hashlib
import json
import os
import re
import threading
import time
import urllib.error

import net
import textfile

from . import databases
from . import paths
from . import rigs
from . import settings

KEYS = ("treble_start_from", "scale_smoothing", "smooth_level", "normalization", "norm_hz", "norm_db", "phon_table")
PATHS = ["site." + k for k in KEYS]
# (Settings' names for them, in the notes: the labels of More settings › Website without their units)
NAMES = {"treble_start_from": "AutoEQ TrebleStartFrom", "scale_smoothing": "Smoothing scale",
         "smooth_level": "Smoothing level", "normalization": "Normalization", "norm_hz": "Around",
         "norm_db": "Loudness", "phon_table": "Loudness tables"}
APP_VALUES = {k: settings.DEFAULTS["site"][k] for k in KEYS}  # (listener800's: the app's own, Best fit's)
USUAL = dict(settings.OLD_PROFILES["squig.link lab"])         # (80 of the 144 websites read in full)
# The classic panel of most websites (98 of 148 equalizer.js): frequency boxes only; its ranges when a website's own
# could not be read
USUAL_PANEL = {"freq_range": [20, 15000], "gain_range": [-12, 12], "q_range": [0.5, 2], "rows_max": 20}
# The panel's clamps where it has the boxes (graphtool_parts.js runAutoEQ: listener800's): gain ±20 dB, Q 5
BOX_CAPS = {"gain_cap": 20, "q_cap": 5}
SITE_MODES = ("site_single", "site_sweep")
# sha1 of equalizer.js from its autoeq function on (comments and spaces taken out): the code of 141 of the 148
# websites read on 2026-11-24, listener800's included (code_hash on its equalizer.js)
USUAL_CODE = "782fcd24dc82f13831a4583c93f864c7cee03f60"

TABLE_PATH = os.path.join(paths.APP, "site_values.json")
CACHE_PATH = os.path.join(paths.CACHE, "site_values.json")
MAX_AGE = 30 * 24 * 3600
FAILED_WAIT = 24 * 3600
REFUSED_WAIT = databases.RETRY_AFTER_DAYS * 24 * 3600
TIMEOUT = 5

_lock = threading.Lock()
_mem = {"table": None, "cache": None, "cache_path": None}
_threads = []  # (refresh_soon's: a test waits for them)


# ---------------------------------------------------------------- reading a website's files
def _first(pattern, text, flags=0):
    m = re.search(pattern, text or "", flags)
    return m.group(1) if m else None


def _number(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return int(v) if v == int(v) else v


def _pair(text, key):
    """[a, b] of `key: [a, b]` in equalizer.js, or None."""
    m = re.search(rf"\b{key}\s*:\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]", text or "")
    if not m:
        return None
    a, b = _number(m.group(1)), _number(m.group(2))
    return [a, b] if a is not None and b is not None and a <= b else None


def code_hash(equalizer_text):
    """The fingerprint of a website's AutoEQ code: equalizer.js from its autoeq function on, comments and spaces taken
    out (its settings above it differ from website to website), or None without one."""
    eq = databases.strip_comments(equalizer_text or "")
    m = re.search(r"\bautoeq\s*=\s*function|\bfunction\s+autoeq\b|\blet\s+autoeq\b|\bautoeq\s*=", eq)
    return hashlib.sha1(re.sub(r"\s+", "", eq[m.start():]).encode()).hexdigest() if m else None


def _valid(key, v):
    """v within the setting's limits or choices, else None (a value the app can't use counts as not read)."""
    path = "site." + key
    if path in settings.CHOICES:
        return v if v in settings.CHOICES[path] else None
    lim = settings.LIMITS.get(path)
    if not isinstance(v, (int, float)) or isinstance(v, bool) or lim and not lim["min"] <= v <= lim["max"]:
        return None
    return v


def parse(texts):
    """A website's row of the table from its files' texts ({"page", "config", "graphtool", "equalizer"}, each may be
    missing): {"values", "missing", "code", "panel", "panel_missing"} (the rules of the survey of 2026-11-24)."""
    raw = {k: (texts or {}).get(k) or "" for k in ("page", "config", "graphtool", "equalizer")}
    cfg, gt, eq = (databases.strip_comments(raw[k]) for k in ("config", "graphtool", "equalizer"))
    modern = bool(re.search(r"\bCONFIG\s*=\s*\{", cfg) and not re.search(r"\bDIR\s*=", cfg))
    v = {}
    if modern:  # (modernGraphTool keeps its levelling in CONFIG.NORMALIZATION)
        norm = _first(r"\bNORMALIZATION\s*:\s*\{[^}]*?\bTYPE\s*:\s*[\"']([^\"']*)", cfg, re.S)
        v["norm_hz"] = _number(_first(r"\bNORMALIZATION\s*:\s*\{[^}]*?\bHZ_VALUE\s*:\s*([\d.]+)", cfg, re.S))
        v["norm_db"] = _number(_first(r"\bNORMALIZATION\s*:\s*\{[^}]*?\bDB_VALUE\s*:\s*([\d.]+)", cfg, re.S))
    else:
        norm = _first(r"\bdefault_normalization\s*=\s*[\"']([^\"']*)[\"']", cfg)
        v["norm_hz"] = _number(_first(r"\bdefault_norm_hz\s*=\s*([\d.]+)", cfg))
        v["norm_db"] = _number(_first(r"\bdefault_norm_db\s*=\s*([\d.]+)", cfg))
    n = (norm or "").strip().lower()
    if n in ("db", "hz", "hz~"):  # (another word, modernGraphTool's "Avg", is not known: missing)
        # ("Hz~" only where the graph tool has its range mode: without it, the tool levels at one frequency)
        v["normalization"] = "dB" if n == "db" else "Hz~" if n == "hz~" and "norm_fr_range" in gt else "Hz"
    v["smooth_level"] = _number(_first(r"\bsmooth_level\s*=\s*([\d.]+)", gt))
    factor = _number(_first(r"\bsmooth_scale\s*=\s*([\d.]+)\s*\*", gt))
    scale = _number(_first(r"\bscale_smoothing\s*=\s*([\d.]+)", cfg))
    # (the app's own factor is 0.1, graphtool_parts.js setSiteConfig: the website's factor × its config's scale)
    v["scale_smoothing"] = _number(round(factor * (1 if scale is None else scale) / 0.1, 6)) if factor is not None else None
    table = _first(r"\biso223_params\s*=\s*(\{.*?\})\s*;", gt, re.S)
    first_af = _first(r"a_f\s*:\s*\[\s*([\d.]+)", table) if table else None
    v["phon_table"] = {"0.532": "ISO 226:2003", "0.635": "ISO 226:2023"}.get(first_af)
    v["treble_start_from"] = _number(_first(r"\bTrebleStartFrom\s*:\s*([\d.]+)", eq))
    values = {k: _valid(k, v.get(k)) for k in KEYS}
    row = {"values": {k: x for k, x in values.items() if x is not None},
           "missing": [k for k in KEYS if values[k] is None]}
    if eq:
        row["code"] = "usual" if code_hash(raw["equalizer"]) == USUAL_CODE else "other"
    elif modern or re.search(r"\bextraEQEnabled\s*=\s*true", cfg):
        row["code"] = "unknown"  # (its AutoEQ is somewhere the reading doesn't know)
    else:
        row["code"] = "none"  # (no equalizer.js and no AutoEQ: the website has no AutoEQ button)
    # the panel: the classic one has the boxes "autoeq-from" and "autoeq-to", and may have gain and Q boxes (in
    # graphtool.js, or in the page itself: Hangout.Audio's)
    both = raw["graphtool"] + raw["page"]
    row["panel"], row["panel_missing"] = None, []
    if eq and re.search(r"autoeq-(?:from|to)\b", both):
        p = {"freq_boxes": True, "gain_boxes": "autoeq-gain-to" in both, "q_boxes": "autoeq-q-to" in both,
             "freq_range": _pair(eq, "AutoEQRange"), "gain_range": _pair(eq, "OptimizeGainRange"),
             "q_range": _pair(eq, "OptimizeQRange"),
             "rows_max": _number(_first(r"\bextraEQBandsMax\s*=\s*(\d+)", cfg)) or USUAL_PANEL["rows_max"],
             "gain_cap": _number(_first(r"autoEQGainTo\s*=\s*Math\.min\(Math\.max\([^;]*?,\s*([\d.]+)\)\s*;", gt)),
             "q_cap": _number(_first(r"autoEQQTo\s*=\s*Math\.min\(Math\.max\([^;]*?,\s*([\d.]+)\)\s*;", gt))}
        row["panel_missing"] = [k for k in ("freq_range", "gain_range", "q_range") if p[k] is None]
        row["panel"] = p
    return row


# ---------------------------------------------------------------- the table and the cache
def _load_table():
    d = textfile.read_json(TABLE_PATH, {})
    sites = d.get("sites") if isinstance(d, dict) else None
    read = d.get("read") if isinstance(d, dict) else None
    return {"read": read if isinstance(read, str) else "", "sites": sites if isinstance(sites, dict) else {}}


def _tables():
    """(shipped table, cache), read once (the cache again when CACHE_PATH changes: a test's own folder)."""
    with _lock:
        if _mem["table"] is None:
            _mem["table"] = _load_table()
        if _mem["cache_path"] != CACHE_PATH:
            c = textfile.read_json(CACHE_PATH, {})
            _mem.update(cache=c if isinstance(c, dict) else {}, cache_path=CACHE_PATH)
        return _mem["table"], _mem["cache"]


def _day_time(day):
    try:
        return datetime.datetime.strptime(day, "%Y-%m-%d").timestamp()
    except (TypeError, ValueError):
        return 0.0


def table_entry(url):
    """The newest row of a website ({"name", "url", "values", "missing", "code", "panel", "panel_missing", "read",
    "time"}), or None when it was never read."""
    table, cache = _tables()
    key = databases.norm_url(url or "")
    shipped, mine = table["sites"].get(key), cache.get(key)
    best = None
    if isinstance(shipped, dict):
        best = dict(shipped, read=table["read"], time=_day_time(table["read"]))
    if isinstance(mine, dict) and isinstance(mine.get("values"), dict) and mine.get("time", 0) >= (best or {}).get("time", 0):
        best = dict(mine)
    return best


def site_name(url):
    """A website's name as the lists say it (the URL when it's not known)."""
    site = databases.find_site(url)
    if site:
        return site["name"]
    e = table_entry(url)
    return (e or {}).get("name") or (url or "").strip()


def is_graph_site(url):
    """A website with a graph and maybe an AutoEQ (not AutoEq on GitHub, a list of files)."""
    site = databases.find_site(url)
    return bool(url) and not (site and site.get("type") == "autoeq")


def choices(cfg=None):
    """Every graph website for the list "Which website to copy": [(value "site:<url>", name)], one per address: the
    table's, the app's lists' and the pages that you added (Find… › Sources…); not AutoEq (GitHub)."""
    table, _ = _tables()
    seen, out = set(), []
    added = [databases.added_site(u) for u in ((cfg or {}).get("databases", {}).get("extra") or [])
             if isinstance(u, str) and u.strip().startswith(("http://", "https://"))]
    for s in [*databases.all_sites(), *added, *table["sites"].values()]:
        url = s.get("url") if isinstance(s, dict) else None
        if not isinstance(url, str) or s.get("type") == "autoeq" or databases.norm_url(url) in seen:
            continue
        seen.add(databases.norm_url(url))
        out.append(("site:" + url, s.get("name") or url))
    return out


# ---------------------------------------------------------------- which website a measurement is from
def site_of(names):
    """(website URL or None, why) for the measurement files in use (their names in the app): only what the app
    recorded when it got them (sources.json: Use, a trace from a website, an average of measurements of one
    database), never a guess from a file name. why: "site", "file" (no website: dropped, your own image, AutoEq),
    "mixed" (more than one database) or "none" (no files)."""
    if not names:
        return None, "none"
    rec = rigs.sources()
    urls = []
    for n in names:
        r = rec.get(n) if isinstance(rec.get(n), dict) else {}
        if r.get("site") == "average":
            parts = r.get("of_sites")
            urls += parts if isinstance(parts, list) and parts else [None]  # (an average made before 2026-11-26: a file)
        else:
            urls.append(r.get("site_url"))
    urls = [u if isinstance(u, str) and is_graph_site(u) else None for u in urls]
    known = {databases.norm_url(u) for u in urls if u}
    if not known:
        return None, "file"
    if len(known) > 1 or None in urls:
        return None, "mixed"
    return next(u for u in urls if u), "site"


# ---------------------------------------------------------------- which values: resolve, apply, lock
def _sentences(parts):
    """One sentence: no period at its end; two or more: a period on each (the owner's style)."""
    parts = [p.rstrip(".") for p in parts if p]
    return parts[0] if len(parts) == 1 else " ".join(p + "." for p in parts)


def _range(lo, hi, unit=""):
    """-12 to 12 dB; Q 0.5–2 (a range with a negative end: "to")."""
    f = lambda x: f"{x:g}"
    return (f"{f(lo)} to {f(hi)}" if lo < 0 else f"{f(lo)}–{f(hi)}") + (f" {unit}" if unit else "")


def _locks(entry, name):
    """(locks {path: {"value", "tip"}}, panel caps, most rows, the sentence) for a website's panel."""
    p = (entry or {}).get("panel")
    if not isinstance(p, dict):
        return {}, None, None, ""
    gr = p.get("gain_range") or USUAL_PANEL["gain_range"]
    qr = p.get("q_range") or USUAL_PANEL["q_range"]
    locks, caps, said = {}, dict(BOX_CAPS), []
    if not p.get("gain_boxes"):
        tip = f"Fixed on {name} (no gain boxes on its AutoEQ panel)"
        locks.update({"site_single.gain_min": {"value": gr[0], "tip": tip},
                      "site_single.gain_max": {"value": gr[1], "tip": tip},
                      "site_sweep.gain_ranges": {"value": [[gr[0], gr[1]]], "tip": tip}})
        caps["gain_cap"] = max(abs(gr[0]), abs(gr[1]))
        said.append(("gain", f"gain {_range(gr[0], gr[1], 'dB')}"))
    elif p.get("gain_cap"):
        caps["gain_cap"] = p["gain_cap"]
    if not p.get("q_boxes"):
        tip = f"Fixed on {name} (no Q boxes on its AutoEQ panel)"
        locks.update({"site_single.q_min": {"value": qr[0], "tip": tip},
                      "site_single.q_max": {"value": qr[1], "tip": tip},
                      "site_sweep.q_min": {"value": qr[0], "tip": tip},
                      "site_sweep.q_max": {"value": [qr[1]], "tip": tip}})
        caps["q_cap"] = qr[1]
        said.append(("Q", f"Q {_range(qr[0], qr[1])}"))
    elif p.get("q_cap"):
        caps["q_cap"] = p["q_cap"]
    rows = p.get("rows_max") if isinstance(p.get("rows_max"), int) and p["rows_max"] < 20 else None
    what = " or ".join(k for k, _ in said)
    sentence = (f"No {what} boxes on its AutoEQ panel, so {' and '.join(t for _, t in said)} "
                f"{'is' if len(said) == 1 else 'are'} fixed") if said else ""
    return locks, caps, rows, sentence


FILE_NOTE = ("Measurement isn't from a database, so the usual squig.link values apply. To copy a website, select it "
             "in this list.")
MIXED_NOTE = ("Measurements are from more than one database, so the usual squig.link values apply. To copy a "
              "website, select it in this list.")
OTHER_NOTE = "Other: values below stay as you set them"
OFF_NOTE = "Automatic settings are off: values below stay as you set them"
BEST_FIT_NOTE = "Best fit keeps its own values; the database's values are for the Website methods"
HISTORY_NOTE = "Showing the values of the EQ from History"


def resolve(cfg, mode, names, as_is=False):
    """Which Website values a method uses for these measurement files (names in the app), and why: {"profile",
    "site_url", "site", "values" {path: value}, "applied" (written into the settings: Automatic settings on and not
    "Other"), "locks" {path: {"value", "tip"}}, "caps", "rows_max", "note" (the gray line)}. mode: the method whose
    values the curves use. as_is: the values as they are (an EQ from History shown on the curves it was made on)."""
    prof = cfg["site"].get("profile", "auto")
    on = bool(cfg["auto"].get("enabled", True))
    info = {"profile": prof, "site_url": None, "site": None, "values": {}, "applied": False, "locks": {}, "caps": None,
            "rows_max": None, "note": ""}
    if as_is:
        info["note"] = HISTORY_NOTE
        return info
    if prof == "custom":
        info["note"] = OTHER_NOTE
        return info
    if isinstance(prof, str) and prof.startswith("site:"):
        url, why = prof[5:], "site"
    else:
        url, why = site_of(names)
    entry = table_entry(url) if url else None
    name = site_name(url) if url else None
    info.update(site_url=url, site=name)
    locks, caps, rows, lock_sentence = _locks(entry, name) if url else ({}, None, None, "")
    info.update(locks=locks, caps=caps, rows_max=rows)
    website = mode in SITE_MODES
    if not website:
        values = dict(APP_VALUES)
    elif url:
        values = dict(USUAL, **(entry or {}).get("values", {}))
    else:
        values = dict(USUAL)
    info["values"] = {"site." + k: v for k, v in values.items()}
    info["applied"] = on
    if not on:
        info["note"] = _sentences([OFF_NOTE, lock_sentence if website else ""])
    elif not website:
        info["note"] = BEST_FIT_NOTE
    elif url:
        parts = [f"{name}: values from its website (read {entry['read']})" if entry else
                 f"{name}: values not read yet, so the usual squig.link values apply"]
        code = (entry or {}).get("code")
        # (a website with no AutoEQ has no TrebleStartFrom to read: not said as missing)
        missing = [NAMES[k] for k in (entry or {}).get("missing", [])
                   if not (code == "none" and k == "treble_start_from")] if entry else []
        if missing:
            listed = ", ".join(missing[:-1]) + " and " + missing[-1] if len(missing) > 1 else missing[0]
            parts.append(f"Couldn't read {listed}, so {'these use' if len(missing) > 1 else 'it uses'} the usual "
                         "squig.link values")
        if code == "other":
            parts.append("Runs changed AutoEQ code, so results may differ from the website")
        elif code == "none":
            parts.append("No AutoEQ button on its website")
        parts.append(lock_sentence)
        if rows:
            parts.append(f"Up to {rows} filter rows on its AutoEQ panel")
        info["note"] = _sentences(parts)
    else:
        info["note"] = MIXED_NOTE if why == "mixed" else FILE_NOTE if why == "file" else ""
    return info


def apply(cfg, mode, names, as_is=False):
    """resolve(), and its values written into cfg (not the settings that you set yourself: auto.manual)."""
    info = resolve(cfg, mode, names, as_is)
    if info["applied"]:
        manual = set(cfg["auto"].get("manual") or [])
        for path, v in info["values"].items():
            if path not in manual:
                settings.set_path(cfg, path, v)
    return info


def _info_ok(info):
    return isinstance(info, dict) and isinstance(info.get("locks"), dict)


# The settings a website's panel can fix, and the form of each value
LOCK_PATHS = {"site_single.gain_min": "n", "site_single.gain_max": "n", "site_single.q_min": "n", "site_single.q_max": "n",
              "site_sweep.gain_ranges": "ranges", "site_sweep.q_min": "n", "site_sweep.q_max": "list"}


def _number_ok(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _lock_value_ok(path, v):
    kind = LOCK_PATHS[path]
    if kind == "n":
        return _number_ok(v)
    if kind == "list":
        return isinstance(v, list) and bool(v) and all(map(_number_ok, v))
    return (isinstance(v, list) and bool(v) and all(isinstance(r, list) and len(r) == 2 and all(map(_number_ok, r))
                                                     and r[0] <= r[1] for r in v))


def lock(cfg, info, mode):
    """A run's settings (a copy: changed and returned) with the website's fixed values, its panel's clamps
    (cfg["panel"]: engines.js_site_cfg) and its most filter rows, for a Website method. info: resolve()'s."""
    if mode not in SITE_MODES or not _info_ok(info):
        return cfg
    for path, x in info["locks"].items():
        value = x.get("value") if isinstance(x, dict) else None
        if path in LOCK_PATHS and path.split(".")[0] == mode and _lock_value_ok(path, value):
            settings.set_path(cfg, path, copy.deepcopy(value))
    caps = info.get("caps")
    if isinstance(caps, dict):
        cfg["panel"] = {k: caps[k] for k in ("gain_cap", "q_cap") if _number_ok(caps.get(k)) and caps[k] > 0}
    top = info.get("rows_max")
    if isinstance(top, int) and not isinstance(top, bool) and top > 0:
        if mode == "site_single":
            cfg["site_single"]["rows"] = min(cfg["site_single"]["rows"], top)
        else:
            cfg["site_sweep"]["filter_rows"] = [r for r in cfg["site_sweep"]["filter_rows"] if r <= top] or [top]
    return cfg


def notes(info, mode):
    """About these settings' lines for the fixed values ({"path", "text", "lock": True}: shown as they are, a value
    that you typed is not used)."""
    if mode not in SITE_MODES or not _info_ok(info):
        return []
    out, name = [], info.get("site") if isinstance(info.get("site"), str) else ""
    v = {p: x["value"] for p, x in info["locks"].items() if isinstance(x, dict) and "value" in x}
    num = lambda *xs: all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in xs)
    first = lambda x: x[0] if isinstance(x, list) and x else None
    if mode == "site_single":
        g, q, rows_path = ("site_single.gain_max", "site_single.q_max", "site_single.rows")
        gv = [v.get("site_single.gain_min"), v.get(g)]
        qv = [v.get("site_single.q_min"), v.get(q)]
    else:
        g, q, rows_path = ("site_sweep.gain_ranges", "site_sweep.q_max", "site_sweep.filter_rows")
        gv = first(v.get(g)) or [None, None]
        qv = [v.get("site_sweep.q_min"), first(v.get(q))]
    if isinstance(gv, list) and len(gv) == 2 and num(*gv):
        out.append({"path": g, "text": f"Gain {_range(gv[0], gv[1], 'dB')}: fixed on {name} (no gain boxes)", "lock": True})
    if num(*qv):
        out.append({"path": q, "text": f"Q {_range(qv[0], qv[1])}: fixed on {name} (no Q boxes)", "lock": True})
    if isinstance(info.get("rows_max"), int) and not isinstance(info["rows_max"], bool):
        out.append({"path": rows_path, "text": f"Up to {info['rows_max']} filter rows (website limit)", "lock": True})
    return out


# ---------------------------------------------------------------- reading a website again (Online)
def _save_cache(cache):
    textfile.write_json(CACHE_PATH, cache, indent=1)


def due(url, now=None):
    """Should the website's values be read again now? (Online, its newest row older than MAX_AGE, and no failed try
    in the last day, nor a refusal in the last 7 days.)"""
    if net.offline() or not url or not is_graph_site(url):
        return False
    now = time.time() if now is None else now
    e = table_entry(url)
    if e and now - e.get("time", 0) < MAX_AGE:
        return False
    _, cache = _tables()
    mine = cache.get(databases.norm_url(url))
    if isinstance(mine, dict) and mine.get("failed"):
        wait = REFUSED_WAIT if mine.get("refused") else FAILED_WAIT
        if now - mine["failed"] < wait:
            return False
    return True


def refresh(url, get=None, now=None):
    """Read a website's values again when due(): its page and three scripts (databases.graph_tool_files, through
    net.check), kept in the cache. Returns "read", "failed", "refused" or "skipped"; never raises."""
    if not due(url, now):
        return "skipped"
    now = time.time() if now is None else now
    key = databases.norm_url(url)
    site = databases.find_site(url) or {"url": url, "name": site_name(url)}
    try:
        texts = databases.graph_tool_files(site, get=get, timeout=TIMEOUT)
        row = parse(texts)
        row.update(name=site.get("name") or url, url=site.get("url") or url, time=now,
                   read=datetime.date.fromtimestamp(now).isoformat())
        result = "read"
    except urllib.error.HTTPError as e:
        row = {"failed": now, "refused": e.code in databases.REFUSED}
        result = "refused" if row["refused"] else "failed"
    except Exception:  # noqa: BLE001 - kept quiet: the older values stay (offline, a slow or changed website)
        row = {"failed": now, "refused": False}
        result = "failed"
    with _lock:
        cache = dict(_mem["cache"] or {})
        old = cache.get(key)
        if "failed" in row and isinstance(old, dict) and isinstance(old.get("values"), dict):
            row = dict(old, failed=row["failed"], refused=row["refused"])  # (the values read before stay)
        cache[key] = row
        _mem["cache"] = cache
        try:
            _save_cache(cache)
        except OSError:
            pass
    return result


def refresh_soon(url):
    """refresh() in a thread of its own when due (Use and a trace from a website go on at once). The download
    function is taken now, so the thread uses the one in place at the request."""
    if not due(url):
        return None
    get = databases.get_function()
    t = threading.Thread(target=refresh, args=(url, get), daemon=True, name="site-values")
    _threads[:] = [x for x in _threads if x.is_alive()] + [t]
    t.start()
    return t


def wait(timeout=30):
    """Wait for refresh_soon's threads to end (a test; the app never waits for them)."""
    for t in list(_threads):
        t.join(timeout)


def valid(key, v):
    """Is v a value the app can use for the Website value key (within its limits or choices)?"""
    return _valid(key, v) is not None and _valid(key, v) == v


def forget_memory():
    """The table and the cache read again at their next use (a test that changes the files)."""
    with _lock:
        _mem.update(table=None, cache=None, cache_path=None)


def table_json(rows, read):
    """The shipped table's text: {"read", "sites": {norm_url: row}} in a stable order."""
    sites = {databases.norm_url(r["url"]): r for r in sorted(rows, key=lambda r: databases.norm_url(r["url"]))}
    return json.dumps({"read": read, "sites": sites}, indent=1, ensure_ascii=False, sort_keys=False) + "\n"
