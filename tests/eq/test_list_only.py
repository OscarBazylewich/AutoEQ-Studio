"""List-only databases (eq\\databases.py, 2026-11-12): the measurements AND the targets of a database that does not
let other programs download its files are in the lists, each with the link that opens it on the website (the graph
tool's share link, or the page of the database for modernGraphTool); a download that the website refuses (HTTP 401
or 403 for each address) makes any graph-page database list only (kept with its time, loaded again, tried again
after 7 days), a 404, a network error or AutoEq's refusal does not; the service answers such a Use with the entry
to trace, and Which measurement lists such entries with their links.

Nothing is downloaded: each test stands in for databases._get (db_guard) and keeps the lists and the refusals in its
own temporary folder; online is stood in for net.offline() only."""
import threading
import time
import urllib.error

import pytest

import net
from eq import compare, databases, service

URL = "https://fake.squig.link/"
SITE = {"name": "Fake site", "url": URL, "short": "Fake", "group": "iem"}
CURVE = "".join(f"{20 * 1.1 ** i:.2f}\t{80 + i % 5}\n" for i in range(80))
CONF = {"base": URL + "data/", "phone_book": URL + "data/phone_book.json", "samples": 0, "channels": ["L", "R"],
        "targets": [{"type": "Reference", "files": ["Harman IE 2019", "IEF Neutral 2023"]}]}
MEAS = [{"kind": "measurement", "name": "Truthear Gate", "sub": "Truthear", "tag": "Fake", "ref": {"file": "Gate"}},
        {"kind": "measurement", "name": "Moondrop Aria (2023)", "sub": "Moondrop", "tag": "Fake",
         "ref": {"file": "Aria 2023"}}]
TARGET = {"kind": "target", "name": "Harman IE 2019", "sub": "Reference", "tag": "Fake",
          "ref": {"file": "Harman IE 2019 Target"}}


def _http(code):
    def get(url, **k):
        raise urllib.error.HTTPError(url, code, "made in the test", None, None)
    return get


@pytest.fixture
def lists(db_guard, monkeypatch, tmp_path):
    """The lists of `sites` loaded from a made index (no internet), in this test's folder, online (net.offline only),
    and the downloads of the test taken away after it. Returns load(sites, items, conf)."""
    monkeypatch.setattr(databases, "CACHE_PATH", str(tmp_path / "dbs.json"))
    monkeypatch.setattr(databases, "LIST_ONLY_PATH", str(tmp_path / "list_only.json"))
    monkeypatch.setattr(databases, "DOWNLOAD_DIR", str(tmp_path / "downloads"))
    monkeypatch.setattr(net, "offline", lambda: False)
    made = {}

    def load(sites, items=None, conf=None, force=True):
        for s in sites:
            made[s["url"]] = (list(MEAS + [TARGET] if items is None else items), dict(conf or CONF))
        monkeypatch.setattr(databases, "_index_squig", lambda s: made[s["url"]])
        databases.refresh_now(sites, force=force)
        return [it for it in databases.items() if it["site_url"] in {s["url"] for s in sites}]
    return load


def _by_name(entries):
    return {(it["kind"], it["name"]): it for it in entries}


def test_targets_of_a_marked_database_with_links(lists, check):
    # (the lists of 1.6.1 left the targets of such a database out: they are added from its config)
    got = _by_name(lists([dict(SITE, browse=True)], items=MEAS))
    links = {k: it.get("link") for k, it in got.items()}
    check("list only: each target of a database that does not let other programs download (its config) is in the "
          "lists as a target, with the share link of its file \"<name> Target\"",
          links.get(("target", "IEF Neutral 2023")) == URL + "?share=IEF_Neutral_2023_Target"
          and links.get(("target", "Harman IE 2019")) == URL + "?share=Harman_IE_2019_Target"
          and got[("target", "IEF Neutral 2023")]["tag"] == "Fake"
          and got[("target", "IEF Neutral 2023")]["sub"] == "Reference", links)
    check("list only: each measurement of such a database has the share link of its file",
          links.get(("measurement", "Truthear Gate")) == URL + "?share=Gate"
          and links.get(("measurement", "Moondrop Aria (2023)")) == URL + "?share=Aria_2023", links)
    again = _by_name(lists([dict(SITE, browse=True)], items=MEAS + [TARGET]))
    check("list only: a target that the list already has is there one time",
          sum(1 for it in databases.items() if it["name"] == "Harman IE 2019") == 1
          and again[("target", "Harman IE 2019")]["id"] == got[("target", "Harman IE 2019")]["id"],
          [it["name"] for it in databases.items()])
    st = {s["url"]: s for s in databases.status()["sites"]}
    check("list only: the status of the lists says list only, and counts its targets",
          st[URL]["list_only"] is True and st[URL]["count"] == 4, st[URL])


