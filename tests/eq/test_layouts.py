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


# ---------------------------------------------------------------- what the user sets per EQ app (best_fit.per_app)
def peace(n=0, per=None, **bf):
    """Best fit's settings for Peace kept within what the user set for it (per: best_fit.per_app.peace, None: an old
    settings file with no such key), with n filters of your own."""
    cfg = settings.with_auto({"best_fit": {"layout": "app:peace", **bf}})["best_fit"]
    if per is None:
        cfg.pop("per_app")
    else:
        cfg["per_app"]["peace"] = per
    return layouts.device_settings(cfg, n), cfg


def test_peace_bands_limit_the_filter_counts(check):
    before = repr(layouts.DEVICES["app:peace"])
    wide = {"filter_counts": list(range(1, 33)), "low_shelf": True}
    ten, _ = peace(per={"bands": 10, "gain": 30}, **wide)
    one, _ = peace(per={"bands": 1, "gain": 30}, **wide)
    two, _ = peace(per={"bands": 2, "gain": 30}, **wide)
    check("Peace: 10 bands with the low shelf on leave filter counts to 9",
          max(ten["filter_counts"]) == 9 and ten["low_shelf"] is True, (ten["filter_counts"], ten["low_shelf"]))
    check("Peace: 1 band is 1 filter with the shelf off; 2 bands are 1 filter and the shelf",
          (one["filter_counts"], one["low_shelf"]) == ([1], False) and (two["filter_counts"], two["low_shelf"]) == ([1], True),
          (one["filter_counts"], one["low_shelf"], two["filter_counts"], two["low_shelf"]))
    check("Peace: the app's own limits stay as they are after the user's values were used (layouts.DEVICES)",
          repr(layouts.DEVICES["app:peace"]) == before and layouts.DEVICES["app:peace"]["bands"] == 31
          and layouts.DEVICES["app:peace"]["gain"] == (-30, 30), layouts.DEVICES["app:peace"])


def test_peace_max_gain_limits_boost_and_cut(check):
    gains = {"gain_min": -16, "gain_max": [6, 20, 35]}
    g12, _ = peace(per={"bands": 31, "gain": 12}, **gains)
    g30, _ = peace(per={"bands": 31, "gain": 30}, **gains)
    g60, _ = peace(per={"bands": 31, "gain": 60}, **gains)
    check("Peace: max gain 12 raises the minimum gain to -12 and leaves no maximum gain above 12",
          (g12["gain_min"], g12["gain_max"]) == (-12, [6, 12]), (g12["gain_min"], g12["gain_max"]))
    check("Peace: max gain 60 keeps a maximum gain of 35 dB (30 stops it at 30); the minimum gain stays -16",
          (g60["gain_min"], g60["gain_max"]) == (-16, [6, 20, 35]) and (g30["gain_min"], g30["gain_max"]) == (-16, [6, 20, 30]),
          (g60["gain_max"], g30["gain_max"]))


def test_peace_without_the_setting_is_as_before(check):
    wide = {"filter_counts": list(range(1, 33)), "low_shelf": True, "gain_min": -16, "gain_max": [6, 20, 35]}
    old, old_cfg = peace(per=None, **wide)
    new, _ = peace(per={"bands": 31, "gain": 30}, **wide)
    new.pop("per_app")
    check("Peace: settings with no best_fit.per_app give the result of before (31 bands, ±30 dB)",
          old == new and max(old["filter_counts"]) == 30 and old["gain_max"] == [6, 20, 30]
          and layouts.capacity(old_cfg) == 31, (old["filter_counts"][-1], old["gain_max"]))
    odd = [peace(per=p, **wide)[0] for p in ("x", {"bands": "x", "gain": None}, {"bands": True, "gain": -4},
                                             {"bands": 500, "gain": 0})]
    check("Peace: values of a wrong kind in best_fit.per_app are the app's own (a run never fails on them)",
          all((max(o["filter_counts"]), o["gain_max"]) == (30, [6, 20, 30]) for o in odd),
          [(max(o["filter_counts"]), o["gain_max"]) for o in odd])


