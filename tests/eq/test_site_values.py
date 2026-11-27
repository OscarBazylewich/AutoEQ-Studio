"""The Website values of each graph website (eq\\site_values.py): a website's files read (made-up texts: the real
websites' code is not in the app), the shipped table (app\\eq\\site_values.json) and its counts, which database a
measurement is from, which values and fixed gain and Q ranges each method and choice gives, with the gray line's
words, and the values read again Online (a stood-in download: the tests never go online)."""
import json
import os
import threading
import time
import urllib.error

import pytest

from eq import compare, databases, rigs, service, settings, site_values

COVERS_FILES = ("app/eq/site_values.json",)

HBB = "https://hbb.squig.link/"
L800 = "https://listener800.github.io/5128iem.html"
SQUIG = "https://squig.link/"
HANGOUT = "https://graph.hangout.audio/iem/711/"
MADE_UP = "https://made-up-for-a-test.squig.link/"

# A squig.link website's files as their template has them (the values, and the panel without gain or Q boxes)
SQUIG_CONFIG = """
// PHONE_BOOK = "phone_book.json"
const default_normalization = "dB",  // dB or Hz
      default_norm_db = 60,
      default_norm_hz = 500,
      extraEQEnabled = true,
      extraEQBands = 10,
      extraEQBandsMax = 20;
"""
SQUIG_GRAPHTOOL = """
<span><input name="autoeq-from" type="number" value="20"></input></span>
<span><input name="autoeq-to" type="number" value="20000"></input></span>
let smooth_level = 5, smooth_scale = 0.01*(typeof scale_smoothing !== "undefined" ? scale_smoothing : 1);
const iso223_params = { // :2003
    a_f : [0.532, 0.506, 0.480],
};
"""
EQUALIZER = """
Equalizer = (function() {
    let config = {
        DefaultSampleRate: 48000,
        TrebleStartFrom: {treble},
        AutoEQRange: [20, 15000],
        OptimizeQRange: [0.5, 2],
        OptimizeGainRange: [-12, 12],
    };
    let autoeq = function (fr, target, maxFilters) { return []; };
    return { config, autoeq };
})();
"""
# listener800's: Hz~ (with its graph tool's range mode), its own smoothing and table, gain and Q boxes with clamps
L800_CONFIG = 'default_normalization = "Hz~", default_norm_db = 60, default_norm_hz = 500, scale_smoothing = 0.2,' \
              ' extraEQEnabled = true, extraEQBandsMax = 50;'
L800_GRAPHTOOL = """
<input name="autoeq-from"><input name="autoeq-to"><input name="autoeq-gain-from"><input name="autoeq-gain-to">
<input name="autoeq-q-from"><input name="autoeq-q-to">
let smooth_level = 3, smooth_scale = 0.1*scale_smoothing;
let norm_fr_range = true;
const iso223_params = { // Updated to comply with both ISO 226:2023 as well as ISO 389-7:2019
    a_f : [0.635, 0.602],
};
let autoEQGainTo = Math.min(Math.max(parseInt(autoEQGainToInput.value) || 0, autoEQGainFrom), 20);
let autoEQQTo = Math.min(Math.max(parseFloat(autoEQQToInput.value) || 0, autoEQQFrom), 5);
"""


def _texts(config=SQUIG_CONFIG, graphtool=SQUIG_GRAPHTOOL, equalizer=None, page=""):
    eq = EQUALIZER.replace("{treble}", "7000") if equalizer is None else equalizer
    return {"config": config, "graphtool": graphtool, "equalizer": eq, "page": page}


def _cfg(profile="auto", mode="site_sweep", **auto):
    cfg = settings.with_auto({})
    cfg["site"]["profile"], cfg["mode"] = profile, mode
    cfg["auto"].update(auto)
    return cfg


