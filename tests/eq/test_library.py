"""This PC's search (eq\\library.py): a found device keeps its id when others are found before it, OneDrive's
online-only files left out, the app's downloads folders (this copy's and another copy's: the online databases'
entries) not searched while your own folders are, and Find… not searching the same folders or loading the database
lists again right after it did. Moved from eq_checks.py's module_checks."""
import contextlib
import os
import shutil
import time

import pytest

from eq import databases, library, settings
from helpers import qt, session


def _top():
    """The studio (the session's copy of the app with its files): the old checks' copy, "top"."""
    return session.SESSION.studio


@contextlib.contextmanager
def _made_here(*places):
    """Files and folders a test makes in the studio taken away again afterwards: only those of `places` that weren't
    there before (the next tests find the studio as this one did)."""
    new = [p for p in places if not os.path.exists(p)]
    try:
        yield
    finally:
        for p in new:
            shutil.rmtree(p, ignore_errors=True)


def test_group_keeps_its_id(check):
    top = _top()  # (made-up files: they needn't exist)
    g1 = library._group([(os.path.join(top, "b", "Bee L.txt"), {"points": 99})])
    g2 = library._group([(os.path.join(top, "a", "Ant L.txt"), {"points": 99}), (os.path.join(top, "b", "Bee L.txt"), {"points": 99})])
    # was eq_checks.py:927
    check("This PC: a group keeps its id when others are found before it", g1[0]["id"] == g2[1]["id"], (g1[0]["id"], g2[1]["id"]))


def test_cloud_only_files_left_out(check):
    # was eq_checks.py:928
    check("This PC: OneDrive's online-only files are left out (reading one downloads it)",
          library.CLOUD_ONLY & 0x400000 and library.CLOUD_ONLY & 0x1000)


@pytest.fixture(scope="module")
def scanned():
    """eq_checks.py lines 932-942: a curve in the app's own downloads folder, one in a folder of yours ("mine"), and
    another copy of the app inside it with a curve in its downloads folder; then the whole studio searched, in this
    thread. Gives the names found. The files are taken away after the module (Find…'s test below searches "mine")."""
    top = _top()
    curve = "".join(f"{20 * 1.1 ** i:.2f}\t80\n" for i in range(80))
    other = os.path.join(top, "mine", "Another AutoEQ Studio")  # (an unzipped copy: its downloads aren't yours either)
    with _made_here(os.path.join(databases.DOWNLOAD_DIR, "Some site"), os.path.join(top, "mine")):
        for folder, name in ((os.path.join(databases.DOWNLOAD_DIR, "Some site"), "Downloaded One.txt"),
                             (os.path.join(top, "mine"), "My Own.txt"), (os.path.join(other, "downloads", "Site"), "Other Copy.txt"),
                             (os.path.join(other, "app", "eq"), "databases.py")):
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, name), "w", encoding="utf-8") as fh:
                fh.write(curve)
        library._state["scanning"] = True  # (as start_scan marks it; the search itself ends it)
        library._scan([top])
        yield {g["name"] for g in library.status(with_items=True)["items"]}


def test_downloads_folders_not_searched(scanned, check):
    found = scanned
    # was eq_checks.py:943
    check("This PC: the downloads folders of this app (and another copy) aren't searched (they're the online entries), "
          "your folders are", "My Own" in found and not {"Downloaded One", "Other Copy"} & found, sorted(found)[:20])


def test_find_doesnt_search_or_load_again(scanned, db_guard, monkeypatch, check):
    # (db_guard: the database lists' state put back afterwards, and nothing downloaded even if the refresh below wasn't
    # skipped; the app is offline too)
    top = _top()
    cfg_mine = dict(settings.DEFAULTS, library={"folders": [os.path.join(top, "mine")]})

    def scan_ended():
        end = time.monotonic() + qt.time_limit(30)
        while library.status()["scanning"] and time.monotonic() < end:
            time.sleep(0.05)
    forced = library.start_scan(cfg_mine, force=True)
    scan_ended()
    again = library.start_scan(cfg_mine)
    scan_ended()
    # (the lists as just loaded for the databases in use, a moment ago)
    monkeypatch.setitem(databases._state, "loading", False)
    monkeypatch.setitem(databases._state, "updated", time.time())
    monkeypatch.setitem(databases._state, "sites", [{"url": s["url"]} for s in databases.sites_for(settings.DEFAULTS)])
    skipped = databases.start_refresh(settings.DEFAULTS) is False and not databases._state["loading"]
    rows1 = databases.status(with_items=True)["items"]
    rows2 = databases.status(with_items=True)["items"]
    # was eq_checks.py:965
    check("Find…: the same folders aren't searched again within a minute (unless asked), nor the lists loaded again "
          "within half an hour; their rows are made once per list", again is False and forced is True and skipped
          and rows1 is rows2, (again, forced, skipped, rows1 is rows2))
