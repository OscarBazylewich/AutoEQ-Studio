"""The EQ apps and their layouts (eq\\eq_apps.py, eq\\layouts.py): a device's limits leave ranges to fit in, a run
outside them still makes filters, your own filters take a device's room first, a graphic EQ app's sliders, a shared
layout's band count, each EQ app described with a known layout and file, and a choice kept (an old device key
becoming the app's). Moved from eq_checks.py's module_checks.

The run on a device (a range outside it) starts a pool of worker processes, as the app's runs do
(AUTOEQSTUDIO_MAX_WORKERS caps it: 2 in the tests)."""
from eq import autoset, eq_apps, exports, layouts, pipeline, settings


def dv(lay, n=0, **bf):
    """Best fit's settings for a layout, kept within the device's (with n filters of your own: eq_checks.py line
    265)."""
    return layouts.device_settings(settings.with_auto({"best_fit": {"layout": lay, **bf}})["best_fit"], n)


def test_ranges_outside_a_device_become_its_own(check):
    # a device's limits leave ranges to fit in (an inverted frequency range or Q from = Q max: every fit failed, an
    # EQ with no filters)
    md, qx, mi = (dv("app:moondrop_free_dsp", freq_range=[12000, 20000]), dv("app:qudelix_5k", q_min=8, q_max=[10, 12]),
                  dv("app:minidsp_2x4hd", q_min=0.1, q_max=[0.3]))
    # was eq_checks.py:268
    check("devices: ranges outside a device's become the device's (never empty)", md["freq_range"] == [40, 10000]
          and (qx["q_min"], qx["q_max"]) == (0.1, [7]) and (mi["q_min"], mi["q_max"]) == (0.5, [6]),
          (md["freq_range"], qx["q_min"], qx["q_max"], mi["q_min"], mi["q_max"]))


def test_a_run_outside_the_device_makes_filters(sample_curves, check):
    # (a pool of worker processes)
    curves, mt, tt = sample_curves
    cm2 = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": {
        "layout": "app:moondrop_free_dsp", "freq_range": [12000, 20000], "filter_counts": [3], "gain_max": [3],
        "q_max": [2], "random_starts": 1, "seed_with_site": False}})
    rs = pipeline.run_mode("best_fit", cm2, curves, mt, tt)["results"]
    # was eq_checks.py:275
    check("devices: a run with a range outside the device's makes filters", all(r["filters"] for r in rs), rs[:1])


def test_your_filters_take_room_first(check):
    # your own filters and the shelves never overfill a device (Voicemeeter: 6 cells, 5 of yours + 2 shelves + 1 = 8)
    vm = lambda n: dv("app:voicemeeter", n, low_shelf=True, high_shelf=True, filter_counts=[1, 2, 3])
    v5, v6 = vm(5), vm(6)
    # was eq_checks.py:279
    check("devices: your filters take room first, then the shelves go, then nothing is added",
          (v5["low_shelf"], v5["high_shelf"], v5["filter_counts"], v5.get("start_add", True)) == (False, False, [1], True)
          and v6.get("start_add") is False, (v5, v6))


def test_graphic_eq_apps_keep_their_sliders(check):
    # a graphic EQ app's sliders: its stated range and steps, whatever best_fit.bands was left at
    fx = settings.with_auto({"best_fit": {"layout": "app:fxsound", "bands": {"gain_min": -16, "gain_max": 16, "step": 0.1}}})
    # was eq_checks.py:292
    check("graphic EQ apps: their sliders' range and steps are kept (FxSound ±12 dB in 1 dB)",
          layouts.sliders(fx["best_fit"]) == (-12, 12, 1.0) and "1 dB steps" in autoset.describe(dict(fx, mode="best_fit")),
          (layouts.sliders(fx["best_fit"]), autoset.describe(dict(fx, mode="best_fit"))))


def test_shared_layout_band_count(check):
    # was eq_checks.py:327
    check("EQ apps: a shared layout's band count from the layout itself; no empty 'Devices' group",
          eq_apps.summary("boom3d").startswith("31 graphic EQ bands") and eq_apps.summary("spotify").startswith("6 graphic EQ bands")
          and {x["group"] for x in layouts.listing()} == {"Any", "Graphic EQ", "EQ apps (Your EQ app)"},
          (eq_apps.summary("boom3d"), {x["group"] for x in layouts.listing()}))