# ---------------------------------------------------------------- reading a website's files
def test_parse_the_two_known_sets(monkeypatch, check):
    squig = site_values.parse(_texts())
    l800 = site_values.parse(_texts(L800_CONFIG, L800_GRAPHTOOL, EQUALIZER.replace("{treble}", "15000")))
    check("site values: the files of a squig.link website give the usual set (7000, 0.1, 5, dB, 500, 60, ISO 226:2003)",
          squig["values"] == site_values.USUAL and squig["missing"] == [], squig)
    check("site values: listener800's files give its own set (15000, 0.2, 3, Hz~, 500, 60, ISO 226:2023), the app's "
          "own values", l800["values"] == site_values.APP_VALUES and l800["missing"] == [], l800)
    p, q = squig["panel"], l800["panel"]
    check("site values: a panel with only frequency boxes has no gain or Q boxes, its fixed ranges from equalizer.js",
          p["freq_boxes"] and not p["gain_boxes"] and not p["q_boxes"] and p["gain_range"] == [-12, 12]
          and p["q_range"] == [0.5, 2] and p["freq_range"] == [20, 15000] and p["rows_max"] == 20, p)
    check("site values: listener800's panel has gain and Q boxes, its clamps (20 dB, Q 5) and 50 rows",
          q["gain_boxes"] and q["q_boxes"] and (q["gain_cap"], q["q_cap"], q["rows_max"]) == (20, 5, 50), q)
    monkeypatch.setattr(site_values, "USUAL_CODE", site_values.code_hash(EQUALIZER.replace("{treble}", "1")))
    check("site values: the AutoEQ code is the usual one by its fingerprint (its settings above it may differ), else "
          "other", site_values.parse(_texts())["code"] == "usual"
          and site_values.parse(_texts(equalizer=EQUALIZER.replace("return [];", "return [1];")))["code"] == "other")


def test_parse_what_is_not_there(check):
    hz = site_values.parse(_texts(config=SQUIG_CONFIG.replace('"dB"', '"Hz~"')))
    check("site values: Hz~ without the graph tool's range mode reads as Hz", hz["values"]["normalization"] == "Hz", hz)
    commented = site_values.parse(_texts(config=SQUIG_CONFIG.replace("default_norm_hz = 500", "// default_norm_hz = 800")))
    check("site values: a commented-out setting is not read (missing)", "norm_hz" in commented["missing"], commented)
    none = site_values.parse(_texts(config=SQUIG_CONFIG.replace("extraEQEnabled = true,", ""), equalizer=""))
    check("site values: without equalizer.js, TrebleStartFrom is missing, the code is none (no AutoEQ button) and "
          "no panel", "treble_start_from" in none["missing"] and none["code"] == "none" and none["panel"] is None, none)
    far = site_values.parse(_texts(config=SQUIG_CONFIG.replace("default_norm_db = 60", "default_norm_db = 400")))
    check("site values: a value out of the setting's limits is missing, never used", "norm_db" in far["missing"], far)
    modern = site_values.parse({"config": 'const CONFIG = { NORMALIZATION: { TYPE: "Avg", HZ_VALUE: 500 } };'})
    check("site values: modernGraphTool: its frequency read, an unknown levelling word missing, its code unknown",
          modern["values"] == {"norm_hz": 500} and "normalization" in modern["missing"] and modern["code"] == "unknown"
          and modern["panel"] is None, modern)
    other_panel = site_values.parse(_texts(graphtool=SQUIG_GRAPHTOOL.replace("autoeq-from", "x").replace("autoeq-to", "y")))
    check("site values: a website with another AutoEQ panel (no autoeq-from or autoeq-to boxes) has no panel: nothing "
          "is fixed", other_panel["panel"] is None, other_panel)
    in_page = site_values.parse(_texts(graphtool="", page='name="autoeq-to" name="autoeq-gain-to" name="autoeq-q-to"'))
    check("site values: the panel's boxes are also found in the page itself (Hangout.Audio's has its graph tool in "
          "it)", in_page["panel"] and in_page["panel"]["gain_boxes"] and in_page["panel"]["q_boxes"], in_page)


