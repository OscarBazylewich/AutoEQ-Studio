"""The EQ part's checks (app\\eq\\: AutoEQ Local's maths and files), on a temporary copy of AutoEQ Studio: your own
files and settings are never used or changed. selftest.py runs them; on their own:

    .venv\\Scripts\\python.exe app\\tools\\eq_checks.py [--keep]

Brought over from AutoEQ Local's app\\tools\\selftest.py (2026-10-05) with its module checks and its server checks
as they were, the server's made direct calls to eq.service (named "requests: …"). Left there: the page's checks and
the web server's own (other sites, GET, oversized requests, serving the page), and the rig builds' (their tools stay
in AutoEQ Local). A fix to AutoEQ Local's checks may be wanted here too, and the other way round.

  1. modules: the settings, reading files, file names, EQ formats, the EQ methods, automatic settings, rigs, History
     and the EQs to compare, called directly;
  2. requests: what the window asks for (files, curves, automatic settings, runs, cancelling, saving, presets,
     errors), through eq.service as the window does.
Each in its own process (the modules' leave settings behind), one line per check; exits 1 if any failed.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback

TOOLS = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(TOOLS)
ROOT = os.path.dirname(APP)
SAMPLE_TARGET = os.path.join("targets", "Diffuse field 5128 -1dB per octave (AutoEq).csv")
SAMPLE_DEVICE = os.path.join("measurements", "Truthear GATe - B&K 5128, 10 seatings")
# the database lists (8 MB, downloaded): AutoEQ Studio's own once it has them, else AutoEQ Local's (beside it, or in
# Downloads since 2026-10-08)
DB_LISTS = [os.path.join(ROOT, "data", "eq", "cache"), os.path.join(os.path.dirname(ROOT), "AutoEQ Local", "data", "cache"),
            os.path.join(os.path.expanduser("~"), "Downloads", "AutoEQ Local", "data", "cache")]

results = []  # (ok, name, detail)


BOXES = []  # (what message boxes said during the EQ screen's checks)


def check(name, cond, detail=""):
    results.append((bool(cond), name, "" if cond else str(detail)))
    print(f"{'ok  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  ({str(detail)[:300]})"), flush=True)


def raises(fn, *a, **k):
    """The error message fn raises (ValueError), or None."""
    try:
        fn(*a, **k)
    except ValueError as e:
        return str(e)
    return None


# ---------------------------------------------------------------- the copy
def make_copy():
    base = tempfile.mkdtemp(prefix="aeqstudio-eqchecks-")
    top = os.path.join(base, "AutoEQ Studio")
    shutil.copytree(APP, os.path.join(top, "app"), ignore=shutil.ignore_patterns("__pycache__", "tools", ".venv", "data"))
    shutil.copytree(os.path.join(ROOT, "samples"), os.path.join(top, "samples"))
    t, m = os.path.join(top, "Targets"), os.path.join(top, "Measurements")
    os.makedirs(t)
    shutil.copy(os.path.join(ROOT, "samples", SAMPLE_TARGET), t)
    shutil.copytree(os.path.join(ROOT, "samples", SAMPLE_DEVICE), m)
    cache = os.path.join(top, "data", "eq", "cache")
    os.makedirs(cache)
    src = next((d for d in DB_LISTS if os.path.isfile(os.path.join(d, "databases.json"))), None)
    for n in ("databases.json", "squigsites.json"):
        if src and os.path.isfile(os.path.join(src, n)):
            shutil.copy(os.path.join(src, n), cache)
    return base, top


def use_copy(top):
    """This process works in the copy: eq.paths reads these when it's first imported."""
    os.environ.update(AUTOEQSTUDIO_ROOT=top, AUTOEQSTUDIO_DATA=os.path.join(top, "data"))
    sys.path.insert(0, os.path.join(top, "app"))


def remove_copy(base):
    """Delete a test copy, trying again for a few seconds while stopped processes let go of its files."""
    for _ in range(20):
        shutil.rmtree(base, ignore_errors=True)
        if not os.path.exists(base):
            return True
        time.sleep(0.3)
    return False


