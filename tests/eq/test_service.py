"""The EQ part's requests (eq\\service.py) as Make an EQ's window makes them: the files, the curves, the automatic
settings, runs (retried from your filters, a second one refused, cancelled), EQ files and reports saved, EQs to
compare, presets, files added, moved and removed, and wrong requests answered with plain messages, never opening
anything. Also a few of the service's answers called directly (Undo after averaging, "use" refusing what it doesn't
know, a run checking the page's analysis is of its curves, History's answer to a Save, a dropped file losing an old
database record) and Which measurement's answer to odd requests. Moved from eq_checks.py's api_checks ("requests:
..."), module_checks and rest_checks.

The requests run in the order the old checks made them, one after another, sharing the settings S (/api/state's,
with 2 worker cores) that they change along the way as the old ones did: S and the answers later requests use live
in the module's `chain` fixture. Nothing is opened with Windows: the api fixture records what service.open_path was
asked to open instead."""
import contextlib
import io
import json
import os
import shutil
import time

import pytest

from eq import autoset, compare, databases, history, inputs, pipeline, rigs, service
from helpers import qt, session
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)

COVERS_FILES = ("samples/**",)  # (every request here works on the sample target and measurements)

CURVE = "".join(f"{20 * 1.1 ** i:.2f}\t{80 + i % 5}\n" for i in range(80))  # (eq_checks.py line 151)
FL = [{"type": "PK", "freq": 1000, "gain": -2, "q": 1}]  # (line 633)
# your own filters, the third switched off (lines 1121-1122)
MINE = [{"type": "PK", "freq": 150, "gain": 3, "q": 1}, {"type": "PK", "freq": 3000, "gain": -2, "q": 2},
        {"type": "PK", "freq": 8000, "gain": 1, "q": 1, "enabled": False}]
F = [{"type": "PK", "freq": 1000, "gain": -2, "q": 1}, {"type": "PK", "freq": 3000, "gain": 3, "q": 2}]  # (line 1153)
FORMATS = ("apo", "graphic", "poweramp", "uapp", "soundsource", "voicemeeter", "rockbox", "convolution")  # (exports.FORMATS)


def _ask(api, path, body=None):
    """A request as the window's page made it (eq_checks.py's call(), lines 1074-1086): its body through JSON, as
    sent, answered by eq.service; (status, answer) as AutoEQ Local's server gave them (an error: 400; an address it
    doesn't have: 404). An error's details (the log's) aren't shown."""
    with contextlib.redirect_stderr(io.StringIO()):
        r = json.loads(json.dumps(api.call(path, json.loads(json.dumps(body or {})))))
    if "error" in r:
        return (404 if r["error"].startswith("unknown") else 400), r
    return 200, r


def _run(api, mode, cfg, retry=None):
    """A run as the page started it and waited for it (eq_checks.py's run(), lines 1088-1096): its body through JSON,
    then /api/job asked until the run has ended (up to 300 s, as before), its end acknowledged; the job as it ended."""
    body = {"mode": mode, "settings": cfg, **({"retry": retry} if retry else {})}
    return json.loads(json.dumps(api.run_and_wait("/api/run", json.loads(json.dumps(body)), timeout=300)))


def _small(S):
    """S made small for the runs, as eq_checks.py made it before them (lines 1110-1112): automatic settings off, a site
    sweep of 4 and 6 rows, Best fit with 3 and 5 filters. Each test from the runs on makes sure of it: the same values
    set again change nothing, so a test run on its own sends what it sent in the chain."""
    S["auto"]["enabled"] = False
    S["site_sweep"].update(filter_rows=[4, 6], freq_high=[10000], gain_ranges=[[-12, 6]], q_max=[2])
    S["best_fit"].update(filter_counts=[3, 5], q_max=[2], gain_max=[6], random_starts=2, seed_with_site=True)
    return S


def _every_format(S):
    """Every file format switched on in S, as eq_checks.py did before saving (line 1155; it stayed on for the later
    requests)."""
    S["export"].update({k: True for k in FORMATS})
    return S