# ---------------------------------------------------------------- the shipped table
def test_shipped_table(check):
    with open(site_values.TABLE_PATH, encoding="utf-8") as fh:
        t = json.load(fh)
    rows = t["sites"]
    keys = {"name", "url", "values", "missing", "code", "panel", "panel_missing"}
    check("site values: the table was read on 2026-11-24 and has the 155 graph websites", t["read"] == "2026-11-24"
          and len(rows) == 155, (t["read"], len(rows)))
    bad = [k for k, r in rows.items() if set(r) != keys or k != databases.norm_url(r["url"])
           or set(r["values"]) | set(r["missing"]) != set(site_values.KEYS)
           or not all(site_values.valid(x, v) for x, v in r["values"].items())]
    check("site values: every row has its keys, its address as the key, each of the 7 values read or missing, every "
          "value within the settings' limits and choices", not bad, bad[:5])
    complete = [r for r in rows.values() if not r["missing"]]
    panels = [r["panel"] for r in rows.values() if r["panel"]]
    counts = (len(complete), sum(r["code"] == "usual" for r in rows.values()), len(panels),
              sum(p["gain_boxes"] for p in panels), sum(p["q_boxes"] for p in panels),
              sum(not p["gain_boxes"] for p in panels), sum(not p["q_boxes"] for p in panels))
    check("site values: the counts of the survey: 144 complete rows, 141 with the usual code, 142 classic panels, 38 "
          "with gain boxes, 41 with Q boxes, 104 with gain fixed, 101 with Q fixed",
          counts == (144, 141, 142, 38, 41, 104, 101), counts)
    sets = {json.dumps(r["values"], sort_keys=True) for r in complete}
    check("site values: 19 different complete sets of the 7 values", len(sets) == 19, len(sets))
    check("site values: listener800's two databases have the app's own values (Best fit's)",
          all(rows[databases.norm_url(u)]["values"] == site_values.APP_VALUES
              for u in (L800, "https://listener800.github.io/")))
    check("site values: 80 websites have the usual squig.link set", sum(r["values"] == site_values.USUAL for r in complete) == 80)
    caps = {(p["gain_cap"], p["q_cap"]) for p in panels if p["gain_boxes"] and p["gain_cap"]}
    check("site values: every panel with gain boxes whose clamps were read clamps at 20 dB and Q 5 (the settings' limits "
          "for the Website methods: settings.LIMITS)", caps == {(20, 5)}
          and settings.LIMITS["site_single.gain_max"]["max"] == 20 and settings.LIMITS["site_single.q_max"]["max"] == 5, caps)


def test_choices(check):
    ch = site_values.choices(settings.with_auto({"databases": {"extra": ["https://my-own.squig.link/"]}}))
    urls = [databases.norm_url(v[5:]) for v, _ in ch]
    check("site values: the list has every graph website once, the pages that you added too, and not AutoEq (GitHub)",
          len(urls) == len(set(urls)) and len(urls) >= 155 and "https://my-own.squig.link" in urls
          and databases.norm_url(databases.SITES[0]["url"]) not in urls and all(v.startswith("site:http") for v, _ in ch),
          len(urls))


