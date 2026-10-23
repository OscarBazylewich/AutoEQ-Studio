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
          eq_apps.summary("boom3d").startswith("31 fixed bands") and eq_apps.summary("spotify").startswith("6 fixed bands")
          and {x["group"] for x in layouts.listing()} == {"Any", "Fixed bands", "EQ apps (Your EQ app)"},
          (eq_apps.summary("boom3d"), {x["group"] for x in layouts.listing()}))


def test_each_eq_app_described(check):
    # the EQ apps (eq_apps.py): each described, sourced, with a layout Best fit knows and a file the app can write
    bad_apps = [k for k, a in eq_apps.APPS.items()
                if not (a["name"] and a["how"] and a.get("source", "").startswith("http") and a["platforms"]
                        and set(a["platforms"]) <= set(eq_apps.PLATFORMS) and a["kind"] in ("parametric", "graphic", "curve", "site")
                        and eq_apps.layout_key(k) in layouts.KEYS and (a.get("file") is None or a["file"] in exports.FORMATS))]
    # was eq_checks.py:516
    check("EQ apps: each has platforms, a source, how to load the EQ, a known layout and file", not bad_apps, bad_apps)


def test_eq_app_choice_kept(check):
    c_app = settings.with_auto({"eq_app": "poweramp", "best_fit": {"layout": "moondrop_free_dsp"}})
    bf_vm = dict(settings.DEFAULTS["best_fit"], layout="app:voicemeeter", filter_counts=[3, 6, 20], low_shelf=True, high_shelf=True)
    # was eq_checks.py:519
    check("EQ apps: a choice is kept, an old device key becomes the app's; an app's shelves take its bands (Voicemeeter 6)",
          c_app["eq_app"] == "poweramp" and c_app["best_fit"]["layout"] == "app:moondrop_free_dsp"
          and settings.with_auto({"eq_app": "nope"})["eq_app"] == ""
          and layouts.device_settings(bf_vm)["filter_counts"] == [3, 4], (c_app["eq_app"], layouts.device_settings(bf_vm)["filter_counts"]))