def _wait(cond, sec):
    end = time.monotonic() + qt.time_limit(sec)
    while not cond() and time.monotonic() < end:
        time.sleep(0.05)
    return cond()


def _no_run_left():
    """No run left going: one still going is cancelled and waited for (a minute at most), its end acknowledged."""
    if service.JOB.get("status") == "running":
        service.call("/api/cancel")
        if not _wait(lambda: service.JOB.get("status") != "running", 60):
            raise AssertionError("A run was still going a minute after it was cancelled.")
    service.call("/api/job", {"ack": True})


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------- the service's answers, called directly
# (eq_checks.py's module_checks; the ones that change your files or settings start and end with the studio as new,
# as the old requests started on a copy the modules part had put back to the default settings)

def test_undo_after_averaging_removes_the_new_file(fresh_studio, eq_cfg, monkeypatch, check):
    cfg = eq_cfg
    avg = {}
    for level in (80, 83):  # (two different averages of one name: the second is kept as "Avg test (2).txt")
        monkeypatch.setattr(compare, "average", lambda keys, name, lv=level: (
            "Avg test.txt", "".join(f"{20 * 1.1 ** k:.2f}\t{lv + k % 5}\n" for k in range(80)), "711", ["a", "b"]))
        avg = service.compare_average({"keys": ["x", "y"], "settings": cfg})
    monkeypatch.undo()
    try:
        # was eq_checks.py:674
        check("files: Undo after averaging removes the new file, also when it was saved as \"… (2)\"",
              avg["names"] == ["Avg test (2).txt"] and avg["created"] == ["Avg test (2).txt"], avg.get("created"))
    finally:
        for n in ("Avg test.txt", "Avg test (2).txt"):
            inputs.remove_file("measurement", n)


def test_use_refuses_an_unknown_as(check):
    # "as" says target or measurement
    # was eq_checks.py:679
    check("use: an unknown \"as\" is refused (was taken for a measurement)",
          raises(service.use, {"src": "app", "kind": "measurement", "names": ["x"], "as": "Target"})
          == "The request doesn't say target or measurement.")


def test_run_uses_only_its_own_analysis(fresh_studio, eq_cfg, monkeypatch, check):
    # a run uses the page's analysis only for the curves it was made from
    cfg = eq_cfg
    tr, ms = inputs.selected(cfg)
    cs, mts, tts = pipeline.load(cfg, tr, ms)
    key = autoset.analysis_key(cfg, mts, tts)
    analysed, real_an = [], autoset.analyse
    monkeypatch.setattr(autoset, "analyse", lambda *a: (analysed.append(1), real_an(*a))[1])
    try:
        for an in ({"key": "an old IEM's"}, dict(real_an(cfg, cs, mts), key=key)):
            service.JOB.update(id="t", status="running")
            service._run_job("t", "site_single", json.loads(json.dumps(cfg)), an)
        monkeypatch.undo()
        # was eq_checks.py:697
        check("runs: the page's analysis of other curves isn't used (analysed again); its own is",
              analysed == [1] and service.JOB.get("status") == "done",
              (analysed, service.JOB.get("status"), service.JOB.get("message")))
    finally:
        service.JOB.clear()
        service.JOB.update(id=None, status="idle")


def test_history_save_answer(check):
    # History's answer to a Save: the entry and the keys, not the whole history; the curves' settings kept with it
    code_h = service.history_add({"entry": {"key": "h-1", "filters": FL, "site": {"smooth_level": 5}, "rig_convert": False,
                                            "band": [20, 12000]}})
    try:
        # was eq_checks.py:715
        check("history: a Save answers with the entry and the keys only; the curves' settings are kept",
              set(code_h) == {"entry", "keys"} and code_h["keys"][-1] == "h-1" and code_h["entry"]["band"] == [20.0, 12000.0]
              and code_h["entry"]["rig_convert"] is False and code_h["entry"]["site"] == {"smooth_level": 5}, code_h)
    finally:
        history.remove(None)


