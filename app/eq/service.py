"""What the EQ part does, for the rest of the app: one function per thing to do (see ROUTES), each taking a dict and
answering one. Most take the current settings in body["settings"] (cfg_from()). call() runs one and turns an error
into {"error": message}; handle() lets it raise.

This was AutoEQ Local's page's API (its /api/... addresses, over its own web server); the addresses are kept as the
names, so the behaviour, its checks and AutoEQ Local's code stay comparable. What only the browser page needed is
gone: the heartbeat and "bye" (the window telling the server it's open), opening a browser window, the list of
browsers.

Groups: state and settings · the app's files · this PC and the online databases · which measurement to use ·
runs · saving (files, report) · presets · history (past EQs) · opening the app's folders.
"""
import copy
import html
import os
import threading
import time
import traceback
import uuid

import net

from . import autoset
from . import compare
from . import databases
from . import engines
from . import exports
from . import history
from . import inputs
from . import eq_apps
from . import layouts
from . import library
from . import listening
from . import paths
from . import pipeline
from . import report
from . import rigconv
from . import rigmap
from . import rigs
from . import settings
import textfile

ROUTES = {}


class UnknownApi(Exception):
    pass


def route(path):
    def add(fn):
        ROUTES[path] = fn
        return fn
    return add


def handle(path, body):
    """The answer for one request. Any answer carrying the app's files ("inputs") gets each file's rig tag too."""
    fn = ROUTES.get(path)
    if fn is None:
        raise UnknownApi(path)
    res = fn(body)
    if isinstance(res, dict) and isinstance(res.get("inputs"), dict):
        res["inputs"]["rigs"] = rigs.inputs_rigs(res["inputs"])
    aside = textfile.take_set_aside()  # (history.json, listen.json or settings.json couldn't be read: the page says so)
    if aside:
        if isinstance(res, dict):
            res["set_aside"] = aside
        for fn in list(SET_ASIDE):
            fn(aside)
    return res


SET_ASIDE = []  # fn(text) for each file set aside (the window says it: called from whichever thread met it)


def call(path, body=None):
    """handle(), with an error as the answer {"error": message} (as AutoEQ Local's server answered the page): a
    missing field says which, anything else its own message. The details go to the log."""
    try:
        return handle(path, body if isinstance(body, dict) else {})
    except UnknownApi as e:
        return {"error": f"unknown {e}"}
    except KeyError as e:
        traceback.print_exc()
        return {"error": f"Missing {e} in the request."}
    except net.Offline as e:  # (expected while offline: the message is enough, no traceback in the log)
        return {"error": str(e)}
    except Exception as e:  # noqa: BLE001 - shown to the user
        traceback.print_exc()
        return {"error": str(e) or type(e).__name__}


def cfg_from(body):
    """The settings the page sent (completed and checked), else the saved ones."""
    if isinstance(body.get("settings"), dict):
        return settings.with_auto(body["settings"])
    return settings.load()


def text_of(body, key):
    """A text field of the request (a clear message, not a Python error, when it's missing or isn't text)."""
    v = body.get(key)
    if not isinstance(v, str):
        raise ValueError(f"Missing {key} in the request.")
    return v


def names_of(body):
    """The file names a request is about: "names" (a list) or one "name"."""
    names = body.get("names") or [text_of(body, "name")]
    if not (isinstance(names, list) and all(isinstance(n, str) for n in names)):
        raise ValueError("Missing names in the request.")
    return names


def kind_of(body):
    if body.get("kind") not in ("target", "measurement"):
        raise ValueError("The request doesn't say target or measurement.")
    return body["kind"]


def open_path(path):
    os.startfile(path)