# ---------------------------------------------------------------- 1. modules (run inside the copy)
def module_checks(top):
    use_copy(top)
    app = os.path.join(top, "app", "eq")  # (where AutoEQ Local's app\ files are: rigdata.json, vendor\ …)
    os.chdir(app)
    from eq import service as api  # (AutoEQ Local's api.py)
    from eq import autoset
    from eq import engines
    from eq import exports
    from eq import inputs
    from eq import pipeline
    from eq import rigconv
    from eq import rigs
    from eq import settings
    import textfile

    # settings
    d = json.loads(json.dumps(settings.DEFAULTS))
    check("settings: the defaults are valid as they are", settings.clamp(json.loads(json.dumps(d))) == d)
    for p in settings.ALL_AUTO_PATHS + list(settings.LIMITS):
        if settings.get_path(settings.DEFAULTS, p) is None and not settings.LIMITS.get(p, {}).get("empty"):
            check(f"settings: {p} exists in the defaults", False)
    bad = {"mode": 3, "site": "x", "site_single": {"rows": 99, "q_min": 9, "q_max": 1}, "scoring": {"band_hz": [15000, 100]},
           "best_fit": {"filter_counts": list(range(-5, 500)), "gain_max": []}, "auto": {"level": "90", "manual": "x"},
           "files": {"excluded": "abc"}, "export": {"q_decimals": 1e9}, "site_sweep": {"gain_ranges": [[1, 2, 3]]}}
    c = settings.with_auto(bad)
    check("settings: wrong kinds go back to the defaults",
          c["mode"] == "best_fit" and isinstance(c["site"], dict) and c["files"]["excluded"] == [] and "level" not in c["auto"], c)
    ceil = lambda p: settings.LIMITS[p]["max"]
    check("settings: numbers kept within their limits", c["site_single"]["rows"] == ceil("site_single.rows")
          and c["export"]["q_decimals"] == ceil("export.q_decimals")
          and max(c["best_fit"]["filter_counts"]) == ceil("best_fit.filter_counts") and min(c["best_fit"]["filter_counts"]) == 1, c)
    check("settings: from/to pairs in order", all(not settings.pair_wrong(c, lo, hi, s) for lo, hi, s in settings.LIMIT_PAIRS))
    check("settings: something that isn't settings at all gives the defaults",
          all(settings.with_auto(x)["mode"] == "best_fit" for x in ("text", 5, [], None)))
    check("settings: a preset needs settings to save", raises(settings.save_preset, "x", "text") is not None)
    sp = os.path.join(top, "data", "test settings.json")
    for enc in ("utf-16", "utf-8-sig", "cp1252"):
        with open(sp, "w", encoding=enc) as fh:
            json.dump({"mode": "site_single"}, fh)
        check(f"settings: settings.json read when saved as {enc}", settings.load(sp)["mode"] == "site_single")
    with open(sp, "w", encoding="utf-8") as fh:
        fh.write('{"mode": "autoeq",')
    old = settings.with_auto({"mode": "autoeq", "autoeq": {"preset": "QUDELIX_5K"}})
    check("settings: the AutoEq method's settings (taken out) become Best fit's", old["mode"] == "best_fit" and "autoeq" not in old)
    check("settings: a broken settings.json gives the defaults and is kept as .bad",
          settings.load(sp)["mode"] == "best_fit" and os.path.exists(sp + ".bad"))

    # reading files and names
    check("files: UTF-16 and cp1252 text decoded", textfile.decode("20 1\n".encode("utf-16")) == "20 1\n"
          and textfile.decode(b"20\xb05") == "20\u00b05")
    check("files: decimal commas and semicolons read", textfile.normalize_fr("20,5;85,3\n30,1;86\n") == "20.5\t85.3\n30.1\t86\n")
    check("files: Windows-safe names", [textfile.safe_name(n) for n in ("CON", "a:b*c?.txt", "....")] == ["_CON", "a_b_c_.txt", "file"])
    check("files: device name from seating files", inputs.device_name(["GATe Wide L1.txt", "GATe Wide R5.txt"]) == "GATe Wide"
          and inputs.device_name([]) == "")
    check("files: targets told apart by name", [inputs.guess_kind(n) for n in ("Harman IE 2019.txt", "JM-1.txt", "HD600.txt")]
          == ["target", "target", "measurement"])
    curve = "".join(f"{20 * 1.1 ** i:.2f}\t{80 + i % 5}\n" for i in range(80))
    check("files: odd names stored safely", [inputs.add_file("measurement", n, curve) for n in (" .txt", "CON", "x.exe")]
          == ["file.txt", "_CON.txt", "x.exe.txt"])
    check("files: a file that isn't a curve is refused", raises(inputs.add_file, "measurement", "x.txt", "hello") is not None)
    check("files: one line repeated isn't a curve", raises(inputs.add_file, "measurement", "x.txt", "1000 80\n" * 500) is not None)
    blank = [raises(f, "target", n) for f in (inputs.remove_file, inputs.move_file) for n in ("", ".", "..")]
    check("files: removing or moving needs a file name (never the folder itself)",
          all(blank) and os.path.isdir(inputs.TARGET_DIR) and os.listdir(inputs.TARGET_DIR), blank)
    for n in ("file.txt", "_CON.txt", "x.exe.txt"):
        inputs.remove_file("measurement", n)

    # EQ formats
    cfg = settings.with_auto({})
    F = [{"type": "LSQ", "freq": 105, "gain": 3.5, "q": 0.7}, {"type": "PK", "freq": 1000, "gain": -2.3, "q": 1.41}]
    check("formats: Equalizer APO text", exports.apo_text(cfg, F, -3.5).splitlines()[1] == "Filter 1: ON LSC Fc 105 Hz Gain 3.5 dB Q 0.700")
    notes = []
    check("formats: USB Audio Player PRO refuses shelves (and says why)", exports.uapp_xml(F, 0, "x", notes) is None and notes)
    check("formats: pre-amp rounded down", exports.preamp_value(cfg, -3.55) == -3.6)
    check("formats: SoundSource text", exports.soundsource_text(cfg, F, -3.5).splitlines()[1] == "Filter 1: ON LS Fc 105 Hz Gain 3.5 dB Q 0.700")
    notes = []
    check("formats: SoundSource refuses more than 32 filters (and says why)",
          exports.soundsource_text(cfg, F * 17, 0, notes) is None and notes, notes)
    check("formats: a frequency typed with decimals keeps them in the file",
          "Fc 100.25 Hz" in exports.apo_text(cfg, [{"type": "PK", "freq": 100.25, "gain": 1, "q": 1}], -1))
    grid = [{"type": "PK", "freq": 20 + 37 * i, "gain": round(-6 + 0.7 * i, 1), "q": round(0.5 + 0.37 * i, 2)} for i in range(16)]
    grid.insert(0, {"type": "LSQ", "freq": 105, "gain": 4.5, "q": 0.71})
    same = {a: exports.for_app(a, grid)[0] == grid for a in ("apo", "soundsource", "poweramp", "uapp", "voicemeeter")}
    check("formats: every file holds the EQ methods' values (whole Hz, 0.1 dB, Q 0.01) exactly, but Rockbox's Q",
          all(same.values()) and exports.for_app("rockbox", grid)[0] != grid, same)
    notes = []
    exports.rockbox_cfg([{"type": "PK", "freq": 6000, "gain": 6, "q": 8.44}], -6, notes)
    check("formats: Rockbox says how much its Q limit (6.4) changes the EQ", any("Q goes from 0.1 to 6.4" in n for n in notes), notes)
    notes = []
    exports.poweramp_json([{"type": "PK", "freq": 1000, "gain": 16, "q": 1}], -16, "x", notes)
    check("formats: Poweramp says how much its gain limit changes the EQ, and no clipping note (the cut is safe)",
          len(notes) == 1 and "+15 dB" in notes[0], notes)
    notes = []
    exports.apo_text(cfg, [{"type": "PK", "freq": 1000, "gain": 6, "q": 1}], -3, notes)
    check("formats: a pre-amp set too small by hand isn't blamed on the app", notes == [], notes)
    got = exports.parse_filters("Preamp: -6 dB\nFilter 1: ON LSC Fc 105 Hz Gain 5,5 dB Q 0.70\nFilter 2: OFF PK Fc 2000 Hz "
                                "Gain 3 dB Q 2\nFilter: ON HS Fc 8000 Hz Gain -3 dB\n# mine\n200 3 1\nLSQ 50 2 0.6")
    check("formats: your filters read from Equalizer APO lines and frequency-gain-Q lines (off ones skipped)",
          [(f["type"], f["freq"], f["gain"], f["q"]) for f in got]
          == [("LSQ", 105, 5.5, 0.7), ("HSQ", 8000, -3, 0.71), ("PK", 200, 3, 1), ("LSQ", 50, 2, 0.6)], got)
    rb = exports.rockbox_cfg(F, -3.5).splitlines()
    check("formats: Rockbox fills all 10 bands (tenths)", len(rb) == 12 and rb[1] == "eq precut: 35"
          and rb[2] == "eq low shelf filter: 105, 7, 35" and rb[3] == "eq peak filter 1: 1000, 14, -23", rb)
    notes = []
    check("formats: Voicemeeter refuses more than 6 filters (and says why)", exports.voicemeeter_xml(F * 4, 0, notes) is None and notes)
    vm = exports.voicemeeter_xml(F, -3.5, notes)
    check("formats: Voicemeeter: 8 channels x 6 cells, unused off", vm.count("<Bus ") == 48 and vm.count('EQon="1"') == 16, vm[:200])
    fs = 48000
    h = exports.impulse_response(F, -3.5, fs)
    spec = engines.np.fft.rfft(h, 1 << 20)
    fr = engines.np.fft.rfftfreq(1 << 20, 1 / fs)
    fq = engines.np.geomspace(20, 20000, 200)
    off = engines.np.interp(fq, fr, 20 * engines.np.log10(engines.np.abs(spec))) - engines.eq_gain(fq, F, fs) + 3.5
    check("formats: convolution impulse response sounds like the filters (within 0.05 dB)", abs(off).max() < 0.05, abs(off).max())
    wav = exports.wav_bytes(h, fs)
    check("formats: convolution WAV: float, stereo, the rate", wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"
          and engines.np.frombuffer(wav[20:28], "<u2").tolist()[:2] == [3, 2]
          and int.from_bytes(wav[24:28], "little") == fs)
    notes = []
    check("formats: convolution refuses a filter above the sample rate's limit (and says why)",
          exports.impulse_response([{"type": "PK", "freq": 23000, "gain": 2, "q": 1}], -2, 44100, notes) is None and notes)
    check("formats: filters that aren't numbers are named", raises(exports.clean_filters, [{"freq": 100, "gain": "x", "q": 1}])
          == "Filter 1: its gain isn't a number.")
    check("formats: filters outside the filter table's limits are named (Q 0 would break an EQ app)",
          raises(exports.clean_filters, [{"freq": 100, "gain": 1, "q": 0}]) == "Filter 1: its Q (0) is outside 0.03 to 27.")
    long_name = "D" * 60 + " to " + "T" * 60 + " - best fit 10f"
    b = exports.file_base(long_name)
    check("formats: long file names keep the method", len(b) <= exports.NAME_MAX and b.endswith(" - best fit 10f"), b)

    # the curves and the EQ methods
    t, meas = inputs.selected(cfg)
    curves, mt, tt = pipeline.load(cfg, t, meas)
    finite = all(map(lambda a: engines.np.isfinite(a).all(), (curves["f"], curves["meas"], curves["target"])))
    check("curves: loaded, averaged, finite", finite and len(curves["channels"]) == len(meas))
    no_eq = engines.rms_error(curves["f"], curves["meas"], curves["target"], cfg["scoring"]["band_hz"])
    out = pipeline.run_mode("site_single", cfg, curves, mt, tt)
    check("methods: site_single lowers the error", out["pick"]["rms"] < no_eq and out["pick"]["filters"], (out["pick"]["rms"], no_eq))
    # Best fit's layouts (layouts.py): fixed bands (gains only, in the sliders' steps and range) and a device's limits
    from eq import layouts
    for lay in ("graphic_10", "spotify", "bands"):
        cg = settings.with_auto({"mode": "best_fit", "best_fit": {"layout": lay, "bands": {
            "freqs": [100, 1000, 5000], "q": 1, "step": 0.5, "gain_min": -6, "gain_max": 6}}})
        fl = pipeline.run_mode("best_fit", cg, curves, mt, tt)["pick"]["filters"]
        want, q = layouts.bands(cg["best_fit"])
        check(f"methods: Best fit, fixed bands ({lay}): its bands, only the gains, in 0.5 dB steps within ±6 dB",
              [f["freq"] for f in fl] == want and all(f["q"] == q and f["type"] == "PK" and -6 <= f["gain"] <= 6
                                                      and abs(f["gain"] * 2 - round(f["gain"] * 2)) < 1e-9 for f in fl), fl)
    cd = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"pick": "lowest"}, "best_fit": {
        "layout": "app:moondrop_free_dsp", "filter_counts": [4, 12], "gain_max": [6, 9], "q_max": [8], "random_starts": 1,
        "seed_with_site": False, "low_shelf": True, "high_shelf": False, "start_filters": ""}})
    rs = pipeline.run_mode("best_fit", cd, curves, mt, tt)["results"]
    check("methods: Best fit, a device layout keeps to it (Moondrop Free DSP: 9 peaking filters, -12..+3 dB, Q 8 of its 10, 40 Hz up)",
          all(len(r["filters"]) <= 9 and all(f["type"] == "PK" and -12 <= f["gain"] <= 3 and f["q"] <= 8 and f["freq"] >= 40
                                              for f in r["filters"]) for r in rs) and max(r["rows"] for r in rs) == 9,
          [(r["rows"], r["filters"]) for r in rs])
    # Retry from these filters keeps them exactly (they were written like a saved file: Q to the Q decimals, gain 0.1 dB)
    own = [{"type": "PK", "freq": 105.5, "gain": 3.25, "q": 1.26, "enabled": True},
           {"type": "LSQ", "freq": 80, "gain": -1.05, "q": 0.707, "enabled": True}]
    check("retry: your filters written as they are (Q 1.26 stays 1.26 with Q decimals 1)",
          exports.parse_filters(exports.filters_text(own)) == [dict(f) for f in own], exports.filters_text(own))
    # the fits' count shown is the real one (your own filters' fit is one more)
    said = []
    cm = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": {
        "filter_counts": [2, 3], "gain_max": [6], "q_max": [2], "random_starts": 1, "seed_with_site": False,
        "start_filters": "1000 2 1", "start_keep": False, "fight_penalty": [0.01]}})
    rs = pipeline.run_mode("best_fit", cm, curves, mt, tt, progress=lambda d, t, m="": said.append((t, m)))["results"]
    totals = {t for t, m in said if m.startswith(("Fits", "Starting"))}
    check("progress: the number of fits said is the number made", totals == {len(rs)} and len(rs) == 3, (totals, len(rs)))
    # a device's limits leave ranges to fit in (an inverted frequency range or Q from = Q max: every fit failed, an
    # EQ with no filters)
    dv = lambda lay, n=0, **bf: layouts.device_settings(settings.with_auto({"best_fit": {"layout": lay, **bf}})["best_fit"], n)
    md, qx, mi = (dv("app:moondrop_free_dsp", freq_range=[12000, 20000]), dv("app:qudelix_5k", q_min=8, q_max=[10, 12]),
                  dv("app:minidsp_2x4hd", q_min=0.1, q_max=[0.3]))
    check("devices: ranges outside a device's become the device's (never empty)", md["freq_range"] == [40, 10000]
          and (qx["q_min"], qx["q_max"]) == (0.1, [7]) and (mi["q_min"], mi["q_max"]) == (0.5, [6]),
          (md["freq_range"], qx["q_min"], qx["q_max"], mi["q_min"], mi["q_max"]))
    cm2 = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": {
        "layout": "app:moondrop_free_dsp", "freq_range": [12000, 20000], "filter_counts": [3], "gain_max": [3],
        "q_max": [2], "random_starts": 1, "seed_with_site": False}})
    rs = pipeline.run_mode("best_fit", cm2, curves, mt, tt)["results"]
    check("devices: a run with a range outside the device's makes filters", all(r["filters"] for r in rs), rs[:1])
    # your own filters and the shelves never overfill a device (Voicemeeter: 6 cells, 5 of yours + 2 shelves + 1 = 8)
    vm = lambda n: dv("app:voicemeeter", n, low_shelf=True, high_shelf=True, filter_counts=[1, 2, 3])
    v5, v6 = vm(5), vm(6)
    check("devices: your filters take room first, then the shelves go, then nothing is added",
          (v5["low_shelf"], v5["high_shelf"], v5["filter_counts"], v5.get("start_add", True)) == (False, False, [1], True)
          and v6.get("start_add") is False, (v5, v6))
    c7 = settings.with_auto({"mode": "best_fit", "best_fit": {"layout": "app:voicemeeter",
                                                             "start_filters": "\n".join(f"{100 * 2 ** i} 1 1" for i in range(7))}})
    try:
        pipeline.check_run("best_fit", c7, curves)
        msg7 = ""
    except ValueError as err:
        msg7 = str(err)
    check("devices: more filters of yours than the device holds is said before the run", "more than Voicemeeter" in msg7, msg7)
    # a graphic EQ app's sliders: its stated range and steps, whatever best_fit.bands was left at
    fx = settings.with_auto({"best_fit": {"layout": "app:fxsound", "bands": {"gain_min": -16, "gain_max": 16, "step": 0.1}}})
    check("graphic EQ apps: their sliders' range and steps are kept (FxSound ±12 dB in 1 dB)",
          layouts.sliders(fx["best_fit"]) == (-12, 12, 1.0) and "1 dB steps" in autoset.describe(dict(fx, mode="best_fit")),
          (layouts.sliders(fx["best_fit"]), autoset.describe(dict(fx, mode="best_fit"))))
    # the automatic notes say the device's limits (they said 32 filters, +10 dB for a 9-filter, +3 dB device)
    an = {"features": 12, "no_eq_rms": 3, "band_top": 10000, "band_why": "default", "n_files": 1, "unstable_from": None,
          "need_boost": 8, "boost_at": 3000, "need_cut": -6, "cut_at": 100, "q_need": 3, "q_at": 2000, "bass_step": 0,
          "treble_step": 0, "data_top": 20000, "agree_to": None}
    notes = " ".join(n["text"] for n in autoset.plan(settings.with_auto({"mode": "best_fit", "best_fit": {
        "layout": "app:moondrop_free_dsp"}}), an)["notes"])
    check("automatic settings: a device's notes give its limits (9 filters, +3 dB)", "Up to 9 filters" in notes
          and "Boosts up to +3 dB" in notes, notes[:200])
    # each note: the value and the fact about your curves behind it, in a line (why the app works so: Help)
    busy = dict(an, treble_step=4, bass_step=-4, unstable_from=5600, band_why="unstable", n_files=10)
    wordy = [n["text"] for n in autoset.plan(settings.with_auto({"mode": "best_fit", "auto": {"level": 100}}), busy)["notes"]
             if len(n["text"]) > 80 or "test" in n["text"]]
    check("automatic settings: each note is a value and its fact in a line (the reasons are on the Help page)", not wordy, wordy)
    # the fits counted as the run makes them (your own filters' too)
    bfc = dict(settings.with_auto({"best_fit": {"filter_counts": [4, 6], "gain_max": [6, 9], "q_max": [2, 3],
                                                "fight_penalty": [0.01]}})["best_fit"], build="scratch")
    counts = (engines.fit_count(bfc), engines.fit_count(bfc, 3), engines.fit_count(dict(bfc, start_keep=False), 3),
              engines.fit_count(dict(bfc, start_add=False), 3))
    check("fits: counted with your own filters (kept: one more; adjusted: one per limit; nothing added: yours only)",
          counts == (8, 9, 12, 1), counts)
    bfg = dict(bfc, build="grow")
    grown = (engines.fit_count(bfg), engines.fit_count(dict(bfg, start_filters="1000 2 1"), 1),
             engines.grows(bfg), engines.grows(dict(bfg, start_filters="1000 2 1", start_keep=False)),
             engines.grows(dict(bfg, start_add=False)))
    both = engines.fit_count(dict(bfc, fight_penalty=[0.003, 0.01]))
    check("fits: growing, one per limit (your filters kept: one more); adjusted or nothing added: each count on its "
          "own; two penalties, twice the fits",
          grown == (4, 5, True, False, False) and both == 16, (grown, both))
    grow_checks(cfg, curves, mt, tt)
    review2_maths_checks()
    removed_settings_checks()
    from eq import eq_apps
    check("EQ apps: a shared layout's band count from the layout itself; no empty 'Devices' group",
          eq_apps.summary("boom3d").startswith("31 fixed bands") and eq_apps.summary("spotify").startswith("6 fixed bands")
          and {x["group"] for x in layouts.listing()} == {"Any", "Fixed bands", "EQ apps (Your EQ app)"},
          (eq_apps.summary("boom3d"), {x["group"] for x in layouts.listing()}))
    # saved files: a Q never rounds down to 0 (Q decimals 1 wrote "Q 0.0")
    c1 = settings.with_auto({"export": {"q_decimals": 1}})
    notes_q = []
    q_text = exports.apo_text(c1, [{"type": "PK", "freq": 1000, "gain": 2, "q": 0.04}], -2.0, notes_q)
    check("formats: a Q under half a step is written as the smallest step, not 0 (and said)",
          "Q 0.1" in q_text and "Q 0.0" not in q_text and notes_q, (q_text, notes_q))
    # Equalizer APO's width in octaves and shelf slopes are read; its other filter types are named
    apo_lines = ("Filter 1: ON PK Fc 3000 Hz Gain -2 dB BW Oct 1\nFilter 2: ON LSC 12 dB Fc 100 Hz Gain 4 dB Q 0.7\n"
                 "Filter 3: OFF LP Fc 18000 Hz")
    read_apo = exports.parse_filters(apo_lines)
    check("formats: APO's \"BW Oct\" and shelf slopes are read (an OFF line of another type is skipped)",
          [(f["type"], f["freq"], round(f["q"], 3)) for f in read_apo] == [("PK", 3000, 1.414), ("LSQ", 100, 0.7)], read_apo)
    check("formats: another APO filter type is named as not supported",
          "“HP” filters aren't supported" in (raises(exports.parse_filters, "Filter 1: ON HP Fc 30 Hz") or ""))
    # only the formats there are
    check("formats: an unknown file format is refused by name",
          raises(exports.file_names, cfg, "x", ["APO"]) == "Unknown file format: APO")
    # every file written in one step (Equalizer APO reloads a file it uses as soon as it changes)
    atomic, real_write = [], textfile.write_atomic
    textfile.write_atomic = lambda p, text, **k: (atomic.append(os.path.basename(p)), real_write(p, text, **k))
    out_tmp = os.path.join(top, "Saved EQs", "atomic")
    try:
        all_on = settings.with_auto({"export": {k: True for k in exports.FORMATS}})
        wrote, _ = exports.write(all_on, [{"type": "PK", "freq": 1000, "gain": 2, "q": 1}], -2.0, "Atomic", out_dir=out_tmp)
        exports.write_report(curves, cfg["scoring"]["band_hz"], "Dev", "Tgt", 1, [], out_dir=out_tmp)
    finally:
        textfile.write_atomic = real_write
    check("formats: every file (the WAV and the report too) is written in one step",
          sorted(atomic) == sorted([os.path.basename(p) for p in wrote.values()] + ["Dev to Tgt - report.html"]), atomic)
    # not asked about a file this EQ can't be written in (UAPP holds no shelves)
    shelf = [{"type": "LSQ", "freq": 100, "gain": 3, "q": 0.7}]
    open(os.path.join(out_tmp, "Atomic - UAPP.xml"), "a").close()
    asked = exports.existing(all_on, "Atomic", ["apo", "uapp"], out_dir=out_tmp, filters=shelf)
    check("formats: saving doesn't ask about an app's file it won't write", asked == ["Atomic - filters.txt"], asked)
    # the report: names as text ("</script>" in one doesn't end its script; the hover builds no HTML)
    rp = os.path.join(out_tmp, "names.html")
    from eq import report
    report.write(rp, title="T", subtitle="S", curves=curves, band=[20, 10000],
                 cards=[{"title": "Mine </script><i>x", "text": "t", "filters": [], "eq": curves["meas"], "rms": 1.0}])
    with open(rp, encoding="utf-8") as fh:
        page_html = fh.read()
    check("report: names can't end its script or become HTML in the hover",
          page_html.count("</script>") == 1 and "<\\/script>" in page_html and "innerHTML" not in page_html)
    # two filters at one spot are merged only while the sum keeps within the gain limits (a +3 dB device got +6)
    np_ = engines.np
    two = np_.array([np_.log10(3000), 3.0, np_.log(2.0), np_.log10(3010), 3.0, np_.log(2.02)])
    lb, ub = np_.array([1, -12, -3] * 2, float), np_.array([5, 3, 3] * 2, float)
    kept_two, merged = engines._tidy(("PK", "PK"), two, lb, ub), engines._tidy(("PK", "PK"), two, lb, ub + [0, 6, 0] * 2)
    check("fits: split filters merged only within the gain limit (two +3 dB stay two at a +3 dB limit)",
          [f["gain"] for f in kept_two] == [3.0, 3.0] and [f["gain"] for f in merged] == [6.0], (kept_two, merged))
    # starting points: a short website seed is padded across the range (was 32, 64, 128 kHz: piled at the top), and
    # random starts spread even when the filter range starts above 12 kHz (were all at its bottom)
    task = {"n": 8, "q_min": 0.5, "q_max": 2, "gain_max": 6, "gain_min": -12, "freq_low": 20, "freq_high": 16000,
            "starts": 2, "shelves": {"low": False, "high": False},
            "seeds": [{"filters": [(100.0, 2.0, 1.0), (1000.0, -3.0, 2.0)], "rms": 1.0}]}
    engines._bf = {"fb": curves["f"], "fs": 48000, "tb": curves["target"], "mb": curves["meas"]}  # (for AutoEq's start)
    pad = [f for f, g, q in engines._starting_points(task)[0][2:]]
    hi_starts = engines._starting_points(dict(task, freq_low=13000, freq_high=20000, seeds=[]))[-2:]
    engines._bf = None
    check("fits: padded seeds spread within 20 Hz-12 kHz; random starts spread above 12 kHz too",
          len(pad) == 6 and len(set(pad)) == 6 and all(20 < f < 12000 for f in pad)
          and all(len({round(f) for f, g, q in s}) > 4 and all(13000 <= f <= 20000 for f, g, q in s) for s in hi_starts),
          (pad, [[round(f) for f, g, q in s] for s in hi_starts]))
    # a task that fails stops the rest (they ran to the end before the error showed)
    from concurrent.futures import ThreadPoolExecutor

    def task_fn(i):
        if i == 0:
            raise RuntimeError("broken fit")
        time.sleep(1)
    t0 = time.time()
    try:
        with ThreadPoolExecutor(1) as pool:
            engines.run_tasks(pool, task_fn, [0, 1, 2, 3, 4])
    except RuntimeError:
        pass
    check("runs: one failed fit stops the others (the error shows at once)", time.time() - t0 < 2.5, round(time.time() - t0, 1))
    # an empty scored range is said, not scored as NaN
    check("scoring: a scored range without curve points is said (was NaN)",
          "has no curve points" in (raises(engines.rms_error, curves["f"], curves["meas"], curves["target"], [19900, 20000]) or ""))
    # the queue errors hidden only while workers are being stopped
    seen_err, real_err = [], engines._feeder_error
    engines._feeder_error = lambda e, obj: seen_err.append(e)
    try:
        engines._stopping["on"] = False
        engines._quiet_feeder_error(OSError("pipe"), None)
        engines._stopping["on"] = True
        engines._quiet_feeder_error(OSError("pipe"), None)
    finally:
        engines._feeder_error, engines._stopping["on"] = real_err, False
    check("runs: a queue's error goes to the log unless workers are being stopped", len(seen_err) == 1, seen_err)
    # counting points and the GraphicEQ text: one V8 per thread, not one per call
    made, real_racer = [], engines._racer
    engines._racer = lambda: (made.append(1), real_racer())[1]
    engines._kept.__dict__.pop("ctxs", None)
    try:
        counts = [engines.count_points(mt[0]) for _ in range(5)]
        texts = [engines.graphic_eq_text(cfg, [{"type": "PK", "freq": 1000, "gain": 2, "q": 1}]) for _ in range(3)]
    finally:
        engines._racer = real_racer
    check("files: points counted and GraphicEQ written with one V8 each per thread", len(made) == 2 and len(set(counts)) == 1
          and counts[0] >= 32 and len(set(texts)) == 1 and texts[0].startswith("GraphicEQ"), (len(made), counts[:1], texts[0][:20]))
    # whether a sweep is cached: the texts the curves were loaded from, not every file read again
    reads, real_read_text = [], inputs.read_text
    pipeline._SWEEPS["dummy"] = []
    inputs.read_text = lambda p: (reads.append(p), real_read_text(p))[1]
    try:
        pipeline.load(cfg, t, meas)
        n_load = len(reads)
        [pipeline.sweep_cached(cfg) for _ in range(4)]
    finally:
        inputs.read_text = real_read_text
        pipeline._SWEEPS.pop("dummy")
    check("estimates: asking whether a sweep is cached reads no files again", len(reads) == n_load, (n_load, len(reads)))
    # scored to 20 kHz, a measurement falling off at the top: the grid's point past 20 kHz (no data) isn't guarded, so
    # the EQ isn't pulled back to 0 dB there (a filter was spent cutting at 20 kHz: 0.35 dB left, now 0.05)
    fall = dict(curves, meas=curves["target"] - engines.np.clip((curves["f"] - 16000) / 400, 0, 10))
    ce = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"band_hz": [20, 20000]},
                             "best_fit": {"filter_counts": [4], "gain_max": [12], "q_max": [4], "random_starts": 2,
                                          "seed_with_site": False, "freq_range": [20, 20000]}})
    r = pipeline.run_mode("best_fit", ce, fall, mt, tt)["best"]
    check("methods: Best fit scored to 20 kHz follows a fall-off there (the grid's point past 20 kHz isn't guarded)",
          r["rms"] < 0.15 and not any(f["freq"] > 19500 and f["gain"] < 0 for f in r["filters"]), (r["rms"], r["filters"]))
    # Best fit from your own filters: kept exactly, filters added, and yours alone among the results
    mine = "Filter 1: ON PK Fc 1000 Hz Gain -2 dB Q 1.5\n120 3 0.8"
    small = {"filter_counts": [2, 4], "gain_max": [6], "q_max": [3], "random_starts": 2, "seed_with_site": False,
             "fight_penalty": [0.01],
             "low_shelf": False, "high_shelf": False, "start_filters": mine}
    cb = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"pick": "lowest"},
                             "best_fit": dict(small, start_keep=True)})
    out = pipeline.run_mode("best_fit", cb, curves, mt, tt)
    kept = [{"type": "PK", "enabled": True, "freq": 1000.0, "gain": -2.0, "q": 1.5}, {"type": "PK", "enabled": True, "freq": 120.0, "gain": 3.0, "q": 0.8}]
    rows = sorted(r["rows"] for r in out["results"])
    check("methods: Best fit keeps your filters exactly and adds to them (and scores yours alone)",
          rows == [0, 2, 4] and all(r["filters"][:2] == kept and len(r["filters"]) >= 2 + (r["rows"] > 0) for r in out["results"])
          and min(r["rms"] for r in out["results"] if r["rows"]) < min(r["rms"] for r in out["results"] if not r["rows"]),
          [(r["rows"], r["rms"], r["filters"][:3]) for r in out["results"]])
    cb = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": dict(small, start_keep=False)})
    out = pipeline.run_mode("best_fit", cb, curves, mt, tt)
    alone = [r for r in out["results"] if not r["rows"]]
    check("methods: Best fit may adjust your filters when asked (yours alone, adjusted, score better than as typed)",
          alone and alone[0]["filters"] != kept and alone[0]["rms"] < engines.finish({"filters": kept}, curves, cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"])["rms"],
          [(r["rows"], r["rms"]) for r in out["results"]])
    cb = settings.with_auto({"mode": "best_fit", "best_fit": dict(small, start_filters="Filter 1: ON PK Fc 100 Hz Gain 3 dB\nhello")})
    check("methods: your filters that can't be read are named before the run",
          (raises(pipeline.run_mode, "best_fit", cb, curves, mt, tt) or "").startswith("Your filters, line 1"))
    big = settings.with_auto({"site_sweep": {"freq_high": list(range(1000, 21000, 10)), "q_max": [0.5 + i / 100 for i in range(300)]}})
    t0 = time.time()
    est = autoset.estimate(big, "site_sweep")
    check("methods: a huge sweep is refused, and its estimate stays quick",
          "at most" in (raises(pipeline.check_run, "site_sweep", big, curves) or "") and time.time() - t0 < 1 and est > 3600)
    huge = "".join(f"{20 * 1.1 ** i:.2f}\t{900000 if i == 40 else 80}\n" for i in range(80))
    check("curves: absurd dB values give a clear message", "values the app can't use" in (raises(engines.load_curves, cfg, [huge], tt) or ""))

    # automatic settings: every method and slider end within the limits, pairs in order
    an = autoset.analyse(cfg, curves, mt)
    for mode in settings.MODES:
        for lv in (0, 50, 100):
            c2 = settings.with_auto({"mode": mode, "auto": {"level": lv}})
            p = autoset.plan(c2, an)
            autoset.apply(c2, p["values"])
            ok = settings.clamp(json.loads(json.dumps(c2))) == c2
            check(f"auto settings: {mode} at {lv} valid, with reasons", ok and p["notes"], p["values"])
    # no cap below where fits stop improving: the counts reach their ceiling, the audible pick at 0.25 dB
    v = {mode: autoset.plan(settings.with_auto({"mode": mode}), an)["values"] for mode in ("best_fit", "site_sweep")}
    reach = (max(v["best_fit"]["best_fit.filter_counts"]), max(v["site_sweep"]["site_sweep.filter_rows"]),
             v["best_fit"]["scoring.pick"], v["best_fit"]["scoring.ear_db"])
    check("auto settings: filter counts reach their ceiling, the audible pick (0.25 dB)",
          reach == (settings.LIMITS["best_fit.filter_counts"]["max"], settings.LIMITS["site_sweep.filter_rows"]["max"],
                    "audible", 0.25), reach)

    # rigs
    from eq import databases
    ae = "https://github.com/jaakkopasanen/AutoEq"
    forms = [databases.name_form(n) for n in ("Harman IE 2019", "Harman over-ear 2018", "HD600", "Tie T3")]
    forms += [databases.item_form({"kind": "measurement", "name": "HD600", "sub": "oratory1990 · over-ear", "site_url": ae}),
              databases.item_form({"kind": "measurement", "name": "X", "sub": "B", "site_url": "https://earphonesarchive.squig.link/headphones/"}),
              databases.item_form({"kind": "target", "name": "Harman IE 2019", "sub": "target", "site_url": ae})]
    check("search filters: device type from AutoEq's folders, the database and names", forms == ["iem", "hp", "", "", "hp", "hp", "iem"], forms)
    # the EQ apps (eq_apps.py): each described, sourced, with a layout Best fit knows and a file the app can write
    from eq import eq_apps
    bad_apps = [k for k, a in eq_apps.APPS.items()
                if not (a["name"] and a["how"] and a.get("source", "").startswith("http") and a["platforms"]
                        and set(a["platforms"]) <= set(eq_apps.PLATFORMS) and a["kind"] in ("parametric", "graphic", "curve", "site")
                        and eq_apps.layout_key(k) in layouts.KEYS and (a.get("file") is None or a["file"] in exports.FORMATS))]
    check("EQ apps: each has platforms, a source, how to load the EQ, a known layout and file", not bad_apps, bad_apps)
    c_app = settings.with_auto({"eq_app": "poweramp", "best_fit": {"layout": "moondrop_free_dsp"}})
    bf_vm = dict(settings.DEFAULTS["best_fit"], layout="app:voicemeeter", filter_counts=[3, 6, 20], low_shelf=True, high_shelf=True)
    check("EQ apps: a choice is kept, an old device key becomes the app's; an app's shelves take its bands (Voicemeeter 6)",
          c_app["eq_app"] == "poweramp" and c_app["best_fit"]["layout"] == "app:moondrop_free_dsp"
          and settings.with_auto({"eq_app": "nope"})["eq_app"] == ""
          and layouts.device_settings(bf_vm)["filter_counts"] == [3, 4], (c_app["eq_app"], layouts.device_settings(bf_vm)["filter_counts"]))
    # the database lists: the saved copy isn't written again when no list was downloaded (it's large: that slowed the start)
    real_cache, site = databases.CACHE_PATH, {"name": "Test", "url": "https://example.invalid/", "short": "T"}
    databases.CACHE_PATH = os.path.join(top, "data", "cache", "db-test.json")
    try:
        textfile.write_json(databases.CACHE_PATH, {site["url"]: {"time": time.time(), "conf": {}, "v": databases.LIST_VERSION,
                                                                 "items": [{"kind": "measurement", "name": "X", "sub": ""}]}})
        os.utime(databases.CACHE_PATH, (1, 1))
        databases.refresh_now([site])
        check("databases: recent lists read, not written again", os.path.getmtime(databases.CACHE_PATH) == 1
              and databases.status()["count"] == 1, databases.status())
    finally:
        databases.CACHE_PATH = real_cache
        databases.set_items([])
    # reading graph-tool sites (pages served from here, nothing downloaded)
    pages = {
        "https://a.test/": ('<meta http-equiv="refresh" content="0; url=https://b.test/hp/">', "https://a.test/"),
        "https://b.test/hp/": ('<script src="assets/js/config.js"></script>', "https://b.test/hp/"),
        "https://b.test/hp/assets/js/config.js": ('const init = ["x"], DIR = "data/", // Where "files" live\n'
                                                  '   // PHONE_BOOK = "phone_book.json", /* old */\n'
                                                  '   url = "https://x.test/a//b";', ""),
        "https://m.test/": ('<script src="./config.js?cachebust"></script>', "https://m.test/"),
        "https://m.test/config.js?cachebust": ('const CONFIG = { PATH: { PHONE_MEASUREMENT: "./data/phones", // c\n'
                                               'TARGET_MEASUREMENT: "./data/targets" },\n'
                                               'TARGET_MANIFEST: { default: [ { type: "Harman", files: ["Harman IE 2019v2", "A \\"b\\""] } ],'
                                               ' i18n: { ko: [ { type: "하만" } ] } } };', ""),
    }
    real_get = databases._get
    databases._get = lambda url, **k: pages[url]
    try:
        old = databases._squig_config({"url": "https://a.test/"})
        new = databases._squig_config({"url": "https://m.test/"})
    except Exception as e:  # noqa: BLE001
        old = new = {"error": repr(e)}
    finally:
        databases._get = real_get
    check("databases: a moved page followed, a commented-out setting ignored",
          old.get("base") == "https://b.test/hp/data/" and old.get("phone_book") == "https://b.test/hp/data/phone_book.json", old)
    check("databases: modernGraphTool's config (folders, targets)",
          new.get("base") == "https://m.test/data/phones/" and new.get("targets_base") == "https://m.test/data/targets/"
          and new.get("phone_book") == "https://m.test/data/phone_book.json"
          and new.get("targets") == [{"type": "Harman", "files": ["Harman IE 2019v2", 'A "b"']}], new)
    pv = databases._phone_variants
    got = [pv("X1"), pv({"name": "Maxwell", "file": ["M (EQ A)", "M (EQ B)"], "prefix": "M", "samples": 3}),
           pv({"name": "R50x", "hptfs": [{"suffix": "", "files": ["R Center", "R Front"]}]}),
           pv({"name": "Y", "file": ["Y a"], "suffix": ["(a)"], "variants": [{"suffix": "(a)", "file": "Y a", "samples": {"count": 4}}]})]
    check("databases: phone-book entries (own samples, seating sets, variants)", got == [
        [("X1", {"file": "X1"})],
        [("Maxwell (EQ A)", {"file": "M (EQ A)", "samples": 3}), ("Maxwell (EQ B)", {"file": "M (EQ B)", "samples": 3})],
        [("R50x", {"file": "R Center", "files": ["R Center", "R Front"]})],
        [("Y (a)", {"file": "Y a", "samples": 4})]], got)
    check("rigs: tags", [rigs.rig_tag(r) for r in (("5128", True), ("711", False), (None, False))] == ["5128", "711?", ""])
    check("rigs: the sample IEM is on a 5128", rigs.file_rig(os.path.basename(meas[0]))[0] == "5128", meas[0])
    named = [rigs.target_rig(n, {})[0] for n in ("Harman IE 2019.txt", "Harman OE 2018 Linear.txt", "Crinacle OE.txt",
                                                  "IEF Neutral 2020.txt")]
    check("rigs: target rig from its name (over-ear names before the IEM ones: review 2)",
          named == ["711", "43AG", "43AG", "711"], named)
    check("rigs: converting by zero changes nothing", "\t1.000" in rigconv.convert_text("1000 1\n", [0.0] * len(rigconv.data()["grid"])))
    # a database's own conversion (build_unit_conversions.py): used for files from that database, whatever its rig
    from eq import rigmap
    saved_sources, n = rigs.sources(), len(rigconv.data()["grid"])
    shipped = rigconv.data().get("units", [])
    check("rig units: the shipped conversions are complete", shipped and all(
        u["from"] in rigs.RIGS and len(u["conversion"]) == n and len(u["uncertainty"]) == n and u["device"] in ("iem", "headphone")
        for u in shipped), len(shipped))
    try:
        rec = {"site_url": "https://fakedb.squig.link/", "site": "Fake DB", "name": "Test IEM"}
        rigs.record_source(["Test IEM (Fake DB) L1.txt"], rec)
        rigs.record_source(["Test IEM 711 (Fake DB) L1.txt"], dict(rec, rig="711"))
        key = rigmap.unit_key(rec)
        fake = {"unit": key, "name": "Fake DB", "device": "iem", "from": "5128", "rig": None, "models": 30,
                "conversion": [2.0] * n, "uncertainty": [1.0] * n, "mismatch": [3.0] * n, "bands": {"3000-6000": [3.0, 1.5], "10000-16000": [5.0, 3.0]}}
        rigconv.data().setdefault("units", []).append(fake)
        check("rig units: a file's database from where it was downloaded", rigs.file_unit("Test IEM (Fake DB) L1.txt") == key
              and rigs.file_unit("unknown.txt") is None, rigs.file_unit("Test IEM (Fake DB) L1.txt"))
        c = settings.with_auto({})
        st = rigconv.status(c, "IEM 5128 DF.txt", [os.path.join(top, "Measurements", "Test IEM (Fake DB) L1.txt")])
        check("rig units: a database of unknown rig gets its own conversion", st.get("state") == "available" and st.get("unit") == "Fake DB"
              and st["meas_rig"] is None and st["conversion"][0] == 2.0, {k: st.get(k) for k in ("state", "unit", "meas_rig")})
        st = rigconv.status(c, "IEM 5128 DF.txt", [os.path.join(top, "Measurements", "Test IEM 711 (Fake DB) L1.txt")])
        check("rig units: its own conversion before the rigs' average", st.get("unit") == "Fake DB" and st["meas_rig"] == "711", st.get("unit"))
        st = rigconv.status(c, "Harman IE 2019.txt", [os.path.join(top, "Measurements", "Test IEM 711 (Fake DB) L1.txt")])
        check("rig units: none from that rig: as before (same rig)", st.get("state") == "same" and not st.get("unit"), st.get("state"))
        # ranking measurements ("Other measurements of this model"): the rig counts by the error left after converting
        from eq import compare
        own, avg = rigconv.expected("iem", "5128", None, key), rigconv.expected("iem", "5128", "711", None)
        check("rig ranking: own conversion, the rigs' average, same rig, unknown", own["how"] == "own" and avg["how"] == "rigs"
              and 0 <= avg["rig_part"] < avg["error"] and rigconv.expected("iem", "5128", "5128", None)["how"] == "same"
              and rigconv.expected("iem", "5128", None, None)["how"] == "unknown", (own.get("how"), avg))
        base = {"sure": True, "dev": None, "bass": None, "n_files": 2, "fmin": 20, "fmax": 20000, "points": 300,
                "channels": ["L", "R"], "source": "X"}
        scores = {}
        for name, c in (("same", dict(base, rig="5128", conv={"how": "same"})), ("converted", dict(base, rig="711", conv=avg)),
                        ("off", dict(base, rig="711", conv=rigconv.expected("iem", "5128", "711", None, enabled=False))),
                        ("no data", dict(base, rig="711", conv={"how": "nodata"}))):
            compare.score(c, "5128")
            scores[name] = c["score"]
        check("rig ranking: same rig > converted > converting off > no data", scores["same"] > scores["converted"] > scores["off"] > scores["no data"], scores)
        pu = rigconv.page_units()
        check("rig units: the search list's marks", "Fake DB" in pu and pu["Fake DB"][0]["from"] == "5128", list(pu)[:3])
    finally:
        rigconv.data()["units"] = [u for u in rigconv.data().get("units", []) if u.get("name") != "Fake DB"]
        textfile.write_json(rigs.SOURCES_PATH, saved_sources, indent=1)

    # Send to Equalizer APO was taken out: its settings in an old settings.json or preset go
    old = settings.with_auto({"export": {"apo_folder": "C:\\x", "apo_on_save": True, "apo_enable": True, "poweramp": True}})
    check("settings: Send to Equalizer APO's old settings are dropped (the rest kept)",
          not any(k.startswith("apo_") for k in old["export"]) and old["export"]["poweramp"] is True, old["export"])

    # your EQs to compare: one list per IEM, kept between sessions (the copy's own data folder)
    from eq import listening
    fl = [{"type": "PK", "freq": 1000, "gain": -2, "q": 1}]
    kept = listening.put("IEM A", [{"key": "a", "name": "  My   EQ ", "filters": fl, "shown": False, "color": 3},
                                   {"name": "x" * 200, "filters": fl + [{"type": "LSQ", "freq": 100, "gain": 3, "q": 0.7}]}])
    check("EQs to compare: kept per IEM, cleaned (names, filters, graph on/off, colour)",
          listening.get("IEM A") == kept and kept[0]["name"] == "My EQ" and kept[0]["shown"] is False and kept[0]["color"] == 3
          and len(kept[1]["name"]) == 80 and kept[1]["shown"] is True and listening.get("IEM B") == [], kept)
    check("EQs to compare: at most 12 per IEM; an EQ without filters or an IEM without a name is refused (and named)",
          "At most 12" in (raises(listening.put, "IEM A", [{"filters": fl}] * 13) or "")
          and "has no filters" in (raises(listening.put, "IEM A", [{"name": "E", "filters": []}]) or "")
          and "Choose a measurement" in (raises(listening.get, "  ") or "") and listening.get("IEM A") == kept)
    listening.put("IEM A", [])
    check("EQs to compare: an emptied list goes", "IEM A" not in textfile.read_json(listening.PATH, default={}))

    # history (the copy's own data folder)
    from eq import history
    history.remove(None)
    e = {"key": "a-1", "device": "IEM", "target": "T", "mode": "best_fit", "filters": [{"type": "PK", "freq": 100, "gain": 2, "q": 1}],
         "rms": 0.3, "preamp": -2.1, "n_filters": 1, "saved": True}
    history.add(e)
    items = history.add({**e, "saved": False, "rms": 0.25})
    check("history: the same EQ again updates it, and it stays saved", len(items) == 1 and items[0]["saved"] and items[0]["rms"] == 0.25, items)
    check("history: an EQ without a name or with bad filters is refused",
          raises(history.add, {**e, "key": ""}) is not None and raises(history.add, {**e, "key": "b", "filters": [{"q": 0}]}) is not None)
    old_max, history.MAX = history.MAX, 3
    for i in range(5):
        history.add({**e, "key": f"u{i}", "saved": False})
    keys = [x["key"] for x in history.entries()]
    history.MAX = old_max
    check("history: past its size, the oldest unsaved EQs go first", keys == ["a-1", "u3", "u4"], keys)
    check("history: one removed, then all", [x["key"] for x in history.remove(["u3"])] == ["a-1", "u4"] and history.remove(None) == [])

    # Undo after averaging removes the file made, also under "… (2)"
    from eq import compare
    real_avg = compare.average
    try:
        for level in (80, 83):
            compare.average = lambda keys, name, lv=level: (
                "Avg test.txt", "".join(f"{20 * 1.1 ** k:.2f}\t{lv + k % 5}\n" for k in range(80)), "711", ["a", "b"])
            avg = api.compare_average({"keys": ["x", "y"], "settings": cfg})
    finally:
        compare.average = real_avg
    check("files: Undo after averaging removes the new file, also when it was saved as \"… (2)\"",
          avg["names"] == ["Avg test (2).txt"] and avg["created"] == ["Avg test (2).txt"], avg.get("created"))
    for n in ("Avg test.txt", "Avg test (2).txt"):
        inputs.remove_file("measurement", n)
    # "as" says target or measurement
    check("use: an unknown \"as\" is refused (was taken for a measurement)",
          raises(api.use, {"src": "app", "kind": "measurement", "names": ["x"], "as": "Target"})
          == "The request doesn't say target or measurement.")
    # a run uses the page's analysis only for the curves it was made from
    tr, ms = inputs.selected(cfg)
    cs, mts, tts = pipeline.load(cfg, tr, ms)
    key = autoset.analysis_key(cfg, mts, tts)
    moved = json.loads(json.dumps(cfg)); moved["scoring"]["band_hz"][1] = 12000  # (the automatic "to" changing: same key)
    check("runs: the analysis key follows the curves, not the automatic scored range",
          key == autoset.analysis_key(moved, mts, tts) and key != autoset.analysis_key(cfg, mts[:1], tts))
    analysed, real_an = [], autoset.analyse
    autoset.analyse = lambda *a: (analysed.append(1), real_an(*a))[1]
    try:
        for an in ({"key": "an old IEM's"}, dict(real_an(cfg, cs, mts), key=key)):
            api.JOB.update(id="t", status="running")
            api._run_job("t", "site_single", json.loads(json.dumps(cfg)), an)
    finally:
        autoset.analyse = real_an
    check("runs: the page's analysis of other curves isn't used (analysed again); its own is",
          analysed == [1] and api.JOB.get("status") == "done", (analysed, api.JOB.get("status"), api.JOB.get("message")))
    api.JOB.clear(); api.JOB.update(id=None, status="idle")
    # EQs to compare read back cleaned (a hand-edited entry broke the page); looking at a list counts as using it
    stored = {"Clean IEM": {"used": 1000.0, "eqs": [{"key": "a", "name": "Fine", "filters": fl, "color": 2},
                                                    {"key": "a", "name": "Same key", "filters": fl, "color": "red"},
                                                    "not an EQ", {"name": "No filters", "filters": "x"}]}}
    textfile.write_json(listening.PATH, stored)
    got = listening.get("Clean IEM")
    check("EQs to compare: stored entries are checked on the way out (bad ones left out, keys unique, colours numbers)",
          [e["name"] for e in got] == ["Fine", "Same key"] and len({e["key"] for e in got}) == 2
          and all(isinstance(e["color"], int) for e in got), got)
    check("EQs to compare: looking at a list counts as using it (the 300-list limit drops the unused)",
          textfile.read_json(listening.PATH, {})["Clean IEM"]["used"] > time.time() - 60)
    listening.put("Clean IEM", [])
    # History's answer to a Save: the entry and the keys, not the whole history; the curves' settings kept with it
    code_h = api.history_add({"entry": {"key": "h-1", "filters": fl, "site": {"smooth_level": 5}, "rig_convert": False,
                                        "band": [20, 12000]}})
    check("history: a Save answers with the entry and the keys only; the curves' settings are kept",
          set(code_h) == {"entry", "keys"} and code_h["keys"][-1] == "h-1" and code_h["entry"]["band"] == [20.0, 12000.0]
          and code_h["entry"]["rig_convert"] is False and code_h["entry"]["site"] == {"smooth_level": 5}, code_h)
    history.remove(None)
    # a damaged history.json or listen.json is kept aside (.bad), never written over (the next save wiped every entry)
    history.add(e)
    with open(history.PATH, encoding="utf-8") as fh:
        whole = fh.read()
    with open(history.PATH, "w", encoding="utf-8") as fh:
        fh.write(whole[:-5])
    items = history.add({**e, "key": "after"})
    with open(history.PATH + ".bad", encoding="utf-8") as fh:
        bad = fh.read()
    check("history: a damaged file is kept as history.json.bad, and a new one started", [x["key"] for x in items] == ["after"]
          and bad == whole[:-5], items)
    os.remove(history.PATH + ".bad")
    history.remove(None)
    listening.put("IEM A", [{"name": "a", "filters": fl}])
    with open(listening.PATH, "w", encoding="utf-8") as fh:
        fh.write('{"IEM A": ')
    listening.put("IEM C", [{"name": "c", "filters": fl}])
    check("EQs to compare: a damaged file is kept as listen.json.bad, not written over",
          os.path.exists(listening.PATH + ".bad") and list(textfile.read_json(listening.PATH, {})) == ["IEM C"])
    os.remove(listening.PATH + ".bad")
    listening.put("IEM C", [])
    # two saves at once (the server answers in parallel threads): neither is lost, no temporary file left
    ths = [threading.Thread(target=history.add, args=({**e, "key": f"t{i}"},)) for i in range(12)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    left = [n for n in os.listdir(os.path.dirname(history.PATH)) if n.endswith(".tmp")]
    check("history: 12 saves at the same moment are all kept", len(history.entries()) == 12 and not left, (len(history.entries()), left))
    history.remove(None)

    # settings.json another program has open for a moment: waited for, then said, never set aside for the defaults
    sp = os.path.join(top, "data", "locked settings.json")
    settings.save(settings.with_auto({"scoring": {"ear_db": 0.3}}), sp)
    real_read, real_sleep = textfile.read, time.sleep
    textfile.read = lambda p: (_ for _ in ()).throw(PermissionError(13, "The file is in use"))
    time.sleep = lambda s: None
    msg = ""
    try:
        settings.load(sp)
    except OSError as err:
        msg = str(err)
    finally:
        textfile.read, time.sleep = real_read, real_sleep
    check("settings: a locked settings.json says so and stays (not moved to .bad for the defaults)",
          "another program has it open" in msg and os.path.exists(sp) and not os.path.exists(sp + ".bad")
          and settings.load(sp)["scoring"]["ear_db"] == 0.3, msg)
    os.remove(sp)
    # presets are written in one step, like settings.json
    writes, real_write = [], textfile.write_atomic
    textfile.write_atomic = lambda p, text, **k: (writes.append(p), real_write(p, text, **k))
    try:
        settings.save_preset("Selftest atomic", settings.DEFAULTS)
    finally:
        textfile.write_atomic = real_write
    check("presets: written in one step (never a cut-off preset)", writes == [settings.preset_path("Selftest atomic")], writes)
    settings.delete_preset("Selftest atomic")
    check("presets: a name that cleans down to nothing is refused (was saved over \"preset\")",
          raises(settings.preset_path, "..") == "Give the preset a name." and raises(settings.preset_path, " . ") is not None)

    # a different file of the same name is never replaced: the new set is "<name> (2)", before the channel
    other = curve.replace("\t8", "\t7", 5)
    first = inputs.add_files("measurement", [("Dup L1.txt", curve), ("Dup R1.txt", curve)])
    again = inputs.add_files("measurement", [("Dup L1.txt", curve)])
    second = inputs.add_files("measurement", [("Dup L1.txt", other), ("Dup R1.txt", curve), ("Dup L2.txt", other)])
    check("files: a different file of the same name is kept; the new set is numbered as one device (the same file: as it is)",
          first == ["Dup L1.txt", "Dup R1.txt"] and again == ["Dup L1.txt"]
          and second == ["Dup (2) L1.txt", "Dup (2) R1.txt", "Dup (2) L2.txt"]
          and inputs.device_name(second) == "Dup (2)", (first, again, second))
    # moving never replaces a different file of that name in the other folder
    inputs.add_file("target", "Dup L1.txt", other)
    moved_msg = raises(inputs.move_file, "measurement", "Dup L1.txt") or ""
    check("files: moving onto a different file of that name is refused, both kept",
          "already has a different" in moved_msg and os.path.exists(os.path.join(inputs.MEAS_DIR, "Dup L1.txt"))
          and os.path.exists(os.path.join(inputs.TARGET_DIR, "Dup L1.txt")), moved_msg)
    inputs.remove_file("target", "Dup L1.txt")
    for n in first + second:
        inputs.remove_file("measurement", n)
    # one ticked file of an IEM is still that IEM
    check("files: one seating file names its device like several do", inputs.device_name(["GATe Wide L1.txt"]) == "GATe Wide"
          and inputs.device_name(["HD 600.txt"]) == "HD 600", inputs.device_name(["GATe Wide L1.txt"]))
    # a file dropped under the name of one that came from a database isn't from that database
    rigs.record_source(["Forget L.txt"], {"site": "Fake DB", "rig": "711"})
    api.files_add({"kind": "measurement", "name": "Forget L.txt", "content": curve, "settings": cfg})
    check("files: a dropped file loses an old database record of its name (its rig)", "Forget L.txt" not in rigs.sources())
    api.files_remove({"kind": "measurement", "names": ["Forget L.txt"], "settings": cfg})
    # a write that fails leaves no temporary file
    folder_as_file = os.path.join(top, "data", "a folder")
    os.makedirs(folder_as_file, exist_ok=True)
    try:
        textfile.write_atomic(folder_as_file, "x")
    except OSError:
        pass
    left = [n for n in os.listdir(os.path.join(top, "data")) if n.startswith("a folder") and n.endswith(".tmp")]
    check("files: a write that fails leaves no temporary file behind", not left, left)
    # Windows' device names, also with spaces before the extension
    check("files: reserved names with spaces or CONIN$ are made safe",
          [textfile.safe_name(n) for n in ("CON .txt", "conin$", "aux  .json")] == ["_CON .txt", "_conin$", "_aux  .json"])
    # a damaged file set aside a second time doesn't replace the first copy, and the page is told
    bad = os.path.join(top, "data", "twice.json")
    for text in ("{ first", "{ second"):
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write(text)
        textfile.read_json_kept(bad, list)
    said = textfile.take_set_aside()
    with open(bad + ".bad", encoding="utf-8") as fh:
        first_bad = fh.read()
    check("files: a second damaged copy is kept beside the first (twice.json.2.bad), and the page is told",
          first_bad == "{ first" and os.path.exists(bad + ".2.bad") and "twice.json.2.bad" in said
          and textfile.take_set_aside() == "", said)

    # the database lists start in the background: squig.link's list (the network) never holds up the window; a
    # failed try isn't repeated for a while
    from eq import databases
    ITEM = {"name": "x", "url": "https://x.squig.link/", "type": "", "group": "added"}
    saved = databases.directory, databases.refresh_now, databases.DIRECTORY_PATH, databases._get, databases.sites_for
    seen = []
    try:
        databases.directory = lambda refresh=False: (seen.append(threading.get_ident()), time.sleep(0.5))
        databases.refresh_now = lambda sites, force=False: databases._state.update(loading=False)
        databases.sites_for = lambda cfg: []
        t0 = time.time()
        databases.start_refresh(settings.DEFAULTS)
        quick = time.time() - t0
        for _ in range(50):
            if not databases._state["loading"]:
                break
            time.sleep(0.05)
        databases.directory = saved[0]
        databases.DIRECTORY_PATH = os.path.join(top, "data", "old squigsites.json")
        textfile.write_json(databases.DIRECTORY_PATH, {"time": 0, "items": [ITEM]})
        tries = []
        databases._get = lambda *a, **k: (tries.append(1), (_ for _ in ()).throw(OSError("offline")))[1]
        lists = [databases.directory(), databases.directory(), databases.added_site("https://a.squig.link/")]
    finally:
        databases.directory, databases.refresh_now, databases.DIRECTORY_PATH, databases._get, databases.sites_for = saved
        databases._dir_failed["at"] = 0.0
    # database entries: ids that stay the same through a refresh, same-named entries told apart, and a site's own
    # channel names kept inside its download folder
    fake = {"name": "Fake site", "url": "https://fake.squig.link/", "short": "Fake"}
    saved_state, saved_confs = (dict(databases._state), list(databases.items())), dict(databases._confs)
    real_index, real_get = databases._index_squig, databases._get
    fake_lists = [[{"kind": "measurement", "name": "Aria", "sub": "Moondrop", "tag": "Fake", "ref": {"file": "Aria 2021"}},
              {"kind": "measurement", "name": "Aria", "sub": "Moondrop", "tag": "Fake", "ref": {"file": "Aria 2023"}}]]
    conf = {"base": "https://fake.squig.link/data/", "samples": 0, "channels": ["L", "\\..\\..\\..\\escape"], "targets": []}
    fetched = []
    try:
        databases._index_squig = lambda site: (fake_lists[0], conf)
        databases.CACHE_PATH, saved_cache_path = os.path.join(top, "data", "fake dbs.json"), databases.CACHE_PATH
        databases.refresh_now([fake], force=True)
        ids1 = [it["id"] for it in databases.items()]
        fake_lists[0] = [{"kind": "measurement", "name": "Blessing", "sub": "Moondrop", "tag": "Fake", "ref": {"file": "B"}}] + fake_lists[0]
        databases.refresh_now([fake], force=True)
        ids2 = [it["id"] for it in databases.items()]
        databases._get = lambda url, **k: (fetched.append(url), ("".join(f"{20 * 1.1 ** i:.2f}\t{80 + i % 5}\n" for i in range(80)), url))[1]
        esc = databases.download(ids2[1], lambda t: 99)[0]
        site_dir = os.path.join(databases.DOWNLOAD_DIR, databases.folder_name("Fake site"))
        msg_escape = "kept inside" if esc and all(textfile.inside(p, site_dir) for p in esc) else str(esc)
        conf["channels"] = ["L", "R"]
        paths_a = databases.download(ids2[1], lambda t: 99)[0]
        paths_b = databases.download(ids2[2], lambda t: 99)[0]
    finally:
        databases._index_squig, databases._get = real_index, real_get
        databases.CACHE_PATH = saved_cache_path
        databases._state.update(saved_state[0]); databases.set_items(saved_state[1])
        databases._confs.clear(); databases._confs.update(saved_confs)
    check("databases: an entry keeps its id when a database adds entries before it",
          ids1 == ids2[1:] and ids2[0] not in ids1, (ids1, ids2))
    check("databases: a site's channel names can't reach outside its download folder", msg_escape == "kept inside", msg_escape)
    check("databases: two entries of one name get their own files",
          len(paths_a) == 2 and not set(paths_a) & set(paths_b) and all("Aria 2021" in p for p in paths_a), (paths_a, paths_b))
    # a copy from before that isn't a whole curve is fetched again (an interrupted download was reused forever)
    with open(paths_a[0], "w", encoding="utf-8") as fh:
        fh.write("20 1\n30 2\n")
    fetched.clear()
    try:
        databases._index_squig = lambda site: (fake_lists[0], dict(conf))
        databases.CACHE_PATH = os.path.join(top, "data", "fake dbs.json")
        databases.refresh_now([fake], force=True)
        databases._get = lambda url, **k: (fetched.append(url), ("".join(f"{20 * 1.1 ** i:.2f}\t{80 + i % 5}\n" for i in range(80)), url))[1]
        again = databases.download(ids2[1], lambda t: len(t.splitlines()))[0]
    finally:
        databases._index_squig, databases._get = real_index, real_get
        databases.CACHE_PATH = saved_cache_path
        databases._state.update(saved_state[0]); databases.set_items(saved_state[1])
        databases._confs.clear(); databases._confs.update(saved_confs)
    with open(paths_a[0], encoding="utf-8") as fh:
        whole = fh.read()
    check("databases: a cut-off copy is fetched again (a whole one is reused)", len(fetched) == 1 and whole.count("\n") == 80,
          (fetched, whole.count("\n")))
    # a refresh asked for during one runs right after it (a database added then wasn't loaded)
    runs, real_now, real_dir = [], databases.refresh_now, databases.directory
    try:
        databases.directory = lambda refresh=False: []
        databases.refresh_now = lambda sites, force=False: (runs.append(1), time.sleep(0.3),
                                                            databases._state.update(loading=False))
        databases.start_refresh(settings.DEFAULTS)
        time.sleep(0.05)
        databases.start_refresh(settings.DEFAULTS)
        for _ in range(40):
            time.sleep(0.05)
            if not databases._state["loading"] and len(runs) == 2:
                break
    finally:
        databases.refresh_now, databases.directory = real_now, real_dir
    check("databases: a refresh asked for during one runs right after it", len(runs) == 2, runs)
    # This PC: ids by folder and name (a rescan kept every id), cloud-only files not read
    from eq import library
    g1 = library._group([(os.path.join(top, "b", "Bee L.txt"), {"points": 99})])
    g2 = library._group([(os.path.join(top, "a", "Ant L.txt"), {"points": 99}), (os.path.join(top, "b", "Bee L.txt"), {"points": 99})])
    check("This PC: a group keeps its id when others are found before it", g1[0]["id"] == g2[1]["id"], (g1[0]["id"], g2[1]["id"]))
    check("This PC: OneDrive's online-only files are left out (reading one downloads it)",
          library.CLOUD_ONLY & 0x400000 and library.CLOUD_ONLY & 0x1000)
    # the app's downloads folder isn't searched as this PC's (its curves are the online entries: with every database
    # downloaded, 95,000 files went through on each Find… and were listed twice)
    curve = "".join(f"{20 * 1.1 ** i:.2f}\t80\n" for i in range(80))
    other = os.path.join(top, "mine", "Another AutoEQ Studio")  # (an unzipped copy: its downloads aren't yours either)
    for folder, name in ((os.path.join(databases.DOWNLOAD_DIR, "Some site"), "Downloaded One.txt"),
                         (os.path.join(top, "mine"), "My Own.txt"), (os.path.join(other, "downloads", "Site"), "Other Copy.txt"),
                         (os.path.join(other, "app", "eq"), "databases.py")):
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), "w", encoding="utf-8") as fh:
            fh.write(curve)
    library._state["scanning"] = True
    library._scan([top])
    found = {g["name"] for g in library.status(with_items=True)["items"]}
    check("This PC: the downloads folders of this app (and another copy) aren't searched (they're the online entries), "
          "your folders are", "My Own" in found and not {"Downloaded One", "Other Copy"} & found, sorted(found)[:20])
    # Find… opening doesn't search the same folders again right after a search, nor load the lists again right after
    # a load (each opening did both: the window was held up for seconds); asked for (Sources), it does
    cfg_mine = dict(settings.DEFAULTS, library={"folders": [os.path.join(top, "mine")]})
    def scan_ended():
        t0 = time.time()
        while library.status()["scanning"] and time.time() - t0 < 30:
            time.sleep(0.05)
    forced = library.start_scan(cfg_mine, force=True)
    scan_ended()
    again = library.start_scan(cfg_mine)
    scan_ended()
    saved_db = (dict(databases._state), databases._state["items"])
    try:
        databases._state.update(loading=False, updated=time.time(),
                                sites=[{"url": s["url"]} for s in databases.sites_for(settings.DEFAULTS)])
        skipped = databases.start_refresh(settings.DEFAULTS) is False and not databases._state["loading"]
        rows1 = databases.status(with_items=True)["items"]
        rows2 = databases.status(with_items=True)["items"]
    finally:
        databases._state.update(saved_db[0])
    check("Find…: the same folders aren't searched again within a minute (unless asked), nor the lists loaded again "
          "within half an hour; their rows are made once per list", again is False and forced is True and skipped
          and rows1 is rows2, (again, forced, skipped, rows1 is rows2))
    # "Which measurement to use": your own files always in the list; short names match whole words only
    from eq import compare
    many = [{"kind": "measurement", "name": f"Brand HD 600 v{i}", "site": "S", "site_url": "https://s.squig.link/",
             "id": f"x{i}", "tag": "S", "ref": {"file": f"HD 600 v{i}"}} for i in range(50)]
    mine_g = {"kind": "measurement", "name": "HD 600", "folder": os.path.join(top, "Measurements"),
              "files": [os.path.join(top, "Measurements", "HD 600 L.txt")], "id": "mine", "in_app": True}
    real_items, real_lib = databases.items, library.status
    try:
        databases.items = lambda: many
        library.status = lambda with_items=False: {"items": [mine_g]}
        cands = compare.candidates("HD 600")
    finally:
        databases.items, library.status = real_items, real_lib
    check("compare: your own files stay in the list past 40 database matches",
          len(cands) == 40 and cands[-1]["id"] == "mine", (len(cands), cands[-1]["id"]))
    check("compare: a short name matches whole words only (\"S12\" isn't inside \"KZ ZS12\")",
          compare.matches("S12", "Letshuoer S12") and not compare.matches("S12", "KZ ZS12")
          and compare.matches("Blessing 2", "Moondrop Blessing2"))
    # an averaged file's name is made safe like any other (Undo looked for a name add_file changed)
    saved_last = dict(compare._LAST)
    compare._LAST.clear()
    compare._LAST.update({k: {"rig": "711", "vals": curves["meas"][:len(compare.F)] if len(curves["meas"]) >= len(compare.F)
                              else engines.np.zeros(len(compare.F)), "name": k, "source": "S"} for k in ("a", "b")})
    try:
        avg_name = compare.average(["a", "b"], "Bad: name?\t.")[0]
    finally:
        compare._LAST.clear(); compare._LAST.update(saved_last)
    check("compare: an averaged file's name is Windows-safe as add_file keeps it",
          avg_name == textfile.safe_name(avg_name) and avg_name.startswith("Bad_ name__"), avg_name)
    # IEM or headphone: the folder when a file has no record (the hint was " ")
    hp_dir = os.path.join(databases.DOWNLOAD_DIR, databases.folder_name("Earphones Archive headphones (5128)"))
    # (an HMS target: its name says no kind, so the measurement's folder decides; a 711 target means an IEM anyway)
    st_hp = rigconv.status(cfg, os.path.join(top, "Targets", "Neutral HMS target.txt"),
                           [os.path.join(hp_dir, "Some Model L.txt")])
    check("rigs: a file's folder says headphones when there's no record", st_hp.get("device") == "headphone",
          {k: st_hp.get(k) for k in ("state", "meas_rig", "target_rig", "device")})
    # a per-entry rig the app doesn't know isn't used
    saved_map = rigmap._data.get("d")
    rigmap._data["d"] = {"units": {"https://m.squig.link": {"rig": "711", "confidence": "high", "models": 5, "wins": 4,
                                                           "entries": {"Odd": "unknown", "Fine": "5128"}}}}
    try:
        odd_rig = rigmap.lookup({"site_url": "https://m.squig.link/", "name": "Odd"})
        fine_rig = rigmap.lookup({"site_url": "https://m.squig.link/", "name": "Fine"})
    finally:
        rigmap._data["d"] = saved_map
    check("rigs: a per-entry rig the app doesn't know isn't used (it broke the comparison)",
          odd_rig[:2] == (None, False) and fine_rig[:2] == ("5128", True), (odd_rig, fine_rig))
    # targets' rigs: sources.json read once per list, not once per target
    reads, real_sources = [], rigs.sources
    rigs.sources = lambda: (reads.append(1), real_sources())[1]
    try:
        rigs.library_rigs([{"kind": "target", "name": f"T{i}", "files": [f"T{i}.txt"], "folder": top} for i in range(5)])
    finally:
        rigs.sources = real_sources
    check("rigs: the targets' rigs read sources.json once per list", len(reads) == 1, len(reads))
    # previews and comparisons: one V8 per thread, not one per curve
    made, real_racer = [], engines._racer
    engines._racer = lambda: (made.append(1), real_racer())[1]
    engines._kept.__dict__.pop("ctxs", None)
    try:
        prev = [engines.preview_curve(cfg, mts[:2]) for _ in range(3)]
    finally:
        engines._racer = real_racer
    check("previews: one V8 per thread for the same settings", len(made) == 1 and prev[0] == prev[2], len(made))
    # squig.link's list is another site's: only web addresses are kept (they become links and downloads)
    saved_path = databases.DIRECTORY_PATH
    databases.DIRECTORY_PATH = os.path.join(top, "data", "odd squigsites.json")
    textfile.write_json(databases.DIRECTORY_PATH, {"time": time.time(), "items": [ITEM, dict(ITEM, url="javascript:alert(1)"),
                                                                                  dict(ITEM, url="file:///C:/x")]})
    try:
        odd = databases.directory()
    finally:
        databases.DIRECTORY_PATH = saved_path
    check("databases: only web addresses from squig.link's list", odd == [ITEM], odd)
    # "in the app" / "downloaded": the folder itself or inside it, not a folder beside it named the same way
    check("files: inside a folder, not one beside it with a longer name",
          textfile.inside(os.path.join(top, "inputs", "x"), os.path.join(top, "inputs"))
          and not textfile.inside(os.path.join(top, "inputs2", "x"), os.path.join(top, "inputs"))
          and textfile.inside(os.path.join(top, "inputs"), os.path.join(top, "inputs")))
    # a rig conversion without its error figures isn't used (working out its error stopped the app's start)
    saved_rd = rigconv._data.pop("d", None), rigconv.DATA_PATH
    rigconv.DATA_PATH = os.path.join(top, "data", "odd rigdata.json")
    good = {"device": "iem", "from": "5128", "to": "711", "models": 3, "bands": {"1000-3000": [2, 1]}, "conversion": [0, 0],
            "uncertainty": [1, 1], "mismatch": [0, 0]}
    textfile.write_json(rigconv.DATA_PATH, {"grid": [20, 20000], "pairs": [good, dict(good, bands={}, to="43AG")],
                                            "units": [{"unit": "u", "from": "711", "name": "U", "bands": None}]})
    try:
        kept_pairs, units = [p["to"] for p in rigconv.data()["pairs"]], rigconv.page_units()
    finally:
        rigconv._data.pop("d", None)
        rigconv.DATA_PATH = saved_rd[1]
        if saved_rd[0] is not None:
            rigconv._data["d"] = saved_rd[0]
    check("rigs: a conversion without its error figures isn't used (no crash)", kept_pairs == ["711"] and units == {},
          (kept_pairs, units))
    check("databases: squig.link's list is fetched in the background (the window doesn't wait); a failed try isn't "
          "repeated at once", quick < 0.3 and seen and seen[0] != threading.get_ident() and len(tries) == 1
          and lists[0] == [ITEM], (quick, seen, tries))