def test_dropped_file_loses_old_database_record(fresh_studio, eq_cfg, check):
    # a file dropped under the name of one that came from a database isn't from that database
    cfg = eq_cfg
    rigs.record_source(["Forget L.txt"], {"site": "Fake DB", "rig": "711"})
    service.files_add({"kind": "measurement", "name": "Forget L.txt", "content": CURVE, "settings": cfg})
    try:
        # was eq_checks.py:801
        check("files: a dropped file loses an old database record of its name (its rig)", "Forget L.txt" not in rigs.sources())
    finally:
        service.files_remove({"kind": "measurement", "names": ["Forget L.txt"], "settings": cfg})


# ---------------------------------------------------------------- the requests, in the old checks' order
@pytest.fixture(scope="module")
def chain():
    """What the requests share, as eq_checks.py's api_checks kept it (lines 1099-1102): /api/state's answer, and S, its
    settings with 2 worker cores, which every later request sends (saved too, as the old requests saved them with
    their first run: AUTOEQSTUDIO_MAX_WORKERS caps the workers anyway); then the answers later checks use. At the
    end of the module no run is left going."""
    from helpers.eq import Api
    api = Api()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(service, "open_path", api.opened.append)  # (nothing opened with Windows from here either)
        code, st = _ask(api, "/api/state")
        S = st.get("settings")
        if isinstance(S, dict):
            S["performance"]["cores"] = 2
            _ask(api, "/api/settings", {"settings": S})
    yield {"state": (code, st), "S": S}
    _no_run_left()


def test_state(chain, check):
    code, st = chain["state"]
    # was eq_checks.py:1100
    check("requests: starts, state", code == 200 and st["inputs"]["active_target"] and st["inputs"]["measurements"], st.get("error"))


def test_curves(api, chain, check):
    code, c = _ask(api, "/api/curves", {"settings": chain["S"]})
    chain["curves"] = c  # (a run's result is checked against it below)
    # was eq_checks.py:1104
    check("requests: curves with the error without EQ", code == 200 and c["no_eq_rms"] > 0, c.get("error"))


def test_analysis(api, chain, check):
    code, an = _ask(api, "/api/analysis", {"settings": chain["S"]})
    chain["analysis"] = an
    # was eq_checks.py:1106
    check("requests: the automatic settings' analysis", code == 200 and an.get("band_top"), an)


def test_automatic_settings(api, chain, check):
    code, a = _ask(api, "/api/auto", {"settings": chain["S"], "analysis": chain["analysis"]})
    # was eq_checks.py:1108
    check("requests: automatic settings with a time estimate", code == 200 and a["values"] and a["seconds"] > 0, a)


@pytest.mark.parametrize("mode", ["site_sweep", "best_fit"])
def test_run(mode, api, chain, check):
    j = _run(api, mode, _small(chain["S"]))
    res = j.get("result") or {}
    chain[mode] = res  # (the best fit run's result is checked below)
    # was eq_checks.py:1116
    check(f"requests: {mode} run", j.get("status") == "done" and res.get("results") and res["results"][res["pick"]]["filters"], j.get("message"))


def test_result_names_what_it_was_made_for(chain, check):
    res, c = chain["best_fit"], chain["curves"]  # (the best fit run above; the curves' answer)
    # was eq_checks.py:1117
    check("requests: a run's result names the IEM, target and files it was made for (the page may show another by then)",
          res.get("device") == c.get("name") and res.get("target_name") == c.get("target_name") and res.get("meas_files")
          and res.get("target_file"), {k: res.get(k) for k in ("device", "target_name", "meas_files", "target_file")})


def test_retry_fine_tune(api, chain, check):
    # Retry from these filters: Best fit from the result card's filters, this run only (the settings stay)
    j = _run(api, "best_fit", _small(chain["S"]), {"filters": MINE, "add": False})
    res = j.get("result") or {}
    rs = res.get("results") or [{}]
    # was eq_checks.py:1126
    check("requests: retry, fine-tune: only your (switched-on) filters, fitted again; settings kept",
          j.get("status") == "done" and all(r.get("rows") == 0 and r.get("yours") == 2 and r.get("n_filters", 9) <= 2 for r in rs)
          and _ask(api, "/api/state")[1]["settings"]["best_fit"]["start_filters"] == "", (j.get("message"), rs[:1]))


