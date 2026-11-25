"""The HTML report (eq\\report.py): the names in it are text, so a name can't end the page's script or become HTML in
the graph's hover. Moved from eq_checks.py's module_checks."""
import os

from eq import report


def test_names_stay_text(tmp_path, sample_curves, check):
    curves = sample_curves[0]
    # the report: names as text ("</script>" in one doesn't end its script; the hover builds no HTML). (The old check
    # wrote it into the folder the files' check had made; report.write doesn't make one, so this test has its own.)
    rp = os.path.join(tmp_path, "names.html")
    report.write(rp, title="T", subtitle="S", curves=curves, band=[20, 10000],
                 cards=[{"title": "Mine </script><i>x", "text": "t", "filters": [], "eq": curves["meas"], "rms": 1.0}])
    with open(rp, encoding="utf-8") as fh:
        page_html = fh.read()
    # was eq_checks.py:372
    check("report: names can't end its script or become HTML in the hover",
          page_html.count("</script>") == 1 and "<\\/script>" in page_html and "innerHTML" not in page_html)


def test_no_error_grid_for_band_counts(tmp_path, sample_curves, check):
    # A run of FxSound's band counts: each count has its own Q, so the grid "error by filter count and maximum Q"
    # would be 5 filled cells on a diagonal among 20 empty ones. The report then has no grid; the filter table stays.
    from eq import engines, settings
    curves = sample_curves[0]
    cfg = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": {"layout": "app:fxsound"}})
    rs = engines.graphic_run(cfg, curves)
    # (the keys that the result card sends for the grid: ui/eq_page_result.py)
    sent = [{k: r.get(k) for k in ("rows", "q_max", "rms", "freq_high", "n_filters", "max_boost", "ear", "engine")} for r in rs]
    grids = report.grids_for("best_fit", sent, 0.25, min(r["rms"] for r in rs))
    check("report: 5 results of a graphic EQ (one for each band count) give no error grid", len(sent) == 5 and grids == [], grids)
    rp = os.path.join(tmp_path, "bands.html")
    report.write(rp, title="T", subtitle="S", curves=curves, band=[20, 10000], grids=grids,
                 cards=[{"title": "FxSound", "text": "t", "filters": rs[-1]["filters"], "eq": rs[-1]["eq"], "rms": rs[-1]["rms"]}])
    with open(rp, encoding="utf-8") as fh:
        page_html = fh.read()
    check("report: the report of that run has the filter table of the EQ (31 rows) and no grid table",
          '<table class="grid-t"' not in page_html and page_html.count('<table class="ft"') == 1
          and page_html.count("<td>PK</td>") == 31, (page_html.count("<table"), page_html.count("<td>PK</td>")))
    # results of a parametric run, and results sent by a page of before (no "engine"), keep their grid
    fits = [dict(s, engine="bestfit", max_boost=3.0) for s in sent]
    old = [{k: v for k, v in s.items() if k != "engine"} | {"max_boost": 3.0} for s in sent]
    check("report: results of a parametric Best fit run, and results with no engine named, keep the error grid",
          len(report.grids_for("best_fit", fits, 0.25, 1.0)) == 1 and len(report.grids_for("best_fit", old, 0.25, 1.0)) == 1
          and '<table class="grid-t"' in report.grids_for("best_fit", fits, 0.25, 1.0)[0][1])