# ---------------------------------------------------------------- 2. requests (eq.service, as the window calls it)
def api_checks(top):
    use_copy(top)
    os.chdir(os.path.join(top, "app", "eq"))
    from eq import service

    def call(path, body=None, raw=None, headers=None):
        """A request as AutoEQ Local's page made it (its body through JSON, as sent), answered by eq.service: (status,
        answer) as its server gave them (an error: 400; an address it doesn't have: 404)."""
        if raw is not None:
            try:
                body = json.loads(raw)
            except ValueError:
                return 400, {"error": "The request wasn't valid JSON."}
        with contextlib.redirect_stderr(io.StringIO()):  # (an error's details: the log's, as the server's were)
            r = json.loads(json.dumps(service.call(path, json.loads(json.dumps(body or {})))))
        if "error" in r:
            return (404 if r["error"].startswith("unknown") else 400), r
        return 200, r

    def run(mode, cfg, retry=None):
        code, r = call("/api/run", {"mode": mode, "settings": cfg, **({"retry": retry} if retry else {})})
        for _ in range(1500):
            j = call("/api/job")[1]
            if j.get("status") != "running":
                call("/api/job", {"ack": True})
                return j
            time.sleep(0.2)
        return {"status": "timeout"}

    if True:
        code, st = call("/api/state")
        check("requests: starts, state", code == 200 and st["inputs"]["active_target"] and st["inputs"]["measurements"], st.get("error"))
        S = st["settings"]
        S["performance"]["cores"] = 2
        code, c = call("/api/curves", {"settings": S})
        check("requests: curves with the error without EQ", code == 200 and c["no_eq_rms"] > 0, c.get("error"))
        code, an = call("/api/analysis", {"settings": S})
        check("requests: the automatic settings' analysis", code == 200 and an.get("band_top"), an)
        code, a = call("/api/auto", {"settings": S, "analysis": an})
        check("requests: automatic settings with a time estimate", code == 200 and a["values"] and a["seconds"] > 0, a)

        S["auto"]["enabled"] = False
        S["site_sweep"].update(filter_rows=[4, 6], freq_high=[10000], gain_ranges=[[-12, 6]], q_max=[2])
        S["best_fit"].update(filter_counts=[3, 5], q_max=[2], gain_max=[6], random_starts=2, seed_with_site=True)
        for mode in ("site_sweep", "best_fit"):
            j = run(mode, S)
            res = j.get("result") or {}
            check(f"requests: {mode} run", j.get("status") == "done" and res.get("results") and res["results"][res["pick"]]["filters"], j.get("message"))
        check("requests: a run's result names the IEM, target and files it was made for (the page may show another by then)",
              res.get("device") == c.get("name") and res.get("target_name") == c.get("target_name") and res.get("meas_files")
              and res.get("target_file"), {k: res.get(k) for k in ("device", "target_name", "meas_files", "target_file")})
        # Retry from these filters: Best fit from the result card's filters, this run only (the settings stay)
        mine = [{"type": "PK", "freq": 150, "gain": 3, "q": 1}, {"type": "PK", "freq": 3000, "gain": -2, "q": 2},
                {"type": "PK", "freq": 8000, "gain": 1, "q": 1, "enabled": False}]
        j = run("best_fit", S, {"filters": mine, "add": False})
        res = j.get("result") or {}
        rs = res.get("results") or [{}]
        check("requests: retry, fine-tune: only your (switched-on) filters, fitted again; settings kept",
              j.get("status") == "done" and all(r.get("rows") == 0 and r.get("yours") == 2 and r.get("n_filters", 9) <= 2 for r in rs)
              and call("/api/state")[1]["settings"]["best_fit"]["start_filters"] == "", (j.get("message"), rs[:1]))
        j = run("best_fit", S, {"filters": mine[:2], "add": True})
        res = j.get("result") or {}
        pick = (res.get("results") or [{}])[res.get("pick", 0)] if res.get("results") else {}
        check("requests: retry, add: your filters kept exactly, filters added",
              j.get("status") == "done" and [(f["freq"], f["gain"], f["q"]) for f in pick.get("filters", [])[:2]] == [(150, 3, 1), (3000, -2, 2)]
              and pick.get("n_filters", 0) > 2, (j.get("message"), pick.get("filters")))
        code, r = call("/api/run", {"mode": "best_fit", "settings": S, "retry": {"filters": [dict(mine[2])], "add": False}})
        check("requests: retry with no filters switched on is refused with a message", code == 400 and "no filters" in r.get("error", ""), r)
        big = json.loads(json.dumps(S))
        big["best_fit"].update(filter_counts=list(range(8, 17)), q_max=[2, 3, 5], random_starts=12, seed_with_site=False)
        call("/api/run", {"mode": "best_fit", "settings": big})
        check("requests: a second run at once is refused", call("/api/run", {"mode": "best_fit", "settings": big})[0] == 400)
        time.sleep(1)
        call("/api/cancel")
        t0 = time.time()
        j = {}
        for _ in range(100):
            j = call("/api/job")[1]
            if j.get("status") != "running":
                call("/api/job", {"ack": True})
                break
            time.sleep(0.2)
        check("requests: Cancel stops a run at once", j.get("status") == "cancelled" and time.time() - t0 < 10, j)

        F = [{"type": "PK", "freq": 1000, "gain": -2, "q": 1}, {"type": "PK", "freq": 3000, "gain": 3, "q": 2}]
        formats = ("apo", "graphic", "poweramp", "uapp", "soundsource", "voicemeeter", "rockbox", "convolution")  # (exports.FORMATS)
        S["export"].update({k: True for k in formats})
        code, r = call("/api/export", {"settings": S, "filters": F, "preamp": -3, "name": "Selftest - best fit 2f"})
        check("requests: filter files saved in every format", code == 200 and sorted(r.get("written", {})) == sorted(formats)
              and all(os.path.isfile(p) for p in r["written"].values()), r)
        # your own File name: the files are named after it; saving again under it asks first (nothing replaced)
        code, r = call("/api/export", {"settings": S, "filters": F, "preamp": -3, "name": "My: EQ?", "formats": ["apo", "poweramp"]})
        mine = sorted(os.path.basename(p) for p in r.get("written", {}).values())
        code2, r2 = call("/api/export", {"settings": S, "filters": F[:1], "preamp": -3, "name": "My: EQ?", "formats": ["apo", "poweramp"]})
        kept = open(os.path.join(os.path.dirname(r["written"]["apo"]), "My_ EQ_ - filters.txt"), encoding="utf-8").read() if mine else ""
        code3, r3 = call("/api/export", {"settings": S, "filters": F[:1], "preamp": -3, "name": "My: EQ?", "formats": ["apo"], "replace": True})
        check("requests: your own file name names the files (made safe); an existing file is only replaced when you say so",
              mine == ["My_ EQ_ - Poweramp.json", "My_ EQ_ - filters.txt"] and sorted(r2.get("exists", [])) == mine
              and "written" not in r2 and "3000" in kept and code3 == 200 and "written" in r3, (r, r2, r3))
        code, r = call("/api/report", {"settings": S, "cards": [{"title": "A", "filters": F}], "open": False})
        check("requests: report saved", code == 200 and os.path.isfile(r.get("path", "")), r)
        code, r = call("/api/report", {"settings": S, "cards": [{"title": "A", "filters": F}], "open": False, "name": "My EQ"})
        check("requests: report under your own file name", code == 200 and os.path.basename(r.get("path", "")) == "My EQ - report.html", r)
        code, r = call("/api/report", {"settings": S, "cards": [{"title": "A", "text": "Mine <i>x</i> & y", "filters": F}],
                                       "open": False, "name": "Escaped"})
        with open(r.get("path", os.devnull), encoding="utf-8") as fh:
            rep = fh.read()
        check("requests: a card's words are text in the report (its own markup kept)", code == 200
              and "Mine &lt;i&gt;x&lt;/i&gt; &amp; y" in rep and "RMS error <b>" in rep, r)
        # (19.9-20 kHz: within the limits and in order, but between the grid's points at 19,897 and 20,186 Hz)
        code, r = call("/api/report", {"settings": dict(S, scoring=dict(S["scoring"], band_hz=[19900, 20000])),
                                       "cards": [{"title": "A", "filters": F}], "open": False, "name": "Empty band"})
        check("requests: a report with no curve points in the scored range says so (was \"nan dB\")",
              code == 400 and "has no data" in r.get("error", ""), r)
        # a report of that name already there: only replaced when you say so (it was replaced silently)
        body = {"settings": S, "cards": [{"title": "A", "filters": F}], "open": False, "name": "My EQ"}
        code, r = call("/api/report", body)
        code2, r2 = call("/api/report", {**body, "replace": True})
        check("requests: an existing report is only replaced when you say so",
              code == 200 and r.get("exists") == ["My EQ - report.html"] and "path" not in r and code2 == 200 and r2.get("path"), (r, r2))
        # (review 2) the files the EQ was made for, sent with it: the report is of them, not of the measurement chosen now
        flat = "".join(f"{20 * 1.1 ** i:.2f} {70 + i % 3}\n" for i in range(80))
        call("/api/files/add", {"kind": "measurement", "files": [{"name": "Report other L.txt", "content": flat},
                                                                 {"name": "Report other R.txt", "content": flat}],
                                "settings": S})
        tgt = S["files"]["active_target"] or call("/api/state")[1]["inputs"]["active_target"]
        code, r = call("/api/report", {"settings": S, "cards": [{"title": "A", "filters": F}], "open": False,
                                       "meas_files": ["Report other L.txt", "Report other R.txt"], "target_file": tgt})
        check("requests: a report for an EQ made for other files is of those files (named as the EQ files are)",
              code == 200 and os.path.basename(r.get("path", "")).startswith("Report other"), r)
        call("/api/files/remove", {"kind": "measurement", "names": ["Report other L.txt", "Report other R.txt"],
                                   "settings": S})
        code, r = call("/api/listen/save", {"device": "Selftest IEM", "eqs": [{"name": "A", "filters": F}]})
        code2, r2 = call("/api/listen", {"device": "Selftest IEM"})
        check("requests: EQs to compare kept for an IEM and read back", code == 200 and code2 == 200
              and [e["name"] for e in r2.get("eqs", [])] == ["A"] and r2.get("max") == 12, (r, r2))
        call("/api/listen/save", {"device": "Selftest IEM", "eqs": []})
        code, r = call("/api/text", {"settings": S, "filters": F, "preamp": -3})
        check("requests: filters as text", code == 200 and r["apo"].startswith("Preamp: -3.0 dB"), r)

        call("/api/presets/save", {"name": "Selftest", "settings": S})
        code, r = call("/api/presets/load", {"name": "Selftest"})
        check("requests: preset saved and loaded (the files stay)", code == 200 and r["settings"]["files"] == S["files"], r)
        call("/api/presets/delete", {"name": "Selftest"})
        curve = "Frequency;dB\n" + "".join(f"{20 * 1.1 ** i:.2f};{80 + i % 5},5\n".replace(".", ",", 1) for i in range(80))
        code, r = call("/api/files/add", {"kind": "auto", "name": "Selftest target.txt", "content": curve, "settings": S})
        check("requests: a dropped target (decimal commas) is added and used", code == 200 and r.get("kind") == "target"
              and r["inputs"]["active_target"] == "Selftest target.txt", r)
        code, r = call("/api/files/move", {"kind": "target", "name": "Selftest target.txt", "settings": r.get("settings", S)})
        check("requests: moved to the measurements", code == 200 and any(m["name"] == "Selftest target.txt" for m in r["inputs"]["measurements"]), r)
        call("/api/files/remove", {"kind": "measurement", "names": ["Selftest target.txt"], "settings": S})
        # (review 2) a traced device's channels added as one set: L unchanged and R changed stay one device's names
        lr = lambda r_db: [{"name": "Selftest set L.txt", "content": curve}, {"name": "Selftest set R.txt",
                                                                             "content": curve.replace(";8", f";{r_db}")}]
        call("/api/files/add", {"kind": "measurement", "files": lr(7), "settings": S})
        code, r = call("/api/files/add", {"kind": "measurement", "files": lr(6), "settings": S})
        check("requests: several files added as one set get one number when a name is taken (one device)",
              code == 200 and r.get("names") == ["Selftest set (2) L.txt", "Selftest set (2) R.txt"], r.get("names") or r)
        call("/api/files/remove", {"kind": "measurement", "settings": S, "names": [
            "Selftest set L.txt", "Selftest set R.txt", "Selftest set (2) L.txt", "Selftest set (2) R.txt"]})

        check("requests: unknown address", call("/api/nope")[0] == 404)
        from eq import service as _svc
        check("requests: a body that isn't a dict is read as empty (a missing field is named)",
              _svc.call("/api/files/move", ["not", "a", "dict"]).get("error") == "The request doesn't say target or "
              "measurement.")
        check("requests: missing field named", call("/api/files/move", {"settings": S})[1].get("error")
              == "The request doesn't say target or measurement.")
        wrong = [call(p, {"kind": "measurement", "name": 5, "names": 4, "content": 9})[1].get("error", "")
                 for p in ("/api/files/add", "/api/files/remove", "/api/files/move", "/api/presets/load", "/api/listen")]
        check("requests: wrong kinds of values get plain messages", all(e.startswith("Missing") for e in wrong), wrong)
        check("requests: opens nothing outside its folder", call("/api/open", {"path": "C:\\Windows"})[0] == 400)
        # only the app's folders by name, and only its own page (opening any file would also start programs)
        inside = os.path.join(top, "app", "start.py")
        check("requests: opens no file by path (a program could start)", call("/api/open", {"path": inside})[0] == 400)
        check("requests: opens nothing when no folder is named", [call("/api/open", b)[0] for b in ({}, {"what": {"a": 1}}, {"path": ""})]
              == [400, 400, 400])


