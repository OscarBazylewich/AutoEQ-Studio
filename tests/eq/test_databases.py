"""The online databases (eq\\databases.py): an entry's device type, the lists kept on this PC read without being
written again, graph-tool sites' settings read (a moved page, comments, modernGraphTool), phone-book entries, ids that
stay the same through a refresh, downloads kept inside their database's folder and a cut-off copy fetched again, a
refresh asked for during one, squig.link's list (only web addresses, fetched in the background, a failed try not
repeated at once), and a refresh after a failed one. Moved from eq_checks.py's module_checks and
review2_maths_checks.

Nothing is downloaded: every test that could reach the internet stands in for databases._get (the db_guard fixture,
which also puts the module's state back afterwards), and the app is offline for the whole session."""
import contextlib
import os
import shutil
import threading
import time
import types

import pytest

from eq import databases, settings
import textfile
from helpers import qt
from helpers.eq import DbGuard

ITEM = {"name": "x", "url": "https://x.squig.link/", "type": "", "group": "added"}  # (eq_checks.py line 831)
CURVE = "".join(f"{20 * 1.1 ** i:.2f}\t{80 + i % 5}\n" for i in range(80))  # (the curve a stood-in download gives)


@contextlib.contextmanager
def _downloads_as_found():
    """What a test adds to the app's downloads folder (a database's folder made for a download, its files) taken away
    again afterwards: the next tests find the folder as this one did."""
    folder = databases.DOWNLOAD_DIR
    before = set(os.listdir(folder)) if os.path.isdir(folder) else None
    try:
        yield
    finally:
        if before is None:
            shutil.rmtree(folder, ignore_errors=True)
        elif os.path.isdir(folder):
            for name in set(os.listdir(folder)) - before:
                shutil.rmtree(os.path.join(folder, name), ignore_errors=True)


def test_device_type_from_folders_database_and_names(check):
    # (with squig.link's saved list, squigsites.json, in the session's data\eq\cache, put there from tests\fixtures\db,
    # as the old check had it; without it, see test_device_type_without_squiglinks_list)
    assert os.path.isfile(databases.DIRECTORY_PATH), "squig.link's saved list (squigsites.json) is missing"
    ae = "https://github.com/jaakkopasanen/AutoEq"
    forms = [databases.name_form(n) for n in ("Harman IE 2019", "Harman over-ear 2018", "HD600", "Tie T3")]
    forms += [databases.item_form({"kind": "measurement", "name": "HD600", "sub": "oratory1990 · over-ear", "site_url": ae}),
              databases.item_form({"kind": "measurement", "name": "X", "sub": "B", "site_url": "https://earphonesarchive.squig.link/headphones/"}),
              databases.item_form({"kind": "target", "name": "Harman IE 2019", "sub": "target", "site_url": ae})]
    # was eq_checks.py:509
    check("search filters: device type from AutoEq's folders, the database and names", forms == ["iem", "hp", "", "", "hp", "hp", "iem"], forms)


def test_device_type_without_squiglinks_list(db_guard, monkeypatch, tmp_path, check):
    # (a bug the map stage found, fixed 2026-10-22: without squig.link's saved list, a first start offline, the index
    # of the databases was never built, not even of the built-in ones, so AutoEq's and Earphones Archive's entries had
    # no device type or rig)
    monkeypatch.setattr(databases, "DIRECTORY_PATH", os.path.join(tmp_path, "never saved", "squigsites.json"))
    monkeypatch.setattr(databases, "_dir_sites", {"mtime": None, "sites": [], "by_url": {}})  # (as at a first start)
    ae = "https://github.com/jaakkopasanen/AutoEq"
    forms = [databases.item_form({"kind": "measurement", "name": "HD600", "sub": "oratory1990 · over-ear", "site_url": ae}),
             databases.item_form({"kind": "measurement", "name": "X", "sub": "B",
                                  "site_url": "https://earphonesarchive.squig.link/headphones/"})]
    found = [(databases.find_site(s["url"]) or {}).get("name") for s in databases.SITES]
    check("search filters: without squig.link's saved list (a first start offline), the built-in databases still give "
          "their entries' device type, and every built-in database is found by its address",
          forms == ["hp", "hp"] and found == [s["name"] for s in databases.SITES], (forms, found))