# ---------------------------------------------------------------- state and settings
@route("/api/state")
def state(body):
    """Everything the page needs to start: the settings and their limits, the files, the choices it offers."""
    cfg = settings.load()
    return {"settings": cfg, "defaults": settings.DEFAULTS, "inputs": inputs.state(cfg),
            "modes": settings.MODES, "presets": settings.list_presets(), "profiles": settings.SITE_PROFILES,
            "layouts": layouts.listing(), "eq_apps": eq_apps.listing(), "cpu_count": pipeline.cpu_threads(),
            "limits": {**settings.LIMITS, **settings.UI_LIMITS}, "limit_pairs": settings.LIMIT_PAIRS,
            "auto_paths": settings.AUTO_PATHS,
            "output_dir": exports.OUTPUT_DIR, "library_defaults": library.default_folders(),
            "home": os.path.expanduser("~"),
            "database_sites": [{"name": s["name"], "url": s["url"], "on": s.get("on", True), "browse": bool(s.get("browse")),
                                "group": s.get("group", "added"), "short": s["short"], "form": databases.site_form(s),
                                "folder": databases.folder_name(s["name"])} for s in databases.all_sites()],
            "database_groups": list(databases.GROUPS.items()),  # in order ("5128" would sort first in a JS object)
            "downloads_dir": databases.DOWNLOAD_DIR, "rigs": rigs.RIGS,
            "rig_example": rigconv.example(), "rig_notes": rigmap.site_notes(), "unit_convs": rigconv.page_units()}


@route("/api/settings")
def save_settings(body):
    cfg = cfg_from(body)
    settings.save(cfg)
    return {"inputs": inputs.state(cfg)}


@route("/api/reset")
def reset(body):
    """Every setting back to its default; the files stay as they are."""
    cfg = settings.load()
    new = settings.merge(settings.DEFAULTS, {"files": cfg["files"]})
    settings.save(new)
    return {"settings": new}


@route("/api/curves")
def curves(body):
    """The measurement and target as the graph shows them, the error without EQ and the rig note. What the automatic
    settings make of them comes from /api/analysis: it needs SciPy, slow to load at the app's start, and the graph
    mustn't wait for it."""
    cfg = cfg_from(body)
    target, meas = inputs.selected(cfg)
    c, _, _ = pipeline.load(cfg, target, meas)
    band = cfg["scoring"]["band_hz"]
    problem = pipeline.band_problem(c, band)
    return {"f": c["f"].tolist(), "meas": c["meas"].tolist(), "target": c["target"].tolist(),
            "channels": [ch.tolist() for ch in c["channels"]],
            "channel_names": [os.path.basename(p) for p in meas],
            "name": inputs.device_name([os.path.basename(p) for p in meas]),
            "target_name": os.path.splitext(os.path.basename(target))[0],
            "no_eq_rms": None if problem else engines.rms_error(c["f"], c["meas"], c["target"], band),
            "band_problem": problem, "rig": _rig_note(c)}


@route("/api/analysis")
def analysis(body):
    """What the automatic settings make of the chosen measurement and target (autoset.analyse)."""
    cfg = cfg_from(body)
    target, meas = inputs.selected(cfg)
    c, meas_texts, target_text = pipeline.load(cfg, target, meas)
    an = autoset.analyse(cfg, c, meas_texts)
    an["key"] = autoset.analysis_key(cfg, meas_texts, target_text)  # (a run checks it's for its own curves)
    return an


def _rig_note(c):
    """The rig note for the page: the rigs, and when converting, the conversion and its uncertainty on the curves'
    frequencies (the graph draws the uncertainty around the target)."""
    r = dict(c.get("rig") or {})
    for k in ("conversion", "uncertainty", "mismatch"):
        if k in r:
            r[k] = [round(v, 2) for v in rigconv.on_grid(r[k], c["f"])]
    r["names"] = rigs.RIGS
    return r


@route("/api/auto")
def auto(body):
    """The automatic values, their reasons, and the run-time estimate."""
    return autoset.auto_result(cfg_from(body), body.get("analysis"))


# ---------------------------------------------------------------- the app's files
def _use_measurements(cfg, names):
    """Only these measurement files ticked."""
    st = inputs.state(cfg)
    cfg["files"]["excluded"] = [m["name"] for m in st["measurements"] if m["name"] not in names]


