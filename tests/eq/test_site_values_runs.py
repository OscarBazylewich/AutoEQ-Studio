"""Which Website values each method's curves and runs use (eq\\service.py with eq\\site_values.py), on the sample
target and measurement, recorded as from HBB (a database whose AutoEQ panel has no gain or Q boxes): the curves'
answer says which; Best fit's curves and result are exactly what they were before feature 5 (the app's own values,
listener800's); a Website run uses HBB's values and its fixed gain and Q; "Calculate from these filters" (Best fit
while a Website method is selected) fits the curves the graph shows."""
import json
import os

import pytest

from eq import inputs, rigs, service, settings, site_values

COVERS_FILES = ("samples/**", "app/eq/site_values.json")
HBB = "https://hbb.squig.link/"
OLD = settings.OLD_PROFILES["listener800"]


@pytest.fixture
def hbb_measurement(fresh_studio):
    """The sample measurement in use, recorded as downloaded from HBB."""
    cfg = settings.with_auto({})
    _target, meas = inputs.selected(cfg)
    names = [os.path.basename(p) for p in meas]
    rigs.record_source(names, {"site_url": HBB, "site": "HBB", "name": "Sample"})
    return names


def _cfg(mode, profile="auto", site=None, **section):
    """Settings for a quick run: every automatic setting yours (small values) but the 7 Website values."""
    cfg = settings.with_auto({})
    cfg["mode"], cfg["site"]["profile"] = mode, profile
    cfg["site"].update(site or {})
    cfg["performance"]["cores"] = 2
    cfg["best_fit"].update(filter_counts=[3], q_max=[2], gain_max=[6], fight_penalty=[0.01])
    cfg["site_single"].update(rows=6, gain_min=-6, gain_max=4, q_max=4)
    for k, v in section.items():
        cfg[k].update(v)
    cfg["auto"]["manual"] = [p for p in settings.ALL_AUTO_PATHS if p not in site_values.PATHS]
    return cfg


def _run(mode, cfg):
    service.JOB.clear()
    service.JOB.update(id="t", status="running")
    service.CANCEL.clear()  # (as /api/run does: a run cancelled before this one leaves it set)
    try:
        service._run_job("t", mode, json.loads(json.dumps(cfg)))
        return dict(service.JOB)
    finally:
        service.JOB.clear()
        service.JOB.update(id=None, status="idle")


def test_curves_say_which_values(hbb_measurement, check):
    web = service.curves({"settings": _cfg("site_sweep")})
    other = service.curves({"settings": _cfg("site_sweep", "custom", OLD)})
    info = web["site_values"]
    check("site values: the curves' answer says the Website values come from HBB, for the gray line",
          info["site"] == "HBB" and info["applied"] and info["note"].startswith("HBB: values from its website")
          and info["values"]["site.norm_hz"] == site_values.table_entry(HBB)["values"]["norm_hz"], info)
    check("site values: a Website method's curves for HBB's measurement differ from the app's own values' curves",
          web["meas"] != other["meas"])


def test_best_fit_unchanged(hbb_measurement, check):
    """Best fit before feature 5 = the old default (listener800's values, no list) = "Other" with those values."""
    before = _cfg("best_fit", "custom", OLD)
    now = _cfg("best_fit", "auto", dict(site_values.USUAL))  # (other values saved: the app's own replace them)
    a, b = service.curves({"settings": before}), service.curves({"settings": now})
    check("site values: Best fit's curves for a database's measurement are exactly those of the app's own values",
          a["meas"] == b["meas"] and a["target"] == b["target"])
    ra, rb = _run("best_fit", before), _run("best_fit", now)
    fa = [r["filters"] for r in (ra.get("result") or {}).get("results", [])]
    fb = [r["filters"] for r in (rb.get("result") or {}).get("results", [])]
    check("site values: a Best fit run gives the same result as before (the app's own values; nothing fixed)",
          ra.get("status") == rb.get("status") == "done" and fa and fa == fb
          and all(rb["result"]["settings"]["site"][k] == v for k, v in OLD.items())
          and "panel" not in rb["result"]["settings"], (ra.get("status"), rb.get("status"), ra.get("message")))


def test_website_run_uses_the_database_and_its_fixed_values(hbb_measurement, check):
    r = _run("site_single", _cfg("site_single"))
    res = (r.get("result") or {}).get("results") or [{}]
    used = (r.get("result") or {}).get("settings", {})
    hbb = site_values.table_entry(HBB)["values"]
    check("site values: a Website run for HBB's measurement uses HBB's values",
          r.get("status") == "done" and all(used["site"][k] == v for k, v in hbb.items()), (r.get("status"), r.get("message")))
    check("site values: and HBB's fixed gain and Q (-12 to 12 dB, Q 0.5–2), over the values typed in the boxes",
          (res[0].get("gain_min"), res[0].get("gain_max"), res[0].get("q_min"), res[0].get("q_max")) == (-12, 12, 0.5, 2)
          and (used["site_single"]["gain_min"], used["site_single"]["q_max"]) == (-12, 2)
          and all(abs(f["gain"]) <= 12 and 0.5 <= f["q"] <= 2 for f in res[0].get("filters", [])), res[0])


def test_calculate_from_these_filters_fits_the_graphs_curves(hbb_measurement, check):
    """Best fit run while the settings' method is a Website method: the curves on the graph (HBB's values)."""
    r = _run("best_fit", _cfg("site_single"))
    used = (r.get("result") or {}).get("settings", {})
    hbb = site_values.table_entry(HBB)["values"]
    check("site values: Calculate from these filters (Best fit with a Website method selected) uses the values of the "
          "curves on the graph, and nothing is fixed", r.get("status") == "done"
          and all(used["site"][k] == v for k, v in hbb.items()) and "panel" not in used
          and used["site_single"]["gain_min"] == -6, (r.get("status"), r.get("message")))