def test_recent_lists_read_not_written(db_guard, monkeypatch, tmp_path, check):
    # the database lists: the saved copy isn't written again when no list was downloaded (it's large: that slowed the
    # start)
    site = {"name": "Test", "url": "https://example.invalid/", "short": "T"}
    monkeypatch.setattr(databases, "CACHE_PATH", os.path.join(tmp_path, "db-test.json"))
    item = {"kind": "measurement", "name": "X", "sub": ""}
    item["h"] = databases.entry_base(site["url"], item)  # (as the app saves its lists since 2026-10-24)
    textfile.write_json(databases.CACHE_PATH, {site["url"]: {"time": time.time(), "conf": {}, "v": databases.LIST_VERSION,
                                                             "items": [item]}})
    os.utime(databases.CACHE_PATH, (1, 1))
    databases.refresh_now([site])
    # was eq_checks.py:531
    check("databases: recent lists read, not written again", os.path.getmtime(databases.CACHE_PATH) == 1
          and databases.status()["count"] == 1, databases.status())


def test_lists_saved_before_given_their_ids_once(db_guard, monkeypatch, tmp_path, check):
    # (2026-10-24: each entry's id was worked out at every start, 55,000 hashes, ~146 ms of Python's time shared with
    # the window; it's kept in the lists file now. A file saved before has none: they're worked out and written once)
    site = {"name": "Test", "url": "https://example.invalid/", "short": "T"}
    monkeypatch.setattr(databases, "CACHE_PATH", os.path.join(tmp_path, "db-old.json"))
    textfile.write_json(databases.CACHE_PATH, {site["url"]: {"time": time.time(), "conf": {}, "v": databases.LIST_VERSION,
                                                             "items": [{"kind": "measurement", "name": "X", "sub": ""}]}})
    os.utime(databases.CACHE_PATH, (1, 1))
    databases.refresh_now([site])
    first = os.path.getmtime(databases.CACHE_PATH) != 1
    saved = databases.load_cache()[site["url"]]["items"][0].get("h")
    os.utime(databases.CACHE_PATH, (1, 1))
    databases.refresh_now([site])
    check("databases: lists saved before the ids were kept get them written once (worked out as before, the same "
          "ids), then aren't written again",
          first and saved == databases.entry_base(site["url"], {"kind": "measurement", "name": "X"})
          and os.path.getmtime(databases.CACHE_PATH) == 1 and databases.status()["count"] == 1,
          (first, saved, os.path.getmtime(databases.CACHE_PATH)))


def test_lists_read_a_site_at_a_time(monkeypatch, check):
    # (2026-10-24: json.loads of the whole lists file (9 MB) held Python's lock ~55 ms in one go, and the window,
    # which needs it to answer, waited that long; read a site at a time, the lock is let go after each. The session's
    # own lists, as installed for the tests)
    import json
    with open(databases.CACHE_PATH, encoding="utf-8") as fh:
        text = fh.read()
    whole = json.loads(text)
    let_go, real_sleep, me = [], time.sleep, threading.get_ident()
    monkeypatch.setattr(databases.time, "sleep", lambda s: (let_go.append(s) if threading.get_ident() == me else None,
                                                           real_sleep(s))[1])
    pieces = databases.load_cache()
    monkeypatch.setattr(databases.time, "sleep", real_sleep)
    odd = databases._sites_one_at_a_time(' \n{ "a" : {"items": [1, 2]} ,\t"b":{} }\n')
    saved = []
    monkeypatch.setattr(databases.textfile, "write_atomic", lambda path, data: saved.append(data))
    databases._save_cache(whole)
    check("databases: the lists file is read a site at a time (Python's lock let go after each), the same as read "
          "whole; any spacing; written back as the same text",
          pieces == whole and len(let_go) == len(whole) >= 2 and odd == {"a": {"items": [1, 2]}, "b": {}}
          and saved == [json.dumps(whole)], (len(whole), len(let_go), odd))


def test_lists_ids_the_same(check):
    # (the ids kept in the lists file are the ones worked out at every start before: a Use button, a History entry
    # or a download named by one finds the same entry)
    cache = databases.load_cache()
    entries = [dict(it, site="s", site_url=url) for url, c in cache.items() for it in (c or {}).get("items", [])]
    without = [{k: v for k, v in e.items() if k != "h"} for e in entries]
    stored = [dict(e, h=databases.entry_base(e["site_url"], e)) for e in without]
    databases.assign_ids(without)
    databases.assign_ids(stored)
    check("databases: the ids from the first parts kept with the entries are the ones worked out before, for every "
          "entry of the session's lists",
          len(without) >= 10 and [e["id"] for e in without] == [e["id"] for e in stored], len(without))