def test_modern_graph_tool_link_is_the_page(lists, check):
    got = lists([dict(SITE, browse=True)], conf=dict(CONF, targets_base=URL + "data/target/"))
    check("list only: for modernGraphTool (no known share link) the link of each entry is the page of the database",
          got and all(it.get("link") == URL for it in got), [it.get("link") for it in got])


def test_saved_lists_keep_the_links_for_version_1_6_1(db_guard, monkeypatch, tmp_path, check):
    # (2026-11-13, the verifier's SF-a: a user can install 1.6.1 again. It reads the links only from the saved lists,
    # and without them a Use of an entry of Hangout.Audio gave HTTP 403 until its lists were 3 days old)
    import json
    monkeypatch.setattr(databases, "CACHE_PATH", str(tmp_path / "dbs.json"))
    monkeypatch.setattr(databases, "LIST_ONLY_PATH", str(tmp_path / "list_only.json"))
    monkeypatch.setattr(net, "offline", lambda: False)
    book = [{"name": "Truthear", "phones": [{"name": "Gate", "file": "Gate"}]}]
    monkeypatch.setattr(databases, "_squig_config", lambda s: dict(CONF))
    monkeypatch.setattr(databases, "_get", lambda url, **k: (json.dumps(book), url))
    site = dict(SITE, browse=True)
    databases.refresh_now([site], force=True)
    # (1.6.1 (357d228) loads the saved lists so: each entry of the file as it is, with the name and the address of
    # its database)
    saved = [dict(it, site=site["name"], site_url=URL) for it in databases.load_cache()[URL]["items"]]
    links = {(it["kind"], it["name"]): it.get("link") for it in saved}
    check("list only: the saved lists keep the links of a marked database (version 1.6.1 reads them from there)",
          links == {("measurement", "Truthear Gate"): URL + "?share=Gate",
                    ("target", "Harman IE 2019"): URL + "?share=Harman_IE_2019_Target",
                    ("target", "IEF Neutral 2023"): URL + "?share=IEF_Neutral_2023_Target"}, links)
    now = {(it["kind"], it["name"]): it.get("link") for it in databases.items()}
    check("list only: this version gives the same links to the entries of the lists", now == links, now)


def test_link_of_an_address_with_a_query_and_of_a_name_with_a_comma(lists, eq_cfg, check):
    # (2026-11-13, the verifier's SF-f: an added address with a query got a second "?"; the graph tool divides the
    # names of its share link at each comma (from memory, not verified): such an entry gets the page of the database)
    query = "https://graphs.example.org/iems/?lang=en"
    check("list only: the share link of an address with a query adds “&share=”, not a second “?”",
          databases.entry_link(query, {"ref": {"file": "Aria 2023"}}, CONF) == query + "&share=Aria_2023",
          databases.entry_link(query, {"ref": {"file": "Aria 2023"}}, CONF))
    got = _by_name(lists([dict(SITE, browse=True)], items=MEAS,
                         conf=dict(CONF, targets=[{"type": "Reference", "files": ["Harman, 2019"]}])))
    comma = got[("target", "Harman, 2019")]
    e = service.call("/api/db/entry", {"id": comma["id"]})["entry"]
    check("list only: an entry whose file name has a comma gets the page of the database, and the service says that "
          "the link is the page (the wait window then tells the user to select the entry)",
          comma.get("link") == URL and e["link"] == URL and e["site_page"] is True, e)
    gate = service.call("/api/db/entry", {"id": got[("measurement", "Truthear Gate")]["id"]})["entry"]
    check("list only: the other entries of that database keep their share links",
          gate["link"] == URL + "?share=Gate" and gate["site_page"] is False, gate)
    # (the final verification's L02: a test with only "Harman, 2019" did not see a check for a comma and a space)
    tight = {f: databases.entry_link(URL, {"ref": {"file": f}}, CONF) for f in ("Harman,2019", "A,B Target", "Gate")}
    check("list only: a file name with a comma and no space after it also gets the page of the database",
          tight == {"Harman,2019": URL, "A,B Target": URL, "Gate": URL + "?share=Gate"}, tight)