@route("/api/files/add")
def files_add(body):
    """A dropped or browsed file into the app: a target becomes the target in use, a measurement is ticked. "files"
    ([{name, content}]) adds a set at once (a traced device's channels): one number for all when names are taken, so
    they stay one device."""
    cfg = cfg_from(body)
    many = body.get("files")
    if isinstance(many, list) and many:
        if not all(isinstance(f, dict) and isinstance(f.get("name"), str) and isinstance(f.get("content"), str)
                   for f in many):
            raise ValueError("Each file needs a name and its text.")
        files = [(f["name"], f["content"]) for f in many]
    else:
        files = [(text_of(body, "name"), text_of(body, "content"))]
    kind = inputs.guess_kind(files[0][0]) if body.get("kind") in (None, "", "auto") else kind_of(body)
    where = inputs.folder(kind)
    had = set(os.listdir(where)) if os.path.isdir(where) else set()
    names = inputs.add_files(kind, files)
    # (new files: not the database a file of that name once came from; one the app already had keeps its record)
    rigs.forget_source([n for n in names if n not in had])
    if kind == "target":
        cfg["files"]["active_target"] = names[0]
    else:
        cfg["files"]["excluded"] = [n for n in cfg["files"]["excluded"] if n not in names]
    settings.save(cfg)
    return {"kind": kind, "name": names[0], "names": names, "settings": cfg, "inputs": inputs.state(cfg)}


ADJUST_GAINS = ("tilt", "bass_gain", "halftilt_gain", "ear_gain", "treble_gain", "air_gain")


@route("/api/target/save")
def target_save(body):
    """The target as adjusted (the Target card's Adjust) saved as a target of its own and put in use, the
    adjustments back to 0 (they're in it now). Made for the target's own rig: before any rig conversion, and recorded
    with that rig, so it's converted for a measurement as the original was (2026-10-08, AutoEQ Studio)."""
    cfg = cfg_from(body)
    name = text_of(body, "name").strip()
    if not name:
        raise ValueError("Give the target a name.")
    target, meas = inputs.selected(cfg)
    if not any(cfg["target_adjust"].get(k) for k in ADJUST_GAINS):
        raise ValueError("The target isn't adjusted: there's nothing to save.")
    plain = copy.deepcopy(cfg)
    plain["rig_convert"]["enabled"] = False
    c, _, _ = pipeline.load(plain, target, meas)
    text = "frequency,raw\n" + "".join(f"{f:.2f},{v:.3f}\n" for f, v in zip(c["f"], c["target"]))
    before = copy.deepcopy(cfg)
    fname = inputs.add_file("target", name + ".csv", text)
    rig, _how = rigs.target_rig(os.path.basename(target))
    if rig:
        rigs.record_source([fname], {"site": f"your adjustments of {os.path.splitext(os.path.basename(target))[0]}",
                                     "rig": rig})
    else:
        rigs.forget_source([fname])
    cfg["files"]["active_target"] = fname
    for k in ADJUST_GAINS:
        cfg["target_adjust"][k] = 0.0
    settings.save(cfg)
    return {"name": fname, "settings": cfg, "before": before, "inputs": inputs.state(cfg)}


@route("/api/files/remove")
def files_remove(body):
    cfg = cfg_from(body)
    for n in names_of(body):
        inputs.remove_file(kind_of(body), n)
    rigs.forget_source(names_of(body))
    settings.save(cfg)
    return {"inputs": inputs.state(cfg)}


@route("/api/files/move")
def files_move(body):
    """A file put in the wrong box: from the Target folder to the Measurement folder, or back."""
    cfg = cfg_from(body)
    name = inputs.move_file(kind_of(body), text_of(body, "name"))
    if body["kind"] == "measurement":  # it is now a target
        cfg["files"]["active_target"] = name
    else:
        cfg["files"]["excluded"] = [n for n in cfg["files"]["excluded"] if n != name]
    settings.save(cfg)
    return {"name": name, "settings": cfg, "inputs": inputs.state(cfg)}


def _source_files(body):
    """Local files for a picker entry: {"src": "app"|"pc"|"db", ...} -> (paths, name, kind). A database entry is
    downloaded first (into downloads\\<database>\\)."""
    src = body.get("src")
    if src == "app":
        where = inputs.folder(kind_of(body))
        files = [os.path.join(where, os.path.basename(n)) for n in names_of(body)]
        missing = [p for p in files if not os.path.exists(p)]
        if missing:
            raise ValueError(f"{os.path.basename(missing[0])} isn't in the app any more.")
        return files, body.get("name") or os.path.splitext(os.path.basename(files[0]))[0], body["kind"]
    if src == "pc":
        g = library.item(body["id"])
        return g["files"], g["name"], g["kind"]
    if src == "db":
        # (no This PC search after it: the downloads folder isn't searched, these are the online entry's files)
        files, it = databases.download(body["id"], lambda text: (library.sniff_text(text) or {"points": 0})["points"])
        return files, it["name"], it["kind"]
    raise ValueError("Unknown source")