# ---------------------------------------------------------------- which database a measurement is from
def test_site_of(fresh_studio, check):
    rigs.record_source(["A L.txt", "A R.txt"], {"site_url": HBB, "site": "HBB"})
    rigs.record_source(["B L.txt"], {"site_url": L800, "site": "listener800 5128 IEMs"})
    rigs.record_source(["G L.txt"], {"site_url": databases.SITES[0]["url"], "site": "AutoEq"})
    rigs.record_source(["Avg.txt"], {"site": "average", "rig": "711", "of": ["x (HBB)", "y (HBB)"], "of_sites": [HBB, HBB]})
    rigs.record_source(["Old avg.txt"], {"site": "average", "rig": "711", "of": ["x (HBB)"]})
    got = [site_values.site_of(n) for n in (["A L.txt", "A R.txt"], ["Dropped (HBB) L.txt"], ["A L.txt", "B L.txt"],
                                           ["G L.txt"], ["Avg.txt"], ["Old avg.txt"], [], ["A L.txt", "Dropped L.txt"])]
    check("site values: a measurement recorded from a database is from it; a dropped file (a database's name in its "
          "name too), an AutoEq (GitHub) file and an average made before are files; two databases are mixed; an average "
          "of one database's measurements is from it",
          got == [(HBB, "site"), (None, "file"), (None, "mixed"), (None, "file"), (HBB, "site"), (None, "file"),
                  (None, "none"), (None, "mixed")], got)


def test_average_records_its_websites(fresh_studio, eq_cfg, monkeypatch, check):
    monkeypatch.setattr(compare, "average", lambda keys, name: (
        "Avg sites.txt", "".join(f"{20 * 1.1 ** k:.2f}\t{80 + k % 5}\n" for k in range(80)), "711", ["a", "b"]))
    monkeypatch.setattr(compare, "average_sites", lambda keys: [HBB, HBB])
    service.compare_average({"keys": ["x", "y"], "settings": eq_cfg})
    check("site values: an average records the website of each of its measurements (of_sites)",
          rigs.sources()["Avg sites.txt"].get("of_sites") == [HBB, HBB], rigs.sources().get("Avg sites.txt"))


# ---------------------------------------------------------------- which values, and the gray line
def test_resolve_for_each_method_and_choice(fresh_studio, check):
    rigs.record_source(["H L.txt"], {"site_url": HBB, "site": "HBB"})
    hbb = site_values.table_entry(HBB)
    web = site_values.resolve(_cfg(), "site_sweep", ["H L.txt"])
    check("site values: the database of the measurement, a Website method: that database's values, its gain and Q fixed",
          web["values"] == {"site." + k: v for k, v in hbb["values"].items()} and web["applied"]
          and web["locks"]["site_single.gain_min"]["value"] == -12 and web["locks"]["site_sweep.q_max"]["value"] == [2], web)
    check("site values: the gray line names the database, the day its values were read and what is fixed",
          web["note"] == "HBB: values from its website (read 2026-11-24). No gain or Q boxes on its AutoEQ panel, so "
                         "gain -12 to 12 dB and Q 0.5–2 are fixed.", web["note"])
    bf = site_values.resolve(_cfg(mode="best_fit"), "best_fit", ["H L.txt"])
    check("site values: Best fit keeps the app's own values, also for a database's measurement",
          bf["values"] == {"site." + k: v for k, v in site_values.APP_VALUES.items()}
          and bf["note"] == "Best fit keeps its own values; the database's values are for the Website methods", bf)
    chosen = site_values.resolve(_cfg("site:" + L800), "site_single", ["Dropped L.txt"])
    check("site values: a website chosen by name gives its values for any file, and nothing is fixed where its panel "
          "has the boxes", chosen["values"]["site.normalization"] == "Hz~" and not chosen["locks"]
          and chosen["note"] == "listener800 5128 IEMs: values from its website (read 2026-11-24)", chosen)
    other = site_values.resolve(_cfg("custom"), "site_sweep", ["H L.txt"])
    check("site values: Other gives no values and fixes nothing", not other["values"] and not other["applied"]
          and not other["locks"] and other["note"] == "Other: values below stay as you set them", other)
    f = site_values.resolve(_cfg(), "site_single", ["Dropped L.txt"])
    check("site values: a measurement from a file: the usual squig.link values, nothing fixed, and the line says to "
          "select the website", f["values"] == {"site." + k: v for k, v in site_values.USUAL.items()} and not f["locks"]
          and f["note"] == "Measurement isn't from a database, so the usual squig.link values apply. To copy a "
                           "website, select it in this list.", f)
    rigs.record_source(["L L.txt"], {"site_url": L800, "site": "listener800 5128 IEMs"})
    mixed = site_values.resolve(_cfg(), "site_single", ["H L.txt", "L L.txt"])
    check("site values: measurements of two databases: the usual values, and the line says so",
          mixed["note"].startswith("Measurements are from more than one database, so the usual squig.link values apply.")
          and mixed["values"]["site.treble_start_from"] == 7000, mixed["note"])
    off = site_values.resolve(_cfg(enabled=False), "site_sweep", ["H L.txt"])
    check("site values: Automatic settings off: nothing is written, the line says so, the fixed values stay",
          not off["applied"] and off["locks"] and off["note"].startswith(
              "Automatic settings are off: values below stay as you set them. No gain or Q boxes"), off["note"])
    shown = site_values.resolve(_cfg(), "site_sweep", ["H L.txt"], as_is=True)
    check("site values: an EQ from History shown: its values as they are (the website's fixed values stay)",
          not shown["applied"] and not shown["values"] and shown["locks"] == web["locks"]
          and shown["note"] == "Showing the values of the EQ from History", shown)