@pytest.fixture
def graph_configs(monkeypatch):
    """Two graph-tool sites' settings read from pages served from here (eq_checks.py lines 537-557: nothing
    downloaded): a page that moved (a meta refresh) to an older graph tool's page, and a modernGraphTool page."""
    pages = {
        "https://a.test/": ('<meta http-equiv="refresh" content="0; url=https://b.test/hp/">', "https://a.test/"),
        "https://b.test/hp/": ('<script src="assets/js/config.js"></script>', "https://b.test/hp/"),
        "https://b.test/hp/assets/js/config.js": ('const init = ["x"], DIR = "data/", // Where "files" live\n'
                                                  '   // PHONE_BOOK = "phone_book.json", /* old */\n'
                                                  '   url = "https://x.test/a//b";', ""),
        "https://m.test/": ('<script src="./config.js?cachebust"></script>', "https://m.test/"),
        "https://m.test/config.js?cachebust": ('const CONFIG = { PATH: { PHONE_MEASUREMENT: "./data/phones", // c\n'
                                               'TARGET_MEASUREMENT: "./data/targets" },\n'
                                               'TARGET_MANIFEST: { default: [ { type: "Harman", files: ["Harman IE 2019v2", "A \\"b\\""] } ],'
                                               ' i18n: { ko: [ { type: "하만" } ] } } };', ""),
    }
    with monkeypatch.context() as m:
        m.setattr(databases, "_get", lambda url, **k: pages[url])
        try:
            old = databases._squig_config({"url": "https://a.test/"})
            new = databases._squig_config({"url": "https://m.test/"})
        except Exception as e:  # noqa: BLE001
            old = new = {"error": repr(e)}
    return old, new


def test_moved_page_followed(graph_configs, check):
    old = graph_configs[0]
    # was eq_checks.py:558
    check("databases: a moved page followed, a commented-out setting ignored",
          old.get("base") == "https://b.test/hp/data/" and old.get("phone_book") == "https://b.test/hp/data/phone_book.json", old)


def test_modern_graph_tool_config(graph_configs, check):
    new = graph_configs[1]
    # was eq_checks.py:560
    check("databases: modernGraphTool's config (folders, targets)",
          new.get("base") == "https://m.test/data/phones/" and new.get("targets_base") == "https://m.test/data/targets/"
          and new.get("phone_book") == "https://m.test/data/phone_book.json"
          and new.get("targets") == [{"type": "Harman", "files": ["Harman IE 2019v2", 'A "b"']}], new)


def test_phone_book_entries(check):
    pv = databases._phone_variants
    got = [pv("X1"), pv({"name": "Maxwell", "file": ["M (EQ A)", "M (EQ B)"], "prefix": "M", "samples": 3}),
           pv({"name": "R50x", "hptfs": [{"suffix": "", "files": ["R Center", "R Front"]}]}),
           pv({"name": "Y", "file": ["Y a"], "suffix": ["(a)"], "variants": [{"suffix": "(a)", "file": "Y a", "samples": {"count": 4}}]})]
    # was eq_checks.py:568
    check("databases: phone-book entries (own samples, seating sets, variants)", got == [
        [("X1", {"file": "X1"})],
        [("Maxwell (EQ A)", {"file": "M (EQ A)", "samples": 3}), ("Maxwell (EQ B)", {"file": "M (EQ B)", "samples": 3})],
        [("R50x", {"file": "R Center", "files": ["R Center", "R Front"]})],
        [("Y (a)", {"file": "Y a", "samples": 4})]], got)


