"""Does the EQ apply? (switcher\\check.py): Equalizer APO's Benchmark output read (the files it loads, the sections
that match the device) and said in plain words for each case, and, without APO's Benchmark tool, said so. APO's real
Benchmark.exe is never run: the stand-in APO folder here has no program folder, so check.run stops before starting
anything (and a stand-in for its subprocess makes sure). Moved from selftest.py's benchmark_checks."""
import os
import types

import pytest

from switcher import check as c
from switcher.apo import Apo


@pytest.fixture(scope="module")
def bench(tmp_path_factory):
    """benchmark_checks' start (selftest.py lines 636-648): a stand-in APO config folder (no program folder), the
    places of AutoEQ Studio's switcher.txt, a profile "My IEM.txt" (never written: the "missing" case needs it
    missing) and Loudness.txt, six lines as Benchmark -v writes them, and what parse() read in them."""
    top = str(tmp_path_factory.mktemp("bench-top"))
    conf = os.path.join(top, "bench", "config")
    os.makedirs(os.path.join(conf, "AutoEQ Studio", "profiles"))
    apo = Apo(conf)
    ours = os.path.join(conf, "AutoEQ Studio", "switcher.txt")
    eq = os.path.join(conf, "AutoEQ Studio", "profiles", "My IEM.txt")
    other = os.path.join(conf, "Loudness.txt")
    out = "\n".join([f"12:00:00.001 (TRACE) Loading configuration from {apo.config_txt}",
                      '12:00:00.002 (TRACE) Matching pattern "all" with device ...',
                      f"12:00:00.003 (TRACE) Loading configuration from {other}",
                      f"12:00:00.004 (TRACE) Loading configuration from {ours}  ",
                      '12:00:00.005 (TRACE) Matching pattern "{5}; {6}" with device Headset',
                      f"12:00:00.006 (TRACE) Loading configuration from {eq}"])
    found = c.parse(out)
    return types.SimpleNamespace(apo=apo, ours=ours, eq=eq, other=other, found=found)


def test_benchmark_lines_read(bench, check):
    apo, ours, eq, other, found = bench.apo, bench.ours, bench.eq, bench.other, bench.found
    # was selftest.py:649
    check("check: Benchmark's lines read (the files loaded, the sections matched but \"all\")",
          found == {"loaded": [apo.config_txt, other, ours, eq], "matched": ["{5}; {6}"]}, found)


def test_said_plainly(bench, check):
    apo, eq, found = bench.apo, bench.eq, bench.found
    applies = c.explain(apo, found, "My IEM", eq)
    off = c.explain(apo, dict(found, loaded=found["loaded"][:3]), None)
    not_ours = c.explain(apo, {"loaded": [apo.config_txt], "matched": []}, "My IEM", eq)
    no_section = c.explain(apo, {"loaded": [apo.config_txt, bench.ours], "matched": []}, "My IEM", eq)
    missing = c.explain(apo, dict(found, loaded=found["loaded"][:3]), "My IEM", eq)
    no_apo = c.explain(apo, found, "My IEM", eq, apo_on_device=False)
    # was selftest.py:657
    check("check: said plainly: the EQ applies (and what config.txt adds on top), off, config.txt without AutoEQ "
          "Studio's line, no section for the device, the EQ's file missing, APO not on the device",
          applies[0] and "“My IEM” applies" in applies[1] and "Loudness.txt" in applies[1]
          and off[0] and "off for this device" in off[1]
          and not not_ours[0] and "doesn't read AutoEQ Studio's file" in not_ours[1]
          and not no_section[0] and "no section" in no_section[1]
          and not missing[0] and "missing" in missing[1]
          and not no_apo[0] and "isn't installed" in no_apo[1], (applies, off, not_ours, no_section, missing, no_apo))


def _never_run(*args, **kwargs):
    """check.py's subprocess.run, in this test: APO's Benchmark tool must never be started by the tests."""
    raise AssertionError(f"APO's Benchmark tool was started ({args[0] if args else kwargs}): the tests never run it")


def test_without_benchmark_tool(bench, monkeypatch, check):
    # (the stand-in APO folder has no program folder, so run() says so before starting anything; and should it ever
    # try, this stand-in stops it instead of running APO's real Benchmark.exe)
    monkeypatch.setattr(c, "subprocess", types.SimpleNamespace(run=_never_run))
    raised = ""
    try:
        c.run(bench.apo, "{5}")
    except OSError as e:
        raised = str(e)
    # was selftest.py:670
    check("check: without APO's Benchmark tool, said (nothing run)", "Benchmark tool isn't there" in raised, raised)