@route("/api/use")
def use(body):
    """A found or downloaded device or target copied into the app and put in use (a device replaces the ticked
    measurements). "created" and "before" let the page undo it."""
    cfg = cfg_from(body)
    if body.get("as") not in (None, ""):
        kind_of({"kind": body["as"]})  # (target or measurement, else a plain message)
    files, name, kind = _source_files(body)
    kind = body.get("as") or kind
    files = files if kind == "measurement" else files[:1]
    before = copy.deepcopy(cfg["files"])  # (a copy: called directly, nothing is serialised in between)
    where = inputs.folder(kind)
    there = set(os.listdir(where)) if os.path.isdir(where) else set()
    # (a different file of the same name already there is kept: these are saved as "<name> (2)" …)
    names = inputs.add_files(kind, [(os.path.basename(f), inputs.read_text(f)) for f in files])
    created = [n for n in names if n not in there]  # (Undo removes only these)
    if body.get("src") == "db":
        rigs.record_source(names, databases.item(body["id"]))
    elif created:
        rigs.forget_source(created)
    if kind == "target":
        cfg["files"]["active_target"] = names[0]
    else:
        _use_measurements(cfg, names)
    settings.save(cfg)
    return {"kind": kind, "name": name, "names": names, "created": created, "before": before, "settings": cfg,
            "inputs": inputs.state(cfg)}


@route("/api/preview")
def preview(body):
    """A picker entry's curve for the graph, without putting it in use."""
    files, name, kind = _source_files(body)
    vals = engines.preview_curve(cfg_from(body), [inputs.read_text(f) for f in files])
    return {"name": name, "kind": kind, "vals": vals}


# ---------------------------------------------------------------- this PC and the online databases
@route("/api/library")
def library_status(body):
    st = library.status(with_items=bool(body.get("items")))
    if "items" in st:  # each group with the rig it was measured on
        st["items"] = rigs.library_rigs([dict(g) for g in st["items"]])
    return st


@route("/api/library/scan")
def library_scan(body):
    library.start_scan(cfg_from(body), force=bool(body.get("force")))
    return library.status()


@route("/api/db")
def db_status(body):
    return databases.status(with_items=bool(body.get("items")), rig=lambda it: rigs.rig_tag(rigs.source_rig(it)))


@route("/api/db/directory")
def db_directory(body):
    """squig.link's list of databases, to add one from."""
    return {"items": databases.directory(bool(body.get("refresh")))}


@route("/api/db/refresh")
def db_refresh(body):
    databases.start_refresh(cfg_from(body), force=bool(body.get("force")))
    return databases.status()


@route("/api/db/download")
def db_download(body):
    files, name, _ = _source_files(dict(body, src="db"))
    return {"name": name, "paths": files, "folder": os.path.dirname(files[0])}


# ---------------------------------------------------------------- which measurement to use
@route("/api/compare/query")
def compare_query(body):
    """The model name to start from (the selected measurement's), and the target's rig."""
    cfg = cfg_from(body)
    st = inputs.state(cfg)
    rig, how = rigs.target_rig(st["active_target"] or "")
    return {"query": compare.clean_query(st["device"] or ""), "target": st["active_target"], "target_rig": rig,
            "how": how, "rigs": rigs.RIGS}


@route("/api/compare")
def compare_run(body):
    cfg = cfg_from(body)
    st = inputs.state(cfg)
    q = body.get("query")  # (not text: as if none was typed)
    query = (q if isinstance(q, str) else "").strip() or compare.clean_query(st["device"] or "")
    if not query:
        raise ValueError("Type the model to look for.")
    if databases.status()["loading"]:
        raise ValueError("The online database lists are still loading - try again in a moment.")
    target = st["active_target"]
    r = compare.compare(cfg, query, target, body.get("rig") if isinstance(body.get("rig"), str) and body.get("rig") else None)
    if body.get("auto"):
        # the selected measurement is a copy of a database entry with a fuller name ("GATe Wide" is listener800's
        # "Truthear GATe (Wide Bore Tips)"): search by that model name to find the other databases' measurements
        own = next((c for c in r["items"] if "in the app" in c["also"] and c["src"] == "db"), None)
        better = own and compare.clean_query(own["name"])
        if better and better.lower() != query.lower():
            r = compare.compare(cfg, better, target, body.get("rig") or None)
    return r