@pytest.fixture(scope="module")
def fake_site(tmp_path_factory):
    """eq_checks.py lines 856-882: a made-up squig.link site whose list is read twice, an entry added before the
    others in between; then its entries downloaded (the downloads stood in for: each gives a whole curve), first with
    a channel name that tries to reach outside the site's download folder, then two entries of one name. Everything
    the module's state was is put back before the checks (DbGuard), as the old checks did; the downloaded files stay
    for the cut-off copy's test below and are taken away after the module."""
    guard = DbGuard()
    guard.save()
    guard.stub_get()  # (nothing downloaded for real, whatever happens)
    site = {"name": "Fake site", "url": "https://fake.squig.link/", "short": "Fake"}
    lists = [[{"kind": "measurement", "name": "Aria", "sub": "Moondrop", "tag": "Fake", "ref": {"file": "Aria 2021"}},
              {"kind": "measurement", "name": "Aria", "sub": "Moondrop", "tag": "Fake", "ref": {"file": "Aria 2023"}}]]
    conf = {"base": "https://fake.squig.link/data/", "samples": 0, "channels": ["L", "\\..\\..\\..\\escape"], "targets": []}
    got = types.SimpleNamespace(site=site, lists=lists, conf=conf, data=str(tmp_path_factory.mktemp("fake site")), fetched=[])
    with _downloads_as_found():
        try:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(databases, "_index_squig", lambda s: (lists[0], conf))
                mp.setattr(databases, "CACHE_PATH", os.path.join(got.data, "fake dbs.json"))
                databases.refresh_now([site], force=True)
                got.ids1 = [it["id"] for it in databases.items()]
                lists[0] = [{"kind": "measurement", "name": "Blessing", "sub": "Moondrop", "tag": "Fake", "ref": {"file": "B"}}] + lists[0]
                databases.refresh_now([site], force=True)
                got.ids2 = [it["id"] for it in databases.items()]
                mp.setattr(databases, "_get", lambda url, **k: (got.fetched.append(url), (CURVE, url))[1])
                esc = databases.download(got.ids2[1], lambda t: 99)[0]
                site_dir = os.path.join(databases.DOWNLOAD_DIR, databases.folder_name("Fake site"))
                got.msg_escape = "kept inside" if esc and all(textfile.inside(p, site_dir) for p in esc) else str(esc)
                conf["channels"] = ["L", "R"]
                got.paths_a = databases.download(got.ids2[1], lambda t: 99)[0]
                got.paths_b = databases.download(got.ids2[2], lambda t: 99)[0]
        finally:
            guard.restore()
        yield got


def test_entry_keeps_its_id(fake_site, check):
    ids1, ids2 = fake_site.ids1, fake_site.ids2
    # was eq_checks.py:883
    check("databases: an entry keeps its id when a database adds entries before it",
          ids1 == ids2[1:] and ids2[0] not in ids1, (ids1, ids2))


def test_channel_names_kept_inside(fake_site, check):
    msg_escape = fake_site.msg_escape
    # was eq_checks.py:885
    check("databases: a site's channel names can't reach outside its download folder", msg_escape == "kept inside", msg_escape)


def test_same_named_entries_own_files(fake_site, check):
    paths_a, paths_b = fake_site.paths_a, fake_site.paths_b
    # was eq_checks.py:886
    check("databases: two entries of one name get their own files",
          len(paths_a) == 2 and not set(paths_a) & set(paths_b) and all("Aria 2021" in p for p in paths_a), (paths_a, paths_b))


def test_cut_off_copy_fetched_again(fake_site, db_guard, monkeypatch, check):
    # a copy from before that isn't a whole curve is fetched again (an interrupted download was reused forever)
    paths_a, fetched = fake_site.paths_a, []
    with open(paths_a[0], "w", encoding="utf-8") as fh:
        fh.write("20 1\n30 2\n")
    monkeypatch.setattr(databases, "_index_squig", lambda site: (fake_site.lists[0], dict(fake_site.conf)))
    monkeypatch.setattr(databases, "CACHE_PATH", os.path.join(fake_site.data, "fake dbs.json"))
    databases.refresh_now([fake_site.site], force=True)
    monkeypatch.setattr(databases, "_get", lambda url, **k: (fetched.append(url), (CURVE, url))[1])
    databases.download(fake_site.ids2[1], lambda t: len(t.splitlines()))
    monkeypatch.undo()  # (put back before checking, as the old check did)
    with open(paths_a[0], encoding="utf-8") as fh:
        whole = fh.read()
    # was eq_checks.py:905
    check("databases: a cut-off copy is fetched again (a whole one is reused)", len(fetched) == 1 and whole.count("\n") == 80,
          (fetched, whole.count("\n")))


