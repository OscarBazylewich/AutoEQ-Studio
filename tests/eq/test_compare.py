"""Which measurement to use (eq\\compare.py): measurements ranked by their rig (the same rig as the target's first,
then one the target is converted for, then one it can't be converted for), your own files kept in the list however
many database entries match, short names matched as whole words, and an averaged file named as Windows allows.
Moved from eq_checks.py's module_checks."""
import os

from eq import compare, databases, engines, library, rigconv
import textfile
from helpers import session

COVERS_FILES = ("samples/**",)  # (the averaged file is made from the sample measurements' curves)


def test_rig_ranking(check):
    # (only the rigs' average conversion from rigdata.json is needed here: eq_checks.py made it at line 607)
    avg = rigconv.expected("iem", "5128", "711", None)
    base = {"sure": True, "dev": None, "bass": None, "n_files": 2, "fmin": 20, "fmax": 20000, "points": 300,
            "channels": ["L", "R"], "source": "X"}
    scores = {}
    for name, c in (("same", dict(base, rig="5128", conv={"how": "same"})), ("converted", dict(base, rig="711", conv=avg)),
                    ("off", dict(base, rig="711", conv=rigconv.expected("iem", "5128", "711", None, enabled=False))),
                    ("no data", dict(base, rig="711", conv={"how": "nodata"}))):
        compare.score(c, "5128")
        scores[name] = c["score"]
    # was eq_checks.py:619
    check("rig ranking: same rig > converted > converting off > no data", scores["same"] > scores["converted"] > scores["off"] > scores["no data"], scores)


def test_own_files_stay_past_40_matches(monkeypatch, check):
    top = session.SESSION.studio  # (the studio: the old checks' copy, "top")
    many = [{"kind": "measurement", "name": f"Brand HD 600 v{i}", "site": "S", "site_url": "https://s.squig.link/",
             "id": f"x{i}", "tag": "S", "ref": {"file": f"HD 600 v{i}"}} for i in range(50)]
    mine_g = {"kind": "measurement", "name": "HD 600", "folder": os.path.join(top, "Measurements"),
              "files": [os.path.join(top, "Measurements", "HD 600 L.txt")], "id": "mine", "in_app": True}
    monkeypatch.setattr(databases, "items", lambda: many)
    monkeypatch.setattr(library, "status", lambda with_items=False: {"items": [mine_g]})
    cands = compare.candidates("HD 600")
    monkeypatch.undo()  # (put back before checking, as the old check did)
    # was eq_checks.py:981
    check("compare: your own files stay in the list past 40 database matches",
          len(cands) == 40 and cands[-1]["id"] == "mine", (len(cands), cands[-1]["id"]))


def test_short_name_matches_whole_words(check):
    # was eq_checks.py:983
    check("compare: a short name matches whole words only (\"S12\" isn't inside \"KZ ZS12\")",
          compare.matches("S12", "Letshuoer S12") and not compare.matches("S12", "KZ ZS12")
          and compare.matches("Blessing 2", "Moondrop Blessing2"))


def test_averaged_name_is_windows_safe(sample_curves, monkeypatch, check):
    curves = sample_curves[0]
    # (the last comparison: two made-up measurements with the sample's curve, as eq_checks.py lines 987-990 put them)
    monkeypatch.setattr(compare, "_LAST", {k: {"rig": "711", "vals": curves["meas"][:len(compare.F)] if len(curves["meas"]) >= len(compare.F)
                                               else engines.np.zeros(len(compare.F)), "name": k, "source": "S"} for k in ("a", "b")})
    avg_name = compare.average(["a", "b"], "Bad: name?\t.")[0]
    monkeypatch.undo()
    # was eq_checks.py:995
    check("compare: an averaged file's name is Windows-safe as add_file keeps it",
          avg_name == textfile.safe_name(avg_name) and avg_name.startswith("Bad_ name__"), avg_name)