def test_retry_add(api, chain, check):
    j = _run(api, "best_fit", _small(chain["S"]), {"filters": MINE[:2], "add": True})
    res = j.get("result") or {}
    pick = (res.get("results") or [{}])[res.get("pick", 0)] if res.get("results") else {}
    # was eq_checks.py:1132
    check("requests: retry, add: your filters kept exactly, filters added",
          j.get("status") == "done" and [(f["freq"], f["gain"], f["q"]) for f in pick.get("filters", [])[:2]] == [(150, 3, 1), (3000, -2, 2)]
          and pick.get("n_filters", 0) > 2, (j.get("message"), pick.get("filters")))


def test_retry_with_no_filters_on_refused(api, chain, check):
    try:
        code, r = _ask(api, "/api/run", {"mode": "best_fit", "settings": _small(chain["S"]),
                                         "retry": {"filters": [dict(MINE[2])], "add": False}})
        # was eq_checks.py:1136
        check("requests: retry with no filters switched on is refused with a message", code == 400 and "no filters" in r.get("error", ""), r)
    finally:
        _no_run_left()  # (had it started, the next test's first run would be refused)


def test_second_run_refused_and_cancel(api, chain, check):
    big = json.loads(json.dumps(_small(chain["S"])))
    big["best_fit"].update(filter_counts=list(range(8, 17)), q_max=[2, 3, 5], random_starts=12, seed_with_site=False)
    try:
        _ask(api, "/api/run", {"mode": "best_fit", "settings": big})
        # was eq_checks.py:1140
        check("requests: a second run at once is refused", _ask(api, "/api/run", {"mode": "best_fit", "settings": big})[0] == 400)
        time.sleep(1)  # (the big run under way for a moment, as the old check let it go)
        _ask(api, "/api/cancel")
        t0 = time.time()
        j = {}
        end = time.monotonic() + qt.time_limit(20)  # (the old check: 100 looks, 0.2 s apart)
        while time.monotonic() < end:
            j = _ask(api, "/api/job")[1]
            if j.get("status") != "running":
                _ask(api, "/api/job", {"ack": True})
                break
            time.sleep(0.2)
        # was eq_checks.py:1151
        check("requests: Cancel stops a run at once", j.get("status") == "cancelled" and time.time() - t0 < qt.time_limit(10), j)
    finally:
        _no_run_left()


def test_files_saved_in_every_format(api, chain, check):
    S = _every_format(_small(chain["S"]))
    code, r = _ask(api, "/api/export", {"settings": S, "filters": F, "preamp": -3, "name": "Selftest - best fit 2f"})
    # was eq_checks.py:1157
    check("requests: filter files saved in every format", code == 200 and sorted(r.get("written", {})) == sorted(FORMATS)
          and all(os.path.isfile(p) for p in r["written"].values()), r)


def test_own_file_name_and_replacing(api, chain, check):
    # your own File name: the files are named after it; saving again under it asks first (nothing replaced)
    S = _every_format(_small(chain["S"]))
    code, r = _ask(api, "/api/export", {"settings": S, "filters": F, "preamp": -3, "name": "My: EQ?", "formats": ["apo", "poweramp"]})
    mine = sorted(os.path.basename(p) for p in r.get("written", {}).values())
    code2, r2 = _ask(api, "/api/export", {"settings": S, "filters": F[:1], "preamp": -3, "name": "My: EQ?", "formats": ["apo", "poweramp"]})
    kept = _read(os.path.join(os.path.dirname(r["written"]["apo"]), "My_ EQ_ - filters.txt")) if mine else ""
    code3, r3 = _ask(api, "/api/export", {"settings": S, "filters": F[:1], "preamp": -3, "name": "My: EQ?", "formats": ["apo"], "replace": True})
    # was eq_checks.py:1165
    check("requests: your own file name names the files (made safe); an existing file is only replaced when you say so",
          mine == ["My_ EQ_ - Poweramp.json", "My_ EQ_ - filters.txt"] and sorted(r2.get("exists", [])) == mine
          and "written" not in r2 and "3000" in kept and code3 == 200 and "written" in r3, (r, r2, r3))


