"""This PC's list (eq\\library.py) after a change to the app's own folders: a file added (the tracer, Add…, a drop and
a paste all use /api/files/add), moved, used from this PC or removed is in Which measurement's answer (/api/compare)
and in the list at once, also when This PC was searched less than a minute before (a search asked for then starts
none: RESCAN_AFTER). And a search that runs while a file is added keeps the new file (2026-11-11: a measurement just
traced was not in "Other measurements of this model" until the next search, and a deleted one was still offered)."""
import os
import shutil
import time

import pytest

from eq import databases, library, service
from eq import paths as eq_paths
from helpers import qt, session

# (lines "frequency<TAB>dB" that the app reads as a curve: 80 points from 20 Hz to 40 kHz)
CURVE = "".join(f"{20 * 1.1 ** i:.2f}\t{80 + i % 5}\n" for i in range(80))
MODEL = "Zorbex Qa7"  # (a made-up model: no database entry has its name)


def _scan_ended():
    end = time.monotonic() + qt.time_limit(30)
    while library.status()["scanning"] and time.monotonic() < end:
        time.sleep(0.05)
    return not library.status()["scanning"]


@pytest.fixture
def searched(fresh_studio, eq_cfg, db_guard, monkeypatch):
    """The settings, This PC's search on a folder of this test's own (empty), searched a moment ago; the database
    lists as loaded (Which measurement asks for that)."""
    mine = os.path.join(session.SESSION.studio, "mine-app-files")
    os.makedirs(mine, exist_ok=True)
    cfg = dict(eq_cfg, library={"folders": [mine]})
    monkeypatch.setitem(databases._state, "loading", False)
    library.start_scan(cfg, force=True)
    _scan_ended()
    yield cfg
    shutil.rmtree(mine, ignore_errors=True)
    for folder in (eq_paths.MEAS_DIR, eq_paths.TARGET_DIR):
        for n in os.listdir(folder):
            if n.startswith(MODEL):
                os.remove(os.path.join(folder, n))


def _compared(cfg):
    """The names in Which measurement's answer for MODEL, after a search request as Find… makes it when it opens."""
    service.call("/api/library/scan", {"settings": cfg})
    _scan_ended()
    r = service.call("/api/compare", {"query": MODEL, "settings": cfg})
    return sorted(c["name"] for c in r.get("items") or []) if "error" not in r else r["error"]


def _listed():
    return sorted(g["name"] for g in library.status(with_items=True)["items"] if g["name"].startswith(MODEL))


def test_added_and_removed_files_in_the_list_at_once(searched, check):
    cfg = searched
    seen = {}
    r = service.call("/api/files/add", {"kind": "measurement", "files": [{"name": f"{MODEL} L.txt", "content": CURVE},
                                                                       {"name": f"{MODEL} R.txt", "content": CURVE}],
                                        "settings": cfg})
    seen["added"] = (_compared(cfg), _listed())
    service.call("/api/files/remove", {"kind": "measurement", "names": r["names"], "settings": cfg})
    seen["removed"] = (_compared(cfg), _listed())
    check("This PC: a measurement added (the tracer, Add…, a drop, a paste) is in Which measurement's answer and in "
          "the list at once, also after a search less than a minute before; removed, it is in neither",
          seen == {"added": ([MODEL], [MODEL]), "removed": ([], [])}, seen)


def test_moved_and_used_files_in_the_list_at_once(searched, check):
    cfg = searched
    seen = {}
    service.call("/api/files/add", {"kind": "target", "name": f"{MODEL} target.txt", "content": CURVE, "settings": cfg})
    seen["a target"] = _compared(cfg)
    r = service.call("/api/files/move", {"kind": "target", "name": f"{MODEL} target.txt", "settings": cfg})
    seen["moved to Measurement"] = _compared(cfg)
    service.call("/api/files/remove", {"kind": "measurement", "names": [r["name"]], "settings": cfg})
    # (a curve of a folder of yours, found by the search, then used: its copy in the app is in the list at once)
    mine = cfg["library"]["folders"][0]
    with open(os.path.join(mine, f"{MODEL} pc.txt"), "w", encoding="utf-8") as fh:
        fh.write(CURVE)
    library.start_scan(cfg, force=True)
    _scan_ended()
    g = next(g for g in library.status(with_items=True)["items"] if g["name"] == f"{MODEL} pc")
    service.call("/api/use", {"src": "pc", "id": g["id"], "kind": "measurement", "settings": cfg})
    seen["used"] = sorted((x["name"], x["in_app"]) for x in library.status(with_items=True)["items"]
                          if x["name"] == f"{MODEL} pc")
    check("This PC: a target moved to Measurement is in Which measurement's answer at once; the copy in the app of a "
          "curve used from this PC is in the list at once",
          seen == {"a target": [], "moved to Measurement": [f"{MODEL} target"],
                   "used": [(f"{MODEL} pc", False), (f"{MODEL} pc", True)]}, seen)


def test_search_running_keeps_a_file_added(searched, monkeypatch, check):
    cfg = searched
    real = library.textfile.write_json
    added = []

    def add_meanwhile(path, data, *a, **k):
        """A file added while the search runs, after it looked at the app's folders (its cache is written then)."""
        if path == library.CACHE_PATH and not added:
            added.append(service.call("/api/files/add", {"kind": "measurement", "name": f"{MODEL} late.txt",
                                                         "content": CURVE, "settings": cfg}).get("name"))
        return real(path, data, *a, **k)
    monkeypatch.setattr(library.textfile, "write_json", add_meanwhile)
    library.start_scan(cfg, force=True)
    ended = _scan_ended()
    monkeypatch.undo()
    check("This PC: a search that runs while a file is added keeps the new file in the list (its own result of the "
          "app's folders is older)", ended and added == [f"{MODEL} late.txt"] and _listed() == [f"{MODEL} late"],
          (ended, added, _listed()))