@route("/api/compare/average")
def compare_average(body):
    """Several measurements of the model on the same rig, averaged into one new measurement, which is then used."""
    cfg = cfg_from(body)
    keys, name = body.get("keys"), body.get("name")
    if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
        raise ValueError("Choose the measurements to average.")
    fname, text, rig, of = compare.average(keys, (name if isinstance(name, str) and name.strip() else "Average").strip())
    before = copy.deepcopy(cfg["files"])  # (a copy: called directly, nothing is serialised in between)
    there = set(os.listdir(inputs.MEAS_DIR)) if os.path.isdir(inputs.MEAS_DIR) else set()
    name = inputs.add_file("measurement", fname, text)
    created = [] if name in there else [name]  # (it may be "… (2)": a different average had that name)
    rigs.record_source([name], {"name": name, "site": "average", "rig": rig, "of": of})
    _use_measurements(cfg, [name])
    settings.save(cfg)
    return {"kind": "measurement", "name": os.path.splitext(name)[0], "names": [name], "created": created,
            "before": before, "settings": cfg, "inputs": inputs.state(cfg)}


# ---------------------------------------------------------------- runs (one at a time, in a background thread)
JOB_LOCK = threading.Lock()
JOB = {"id": None, "status": "idle"}  # id, status (idle, running, done, error, cancelled), done/total/message, result
CANCEL = threading.Event()


def _run_job(job_id, mode, cfg, analysis=None):
    def progress(done, total, msg=""):
        with JOB_LOCK:
            if JOB["id"] == job_id:
                JOB.update(done=done, total=total, message=msg)
    try:
        target, meas = inputs.selected(cfg)
        progress(0, 1, "Loading files")
        curves, meas_texts, target_text = pipeline.load(cfg, target, meas)
        if cfg["auto"]["enabled"]:  # the same automatic values the window showed (in case it hadn't caught up)
            key = autoset.analysis_key(cfg, meas_texts, target_text)
            # (the page's analysis only when it's of these curves: files just changed, it's the IEM before's)
            an = analysis if isinstance(analysis, dict) and analysis.get("key") == key else autoset.analyse(cfg, curves, meas_texts)
            autoset.apply(cfg, autoset.plan(cfg, an, mode)["values"])
        t0 = time.time()
        out = pipeline.run_mode(mode, cfg, curves, meas_texts, target_text, progress, CANCEL)
        if not out.get("reused_sweep"):  # (a run that reused recent site runs says little about this PC's speed)
            autoset.learn(cfg, mode, time.time() - t0)  # so the next estimate fits this PC
        payload = {"mode": mode, "results": [pipeline.result_summary(r) for r in out["results"]],
                   # (the IEM and target it was made for: the page may have another one on the graph by now)
                   "device": inputs.device_name([os.path.basename(p) for p in meas]),
                   "target_name": os.path.splitext(os.path.basename(target))[0],
                   "meas_files": [os.path.basename(p) for p in meas], "target_file": os.path.basename(target),
                   "pick": out["pick"]["id"], "best": out["best"]["id"], "seconds": round(time.time() - t0, 1),
                   # (the audible pick: did the EQ reach the target inaudibly, or only as close as the limits allow)
                   "pick_case": out.get("pick_case"), "ear_db": cfg["scoring"].get("ear_db"),
                   "settings": cfg}
        with JOB_LOCK:
            if JOB["id"] == job_id:
                JOB.update(status="done", result=payload)
    except engines.Cancelled:
        with JOB_LOCK:
            JOB.update(status="cancelled", message="Cancelled")
    except Exception as e:  # noqa: BLE001 - shown to the user
        traceback.print_exc()
        with JOB_LOCK:
            JOB.update(status="error", message=str(e))