# ---------------------------------------------------------------- 3. AutoEQ Studio's own (not from AutoEQ Local)
def studio_checks(top):
    use_copy(top)
    from eq import bring_over, paths
    check("studio: the EQ part's files are in AutoEQ Studio's folders (data\\eq\\; your Targets, Measurements, Saved "
          "EQs, Presets), its data next to it",
          paths.DATA == os.path.join(top, "data", "eq") and paths.TARGET_DIR == os.path.join(top, "Targets")
          and paths.MEAS_DIR == os.path.join(top, "Measurements") and paths.OUTPUT_DIR == os.path.join(top, "Saved EQs")
          and paths.PRESET_DIR == os.path.join(top, "Presets")
          and paths.SOURCES_PATH == os.path.join(top, "data", "eq", "sources.json")
          and os.path.isfile(os.path.join(paths.APP, "rigdata.json"))
          and os.path.isfile(os.path.join(paths.APP, "vendor", "squiglink", "equalizer.js")), (paths.DATA, paths.APP))
    # a fake AutoEQ Local beside it, with what it keeps
    src = os.path.join(os.path.dirname(top), "AutoEQ Local")
    files = {r"data\settings.json": '{"mode": "best_fit"}', r"data\history.json": "[]", r"data\listen.json": "{}",
             r"data\app.log": "log", r"data\cache\databases.json": '{"local": 1}', r"data\cache\timing.json": "{}",
             r"data\cache\rig-build\x.json": "{}", r"inputs\target\T.csv": "20 0", r"output\My EQ - filters.txt": "x",
             r"presets\P.json": "{}", r"downloads\site\M L.txt": "20 0"}
    for rel, text in files.items():
        os.makedirs(os.path.dirname(os.path.join(src, rel)), exist_ok=True)
        with open(os.path.join(src, rel), "w") as fh:
            fh.write(text)
    with open(os.path.join(paths.CACHE, "databases.json"), "w") as fh:
        fh.write('{"studio": 1}')
    os.makedirs(paths.DATA, exist_ok=True)
    with open(paths.SETTINGS_PATH, "w") as fh:
        fh.write("{}")
    check("studio: AutoEQ Local is found beside it; nothing brought while it has its own settings",
          bring_over.default_source() == src and not bring_over.needed() and bring_over.bring_over() == [])
    for p in (paths.SETTINGS_PATH, os.path.join(paths.DATA, "history.json"), os.path.join(paths.DATA, "listen.json"),
              os.path.join(paths.CACHE, "timing.json")):  # (the earlier checks' own: as on a first use)
        if os.path.exists(p):
            os.remove(p)
    done = [os.path.relpath(p, top) for p in bring_over.bring_over()]
    with open(os.path.join(paths.CACHE, "databases.json")) as fh:
        kept = fh.read()
    check("studio: AutoEQ Local's files are copied in (settings last), its logs and the rig builds' cache aren't, and "
          "a file already here is kept", sorted(done) == sorted([
              r"data\eq\cache\timing.json", r"Targets\T.csv", r"Saved EQs\My EQ - filters.txt", r"Presets\P.json",
              r"downloads\site\M L.txt", r"data\eq\history.json", r"data\eq\listen.json", r"data\eq\settings.json"])
          and done[-1].endswith("settings.json") and kept == '{"studio": 1}'
          and os.path.isfile(os.path.join(src, r"data\settings.json")), done)
    check("studio: brought once", bring_over.bring_over() == [] and not bring_over.needed())
    # offline: nothing goes to the internet (the one place the EQ part downloads asks first)
    import net
    from eq import databases, service
    net.set_offline(True)
    try:
        try:
            databases._get("https://127.0.0.1:9/never")
            said = ""
        except net.Offline as e:
            said = str(e)
        with contextlib.redirect_stderr(io.StringIO()):  # (an unknown entry: its error's details go to the log)
            r = service.call("/api/db/download", {"id": "x", "settings": {}})
    finally:
        net.set_offline(False)
    check("studio: offline, nothing is fetched from the internet (said plainly, before any connection)",
          "offline" in said and "Online" in said and isinstance(r, dict), (said, r))


def watch_strays(qapp):
    """Every control (a button, a label, a box, a bare widget or frame) shown as a window of its own while the checks
    run: made visible before it had a parent, it flashes on the screen (off-screen nothing shows, so only this sees
    it). Windows by design (dialogs, the main window, menus, pop-up lists, tooltips) aren't counted."""
    from PySide6.QtCore import QEvent, QObject, Qt
    from PySide6.QtWidgets import (QAbstractButton, QAbstractSlider, QAbstractSpinBox, QComboBox, QFrame, QLabel,
                                   QLineEdit, QProgressBar, QWidget)
    found = []

    class Watch(QObject):
        def eventFilter(self, obj, e):
            if e.type() == QEvent.Show and isinstance(obj, QWidget) and obj.isWindow()                     and not obj.windowFlags() & (Qt.Popup | Qt.ToolTip) & ~Qt.Window                     and (isinstance(obj, (QAbstractButton, QLabel, QLineEdit, QComboBox, QAbstractSlider,
                                          QAbstractSpinBox, QProgressBar)) or type(obj) in (QWidget, QFrame)):
                found.append(f"{type(obj).__name__} {getattr(obj, 'text', lambda: '')()!r}"[:60])
            return False
    qapp._stray_watch = Watch()
    qapp.installEventFilter(qapp._stray_watch)
    return found