def test_refresh_reads_only_new_files(searched, monkeypatch, check):
    cfg = searched
    service.call("/api/files/add", {"kind": "measurement", "name": f"{MODEL} one.txt", "content": CURVE,
                                    "settings": cfg})
    read, real = [], library.sniff
    monkeypatch.setattr(library, "sniff", lambda p: (read.append(os.path.basename(p)), real(p))[1])
    library.refresh_app()
    again = list(read)
    with open(os.path.join(eq_paths.MEAS_DIR, f"{MODEL} two.txt"), "w", encoding="utf-8") as fh:
        fh.write(CURVE)
    library.refresh_app()
    monkeypatch.undo()
    check("This PC: the app's folders searched again read only the files that are new or changed (a file read once "
          "is not read again)", again == [] and read == [f"{MODEL} two.txt"], (again, read))


def test_a_problem_never_fails_the_add(searched, monkeypatch, check):
    cfg = searched

    def broken(files):
        raise OSError("a disk problem in the test")
    monkeypatch.setattr(library, "_group", broken)
    r = service.call("/api/files/add", {"kind": "measurement", "name": f"{MODEL} kept.txt", "content": CURVE,
                                        "settings": cfg})
    monkeypatch.undo()
    check("This PC: a problem while the app's folders are searched again never fails the add (the list waits for the "
          "next search)", r.get("name") == f"{MODEL} kept.txt" and "error" not in r, r.get("error") or r.get("name"))


def test_saved_target_and_average_in_the_list_at_once(searched, monkeypatch, check):
    # (the two routes that make a file of their own: Save as a target… of Adjust, and the average of Which measurement)
    from eq import compare
    cfg = searched
    seen = {}
    adjusted = dict(cfg, target_adjust=dict(cfg["target_adjust"], bass_gain=3.0))
    r = service.call("/api/target/save", {"name": f"{MODEL} saved", "settings": adjusted})
    seen["saved target"] = (r.get("error"), _listed())
    monkeypatch.setattr(compare, "average", lambda keys, name: (f"{MODEL} avg.txt", CURVE, "711", ["a", "b"]))
    r = service.call("/api/compare/average", {"keys": ["x", "y"], "settings": cfg})
    monkeypatch.undo()
    seen["average"] = (r.get("error"), _listed())
    check("This PC: a target saved from Adjust and an average of Which measurement are in the list at once",
          seen == {"saved target": (None, [f"{MODEL} saved"]), "average": (None, [f"{MODEL} avg", f"{MODEL} saved"])},
          seen)


def test_refreshed_list_in_name_order(searched, check):
    # (Find… shows the list in its sequence: a file of the app between two of a folder of yours goes between them)
    cfg = searched
    mine = cfg["library"]["folders"][0]
    for n in ("alpha", "gamma"):
        with open(os.path.join(mine, f"{MODEL} {n}.txt"), "w", encoding="utf-8") as fh:
            fh.write(CURVE)
    library.start_scan(cfg, force=True)
    _scan_ended()
    service.call("/api/files/add", {"kind": "measurement", "name": f"{MODEL} beta.txt", "content": CURVE,
                                    "settings": cfg})
    items = library.status(with_items=True)["items"]
    keys = [(g["name"].lower(), g["folder"].lower()) for g in items]
    seen = {"ours": [g["name"] for g in items if g["name"].startswith(MODEL)], "sorted": keys == sorted(keys)}
    check("This PC: after an add, the list is in the sequence of the names (a file of the app between two of a folder "
          "of yours goes between them)",
          seen == {"ours": [f"{MODEL} alpha", f"{MODEL} beta", f"{MODEL} gamma"], "sorted": True}, seen)


def test_two_refreshes_at_once_keep_the_newer_list(searched, monkeypatch, check):
    # (Use in a background thread and an add on the window's thread at the same time: the call that started first
    # read the folders before the add, and ends last; its older groups must not replace the newer ones)
    import threading
    cfg = searched
    real_walk = library._walk
    roots = (library.paths.TARGET_DIR, library.paths.MEAS_DIR)
    slow, read, go_on = {}, threading.Event(), threading.Event()

    def walk(root, cb):
        if threading.current_thread() is not slow.get("thread"):
            yield from real_walk(root, cb)
            return
        if "seen" not in slow:  # (the folders as they are now, before the add; then it waits for the add)
            slow["seen"] = {r: list(real_walk(r, cb)) for r in roots}
            read.set()
            go_on.wait(qt.time_limit(20))
        yield from slow["seen"][root]
    monkeypatch.setattr(library, "_walk", walk)
    slow["thread"] = threading.Thread(target=library.refresh_app, daemon=True)
    slow["thread"].start()
    seen = {"first one read the folders": read.wait(qt.time_limit(20))}
    service.call("/api/files/add", {"kind": "measurement", "name": f"{MODEL} new.txt", "content": CURVE,
                                    "settings": cfg})
    seen["the add did not wait for the first one"] = slow["thread"].is_alive()
    seen["listed after the add"] = _listed()
    go_on.set()
    slow["thread"].join(qt.time_limit(20))
    monkeypatch.undo()
    seen["listed after the first one ended"] = _listed()
    check("This PC: two searches of the app's folders at the same time: the one that started first and ends last does "
          "not take out a file that the other one found; the add does not wait for the first one",
          seen == {"first one read the folders": True, "the add did not wait for the first one": True,
                   "listed after the add": [f"{MODEL} new"], "listed after the first one ended": [f"{MODEL} new"]},
          seen)