def test_service_says_a_modern_graph_tool_link_is_the_page(lists, eq_cfg, check):
    # (the verifier's M17: no test gave the service a link to the page of a database)
    got = lists([dict(SITE, browse=True)], conf=dict(CONF, targets_base=URL + "data/target/"))
    e = service.call("/api/db/entry", {"id": got[0]["id"]})["entry"]
    check("list only: /api/db/entry says site_page for a link to the page of the database (modernGraphTool)",
          e["link"] == URL and e["site_page"] is True, e)


def test_a_downloadable_database_has_no_links(lists, check):
    got = lists([SITE])
    check("list only: the entries of a database that downloads have no link (its targets as usual)",
          got and not any(it.get("link") for it in got)
          and sorted(it["name"] for it in got if it["kind"] == "target") == ["Harman IE 2019"], got)


def _refused(lists, monkeypatch, code, site=SITE):
    entries = lists([site])
    monkeypatch.setattr(databases, "_get", _http(code))
    gate = next(it for it in entries if it["name"] == "Truthear Gate")
    try:
        databases.download(gate["id"], lambda t: 99)
        return None, gate
    except Exception as e:  # noqa: BLE001
        return e, gate


@pytest.mark.parametrize("code", [403, 401])
def test_refusal_makes_the_database_list_only(lists, monkeypatch, code, check):
    t0 = time.time()
    changes = databases.status()["changes"]
    err, gate = _refused(lists, monkeypatch, code)
    mine = [it for it in databases.items() if it["site_url"] == URL]
    got = _by_name(mine)
    # (the verifier's M34: with the links given only to the first entry, the other entries were in the lists two
    # times, and a dict by name did not show it)
    check("list only: the refusal gives each entry of that database its link one time: no entry two times, no "
          "entry lost, and the target of the config added",
          sorted((it["kind"], it["name"]) for it in mine) == sorted(
              [("measurement", "Truthear Gate"), ("measurement", "Moondrop Aria (2023)"),
               ("target", "Harman IE 2019"), ("target", "IEF Neutral 2023")])
          and len({it["id"] for it in mine}) == len(mine), [(it["kind"], it["name"], it["id"]) for it in mine])
    # (the verifier's M14: Find… asks for its rows again when this number changes; no new refresh of the lists
    # occurs in this test)
    check("list only: the refusal changes the number of changes of the lists (Find… then shows the links)",
          databases.status()["changes"] > changes + 1, (changes, databases.status()["changes"]))
    check(f"list only: a download refused with HTTP {code} for each address gives ListOnly, with the entry and the "
          "words of the message", isinstance(err, databases.ListOnly) and err.entry_id == gate["id"]
          and str(err) == databases.REFUSED_NOTE.format(site="Fake site"), repr(err))
    at = databases.refusals().get(databases.norm_url(URL))
    check("list only: the refusal is kept with its time", at is not None and t0 - 1 <= at <= time.time() + 1,
          databases.refusals())
    check("list only: at once, each entry of that database (measurements and targets) has its link, the targets of "
          "the config too", all(it.get("link") for it in got.values())
          and got[("measurement", "Truthear Gate")]["link"] == URL + "?share=Gate"
          and got[("target", "IEF Neutral 2023")]["link"] == URL + "?share=IEF_Neutral_2023_Target"
          and got[("measurement", "Truthear Gate")]["id"] == gate["id"], {k: v.get("link") for k, v in got.items()})
    check("list only: the status of the lists says list only at once",
          any(s["url"] == URL and s.get("list_only") for s in databases.status()["sites"]),
          databases.status()["sites"])


def _use(entry_id):
    """databases.download of the entry: its error (None when it downloads)."""
    try:
        databases.download(entry_id, lambda t: 99)
        return None
    except Exception as e:  # noqa: BLE001
        return e


