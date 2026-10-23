"""Edge-case probe (AutoEQ Local's tools\\edge_probe.py, for AutoEQ Studio): odd files, names, settings, filters,
presets and malformed requests, tried on a copy of the app (app_copy.py: your own files, settings and Equalizer APO
are never used; it runs offline, so nothing is downloaded). Wider and slower than the self-test (a few minutes): run
it after bigger changes. One line per case:
  ok     it worked (with a short note of what came out)
  msg    it refused with a clear message
  CRASH  a Python error, or a message that reads like one: fix it, then add a test for it (tests\\<area>\\)

    .venv\\Scripts\\python.exe app\\tools\\edge_probe.py [--keep]
(Set PYTHONIOENCODING=utf-8 when writing the output to a file: some cases have non-English names.)
Besides AutoEQ Local's cases: every eq.service request with malformed bodies (the old server's are direct calls
here), the tracer on odd pictures, Listen's sound with odd filters, and EQ files the device part reads.
"""
import math
import os
import subprocess
import sys
import time

import app_copy  # (make_copy, use_copy, remove_copy)

TECHNICAL = ("Traceback", "NoneType", "object has no attribute", "could not convert", "index out of range",
             "unsupported operand", "not subscriptable", "Errno", "KeyError", "invalid literal", "list index",
             "division by zero", "not iterable", "unhashable", "expected str", "Expecting value", "WinError")
results = []


def case(name, fn, *a, **k):
    t = time.time()
    try:
        out = fn(*a, **k)
        note = out if isinstance(out, str) else repr(out)[:140]
        tag = "ok"
    except ValueError as e:
        note, tag = str(e), "msg"
        if any(w in note for w in TECHNICAL):
            tag = "CRASH"
    except Exception as e:  # noqa: BLE001
        note, tag = f"{type(e).__name__}: {e}", "CRASH"
    results.append((tag, name, note))
    print(f"{tag:5} {name}  [{time.time() - t:.1f}s]  {str(note)[:230]}", flush=True)