def ui_checks(top):
    """The EQ screen (ui\\eq_page.py), drawn off-screen on the copy: its files, a run, the result, Save, Use on device
    (a fake APO folder)."""
    use_copy(top)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # (off-screen Qt has no font list of its own: Windows' fonts, so text is drawn as text, e.g. the tracer's sample)
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFrame, QMessageBox, QPushButton, QSlider
    qapp = QApplication.instance() or QApplication([])
    strays = watch_strays(qapp)
    # (no message box may wait for a click that never comes: each is answered here, said in the output, and kept in
    # BOXES for the checks; Yes to a question. A check that expects one patches it itself)
    for kind in ("information", "warning", "critical"):
        setattr(QMessageBox, kind, staticmethod(lambda *a, kind=kind, **k: (BOXES.append(a[2]), print(f"({kind}: {a[2]})"))[0]))
    QMessageBox.question = staticmethod(lambda *a, **k: (BOXES.append(a[2]), print(f"(question: {a[2]})"),
                                                         QMessageBox.Yes)[2])
    from switcher import core, devices as D
    from switcher.apo import Apo
    from ui import theme
    from ui.eq_page import EqPage, file_base_name
    theme.apply(qapp, dark=False)
    conf = os.path.join(top, "apo", "config")
    os.makedirs(conf)
    with open(os.path.join(conf, "config.txt"), "w") as fh:
        fh.write("Include: AutoEQ Studio\\switcher.txt\n")
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)]
    sw = core.Switcher(os.path.join(top, "data", "switcher.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    said = []
    page = EqPage(sw, lambda text, ms=0: said.append(text))
    page.resize(1000, 900)
    page.show()
    import net
    net.set_offline(True)  # (opening, the EQ part loads the database lists: never fetched in a check)
    page.start()

    def wait_for(cond, sec=90):
        t = time.time()
        while time.time() - t < sec and not cond():
            qapp.processEvents()
            time.sleep(0.02)
        return cond()
    loaded = wait_for(lambda: page.curves is not None and page.auto is not None)
    check("ui: the EQ screen opens with the app's files and draws them (the curves, the automatic settings)",
          loaded and page.target_combo.count() >= 1 and page.measurement_combo.count() >= 1
          and "→" in page.graph_title.text(), (loaded, page.graph_note.text()))
    page.choose_app("poweramp")
    check("ui: your EQ app sets the method and Save writes exactly its file",
          page.S["eq_app"] == "poweramp" and page.S["mode"] == "best_fit"
          and [k for k in ("apo", "poweramp", "graphic") if page.S["export"][k]] == ["poweramp"]
          and "Poweramp" in page.formats_line.text(), page.S["export"])
    # Find…: the app's files, this PC (here: the sample curves) and the online lists, offline (nothing downloaded)
    import net
    net.set_offline(True)
    page.S["library"]["folders"] = [os.path.join(top, "samples")]
    from ui.picker import Picker
    pk = Picker(page, "measurement")
    pk.show()
    loaded = wait_for(lambda: not pk.db.get("loading") and not pk.lib.get("scanning"), 120)
    pk.q.setText("gate")
    pk.render()
    pk.finish_list()
    rows = [pk.list.item(i).data(Qt.UserRole) for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole)]
    srcs = {r["src"] for r in rows}
    check("ui: Find… searches the app's files, this PC and the online lists (offline: the saved ones)",
          loaded and "app" in srcs and "pc" in srcs and ("db" in srcs or not pk.db.get("items")), (loaded, srcs, pk.status.text()))
    # a long list: the first rows at once, the rest a batch at a time (each row is ~2 ms of widgets: a key waited)
    saved_db, saved_src = pk.db, pk.src
    pk.db = {"items": [[f"fake{i}", "m", f"Fakeone {i}", "Sub", "Site", None, "", ""] for i in range(200)], "loading": False}
    pk.src = "db"
    pk.q.setText("fakeone")
    pk.render()
    first = sum(1 for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole))
    wait_for(lambda: not pk._pending, 10)
    every = sum(1 for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole))
    # (review 2) drawn again with the same search (Show, a file ticked, a list loaded): the place in the list stays
    pk.resize(700, 500)
    QApplication.processEvents()
    bar = pk.list.verticalScrollBar()
    bar.setValue(bar.maximum() // 2)
    pk.list.setCurrentRow(120)
    was = bar.value()
    pk.render()
    QApplication.processEvents()
    check("ui: Find… drawn again with the same search keeps its place in the list and the selected row",
          was > 0 and abs(bar.value() - was) <= 2 and pk.list.currentRow() == 120, (was, bar.value(), pk.list.currentRow()))
    pk.q.setText("fakeone 19")
    pk.render()
    pk.finish_list()
    narrowed = [pk.list.item(i).data(Qt.UserRole)["name"] for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole)]
    pk.db, pk.src = saved_db, saved_src
    pk.q.setText("gate")
    pk.render()
    pk.finish_list()
    check("ui: Find…'s long list makes its first rows at once and the rest after (typing doesn't wait for 120 rows)",
          first <= 30 and every == 200 and sorted(narrowed) == sorted(f"Fakeone {i}" for i in range(200) if "19" in str(i)),
          (first, every, narrowed[:12]))
    # while nothing changes, Find… asks for the counts only (the whole lists, 55,000 rows, were built every 0.5 s)
    asked = []

    class _Counting:
        def call(self, route, body=None):
            asked.append((route, bool((body or {}).get("items"))))
            return page.svc.call(route, body)
    drawn = []
    pk._later.stop()  # (the search typed above: its own drawing, not the poll's)
    pk.svc, real_render = _Counting(), pk.render
    pk.render = lambda: drawn.append(1)
    pk._load()
    wait_for(lambda: not pk._fetching, 10)
    pk.svc, pk.render = page.svc, real_render
    check("ui: Find… asks only for the lists' counts while they haven't changed, and doesn't draw its list again",
          asked and not any(items for _r, items in asked) and not drawn, (asked, len(drawn)))
    pk.set_filter("rig", "5128")
    kept = [pk.list.item(i).data(Qt.UserRole) for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole)]
    check("ui: Find…'s rig filter leaves only that rig, and its list counts them",
          kept and all(pk.rig_of(r) == "5128" for r in kept) and "5128" in pk.f_rig.currentText(), [r["rig"] for r in kept][:5])
    pk.clear_filters()
    app_row = next(r for r in rows if r["src"] == "app")
    pk.preview(app_row)
    wait_for(lambda: page.previews, 30)
    check("ui: Find…'s Show draws the curve on the graph without using it", [p[0] for p in page.previews] == [app_row["key"]],
          page.previews)
    page.remove_preview(app_row["key"])
    db_row = next((r for r in pk.db_rows([]) if not r.get("link") and r["src"] == "db"), None)
    if not db_row:
        print("skip ui: offline, an online entry never downloaded (no database lists on this PC to try it with)")
    if db_row:
        said = []
        real_warning = QMessageBox.warning
        QMessageBox.warning = staticmethod(lambda *a, **k: said.append(a[2]))
        try:
            pk.choose(db_row)
            wait_for(lambda: said or pk.busy is None and not pk.isVisible(), 60)
            wait_for(lambda: said, 30)
        finally:
            QMessageBox.warning = real_warning
        check("ui: offline, an online entry never downloaded says it needs the internet (nothing fetched)",
              said and "offline" in said[0] and "Online" in said[0], said)
    pc_row = next(r for r in pk.pc_rows(["gate"]))
    pk.choose(pc_row)
    used = wait_for(lambda: not pk.isVisible() and page.curves is not None, 60)
    check("ui: Find…'s Use puts a file from this PC into the app and in use", used and any(
          f["included"] for f in page.groups.get(page.measurement_combo.currentData(), [])), page.measurement_combo.currentText())
    # Which measurement to use? (offline: what's on this PC and in the app)
    from ui.compare_window import CompareWindow
    cw = CompareWindow(page)
    cw.show()
    cw.q.setText("gate")
    cw.run()
    compared = wait_for(lambda: cw.data is not None and not cw.busy, 240)
    items = (cw.data or {}).get("items") or []
    check("ui: Which measurement to use ranks the model's measurements for the target (each with its score and reasons)",
          compared and items and all("score" in c and c.get("reasons") is not None for c in items)
          and items == sorted(items, key=lambda c: -c["score"]), (compared, cw.status.text()))
    uses = [b for b in cw.scroll.widget().findChildren(QPushButton) if b.text() == "Use"]
    if uses:
        uses[0].click()
        wait_for(lambda: not cw.isVisible(), 60)
    check("ui: Which measurement's Use puts the top one in use", uses and not cw.isVisible() and page.curves is not None,
          len(uses))
    net.set_offline(False)
    page.choose_app("apo")
    # the settings folds: a value of your own, a wrong one, one past a limit, handing back, side effects
    st = page.settings
    st.auto_switched(True)  # (the request checks before left them off in the copy)
    page.refresh_auto()
    f = st.form.fields["best_fit.filter_counts"]
    f.box.setText("4-8")
    f._typed()
    yours = (page.S["best_fit"]["filter_counts"], "best_fit.filter_counts" in page.S["auto"]["manual"], f.tag.text())
    f.box.setText("4-x")
    f._typed()
    wrong = (f.box.property("bad"), page.S["best_fit"]["filter_counts"])
    check("ui: settings: a value of your own is used and marked yours; a wrong one is red and not used",
          yours == ([4, 5, 6, 7, 8], True, "yours ↺") and wrong == (True, [4, 5, 6, 7, 8]), (yours, wrong))
    b = st.form.fields["scoring.band_hz.0"]
    b.box.setText("5")
    b._typed()
    b._left()
    hi = st.form.fields["scoring.band_hz.1"]
    hi.box.setText("10")
    hi._typed()
    check("ui: settings: past a limit it moves to the limit on leaving (said); a “to” below its “from” is red",
          page.S["scoring"]["band_hz"][0] == 20 and any("Changed to 20" in s for s in said) and hi.box.property("bad"),
          (page.S["scoring"]["band_hz"], said[-1:]))
    hi.show_value(page.S["scoring"]["band_hz"][1])
    st.hand_back("best_fit.filter_counts")
    check("ui: settings: handing a value back gives it to the automatic settings again (auto tag)",
          "best_fit.filter_counts" not in page.S["auto"]["manual"] and f.tag.text() == "auto", page.S["auto"]["manual"])
    st.changed("site.profile", "squig.link lab")
    sq = dict(page.S["site"])
    st.changed("site.smooth_level", sq["smooth_level"] + 1)
    check("ui: settings: a website's profile sets its values (a change makes it custom)",
          sq["profile"] == "squig.link lab" and sq["smooth_level"] == page.meta["profiles"]["squig.link lab"]["smooth_level"]
          and page.S["site"]["profile"] == "custom", (sq, page.S["site"]["profile"]))
    st.auto_switched(False)
    check("ui: settings: with automatic settings off, no tags and nothing in Why these values",
          not f.tag.isVisible() and "off" in st.why.text().lower(), st.why.text())
    page.S["auto"]["enabled"] = False
    page.S["best_fit"].update(filter_counts=[3, 5], random_starts=0, gain_max=[6], q_max=[2], seed_with_site=False)
    page.run_btn.click()  # (the button itself: it passed Qt's checked=False on as a retry and crashed, run() didn't)
    done = wait_for(lambda: page.run_result is not None, 180)
    run, r = page.current()
    check("ui: the Run button makes a result: its numbers, its filters, the best for each count",
          done and r and page.editor.table.rowCount() == len(r["filters"]) and page.count_combo.count() >= 1
          and page.result_box.isVisible() and "dB" in page.chips["error"].text(), page.progress_text.text())
    # editing the filters: the numbers, the title and the file name follow; Revert; Sort isn't an edit; Retry
    before = (page.chips["error"].text(), page.name_edit.text())
    box = page.editor.table.cellWidget(0, 4)
    box.setText(str(page.EDIT[0]["gain"] + 3))
    box.textEdited.emit(box.text())
    after = (page.chips["error"].text(), page.res_title.text(), page.name_edit.text(), page.pick_lab.text())
    check("ui: editing a filter: the error, the title (edited), the file name (… edited) and the line on how it sounds "
          "follow at once",
          after[0] != before[0] and after[1].endswith("edited") and after[2] == before[1] + " edited"
          and (after[3].startswith("As edited: sounds within") or not run.get("pick_case")), (before, after))
    box.setText("99999")
    box.textEdited.emit(box.text())
    check("ui: editing: a value past the edit limits is red and not used", box.property("bad") is True
          and page.EDIT[0]["gain"] != 99999)
    page.revert()
    page.sort_filters()
    check("ui: Revert gives the run's filters back; Sort alone isn't an edit",
          page.chips["error"].text() == before[0] and not page.edited() and page.name_edit.text() == before[1],
          page.chips["error"].text())
    page.add_filter()
    n = len(page.active())
    page.set_view("sliders")
    sl = page.editor.sliders_scroll.widget().findChildren(QSlider)
    sl[-1].setValue(25)
    check("ui: the sliders edit the same filters (a new one at 1 kHz, its gain dragged to +2.5 dB)",
          n == len(r["filters"]) + 1 and page.EDIT[-1]["freq"] == 1000 and page.EDIT[-1]["gain"] == 2.5, page.EDIT[-1])
    page.set_view("table")
    page.revert()
    page.run(retry={"filters": page.active(), "add": False})
    retried = wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not run, 180)
    check("ui: Retry from these filters: Best fit again from them (fine-tune)",
          retried and page.current()[1] is not None and page.run_result["mode"] == "best_fit", page.progress_text.text())
    run, r = page.current()
    check("ui: the result's file name is AutoEQ Local's (<IEM> to <target> - <method> <n>f)",
          page.name_edit.text() == file_base_name(run["device"], run["target_name"], "", run["mode"], r["n_filters"])
          and file_base_name("A", "B", "Poweramp / Poweramp Equalizer", "best_fit", 5) == "A to B - Poweramp, Poweramp Equalizer 5f",
          page.name_edit.text())
    page.name_edit.setText("UI check")
    page.save()
    check("ui: Save filters writes the file under the File name", os.path.isfile(os.path.join(top, "Saved EQs", "UI check - filters.txt"))
          and any("Saved" in s for s in said), said[-1:])
    # History: a saved EQ is kept (once, also when copied), Show brings it back, ✕ removes it
    kept = [e for e in page.history if e.get("saved")]
    page.copy_filters(page.active(), page.stats()["preamp_raw"])
    check("ui: History keeps a saved EQ (copying the same one again doesn't add another)",
          len(kept) == 1 and len([e for e in page.history if e.get("saved")]) == 1
          and kept[0]["device"] == run["device"] and kept[0]["filters"], [e.get("label") for e in page.history])
    page.bring_back(kept[0])
    shown = page.current()
    check("ui: History's Show brings the EQ back as a result of its own (its filters, “From History”)",
          shown[0].get("history") == kept[0]["base"] and len(page.EDIT) == len(kept[0]["filters"])
          and page.res_sub.text().startswith("From History"), page.res_sub.text())
    from ui.history_window import HistoryWindow
    hw = HistoryWindow(page, True)
    rows = len(hw.scroll.widget().findChildren(QFrame))
    hw.remove([kept[0]["key"]])
    check("ui: the History window lists the EQs (this IEM only) and ✕ removes one", rows >= 1 and not any(
          e["key"] == kept[0]["key"] for e in page.history), rows)
    hw.close()
    # (review 2) a long History: the first rows at once, the rest in batches; a typed search waits a moment
    from ui import history_window as hwm
    real_history = page.history
    base = dict(real_history[0]) if real_history else {"device": "X", "target": "Y", "mode": "best_fit", "filters": [],
                                                         "n_filters": 0, "when": time.time()}
    page.history = [dict(base, key=f"many{i}", when=base.get("when", time.time()) - i * 60) for i in range(300)]
    rows_in = lambda w: sum(1 for x in w.scroll.widget().findChildren(QFrame) if type(x) is QFrame)  # (rows only)
    try:
        hw = HistoryWindow(page, False)
        first = rows_in(hw)
        wait_for(lambda: not hw._todo, 20)
        every = rows_in(hw)
        hw.q.setText("no such words at all")
        at_once = rows_in(hw)
        wait_for(lambda: rows_in(hw) == 0, 5)
        after = rows_in(hw)
        hw.close()
    finally:
        page.history = real_history
    check("ui: a long History draws its first rows at once and the rest after; a typed search waits a moment",
          first <= hwm.FIRST_ROWS < every == 300 and at_once == 300 and after == 0, (first, every, at_once, after))
    page.name_edit.setText("UI check")  # (Show named the EQ it brought back)
    page.name_edit.setProperty("auto", False)
    page.use_on("Headset|EarPods")
    rec = sw.record("Headset|EarPods")
    with open(os.path.join(conf, "AutoEQ Studio", "switcher.txt")) as fh:
        sw_text = fh.read()
    check("ui: Use on device makes the result the device's profile, switched on, in APO's file",
          rec["active"] and sw.profile_name(rec["active"]) == "UI check" and "Include: profiles\\UI check.txt" in sw_text
          and "is now on for Headset (EarPods)" in said[-1], (rec, said[-1:]))
    listen_checks(page, sw, said, kept[0], qapp)
    trace_checks(page, wait_for)
    guide_checks(page, wait_for)
    rest_checks(page, wait_for, qapp)
    in_use_checks()
    try_checks(page)
    a11y_checks(page, wait_for)
    queue_checks(page, wait_for)
    compare_results_checks(page)
    order_checks(page, wait_for)
    search_checks(page, wait_for)
    pick_note_checks(page)
    adjust_checks(page, wait_for)
    preset_checks(page, wait_for)
    target_save_checks(page, wait_for)
    review_checks(page, sw, kept[0], wait_for, qapp)
    from collections import Counter
    check("ui: no control is ever shown as a window of its own (each flashed on the screen: Find…'s rows showed one "
          "Show button each while the lists loaded, 779 in a session, and each cost the window's time)",
          not strays, Counter(strays).most_common(5))
    page.close()


def review_checks(page, sw, entry, wait_for, qapp):
    """The code review's fixes (2026-10-07, of the review of 2026-10-06), each checked as it shows."""
    import numpy as np
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtTest import QTest
    from eq import databases
    from ui import audio, guide, trace_core
    # #4: the database lists load when the EQ part opens (a target's rig can come from them)
    lists = os.path.exists(os.path.join(os.environ["AUTOEQSTUDIO_DATA"], "eq", "cache", "databases.json"))
    # (a refresh an earlier check started, e.g. by opening Find…, may still be going: it was the flaky part)
    wait_for(lambda: not databases.status()["loading"], 60)
    st = databases.status()
    check("review: the online database lists are loaded when Make an EQ opens (offline: the saved ones)",
          not st["loading"] and (st["count"] > 0 or not lists), (st["loading"], st["count"], lists))
    # #2: an axis with ten lines before its first decade line
    try:
        vals = trace_core.freq_values([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 400, 410, 420])
        crash = ""
    except Exception as e:  # noqa: BLE001
        vals, crash = None, repr(e)
    check("review: the tracer reads an axis with ten gridlines before its first decade line (it crashed)",
          not crash and vals is not None, crash)
    # #22, #3: Save with nothing ticked; the HTML report
    page.show_result(page.current()[0]["pick"]) if page.current()[1] is None and page.run_result else None
    exp = dict(page.S["export"])
    n_hist = len(page.history)
    page.S["export"].update({k: False for k in exp if isinstance(exp[k], bool)})
    BOXES.clear()
    page.save()
    nothing = (any("No file is ticked" in b for b in BOXES), len(page.history) == n_hist)
    page.S["export"].update(exp)
    path = page.report(open_it=False)
    check("review: Save with no file ticked says so (no “Saved”, nothing in History); Report writes the HTML report",
          nothing == (True, True) and path and os.path.isfile(path) and path.endswith(" - report.html"), (nothing, path))
    # #21: this session's runs, chosen again
    runs = list(page.session_runs)
    other = runs[0] if runs and runs[0] is not page.run_result else None
    if other:
        page.choose_run(id(other))
    check("review: the runs of this session are kept and one can be chosen again (Runs this session)",
          len(runs) >= 2 and page.runs_row.isVisibleTo(page) and other is not None and page.run_result is other,
          (len(runs), page.runs_combo.count()))
    # #20: History's Show goes through the curves' whole loading (Listen's list, the chip, the automatic settings)
    page.bring_back(entry)
    wait_for(lambda: page.curves is not None, 30)
    check("review: History's Show loads the measurement as a choice does (Listen's EQs to compare, Error without EQ)",
          page.curves and page.listen.pins_for == page.curves["name"] and page.chip_noeq.isVisibleTo(page),
          (page.listen.pins_for, page.curves and page.curves["name"]))
    # #19: curves shown from Find… can be taken off the graph outside it
    page.add_preview("check", "Check", list(page.curves["meas"]),
                     {"src": "app", "kind": "target", "names": [page.S["files"]["active_target"]]})
    shown = page.clear_prev_btn.isVisibleTo(page)
    page.clear_previews()
    check("review: a curve shown from Find… can be hidden from the graph (Hide shown curves)",
          shown and not page.previews and not page.clear_prev_btn.isVisibleTo(page))
    # #12, #15: Listen's list
    lis = page.listen
    BOXES.clear()
    empty = lis.add("Nothing", [{"type": "PK", "freq": 1000, "gain": 3, "q": 1, "enabled": False}])
    while len(lis.pins) > 1:
        lis._remove(lis.pins[-1])
    lis.add("One", [{"type": "PK", "freq": 500, "gain": 2, "q": 1}])
    lis.add("Two", [{"type": "PK", "freq": 600, "gain": 2, "q": 1}])
    lis._remove(next(p for p in lis.pins if p["name"] == "One"))
    lis.add("Three", [{"type": "PK", "freq": 700, "gain": 2, "q": 1}])
    colours = [p.get("color") for p in lis.pins]
    check("review: Listen refuses an EQ with no filter switched on; a new EQ to compare takes a colour not in use",
          empty is False and any("no filters" in b for b in BOXES) and len(set(colours)) == len(colours), colours)
    # #13: Listen's sliders: saved once, a moment after the last change, without redrawing the other screens
    told = []
    sw.listeners.append(lambda what, info: told.append(what))
    on_disk = lambda: (json.load(open(sw.path, encoding="utf-8")).get("listen") or {}).get("vol")
    for v in (-30, -31, -32):
        lis.vol.setValue(v)
    now = (on_disk(), list(told), sw.s["listen"].get("vol"))
    wait_for(lambda: on_disk() == -32, 3)
    check("review: Listen's volume is saved a moment after it stops moving, and the other screens aren't redrawn for it",
          now[0] != -32 and now[1:] == ([], -32) and on_disk() == -32, (now, on_disk()))
    # #14: editing the version heard crossfades (no dip)
    eng = audio.Engine(48000)
    eng.volume_db = 0
    eng.set_versions([("off", "EQ off", []), ("sel", "EQ", [{"type": "PK", "freq": 1000, "gain": 6, "q": 1}])])
    eng.set_level_match(False)
    eng.set_source("tone")
    eng.tone_hz = 1000
    eng.active = "sel"
    for _ in range(3):
        eng.render(4800)
    eng.set_versions([("off", "EQ off", []), ("sel", "EQ", [{"type": "PK", "freq": 1000, "gain": 5, "q": 1}])])
    y = eng.render(480)[:, 0]
    peaks = np.abs(y).reshape(-1, 48).max(1)
    check("review: changing the EQ being heard crossfades to the new one (no dip), and the old one goes after",
          peaks.min() > 0.9 * peaks.max() and not any(s.get("fading") for s in eng.slots), np.round(peaks, 3))
    # #16, #17: Enter in the search boxes
    from ui.picker import Picker
    pk = Picker(page, "measurement")
    pk.show()
    src = pk.src
    pk.q.setText("zzzz qqqq none")
    pk.q.setFocus()
    QTest.keyClick(pk.q, Qt.Key_Return)
    qapp.processEvents()
    pk_ok = pk.isVisible() and pk.src == src
    pk.close()
    from ui.history_window import HistoryWindow
    hw = HistoryWindow(page, False)
    hw.show()
    run_before = page.run_result
    hw.q.setFocus()
    QTest.keyClick(hw.q, Qt.Key_Return)
    qapp.processEvents()
    hw_ok = hw.isVisible() and page.run_result is run_before
    hw.close()
    check("review: Enter in Find…'s and History's search boxes presses no button (no source reset, no EQ brought back)",
          pk_ok and hw_ok, (pk_ok, hw_ok))
    # #8: the tour keeps the keyboard
    t = guide.start_eq(page)
    kept_focus = t.focusNextPrevChild(True) is True and t.focusNextPrevChild(False) is True
    # (review 2) the window resized mid-demo: the kept graph picture is laid out again inside it
    win = t.win
    was_size = win.size()
    t.pin_graph(page.plot)
    win.resize(was_size.width() - 300, was_size.height())
    qapp.processEvents()
    t.place()
    pin_inside = t.pin is not None and t.rect().contains(t.pin.geometry())
    win.resize(was_size)
    qapp.processEvents()
    t.end()
    check("review: a resized window keeps the Guide's graph picture inside it, laid out again", pin_inside,
          (t.rect(), t.pin.geometry() if t.pin is not None else None))
    check("review: Tab stays in the Guide (the controls under it can't be reached)", kept_focus)
    # #10, #11: the tracer's curve names and values shown
    page.open_trace()
    tw = page.tracer
    from ui.trace_window import sample_image
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    wait_for(lambda: not tw.reading, 60)
    tw.t.v.update(d1="90", d2="40")
    tw.auto_trace()
    tw.auto_trace()
    rows = list(tw.curve_rows)
    from PySide6.QtWidgets import QLineEdit
    box = rows[0].findChild(QLineEdit)
    QApplication_ = type(qapp)
    QApplication_.sendEvent(box, QFocusEvent(QEvent.FocusIn, Qt.MouseFocusReason))
    qapp.processEvents()
    same = tw.curve_rows == rows and tw.t.cur == 0 and not box.isHidden()
    tw.t.v["dashed"] = not tw.dashed.isChecked()
    tw.changed()
    check("review: the tracer: a curve's name box is selected without rebuilding the rows; values it sets show",
          same and tw.dashed.isChecked() == tw.t.v["dashed"], (same, tw.dashed.isChecked(), tw.t.v["dashed"]))
    tw.close()
    # (#31) the EQ screen in the dark theme, then light again
    from ui import theme
    theme.apply(qapp, dark=True)
    qapp.processEvents()
    dark = (page.plot.backgroundBrush().color().name(), theme.graph_colours()["bg"].lower())
    theme.apply(qapp, dark=False)
    qapp.processEvents()
    light = (page.plot.backgroundBrush().color().name(), theme.graph_colours()["bg"].lower())
    check("review: the EQ screen switches to the dark theme and back (the graph follows)",
          dark[0] == dark[1] and light[0] == light[1] and dark[0] != light[0], (dark, light))
    review_low_checks(page, wait_for, qapp)
    # #7: a checked button looks checked
    check("review: checked buttons are drawn as checked (the tracer's tools, Listen's versions)",
          "QPushButton:checked" in qapp.styleSheet())


