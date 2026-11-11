"""Use on device › Update a profile on Make an EQ (ui\\eq_page_result.py over switcher\\core.py, 2026-11-10): any
result (here a calculated one) goes into a profile that you have, with no question first. The menu keeps its device
rows first, then a row Update “…” for each profile that is on for a device (the device in the keys' column), then the
submenu Update a profile with every profile, A to Z. The profile keeps its name, its file's name, its id and its
devices; the message names only the devices where it is on and offers Undo, which puts the old file back byte for
byte (or says why it can't). Also: a graphic profile as the target, the profile an EQ by hand came from when it can't
show all of it (off), a device that plays an EQ for 5 minutes (kept), read-only settings (refused). One page for the
file (the eq_screen fixture: a stand-in APO folder and one stand-in device, Headset (EarPods); a second one,
Speakers (Realtek), stood in where a test needs two)."""
import os

import pytest

import textfile
from helpers import eqpage
from switcher import devices as D

HEADSET = D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)
SPEAKERS = D.Endpoint("{6}", "Speakers", "Realtek", D.ACTIVE, True)
KEY, KEY2 = eqpage.DEVICE, "Speakers|Realtek"
EQ = "Preamp: -3 dB\r\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\r\n# a note\r\n"


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return path


def _bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _lines(text):
    """A text's lines that are not empty (Make an EQ's temporary file is its CRLF text written in text mode, so a
    profile's file read back as text has an empty line after each line)."""
    return [line for line in text.splitlines() if line.strip()]


def _rows(menu):
    """The words of a menu's rows (not its separators)."""
    return [a.text() for a in menu.actions() if not a.isSeparator()]


def _row(menu, start):
    return next(a for a in menu.actions() if not a.isSeparator() and a.text().startswith(start))


def _sub(page, title):
    """The submenu of Use on device with this title."""
    return next((a.menu() for a in page.use_menu.actions() if a.menu() is not None and a.text() == title), None)


def _profiles(sw, tmp, *specs, text=EQ):
    """Every profile removed, then these made: (name, {device key: "on" or "list"}). Returns {name: id}."""
    for pid in list(sw.profiles()):
        sw.remove_profile(pid)
    ids = {}
    for name, _ in specs:
        ids[name] = sw.import_profile(_write(os.path.join(tmp, textfile.safe_name(name, "EQ", 80) + ".txt"), text), name)
    for want in ("on", "list"):  # (on first: a device's only profile is switched on whatever was asked)
        for name, where in specs:
            for key, how in where.items():
                if how == want:
                    sw.add_to_device(key, ids[name], switch_on=how == "on")
    return ids


def _two_devices(sw, monkeypatch):
    """Speakers (Realtek) connected too (put back by the test's monkeypatch.undo, then sw.refresh)."""
    monkeypatch.setattr(sw, "_endpoints", lambda: [HEADSET, SPEAKERS])
    sw.refresh(quiet=True)


def _apart(sw, monkeypatch):
    monkeypatch.undo()
    sw.refresh(quiet=True)


def _file(sw, pid):
    return os.path.join(sw.apo.profiles, sw.profiles()[pid]["file"])


@pytest.fixture(scope="module")
def result(eq_screen):
    """A calculated result on the card (Best fit, quick)."""
    eq_screen.page.choose_app("apo")
    return eqpage.quick_run(eq_screen)


def test_no_profiles_no_update_rows(eq_screen, result, tmp_path, check):
    page, sw = eq_screen.page, eq_screen.sw
    _profiles(sw, str(tmp_path))
    page._fill_use_menu()
    rows = _rows(page.use_menu)
    check("update a profile: with no profiles the menu has no Update rows and no empty submenu",
          rows and rows[0].startswith("Headset (EarPods)") and not any(r.startswith("Update") for r in rows)
          and _sub(page, "Update a profile") is None and _sub(page, "Use for 5 minutes on") is not None, rows)


def test_menu_has_the_update_rows(eq_screen, result, tmp_path, check):
    from ui.window_parts import profile_line
    page, sw = eq_screen.page, eq_screen.sw
    ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}), ("Beta", {KEY: "list"}), ("alpha & co", {}))
    page._fill_use_menu()
    rows = _rows(page.use_menu)
    check("update a profile: the menu keeps the device rows first (one click), then a row Update “…” for each profile "
          "that is on with its device in the keys' column, then Update a profile, then Use for 5 minutes on",
          rows == ["Headset (EarPods)\tactive", "Update “Daily”\ton for Headset (EarPods)", "Update a profile",
                   "Use for 5 minutes on"], rows)
    sub = _sub(page, "Update a profile")
    check("update a profile: the submenu lists every profile A to Z, each with the devices where it is on, or “not on”; "
          "a name with & shows as it is",
          sub is not None and _rows(sub) == ["alpha && co\tnot on", "Beta\tnot on", "Daily\ton for Headset (EarPods)"]
          and all(a.isEnabled() for a in sub.actions()), sub and _rows(sub))
    flat, beta = _row(page.use_menu, "Update “Daily”"), _row(sub, "Beta")
    check("update a profile: each update row's tooltip says which devices use the EQ immediately and the profile's EQ "
          "at this time",
          "Headset (EarPods) uses it immediately" in flat.toolTip()
          and profile_line(sw.profiles()[ids["Daily"]]) in flat.toolTip()
          and "No device has this profile on" in beta.toolTip(), (flat.toolTip(), beta.toolTip()))


