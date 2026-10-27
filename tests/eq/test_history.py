"""History (eq\\history.py): past EQs kept in data\\eq\\history.json. The same EQ saved again updates its entry (and
it stays saved), an EQ without a name or with bad filters is refused, past its size the oldest unsaved EQs go first,
one entry or all removed, a damaged file kept aside as history.json.bad (never written over), and 12 saves at the
same moment all kept. Moved from eq_checks.py's module_checks.

The tests work on the session's own data folder (as the old checks worked on their copy's) and run in the order
written: two chains, each step on what the one before left (pytest runs a file's tests in that order)."""
import os
import threading

import pytest

from eq import history
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)


def entry():
    """e in the old checks (eq_checks.py lines 649-650): a saved EQ (history.add changes nothing in it; made new for
    each test all the same)."""
    return {"key": "a-1", "device": "IEM", "target": "T", "mode": "best_fit",
            "filters": [{"type": "PK", "freq": 100, "gain": 2, "q": 1}],
            "rms": 0.3, "preamp": -2.1, "n_filters": 1, "saved": True}


def _remove_left_over():
    """What an earlier test of the session may have left in the EQ part's data folder: copies of a damaged
    history.json kept aside (history.json.bad, history.json.2.bad ...) and temporary files of a write. The old checks'
    copy had none: the damaged-file test needs no .bad there before it, and the 12-saves test counts every
    temporary file in the folder."""
    folder, name = os.path.split(history.PATH)
    for n in os.listdir(folder) if os.path.isdir(folder) else []:
        if (n.startswith(name + ".") and n.endswith(".bad")) or n.endswith(".tmp"):
            os.remove(os.path.join(folder, n))


@pytest.fixture(scope="module")
def emptied():
    """History emptied before the first test (eq_checks.py line 648) and after the last; nothing left over beside it."""
    import textfile
    _remove_left_over()
    history.remove(None)
    yield
    history.remove(None)
    _remove_left_over()
    textfile.take_set_aside()  # (a notice a damaged file left for the window: no later test should see it)


# ---------------------------------------------------------------- the first chain (lines 648-662)
def test_same_eq_again_updates_it(emptied, check):
    e = entry()
    history.add(e)
    items = history.add({**e, "saved": False, "rms": 0.25})
    # was eq_checks.py:653
    check("history: the same EQ again updates it, and it stays saved", len(items) == 1 and items[0]["saved"] and items[0]["rms"] == 0.25, items)


def test_no_name_or_bad_filters_refused(emptied, check):
    e = entry()
    # was eq_checks.py:654
    check("history: an EQ without a name or with bad filters is refused",
          raises(history.add, {**e, "key": ""}) is not None and raises(history.add, {**e, "key": "b", "filters": [{"q": 0}]}) is not None)


def test_oldest_unsaved_go_first(emptied, monkeypatch, check):
    # (after the first test: History holds the saved "a-1")
    e = entry()
    monkeypatch.setattr(history, "MAX", 3)
    for i in range(5):
        history.add({**e, "key": f"u{i}", "saved": False})
    keys = [x["key"] for x in history.entries()]
    monkeypatch.undo()  # (MAX back, as the old check put it back before checking)
    # was eq_checks.py:661
    check("history: past its size, the oldest unsaved EQs go first", keys == ["a-1", "u3", "u4"], keys)


def test_one_removed_then_all(emptied, check):
    # (after the test before: History holds "a-1", "u3" and "u4")
    # was eq_checks.py:662
    check("history: one removed, then all", [x["key"] for x in history.remove(["u3"])] == ["a-1", "u4"] and history.remove(None) == [])


def test_restore_puts_one_back_in_its_place(emptied, check):
    # (2026-10-27, History's ✕ with Undo, UI-RULES 20: the entry back as it was, its time too, in its place; one whose
    # key is there again meanwhile isn't doubled. After the test before: History is empty)
    e = entry()
    for k in ("r1", "r2", "r3"):
        history.add({**e, "key": k})
    gone = next(x for x in history.entries() if x["key"] == "r2")
    history.remove(["r2"])
    back = history.restore([gone])
    again = history.restore([gone])
    put = next((x for x in back if x["key"] == "r2"), {})
    history.remove(None)
    check("history: Undo of a removed entry puts it back as it was (its time too) in its place, once",
          [x["key"] for x in back] == ["r1", "r2", "r3"] and put.get("when") == gone["when"]
          and [x["key"] for x in again] == ["r1", "r2", "r3"], ([x["key"] for x in back], put.get("when"), gone["when"]))


# ---------------------------------------------------------------- the second chain (lines 718-746)
def test_damaged_file_kept_aside(emptied, check):
    import textfile
    e = entry()
    history.remove(None)  # (line 718: an empty History to start from)
    # a damaged history.json is kept aside (.bad), never written over (the next save wiped every entry)
    history.add(e)
    with open(history.PATH, encoding="utf-8") as fh:
        whole = fh.read()
    with open(history.PATH, "w", encoding="utf-8") as fh:
        fh.write(whole[:-5])
    items = history.add({**e, "key": "after"})
    with open(history.PATH + ".bad", encoding="utf-8") as fh:
        bad = fh.read()
    # was eq_checks.py:728
    check("history: a damaged file is kept as history.json.bad, and a new one started", [x["key"] for x in items] == ["after"]
          and bad == whole[:-5], items)
    os.remove(history.PATH + ".bad")  # (as the old checks did after, lines 730-731)
    history.remove(None)
    textfile.take_set_aside()  # (the notice it left for the window: no later test should see it)


def test_twelve_saves_at_once(emptied, check):
    e = entry()
    history.remove(None)  # (as the test before left it: an empty History; said again, so this one stands alone)
    # two saves at once (the server answers in parallel threads): neither is lost, no temporary file left
    ths = [threading.Thread(target=history.add, args=({**e, "key": f"t{i}"},)) for i in range(12)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    left = [n for n in os.listdir(os.path.dirname(history.PATH)) if n.endswith(".tmp")]
    # was eq_checks.py:745
    check("history: 12 saves at the same moment are all kept", len(history.entries()) == 12 and not left, (len(history.entries()), left))
    history.remove(None)