def test_refusal_while_the_lists_load_keeps_the_links(lists, monkeypatch, check):
    # (2026-11-13, the verifier's case MF1: the refusal came after the refresh read the marks and before it gave the
    # items. The refresh then gave the items with no links, and Find… opened an empty address)
    lists([SITE])
    monkeypatch.setattr(databases, "_get", _http(403))
    gate = next(it for it in databases.items() if it["name"] == "Truthear Gate")["id"]
    real_assign, use = databases.assign_ids, {}

    def assign_then_refuse(entries):
        real_assign(entries)
        if "thread" not in use and threading.current_thread().name == "refresh":
            # (a Use refused at this moment, in a thread of its own; its wait is limited: with the lock it waits for
            # the end of the refresh)
            use["thread"] = threading.Thread(target=lambda: use.__setitem__("err", _use(gate)))
            use["thread"].start()
            use["thread"].join(2.0)
    monkeypatch.setattr(databases, "assign_ids", assign_then_refuse)
    th = threading.Thread(target=lambda: databases.refresh_now([SITE], force=False), name="refresh")
    th.start()
    th.join(60)
    use["thread"].join(60)
    it = databases.item(gate)
    st = {s["url"]: s.get("list_only") for s in databases.status()["sites"]}
    check("list only: a refusal while the lists load keeps its links and the list-only status of the database",
          isinstance(use.get("err"), databases.ListOnly) and it.get("link") == URL + "?share=Gate"
          and st.get(URL) is True and databases.norm_url(URL) in databases.refusals(),
          (repr(use.get("err")), it.get("link"), st))


def test_two_refusals_of_two_databases_at_the_same_time(lists, monkeypatch, check):
    # (2026-11-13, the verifier's case MF2: each refusal read the items, then gave them with the links of its own
    # database only: the links of one database were lost. Which measurement downloads in parallel threads)
    other = dict(SITE, name="Other site", url="https://other.squig.link/", short="Other")
    lists([SITE, other])
    bar = threading.Barrier(2)
    real_assign = databases.assign_ids

    def slow_assign(entries):  # (the two refusals at the same point: both read the items before each gives them)
        try:
            bar.wait(2)
        except threading.BrokenBarrierError:
            pass
        return real_assign(entries)
    monkeypatch.setattr(databases, "assign_ids", slow_assign)
    monkeypatch.setattr(databases, "_get", _http(403))
    ids = [next(it["id"] for it in databases.items() if it["site_url"] == u and it["name"] == "Truthear Gate")
           for u in (URL, other["url"])]
    out = [None, None]
    th = [threading.Thread(target=lambda i=i: out.__setitem__(i, _use(ids[i]))) for i in range(2)]
    for t in th:
        t.start()
    for t in th:
        t.join(60)
    links = {u: sum(1 for it in databases.items() if it["site_url"] == u and it.get("link"))
             for u in (URL, other["url"])}
    count = {u: sum(1 for it in databases.items() if it["site_url"] == u) for u in (URL, other["url"])}
    st = {s["url"]: s.get("list_only") for s in databases.status()["sites"]}
    check("list only: two refusals of two databases at the same time give each database its links and its status",
          all(isinstance(o, databases.ListOnly) for o in out) and links == count and all(count.values())
          and st.get(URL) is True and st.get(other["url"]) is True
          and {databases.norm_url(URL), databases.norm_url(other["url"])} <= set(databases.refusals()),
          (out, links, count, st, databases.refusals()))


def test_other_errors_are_not_a_refusal(lists, monkeypatch, check):
    seen = {}
    for name, fn in (("404", _http(404)), ("500", _http(500)), ("network", lambda url, **k: (_ for _ in ()).throw(
            OSError("no connection"))), ("time-out", lambda url, **k: (_ for _ in ()).throw(TimeoutError("slow")))):
        err, _gate = _refused(lists, monkeypatch, None)
        monkeypatch.setattr(databases, "_get", fn)
        try:
            databases.download(_gate["id"], lambda t: 99)
        except Exception as e:  # noqa: BLE001
            err = e
        seen[name] = (type(err).__name__, bool(databases.refusals()),
                      any(it.get("link") for it in databases.items() if it["site_url"] == URL))
    check("list only: a 404, an HTTP 500, a network error and a time-out are errors as before (no mark, no link)",
          all(v == ("ValueError", False, False) for v in seen.values()), seen)
    answers = iter([403, 404] * 8)
    monkeypatch.setattr(databases, "_get", lambda url, **k: _http(next(answers))(url))
    gate = next(it for it in databases.items() if it["name"] == "Truthear Gate")
    try:
        databases.download(gate["id"], lambda t: 99)
        err = None
    except Exception as e:  # noqa: BLE001
        err = e
    check("list only: a refusal of some addresses only (the others 404) is not a refusal of the entry",
          type(err) is ValueError and not databases.refusals(), repr(err))


