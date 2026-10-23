"""Your EQs to compare (eq\\listening.py): one list per IEM or headphone, kept in data\\eq\\listen.json. Kept cleaned
(names, filters, shown on the graph or not, colour), at most 12 per IEM, an EQ without filters or an IEM without a
name refused, an emptied list removed, hand-edited entries checked on the way out, looking at a list counted as
using it, and a damaged file kept aside as listen.json.bad (never written over). Moved from eq_checks.py's
module_checks.

The tests work on the session's own data folder (as the old checks worked on their copy's), starting with no
listen.json, and run in the order written: two chains, each in a module-scoped fixture (pytest runs a file's tests in
that order)."""
import os
import time
import types

import pytest

import textfile
from eq import listening
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)


def one_filter():
    """fl in the old checks (eq_checks.py line 633)."""
    return [{"type": "PK", "freq": 1000, "gain": -2, "q": 1}]


def _start_again():
    """No listen.json and no damaged copy of it kept aside (listen.json.bad, .2.bad ...): the old checks' copy had
    none (so no "IEM B" list, and room for the damaged-file test's .bad)."""
    folder, name = os.path.split(listening.PATH)
    for n in os.listdir(folder) if os.path.isdir(folder) else []:
        if n == name or (n.startswith(name + ".") and n.endswith(".bad")):
            os.remove(os.path.join(folder, n))


@pytest.fixture(scope="module", autouse=True)
def no_lists():
    _start_again()
    yield
    _start_again()
    textfile.take_set_aside()  # (a notice a damaged file left for the window: no later test should see it)


# ---------------------------------------------------------------- the first chain (lines 633-644)
@pytest.fixture(scope="module")
def iem_a():
    """eq_checks.py lines 633-635: "IEM A"'s list kept: two EQs, both to be cleaned. The three tests below check it,
    then empty it."""
    fl = one_filter()
    kept = listening.put("IEM A", [{"key": "a", "name": "  My   EQ ", "filters": fl, "shown": False, "color": 3},
                                   {"name": "x" * 200, "filters": fl + [{"type": "LSQ", "freq": 100, "gain": 3, "q": 0.7}]}])
    yield types.SimpleNamespace(fl=fl, kept=kept)
    listening.put("IEM A", [])


def test_kept_per_iem_cleaned(iem_a, check):
    kept = iem_a.kept
    # was eq_checks.py:636
    check("EQs to compare: kept per IEM, cleaned (names, filters, graph on/off, colour)",
          listening.get("IEM A") == kept and kept[0]["name"] == "My EQ" and kept[0]["shown"] is False and kept[0]["color"] == 3
          and len(kept[1]["name"]) == 80 and kept[1]["shown"] is True and listening.get("IEM B") == [], kept)


def test_too_many_or_unnamed_refused(iem_a, check):
    fl, kept = iem_a.fl, iem_a.kept
    # was eq_checks.py:639
    check("EQs to compare: at most 12 per IEM; an EQ without filters or an IEM without a name is refused (and named)",
          "At most 12" in (raises(listening.put, "IEM A", [{"filters": fl}] * 13) or "")
          and "has no filters" in (raises(listening.put, "IEM A", [{"name": "E", "filters": []}]) or "")
          and "Choose a measurement" in (raises(listening.get, "  ") or "") and listening.get("IEM A") == kept)


def test_emptied_list_goes(iem_a, check):
    # (the list the fixture kept, emptied)
    listening.put("IEM A", [])
    # was eq_checks.py:644
    check("EQs to compare: an emptied list goes", "IEM A" not in textfile.read_json(listening.PATH, default={}))


# ---------------------------------------------------------------- the second chain (lines 700-711)
@pytest.fixture(scope="module")
def clean_iem():
    """eq_checks.py lines 701-705: a hand-edited listen.json written over the file (two EQs under one key, a colour
    that isn't a number, an entry that isn't an EQ, one whose filters aren't filters; last used long ago), then
    "Clean IEM"'s list read back, which notes it as used. The two tests below check what came back, then the time
    noted. Its list emptied after (line 711)."""
    fl = one_filter()
    stored = {"Clean IEM": {"used": 1000.0, "eqs": [{"key": "a", "name": "Fine", "filters": fl, "color": 2},
                                                    {"key": "a", "name": "Same key", "filters": fl, "color": "red"},
                                                    "not an EQ", {"name": "No filters", "filters": "x"}]}}
    textfile.write_json(listening.PATH, stored)
    got = listening.get("Clean IEM")
    yield got
    listening.put("Clean IEM", [])


def test_stored_entries_checked_on_the_way_out(clean_iem, check):
    got = clean_iem
    # EQs to compare read back cleaned (a hand-edited entry broke the page)
    # was eq_checks.py:706
    check("EQs to compare: stored entries are checked on the way out (bad ones left out, keys unique, colours numbers)",
          [e["name"] for e in got] == ["Fine", "Same key"] and len({e["key"] for e in got}) == 2
          and all(isinstance(e["color"], int) for e in got), got)


def test_looking_counts_as_using(clean_iem, check):
    # looking at a list (the fixture's get) counts as using it
    # was eq_checks.py:709
    check("EQs to compare: looking at a list counts as using it (the 300-list limit drops the unused)",
          textfile.read_json(listening.PATH, {})["Clean IEM"]["used"] > time.time() - 60)


# ---------------------------------------------------------------- a damaged file (lines 732-739)
def test_damaged_file_kept_aside(check):
    fl = one_filter()
    listening.put("IEM A", [{"name": "a", "filters": fl}])
    with open(listening.PATH, "w", encoding="utf-8") as fh:
        fh.write('{"IEM A": ')
    listening.put("IEM C", [{"name": "c", "filters": fl}])
    # was eq_checks.py:736
    check("EQs to compare: a damaged file is kept as listen.json.bad, not written over",
          os.path.exists(listening.PATH + ".bad") and list(textfile.read_json(listening.PATH, {})) == ["IEM C"])
    if os.path.exists(listening.PATH + ".bad"):  # (as the old checks did after, lines 738-739)
        os.remove(listening.PATH + ".bad")
    listening.put("IEM C", [])
    textfile.take_set_aside()  # (the notice it left for the window: no later test should see it)