def test_the_gray_line_of_odd_websites(check):
    hang = site_values.resolve(_cfg("site:" + HANGOUT), "site_sweep", [])
    check("site values: values that couldn't be read are named, and the usual ones used",
          hang["note"] == "Hangout.Audio IEMs (Crinacle, 711): values from its website (read 2026-11-24). Couldn't read "
                          "Smoothing scale, Smoothing level, and Loudness tables, so these use the usual squig.link "
                          "values." and hang["values"]["site.smooth_level"] == 5 and not hang["locks"], hang)
    sq = site_values.resolve(_cfg("site:" + SQUIG), "site_sweep", [])
    check("site values: a website with changed AutoEQ code: the warning line, nothing fixed (its panel is another)",
          sq["note"].endswith("Runs changed AutoEQ code, so results may differ from the website.") and not sq["locks"],
          sq["note"])
    bry = site_values.resolve(_cfg("site:https://bryaudioreviews.squig.link/"), "site_sweep", [])
    check("site values: a website with no AutoEQ button says so (its missing TrebleStartFrom is not named)",
          bry["note"] == "Bry Audio Reviews: values from its website (read 2026-11-24). No AutoEQ button on its "
                         "website.", bry["note"])
    new = site_values.resolve(_cfg("site:" + MADE_UP), "site_single", [])
    check("site values: a website not read yet: the usual values, and the line says so",
          new["note"] == f"{MADE_UP}: values not read yet, so the usual squig.link values apply", new["note"])


def test_apply_leaves_your_values(check):
    cfg = _cfg("site:" + HBB, manual=["site.smooth_level"])
    cfg["site"]["smooth_level"] = 9
    site_values.apply(cfg, "site_sweep", [])
    check("site values: apply writes the website's values, not one that you typed", cfg["site"]["smooth_level"] == 9
          and cfg["site"]["norm_hz"] == site_values.table_entry(HBB)["values"]["norm_hz"], cfg["site"])
    off = _cfg("site:" + HBB, enabled=False)
    before = dict(off["site"])
    site_values.apply(off, "site_sweep", [])
    check("site values: with Automatic settings off apply writes nothing", off["site"] == before)


