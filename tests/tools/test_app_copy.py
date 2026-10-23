"""The copy of the app that edge_probe.py and the README pictures work on (app\\tools\\app_copy.py, moved unchanged
from the old EQ checks, eq_checks.py, which made one on every full run): make_copy puts the program without its
tools, the samples, the sample target in Targets, the sample device's measurements in Measurements and the database
lists into a new temporary folder; use_copy points the EQ part at it; remove_copy deletes it. Here with the tests'
own small lists (never this PC's downloaded ones), in the test folder."""
import os

from helpers import paths as project
from helpers import subproc

# (for app\tools\relevant_tests.py: the tool these tests import through helpers.paths.import_tool)
COVERS = ("app_copy",)


def _norm(p):
    return os.path.normcase(os.path.realpath(p))


def test_copy_made_used_and_removed(check, monkeypatch):
    ac = project.import_tool("app_copy")
    monkeypatch.setattr(ac, "DB_LISTS", [project.DB_FIXTURES])
    base, top = ac.make_copy()
    app = os.path.join(top, "app")
    device = os.path.join(project.SAMPLES, "measurements", project.SAMPLE_DEVICE)
    made = {"the program": os.path.isfile(os.path.join(app, "start.py")) and os.path.isdir(os.path.join(app, "eq")),
            "without its tools": not os.path.exists(os.path.join(app, "tools")),
            "the samples": os.path.isdir(os.path.join(top, "samples", "targets")),
            "the sample target": os.listdir(os.path.join(top, "Targets")) == [project.SAMPLE_TARGET],
            "the sample device": sorted(os.listdir(os.path.join(top, "Measurements"))) == sorted(os.listdir(device)),
            "the lists": sorted(os.listdir(os.path.join(top, "data", "eq", "cache")))
            == ["databases.json", "squigsites.json"]}
    check("app copy (edge_probe.py, the README pictures): the program without its tools, the samples, the sample "
          "target and device, the database lists", all(made.values()), [k for k, ok in made.items() if not ok])
    run = subproc.run_python("import json, sys; sys.path.insert(0, sys.argv[1]); import app_copy; "
                             "app_copy.use_copy(sys.argv[2]); import paths, eq.paths as p; "
                             "print(json.dumps([p.ROOT, p.STUDIO_DATA, p.__file__, paths.__file__]))",
                             project.TOOLS, top)
    where = [_norm(w) for w in run.data or []]
    check("app copy: use_copy points the EQ part at the copy (your files and its data there, the program from it)",
          run.returncode == 0 and where[:2] == [_norm(top), _norm(os.path.join(top, "data"))]
          and len(where) == 4 and all(w.startswith(_norm(app) + os.sep) for w in where[2:]),
          (where, run.stderr[-300:]))
    check("app copy: remove_copy deletes it", ac.remove_copy(base) and not os.path.exists(base), base)