def test_refresh_asked_during_one_runs_after(db_guard, monkeypatch, check):
    # a refresh asked for during one runs right after it (a database added then wasn't loaded)
    assert not databases._state["loading"], "the database lists were still loading as the test began"
    runs = []
    monkeypatch.setattr(databases, "directory", lambda refresh=False: [])
    monkeypatch.setattr(databases, "refresh_now", lambda sites, force=False: (runs.append(1), time.sleep(0.3),
                                                                              databases._state.update(loading=False)))
    databases.start_refresh(settings.DEFAULTS)
    time.sleep(0.05)  # (the second one asked for while the first is loading: it takes 0.3 s)
    databases.start_refresh(settings.DEFAULTS)
    end = time.monotonic() + qt.time_limit(2)  # (the old check: 40 looks, 0.05 s apart)
    while time.monotonic() < end:
        time.sleep(0.05)
        if not databases._state["loading"] and len(runs) == 2:
            break
    # was eq_checks.py:922
    check("databases: a refresh asked for during one runs right after it", len(runs) == 2, runs)


def test_only_web_addresses_from_squiglink_list(db_guard, monkeypatch, tmp_path, check):
    # squig.link's list is another site's: only web addresses are kept (they become links and downloads)
    monkeypatch.setattr(databases, "DIRECTORY_PATH", os.path.join(tmp_path, "odd squigsites.json"))
    textfile.write_json(databases.DIRECTORY_PATH, {"time": time.time(), "items": [ITEM, dict(ITEM, url="javascript:alert(1)"),
                                                                                  dict(ITEM, url="file:///C:/x")]})
    odd = databases.directory()
    # was eq_checks.py:1041
    check("databases: only web addresses from squig.link's list", odd == [ITEM], odd)


def test_squiglink_list_in_background(db_guard, monkeypatch, tmp_path, check):
    # the database lists start in the background: squig.link's list (the network) never holds up the window; a failed
    # try isn't repeated for a while (eq_checks.py lines 828-853, checked at line 1063). The stood-in fetch sleeps
    # time_limit(0.5) and the limit is time_limit(0.3): on a busy PC both get longer together, so a refresh that waits
    # for the list still goes past the limit at any time factor, as in the old check (0.5 s against 0.3 s)
    seen, tries = [], []
    nap = qt.time_limit(0.5)
    monkeypatch.setattr(databases, "refresh_now", lambda sites, force=False: databases._state.update(loading=False))
    monkeypatch.setattr(databases, "sites_for", lambda cfg: [])
    with monkeypatch.context() as m:
        m.setattr(databases, "directory", lambda refresh=False: (seen.append(threading.get_ident()), time.sleep(nap)))
        t0 = time.time()
        databases.start_refresh(settings.DEFAULTS)
        quick = time.time() - t0
        end = time.monotonic() + qt.time_limit(2.5)  # (the old check: 50 looks, 0.05 s apart)
        while databases._state["loading"] and time.monotonic() < end:
            time.sleep(0.05)
    # (squig.link's list as saved long ago; fetching it fails, as offline)
    monkeypatch.setattr(databases, "DIRECTORY_PATH", os.path.join(tmp_path, "old squigsites.json"))
    textfile.write_json(databases.DIRECTORY_PATH, {"time": 0, "items": [ITEM]})
    monkeypatch.setattr(databases, "_get", lambda *a, **k: (tries.append(1), (_ for _ in ()).throw(OSError("offline")))[1])
    lists = [databases.directory(), databases.directory(), databases.added_site("https://a.squig.link/")]
    monkeypatch.undo()  # (put back before checking, as the old checks did; db_guard puts back the failed try's time)
    # was eq_checks.py:1063
    check("databases: squig.link's list is fetched in the background (the window doesn't wait); a failed try isn't "
          "repeated at once", quick < qt.time_limit(0.3) and seen and seen[0] != threading.get_ident() and len(tries) == 1
          and lists[0] == [ITEM], (quick, seen, tries))


def test_refresh_after_failed_one(api, db_guard, monkeypatch, check):
    # (nothing loaded for real: stand-ins that just finish; the last refresh failed a moment ago)
    monkeypatch.setattr(databases, "refresh_now", lambda sites, force=False: databases._state.update(loading=False))
    monkeypatch.setattr(databases, "directory", lambda refresh=False: [])
    monkeypatch.setitem(databases._state, "updated", time.time())
    monkeypatch.setitem(databases._state, "sites", [{"name": "all", "error": "x", "count": 0}])
    r = api.call("/api/db/refresh", {})
    end = time.monotonic() + qt.time_limit(5)
    while databases._state.get("loading") and time.monotonic() < end:
        time.sleep(0.05)
    # was eq_checks.py:2214
    check("databases: a refresh after a failed one isn't refused with \"Missing 'url'\"", "url" not in str(r.get("error", "")), r)