def test_one_row_for_a_profile_on_for_two_devices(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch)
    try:
        ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on", KEY2: "on"}))
        page._fill_use_menu()
        flats = [r for r in _rows(page.use_menu) if r.startswith("Update “")]
        tip = _row(page.use_menu, "Update “Daily”").toolTip()
        _row(page.use_menu, "Update “Daily”").trigger()
        message = said[-1]
        eq_screen.undo()
    finally:
        _apart(sw, monkeypatch)
    check("update a profile: a profile that is on for two devices has one row, “on for … and 1 more device”; its "
          "tooltip and the message name the two devices",
          flats == ["Update “Daily”\ton for Headset (EarPods) and 1 more device"]
          and "Headset (EarPods) and Speakers (Realtek) use it immediately" in tip
          and "Headset (EarPods) and Speakers (Realtek) use the new EQ immediately" in message
          and sw.record(KEY)["active"] == ids["Daily"], (flats, tip, message))


def test_a_calculated_result_updates_a_profile(eq_screen, result, tmp_path, check, dialogs, monkeypatch):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch)
    try:
        ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on", KEY2: "list"}), ("Night", {KEY2: "on"}))
        pid = ids["Daily"]
        p = sw.profiles()[pid]
        name_before, file_before = p["name"], p["file"]
        rec_before = dict(p)
        old = _bytes(_file(sw, pid))
        lists = {k: (list(sw.record(k)["profiles"]), sw.record(k)["active"]) for k in (KEY, KEY2)}
        dialogs.reset()
        page._fill_use_menu()
        _row(page.use_menu, "Update “Daily”").trigger()
        text = page._apo_text("Update the profile")
        with open(_file(sw, pid), encoding="utf-8") as fh:
            now = fh.read()
        p = sw.profiles()[pid]
        with open(os.path.join(sw.apo.own, "switcher.txt"), encoding="utf-8") as fh:
            sw_text = fh.read()
        message, offered = said[-1], eq_screen.undo_offered()
        result_name = (page.name_edit.text().strip() or page.auto_name())[:80]
        source = os.path.basename(p["source"])
        after = {k: (list(sw.record(k)["profiles"]), sw.record(k)["active"]) for k in (KEY, KEY2)}
        check("update a profile: a calculated result goes into the profile's own file with no question; its name, its "
              "file's name, its id, its devices' lists and what is on stay; APO's file still includes it",
              text and _lines(now) == _lines(text) and "Filter 1:" in now
              and (p["name"], p["file"]) == (name_before, file_before) and pid in sw.profiles()
              and after == lists and "profiles\\Daily.txt" in sw_text and not dialogs.asked,
              (now[:200], after, lists, dialogs.asked))
        check("update a profile: the message names only the devices where the profile is on (not one that has it only "
              "in its list) and offers Undo",
              "Headset (EarPods) uses the new EQ immediately" in message and "Speakers" not in message and offered,
              message)
        check("update a profile: the profile's From becomes the result's name",
              source == textfile.safe_name(result_name, "EQ", 80) + ".txt", (source, result_name))
        eq_screen.undo()
        check("update a profile: Undo puts the profile's file back byte for byte, with its old counts and From, and "
              "says so",
              _bytes(_file(sw, pid)) == old and sw.profiles()[pid] == rec_before
              and "has its previous EQ again" in said[-1], (sw.profiles()[pid], rec_before, said[-1]))
    finally:
        _apart(sw, monkeypatch)


def test_update_from_the_submenu_of_a_profile_that_is_not_on(eq_screen, result, tmp_path, check):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}), ("Beta", {KEY: "list"}))
    old = _bytes(_file(sw, ids["Beta"]))
    active = {k: d["active"] for k, d in sw.s["devices"].items()}
    page._fill_use_menu()
    _row(_sub(page, "Update a profile"), "Beta\t").trigger()
    check("update a profile: Update a profile › a profile that is on for no device updates it; the message says no "
          "device has it on; no device changes",
          _bytes(_file(sw, ids["Beta"])) != old and "No device has it on." in said[-1]
          and {k: d["active"] for k, d in sw.s["devices"].items()} == active, (said[-1], active))