def test_each_eq_app_described(check):
    # the EQ apps (eq_apps.py): each described, sourced, with a layout Best fit knows and a file the app can write.
    # (the text survey, 2026-11-23: the steps to load the EQ, "how", went; "note" is the one line of limits that the ⓘ
    # of Your EQ app shows, with no end period and no "how" beside it)
    bad_apps = [k for k, a in eq_apps.APPS.items()
                if not (a["name"] and a["note"] and not a["note"].endswith(".") and "how" not in a
                        and a.get("source", "").startswith("http") and a["platforms"]
                        and set(a["platforms"]) <= set(eq_apps.PLATFORMS) and a["kind"] in ("parametric", "graphic", "curve", "site")
                        and eq_apps.layout_key(k) in layouts.KEYS and (a.get("file") is None or a["file"] in exports.FORMATS))]
    # was eq_checks.py:516
    check("EQ apps: each has platforms, a source, its one line of limits, a known layout and file", not bad_apps, bad_apps)


def test_eq_app_choice_kept(check):
    c_app = settings.with_auto({"eq_app": "poweramp", "best_fit": {"layout": "moondrop_free_dsp"}})
    bf_vm = dict(settings.DEFAULTS["best_fit"], layout="app:voicemeeter", filter_counts=[3, 6, 20], low_shelf=True, high_shelf=True)
    # was eq_checks.py:519
    check("EQ apps: a choice is kept, an old device key becomes the app's; an app's shelves take its bands (Voicemeeter 6)",
          c_app["eq_app"] == "poweramp" and c_app["best_fit"]["layout"] == "app:moondrop_free_dsp"
          and settings.with_auto({"eq_app": "nope"})["eq_app"] == ""
          and layouts.device_settings(bf_vm)["filter_counts"] == [3, 4], (c_app["eq_app"], layouts.device_settings(bf_vm)["filter_counts"]))


def test_notes_of_peace_and_neutron(check):
    # (2026-11-24: "(±60 dB max)" left the note of Peace, as no source of Peace states it; Neutron's store pages
    # state 4 to 130 bands)
    notes = {k: eq_apps.APPS[k]["note"] for k in ("peace", "neutron")}
    check("EQ apps: the note of Peace is “Up to 31 bands · ±30 dB” and that of Neutron “4–130 bands”, and Peace "
          "stays a device of 31 bands and ±30 dB",
          notes == {"peace": "Up to 31 bands · ±30 dB", "neutron": "4–130 bands"}
          and layouts.capacity("app:peace") == 31 and layouts.DEVICES["app:peace"]["gain"] == (-30, 30), notes)


# ---------------------------------------------------------------- FxSound's band counts
def test_fxsound_ten_bands_are_those_of_fxsound(check):
    # (a repair: the app had 10 bands from 20 Hz to 20 kHz with Q 1.0; FxSound 1.2.14.0 and later has 62.5 Hz to
    # 16 kHz with Q 1.598: GraphicEqSet.cpp, the source in eq_apps.py)
    freqs, q = layouts.bands({"layout": "app:fxsound"})
    check("FxSound: its 10 bands start at 62.5 Hz and end at 16 kHz, with Q 1.598",
          len(freqs) == 10 and (freqs[0], freqs[-1]) == (62.5, 16000) and q == 1.598, (freqs, q))


def test_fxsound_offers_its_five_counts(check):
    sets = eq_apps.band_sets("fxsound")
    # the Q of FxSound for a count: max(1, sqrt(r) / (r - 1)), r the ratio of two bands next to each other
    # (GraphicEqSet.cpp lines 106-116 and 512-524, the source in eq_apps.py)
    def fx_q(freqs):
        r = (freqs[-1] / freqs[0]) ** (1 / (len(freqs) - 1))
        return max(1.0, r ** 0.5 / (r - 1))
    check("FxSound: offers 5, 10, 15, 20 and 31 bands, each set with that many rising frequencies",
          layouts.counts("app:fxsound") == [5, 10, 15, 20, 31] == sorted(sets)
          and all(len(f) == n and f == sorted(set(f)) for n, (f, _q) in sets.items()), {n: len(f) for n, (f, _q) in sets.items()})
    check("FxSound: the Q of each count is 1.0, 1.598, 2.148, 2.828 and 4.333, as its formula gives",
          [sets[n][1] for n in sorted(sets)] == [1.0, 1.598, 2.148, 2.828, 4.333]
          and all(abs(fx_q(f) - q) < 0.0006 for f, q in sets.values()),
          [(sets[n][1], round(fx_q(sets[n][0]), 4)) for n in sorted(sets)])
    check("FxSound: the ends of each set (5 and 10: 62.5 Hz to 16 kHz; 15: 25 Hz; 20: 20 Hz; 31: 20 Hz to 20 kHz)",
          {n: (f[0], f[-1]) for n, (f, _q) in sets.items()} == {5: (62.5, 16000), 10: (62.5, 16000), 15: (25, 16000),
                                                                20: (20, 16000), 31: (20, 20000)},
          {n: (f[0], f[-1]) for n, (f, _q) in sets.items()})
    check("FxSound: bands() gives the set of a count, and the default set with no count",
          all(layouts.bands({"layout": "app:fxsound"}, n) == (sets[n][0], sets[n][1]) for n in sets)
          and layouts.bands({"layout": "app:fxsound"}) == (sets[10][0], sets[10][1]))
    check("layouts: the summary of FxSound names its band counts",
          layouts.summary("app:fxsound") == "5, 10, 15, 20, or 31 bands: Best fit adjusts only their gains.",
          layouts.summary("app:fxsound"))
    none = {k: layouts.counts(k) for k in ("app:foobar2000", "graphic_10", "bands", "any", "app:peace")}
    check("layouts: foobar2000, the 10-band graphic EQ, Your bands and the parametric layouts have no band counts",
          all(v == [] for v in none.values()), none)