def test_capacity_and_summary_follow_the_users_values(check):
    _, bf = peace(per={"bands": 10, "gain": 12})
    check("Peace: capacity is the user's 10 bands for the settings and the app's 31 for the key; other layouts as before",
          layouts.capacity(bf) == 10 and layouts.capacity("app:peace") == 31 and layouts.capacity("any") is None
          and layouts.capacity("app:voicemeeter") == 6 and layouts.capacity({"layout": "app:fxsound"}) is None,
          (layouts.capacity(bf), layouts.capacity("app:peace")))
    check("Peace: the summary of the layout says the numbers in use",
          layouts.summary("app:peace", bf) == "Peace (for Equalizer APO) limits: up to 10 peaking/shelf filters, gain -12 to +12 dB"
          and layouts.summary("app:peace") == "Peace (for Equalizer APO) limits: up to 31 peaking/shelf filters, gain -30 to +30 dB"
          # (the settings of another layout change nothing for this one)
          and layouts.summary("app:peace", dict(bf, layout="any")) == layouts.summary("app:peace"),
          (layouts.summary("app:peace", bf), layouts.summary("app:peace")))
    _, one = peace(per={"bands": 1, "gain": 30})
    check("Peace: the summary of the layout with 1 band says “1 peaking/shelf filter”",
          layouts.summary("app:peace", one) == "Peace (for Equalizer APO) limits: up to 1 peaking/shelf filter, gain -30 to +30 dB",
          layouts.summary("app:peace", one))


def test_peace_note_follows_the_two_numbers(check):
    check("EQ apps: the note of Peace is made from its form and the user's two numbers",
          eq_apps.note("peace", {"bands": 10}) == "Up to 10 bands · ±30 dB"
          and eq_apps.note("peace", {"bands": 10, "gain": 12, "other": 1}) == "Up to 10 bands · ±12 dB"
          and eq_apps.note("peace") == eq_apps.APPS["peace"]["note"] == "Up to 31 bands · ±30 dB"
          and eq_apps.note("apo") == "No limits" and eq_apps.APPS["neutron"]["note"] == "4–130 bands",
          (eq_apps.note("peace", {"bands": 10}), eq_apps.note("peace")))
    check("EQ apps: the note of Peace with 1 band says “Up to 1 band”",
          eq_apps.note("peace", {"bands": 1}) == "Up to 1 band · ±30 dB" and eq_apps.note("peace", {"bands": 2}) == "Up to 2 bands · ±30 dB",
          eq_apps.note("peace", {"bands": 1}))


def test_user_items_are_the_one_description(check):
    items = {k: eq_apps.user_items(k) for k in eq_apps.APPS}
    with_items = {k: [i["name"] for i in v] for k, v in items.items() if v}
    keys = {"name", "path", "label", "kind", "limit", "default", "auto", "auto_name", "placeholder"}
    wrong = [(k, i.get("name")) for k, v in items.items() for i in v
             if not (set(i) == keys and i["path"] == f"best_fit.per_app.{k}.{i['name']}" and i["label"]
                     and i["kind"] in ("num", "intlist") and {"min", "max"} <= set(i["limit"])
                     and isinstance(i["auto"], bool) and bool(i["auto_name"]) == i["auto"]
                     and (isinstance(i["default"], list)) == (i["kind"] == "intlist") == bool(i["limit"].get("list")))]
    check("EQ apps: Peace has the items bands and gain, FxSound the item band_counts, the other apps none; each item "
          "has every key that the settings and the form read",
          with_items == {"peace": ["bands", "gain"], "fxsound": ["band_counts"]} and not wrong, (with_items, wrong))
    by = {i["name"]: i for i in items["peace"] + items["fxsound"]}
    check("EQ apps: the labels, limits and defaults of the three items",
          [(i["label"], i["limit"], i["default"], i["auto"], i["placeholder"]) for i in by.values()] == [
              ("Peace bands", {"min": 1, "max": 31, "int": True}, 31, False, None),
              ("Peace max gain (± dB)", {"min": 1, "max": 99, "int": True, "unit": "dB"}, 30, False, None),
              ("Band counts to try", {"min": 5, "max": 31, "int": True, "list": True, "of": [5, 10, 15, 20, 31]}, [10],
               True, "e.g., 10 or 10, 31")]
          and by["band_counts"]["auto_name"] == "Band counts",
          [(i["label"], i["limit"], i["default"]) for i in by.values()])
    check("EQ apps: the defaults of best_fit.per_app are made from the items",
          eq_apps.user_defaults() == {"peace": {"bands": 31, "gain": 30}, "fxsound": {"band_counts": [10]}}
          == settings.DEFAULTS["best_fit"]["per_app"], eq_apps.user_defaults())