def test_autoeq_refusal_stays_an_error(lists, monkeypatch, check):
    auto = {"name": "AutoEq (GitHub)", "url": "https://github.com/jaakkopasanen/AutoEq", "short": "AutoEq",
            "type": "autoeq", "group": "all"}
    item = {"kind": "measurement", "name": "Truthear Gate", "sub": "Fahryst", "tag": "Fahryst",
            "ref": {"url": "https://raw.githubusercontent.com/x/Truthear%20Gate.csv"}}
    monkeypatch.setattr(databases, "_index_autoeq", lambda s: ([item], {}))
    entries = lists([auto])
    monkeypatch.setattr(databases, "_get", _http(403))
    try:
        databases.download(entries[0]["id"], lambda t: 99)
        err = None
    except Exception as e:  # noqa: BLE001
        err = e
    check("list only: a refusal by AutoEq (GitHub, not a graph page) stays an error, with no mark",
          type(err) is ValueError and not databases.refusals() and not databases.list_only(auto)
          and not any(it.get("link") for it in databases.items()), repr(err))


def test_mark_saved_loaded_and_tried_again(lists, monkeypatch, check):
    _refused(lists, monkeypatch, 403)
    # (the lists made again from the saved list, not downloaded: the mark comes from its file)
    again = _by_name(lists([SITE], force=False))
    check("list only: the mark is saved and loaded: the next lists have the links",
          again and all(it.get("link") for it in again.values()), {k: v.get("link") for k, v in again.items()})
    d = databases.refusals()
    d[databases.norm_url(URL)] = time.time() - 8 * 24 * 3600
    import textfile
    textfile.write_json(databases.LIST_ONLY_PATH, {"sites": d})
    databases.load_refusals()  # (the app reads the file at the start and keeps the marks in memory)
    old = _by_name(lists([SITE], force=False))
    check("list only: 8 days after the mark, the lists have no links for it (the next Use tries the download)",
          old and not any(it.get("link") for it in old.values()) and not databases.list_only(SITE), old)
    fetched = []
    monkeypatch.setattr(databases, "_get", lambda url, **k: (fetched.append(url), (CURVE, url))[1])
    files, _it = databases.download(old[("measurement", "Truthear Gate")]["id"], lambda t: 99)
    check("list only: a new try that works downloads the entry and removes the mark",
          len(files) == 2 and fetched and databases.norm_url(URL) not in databases.refusals(), (files, fetched))
    six = time.time() - 6 * 24 * 3600
    textfile.write_json(databases.LIST_ONLY_PATH, {"sites": {databases.norm_url(URL): six}})
    databases.load_refusals()
    check("list only: 6 days after the mark, the database is still list only", databases.list_only(SITE),
          databases.refusals())


def test_a_mark_in_the_future_is_not_valid(lists, check):
    # (2026-11-13, the verifier's SF-b: with the clock set back, a mark 30 days in the future kept the database list
    # only for 37 days)
    import textfile
    now = time.time()
    seen = {}
    for days in (30, 1, 0, -6):
        textfile.write_json(databases.LIST_ONLY_PATH, {"sites": {databases.norm_url(URL): now + days * 24 * 3600}})
        databases.load_refusals()
        seen[days] = databases.list_only(SITE, now=now)
    check("list only: a mark with a time in the future is not valid (the clock set back); a mark of now or of 6 "
          "days ago is", seen == {30: False, 1: False, 0: True, -6: True}, seen)


def test_a_damaged_mark_file_gives_no_error(lists, check):
    # (the final verification's L05: with a mark whose time is not a number, list_only() gave a TypeError in each
    # state of the service; the file is the user's, and a different program or a damaged disk can change it)
    import textfile
    other = databases.norm_url("https://other.squig.link/")
    seen = {}
    for name, d in (("text", {"sites": {databases.norm_url(URL): "abc", other: time.time()}}),
                    ("none", {"sites": {databases.norm_url(URL): None, other: time.time()}}),
                    ("a list", {"sites": [databases.norm_url(URL)]}), ("a list of all", [1, 2])):
        textfile.write_json(databases.LIST_ONLY_PATH, d)
        databases.load_refusals()
        try:
            seen[name] = (databases.list_only(SITE), sorted(databases.refusals()))
        except Exception as e:  # noqa: BLE001
            seen[name] = repr(e)
    good = (False, [other])
    check("list only: a damaged list_only.json (a time that is not a number, a list) gives no error: the damaged "
          "marks are not used, the good marks are", seen == {"text": good, "none": good, "a list": (False, []),
                                                            "a list of all": (False, [])}, seen)


