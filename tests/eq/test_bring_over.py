"""Bringing AutoEQ Local's files in, once (eq\\bring_over.py): AutoEQ Local found beside the program, nothing brought
while AutoEQ Studio's EQ part has settings of its own, its files copied in (the settings last) but not its logs or
the rig builds' download cache, a file already here kept, and only once; its record of where each file came from
added to the app's (the app's own kept); and never on a test's data folder alone. Moved from eq_checks.py's
studio_checks and review_low_checks.

The bring-over looks beside the program's folder for AutoEQ Local, so its three steps run as the old studio part ran
them: in a copy of the app of their own (in tmp_path, never the session's copy, which must never find an AutoEQ Local
beside it, and never your Downloads), with a stand-in AutoEQ Local beside that copy, in a Python of their own whose
AUTOEQSTUDIO_ROOT and AUTOEQSTUDIO_DATA point at the copy. That Python prints what each step did; the checks are made
here."""
import json
import os
import types

import pytest

from eq import bring_over
from helpers import session, subproc

COVERS = ("eq.bring_over", "eq.paths", "paths")  # (the chain reaches them only through text: python -c, in its copy)

# The chain eqa-178 -> 179 -> 180 (eq_checks.py lines 1250-1290), run in the copy: sys.argv[1] is the copy's main
# folder (the old checks' `top`). Its last line: what each step did, as JSON.
CHAIN = r'''
import json
import os
import sys

top = sys.argv[1]
sys.path.insert(0, os.path.join(top, "app"))  # (the copy's app first, as the old checks' use_copy did)
from eq import bring_over, paths

out = {"eq_app": paths.APP}  # (where the EQ part was loaded from: the copy's, the fixture makes sure)
# a fake AutoEQ Local beside it, with what it keeps (lines 1260-1269)
src = os.path.join(os.path.dirname(top), "AutoEQ Local")
files = {r"data\settings.json": '{"mode": "best_fit"}', r"data\history.json": "[]", r"data\listen.json": "{}",
         r"data\app.log": "log", r"data\cache\databases.json": '{"local": 1}', r"data\cache\timing.json": "{}",
         r"data\cache\rig-build\x.json": "{}", r"inputs\target\T.csv": "20 0", r"output\My EQ - filters.txt": "x",
         r"presets\P.json": "{}", r"downloads\site\M L.txt": "20 0"}
for rel, text in files.items():
    os.makedirs(os.path.dirname(os.path.join(src, rel)), exist_ok=True)
    with open(os.path.join(src, rel), "w") as fh:
        fh.write(text)
with open(os.path.join(paths.CACHE, "databases.json"), "w") as fh:
    fh.write('{"studio": 1}')
os.makedirs(paths.DATA, exist_ok=True)
with open(paths.SETTINGS_PATH, "w") as fh:
    fh.write("{}")
# eqa-178 (line 1275)
out.update(src=src, default_source=bring_over.default_source(), needed=bring_over.needed(),
           brought=bring_over.bring_over())
# eqa-179 (lines 1277-1284)
for p in (paths.SETTINGS_PATH, os.path.join(paths.DATA, "history.json"), os.path.join(paths.DATA, "listen.json"),
          os.path.join(paths.CACHE, "timing.json")):  # (the earlier checks' own: as on a first use)
    if os.path.exists(p):
        os.remove(p)
done = [os.path.relpath(os.path.realpath(p), os.path.realpath(top)) for p in bring_over.bring_over()]
with open(os.path.join(paths.CACHE, "databases.json")) as fh:
    kept = fh.read()
out.update(done=done, kept=kept)
# eqa-180 (line 1290)
out.update(again=bring_over.bring_over(), needed_again=bring_over.needed())
print(json.dumps(out))
'''


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    """The chain's three steps, in order, in a copy of the app of their own (see above). Raises when they didn't
    finish (a fixture doesn't check: the tests below do)."""
    base = str(tmp_path_factory.mktemp("bring_over"))
    top = os.path.join(base, "AutoEQ Studio")
    subproc.app_copy(top)
    r = subproc.run_python(CHAIN, top, env={"AUTOEQSTUDIO_ROOT": top, "AUTOEQSTUDIO_DATA": os.path.join(top, "data")},
                           cwd=top)
    if r.returncode != 0 or not isinstance(r.data, dict):
        raise RuntimeError(f"The bring-over's steps didn't finish in their copy of the app (exit {r.returncode}):\n"
                           f"{r.stdout[-2000:]}\n{r.stderr[-4000:]}")
    if not session.inside(r.data["eq_app"], top):
        raise RuntimeError(f"The bring-over's steps loaded the EQ part from {r.data['eq_app']}, not their copy {top}")
    return types.SimpleNamespace(top=top, **r.data)


def test_found_beside_nothing_brought_with_own_settings(chain, check):
    src, found = chain.src, chain.default_source
    # (paths compared the long way on both sides, never as text)
    # was eq_checks.py:1275
    check("studio: AutoEQ Local is found beside it; nothing brought while it has its own settings",
          found is not None and os.path.realpath(found) == os.path.realpath(src) and not chain.needed
          and chain.brought == [], (found, src, chain.needed, chain.brought))


def test_files_copied_in_settings_last(chain, check):
    done, kept, src = chain.done, chain.kept, chain.src
    # was eq_checks.py:1284
    check("studio: AutoEQ Local's files are copied in (settings last), its logs and the rig builds' cache aren't, and "
          "a file already here is kept", sorted(done) == sorted([
              r"data\eq\cache\timing.json", r"Targets\T.csv", r"Saved EQs\My EQ - filters.txt", r"Presets\P.json",
              r"downloads\site\M L.txt", r"data\eq\history.json", r"data\eq\listen.json", r"data\eq\settings.json"])
          and done[-1].endswith("settings.json") and kept == '{"studio": 1}'
          and os.path.isfile(os.path.join(src, r"data\settings.json")), done)


def test_brought_once(chain, check):
    # was eq_checks.py:1290
    check("studio: brought once", chain.again == [] and not chain.needed_again, (chain.again, chain.needed_again))


def test_records_merged_never_on_a_test_data_folder_alone(tmp_path, monkeypatch, check):
    # #66, #67: the bring-over: never into the real folders on a test's data folder alone; sources.json merged
    d = str(tmp_path)
    a_, b_ = os.path.join(d, "a.json"), os.path.join(d, "b.json")
    with open(a_, "w") as fh:
        json.dump({"x.txt": {"site": "A"}, "y.txt": {"site": "B"}}, fh)
    with open(b_, "w") as fh:
        json.dump({"y.txt": {"site": "mine"}}, fh)
    done = []
    bring_over._merge_sources(a_, b_, done)
    with open(b_) as fh:
        merged = json.load(fh)
    monkeypatch.delenv("AUTOEQSTUDIO_ROOT")  # (AUTOEQSTUDIO_DATA stays: a test's data folder alone)
    blocked = not bring_over.needed()
    monkeypatch.undo()
    # was eq_checks.py:1965
    check("review: bring-over adds AutoEQ Local's file records to the app's (keeps its own); never on a test's data "
          "folder alone", merged == {"y.txt": {"site": "mine"}, "x.txt": {"site": "A"}} and blocked, merged)