@route("/api/run")
def run(body):
    if body.get("mode") not in settings.MODES:
        raise ValueError("The request doesn't name an EQ method.")
    cfg = cfg_from(body)
    settings.save(cfg)
    retry = body.get("retry")
    if retry is not None:  # this run only: Best fit from the filters on the result card (the saved settings stay)
        if body["mode"] != "best_fit" or not isinstance(retry, dict):
            raise ValueError("Retry from these filters works with Best fit only.")
        filters = [f for f in exports.clean_filters(retry.get("filters")) if f["enabled"]]
        if not filters:
            raise ValueError("There are no filters to start from: add one, or switch one on.")
        add = bool(retry.get("add"))
        cfg = copy.deepcopy(cfg)
        # (as they are: kept ones must stay exactly the card's, not rounded like a saved file)
        cfg["best_fit"].update(start_filters=exports.filters_text(filters), start_keep=add, start_add=add)
    with JOB_LOCK:
        if JOB.get("status") == "running":
            raise ValueError("A run is already in progress.")
        CANCEL.clear()
        job_id = uuid.uuid4().hex
        JOB.clear()
        JOB.update(id=job_id, status="running", mode=body["mode"], done=0, total=1, message="Starting",
                   started=time.time())
    threading.Thread(target=_run_job, args=(job_id, body["mode"], cfg, body.get("analysis")), daemon=True).start()
    return {"id": job_id}


@route("/api/job")
def job(body):
    """How the run is going; {"ack": true} once its end has been seen (the next run can start)."""
    with JOB_LOCK:
        j = dict(JOB)
        if j.get("status") in ("done", "error", "cancelled") and body.get("ack"):
            JOB.update(status="idle")
    if "started" in j:
        j["elapsed"] = round(time.time() - j["started"], 1)
    return j


@route("/api/cancel")
def cancel(body):
    CANCEL.set()
    return {"ok": True}


def job_running():
    return JOB.get("status") == "running"


def result_waiting():
    """A run has finished and the page hasn't taken its result yet: e.g. the window was minimised during a long run
    and the browser put the page to sleep (it stops asking until it's looked at again)."""
    return JOB.get("status") == "done"


# ---------------------------------------------------------------- saving
@route("/api/text")
def text(body):
    """The filters as text, for the clipboard."""
    cfg = cfg_from(body)
    filters = exports.clean_filters(body.get("filters"))
    pre = exports.preamp_value(cfg, exports.clean_preamp(body.get("preamp")))
    return {"apo": exports.apo_text(cfg, filters, pre), "graphic": engines.graphic_eq_text(cfg, filters), "preamp": pre}


@route("/api/export")
def export(body):
    """The EQ files. Files of those names already in your Saved EQs folder are only replaced with "replace": else the
    answer is {"exists": [their names]} and nothing is written (the page asks first)."""
    cfg = cfg_from(body)
    notes = []
    filters, preamp_raw = exports.clean_filters(body.get("filters")), exports.clean_preamp(body.get("preamp"))
    name = text_of(body, "name")
    if not body.get("replace"):
        there = exports.existing(cfg, name, body.get("formats"), filters=filters)
        if there:
            return {"exists": there}
    written, preamp = exports.write(cfg, filters, preamp_raw, name, body.get("formats"), notes=notes)
    return {"written": written, "preamp": preamp, "notes": notes}