def fr(n=200, f0=20, f1=20000, fn=None):
    lines = []
    for i in range(n):
        f = f0 * (f1 / f0) ** (i / (n - 1))
        lines.append(f"{f:.3f}\t{(fn(f) if fn else 80 + 3 * math.sin(i / 9)):.3f}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- the EQ part's modules (inside the copy)
def modules(top):
    from eq import autoset, engines, exports, inputs, pipeline, settings
    cfg = settings.with_auto({})
    tgt_dir, meas_dir = inputs.TARGET_DIR, inputs.MEAS_DIR
    good_target = os.path.join(tgt_dir, os.listdir(tgt_dir)[0])
    probe_dir = os.path.join(top, "probe_files")
    os.makedirs(probe_dir, exist_ok=True)

    def load_meas(text, target=None):
        p = os.path.join(probe_dir, "probe.txt")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return pipeline.load(cfg, target or good_target, [p])

    def load_and_run(text, modes=("site_single", "best_fit"), target_text=None):
        tp = None
        if target_text is not None:
            tp = os.path.join(probe_dir, "probe_target.txt")
            with open(tp, "w", encoding="utf-8") as fh:
                fh.write(target_text)
        c, mt, tt = load_meas(text, target=tp)
        notes = [f"{len(c['f'])} pts, no-EQ {engines.rms_error(c['f'], c['meas'], c['target'], cfg['scoring']['band_hz']):.2f} dB"]
        for m in modes:
            run_cfg = settings.with_auto({"best_fit": {"filter_counts": [4], "seed_with_site": False}})
            pipeline.check_run(m, run_cfg, c)
            r = pipeline.run_mode(m, run_cfg, c, mt, tt)
            b = r["best"]
            notes.append(f"{m}: {b.get('n_filters')} filters, {b['rms']:.2f} dB, pre-amp {b.get('preamp')}")
        return "; ".join(notes)

    print("-- parsing and running odd files", flush=True)
    case("empty file: add", inputs.add_file, "measurement", "empty.txt", "")
    case("header only: add", inputs.add_file, "measurement", "hdr.txt", "Frequency\tdB\n")
    case("31 points: add", inputs.add_file, "measurement", "few.txt", fr(31))
    case("binary junk: add", inputs.add_file, "measurement", "junk.txt", "\x89PNG\r\n\x1a\n" + "\x00\xff" * 500)
    case("unsorted freqs: run", load_and_run, "".join(sorted(fr(300).splitlines(True), key=lambda l: hash(l) % 97)))
    case("duplicate freqs: run", load_and_run, "".join(l + l for l in fr(200).splitlines(True)))
    case("zero/negative freqs: run", load_and_run, "0\t80\n-10\t80\n" + fr(200))
    case("NaN/inf values: run", load_and_run, "100\tnan\n200\tinf\n" + fr(200))
    case("absurd dB 1e6: run", load_and_run, fr(200, fn=lambda f: 1e6))
    case("very quiet -200 dB: run", load_and_run, fr(200, fn=lambda f: -200))
    case("narrow band 1-2 kHz: run", load_and_run, fr(200, 1000, 2000))
    case("kHz units 0.02-20: run", load_and_run, fr(200, 0.02, 20))
    case("3 columns (phase): run", load_and_run, "".join(l.rstrip("\n") + "\t-45.0\n" for l in fr(200).splitlines(True)))
    case("scientific notation: run", load_and_run,
         "".join(f"{float(a):.4E} {float(b):.4E}\n" for a, b in (l.split("\t") for l in fr(200).splitlines())))
    case("REW header with * comments: run", load_and_run, "* Measurement data measured by REW\n* Freq(Hz) SPL(dB) Phase\n" + fr(200))
    case("CR-only line ends: run", load_and_run, fr(200).replace("\n", "\r"))
    case("decimal commas + semicolons: run", load_and_run, fr(200).replace(".", ",").replace("\t", ";"))
    case("flat line = target: run", load_and_run, fr(200, fn=lambda f: 75), target_text=fr(200, fn=lambda f: 75))
    case("identical to target: run", load_and_run, open(good_target, encoding="utf-8", errors="replace").read())
    case("200k lines: load", lambda: load_meas(fr(200000))[0]["f"].shape)
    case("huge spike +80 dB at 1k: run", load_and_run, fr(400, fn=lambda f: 80 + (80 if 990 < f < 1010 else 0)))

    print("-- file names", flush=True)
    ok = fr(100)
    for n in ["../../evil.txt", "..\\..\\evil2.txt", "C:\\Windows\\x.txt", "CON", "nul.txt", "a" * 300 + ".txt",
              "名前 ÄÖ.txt", " .txt", "x.csv.exe", "", None, "   ", "a:b*c?.txt", "trailing. ", ".hidden"]:
        case(f"add name {n!r}"[:50], lambda n=n: (inputs.add_file("measurement", n, ok), "ESCAPED" if any(
            os.path.exists(os.path.join(d, e)) for d in (top, os.path.dirname(top)) for e in ("evil.txt", "evil2.txt"))
            else "stayed inside"))
    for n in ["", ".", "..", "../target", "nope.txt"]:
        case(f"remove name {n!r}", lambda n=n: (inputs.remove_file("measurement", n),
                                                "folder still there" if os.path.isdir(meas_dir) else "FOLDER GONE"))
    for n in ["", ".", "..", "nope.txt"]:
        case(f"move name {n!r}", lambda n=n: (inputs.move_file("target", n),
                                              f"target folder {'there' if os.path.isdir(tgt_dir) else 'GONE'}, "
                                              f"measurement folder {'there' if os.path.isdir(meas_dir) else 'GONE'}"))

    print("-- settings", flush=True)
    for bad in [{"site_sweep": {"gain_ranges": "abc"}}, {"site_sweep": {"gain_ranges": [[1]]}},
                {"site_sweep": {"filter_rows": [-5, 0, 100]}}, {"best_fit": {"filter_counts": []}},
                {"scoring": {"band_hz": [20000, 20]}}, {"scoring": {"band_hz": "x"}}, {"scoring": None},
                {"files": {"excluded": "x"}}, {"files": {"active_target": 5}}, {"auto": {"manual": "x"}},
                {"export": {"apo_folder": 7}}, {"mode": "nope"}, {"site_sweep": {"q_max": [float("nan")]}},
                {"performance": {"cores": -3}}, {"best_fit": {"gain_max": [1e308]}},
                {"databases": {"extra": "x", "disabled": 5}}, {"library": {"folders": "C:\\"}}, [], "text", 5]:
        case(f"with_auto {bad!r}"[:70],
             lambda bad=bad: (lambda c: f"band {c['scoring']['band_hz']}, rows {c['site_sweep']['filter_rows']}")(settings.with_auto(bad)))
    big = settings.with_auto({"site_sweep": {"freq_high": list(range(1000, 21000, 10)), "q_max": [0.5 + i / 100 for i in range(300)]}})
    case("huge sweep: estimate", lambda: autoset.fmt_time(autoset.estimate(big, "site_sweep")))
    case("huge sweep: run refused", lambda: pipeline.check_run("site_sweep", big, load_meas(fr(200))[0]))
    bigfit = settings.with_auto({"best_fit": {"gain_max": [i / 4 for i in range(80)], "q_max": [0.5 + i / 10 for i in range(60)]}})
    case("huge best fit: run refused", lambda: pipeline.check_run("best_fit", bigfit, load_meas(fr(200))[0]))
    case("one line repeated: add", inputs.add_file, "measurement", "same.txt", "1000 80\n" * 5000)

    print("-- presets", flush=True)
    for n in ["", "   ", "../evil", "CON", "a" * 300, "名前", "x/y", "x\\y", ".", ".."]:
        case(f"save preset {n!r}"[:40], lambda n=n: (settings.save_preset(n, cfg), settings.list_presets()[-3:]))
    case("load missing preset", settings.load_preset, "nope-nope")
    case("delete missing preset", settings.delete_preset, "nope-nope")

    print("-- saving filters", flush=True)
    for label, filters in [("no filters", []), ("freq 0", [{"type": "PK", "freq": 0, "gain": 3, "q": 1}]),
                           ("freq -100", [{"type": "PK", "freq": -100, "gain": 3, "q": 1}]),
                           ("freq 1e9", [{"type": "PK", "freq": 1e9, "gain": 3, "q": 1}]),
                           ("q 0", [{"type": "PK", "freq": 1000, "gain": 3, "q": 0}]),
                           ("q -1", [{"type": "PK", "freq": 1000, "gain": 3, "q": -1}]),
                           ("gain 500", [{"type": "PK", "freq": 1000, "gain": 500, "q": 1}]),
                           ("200 filters", [{"type": "PK", "freq": 100 + i * 50, "gain": 1, "q": 1} for i in range(200)])]:
        def save(filters=filters, label=label):
            f = exports.clean_filters(filters)
            out = os.path.join(top, "probe_out")
            written, pre = exports.write(settings.with_auto({"export": {k: True for k in exports.FORMATS}}),
                                         f, -3, "probe " + label, out_dir=out, notes=[])
            g = open(written["graphic"], encoding="utf-8").read()
            return f"{sorted(written)} pre-amp {pre}; GraphicEQ has nan/inf: {'nan' in g.lower() or 'inf' in g.lower()}"
        case(f"save: {label}", save)


# ---------------------------------------------------------------- eq.service: every request, malformed
def requests():
    from eq import service

    def call(path, body):
        r = service.call(path, body)
        text = str(r.get("error", "")) if isinstance(r, dict) else ""
        if any(w in text for w in TECHNICAL):
            raise RuntimeError(text)
        if text:
            raise ValueError(text)
        return str(r)[:100]

    skip = {"/api/open"}  # (opens Explorer windows)
    print("-- requests: malformed bodies on every route", flush=True)
    for r in sorted(p for p in service.ROUTES if p not in skip):
        for label, body in [("a list", [1, 2]), ("empty", {}),
                            ("wrong types", {"settings": "x", "name": 5, "kind": [], "filters": "x", "id": {"a": 1},
                                             "mode": 7, "preamp": "x", "files": 3, "content": 9, "names": 4,
                                             "device": [], "eqs": "x", "text": 5, "keys": "x", "query": 3})]:
            case(f"{r} {label}", call, r, body)
    case("unknown route", call, "/api/nope", {})
    case("50 MB file", call, "/api/files/add", {"kind": "measurement", "name": "big.txt", "content": "1 2\n" * 12_500_000})


# ---------------------------------------------------------------- AutoEQ Studio's own parts
def studio():
    import numpy as np
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ui import audio, trace_core
    print("-- the tracer on odd pictures", flush=True)
    rng = np.random.default_rng(1)
    for label, img in [("1x1", np.zeros((1, 1, 3), np.uint8)), ("all white", np.full((300, 400, 3), 255, np.uint8)),
                       ("all black", np.zeros((300, 400, 3), np.uint8)),
                       ("noise", rng.integers(0, 256, (300, 400, 3), dtype=np.uint8)),
                       ("one line", np.where(np.arange(400)[None, :, None] == 200, 0, 255).repeat(300, 0).astype(np.uint8)),
                       ("tall 4000x20", np.full((4000, 20, 3), 255, np.uint8))]:
        def trace(img=img):
            t = trace_core.Tracer()
            note = t.load(np.broadcast_to(img, img.shape).copy(), "probe")
            msg = t.auto_trace()
            t.v.update(d1="90", d2="40")
            try:
                t.outputs()
                saved = "saved"
            except ValueError as e:
                saved = str(e)
            return f"{note[:60]} | {msg[:60]} | {saved[:50]}"
        case(f"tracer: {label}", trace)
    print("-- Listen's sound with odd filters", flush=True)
    for label, filters in [("none", []), ("freq 0", [{"type": "PK", "freq": 0, "gain": 3, "q": 1}]),
                           ("above Nyquist", [{"type": "PK", "freq": 30000, "gain": 3, "q": 1}]),
                           ("gain 60", [{"type": "PK", "freq": 1000, "gain": 60, "q": 1}]),
                           ("q 0.001", [{"type": "PK", "freq": 1000, "gain": 3, "q": 0.001}]),
                           ("30 filters", [{"type": "PK", "freq": 50 + i * 600, "gain": 2, "q": 2} for i in range(30)])]:
        def play(filters=filters):
            e = audio.Engine(48000)
            e.set_versions([("off", "off", []), ("x", "x", filters)])
            e.active = "x"
            e.set_source("pink", audio.noise(48000, True, seconds=1))
            y = np.concatenate([e.render(4800) for _ in range(5)])
            if not np.isfinite(y).all():
                raise RuntimeError("not finite sound")
            return f"peak {np.max(np.abs(y)):.3f}"
        case(f"listen: {label}", play)
    print("-- EQ files the device part reads", flush=True)
    from switcher import eqfile
    d = os.path.join(os.environ["AUTOEQSTUDIO_DATA"], "probe_eq")
    os.makedirs(d, exist_ok=True)
    for label, text in [("empty", ""), ("binary", "\x00\xff" * 400), ("only comments", "# x\n# y\n"),
                        ("UTF-16", None), ("huge", "Filter: ON PK Fc 1000 Hz Gain 1 dB Q 1\n" * 50000)]:
        p = os.path.join(d, label + ".txt")
        if text is None:
            open(p, "wb").write("Preamp: -3 dB\nFilter: ON PK Fc 100 Hz Gain 3 dB Q 1\n".encode("utf-16"))
        else:
            open(p, "w", encoding="utf-8", errors="replace").write(text)
        case(f"eq file: {label}", lambda p=p: str(eqfile.read_eq(p))[:80])


def inner(top):
    app_copy.use_copy(top)
    import net
    net.set_offline(True)  # (nothing fetched: a probe never downloads)
    modules(top)
    requests()
    studio()
    return min(100, sum(1 for r in results if r[0] == "CRASH"))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 2 and sys.argv[1] == "--inner":  # (in its own process: its crashes as the exit code)
        return inner(sys.argv[2])
    base, top = app_copy.make_copy()
    print("copy:", top, flush=True)
    crashes = subprocess.call([sys.executable, os.path.abspath(__file__), "--inner", top])
    if "--keep" not in sys.argv and not app_copy.remove_copy(base):
        print(f"Couldn't delete the copy (a process still holds it?): {base}")
    print(f"\n{crashes or 'No'} crash(es)." + (" See the CRASH lines above." if crashes else ""))
    return 1 if crashes else 0


if __name__ == "__main__":
    sys.exit(main())
