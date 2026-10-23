"""Rigs and rig conversions (eq\\rigs.py, eq\\rigconv.py, eq\\rigmap.py; the shipped app\\eq\\rigdata.json and
rigmap.json): the rig tags, a file's rig and a target's from their names, a conversion by zero, the shipped
conversions complete, a database's own conversion (with a made-up database), the ranking's kinds of conversion, the
search list's marks, a headphones folder, a per-entry rig the app doesn't know, sources.json read once per list, and
a conversion without its error figures. Moved from eq_checks.py's module_checks.

The made-up database (the fake_db fixture) is added for the TestFakeDatabase checks only and taken away after them,
as the old checks added it and took it away around theirs."""
import os

import pytest

import textfile
from eq import databases, rigconv, rigmap, rigs, settings
from helpers import session, studio


def top():
    """The studio's own folder (your files' folders and data: the old checks' copy of the app, "top")."""
    return session.SESSION.studio


# ---------------------------------------------------------------- tags and names
def test_rig_tags(check):
    # was eq_checks.py:573
    check("rigs: tags", [rigs.rig_tag(r) for r in (("5128", True), ("711", False), (None, False))] == ["5128", "711?", ""])


def test_sample_iem_on_a_5128(check):
    meas = studio.measurement_paths()
    # was eq_checks.py:574
    check("rigs: the sample IEM is on a 5128", rigs.file_rig(os.path.basename(meas[0]))[0] == "5128", meas[0])


def test_target_rig_from_its_name(check):
    named = [rigs.target_rig(n, {})[0] for n in ("Harman IE 2019.txt", "Harman OE 2018 Linear.txt", "Crinacle OE.txt",
                                                  "IEF Neutral 2020.txt")]
    # was eq_checks.py:577
    check("rigs: target rig from its name (over-ear names before the IEM ones: review 2)",
          named == ["711", "43AG", "43AG", "711"], named)


def test_converting_by_zero(check):
    # was eq_checks.py:579
    check("rigs: converting by zero changes nothing", "\t1.000" in rigconv.convert_text("1000 1\n", [0.0] * len(rigconv.data()["grid"])))


def test_shipped_conversions_complete(check):
    # a database's own conversion (build_unit_conversions.py): used for files from that database, whatever its rig
    n = len(rigconv.data()["grid"])
    shipped = rigconv.data().get("units", [])
    # was eq_checks.py:584
    check("rig units: the shipped conversions are complete", shipped and all(
        u["from"] in rigs.RIGS and len(u["conversion"]) == n and len(u["uncertainty"]) == n and u["device"] in ("iem", "headphone")
        for u in shipped), len(shipped))


# ---------------------------------------------------------------- a database's own conversion (a made-up database)
@pytest.fixture(scope="class")
def fake_db():
    """A made-up database, "Fake DB", with its own conversion: two of its files recorded in sources.json as
    downloaded from it (one of them measured on a 711) and its conversion added to the shipped ones (eq_checks.py
    lines 587-594). Afterwards the conversion is taken out and sources.json written back as it was (lines 622-624).
    Gives the database's unit key."""
    saved_sources, n = rigs.sources(), len(rigconv.data()["grid"])
    with pytest.MonkeyPatch.context() as mp:
        try:
            rec = {"site_url": "https://fakedb.squig.link/", "site": "Fake DB", "name": "Test IEM"}
            rigs.record_source(["Test IEM (Fake DB) L1.txt"], rec)
            rigs.record_source(["Test IEM 711 (Fake DB) L1.txt"], dict(rec, rig="711"))
            key = rigmap.unit_key(rec)
            fake = {"unit": key, "name": "Fake DB", "device": "iem", "from": "5128", "rig": None, "models": 30,
                    "conversion": [2.0] * n, "uncertainty": [1.0] * n, "mismatch": [3.0] * n,
                    "bands": {"3000-6000": [3.0, 1.5], "10000-16000": [5.0, 3.0]}}
            mp.setitem(rigconv.data(), "units", [*rigconv.data().get("units", []), fake])
            yield key
        finally:
            textfile.write_json(rigs.SOURCES_PATH, saved_sources, indent=1)