def test_listings_keep_their_keys(check):
    apps, lays = eq_apps.listing(), layouts.listing()
    old_app = {"key", "name", "platforms", "kind", "layout", "file", "summary", "note", "source", "approx", "bands_gain",
               "bands_step"}
    by = {a["key"]: a for a in apps}
    others = [a["key"] for a in apps if a["key"] not in ("peace", "fxsound")
              and (a["user"] != [] or a["note_form"] is not None or a["user_defaults"] != {} or a["band_counts"] is not None)]
    check("EQ apps: the listing for the page keeps its keys and adds user, note_form, user_defaults and band_counts",
          all(set(a) == old_app | {"user", "note_form", "user_defaults", "band_counts"} for a in apps), sorted(apps[0]))
    check("EQ apps: the new listing fields are empty for every other app",
          not others and len(apps) == len(eq_apps.APPS) > 2, (others, len(apps)))
    check("EQ apps: the listing of Peace has its form and defaults, that of FxSound its band counts",
          by["peace"]["note_form"] == "Up to {bands} {band_word} · ±{gain} dB" and by["peace"]["user_defaults"] == {"bands": 31, "gain": 30}
          and [i["path"] for i in by["peace"]["user"]] == ["best_fit.per_app.peace.bands", "best_fit.per_app.peace.gain"]
          and by["fxsound"]["band_counts"] == [5, 10, 15, 20, 31] and by["fxsound"]["summary"].startswith("10 graphic EQ bands")
          and by["fxsound"]["user_defaults"] == {"band_counts": [10]}, (by["peace"]["user_defaults"], by["fxsound"]["band_counts"]))
    lay = {x["key"]: x for x in lays}
    check("layouts: the listing for the page keeps its keys and adds the band counts of a layout (FxSound's five; "
          "none for the others)",
          all(set(x) == {"key", "name", "group", "summary", "fixed", "shelves", "counts"} for x in lays)
          and lay["app:fxsound"]["counts"] == [5, 10, 15, 20, 31]
          and not [k for k, x in lay.items() if k != "app:fxsound" and x["counts"]]
          and lay["app:fxsound"]["fixed"] is True and lay["app:peace"]["shelves"] is True,
          (sorted(lays[0]), lay["app:fxsound"]["counts"]))


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


def test_counts_to_try(check):
    fx = lambda counts: {"layout": "app:fxsound", "per_app": {"fxsound": {"band_counts": counts}}}
    found = {"none": layouts.counts_to_try(fx([])), "not offered": layouts.counts_to_try(fx([12])),
             "some": layouts.counts_to_try(fx([31, 12, 5, 5])), "all": layouts.counts_to_try(fx([5, 10, 15, 20, 31])),
             "wrong kind": layouts.counts_to_try(fx("x")), "old settings": layouts.counts_to_try({"layout": "app:fxsound"}),
             # (a list of another app is never used for this one)
             "another app's": layouts.counts_to_try({"layout": "app:fxsound", "per_app": {"peace": {"band_counts": [31]}}})}
    check("FxSound: the counts to try are the stored counts that it offers, else its default 10",
          found == {"none": [10], "not offered": [10], "some": [5, 31], "all": [5, 10, 15, 20, 31], "wrong kind": [10],
                    "old settings": [10], "another app's": [10]}, found)
    none = {k: (layouts.counts(k), layouts.counts_to_try({"layout": k, "per_app": {"fxsound": {"band_counts": [5, 31]}}}))
            for k in ("app:foobar2000", "graphic_10", "bands", "any", "app:peace")}
    check("layouts: foobar2000, the 10-band graphic EQ, Your bands and the parametric layouts have no band counts",
          all(v == ([], []) for v in none.values()), none)