# ---------------------------------------------------------------- the fixed values in a run
def test_lock(check):
    cfg = _cfg("site:" + HBB, manual=["site_single.gain_max", "site_sweep.q_max"])
    cfg["site_single"].update(gain_min=-6, gain_max=4, q_max=4)
    cfg["site_sweep"]["q_max"] = [1, 3]
    info = site_values.resolve(cfg, "site_single", [])
    one = site_values.lock(json.loads(json.dumps(cfg)), info, "site_single")
    sweep = site_values.lock(json.loads(json.dumps(cfg)), info, "site_sweep")
    bf = site_values.lock(json.loads(json.dumps(cfg)), info, "best_fit")
    check("site values: a Website run on a website without gain and Q boxes uses its fixed ranges, over your values, "
          "with its panel's clamps", (one["site_single"]["gain_min"], one["site_single"]["gain_max"],
                                      one["site_single"]["q_min"], one["site_single"]["q_max"]) == (-12, 12, 0.5, 2)
          and one["panel"] == {"gain_cap": 12, "q_cap": 2}, one["site_single"])
    check("site values: the sweep tries only the website's gain range and Q range",
          sweep["site_sweep"]["gain_ranges"] == [[-12, 12]] and sweep["site_sweep"]["q_max"] == [2]
          and sweep["site_sweep"]["q_min"] == 0.5, sweep["site_sweep"])
    check("site values: a Best fit run is not changed", "panel" not in bf and bf["site_single"] == cfg["site_single"])
    aqua = next(r["url"] for r in json.load(open(site_values.TABLE_PATH, encoding="utf-8"))["sites"].values()
                if r["panel"] and r["panel"]["rows_max"] < 20)
    a = site_values.resolve(_cfg("site:" + aqua), "site_sweep", [])
    c = _cfg("site:" + aqua)
    c["site_single"]["rows"], c["site_sweep"]["filter_rows"] = 15, [4, 8, 12, 16]
    check("site values: a website with fewer filter rows (10) keeps the runs within them, and its line says so",
          site_values.lock(json.loads(json.dumps(c)), a, "site_single")["site_single"]["rows"] == 10
          and site_values.lock(json.loads(json.dumps(c)), a, "site_sweep")["site_sweep"]["filter_rows"] == [4, 8]
          and "Up to 10 filter rows on its AutoEQ panel." in a["note"], a["note"])


def test_notes_and_the_automatic_answer(check):
    cfg = _cfg("site:" + HBB)
    info = site_values.resolve(cfg, "site_sweep", [])
    notes = site_values.notes(info, "site_sweep")
    check("site values: About these settings has a line for each fixed value",
          [n["text"] for n in notes] == ["Gain -12 to 12 dB: fixed on HBB (no gain boxes)",
                                         "Q 0.5–2: fixed on HBB (no Q boxes)"] and all(n["lock"] for n in notes), notes)
    an = {"n_files": 2, "data_top": 20000, "unstable_from": None, "agree_to": None, "band_top": 10000, "band_why": "default",
          "score_top": 10000, "need_boost": 8.0, "boost_at": 3000, "need_cut": -6.0, "cut_at": 100, "features": 6,
          "q_need": 3.0, "q_at": 4000, "bass_step": 0.0, "treble_step": 0.0, "no_eq_rms": 3.0}
    a = service.auto({"settings": cfg, "analysis": an, "site_values": json.loads(json.dumps(info))})
    paths = {n["path"]: n for n in a["notes"]}
    check("site values: the automatic answer has the gray line's words and the fixed lines in place of the automatic "
          "gain and Q lines, never the website's 7 values (they are not written into the settings); its search tries "
          "one gain range and one Q",
          not any(p in a["values"] for p in site_values.PATHS) and paths["site.profile"]["text"] == info["note"]
          and paths["site_sweep.gain_ranges"].get("lock") and paths["site_sweep.q_max"].get("lock")
          and "1 gain range × 1 Q limit" in a["search"], (a["search"], a["notes"]))
    bf = service.auto({"settings": _cfg("site:" + HBB, mode="best_fit"), "analysis": an,
                       "site_values": site_values.resolve(_cfg("site:" + HBB, mode="best_fit"), "best_fit", [])})
    check("site values: with Best fit the answer has no Website value and no website line",
          not any(p in bf["values"] for p in site_values.PATHS)
          and "site.profile" not in {n["path"] for n in bf["notes"]}, bf["notes"])
    odd = [service.call("/api/auto", {"settings": cfg, "analysis": an, "site_values": s}) for s in (
        {"locks": {"site_sweep.gain_ranges": {"value": "x"}, "site_sweep.q_max": 3, "other": {"value": [1]}},
         "caps": {"q_cap": "5"}, "rows_max": True, "values": {"site.smooth_level": 2, "best_fit.q_max": [9]}, "applied": 1},
        {"locks": [], "note": 5}, "text")]
    check("site values: odd Website values in the automatic request are left out, never an error, never a setting "
          "other than the 7", all("error" not in a and "best_fit.q_max" not in a["values"] for a in odd),
          [a.get("error") for a in odd])