def test_marks_are_read_from_the_file_only_at_the_start_and_kept_after_a_write(lists, monkeypatch, check):
    # (2026-11-13, the verifier's SF-c: list_only() read list_only.json at each call, 0.18 ms, for each database of
    # each state and each refresh)
    import textfile
    textfile.write_json(databases.LIST_ONLY_PATH, {"sites": {databases.norm_url(URL): time.time()}})
    reads, real = [], textfile.read_json
    monkeypatch.setattr(textfile, "read_json", lambda path, *a, **k: (
        reads.append(path) if path == databases.LIST_ONLY_PATH else None, real(path, *a, **k))[1])
    first = databases.list_only(SITE)
    for _ in range(100):
        databases.list_only(SITE)
    databases.refusals()
    n_first = len(reads)
    other = dict(SITE, name="Other site", url="https://other.squig.link/", short="Other")
    err, _gate = _refused(lists, monkeypatch, 403, site=other)  # (a refused download writes its mark)
    after = isinstance(err, databases.ListOnly) and databases.list_only(other)
    # (a write reads the file one more time: a second process can have kept a mark, the next test)
    check("list only: the marks are read from the file one time, then from the memory, and a written mark is in "
          "the memory at once", first and after and n_first == 1 and len(reads) == 2, (first, after, reads))


def test_a_mark_of_a_second_process_is_kept(lists, monkeypatch, check):
    # (2026-11-13, the final verification: download_all.py kept a mark in the file after the app read the marks; the
    # next write of the app, from its memory alone, removed that mark)
    import textfile
    lists([SITE])
    databases.load_refusals()
    other = databases.norm_url("https://other.squig.link/")
    textfile.write_json(databases.LIST_ONLY_PATH, {"sites": {other: time.time()}})  # (the second process)
    err, _gate = _refused(lists, monkeypatch, 403)
    saved = set((textfile.read_json(databases.LIST_ONLY_PATH) or {}).get("sites") or {})
    check("list only: a write of a mark keeps the mark that a second process kept in the file meanwhile",
          isinstance(err, databases.ListOnly) and saved == {other, databases.norm_url(URL)}, saved)


def test_added_database_learns_too(lists, monkeypatch, check):
    added = databases.added_site("https://graphs.example.org/iems/")
    err, gate = _refused(lists, monkeypatch, 403, site=added)
    got = [it for it in databases.items() if it["site_url"] == added["url"]]
    check("list only: a database that the user added gets the same: the mark and the links of its entries",
          isinstance(err, databases.ListOnly) and databases.list_only(added)
          and got and all(it.get("link", "").startswith(added["url"] + "?share=") for it in got)
          and any(it["kind"] == "target" for it in got), [(it["name"], it.get("link")) for it in got])


def test_service_answers_with_the_entry_to_trace(lists, monkeypatch, eq_cfg, check):
    entries = lists([SITE])
    monkeypatch.setattr(databases, "_get", _http(403))
    gate = next(it for it in entries if it["name"] == "Truthear Gate")
    r = service.call("/api/use", {"src": "db", "id": gate["id"], "kind": "measurement", "settings": eq_cfg})
    check("list only: /api/use on a refused download answers with the entry to trace and the message (no error)",
          r == {"list_only": {"id": gate["id"], "message": databases.REFUSED_NOTE.format(site="Fake site")}}, r)
    p = service.call("/api/preview", {"src": "db", "id": gate["id"], "settings": eq_cfg})
    check("list only: /api/preview on such an entry answers list only with the words of Use in Find…",
          p == {"list_only": {"id": gate["id"], "message": databases.BROWSE_NOTE.format(site="Fake site")}}, p)
    e = service.call("/api/db/entry", {"id": gate["id"]})["entry"]
    check("list only: /api/db/entry gives the link (not the page of the database)",
          e["link"] == URL + "?share=Gate" and e["site_page"] is False, e)