def test_undo_after_delete_or_change(eq_screen, result, tmp_path, check):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}))
    page._fill_use_menu()
    _row(page.use_menu, "Update “Daily”").trigger()
    sw.remove_profile(ids["Daily"])
    eq_screen.undo()
    deleted = said[-1]
    ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}))
    page._fill_use_menu()
    _row(page.use_menu, "Update “Daily”").trigger()
    with open(_file(sw, ids["Daily"]), "ab") as fh:  # (another program changes the file after the update)
        fh.write(b"Filter 9: ON PK Fc 200 Hz Gain 1 dB Q 1\r\n")
    changed_bytes = _bytes(_file(sw, ids["Daily"]))
    eq_screen.undo()
    changed = said[-1]
    check("update a profile: Undo after the profile was deleted, or after its file changed, says it is not possible "
          "and changes nothing",
          "You deleted “Daily” in Profiles: Undo is not possible." in deleted and ids["Daily"] in sw.profiles()
          and "The file of “Daily” changed after the update: Undo is not possible." in changed
          and _bytes(_file(sw, ids["Daily"])) == changed_bytes, (deleted, changed))


def test_a_graphic_profile_can_be_the_target(eq_screen, result, tmp_path, check):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    ids = _profiles(sw, str(tmp_path), ("Wavelet", {KEY: "on"}), text="GraphicEQ: 20 0; 1000 2; 20000 0\r\n")
    old = _bytes(_file(sw, ids["Wavelet"]))
    page._fill_use_menu()
    row = _row(page.use_menu, "Update “Wavelet”")
    on, tip = row.isEnabled(), row.toolTip()
    row.trigger()
    updated = _bytes(_file(sw, ids["Wavelet"])) != old
    eq_screen.undo()
    check("update a profile: a different profile that is a graphic EQ can be updated (its row is on, its tooltip shows "
          "“GraphicEQ”); Undo puts the graphic EQ back",
          on and "GraphicEQ" in tip and updated and _bytes(_file(sw, ids["Wavelet"])) == old
          and sw.profiles()[ids["Wavelet"]]["graphic"], (tip, said[-2:]))


def test_update_refused_when_settings_are_read_only(eq_screen, result, tmp_path, check, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}))
    old, n = _bytes(_file(sw, ids["Daily"])), len(said)
    page._fill_use_menu()
    boxes = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda parent, title, text, *a, **k: boxes.append((title, text))))
    monkeypatch.setattr(sw, "read_only", True)
    _row(page.use_menu, "Update “Daily”").trigger()
    monkeypatch.undo()
    check("update a profile: with the settings read-only the update is refused in a box titled Update the profile and "
          "the file stays",
          len(boxes) == 1 and boxes[0][0] == "Update the profile" and "settings" in boxes[0][1]
          and _bytes(_file(sw, ids["Daily"])) == old and len(said) == n, (boxes, said[n:]))


def test_a_device_trying_an_eq_keeps_it(eq_screen, result, tmp_path, check):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}))
    try:
        page.start_trial(KEY)
        page._fill_use_menu()
        _row(page.use_menu, "Update “Daily”").trigger()
        with open(os.path.join(sw.apo.own, "switcher.txt"), encoding="utf-8") as fh:
            sw_text = fh.read()
        trial = sw.trial and sw.trial["key"]
    finally:
        sw.end_trial()
    check("update a profile: updating the profile of a device that plays an EQ for 5 minutes leaves the 5 minutes "
          "running (APO's file still has _trying.txt); the message says the device uses the new EQ after that",
          trial == KEY and "_trying.txt" in sw_text
          and "A device with an EQ for 5 minutes, or with its EQ off to compare, uses the new EQ after that." in said[-1],
          (trial, said[-1]))


def test_own_profile_with_items_left_out_stays_protected(eq_screen, result, tmp_path, check):
    page, sw = eq_screen.page, eq_screen.sw
    ids = _profiles(sw, str(tmp_path), ("Graphic one", {KEY: "on"}), ("Daily", {KEY: "list"}),
                    text="Filter 1: ON PK Fc 500 Hz Gain 1 dB Q 1\r\nGraphicEQ: 20 0; 1000 2; 20000 0\r\n")
    page.set_way("hand", remember=False)
    page.fill_manual_sources()
    c = page.hand_source
    c.setCurrentIndex(next(k for k in range(c.count()) if c.itemText(k).startswith("Profile: Graphic one")))
    page.hand_start.click()
    run, _ = page.current()
    page._fill_use_menu()
    first = page.use_menu.actions()[0]
    sub = _sub(page, "Update a profile")
    own, other = _row(sub, "Graphic one\t"), _row(sub, "Daily\t")
    check("update a profile: the profile an EQ by hand came from, when the EQ can't show all of it, is off in the first "
          "row and in Update a profile, with the reason; other profiles' rows stay on",
          run.get("profile") == ids["Graphic one"] and run.get("left_out")
          and first.text().startswith("Update “Graphic one”") and not first.isEnabled() and not own.isEnabled()
          and "graphic EQ" in first.toolTip() and "graphic EQ" in own.toolTip() and other.isEnabled(),
          (run.get("profile"), run.get("left_out"), first.text(), own.toolTip()))