# ---------------------------------------------------------------- read again, Online
@pytest.fixture
def own_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(site_values, "CACHE_PATH", str(tmp_path / "site_values.json"))
    yield str(tmp_path / "site_values.json")
    site_values.forget_memory()


def _fake_site(requests, treble="6000", fail=None):
    page = '<script src="config.js"></script><script src="graphtool.js"></script><script src="equalizer.js"></script>'
    files = {"": page, "config.js": SQUIG_CONFIG, "graphtool.js": SQUIG_GRAPHTOOL,
             "equalizer.js": EQUALIZER.replace("{treble}", treble)}

    def get(url, **k):
        requests.append((url, k.get("timeout")))
        if fail:
            raise fail
        return files[url[len(MADE_UP):]], url
    return get


def test_refresh_offline_makes_no_request(own_cache, check):
    asked = []
    r = site_values.refresh(MADE_UP, get=_fake_site(asked))
    check("site values: offline, nothing is read again and no request is made", r == "skipped" and not asked, (r, asked))


def test_refresh_online(online, own_cache, check):
    asked = []
    r = site_values.refresh(MADE_UP, get=_fake_site(asked))
    e = site_values.table_entry(MADE_UP)
    check("site values: online, a website not read is read (its page and three scripts, 5 s each at most) and kept",
          r == "read" and len(asked) == 4 and {t for _u, t in asked} == {5} and e["values"]["treble_start_from"] == 6000
          and json.load(open(own_cache, encoding="utf-8"))[databases.norm_url(MADE_UP)]["values"]["treble_start_from"]
          == 6000, (r, asked))
    note = site_values.resolve(_cfg("site:" + MADE_UP), "site_single", [])["note"]
    check("site values: the next values come from what was read, with its day",
          note.startswith(f"{MADE_UP}: values from its website (read {time.strftime('%Y-%m-%d')})"), note)
    again = []
    check("site values: read again within 30 days: no request",
          site_values.refresh(MADE_UP, get=_fake_site(again)) == "skipped" and not again, again)
    later = site_values.refresh(MADE_UP, get=_fake_site(again, treble="8000"), now=time.time() + 31 * 24 * 3600)
    check("site values: after 30 days it is read again", later == "read" and len(again) == 4
          and site_values.table_entry(MADE_UP)["values"]["treble_start_from"] == 8000, later)


def test_refresh_refused_and_failed(online, own_cache, check):
    asked = []
    refused = urllib.error.HTTPError(MADE_UP, 403, "made in the test", None, None)
    r1 = site_values.refresh(MADE_UP, get=_fake_site(asked, fail=refused))
    r2 = site_values.refresh(MADE_UP, get=_fake_site(asked), now=time.time() + 6 * 24 * 3600)
    r3 = site_values.refresh(MADE_UP, get=_fake_site(asked), now=time.time() + 8 * 24 * 3600)
    check("site values: a refusal (HTTP 403) is kept, not tried again for 7 days, then tried again",
          (r1, r2, r3) == ("refused", "skipped", "read") and len(asked) == 5, (r1, r2, r3, asked))
    site_values.forget_memory()
    asked = []
    s1 = site_values.refresh(HBB, get=_fake_site(asked, fail=OSError("no network")), now=time.time() + 40 * 24 * 3600)
    check("site values: a failed try is kept quiet: the shipped values stay", s1 == "failed"
          and site_values.table_entry(HBB)["read"] == "2026-11-24", s1)