def review_low_checks(page, wait_for, qapp):
    """The review's small findings, fixed (2026-10-07)."""
    import numpy as np
    from PySide6.QtGui import QImage, QColor, QShortcut
    from PySide6.QtWidgets import QApplication, QLineEdit
    from eq import bring_over
    from ui import audio, tour
    # #62, #65: Max Q on the result; the sliders edit frequency and Q too
    page.show_result(page.run_result["pick"])
    page.set_view("sliders")
    boxes = page.editor.sliders_scroll.widget().findChildren(QLineEdit)
    page.set_view("table")
    check("review: the result shows Max Q; the Sliders view edits each filter's frequency and Q",
          page.chips["maxq"].text().startswith("Max Q") and len(boxes) >= 2 * len(page.EDIT), (page.chips["maxq"].text(), len(boxes)))
    # #60: Best fit's own filters drawn ("With your filters")
    mode, mine = page.S["mode"], page.S["best_fit"].get("start_filters", "")
    page.S["mode"] = "best_fit"
    page.S["best_fit"]["start_filters"] = "Filter 1: ON PK Fc 300 Hz Gain 4 dB Q 1"
    page.draw()
    names = [it.name() for it in page.plot.listDataItems()]
    page.S["mode"], page.S["best_fit"]["start_filters"] = mode, mine
    page.draw()
    check("review: Best fit's own filters are drawn as “With your filters”", "With your filters" in names, names)
    # #63: the website methods' line, and Use in single run
    run_before = page.run_result
    fake = {"mode": "site_sweep", "pick": 1, "best": 1, "n": 99, "device": "X", "target_name": "Y",
            "results": [{"id": 1, "filters": [{"type": "PK", "freq": 1000, "gain": -3, "q": 1}], "n_filters": 1,
                         "rms": 1.0, "rows": 5, "freq_low": 20, "freq_high": 10000, "gain_min": -12, "gain_max": 6,
                         "q_min": 0.5, "q_max": 3, "preamp": -1.5, "max_boost": 0}]}
    page.run_result = fake
    page.show_result(1)
    shown = (page.site_row.isVisibleTo(page), "Filter rows <b>5</b>" in page.site_text.text(), page.site_use.isVisibleTo(page))
    page.use_in_single_run()
    copied = (page.S["mode"], page.S["site_single"]["rows"], "site_single.rows" in page.S["auto"]["manual"])
    page.S["mode"] = mode
    page.S["auto"]["manual"] = [m for m in page.S["auto"]["manual"] if not m.startswith("site_single.")]
    page.session_runs = [r for r in page.session_runs if r is not fake]
    page.run_result = run_before
    page.show_result(run_before["pick"])
    page.changed()
    check("review: a website method's result says what to type into squiglink's panel; Use in single run copies it",
          shown == (True, True, True) and copied == ("site_single", 5, True), (shown, copied))
    # #58: Use, with Undo
    from ui.picker import Picker
    pk = Picker(page, "measurement")
    wait_for(lambda: not pk.lib.get("scanning"), 60)
    row = next(iter(pk.pc_rows(["earpods"])), None)
    pk.close()
    if row:
        before = list(page.S["files"]["excluded"])
        res = page.svc.call("/api/use", dict(pk.body(row), kind="measurement", settings=page.S))
        page.used(res)
        offered = page.notice.isVisibleTo(page) and page.notice_undo.isVisibleTo(page)
        page.notice_undo.click()
        wait_for(lambda: not any(n in {m["name"] for m in page.inputs["measurements"]} for n in res.get("created") or []), 30)
        names_now = {m["name"] for m in page.inputs["measurements"]}
        check("review: Use offers Undo, which takes the file it made away and puts the measurement back",
              offered and sorted(page.S["files"]["excluded"]) == sorted(before)
              and not any(n in names_now for n in res.get("created") or []),
              (offered, res.get("created"), sorted(set(page.S["files"]["excluded"]) ^ set(before)),
               [n for n in res.get("created") or [] if n in names_now], BOXES[-2:]))
    else:
        print("skip review: Use's Undo (no sample measurement found on this PC)")
    # #69: a file set aside is said
    hist = os.path.join(os.environ["AUTOEQSTUDIO_DATA"], "eq", "history.json")
    with open(hist, "w") as fh:
        fh.write("{cut off")
    BOXES.clear()
    page.svc.call("/api/history")
    wait_for(lambda: BOXES, 5)
    check("review: a data file that can't be read (History's) is said, kept as .bad", any("couldn't be read" in b for b in BOXES)
          and os.path.exists(hist + ".bad"), BOXES[-1:])
    # #44, #47: "/" for Find…; a picture pasted on Make an EQ opens the tracer with it
    keys = [sc.key().toString() for sc in page.findChildren(QShortcut)]
    img = QImage(400, 300, QImage.Format_RGB888)
    img.fill(QColor("white"))
    QApplication.clipboard().setImage(img)
    page.paste_picture()
    pasted = page.tracer.isVisible() and page.tracer.t.has_image
    page.tracer.close()
    check("review: “/” opens Find…; a picture pasted on Make an EQ opens the tracer with it", "/" in keys and pasted, (keys, pasted))
    # #50: two blue lines close together: Hz far from them work out (no OverflowError)
    t = page.tracer.t
    if t.has_image:
        t.v.update(f1="1000", f2="1001", d1="90", d2="40")
        t.cal.update(x1=200.0, x2=203.0)
        k = t.calib()
        try:
            far = k.f(0) if k else None
            ok = True
        except OverflowError:
            ok = False
        check("review: the tracer's Hz far from two close blue lines is huge, not an error", ok, far)
    # #52, #53, #54, #56: Listen
    lis = page.listen
    tone_text = lis.tone_lab.text()
    lis._add_text("Filter 1: ON PK Fc 333 Hz Gain 2 dB Q 1", "Pasted check", "pasted")
    pasted_note = lis.pins[-1]["note"] if lis.pins else ""
    lis._remove(lis.pins[-1])
    undo_shown = lis.undo_row.isVisibleTo(lis)
    n = len(lis.pins)
    lis.undo_btn.click()
    check("review: Listen: the tone's frequency shown from the start; a pasted EQ says so; ✕ offers Undo, which puts it back",
          tone_text.endswith("Hz") and pasted_note == "pasted" and undo_shown and len(lis.pins) == n + 1,
          (tone_text, pasted_note, undo_shown, len(lis.pins), n))
    # (review 2) the tone's range: "nan" and 5 Hz shown as the values used, kept for the next start
    lis.tone_from.setText("nan")
    lis.tone_to.setText("5")
    lis.tone_range_done()
    kept = {k: (page.sw.s.get("listen") or {}).get(k) for k in ("tone_from", "tone_to")}
    check("listen: the tone's From and To show the values used (\"nan\", 5 Hz) and are kept for the next start",
          (lis.tone_from.text(), lis.tone_to.text()) == ("20", "20") and kept == {"tone_from": 20, "tone_to": 20}
          and lis.tone_lab.text().endswith("Hz"), (lis.tone_from.text(), lis.tone_to.text(), kept))
    lis.tone_from.setText("20")
    lis.tone_to.setText("20000")
    lis.tone_range_done()
    eng = audio.Engine(48000)
    eng.set_versions([("off", "EQ off", [])])
    eng.set_source("tone")
    eng.tone_hz = 1000
    eng.active, eng.volume_db = "off", -40
    for _ in range(3):
        eng.render(4800)
    eng.volume_db = 0
    y = np.abs(eng.render(4800)[:, 0])
    check("review: Listen's volume glides to a new value over a block (no step, no click)",
          y[:200].max() < 0.2 * y[-200:].max(), (y[:200].max(), y[-200:].max()))
    # #38: the tour's ring cut to what a scroll area shows
    r = tour._rect(page.window(), [page.listen])
    check("review: the Guide's ring is cut to what its scroll area shows", r.height() <= page.window().height(), r.getRect())
    # #66, #67: the bring-over: never into the real folders on a test's data folder alone; sources.json merged
    import tempfile
    d = tempfile.mkdtemp()
    a_, b_ = os.path.join(d, "a.json"), os.path.join(d, "b.json")
    with open(a_, "w") as fh:
        json.dump({"x.txt": {"site": "A"}, "y.txt": {"site": "B"}}, fh)
    with open(b_, "w") as fh:
        json.dump({"y.txt": {"site": "mine"}}, fh)
    done = []
    bring_over._merge_sources(a_, b_, done)
    merged = json.load(open(b_))
    root = os.environ.pop("AUTOEQSTUDIO_ROOT")
    try:
        blocked = not bring_over.needed()
    finally:
        os.environ["AUTOEQSTUDIO_ROOT"] = root
    check("review: bring-over adds AutoEQ Local's file records to the app's (keeps its own); never on a test's data "
          "folder alone", merged == {"y.txt": {"site": "mine"}, "x.txt": {"site": "A"}} and blocked, merged)


def rest_checks(page, wait_for, qapp):
    """The rest of AutoEQ Local brought over (2026-10-07): All results and the error grid, the graph's views (and
    the hover readout), Find… › Sources, the tracer's two-finger pinch and finger taps, odd /api/compare requests."""
    import numpy as np
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QMessageBox, QPinchGesture, QGestureEvent
    import net
    from ui.all_results import AllResults
    # All N results, and the grid by filter count and max Q (on a run of nine results made from this one's)
    real = page.run_result
    page.show_result(real["pick"])
    base = next(r for r in real["results"] if r["id"] == real["pick"])
    rs = [dict(base, id=f"t{n}-{q}" + "b" * k, n_filters=n, rows=n, q_max=q, rms=base["rms"] + 0.01 * (8 - n) + 0.002 * q + k * 0.0001)
          for n in (4, 6, 8) for q in (2, 4, 6) for k in (0, 1)]
    fake = dict(real, mode="best_fit", results=rs, best="t8-2", pick="t8-2")
    page.run_result = fake
    page.show_result("t8-2")
    ar = AllResults(page)
    grid_cells = [ar.grid.item(i, j) for i in range(ar.grid.rowCount()) for j in range(ar.grid.columnCount())]
    ids = [c.data(Qt.UserRole) for c in grid_cells if c is not None and c.data(Qt.UserRole) is not None]
    ar.pick("t4-6")
    grid_cells = [ar.grid.item(i, j) for i in range(ar.grid.rowCount()) for j in range(ar.grid.columnCount())]
    bold = [c.data(Qt.UserRole) for c in grid_cells if c is not None and c.font().bold()]
    picked = page.sel
    ar.table.sortItems(1, Qt.DescendingOrder)
    counts = [ar.table.item(i, 1).value for i in range(ar.table.rowCount())]
    shape = (ar.grid.rowCount(), ar.grid.columnCount(), ar.table.rowCount(), ar.grid.isHidden())
    ar.close()
    page.run_result = real
    page.show_result(real["pick"])
    check("all results: every result listed, the grid's cells by filter count and max Q (the best per cell), a click "
          "shows one (and marks it), the table sorts by value", shape == (3, 3, 18, False) and len(ids) == 9
          and picked == "t4-6" and bold == ["t4-6"] and counts == sorted(counts, reverse=True) and counts[0] == 8,
          (shape, len(ids), picked, bold, counts[:3]))
    # the graph's views: relative to target, the Y range, channels; the values under the pointer
    keep = dict(page.sw.s.get("graph") or {})
    page.graph_option(view="rel")
    tgt = dict(page._drawn["series"])["Target"]
    rel_ok = page._drawn["rel"] and float(np.max(np.abs(tgt))) < 1e-9 and page.plot.getAxis("left").labelText == "Δ dB"
    page.graph_option(y="30")
    lo, hi = page.plot.viewRange()[1]
    page.graph_option(view="abs", y="auto")
    page.plot.resize(800, 300)
    pl = page.plot
    page._hover(pl.mapToScene(QPoint(int(pl.width() * 0.5), int(pl.height() * 0.5))))
    read = page.hover_lab.text()
    page.graph_option(**keep)
    page._graph_timer.stop()
    check("graph views: Relative to target (the target at 0 dB, the axis Δ dB), a 30 dB Y range, the values under "
          "the pointer (Hz and each curve's dB); kept in the settings", rel_ok and abs((hi - lo) - 30) < 0.01
          and "Hz" in read and "Measurement" in read and (page.sw.s.get("graph") or {}).get("view") == keep.get("view", "abs"),
          (rel_ok, lo, hi, read))
    # Find… › Sources (offline: no list is fetched)
    from ui.sources_window import Sources
    S = page.S
    kept_db, kept_folders = json.loads(json.dumps(S["databases"])), list(S["library"].get("folders") or [])
    was_off = net.offline()
    net.set_offline(True)
    said = []
    real_info = QMessageBox.information
    QMessageBox.information = staticmethod(lambda *a, **k: said.append(a[2]))
    try:
        src = Sources(page)
        rows, _ = src.rows()
        builtin = next(r for r in rows if r["builtin"])
        src.set_on(builtin, False)
        off = builtin["name"] in S["databases"]["disabled"]
        src.set_on(builtin, True)
        on = builtin["name"] not in S["databases"]["disabled"]
        src.add("example.squig.link")
        src.add("https://example.squig.link/")
        src.add("https://example.squig.link")
        added = S["databases"]["extra"] == kept_db.get("extra", []) + ["https://example.squig.link/"]
        # (review 2) the added one's group switched off, answered No: nothing changes (it asked after removing them)
        src.render()
        grp = next(src.tree.topLevelItem(i) for i in range(src.tree.topLevelItemCount())
                   if any("example.squig.link" in src.tree.topLevelItem(i).child(j).text(0).lower()
                          or "example" in src.tree.topLevelItem(i).child(j).text(0).lower()
                          for j in range(src.tree.topLevelItem(i).childCount())))
        real_q = QMessageBox.question
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
        try:
            grp.setCheckState(0, Qt.Unchecked)
        finally:
            QMessageBox.question = real_q
        qapp.processEvents()
        asked_first = "https://example.squig.link/" in S["databases"]["extra"]
        check("sources: switching off a group with ones you added asks first; No keeps them", asked_first,
              S["databases"]["extra"])
        extra = next(r for r in src.rows()[0] if r["extra"] and "example.squig.link" in r["url"])
        src.set_on(extra, False)
        removed = S["databases"]["extra"] == kept_db.get("extra", [])
        src.folders.setPlainText("C:\\Music\n\n  D:\\Curves  ")
        folders = S["library"]["folders"]
        offline_note = "Offline" in src.dir_note.text()
        src._refresh_soon.stop()
        S["databases"].clear()
        S["databases"].update(kept_db)
        S["library"]["folders"] = kept_folders
        src.reject()
    finally:
        QMessageBox.information = real_info
        net.set_offline(was_off)
    check("sources: a database switched off and on, one added by its address (a wrong or repeated address said), "
          "removed again, the folders one per line; offline, squig.link's list isn't fetched",
          off and on and added and removed and folders == ["C:\\Music", "D:\\Curves"] and offline_note
          and len(said) == 2 and "https://" in said[0] and "already" in said[1], (off, on, added, removed, folders, said))
    # the tracer: two fingers pinch (zoom about their centre) and drag; a finger's tap traces, a moving finger drags
    from ui.trace_window import sample_image
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    wait_for(lambda: not tw.reading, 60)
    st = tw.stage
    st.resize(900, 600)
    v0 = dict(st.view)
    g = QPinchGesture()
    g.setScaleFactor(1.5)
    centre = st.mapToGlobal(QPoint(450, 300))
    g.setCenterPoint(QPointF(centre))
    g.setLastCenterPoint(QPointF(centre) - QPointF(10, 0))
    st.event(QGestureEvent([g]))
    v1 = dict(st.view)
    tw.set_tool("trace")
    st.line_at = lambda *_a: None  # (a finger here, not on a calibration line)
    v_before = dict(st.view)

    def finger(kind, x, y):
        p = QPointF(x, y)
        st.event(QMouseEvent(kind, p, p, QPointF(st.mapToGlobal(p.toPoint())), Qt.LeftButton,
                             Qt.LeftButton if kind != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier,
                             Qt.MouseEventSynthesizedBySystem))
    finger(QEvent.MouseButtonPress, 300, 300)
    finger(QEvent.MouseMove, 340, 320)
    finger(QEvent.MouseButtonRelease, 340, 320)
    panned = (st.view["ox"] - v_before["ox"], st.view["oy"] - v_before["oy"])
    del st.line_at
    tw.close()
    check("tracer: two fingers zoom about their centre and drag the picture; a finger that moves drags it (a tap "
          "would trace)", abs(v1["s"] / v0["s"] - 1.5) < 0.01 and v1["ox"] != v0["ox"]
          and panned == (40, 20), (v0, v1, panned))
    # /api/compare: a query that isn't text (a number, a list) answers as an empty one, never a crash
    odd = [page.svc.call("/api/compare", {"query": q, "settings": page.S}) for q in (5, ["x"], None)]
    avg = page.svc.call("/api/compare/average", {"keys": "x", "name": 3})
    check("compare: a query that isn't text is answered (no crash); average with odd keys says what to choose",
          all("Traceback" not in json.dumps(r) for r in odd) and "Choose the measurements" in avg.get("error", ""),
          (odd, avg))


def preset_checks(page, wait_for):
    """Presets ▾ (the user, 2026-10-12: brought back from AutoEQ Local): the settings saved under a name (not the
    files), loaded again (Undo puts the ones before back), deleted; Reset all settings with its Undo."""
    from PySide6.QtWidgets import QInputDialog, QMenu
    from eq import paths as eq_paths
    S = page.S
    was_all = json.loads(json.dumps(S))
    was_mode, was_files = S["mode"], json.dumps(S["files"])
    real = QInputDialog.getText
    QInputDialog.getText = staticmethod(lambda *a, **k: ("Check preset", True))
    try:
        page.save_preset()
    finally:
        QInputDialog.getText = real
    saved = os.path.exists(os.path.join(eq_paths.PRESET_DIR, "Check preset.json"))
    menu = QMenu()
    page.fill_presets(menu)
    listed = [a.text() for a in menu.actions()]
    page.S["mode"] = "site_single" if was_mode != "site_single" else "best_fit"
    page.changed()
    page.load_preset("Check preset")
    loaded = (page.S["mode"], json.dumps(page.S["files"]), page.mode_combo.currentData())
    page.notice_undo.click()
    undone = page.S["mode"]
    page.load_preset("Check preset")
    page.delete_preset("Check preset")
    gone = not os.path.exists(os.path.join(eq_paths.PRESET_DIR, "Check preset.json"))
    page.S["best_fit"]["q_min"] = 0.7
    page.reset_settings()
    reset = page.S["best_fit"]["q_min"] != 0.7 and json.dumps(page.S["files"]) == was_files
    page.notice_undo.click()
    reset_undone = page.S["best_fit"]["q_min"] == 0.7
    check("presets: Presets ▾ saves the settings (not the files) under a name, lists it, loads it (Undo puts the ones "
          "before back), deletes it; Reset all settings, with its Undo",
          saved and "Check preset" in listed and "Save current settings as…" in listed
          and loaded == (was_mode, was_files, was_mode) and undone != was_mode and gone and reset and reset_undone,
          (saved, listed, loaded, undone, gone, reset, reset_undone))
    page.S = was_all  # (the settings as they were)
    page.changed(curves=True)
    wait_for(lambda: page.curves is not None, 30)


def removed_settings_checks():
    """The settings review (the user, 2026-10-13): removed settings leave an older copy's settings and presets;
    the hidden ones (gain penalty, treble guard, high shelf, Simpler means) stay usable but aren't on the screens."""
    from eq import settings
    old = settings.with_auto({"app": {"browser": "auto", "window": "tab"},
                              "best_fit": {"build": "scratch", "random_starts": 5, "seed_with_site": True},
                              "scoring": {"pick": "simplest", "tolerance_db": 0.2}})
    kept = settings.with_auto({"best_fit": {"gain_penalty": 0.001, "high_shelf": True},
                               "scoring": {"priority": ["max_q", "n_filters", "max_boost"]}})
    gone = ["app" in old, *(k in old["best_fit"] for k in ("build", "random_starts", "seed_with_site")),
            "tolerance_db" in old["scoring"]]
    check("settings: the removed ones leave an older copy's settings (the old pick becomes the audible one); the hidden "
          "ones still work",
          not any(gone) and old["scoring"]["pick"] == "audible" and kept["best_fit"]["gain_penalty"] == 0.001
          and kept["best_fit"]["high_shelf"] is True and kept["scoring"]["priority"][0] == "max_q", (gone, old["scoring"]))