def test_fxsound_bands_are_the_tables_of_its_source(check):
    # The tables a second time, from the source: GraphicEqSet.cpp lines 118-250 and 430-492 of fxsound-app (main,
    # file commit 5246dbd9 of 2026-08-22, fetched 2026-11-24): a changed inner frequency of eq_apps.py (115.734 ->
    # 120 Hz) passed every other check, which look at the number of bands, the two ends and the Q
    iso_31 = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000,
              2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]  # (the ISO 1/3-octave centres)
    source = {5: [62.5, 250, 1000, 4000, 16000],
              10: [62.5, 115.734, 214.311, 396.85, 734.867, 1360.79, 2519.84, 4666.12, 8640.48, 16000],
              15: [25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000, 16000],
              20: [20, 31.5, 40, 63, 80, 125, 160, 250, 315, 500, 630, 1000, 1250, 2000, 2500, 4000, 5000, 8000, 10000,
                   16000],
              31: iso_31}
    sets = eq_apps.band_sets("fxsound")
    wrong = {n: [(a, b) for a, b in zip(sets[n][0], f) if a != b] or len(sets[n][0]) - len(f)
             for n, f in source.items() if list(sets.get(n, ([],))[0]) != f}
    check("FxSound: every frequency of its 5, 10, 15, 20 and 31 bands is the one of the tables of FxSound",
          sorted(sets) == sorted(source) and not wrong, wrong)
    # (FxSound makes its 10 bands by a formula: evenly on a log scale from 62.5 Hz to 16 kHz)
    by_formula = [62.5 * 256 ** (i / 9) for i in range(10)]
    check("FxSound: its 10 bands are 62.5 Hz × 256^(i/9), within 0.01 Hz",
          all(abs(a - b) < 0.01 for a, b in zip(sets[10][0], by_formula)),
          [(a, round(b, 3)) for a, b in zip(sets[10][0], by_formula)])


def test_count_of_a_card(check):
    sets = eq_apps.band_sets("fxsound")
    shown = lambda n: [round(f, 1) for f in sets[n][0]]  # (as the filter table shows a frequency: 115.7)
    found = {"each count": [layouts.count_of("app:fxsound", sets[n][0]) for n in sorted(sets)],
             "as shown, another order": layouts.count_of("app:fxsound", list(reversed(shown(10)))),
             "one band moved": layouts.count_of("app:fxsound", [70.0, *sets[10][0][1:]]),
             "a filter added": layouts.count_of("app:fxsound", [*sets[15][0], 300.0]),
             "a band removed": layouts.count_of("app:fxsound", sets[10][0][:-1]),
             "10 other filters": layouts.count_of("app:fxsound", [100.0 + 100 * i for i in range(10)]),
             "no filters": layouts.count_of("app:fxsound", []), "not numbers": layouts.count_of("app:fxsound", ["x"]),
             "a layout with no counts": layouts.count_of("graphic_10", sets[10][0])}
    check("layouts: the band count of a card is known by the frequencies of all its filters: exactly the bands of one "
          "count, else none",
          found == {"each count": [5, 10, 15, 20, 31], "as shown, another order": 10, "one band moved": None,
                    "a filter added": None, "a band removed": None, "10 other filters": None, "no filters": None,
                    "not numbers": None, "a layout with no counts": None}, found)
