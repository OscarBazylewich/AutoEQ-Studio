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