def test_first_refusal_from_preview_has_the_words_of_preview(lists, monkeypatch, eq_cfg, check):
    # (the verifier's M18: a refusal that came first from Preview gave the words of Use, "Thus, the app opens…",
    # but Preview opens nothing)
    entries = lists([SITE])
    monkeypatch.setattr(databases, "_get", _http(403))
    gate = next(it for it in entries if it["name"] == "Truthear Gate")
    p = service.call("/api/preview", {"src": "db", "id": gate["id"], "settings": eq_cfg})
    check("list only: /api/preview with the first refusal of a database answers list only with the words of Use in "
          "Find…, and the database is list only",
          p == {"list_only": {"id": gate["id"], "message": databases.BROWSE_NOTE.format(site="Fake site")}}
          and databases.list_only(SITE), p)


def test_which_measurement_lists_refused_entries_with_links(lists, monkeypatch, eq_cfg, check):
    lists([SITE])
    monkeypatch.setattr(databases, "_get", _http(403))
    monkeypatch.setattr(compare.library, "status", lambda with_items=False: {"items": []})
    r = compare.compare(eq_cfg, "truthear gate", None)
    check("list only: Which measurement lists an entry whose download was refused with its link, not as an error",
          [lnk["link"] for lnk in r["links"]] == [URL + "?share=Gate"] and not r["errors"] and not r["items"]
          and r["note"] == "The app found no measurements with that name that it can download.", r)
    r2 = compare.compare(eq_cfg, "truthear gate", None)
    check("list only: the next search lists it with its link at once (no download)",
          [lnk["link"] for lnk in r2["links"]] == [URL + "?share=Gate"] and not r2.get("errors"), r2)


def test_state_marks_a_learned_database(lists, monkeypatch, eq_cfg, check):
    monkeypatch.setattr(databases, "SITES", databases.SITES + [SITE])
    _refused(lists, monkeypatch, 403)
    st = service.state({})
    row = next((s for s in st["database_sites"] if s["url"] == URL), None)
    check("list only: the app's state marks a database that refused a download as one from a picture (Sources)",
          row is not None and row["browse"] is True, row)


def test_download_all_skips_a_learned_database(db_guard, monkeypatch, tmp_path, check):
    # (app\tools\download_all.py: the saved lists of the tests (43 entries; Hangout.Audio 5128's 7 are list only), and
    # squig.link's 7 after a refusal kept now: both are skipped)
    import io
    import sys
    import textfile
    from helpers import paths
    tool = paths.import_tool("download_all")
    monkeypatch.setattr(databases, "LIST_ONLY_PATH", str(tmp_path / "list_only.json"))
    textfile.write_json(databases.LIST_ONLY_PATH, {"sites": {databases.norm_url("https://squig.link/"): time.time()}})
    out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "argv", ["download_all.py", "--dry-run"])
    tool.main()
    out.flush()
    words = out.buffer.getvalue().decode("utf-8").splitlines()[0]
    check("list only: download_all.py skips the entries of a database that stopped a download in the last 7 days",
          words.startswith("43 entries in 6 databases; 14 skipped (list-only); 29 to get"), words)


def test_download_all_skips_a_marked_database_with_no_links_in_its_lists(db_guard, monkeypatch, tmp_path, check):
    # (the verifier's M32: the saved lists of the tests have the links of Hangout.Audio 5128, as 1.6.1 saved them.
    # Lists saved with no links (as the version before 2026-11-13 saved them) must also skip its 7 entries: the
    # mark of the database (SITES), not the links of its entries)
    import io
    import json
    import sys
    import textfile
    from helpers import paths
    tool = paths.import_tool("download_all")
    cache = databases.load_cache()
    for c in cache.values():
        for it in c.get("items") or [] if isinstance(c, dict) else []:
            it.pop("link", None)
    monkeypatch.setattr(databases, "CACHE_PATH", str(tmp_path / "dbs.json"))
    monkeypatch.setattr(databases, "LIST_ONLY_PATH", str(tmp_path / "list_only.json"))
    textfile.write_atomic(databases.CACHE_PATH, json.dumps(cache))
    out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "argv", ["download_all.py", "--dry-run"])
    tool.main()
    out.flush()
    words = out.buffer.getvalue().decode("utf-8").splitlines()[0]
    check("list only: download_all.py skips the entries of a database with the mark when its lists have no links",
          words.startswith("43 entries in 6 databases; 7 skipped (list-only); 36 to get"), words)