def test_report_saved(api, chain, check):
    S = _every_format(_small(chain["S"]))
    code, r = _ask(api, "/api/report", {"settings": S, "cards": [{"title": "A", "filters": F}], "open": False})
    # was eq_checks.py:1169
    check("requests: report saved", code == 200 and os.path.isfile(r.get("path", "")), r)


def test_report_own_name(api, chain, check):
    S = _every_format(_small(chain["S"]))
    code, r = _ask(api, "/api/report", {"settings": S, "cards": [{"title": "A", "filters": F}], "open": False, "name": "My EQ"})
    # was eq_checks.py:1171
    check("requests: report under your own file name", code == 200 and os.path.basename(r.get("path", "")) == "My EQ - report.html", r)


def test_report_card_words_are_text(api, chain, check):
    S = _every_format(_small(chain["S"]))
    code, r = _ask(api, "/api/report", {"settings": S, "cards": [{"title": "A", "text": "Mine <i>x</i> & y", "filters": F}],
                                        "open": False, "name": "Escaped"})
    rep = _read(r.get("path", os.devnull))
    # was eq_checks.py:1176
    check("requests: a card's words are text in the report (its own markup kept)", code == 200
          and "Mine &lt;i&gt;x&lt;/i&gt; &amp; y" in rep and "RMS error <b>" in rep, r)


def test_report_no_points_in_scored_range(api, chain, check):
    # (19.9-20 kHz: within the limits and in order, but between the grid's points at 19,897 and 20,186 Hz)
    S = _every_format(_small(chain["S"]))
    code, r = _ask(api, "/api/report", {"settings": dict(S, scoring=dict(S["scoring"], band_hz=[19900, 20000])),
                                        "cards": [{"title": "A", "filters": F}], "open": False, "name": "Empty band"})
    # was eq_checks.py:1181
    check("requests: a report with no curve points in the scored range says so (was \"nan dB\")",
          code == 400 and "has no data" in r.get("error", ""), r)


def test_existing_report_replaced_only_when_asked(api, chain, check):
    # a report of that name already there (the one under your own file name above): only replaced when you say so
    # (before, it was replaced silently)
    body = {"settings": _every_format(_small(chain["S"])), "cards": [{"title": "A", "filters": F}], "open": False, "name": "My EQ"}
    code, r = _ask(api, "/api/report", body)
    code2, r2 = _ask(api, "/api/report", {**body, "replace": True})
    # was eq_checks.py:1187
    check("requests: an existing report is only replaced when you say so",
          code == 200 and r.get("exists") == ["My EQ - report.html"] and "path" not in r and code2 == 200 and r2.get("path"), (r, r2))


def test_report_of_the_files_the_eq_was_made_for(api, chain, check):
    # (review 2) the files the EQ was made for, sent with it: the report is of them, not of the measurement chosen now
    S = _every_format(_small(chain["S"]))
    flat = "".join(f"{20 * 1.1 ** i:.2f} {70 + i % 3}\n" for i in range(80))
    _ask(api, "/api/files/add", {"kind": "measurement", "files": [{"name": "Report other L.txt", "content": flat},
                                                                  {"name": "Report other R.txt", "content": flat}],
                                 "settings": S})
    try:
        tgt = S["files"]["active_target"] or _ask(api, "/api/state")[1]["inputs"]["active_target"]
        code, r = _ask(api, "/api/report", {"settings": S, "cards": [{"title": "A", "filters": F}], "open": False,
                                            "meas_files": ["Report other L.txt", "Report other R.txt"], "target_file": tgt})
        # was eq_checks.py:1197
        check("requests: a report for an EQ made for other files is of those files (named as the EQ files are)",
              code == 200 and os.path.basename(r.get("path", "")).startswith("Report other"), r)
    finally:
        _ask(api, "/api/files/remove", {"kind": "measurement", "names": ["Report other L.txt", "Report other R.txt"],
                                        "settings": S})