def review2_maths_checks():
    """Review 2's fixes in the EQ part's maths and files."""
    from eq import databases, engines, exports, inputs
    check("best fit: a shelf's Q stays within the EQ app's (0.5-6 took shelves at 0.44), AutoEq's 0.4-0.7 otherwise",
          engines.shelf_q({"q_min": 0.5, "q_max": 6}) == (0.5, 0.7) and engines.shelf_q({"q_min": 0.18, "q_max": 6})
          == (0.4, 0.7) and engines.shelf_q({"q_min": 1.0, "q_max": 6})[0] == 1.0)
    lo, hi, _s = engines._mine_bounds([{"type": "PK", "freq": 8000.0, "gain": 3.0, "q": 1.0}],
                                      {"q_min": 0.5, "q_max": 6, "gain_min": -12, "gain_max": 12, "freq_low": 40,
                                       "freq_high": 10000})
    check("best fit: your own filters, when adjusted, stay within the EQ app's frequency range", 10 ** hi[0] <= 10000.01,
          10 ** hi[0])
    named = [inputs.device_name(x) for x in (["Foo (Bar) 1 L.txt", "Foo (Bar) 1 R.txt", "Foo (Bar) 2 L.txt"],
                                             ["Foo (Bar) 1 L.txt", "Foo (Bar) 1 R.txt"], ["IE 900 L.txt", "IE 900 R.txt"])]
    check("files: a database's several measurements (\"Foo 1 L\", \"Foo 2 L\"), or one of them, are named Foo; a "
          "model's own number stays", named == ["Foo (Bar)", "Foo (Bar)", "IE 900"], named)
    notes = []
    exports.uapp_xml([{"type": "PK", "freq": 100, "gain": 15, "q": 1}, {"type": "PK", "freq": 120, "gain": 12, "q": 1}],
                     -24.0, "x", notes)
    check("files: USB Audio Player PRO's file says when its pre-amp can't go low enough (it can clip)",
          any("can clip" in n for n in notes), notes)
    saved = dict(databases._state)
    real = databases.refresh_now, databases.directory  # (nothing loaded for real: a stand-in that just finishes)
    databases.refresh_now = lambda sites, force=False: databases._state.update(loading=False)
    databases.directory = lambda refresh=False: []
    try:
        databases._state.update(updated=time.time(), sites=[{"name": "all", "error": "x", "count": 0}])
        from eq import service
        r = service.call("/api/db/refresh", {})
        t0 = time.time()
        while databases._state.get("loading") and time.time() - t0 < 5:
            time.sleep(0.05)
    finally:
        databases.refresh_now, databases.directory = real
        databases._state.clear()
        databases._state.update(saved)
    check("databases: a refresh after a failed one isn't refused with \"Missing 'url'\"", "url" not in str(r.get("error", "")), r)


def grow_checks(cfg, curves, mt, tt):
    """Best fit grown one filter at a time (best_fit.build "grow", the default since 2026-10-13: the method test,
    BENCHMARKS.md), the audible pick (the target first, then the closest result) and the ear error;
    website seeding off (B1)."""
    import numpy as np
    from eq import autoset, engines, pipeline, settings
    d = settings.DEFAULTS["best_fit"]
    plans = [autoset.plan(settings.with_auto({"mode": "best_fit", "auto": {"level": lv}}),
                          {"features": 10, "no_eq_rms": 3, "band_top": 10000, "band_why": "default", "n_files": 1,
                           "unstable_from": None, "need_boost": 6, "boost_at": 3000, "need_cut": -6, "cut_at": 100,
                           "q_need": 3, "q_at": 2000, "bass_step": 0, "treble_step": 0, "data_top": 20000,
                           "agree_to": None})["values"] for lv in (0, 50, 100)]
    adjusted = autoset.plan(settings.with_auto({"mode": "best_fit", "auto": {"level": 0}, "best_fit": {
        "start_filters": "1000 2 1", "start_keep": False}}), {"features": 10, "no_eq_rms": 3, "band_top": 10000,
        "band_why": "default", "n_files": 1, "unstable_from": None, "need_boost": 6, "boost_at": 3000, "need_cut": -6,
        "cut_at": 100, "q_need": 3, "q_at": 2000, "bass_step": 0, "treble_step": 0, "data_top": 20000,
        "agree_to": None})["values"]["best_fit.filter_counts"]
    check("Best fit: your own filters adjusted (each count on its own): Quick's counts stay sparse",
          len(adjusted) < 32, adjusted)
    check("Best fit: grows by default, no website seeding; the automatic settings: every filter count, the audible pick "
          "(0.25 dB), no seeding, at every search",
          "build" not in d and "seed_with_site" not in d and settings.DEFAULTS["scoring"]["pick"] == "audible"
          and all("best_fit.seed_with_site" not in v and v["scoring.pick"] == "audible" and v["scoring.ear_db"] == 0.25
                  and v["best_fit.filter_counts"] == list(range(1, 33)) for v in plans),
          [(v["scoring.pick"], len(v["best_fit.filter_counts"])) for v in plans])
    # every count a result, closer with more filters; the progress counts the filters added
    said = []
    cg = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"pick": "lowest"}, "best_fit": {
        "filter_counts": list(range(1, 7)), "gain_max": [6], "q_max": [3], "low_shelf": False, "high_shelf": False,
        "fight_penalty": [0.01]}})
    out = pipeline.run_mode("best_fit", cg, curves, mt, tt, progress=lambda dn, t, m="": said.append((dn, t, m)))
    rs = sorted(out["results"], key=lambda r: r["rows"])
    grew = [m for _d, _t, m in said if m.startswith("Adding filters one at a time")]
    check("Best fit, growing: every count is a result, each closer than the first; the progress counts the filters added",
          [r["rows"] for r in rs] == [1, 2, 3, 4, 5, 6] and all(len(r["filters"]) <= r["rows"] for r in rs)
          and rs[-1]["rms"] < rs[0]["rms"] and grew and said[-1][:2] == (6, 6),
          ([(r["rows"], round(r["rms"], 3)) for r in rs], said[-1:]))
    # the audible pick: the fewest filters that sound the same as the target; the growing stops there
    ca = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": {
        "filter_counts": list(range(1, 33)), "gain_max": [6, 9], "q_max": [3, 5]}})
    t0 = time.time()
    out = pipeline.run_mode("best_fit", ca, curves, mt, tt)
    p, lim = out["pick"], ca["scoring"]["ear_db"]
    fewer = [r for r in out["results"] if r["ear"] <= lim and (r["n_filters"], r["rows"]) < (p["n_filters"], p["rows"])]
    check("pick: the fewest filters that sound the same as the target (ear error within 0.25 dB); growing stops there",
          out["pick_case"] == "target" and p["ear"] <= lim and not fewer
          and max(r["rows"] for r in out["results"]) < 32 and p.get("ear_at"),
          (out["pick_case"], p["n_filters"], round(p["ear"], 3), round(time.time() - t0, 1), fewer[:1]))
    # pick() itself: the target first; out of reach: the simplest that sounds the same as the closest
    f = np.geomspace(20, 20000, 400)
    bump = lambda db, at: db * np.exp(-0.5 * (np.log2(f / at) / 0.5) ** 2)
    cv, band = {"f": f, "meas": np.zeros_like(f), "target": np.zeros_like(f)}, [20, 10000]

    def res(i, n, eq):
        r = {"id": i, "rows": n, "n_filters": n, "max_q": 1, "max_boost": 1, "eq": eq,
             "rms": engines.rms_error(f, eq, cv["target"], band)}
        r["ear"], r["ear_at"] = engines.ear_error(f, eq, band)
        return r
    sc = {"pick": "audible", "ear_db": 0.25, "tolerance_db": 0.1, "priority": ["n_filters", "max_q", "max_boost"]}
    near = [res(0, 3, bump(0.6, 1000)), res(1, 5, bump(0.1, 1000) + 0.4), res(2, 8, np.zeros_like(f))]
    far = [res(0, 3, bump(1.0, 5000)), res(1, 5, bump(0.95, 1000)), res(2, 8, bump(0.8, 1000))]
    (a, _, a_case), (b, _, b_case) = engines.pick(near, sc, cv, band), engines.pick(far, sc, cv, band)
    high = engines.ear_error(f, np.where(f > 10000, 3.0, 0.0), band)[0]  # (only above the scored range)
    check("pick: the target first (a level offset isn't a difference); out of reach, the simplest close to the closest; "
          "the ear error only within the scored range",
          (a["id"], a_case, b["id"], b_case) == (1, "target", 1, "best") and high < 0.05 and "pick_case" not in a,
          (a["id"], a_case, b["id"], b_case, round(high, 3)))


def pick_note_checks(page):
    """The line under the result's numbers: sounds the same as the target, or out of reach (how far off, where)."""
    r = {"id": 1, "ear": 0.18, "ear_at": 2500.0}
    best = {"id": 2, "ear": 0.47, "ear_at": 6200.0}
    same = page.pick_note({"pick": 1, "pick_case": "target", "ear_db": 0.25, "results": [r]}, r)
    far = {"id": 1, "ear": 0.52, "ear_at": 2500.0}  # (out of reach: the closest is the lowest ear error, 0.47 dB)
    out = page.pick_note({"pick": 1, "best": 1, "pick_case": "best", "ear_db": 0.25, "results": [far, best]}, far)
    other = page.pick_note({"pick": 1, "pick_case": "target", "ear_db": 0.25, "results": [r, best]}, best)
    none = page.pick_note({"pick": 1, "results": [r]}, r)
    alone = page.pick_note({"pick": 1, "pick_case": "best", "ear_db": 0.25, "results": [far]}, far)
    check("result: says it sounds the same as the target, or how far off the closest is and where (none for an old run); "
          "the closest one itself isn't said to have fewer filters (review 2)",
          same.startswith("Sounds the same as the target: within 0.18 dB") and "0.47 dB off around 6.2 kHz" in out
          and "fewer filters" in out and "most off around 6.2 kHz" in other and none == ""
          and alone.endswith("This is that closest one."), (same, out, other, none, alone))


def search_checks(page, wait_for):
    """One search (1.0.8, the user's ask 2026-10-13, instead of Quick, Standard and Thorough): the line says what a
    run tries (every limit with both fighting-filter penalties) and how long; no buttons; an older copy's settings
    (a search level, one penalty) are brought up to date."""
    from eq import settings
    kept = json.loads(json.dumps(page.S["auto"]))  # (the checks before turned the automatic settings off and set values)
    page.S["auto"].update(enabled=True, manual=[])
    page.refresh_auto()
    bf = page.S["best_fit"]
    what, est = page.sa_what.text(), page.estimate.text()
    old = settings.with_auto({"auto": {"level": 100}, "best_fit": {"fight_penalty": 0.004}})
    page.S["auto"] = kept
    page.refresh_auto()
    check("search: one search, every limit with both fighting-filter penalties, said with its time; no buttons; an "
          "older copy's level dropped and its one penalty made a list",
          bf["fight_penalty"] == [0.003, 0.01] and len(bf["q_max"]) >= 4 and "fighting-filter penalties" in what
          and est.startswith("A run takes") and not hasattr(page, "sa_btns")
          and "level" not in old["auto"] and old["best_fit"]["fight_penalty"] == [0.004],
          (bf["fight_penalty"], bf["q_max"], what, est, old["auto"], old["best_fit"]["fight_penalty"]))


def order_checks(page, wait_for):
    """A to Z (the user, 2026-10-12): the Target and Measurement lists and Find…'s rows in A to Z order with numbers
    as numbers ("IEM 2" before "IEM 10"); Find…'s Rig, Type and Source lists open with a search box that narrows
    them, and Enter there chooses."""
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication
    from ui.picker import Picker
    from PySide6.QtWidgets import QComboBox
    from ui.search_combo import SEARCH_FROM, SearchCombo, natural_key
    keyed = sorted(["IEM 10", "iem 2", "IEM 1", "Alpha  b"], key=natural_key)
    names = [page.target_combo.itemText(i) for i in range(page.target_combo.count())]
    devs = list(page.groups)
    pk = Picker(page, "measurement")
    pk.finish_list()
    rows = [pk.list.item(k).data(Qt.UserRole) for k in range(pk.list.count()) if pk.list.item(k).data(Qt.UserRole)]
    app_rows = [r["name"] for r in rows if r["src"] == "app"]
    pc_rows = [r["name"] for r in rows if r["src"] == "pc"]
    combos = all(isinstance(b, SearchCombo) for b in (pk.f_rig, pk.f_form, pk.f_site))
    sites = [pk.f_site.itemData(i) for i in range(pk.f_site.count())]
    # a list over SEARCH_FROM choices opens with the search box; typed in part, the one left; Enter chooses it
    big, small = SearchCombo(), SearchCombo()
    big.addItems([f"Choice {i}" for i in range(1, SEARCH_FROM + 6)])
    small.addItems(["a", "b", "c"])
    last = big.itemText(big.count() - 1)
    big.showPopup()
    pop = big._popup
    pop.q.setText(last)
    shown = [pop.list.item(k).text() for k in range(pop.list.count()) if not pop.list.item(k).isHidden()]
    QApplication.sendEvent(pop.q, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
    chosen = (big.currentIndex() == big.count() - 1, pop.isVisible())
    lay = page.settings.adv_form.fields["best_fit.layout"].box
    rule = (big.searches(), small.searches(), isinstance(lay, SearchCombo) and lay.searches(),
            all(isinstance(b, SearchCombo) for b in page.findChildren(QComboBox)))
    # every drop-down A to Z, numbers as numbers (a first "Choose…" or "Automatic…" may stay on top); Find…'s filters
    # keep their own order (any, "fits", in the app and this PC first, "not known" last)
    unsorted = []
    for c in page.findChildren(SearchCombo):
        # (the Target and Measurement lists: A to Z by name, their own check above; the counts after a name aside)
        if isinstance(c.window(), Picker) or c.count() < 3 or c in (page.target_combo, page.measurement_combo):
            continue
        texts = [c.itemText(k) for k in range(c.count())]
        if not any(texts[k:] == sorted(texts[k:], key=natural_key) for k in (0, 1)):
            unsorted.append((texts[:4], type(c.parent()).__name__))
    pk.clear_filters()
    pk.reject()
    check("order: the Target and Measurement lists and Find…'s rows A to Z, numbers as numbers; Find…'s filter lists "
          "open with a search box that narrows them, Enter chooses; every drop-down searches when over SEARCH_FROM "
          "choices (Advanced's Layout), a short one doesn't; every drop-down A to Z",
          keyed == ["Alpha  b", "IEM 1", "iem 2", "IEM 10"] and sorted(["0.8", "0.707", "0.42", "0.5"], key=natural_key) == ["0.42", "0.5", "0.707", "0.8"] and names == sorted(names, key=natural_key)
          and devs == sorted(devs, key=natural_key) and app_rows == sorted(app_rows, key=natural_key)
          and pc_rows == sorted(pc_rows, key=natural_key) and combos and len(sites) >= 2 and shown == [last]
          and chosen == (True, False) and sites[0] == "" and sites[1] in ("app", "pc")
          and rule == (True, False, True, True) and not unsorted,
          (combos, sites[:4], last, shown, chosen, rule, unsorted[:3], names == sorted(names, key=natural_key),
           devs == sorted(devs, key=natural_key), app_rows == sorted(app_rows, key=natural_key),
           pc_rows == sorted(pc_rows, key=natural_key), keyed))


def adjust_checks(page, wait_for):
    """The Target card's Adjust (the user, 2026-10-12: the tilt and the rest couldn't be found in the Settings fold):
    it opens under the target; + and ↑ step the tilt and the target is drawn again; Reset puts every adjustment back
    to 0 and Undo brings them back."""
    import numpy as np
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication
    st = page.settings
    was = dict(page.S["target_adjust"])
    on_card = st.adjust_btn.isVisibleTo(page) and st.adjust_panel.parentWidget() is page.target_box
    st.adjust_btn.setChecked(True)
    QApplication.processEvents()
    tilt = st.adjust_form.fields["target_adjust.tilt"]
    opened = tilt.box.isVisibleTo(page) and tilt.plus.isVisibleTo(page)
    wait_for(lambda: page.curves is not None, 30)
    before = np.asarray(page.curves["target"]).copy()
    tilt.plus.click()
    stepped = page.S["target_adjust"]["tilt"]
    wait_for(lambda: page.curves is not None and not np.allclose(np.asarray(page.curves["target"]), before), 30)
    redrawn = page.curves is not None and not np.allclose(np.asarray(page.curves["target"]), before)
    QApplication.sendEvent(tilt.box, QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier))
    keyed = (page.S["target_adjust"]["tilt"], tilt.box.text())
    summary = st.adjust_summary.text()
    shown = st.reset_adjust_btn.isEnabled() and st.save_target_btn.isEnabled()
    st.reset_adjust_btn.click()
    reset = (page.S["target_adjust"]["tilt"], tilt.box.text(), st.reset_adjust_btn.isEnabled())
    page.notice_undo.click()
    undone = page.S["target_adjust"]["tilt"]
    bass, bass_hz = st.adjust_form.fields["target_adjust.bass_gain"], st.adjust_form.fields["target_adjust.bass_freq"]
    hz_greyed = bass_hz.box.isVisibleTo(page) and not bass_hz.box.isEnabled()
    bass.plus.click()
    hz_usable = bass_hz.box.isVisibleTo(page) and bass_hz.box.isEnabled()
    bass.minus.click()
    check("target: Adjust, on the Target card, opens the adjustments; + and ↑ step the tilt and the target is drawn "
          "again; a gain's Hz and Q stay in place, greyed while it's 0; Reset puts them back to 0 (Undo brings them back)",
          on_card and opened and hz_greyed and hz_usable and stepped == 0.1 and redrawn and keyed == (0.2, "0.2") and "tilt +0.2" in summary
          and shown and reset == (0.0, "0", False) and undone == 0.2,
          (on_card, opened, hz_greyed, hz_usable, stepped, redrawn, keyed, summary, shown, reset, undone))
    page.S["target_adjust"] = was
    page.changed(curves=True)
    st.adjust_btn.setChecked(False)
    wait_for(lambda: page.curves is not None, 30)


def target_save_checks(page, wait_for):
    """Target › Adjust › Save as a target…: the adjusted target becomes a target of its own (made for
    the original's rig, before any conversion), in use, the adjustments back to 0; Undo puts it all back."""
    import numpy as np
    from PySide6.QtWidgets import QInputDialog
    from eq import rigs
    S = page.S
    was_target, was_adj = S["files"]["active_target"], dict(S["target_adjust"])
    hidden = not page.settings.save_target_btn.isEnabled()  # (greyed until the target is adjusted)
    S["target_adjust"]["tilt"] = -0.5
    S["target_adjust"]["bass_gain"] = 4.0
    page.svc.call("/api/settings", {"settings": S})
    page.load_curves()
    wait_for(lambda: page.curves is not None, 30)
    shown_before = np.asarray(page.curves["target"]).copy()
    real = QInputDialog.getText
    QInputDialog.getText = staticmethod(lambda *a, **k: ("My bassy target", True))
    try:
        page.save_adjusted_target()
    finally:
        QInputDialog.getText = real
    wait_for(lambda: page.curves is not None and page.S["files"]["active_target"] == "My bassy target.csv", 30)
    page.load_curves()
    wait_for(lambda: page.curves is not None, 30)
    now = page.S
    same = float(np.max(np.abs(np.asarray(page.curves["target"]) - shown_before))) if page.curves else 99
    rig_kept = rigs.target_rig("My bassy target.csv")[0] == rigs.target_rig(was_target)[0]
    state = (now["files"]["active_target"], now["target_adjust"]["tilt"], now["target_adjust"]["bass_gain"])
    from eq import paths as eq_paths
    made = os.path.exists(os.path.join(eq_paths.TARGET_DIR, "My bassy target.csv"))
    undo_shown = page.notice_undo.isVisibleTo(page)
    page.notice_undo.click()
    wait_for(lambda: page.S["files"]["active_target"] == was_target, 30)
    back = (page.S["files"]["active_target"], page.S["target_adjust"]["bass_gain"],
            os.path.exists(os.path.join(eq_paths.TARGET_DIR, "My bassy target.csv")))
    check("target: Save as a target… (shown once the target is adjusted) keeps it as a target of its own, in use, the "
          "adjustments back to 0, drawn the same (its rig kept); Undo puts it all back",
          hidden and state == ("My bassy target.csv", 0.0, 0.0) and same < 0.05 and rig_kept
          and made and undo_shown and back == (was_target, 4.0, False), (hidden, state, same, rig_kept, made, back))
    page.S["target_adjust"] = was_adj
    page.S["files"]["active_target"] = was_target
    page.svc.call("/api/settings", {"settings": page.S})
    page.load_curves()
    wait_for(lambda: page.curves is not None, 30)


def compare_results_checks(page):
    """Compare… (ui/compare_results.py): the result shown now and the others of this session (and History) side by
    side, their numbers worked out as the result card's, Show B putting one on the card (2026-10-08)."""
    from ui.compare_results import CompareResults, options
    run, r = page.current()
    first = page.sel
    # (another run of this session to compare with: the result with its first four filters)
    extra = dict(run, n=99, pick="cmp-4", best="cmp-4", device=page.curves["name"],
                 results=[dict(r, id="cmp-4", n_filters=4, rms=r["rms"] + 0.3, filters=r["filters"][:4])])
    page.session_runs.append(extra)
    opts = options(page)
    dlg = CompareResults(page)
    if len(opts) > 1:  # (B: the other run's result; the lists are A to Z, so by its name)
        dlg.combos[1].setCurrentIndex(dlg.combos[1].findText(opts[1]["label"]))
    a_rms = dlg.numbers.item(0, 1).text() if dlg.numbers.rowCount() else ""
    card = page.stats()["rms"]
    names = [dlg.numbers.item(i, 0).text() for i in range(dlg.numbers.rowCount())]
    rows = (dlg.tables[0].rowCount(), dlg.tables[1].rowCount())
    other = opts[1] if len(opts) > 1 else None
    if other and other["rid"] is not None:
        dlg.show_on_card(1)
    moved = page.sel
    dlg.close()
    page.session_runs.remove(extra)
    page.run_result = run
    page.show_result(first)
    check("compare: the result shown now and another side by side (the error as the result card's, every number, "
          "both filter tables); Show B puts it on the result card", len(opts) >= 2 and opts[0]["label"].startswith("Shown now")
          and a_rms == f"{card:.2f}" and len(names) == 6 and rows[0] == len(page.active()) and rows[1] == 4
          and (other is None or other["rid"] is None or moved == other["rid"]) and page.cmp_btn.isVisibleTo(page),
          (len(opts), a_rms, card, names, rows, moved))


def queue_checks(page, wait_for):
    """Run several… (ui/queue_window.py): two EQs in one go, each saved (never over a file) and kept in History and
    Runs this session; your own choice of files put back after (2026-10-08)."""
    import copy as _copy
    from PySide6.QtCore import Qt
    from ui.queue_window import QueueWindow
    from eq import paths as eq_paths
    before = _copy.deepcopy(page.S["files"])
    kept_S = _copy.deepcopy(page.S)  # (quick runs for the check: no automatic settings, one filter count)
    page.S["auto"]["enabled"] = False
    page.S["mode"] = "best_fit"
    page.S["best_fit"].update(filter_counts=[5], random_starts=0, seed_with_site=False)
    runs, hist = len(page.session_runs), len(page.history)
    out_before = set(os.listdir(eq_paths.OUTPUT_DIR)) if os.path.isdir(eq_paths.OUTPUT_DIR) else set()
    q = QueueWindow(page)
    targets = [q.tgts.item(i) for i in range(q.tgts.count())]
    for it in targets[:2]:
        it.setCheckState(Qt.Checked)
    from ui.queue_window import _ticked
    n = len(_ticked(q.devs)) * len(_ticked(q.tgts))
    q.start()
    done = wait_for(lambda: not q.running, 300)
    said = [q.table.item(i, 2).text() for i in range(q.table.rowCount())]
    made = set(os.listdir(eq_paths.OUTPUT_DIR)) - out_before
    q.close()
    page.S = kept_S
    page.svc.call("/api/settings", {"settings": page.S})
    check("queue: Run several makes an EQ for each IEM and target ticked, each saved and kept in History and Runs this "
          "session; your choice of files is as it was", done and len(said) == n >= 1
          and all(s.startswith("Done") for s in said) and len(made) >= n and len(page.session_runs) == min(20, runs + n)
          and len(page.history) >= hist + n and page.S["files"] == before, (done, said, sorted(made), runs, hist))