@route("/api/report")
def make_report(body):
    """The HTML report for the cards the page sends (each one's error worked out again here), and optionally the
    grid of a sweep's results. A report of that name already in your Saved EQs folder is only replaced with "replace":
    else the answer is {"exists": [its name]} (the page asks first)."""
    cfg = cfg_from(body)
    target, meas = inputs.selected(cfg)
    # (the files the shown EQ was made for, when the page sends them and they're still there: the report then
    # matches the EQ files saved beside it, not the measurement chosen now)
    mf, tf = body.get("meas_files"), body.get("target_file")
    if isinstance(mf, list) and mf and all(isinstance(n, str) for n in mf) and isinstance(tf, str):
        made = (os.path.join(inputs.TARGET_DIR, os.path.basename(tf)),
                [os.path.join(inputs.MEAS_DIR, os.path.basename(n)) for n in mf])
        if os.path.isfile(made[0]) and all(os.path.isfile(p) for p in made[1]):
            target, meas = made
    device, target_name = inputs.device_name([os.path.basename(p) for p in meas]), os.path.splitext(os.path.basename(target))[0]
    name = text_of(body, "name") if body.get("name") else ""
    there = exports.report_name(device, target_name, name)
    if not body.get("replace") and os.path.exists(os.path.join(exports.OUTPUT_DIR, there)):
        return {"exists": [there]}  # (only replaced with "replace", as the EQ files: the page asks first)
    c, _, _ = pipeline.load(cfg, target, meas)
    band, fs = cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"]
    problem = pipeline.band_problem(c, band)
    if problem:
        raise ValueError(problem)
    cards = []
    for card in body["cards"]:
        card["filters"] = exports.clean_filters(card.get("filters"))
        r = engines.finish({"filters": card["filters"]}, c, band, fs)
        cards.append({"title": card["title"], "badge": card.get("badge"), "fields": card.get("fields", []),
                      # (the page's words are text; the report's own markup is added here)
                      "text": html.escape(str(card.get("text", ""))) + f" RMS error <b>{r['rms']:.2f} dB</b>, pre-amp "
                              f"<b>{exports.preamp_value(cfg, r['preamp']):.1f} dB</b>.",
                      "filters": card["filters"], "eq": r["eq"], "rms": r["rms"]})
    grids = []
    if body.get("grid_mode") and body.get("grid_results"):
        res = body["grid_results"]
        grids = report.grids_for(body["grid_mode"], res, cfg["scoring"].get("ear_db", 0.25), min(r["rms"] for r in res))
    out = exports.write_report(c, band, device, target_name, len(meas), cards, grids, name=name)
    if body.get("open", True):
        open_path(out)
    return {"path": out}


@route("/api/filters/parse")
def filters_parse(body):  # (an EQ file's filters, for Best fit's "Start from your own filters")
    return {"filters": exports.parse_filters(text_of(body, "text"))}


# ---------------------------------------------------------------- history: past EQs (history.py)
@route("/api/history")
def history_list(body):
    return {"entries": history.entries()}


@route("/api/history/add")
def history_add(body):
    """The entry as kept and every entry's key in order (the page has the rest: the whole history, 1-2 MB, went back
    with every Save and Copy)."""
    items = history.add(body.get("entry"))
    return {"entry": items[-1], "keys": [x["key"] for x in items]}


@route("/api/history/remove")
def history_remove(body):
    return {"entries": history.remove(None if body.get("all") is True else names_of(body))}


# ---------------------------------------------------------------- your EQs to compare, per IEM (listening.py)
@route("/api/listen")
def listen_list(body):
    return {"eqs": listening.get(text_of(body, "device")), "max": listening.MAX_EQS}


@route("/api/listen/save")
def listen_save(body):
    return {"eqs": listening.put(text_of(body, "device"), body.get("eqs"))}


# ---------------------------------------------------------------- presets
@route("/api/presets/save")
def preset_save(body):
    settings.save_preset(text_of(body, "name"), body.get("settings"))
    return {"presets": settings.list_presets()}


@route("/api/presets/load")
def preset_load(body):
    return {"settings": settings.load_preset(text_of(body, "name"))}


@route("/api/presets/delete")
def preset_delete(body):
    settings.delete_preset(text_of(body, "name"))
    return {"presets": settings.list_presets()}


# ---------------------------------------------------------------- the window
OPENABLE = {"target": paths.TARGET_DIR, "measurement": paths.MEAS_DIR, "output": paths.OUTPUT_DIR,
            "downloads": paths.DOWNLOAD_DIR, "samples": paths.SAMPLES_DIR}


@route("/api/open")
def open_folder(body):
    """Open one of the app's folders (by name) in Explorer. (Only these: opening any file would also start programs.)"""
    what = body.get("what")
    if not (isinstance(what, str) and what in OPENABLE):
        raise ValueError("Nothing to open: the request names none of the app's folders.")
    where = OPENABLE[what]
    os.makedirs(where, exist_ok=True)
    open_path(where)
    return {"ok": True}