def test_eqs_to_compare_kept_and_read_back(api, check):
    code, r = _ask(api, "/api/listen/save", {"device": "Selftest IEM", "eqs": [{"name": "A", "filters": F}]})
    code2, r2 = _ask(api, "/api/listen", {"device": "Selftest IEM"})
    try:
        # was eq_checks.py:1203
        check("requests: EQs to compare kept for an IEM and read back", code == 200 and code2 == 200
              and [e["name"] for e in r2.get("eqs", [])] == ["A"] and r2.get("max") == 12, (r, r2))
    finally:
        _ask(api, "/api/listen/save", {"device": "Selftest IEM", "eqs": []})


def test_filters_as_text(api, chain, check):
    code, r = _ask(api, "/api/text", {"settings": _every_format(_small(chain["S"])), "filters": F, "preamp": -3})
    # was eq_checks.py:1207
    check("requests: filters as text", code == 200 and r["apo"].startswith("Preamp: -3.0 dB"), r)


def test_preset_saved_and_loaded(api, chain, check):
    # (loading a preset takes the files from the settings saved last: S's, as every request above that saved settings
    # saved S)
    S = _every_format(_small(chain["S"]))
    _ask(api, "/api/presets/save", {"name": "Selftest", "settings": S})
    code, r = _ask(api, "/api/presets/load", {"name": "Selftest"})
    try:
        # was eq_checks.py:1211
        check("requests: preset saved and loaded (the files stay)", code == 200 and r["settings"]["files"] == S["files"], r)
    finally:
        _ask(api, "/api/presets/delete", {"name": "Selftest"})


def test_dropped_target_added_used_and_moved(api, chain, check):
    S = _every_format(_small(chain["S"]))
    curve = "Frequency;dB\n" + "".join(f"{20 * 1.1 ** i:.2f};{80 + i % 5},5\n".replace(".", ",", 1) for i in range(80))
    try:
        code, r = _ask(api, "/api/files/add", {"kind": "auto", "name": "Selftest target.txt", "content": curve, "settings": S})
        # was eq_checks.py:1215
        check("requests: a dropped target (decimal commas) is added and used", code == 200 and r.get("kind") == "target"
              and r["inputs"]["active_target"] == "Selftest target.txt", r)
        code, r = _ask(api, "/api/files/move", {"kind": "target", "name": "Selftest target.txt", "settings": r.get("settings", S)})
        # was eq_checks.py:1218
        check("requests: moved to the measurements", code == 200 and any(m["name"] == "Selftest target.txt" for m in r["inputs"]["measurements"]), r)
    finally:
        _ask(api, "/api/files/remove", {"kind": "measurement", "names": ["Selftest target.txt"], "settings": S})


def test_set_of_files_numbered_as_one(api, chain, check):
    # (review 2) a traced device's channels added as one set: L unchanged and R changed stay one device's names
    S = _every_format(_small(chain["S"]))
    curve = "Frequency;dB\n" + "".join(f"{20 * 1.1 ** i:.2f};{80 + i % 5},5\n".replace(".", ",", 1) for i in range(80))
    lr = lambda r_db: [{"name": "Selftest set L.txt", "content": curve}, {"name": "Selftest set R.txt",
                                                                         "content": curve.replace(";8", f";{r_db}")}]
    try:
        _ask(api, "/api/files/add", {"kind": "measurement", "files": lr(7), "settings": S})
        code, r = _ask(api, "/api/files/add", {"kind": "measurement", "files": lr(6), "settings": S})
        # was eq_checks.py:1225
        check("requests: several files added as one set get one number when a name is taken (one device)",
              code == 200 and r.get("names") == ["Selftest set (2) L.txt", "Selftest set (2) R.txt"], r.get("names") or r)
    finally:
        _ask(api, "/api/files/remove", {"kind": "measurement", "settings": S, "names": [
            "Selftest set L.txt", "Selftest set R.txt", "Selftest set (2) L.txt", "Selftest set (2) R.txt"]})