def a11y_checks(page, wait_for):
    """Every control a screen reader can name, and Tab can reach (tools\a11y.py), on Make an EQ (its folds open) and
    in its windows; the tracer's buttons stay out of the Tab order on purpose (Space is the picture's), so there only
    the names (2026-10-08)."""
    import net
    sys.path.insert(0, TOOLS)
    import a11y
    from ui.all_results import AllResults
    from ui.compare_results import CompareResults
    from ui.history_window import HistoryWindow
    from ui.picker import Picker
    from ui.queue_window import QueueWindow
    from ui.sources_window import Sources
    folds = (page.settings.fold.btn.isChecked(), page.settings.adv.btn.isChecked())
    page.settings.fold.btn.setChecked(True)
    page.settings.adv.btn.setChecked(True)
    page.window().show()
    wait_for(lambda: False, 0.3)
    found = {"Make an EQ": (a11y.unnamed(page), a11y.unreachable(page))}
    page.settings.fold.btn.setChecked(folds[0])
    page.settings.adv.btn.setChecked(folds[1])
    was_off = net.offline()
    net.set_offline(True)
    try:
        for name, make in (("All results", lambda: AllResults(page)), ("Compare", lambda: CompareResults(page)),
                           ("Run several", lambda: QueueWindow(page)), ("History", lambda: HistoryWindow(page, False)),
                           ("Find…", lambda: Picker(page, "measurement")), ("Sources", lambda: Sources(page))):
            w = make()
            w.show()
            wait_for(lambda: False, 0.3)
            found[name] = (a11y.unnamed(w), a11y.unreachable(w))
            if name == "Sources":
                w._refresh_soon.stop()
            w.close()
        page.open_trace()
        page.tracer.show()
        wait_for(lambda: False, 0.3)
        found["Trace image"] = (a11y.unnamed(page.tracer), [])
        page.tracer.close()
    finally:
        net.set_offline(was_off)
    bad = {k: v for k, v in found.items() if v[0] or v[1]}
    check("access: every control on Make an EQ and in its windows has a name a screen reader reads, and Tab reaches "
          "it", not bad, {k: ([f"{x[0]}:{x[1] or x[2][:16]}" for x in v[0]], [f"{x[0]}:{x[1]}" for x in v[1]])
                          for k, v in bad.items()})


def in_use_checks():
    """A file in use for a moment (a curves load reading it) is still removed: Undo's removal failed so once."""
    import threading
    from eq import inputs
    p = os.path.join(inputs.folder("measurement"), "Busy for a moment L.txt")
    with open(p, "w") as fh:
        fh.write("20 0\n20000 0\n")
    held = open(p, "rb")
    threading.Timer(0.3, held.close).start()
    try:
        inputs.remove_file("measurement", "Busy for a moment L.txt")
        gone = not os.path.exists(p)
    except OSError as e:
        gone = e
    check("files: one in use for a moment (being read) is removed once it's free, not left behind", gone is True, gone)


def try_checks(page):
    """Use on device › Try for 5 minutes on: the result plays on the device from APO's file (a trial, not a profile),
    and ends with the device's own EQ back (2026-10-08)."""
    from PySide6.QtWidgets import QMenu
    sw = page.sw
    key = next((d.key for d in sw.devices if d.connected), None)
    if key is None:
        check("try: Try for 5 minutes on a device (skipped: the test's devices are all disconnected)", True)
        return
    page._fill_use_menu()
    sub = next((a.menu() for a in page.use_menu.actions() if a.menu() is not None), None)
    profiles = len(sw.profiles())
    page.try_on(key)
    swt = os.path.join(sw.apo.config, "AutoEQ Studio", "switcher.txt")
    on = (sw.trial and sw.trial["key"], "_trying.txt" in open(swt).read(), len(sw.profiles()))
    sw.end_trial()
    check("try: Use on device › Try for 5 minutes on plays the result on that device (APO's file), not as a profile; "
          "its end puts the device's own EQ back", isinstance(sub, QMenu) and sub.actions() and on == (key, True, profiles)
          and sw.trial is None and "_trying.txt" not in open(swt).read(), (on, sub))


def guide_checks(page, wait_for):
    """The Guides (ui\\guide.py over ui\\tour.py): every step's control is there and in sight; a tour steps through
    and puts back what it opened; the tracer's runs on the sample graph and leaves the tracer as it was."""
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QMessageBox
    from ui import guide, tour
    page.resize(1100, 900)
    from PySide6.QtWidgets import QWidget
    from ui import help_window
    tagged = [w.property("help_key") for root in (page, page.tracer) for w in root.findChildren(QWidget)
              if w.property("help_key")]
    unknown = sorted({k for k in tagged if not help_window.help_key(k)})
    check("help: every control tagged for F1 (Make an EQ, the tracer) has a help text", len(tagged) > 60 and not unknown,
          (len(tagged), unknown))
    probs = tour.problems(page, guide.eq_steps(page))
    check("guide: every step of Make an EQ's Guide points at a control that's there and in sight", not probs, probs)
    fold = page.settings.fold.btn.isChecked()
    t = guide.start_eq(page)
    seen = []
    for _ in range(len(t.steps)):
        seen.append(t.title.text())
        t.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Right, Qt.NoModifier))
    check("guide: → steps through every step to Done; the Settings fold is as it was", len(set(seen)) == len(t.steps)
          and not t.isVisible() and page.settings.fold.btn.isChecked() == fold, (len(set(seen)), t.isVisible()))
    # the demos: each played to its end (fast), nothing of yours changed after (settings, the graph's view, the
    # slider, the file name), and a demo left half-way is put back too
    import json as _json
    before = _json.dumps(page.sw.s, sort_keys=True, default=str)
    before_S = _json.dumps(page.S, sort_keys=True, default=str)
    # (nothing a demo does may reach what changes your files or settings: every call to the EQ part is watched)
    real_call, changing = page.svc.call, []

    def watched(path, body=None):
        if path in ("/api/files/move", "/api/files/remove", "/api/use", "/api/presets/save", "/api/presets/delete",
                    "/api/presets/load", "/api/reset", "/api/settings", "/api/target/save", "/api/run", "/api/download"):
            changing.append(path)
        return real_call(path, body) if body is not None else real_call(path)
    page.svc.call = watched
    kept = (page.view_combo.currentIndex(), page.yrange_combo.currentIndex(), page.channels_chk.isChecked(),
            page.sa_what.text(), page.name_edit.text(), page.settings.fold.btn.isChecked())
    t = guide.start_eq(page)
    t.all_chk.setChecked(False)
    played, stuck = 0, []
    for i, st in enumerate(t.steps):
        t.go(i)
        if not tour._demo(st):
            continue
        t.speed = 40.0
        t.replay()
        if wait_for(lambda: not t.demo_running, 20):
            played += 1
        else:
            stuck.append(st["title"])
    # with Windows' animation effects off: numbered markers on the controls and the list in the card, nothing moved
    t.glide = False
    t.go(next(n for n, st in enumerate(t.steps) if st["title"] == "How an EQ job goes"))
    t.replay()
    marked = (len(t.markers), "1." in t.acts_lab.text() and "5." in t.acts_lab.text(), t.demo_running)
    t.glide = True
    views = next(n for n, st in enumerate(t.steps) if st["title"] == "Graph views")
    t.go(views)
    t.speed = 40.0
    t.replay()
    wait_for(lambda: page.view_combo.currentData() == "rel" or not t.demo_running, 20)
    mid = page.view_combo.currentData()
    # the card's own controls: Pause and Resume; the wheel scrolls the page and pauses the demo, Resume scrolls back
    t.go(next(n for n, st in enumerate(t.steps) if st["title"] == "Run"))
    t.speed = 1.0
    t.replay()
    wait_for(lambda: t.demo_running, 5)
    t.toggle_pause()
    paused = (t.paused, t.pause_btn.text())
    t.toggle_pause()
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QScrollArea
    area = next(a for a in page.findChildren(QScrollArea) if a.widget() and a.widget().isAncestorOf(page.run_btn))
    bar = area.verticalScrollBar()
    at = bar.value()
    pos = QPointF(area.viewport().mapTo(page.window(), QPoint(40, 40)))
    t.wheelEvent(QWheelEvent(pos, pos, QPoint(0, 0), QPoint(0, -240), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))
    scrolled = (bar.value() != at, t.paused_by_you, "Resume" in t.pause_btn.text())
    t.toggle_pause()
    resumed = (bar.value() == at, t.paused)
    t.speed = 40.0
    wait_for(lambda: not t.demo_running, 20)
    # the step list: every step by chapter; one chosen opens it
    t.count_btn.click()
    listed = t.step_list.isVisible() and t.step_list.list.count() > len(t.steps)
    item = next(t.step_list.list.item(k) for k in range(t.step_list.list.count())
                if t.step_list.list.item(k).data(Qt.UserRole) == 1)
    t.step_list._chosen(item)
    jumped = (t.i, t.step_list.isVisible())
    t.end()
    page.svc.call = real_call
    after = _json.dumps(page.sw.s, sort_keys=True, default=str)
    after_S = _json.dumps(page.S, sort_keys=True, default=str)
    now = (page.view_combo.currentIndex(), page.yrange_combo.currentIndex(), page.channels_chk.isChecked(),
           page.sa_what.text(), page.name_edit.text(), page.settings.fold.btn.isChecked())
    check("guide: every step's demo plays to its end, a view it shows is put back when the tour ends mid-demo, and "
          "nothing of yours changed (settings, the graph's view, the search chosen, the file name)",
          played >= 20 and not stuck and mid == "rel" and before == after and before_S == after_S and now == kept
          and not changing, (played, stuck, mid, before == after, before_S == after_S, now, kept, changing))
    check("guide: with Windows' animation effects off, a step's demo is numbered markers on its controls and a list "
          "in the card (nothing moves)", marked == (5, True, False), marked)
    check("guide: the card's Pause / Resume; the wheel scrolls the page and pauses the demo, Resume scrolls back; the "
          "step list (3 of 28 ▾) goes straight to a step",
          paused == (True, "▶ Resume") and scrolled == (True, True, True) and resumed == (True, False) and listed
          and jumped == (1, False), (paused, scrolled, resumed, listed, jumped))
    tw = page.tracer
    tw.show()
    real_q = QMessageBox.question
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    try:
        tw.remove_image()
    finally:
        QMessageBox.question = real_q
    t = guide.start_trace(tw)
    opened = tw.t.has_image and tw.sample_open
    probs = tour.problems(tw, guide.trace_steps(tw))
    t.go(7)  # (Auto trace: the sample's curves traced for it)
    traced = sum(map(tw.t.has_data, tw.t.curves))
    t.all_chk.setChecked(False)
    demos = 0
    for i, st in enumerate(t.steps):
        t.go(i)
        if tour._demo(st):
            t.speed = 40.0
            t.replay()
            demos += wait_for(lambda: not t.demo_running, 20)
    t.end()
    check("guide: the tracer's Guide opens the sample graph, every step's control is there, its demo traces the "
          "sample, and the tracer is empty again after", opened and not probs and traced >= 2 and not tw.t.has_image
          and not tw.sample_open and demos >= 7, (opened, probs, traced, demos))
    tw.close()


def trace_checks(page, wait_for):
    """The tracer (ui\\trace_core.py, ui\\trace_window.py) on AutoEQ Local's sample graph, drawn here: the axes found,
    the labels read (Windows' text reader, when this PC has one), three curves traced to within a fraction of a dB,
    editing, saving into the app."""
    import numpy as np
    from PySide6.QtWidgets import QMessageBox
    from ui import ocr
    from ui.trace_window import sample_image
    img, s = sample_image()
    page.open_trace()
    tw = page.tracer
    t = tw.t
    tw.load_image(img, "Sample IEM")
    check("trace: the gridlines and their frequencies found (20 Hz to 20 kHz, 28 lines), the frame, the clean colours",
          [g["v"] for g in t.grid_x][:3] == [20, 30, 40] and len(t.grid_x) == 28 and t.v["f2"] == "20000"
          and t.bg == (255, 255, 255) and t.v["tol"] == 45, (t.v, t.box))
    read = wait_for(lambda: not tw.reading, 60)
    try:
        ocr._get_engine()
        has_reader = True
    except ocr.Unavailable:
        has_reader = False
    check("trace: the axis labels read (+90 to +40 dB; the Hz labels match the gridlines), or said when Windows has no "
          "text reader", read and ((t.v["d1"], t.v["d2"]) == ("90", "40") and "frequency labels match" in t.axis_note
                                   if has_reader else "Couldn't read" in t.axis_note), t.axis_note)
    if not has_reader:
        t.v.update(d1="90", d2="40")
    msgs = [t.auto_trace() for _ in range(3)]
    errs = []
    for c, truth in zip(t.curves, (s["chans"][0], s["chans"][1], s["tgt"])):
        pts, _gaps = t.points(c["ys"])
        errs.append(round(max(abs(v - truth(f)) for f, v in pts), 2))
    check("trace: Auto trace finds the left and right channels and then the dashed target, each within 0.7 dB",
          [c["label"] for c in t.curves] == ["L", "R", "L2"] and max(errs) < 0.7 and "dashed" in msgs[0], (errs, msgs))
    check("trace: a pixel where two other lines blend into the target's grey isn't taken for it (within 0.2 dB)",
          errs[2] < 0.2, errs)
    # a dashed grey target in a JPEG (quality 50): it went off along the orange and green curves where they neared it
    # (7 dB), or wasn't found; the scales set as read on the clean picture (the same columns and rows)
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QImage
    from ui.trace_core import Tracer
    from ui.trace_window import rgb_of
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "JPG", 50)
    jp = QImage()
    jp.loadFromData(bytes(buf.data()), "JPG")
    tj = Tracer()
    tj.load(rgb_of(jp), "Sample IEM (JPEG)", True)
    tj.cal, tj.v["d1"], tj.v["d2"], tj.v["f1"], tj.v["f2"] = dict(t.cal), t.v["d1"], t.v["d2"], t.v["f1"], t.v["f2"]
    [tj.auto_trace() for _ in range(3)]
    grey = [c for c in tj.curves if c["colour"] and max(c["colour"]) - min(c["colour"]) < 45]
    jerr = round(max(abs(v - s["tgt"](f)) for f, v in tj.points(grey[0]["ys"])[0]), 2) if grey else None
    check("trace: the dashed grey target in a JPEG found by Auto trace and traced within 0.3 dB (it went along the "
          "coloured curves where they neared it)", jerr is not None and jerr < 0.3, (jerr, [c["colour"] for c in tj.curves]))
    tw.changed()
    n = int(np.isfinite(t.ys).sum())
    beside = t.erase(-50, 0, -10, t.H)  # (review 2: a box left of the picture erased nearly the whole curve)
    check("trace: Erase with a box beside the picture erases nothing", beside == 0
          and int(np.isfinite(t.ys).sum()) == n, (beside, n))
    t.erase(0, 0, t.W, t.H)
    erased = int(np.isfinite(t.ys).sum())
    t.undo()
    t.smooth()
    t.undo()
    t.redo()
    check("trace: Erase, Undo, Smooth and Redo", erased == 0 and int(np.isfinite(t.ys).sum()) == n and t.undo_stack, (n, erased))
    t.undo()
    t.cur = 0
    t.v["d1"] = ""
    tw.update_ui()
    try:
        t.outputs()
        missing = ""
    except ValueError as e:
        missing = str(e)
    check("trace: saving without a dB value says to type it", "Type the values" in missing
          and "Type the dB values" in tw.save_note.text(), (missing, tw.save_note.text()))
    t.v["d1"] = "90"
    t.v["tol"] = 70
    t.touched("tol")
    t.load(t.px, "Again")  # (another picture: its own automatic values again)
    tw.fit_and_show()
    t.v["tol"] = 70
    t.touched("tol")
    t.fit_settings()
    kept_tol = t.v["tol"]
    t.hand_back("tol")
    check("trace: a value you set is yours (kept by the automatic settings) until handed back",
          kept_tol == 70 and t.v["tol"] == 45 and not t.own("tol"), (kept_tol, t.v["tol"]))
    tw.load_image(img, "Sample IEM")
    wait_for(lambda: not tw.reading, 60)
    t.v.update(d1="90", d2="40")
    t.auto_trace()
    t.auto_trace()
    t.curves[0]["label"] = "R"
    try:
        t.outputs()
        same = ""
    except ValueError as e:
        same = str(e)
    t.curves[0]["label"] = "L"
    outs = t.outputs()
    check("trace: each curve its own file (“Sample IEM L.txt”, “… R.txt”, 48 points per octave); two named alike refused",
          [o["file"] for o in outs] == ["Sample IEM L.txt", "Sample IEM R.txt"] and "named “R”" in same
          and outs[0]["text"].startswith("* Traced from Sample IEM") and 470 < len(outs[0]["text"].splitlines()) < 480,
          ([o["file"] for o in outs], same, len(outs[0]["text"].splitlines())))
    real_info = QMessageBox.information
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    try:
        tw.save("measurement")
    finally:
        QMessageBox.information = real_info
    loaded = wait_for(lambda: page.curves is not None and page.curves.get("name") == "Sample IEM", 60)
    check("trace: Add as measurement puts the curves in the app as one device, in use (on the graph)",
          loaded and "2 files of one measurement" in tw.save_note.text()
          and [m["name"] for m in page.inputs["measurements"] if m["included"]] == ["Sample IEM L.txt", "Sample IEM R.txt"],
          (tw.save_note.text(), page.graph_title.text()))
    tw.close()


def listen_checks(page, sw, said, entry, qapp):
    """Listen: the sound (ui\\audio.py, rendered without a sound card) and the card (ui\\listen.py: Play's sound card
    replaced by a stand-in, so nothing is heard)."""
    import numpy as np
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QPushButton
    from ui import audio
    rms = lambda x: 20 * np.log10(np.sqrt(np.mean(np.asarray(x, float) ** 2)) + 1e-12)
    boost = [{"type": "PK", "freq": 1000, "gain": 6, "q": 1}]
    eng = audio.Engine(48000)
    eng.volume_db = 0
    eng.set_versions([("off", "EQ off", []), ("sel", "+6 dB at 1 kHz", boost)])
    eng.set_level_match(False)
    eng.set_source("tone")
    eng.tone_hz = 1000
    lv = {}
    for k in ("off", "sel"):
        eng.active = k
        eng.render(4800)
        lv[k] = rms(eng.render(4800)[:, 0])
    check("listen: each version plays through its own filters (+6 dB at 1 kHz, turned down by its boost: the same level)",
          abs(lv["off"] - lv["sel"]) < 0.1 and abs(lv["off"] + 16.99) < 0.1, lv)
    eng.set_level_match(True)
    g = {s["key"]: s["gain_db"] for s in eng.slots}
    peak, loud = audio.levels(boost, 48000)
    check("listen: level-matched, every version at the same A-weighted loudness, none above full scale",
          abs((g["off"] - g["sel"]) - loud) < 0.01 and max(g["sel"] + peak, g["off"]) <= 1e-9, (g, peak, loud))
    eng.active = "nothing"
    y = eng.render(4800)[:, 0]
    check("listen: a switch fades over a block (no click), then it's silent",
          rms(y[:1200]) > rms(y[-1200:]) + 6 and abs(y[-1]) < 0.01 and rms(eng.render(4800)) < -200, (rms(y[:1200]), rms(y[-1200:])))
    eng.ears, eng.left, eng.right = "split", "off", "sel"
    eng.render(4800)
    y = eng.render(4800)
    check("listen: a different version in each ear (left EQ off, right the EQ: louder at 1 kHz, level-matched)",
          rms(y[:, 1]) - rms(y[:, 0]) > 1, (rms(y[:, 0]), rms(y[:, 1])))
    check("listen: a filter above what the sound card can play is left out; the music loop at 44.1 and 48 kHz",
          len(audio.sos_of([{"freq": 30000, "gain": 3, "q": 1}], 48000)) == 0
          and all(audio.groove(sr).shape == (int(np.ceil(sr * 9.6)), 2) for sr in (44100, 48000)))
    # the card on the EQ screen
    lis = page.listen
    audio.Engine.start = lambda self: None  # (silent: no sound card)
    lis.src.setCurrentIndex(lis.src.findData("tone"))
    lis.source_changed()
    lis.ears.setCurrentIndex(0)
    lis.ears_changed()
    keys = [k for k, *_ in lis.versions()]
    lis.play()
    check("listen: the versions are EQ off, the selected EQ, then the EQs to compare; Play plays the selected EQ",
          keys[:2] == ["off", "sel"] and lis.playing and lis.engine.active == "sel"
          and [s["key"] for s in lis.engine.slots] == keys, (keys, lis.play_btn.text()))
    page.setFocus()
    page.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_1, Qt.NoModifier))
    k1 = lis.engine.active
    page.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_2, Qt.NoModifier))
    check("listen: keys 1 and 2 switch to EQ off and the selected EQ", (k1, lis.engine.active) == ("off", "sel"),
          (k1, lis.engine.active))
    page.draw_marker()
    check("listen: the tone's frequency is marked on the graph", page.marker.isVisible()
          and abs(10 ** page.marker.value() - lis.engine.tone_hz) < 0.5, (page.marker.value(), lis.engine.tone_hz))
    n = len(lis.pins)
    lis.add_selected()
    lis.add_selected()
    names = [it.name() for it in page.plot.listDataItems()]
    saved = page.svc.call("/api/listen", {"device": page.curves["name"]}).get("eqs") or []
    check("listen: Keep to compare adds the result once (kept for this IEM, on the graph, a version to hear)",
          len(lis.pins) == n + 1 and len(saved) == n + 1 and lis.pins[-1]["name"] in names
          and lis.pins[-1]["key"] in [s["key"] for s in lis.engine.slots]
          and any("already" in s for s in said), (len(lis.pins), names))
    lis.blind.setChecked(True)
    hidden = [b.text() for b in lis.ab_box.findChildren(QPushButton)]
    lis.reveal()
    shown = [b.text() for b in lis.ab_box.findChildren(QPushButton) if not b.isHidden()]
    check("listen: Blind test names the versions A, B, C … until Reveal",
          [t.split()[1] for t in hidden] == ["A", "B", "C"][:len(hidden)] and len(hidden) >= 3
          and all(" = " in t for t in shown), (hidden, shown))
    lis.blind.setChecked(False)
    lis.ears.setCurrentIndex(lis.ears.findData("split"))
    lis.ears_changed()
    check("listen: a different version in each ear (EQ off left, the EQ right; Swap)",
          (lis.engine.ears, lis.engine.left, lis.engine.right) == ("split", "off", "sel") and not lis.blind.isEnabled()
          and (lis.swap() or (lis.engine.left, lis.engine.right) == ("sel", "off")), (lis.engine.left, lis.engine.right))
    from ui.history_window import HistoryWindow
    hw = HistoryWindow(page, True)
    hw.listen_to(dict(entry, device="Another IEM", filters=[dict(f, gain=f["gain"] - 1) for f in entry["filters"]]))
    hw.close()
    check("listen: History's Listen adds an EQ made for another IEM, and says it won't sound as intended",
          len(lis.pins) == n + 2 and "made for Another IEM" in lis.pins[-1]["note"] and "won't sound" in said[-1], said[-1:])
    check("listen: the device's own EQ (Use on device switched it on) is said: it plays on top", lis.apo_box.isVisibleTo(lis)
          and "Headset" in lis.apo_text.text(), lis.apo_text.text())
    lis.device_eq_off()
    check("listen: Switch it off turns the device's EQ off", sw.record("Headset|EarPods")["active"] is None
          and not lis.apo_box.isVisibleTo(lis))
    lis._remove(lis.pins[-1])
    lis.stop()
    check("listen: ✕ removes an EQ to compare; Stop stops and the mark goes",
          len(lis.pins) == n + 1 and not lis.playing and not page.marker.isVisible() and lis.play_btn.text() == "▶ Play")
    qapp.processEvents()


def main():
    # (UTF-8 whatever the console: check names have characters like ⓘ and →, which Windows' console code page lacks)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parts = {"--inner-modules": module_checks, "--inner-requests": api_checks, "--inner-studio": studio_checks,
             "--inner-ui": ui_checks}
    if len(sys.argv) > 2 and sys.argv[1] in parts:
        part = parts[sys.argv[1]]
        try:
            part(sys.argv[2])
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            check(f"{part.__name__}: finished without an error", False)
        return 1 if any(not ok for ok, _, _ in results) else 0
    base, top = make_copy()
    print(f"Test copy: {top}", flush=True)
    failed = False
    # (studio last: its bring-over check puts stand-in settings, files and lists into the copy)
    for part, title in (("--inner-modules", "modules"), ("--inner-requests", "requests"), ("--inner-ui", "the EQ screen"),
                        ("--inner-studio", "studio")):
        print(f"-- {title}", flush=True)
        failed = subprocess.call([sys.executable, os.path.abspath(__file__), part, top]) != 0 or failed
    if "--keep" not in sys.argv and not remove_copy(base):
        print(f"Couldn't delete the test copy (a process still holds it?): {base}")
    print("\nAll checks passed." if not failed else "\nSome checks FAILED (see above).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