def test_refresh_never_replaces_good_values_with_less(online, own_cache, check):
    # (the review of feature 5, 2026-11-26: a maintenance page that answers 200 replaced HBB's values and its fixed
    # gain and Q with nothing for 30 days)
    later = time.time() + 40 * 24 * 3600
    before = site_values.table_entry(HBB)
    pages = {"maintenance": lambda u, **k: ("<html><body>Site under maintenance</body></html>", u),
             "no graph tool scripts": lambda u, **k: ('<script src="config.js"></script>', u) if u == HBB
             else (SQUIG_CONFIG, u)}
    got = {}
    for name, get in pages.items():
        if os.path.exists(own_cache):  # (each case from no cache: a failed try waits a day)
            os.remove(own_cache)
        site_values.forget_memory()
        r = site_values.refresh(HBB, get=get, now=later)
        e = site_values.table_entry(HBB)
        got[name] = (r, e["values"] == before["values"], e["panel"] == before["panel"], e["read"],
                     site_values.due(HBB, now=later + 3600), site_values.due(HBB, now=later + 25 * 3600))
    check("site values: a read that finds no graph tool, or fewer values or panel facts than the row before, is a "
          "failed try: the older values and fixed ranges stay, and the next try comes after a day",
          all(g == ("failed", True, True, "2026-11-24", False, True) for g in got.values()), got)
    site_values.forget_memory()
    same = site_values.refresh(MADE_UP, get=_fake_site([]))
    fewer = site_values.refresh(MADE_UP, get=_fake_site([], treble="x"), now=time.time() + 31 * 24 * 3600)
    check("site values: a read as complete as the row before replaces it; one with a value fewer does not",
          (same, fewer) == ("read", "failed") and site_values.table_entry(MADE_UP)["values"]["treble_start_from"] == 6000,
          (same, fewer))


def test_refresh_soon_never_waits(online, own_cache, monkeypatch, check):
    release, asked = threading.Event(), []

    def slow(url, **k):
        asked.append(url)
        release.wait(30)
        raise OSError("released")
    monkeypatch.setattr(databases, "get_function", lambda: slow)
    t0 = time.monotonic()
    t = site_values.refresh_soon(MADE_UP)
    took = time.monotonic() - t0
    release.set()
    t.join(30)
    check("site values: refresh_soon returns at once while the website is slow, and reads it in a thread of its own",
          took < 1 and asked == [MADE_UP] and not t.is_alive(), (took, asked))
    check("site values: refresh_soon starts nothing when the values are new (the shipped table, 30 days)",
          site_values.refresh_soon(HBB) is None)


def test_files_add_does_not_wait_for_the_website(online, own_cache, fresh_studio, eq_cfg, monkeypatch, check):
    release = threading.Event()
    started = []

    def slow(site, get=None, timeout=20):
        started.append(site["url"])
        release.wait(30)
        raise OSError("released")
    monkeypatch.setattr(databases, "graph_tool_files", slow)
    monkeypatch.setattr(site_values, "MAX_AGE", 0)  # (HBB's shipped values due again)
    t0 = time.monotonic()
    r = service.files_add({"kind": "measurement", "name": "Traced HBB L.txt",
                           "content": "".join(f"{20 * 1.1 ** k:.2f}\t{80 + k % 5}\n" for k in range(80)),
                           "settings": eq_cfg, "source": {"site_url": HBB, "site": "HBB", "name": "Traced"}})
    took = time.monotonic() - t0
    release.set()
    site_values.wait()
    check("site values: a trace from a website is added at once, and its database's values are read in the "
          "background", took < 5 and r["names"] == ["Traced HBB L.txt"] and started == [HBB], (took, started))