class TestFakeDatabase:
    """The made-up database's checks, in the old order (eq_checks.py lines 595-621)."""

    def test_database_from_where_downloaded(self, fake_db, check):
        key = fake_db
        # was eq_checks.py:595
        check("rig units: a file's database from where it was downloaded", rigs.file_unit("Test IEM (Fake DB) L1.txt") == key
              and rigs.file_unit("unknown.txt") is None, rigs.file_unit("Test IEM (Fake DB) L1.txt"))

    def test_unknown_rig_gets_its_own_conversion(self, fake_db, check):
        c = settings.with_auto({})
        st = rigconv.status(c, "IEM 5128 DF.txt", [os.path.join(top(), "Measurements", "Test IEM (Fake DB) L1.txt")])
        # was eq_checks.py:599
        check("rig units: a database of unknown rig gets its own conversion", st.get("state") == "available" and st.get("unit") == "Fake DB"
              and st["meas_rig"] is None and st["conversion"][0] == 2.0, {k: st.get(k) for k in ("state", "unit", "meas_rig")})

    def test_own_conversion_before_the_rigs_average(self, fake_db, check):
        c = settings.with_auto({})
        st = rigconv.status(c, "IEM 5128 DF.txt", [os.path.join(top(), "Measurements", "Test IEM 711 (Fake DB) L1.txt")])
        # was eq_checks.py:602
        check("rig units: its own conversion before the rigs' average", st.get("unit") == "Fake DB" and st["meas_rig"] == "711", st.get("unit"))

    def test_none_from_that_rig_same_rig(self, fake_db, check):
        c = settings.with_auto({})
        st = rigconv.status(c, "Harman IE 2019.txt", [os.path.join(top(), "Measurements", "Test IEM 711 (Fake DB) L1.txt")])
        # was eq_checks.py:604
        check("rig units: none from that rig: as before (same rig)", st.get("state") == "same" and not st.get("unit"), st.get("state"))

    def test_ranking_kinds_of_conversion(self, fake_db, check):
        # ranking measurements ("Other measurements of this model"): the rig counts by the error left after converting
        key = fake_db
        own, avg = rigconv.expected("iem", "5128", None, key), rigconv.expected("iem", "5128", "711", None)
        # was eq_checks.py:608
        check("rig ranking: own conversion, the rigs' average, same rig, unknown", own["how"] == "own" and avg["how"] == "rigs"
              and 0 <= avg["rig_part"] < avg["error"] and rigconv.expected("iem", "5128", "5128", None)["how"] == "same"
              and rigconv.expected("iem", "5128", None, None)["how"] == "unknown", (own.get("how"), avg))

    def test_search_list_marks(self, fake_db, check):
        pu = rigconv.page_units()
        # was eq_checks.py:621
        check("rig units: the search list's marks", "Fake DB" in pu and pu["Fake DB"][0]["from"] == "5128", list(pu)[:3])


# ---------------------------------------------------------------- odd cases
def test_headphones_folder_without_a_record(eq_cfg, check):
    # IEM or headphone: the folder when a file has no record (the hint was " ")
    hp_dir = os.path.join(databases.DOWNLOAD_DIR, databases.folder_name("Earphones Archive headphones (5128)"))
    # (an HMS target: its name says no kind, so the measurement's folder decides; a 711 target means an IEM anyway)
    st_hp = rigconv.status(eq_cfg, os.path.join(top(), "Targets", "Neutral HMS target.txt"),
                           [os.path.join(hp_dir, "Some Model L.txt")])
    # was eq_checks.py:1002
    check("rigs: a file's folder says headphones when there's no record", st_hp.get("device") == "headphone",
          {k: st_hp.get(k) for k in ("state", "meas_rig", "target_rig", "device")})


def test_unknown_per_entry_rig_not_used(monkeypatch, check):
    # a per-entry rig the app doesn't know isn't used
    monkeypatch.setitem(rigmap._data, "d", {"units": {"https://m.squig.link": {"rig": "711", "confidence": "high", "models": 5, "wins": 4,
                                                                            "entries": {"Odd": "unknown", "Fine": "5128"}}}})
    odd_rig = rigmap.lookup({"site_url": "https://m.squig.link/", "name": "Odd"})
    fine_rig = rigmap.lookup({"site_url": "https://m.squig.link/", "name": "Fine"})
    monkeypatch.undo()  # (rigmap.json's own data back, as the old check's finally did)
    # was eq_checks.py:1013
    check("rigs: a per-entry rig the app doesn't know isn't used (it broke the comparison)",
          odd_rig[:2] == (None, False) and fine_rig[:2] == ("5128", True), (odd_rig, fine_rig))


def test_targets_rigs_read_sources_once(monkeypatch, check):
    # targets' rigs: sources.json read once per list, not once per target
    reads, real_sources = [], rigs.sources
    monkeypatch.setattr(rigs, "sources", lambda: (reads.append(1), real_sources())[1])
    rigs.library_rigs([{"kind": "target", "name": f"T{i}", "files": [f"T{i}.txt"], "folder": top()} for i in range(5)])
    monkeypatch.undo()
    # was eq_checks.py:1022
    check("rigs: the targets' rigs read sources.json once per list", len(reads) == 1, len(reads))


def test_conversion_without_error_figures_not_used(tmp_path, monkeypatch, check):
    # a rig conversion without its error figures isn't used (working out its error stopped the app's start)
    rigconv.data()  # (the shipped conversions loaded, so they are put back after the test)
    monkeypatch.delitem(rigconv._data, "d")
    monkeypatch.setattr(rigconv, "DATA_PATH", os.path.join(tmp_path, "odd rigdata.json"))
    good = {"device": "iem", "from": "5128", "to": "711", "models": 3, "bands": {"1000-3000": [2, 1]}, "conversion": [0, 0],
            "uncertainty": [1, 1], "mismatch": [0, 0]}
    textfile.write_json(rigconv.DATA_PATH, {"grid": [20, 20000], "pairs": [good, dict(good, bands={}, to="43AG")],
                                            "units": [{"unit": "u", "from": "711", "name": "U", "bands": None}]})
    kept_pairs, units = [p["to"] for p in rigconv.data()["pairs"]], rigconv.page_units()
    monkeypatch.undo()  # (the shipped conversions back, as the old check's finally did)
    # was eq_checks.py:1061
    check("rigs: a conversion without its error figures isn't used (no crash)", kept_pairs == ["711"] and units == {},
          (kept_pairs, units))