def test_unknown_address(api, check):
    # was eq_checks.py:1230
    check("requests: unknown address", _ask(api, "/api/nope")[0] == 404)


def test_body_not_a_dict(api, check):
    # (straight to eq.service, as the old check sent it: not through JSON)
    # was eq_checks.py:1232
    check("requests: a body that isn't a dict is read as empty (a missing field is named)",
          api.call("/api/files/move", ["not", "a", "dict"]).get("error") == "The request doesn't say target or "
          "measurement.")


def test_missing_field_named(api, chain, check):
    # was eq_checks.py:1235
    check("requests: missing field named", _ask(api, "/api/files/move", {"settings": _every_format(_small(chain["S"]))})[1].get("error")
          == "The request doesn't say target or measurement.")


def test_wrong_kinds_of_values(api, check):
    wrong = [_ask(api, p, {"kind": "measurement", "name": 5, "names": 4, "content": 9})[1].get("error", "")
             for p in ("/api/files/add", "/api/files/remove", "/api/files/move", "/api/presets/load", "/api/listen")]
    # was eq_checks.py:1239
    check("requests: wrong kinds of values get plain messages", all(e.startswith("Missing") for e in wrong), wrong)


def test_opens_nothing_outside_its_folder(api, check):
    # was eq_checks.py:1240
    check("requests: opens nothing outside its folder", _ask(api, "/api/open", {"path": "C:\\Windows"})[0] == 400)


def test_opens_no_file_by_path(api, check):
    # only the app's folders by name, and only its own page (opening any file would also start programs: here, the
    # session's copy of the app)
    inside = os.path.join(session.SESSION.studio, "app", "start.py")
    # was eq_checks.py:1243
    check("requests: opens no file by path (a program could start)", _ask(api, "/api/open", {"path": inside})[0] == 400)


def test_opens_nothing_when_no_folder_named(api, check):
    # was eq_checks.py:1244
    check("requests: opens nothing when no folder is named", [_ask(api, "/api/open", b)[0] for b in ({}, {"what": {"a": 1}}, {"path": ""})]
          == [400, 400, 400])


# ---------------------------------------------------------------- Which measurement: odd requests
def test_compare_odd_queries(api, db_guard, eq_cfg, check):
    # /api/compare: a query that isn't text (a number, a list) answers as an empty one, never a crash. (The old check
    # asked while the database lists were still loading, so it was answered "still loading" before the query was
    # read. Here the lists are loaded first, and the measurements Which measurement downloads get a whole curve each
    # from a stand-in, as they got theirs from the sites when the old check ran online: offline, nothing is
    # downloaded for real. With every download failing instead, each answer is an app error, "list index out of
    # range": compare.compare's note reads the first of no measurements.)
    folder = databases.DOWNLOAD_DIR
    before = set(os.listdir(folder)) if os.path.isdir(folder) else set()
    try:
        databases.refresh_now(databases.sites_for(eq_cfg))
        st = databases.status()
        assert st["count"] and not st["loading"], f"the database lists didn't load: {st}"
        db_guard.stub_get(lambda url, **k: (CURVE, url))
        odd = [api.call("/api/compare", {"query": q, "settings": eq_cfg}) for q in (5, ["x"], None)]
        avg = api.call("/api/compare/average", {"keys": "x", "name": 3})
        # was eq_checks.py:2115
        check("compare: a query that isn't text is answered (no crash); average with odd keys says what to choose",
              all("Traceback" not in json.dumps(r) for r in odd) and "Choose the measurements" in avg.get("error", ""),
              (odd, avg))
    finally:  # (the database folders a download tried to make, taken away again)
        for name in (set(os.listdir(folder)) if os.path.isdir(folder) else set()) - before:
            shutil.rmtree(os.path.join(folder, name), ignore_errors=True)
