"""Use on device › Update a profile on Make an EQ (ui\\eq_page_result.py over switcher\\core.py, 2026-11-10): any
result (here a calculated one) goes into a profile that you have, with no question first. The menu keeps its device
rows first, then a row Update “…” for each profile that is on for a device (the device in the keys' column), then the
submenu Update a profile with every profile, A to Z. The profile keeps its name, its file's name, its id and its
devices; the message names only the devices where it is on and offers Undo, which puts the old file back byte for
byte (or says why it can't). Also: a graphic profile as the target, the profile an EQ by hand came from when it can't
show all of it (off), a device that plays an EQ for 5 minutes or has its EQ off to compare (kept, and said apart, as
a device not connected and one without Equalizer APO), read-only settings (refused, Undo too), long names (cut, so the
menu stays narrow), "&" in a device's name, the file's bytes (CRLF, not CR CR LF). One page for the
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


def _two_devices(sw, monkeypatch, *more):
    """Speakers (Realtek) connected too, or these endpoints with Headset (put back by _apart)."""
    monkeypatch.setattr(sw, "_endpoints", lambda: [HEADSET, *(more or [SPEAKERS])])
    sw.refresh(quiet=True)


def _apart(sw, monkeypatch):
    """Only the stand-in device again: the others' records go too (else they stay as devices not connected)."""
    monkeypatch.undo()
    sw.refresh(quiet=True)
    for key in [k for k in sw.s["devices"] if k != KEY]:
        del sw.s["devices"][key]


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
          "at this time (no “it” or “its” that can be the EQ or the device)",
          flat.toolTip() == "The profile changes to this EQ. Headset (EarPods) uses the new EQ immediately. The EQ of the "
                            f"profile at this time: {profile_line(sw.profiles()[ids['Daily']])}."
          and "No device has this profile on" in beta.toolTip(), (flat.toolTip(), beta.toolTip()))
    from PySide6.QtGui import QAccessible
    face = QAccessible.queryAccessibleInterface(page.use_menu)
    names = [face.child(k).text(QAccessible.Name) for k in range(face.childCount())] if face else []
    check("update a profile: a screen reader reads an update row's profile name and where it is on",
          any(n.startswith("Update “Daily”") and "on for Headset (EarPods)" in n for n in names), names)


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
    # (since 2026-11-11 the message gives the first device and the count, as the row: first_names)
    check("update a profile: a profile that is on for two devices has one row, “on for … and 1 more device”; its "
          "tooltip names the two devices, the message the first and “1 more device”",
          flats == ["Update “Daily”\ton for Headset (EarPods) and 1 more device"]
          and "Headset (EarPods) and Speakers (Realtek) use the new EQ immediately" in tip
          and "Headset (EarPods) and 1 more device use the new EQ immediately" in message
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
        now = _bytes(_file(sw, pid))
        p = sw.profiles()[pid]
        with open(os.path.join(sw.apo.own, "switcher.txt"), encoding="utf-8") as fh:
            sw_text = fh.read()
        message, offered = said[-1], eq_screen.undo_offered()
        result_name = (page.name_edit.text().strip() or page.auto_name())[:80]
        source = os.path.basename(p["source"])
        after = {k: (list(sw.record(k)["profiles"]), sw.record(k)["active"]) for k in (KEY, KEY2)}
        check("update a profile: a calculated result goes into the profile's own file with no question, byte for byte "
              "(its CRLF line ends, not CR CR LF); its name, its file's name, its id, its devices' lists and what is "
              "on stay; APO's file still includes it",
              text and now == text.encode("utf-8") and b"\r\r\n" not in now and b"Filter 1:" in now
              and (p["name"], p["file"]) == (name_before, file_before) and pid in sw.profiles()
              and after == lists and "profiles\\Daily.txt" in sw_text and not dialogs.asked,
              (now[:200], after, lists, dialogs.asked))
        check("update a profile: the message names only the devices where the profile is on (not one that has it only "
              "in its list) and offers Undo",
              "Headset (EarPods) uses the new EQ immediately" in message and "Speakers" not in message and offered,
              message)
        check("update a profile: the profile's From becomes the result's name",
              source == textfile.safe_name(result_name, "EQ", 80, keep_ext=False) + ".txt", (source, result_name))
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
    gone = ids["Daily"]
    sw.remove_profile(gone)
    eq_screen.undo()
    deleted = said[-1]
    still_gone = gone not in sw.profiles() and not any(d["active"] == gone for d in sw.s["devices"].values())
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
          "You deleted “Daily” in Profiles: Undo is not possible." in deleted and still_gone
          and "The file of “Daily” changed after the app updated it: Undo is not possible." in changed
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
          "running (APO's file still has _trying.txt); the message says that device uses the new EQ after that, not "
          "immediately",
          trial == KEY and "_trying.txt" in sw_text
          and "Headset (EarPods) has an EQ for 5 minutes, or its EQ off to compare. It uses the new EQ after that."
          in said[-1] and "immediately" not in said[-1], (trial, said[-1]))


def test_a_device_with_its_eq_off_to_compare_keeps_it(eq_screen, result, tmp_path, check):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}))
    try:
        off = sw.compare_toggle(KEY)
        page._fill_use_menu()
        _row(page.use_menu, "Update “Daily”").trigger()
        compare = sw.compare and sw.compare["key"]
    finally:
        sw.compare_end()
    check("update a profile: updating the profile of a device with its EQ off to compare leaves it off; the message "
          "says that device uses the new EQ after that, not immediately",
          off and off[0] == "off" and compare == KEY
          and "Headset (EarPods) has an EQ for 5 minutes, or its EQ off to compare. It uses the new EQ after that."
          in said[-1] and "immediately" not in said[-1], (off, compare, said[-1]))


def test_apo_without_the_app_is_said(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    apo = "Equalizer APO does not use AutoEQ Studio: click Add AutoEQ Studio to APO… on the Devices screen."
    seen = []
    for on in ({KEY: "on"}, {KEY: "on", KEY2: "on"}):
        _two_devices(sw, monkeypatch)
        try:
            _profiles(sw, str(tmp_path), ("Daily", on))
            monkeypatch.setattr(sw.apo, "includes_studio", lambda: False)
            page._fill_use_menu()
            row = _row(page.use_menu, "Update “Daily”")
            tip = row.toolTip()
            row.trigger()
            seen.append((said[-1], tip))
        finally:
            _apart(sw, monkeypatch)
    one, two = seen
    check("update a profile: when Equalizer APO does not include AutoEQ Studio, no device uses the new EQ immediately: "
          "the message says so first, how to add it, then that the device uses the new EQ after that; the tooltip "
          "says the same",
          one[0] == f"The app updated “Daily”. {apo} Headset (EarPods) uses the new EQ after that."
          and f"{apo} Headset (EarPods) uses the new EQ after that. The EQ of the profile" in one[1]
          and "immediately" not in one[0] + one[1], one)
    check("update a profile: the same with two devices (“use”, plural; the message: the first and the count)",
          two[0] == f"The app updated “Daily”. {apo} Headset (EarPods) and 1 more device use the new EQ after that."
          and f"{apo} Headset (EarPods) and Speakers (Realtek) use the new EQ after that." in two[1]
          and "immediately" not in two[0] + two[1], two)


def _without_the_app(eq_screen, tmp_path, monkeypatch, on, *endpoints, compare=None):
    """The message and the tooltip of Update “Daily” (on for these devices; with none, the submenu's row) when
    Equalizer APO does not include AutoEQ Studio; compare: a device with its EQ off to compare meanwhile."""
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch, *endpoints)
    try:
        _profiles(sw, str(tmp_path), ("Daily", on))
        off = sw.compare_toggle(compare) if compare else ("off",)
        try:
            with monkeypatch.context() as mp:
                mp.setattr(sw.apo, "includes_studio", lambda: False)
                page._fill_use_menu()
                row = _row(page.use_menu, "Update “Daily”") if on else _row(_sub(page, "Update a profile"), "Daily\t")
                tip = row.toolTip()
                row.trigger()
        finally:
            if compare:
                sw.compare_end()
    finally:
        _apart(sw, monkeypatch)
    return said[-1], tip, off[0]


def test_apo_without_the_app_and_devices_not_used_now(eq_screen, result, tmp_path, check, monkeypatch):
    # (2026-11-11: the APO sentence was tested only with connected devices; a device not connected was said to use
    # the new EQ when you connect it, but APO uses it only after the app is added)
    apo = "Equalizer APO does not use AutoEQ Studio: click Add AutoEQ Studio to APO… on the Devices screen."
    line = "The EQ of the profile at this time: 1 filter, pre-amp -3 dB."
    away = D.Endpoint("{6}", "Speakers", "Realtek", D.UNPLUGGED, True)
    held = _without_the_app(eq_screen, tmp_path, monkeypatch, {KEY: "on"}, compare=KEY)
    words = (f"{apo} Headset (EarPods) has an EQ for 5 minutes, or its EQ off to compare. It uses the new EQ after "
             "that.")
    check("update a profile: Equalizer APO without the app and a device with its EQ off to compare only: the APO "
          "sentence first, then the held sentence, in the message and the tooltip",
          held == (f"The app updated “Daily”. {words}", f"The profile changes to this EQ. {words} {line}", "off"), held)
    one = _without_the_app(eq_screen, tmp_path, monkeypatch, {KEY2: "on"}, away)
    words = f"{apo} Speakers (Realtek) uses the new EQ after that, when you connect it."
    check("update a profile: Equalizer APO without the app and a device that is not connected only: the APO sentence, "
          "then the device uses the new EQ “after that, when you connect it”, in the message and the tooltip",
          one == (f"The app updated “Daily”. {words}", f"The profile changes to this EQ. {words} {line}", "off"), one)
    two = _without_the_app(eq_screen, tmp_path, monkeypatch, {KEY2: "on", "TV|NVIDIA": "on"}, away,
                           D.Endpoint("{7}", "TV", "NVIDIA", D.UNPLUGGED, True))
    words = f"{apo} Speakers (Realtek) and TV (NVIDIA) use the new EQ after that, when you connect them."
    short = f"{apo} Speakers (Realtek) and 1 more device use the new EQ after that, when you connect them."
    check("update a profile: the same with two devices that are not connected (“use … them”, plural; the message: "
          "the first and the count)",
          two == (f"The app updated “Daily”. {short}", f"The profile changes to this EQ. {words} {line}", "off"), two)
    none = _without_the_app(eq_screen, tmp_path, monkeypatch, {})
    check("update a profile: Equalizer APO without the app and a profile that no device has on: no APO sentence, only "
          "“No device has it on.” (the tooltip: “No device has this profile on.”)",
          none == ("The app updated “Daily”. No device has it on.",
                   f"The profile changes to this EQ. No device has this profile on. {line}", "off"), none)


def test_undo_refused_when_settings_are_read_only(eq_screen, result, tmp_path, check, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}))
    page._fill_use_menu()
    _row(page.use_menu, "Update “Daily”").trigger()
    updated, n = _bytes(_file(sw, ids["Daily"])), len(said)
    boxes = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda parent, title, text, *a, **k: boxes.append((title, text))))
    monkeypatch.setattr(sw, "read_only", True)
    eq_screen.undo()
    monkeypatch.undo()
    check("update a profile: with the settings read-only, Undo is refused in a box titled Update the profile, with no "
          "message, and the file keeps the update",
          len(boxes) == 1 and boxes[0][0] == "Update the profile" and len(said) == n
          and _bytes(_file(sw, ids["Daily"])) == updated, (boxes, said[n:]))


def test_three_devices_named_in_the_message(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch, SPEAKERS, D.Endpoint("{7}", "TV", "NVIDIA", D.ACTIVE, True))
    try:
        _profiles(sw, str(tmp_path), ("Daily", {KEY: "on", KEY2: "on", "TV|NVIDIA": "on"}))
        page._fill_use_menu()
        row = _row(page.use_menu, "Update “Daily”")
        text, tip = row.text(), row.toolTip()
        row.trigger()
        message = said[-1]
    finally:
        _apart(sw, monkeypatch)
    check("update a profile: a profile on for three devices: its row and the message name the first and “2 more "
          "devices”; its tooltip names the three, “A, B, and C”",
          text == "Update “Daily”\ton for Headset (EarPods) and 2 more devices"
          and "Headset (EarPods), Speakers (Realtek), and TV (NVIDIA) use the new EQ immediately." in tip
          and "Headset (EarPods) and 2 more devices use the new EQ immediately." in message,
          (text, tip, message))


def test_devices_not_connected_or_without_apo_are_said_apart(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch, D.Endpoint("{6}", "Speakers", "Realtek", D.UNPLUGGED, True),
                 D.Endpoint("{7}", "TV", "NVIDIA", D.ACTIVE, False))
    try:
        _profiles(sw, str(tmp_path), ("Daily", {KEY: "on", KEY2: "on", "TV|NVIDIA": "on"}))
        page._fill_use_menu()
        row = _row(page.use_menu, "Update “Daily”")
        tip = row.toolTip()
        row.trigger()
        message = said[-1]
    finally:
        _apart(sw, monkeypatch)
    check("update a profile: the message says that only a connected device with Equalizer APO uses the new EQ "
          "immediately, a device not connected uses it when you connect it, and Equalizer APO is not installed on "
          "the other; the tooltip says the same",
          message == "The app updated “Daily”. Headset (EarPods) uses the new EQ immediately. Speakers (Realtek) uses "
                     "the new EQ when you connect it. Equalizer APO is not installed on TV (NVIDIA) (refer to Devices)."
          and "Headset (EarPods) uses the new EQ immediately. Speakers (Realtek) uses the new EQ when you connect it. "
              "Equalizer APO is not installed on TV (NVIDIA) (refer to Devices)." in tip, (message, tip))


def test_a_device_name_with_and_sign_shows_as_it_is(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw = eq_screen.page, eq_screen.sw
    _two_devices(sw, monkeypatch, D.Endpoint("{7}", "TV", "R&D Audio", D.ACTIVE, True))
    try:
        _profiles(sw, str(tmp_path), ("Daily", {"TV|R&D Audio": "on"}))
        page._fill_use_menu()
        rows = _rows(page.use_menu)
        tries = _rows(_sub(page, "Use for 5 minutes on"))
    finally:
        _apart(sw, monkeypatch)
    check("update a profile: a device name with & shows as it is in the device rows, the update rows and Use for 5 "
          "minutes on (Qt reads one & as a key's mark)",
          "TV (R&&D Audio)\tconnected" in rows and "Update “Daily”\ton for TV (R&&D Audio)" in rows
          and "TV (R&&D Audio)" in tries, (rows, tries))


def test_long_names_do_not_make_the_menu_wide(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw = eq_screen.page, eq_screen.sw
    long_key = "Speakers|Realtek(R) High Definition Audio"
    name = ("Truthear x Crinacle Zero Red to Harman in-ear 2019 v2 - best fit 10f with a very long name, 80 ch")[:80]
    _two_devices(sw, monkeypatch, D.Endpoint("{8}", "Speakers", "Realtek(R) High Definition Audio", D.ACTIVE, True))
    try:
        ids = _profiles(sw, str(tmp_path), (name, {long_key: "on"}), ("Daily", {KEY: "on"}))
        page._fill_use_menu()
        sub = _sub(page, "Update a profile")
        wide = (page.use_menu.sizeHint().width(), sub.sizeHint().width())
        row = next(a for a in page.use_menu.actions() if a.text().startswith("Update “Truthear"))
        text, tip = row.text(), row.toolTip()
        short = _row(page.use_menu, "Update “Daily”").text()
    finally:
        _apart(sw, monkeypatch)
    check("update a profile: a profile name of 80 characters and a long Windows device name are cut with “…” so the "
          "menu and Update a profile stay narrower than 700 px; the tooltip has the whole name and the device; a short "
          "name stays whole",
          len(sw.profiles()[ids[name]]["name"]) == 80 and max(wide) < 700 and "…" in text and name not in text
          and text.startswith("Update “Truthear") and f"The profile “{name}” changes to this EQ." in tip
          and "Speakers (Realtek(R) High Definition Audio) uses the new EQ immediately." in tip
          and short == "Update “Daily”\ton for Headset (EarPods)", (wide, text, tip, short))
    first = text.split("\t")[0]
    check("update a profile: a long profile name is cut in the middle: the row keeps its start and its end (the end, "
          "“… 10f”, tells automatic names apart)",
          first.startswith("Update “" + name[:8]) and first.endswith(name[-5:] + "”") and "…" in first, first)


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
    why = ("Its file has items that this EQ cannot show (" + " · ".join(run.get("left_out") or []) + "): use this EQ as "
           "a new profile (click a device in this menu)")  # (2026-11-11: not "below", an adverb in STE)
    check("update a profile: the off row of a whole (short) name has the reason only, with a capital letter, and no "
          "“The profile “”, in the menu and in Update a profile",
          first.toolTip() == why and own.toolTip() == why and "The profile “" not in first.toolTip() + own.toolTip(),
          (first.toolTip(), own.toolTip()))


def test_an_eq_by_hand_updates_its_own_profile(eq_screen, result, tmp_path, check):
    # (after the test above: the page's way is By hand)
    page, sw = eq_screen.page, eq_screen.sw
    ids = _profiles(sw, str(tmp_path), ("A & B", {KEY: "on"}))
    pid = ids["A & B"]
    source = sw.profiles()[pid]["source"]
    page.set_way("hand", remember=False)
    page.fill_manual_sources()
    c = page.hand_source
    c.setCurrentIndex(next(k for k in range(c.count()) if c.itemText(k).startswith("Profile: A & B")))
    page.hand_start.click()
    page._fill_use_menu()
    rows = _rows(page.use_menu)
    page.use_menu.actions()[0].trigger()
    check("update a profile: an EQ by hand begun from a profile that is on has its Update “…” row first (a name with & "
          "as it is), with no second row for it; the update keeps the profile's From",
          rows[0] == "Update “A && B”\ton for Headset (EarPods)"
          and not any(r.startswith("Update “A") for r in rows[1:]) and sw.profiles()[pid]["source"] == source
          and "updated “A & B”" in eq_screen.said[-1], (rows, sw.profiles()[pid]["source"], source))


def test_own_profile_off_with_a_long_name_gives_the_whole_name(eq_screen, result, tmp_path, check):
    page, sw = eq_screen.page, eq_screen.sw
    name = ("Graphic one, a profile with a very long name that the menu cuts in the middle of it, end")[:80]
    ids = _profiles(sw, str(tmp_path), (name, {KEY: "on"}),
                    text="Filter 1: ON PK Fc 500 Hz Gain 1 dB Q 1\r\nGraphicEQ: 20 0; 1000 2; 20000 0\r\n")
    page.set_way("hand", remember=False)
    page.fill_manual_sources()
    c = page.hand_source
    c.setCurrentIndex(next(k for k in range(c.count()) if c.itemText(k).startswith("Profile: Graphic one, a")))
    page.hand_start.click()
    run, _ = page.current()
    page._fill_use_menu()
    first = page.use_menu.actions()[0]
    check("update a profile: the off row of the profile an EQ by hand came from, its name cut, has a tooltip that "
          "starts with the whole name, then the reason",
          run.get("profile") == ids[name] and not first.isEnabled() and "…" in first.text()
          and first.toolTip().startswith(f"The profile “{name}”: its file has items that this EQ cannot show (")
          and "graphic EQ" in first.toolTip(), (first.text(), first.toolTip()))


LONG_SPEAKERS = D.Endpoint("{8}", "Speakers", "Realtek(R) High Definition Audio", D.ACTIVE, True)
TV = D.Endpoint("{7}", "TV", "NVIDIA", D.ACTIVE, True)


def test_cut_on_words_keep_the_count(eq_screen, result, tmp_path, check, monkeypatch):
    from ui.eq_page_parts import UPDATE_ROOM
    page, sw = eq_screen.page, eq_screen.sw
    long_key = "Speakers|Realtek(R) High Definition Audio"
    _two_devices(sw, monkeypatch, LONG_SPEAKERS, TV)
    try:
        _profiles(sw, str(tmp_path), ("Night", {long_key: "on", "TV|NVIDIA": "on"}), ("Daily", {KEY: "on"}))
        page._fill_use_menu()
        row = _row(page.use_menu, "Update “Night”")
        sub = _sub(page, "Update a profile")
        sub_row = _row(sub, "Night\t")
        wide = (page.use_menu.sizeHint().width(), sub.sizeHint().width())
        fm = page.use_menu.fontMetrics()
        where, sub_where, tip = row.text().split("\t")[1], sub_row.text().split("\t")[1], row.toolTip()
    finally:
        _apart(sw, monkeypatch)
    check("update a profile: on words too long for their room cut the first device's name, not the count: the row "
          "ends with “and 1 more device”, has “…”, fits in its room, and the menus stay narrower than 700 px; the "
          "tooltip names the two devices",
          where.startswith("on for Speakers (Realtek") and "…" in where and where.endswith("… and 1 more device")
          and sub_where == where and fm.horizontalAdvance(where) <= fm.averageCharWidth() * UPDATE_ROOM
          and max(wide) < 700
          and "Speakers (Realtek(R) High Definition Audio) and TV (NVIDIA) use the new EQ immediately." in tip,
          (where, sub_where, wide, tip))
    # (one device only, its name wider than the room: cut too, 2026-11-11: only names of two or more were tested)
    dock = D.Endpoint("{9}", "Speakers", "Realtek(R) High Definition Audio, the second output of the dock", D.ACTIVE,
                      True)
    _two_devices(sw, monkeypatch, dock)
    try:
        _profiles(sw, str(tmp_path), ("Solo", {"Speakers|" + dock.conn: "on"}))
        page._fill_use_menu()
        fm = page.use_menu.fontMetrics()
        one = _row(page.use_menu, "Update “Solo”").text().split("\t")[1]
    finally:
        _apart(sw, monkeypatch)
    check("update a profile: the on words of one device with a name of 60 or more characters are cut too: “on for "
          "…” with “…”, in their room",
          len(f"Speakers ({dock.conn})") >= 60 and one.startswith("on for Speakers (Realtek") and "…" in one
          and " more device" not in one and fm.horizontalAdvance(one) <= fm.averageCharWidth() * UPDATE_ROOM, one)


def test_two_held_devices_are_said_in_the_plural(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch)
    try:
        _profiles(sw, str(tmp_path), ("Daily", {KEY: "on", KEY2: "on"}))
        try:
            page.start_trial(KEY)
            off = sw.compare_toggle(KEY2)
            page._fill_use_menu()
            row = _row(page.use_menu, "Update “Daily”")
            tip = row.toolTip()
            row.trigger()
            message = said[-1]
            held = (sw.trial and sw.trial["key"], sw.compare and sw.compare["key"])
        finally:
            sw.end_trial()
            sw.compare_end()
    finally:
        _apart(sw, monkeypatch)
    words = ("Headset (EarPods) and Speakers (Realtek) have an EQ for 5 minutes, or their EQ off to compare. They use "
             "the new EQ after that.")
    short = ("Headset (EarPods) and 1 more device have an EQ for 5 minutes, or their EQ off to compare. They use the "
             "new EQ after that.")
    check("update a profile: a device with an EQ for 5 minutes and a second with its EQ off to compare: the message "
          "and the tooltip say “have … their … They use” (the plural), and nothing “immediately”",
          off and off[0] == "off" and held == (KEY, KEY2) and message == f"The app updated “Daily”. {short}"
          and f"The profile changes to this EQ. {words} The EQ of the profile" in tip
          and "immediately" not in message + tip, (held, message, tip))


def test_two_devices_not_connected_are_said_in_the_plural(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch, D.Endpoint("{6}", "Speakers", "Realtek", D.UNPLUGGED, True),
                 D.Endpoint("{7}", "TV", "NVIDIA", D.UNPLUGGED, True))
    try:
        _profiles(sw, str(tmp_path), ("Daily", {KEY2: "on", "TV|NVIDIA": "on"}))
        page._fill_use_menu()
        row = _row(page.use_menu, "Update “Daily”")
        tip = row.toolTip()
        row.trigger()
        message = said[-1]
    finally:
        _apart(sw, monkeypatch)
    words = "Speakers (Realtek) and TV (NVIDIA) use the new EQ when you connect them."
    short = "Speakers (Realtek) and 1 more device use the new EQ when you connect them."
    check("update a profile: two devices that are not connected: the message and the tooltip say “use … them” (the "
          "plural)",
          message == f"The app updated “Daily”. {short}" and f" {words} The EQ of the profile" in tip, (message, tip))


def test_the_groups_are_said_in_their_sequence(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch, D.Endpoint("{6}", "Speakers", "Realtek", D.UNPLUGGED, True),
                 D.Endpoint("{7}", "TV", "NVIDIA", D.ACTIVE, False), D.Endpoint("{9}", "Monitor", "Dell", D.ACTIVE, True))
    try:
        _profiles(sw, str(tmp_path), ("Daily", {KEY: "on", KEY2: "on", "TV|NVIDIA": "on", "Monitor|Dell": "on"}))
        try:
            off = sw.compare_toggle(KEY)
            page._fill_use_menu()
            row = _row(page.use_menu, "Update “Daily”")
            tip = row.toolTip()
            row.trigger()
            message = said[-1]
        finally:
            sw.compare_end()
    finally:
        _apart(sw, monkeypatch)
    words = ("Monitor (Dell) uses the new EQ immediately. Headset (EarPods) has an EQ for 5 minutes, or its EQ off to "
             "compare. It uses the new EQ after that. Speakers (Realtek) uses the new EQ when you connect it. Equalizer "
             "APO is not installed on TV (NVIDIA) (refer to Devices).")
    check("update a profile: the message and the tooltip give the groups in this sequence: immediately, an EQ for 5 "
          "minutes or off to compare, not connected, no Equalizer APO (the held sentence in the tooltip too)",
          off and off[0] == "off" and message == f"The app updated “Daily”. {words}"
          and tip == f"The profile changes to this EQ. {words} The EQ of the profile at this time: 1 filter, pre-amp "
                     "-3 dB.", (message, tip))


def test_a_profile_on_only_for_a_device_that_windows_does_not_list(eq_screen, result, tmp_path, check, monkeypatch):
    # (2026-11-11: a device's record stays when Windows no longer lists it; nothing checked its profile's Update row)
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch)
    try:
        ids = _profiles(sw, str(tmp_path), ("Daily", {KEY2: "on"}))
        monkeypatch.setattr(sw, "_endpoints", lambda: [HEADSET])  # (Speakers gone from Windows' list, its record kept)
        sw.refresh(quiet=True)
        gone = sw.device(KEY2) is None and sw.record(KEY2)["active"] == ids["Daily"]
        page._fill_use_menu()
        rows = _rows(page.use_menu)
        row = next((a for a in page.use_menu.actions() if a.text().startswith("Update “Daily”")), None)
        tip = row.toolTip() if row else ""
        if row:
            row.trigger()
        message = said[-1]
    finally:
        _apart(sw, monkeypatch)
    words = "Speakers (Realtek) uses the new EQ when you connect it."
    check("update a profile: a profile that is on only for a device that Windows does not list has its Update row "
          "(“on for” that device); its tooltip and the message say the device uses the new EQ when you connect it",
          gone and "Speakers (Realtek)\tnot connected" in rows and "Update “Daily”\ton for Speakers (Realtek)" in rows
          and f"The profile changes to this EQ. {words} The EQ of the profile" in tip
          and message == f"The app updated “Daily”. {words}", (gone, rows, tip, message))


def test_submenu_sorts_numbers_as_numbers(eq_screen, result, tmp_path, check):
    page, sw = eq_screen.page, eq_screen.sw
    _profiles(sw, str(tmp_path), ("EQ 10", {}), ("EQ 2", {}), ("EQ 1", {KEY: "on"}), ("alpha", {}), ("Beta", {}))
    page._fill_use_menu()
    rows = [r.split("\t")[0] for r in _rows(_sub(page, "Update a profile"))]
    check("update a profile: the submenu Update a profile sorts A to Z with numbers as numbers (EQ 2 before EQ 10)",
          rows == ["alpha", "Beta", "EQ 1", "EQ 2", "EQ 10"], rows)


def test_undo_after_a_rename_says_the_new_name(eq_screen, result, tmp_path, check):
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    ids = _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}))
    page._fill_use_menu()
    _row(page.use_menu, "Update “Daily”").trigger()
    sw.rename_profile(ids["Daily"], "Evening")
    eq_screen.undo()
    check("update a profile: Undo of an update after a rename of the profile says its name at that time",
          said[-1] == "“Evening” has its previous EQ again.", said[-1])


def test_each_device_row_uses_its_device(eq_screen, result, tmp_path, check, monkeypatch):
    page, sw = eq_screen.page, eq_screen.sw
    _two_devices(sw, monkeypatch)
    try:
        _profiles(sw, str(tmp_path))
        page._fill_use_menu()
        rows = _rows(page.use_menu)
        _row(page.use_menu, "Speakers (Realtek)").trigger()
        on = {k: bool(sw.record(k)["active"]) for k in (KEY, KEY2)}
    finally:
        _apart(sw, monkeypatch)
    check("use on device: the row of the second device makes the EQ the profile of that device, not of the first",
          on == {KEY: False, KEY2: True}, (rows, on))


def _devices(n, conn=D.ACTIVE, apo=True, start=20):
    """n stand-in endpoints "Dev NN (Maker)", from start."""
    return [D.Endpoint("{%d}" % k, f"Dev {k:02d}", "Maker", conn, apo) for k in range(start, start + n)]


def _message_for(eq_screen, tmp_path, monkeypatch, eps, *, unused=False, held=False):
    """The message and the row's tooltip after Update “Daily”, on for these endpoints only (held: the first has its
    EQ off to compare)."""
    page, sw, said = eq_screen.page, eq_screen.sw, eq_screen.said
    _two_devices(sw, monkeypatch, *eps)
    try:
        _profiles(sw, str(tmp_path), ("Daily", {f"{e.name}|{e.conn}": "on" for e in eps}))
        if held:
            sw.compare_toggle(f"{eps[0].name}|{eps[0].conn}")
        try:
            with monkeypatch.context() as mp:
                if unused:
                    mp.setattr(sw.apo, "includes_studio", lambda: False)
                page._fill_use_menu()
                row = _row(page.use_menu, "Update “Daily”")
                tip = row.toolTip()
                row.trigger()
        finally:
            if held:
                sw.compare_end()
    finally:
        _apart(sw, monkeypatch)
    return said[-1], tip


@pytest.mark.parametrize("n", [1, 2, 3, 4, 12])
def test_the_message_gives_the_first_device_and_the_count(eq_screen, result, tmp_path, check, monkeypatch, n):
    # (2026-11-11: the message after Update gave every name, 12 names in one sentence of about 600 characters; now
    # each group gives the first name and "and N more devices", as the menu's on words; the tooltip keeps all names)
    def group(words, plural, single):
        return (f"Dev 20 (Maker) {single}" if n == 1 else
                f"Dev 20 (Maker) and {n - 1} more device{'' if n == 2 else 's'} {plural}") + words
    all_names = [f"Dev {k:02d} (Maker)" for k in range(20, 20 + n)]
    now, tip = _message_for(eq_screen, tmp_path, monkeypatch, _devices(n))
    check(f"update a profile: {n} connected devices: the message gives the first device and the count; the tooltip all",
          now == "The app updated “Daily”. " + group(" the new EQ immediately.", "use", "uses")
          and all(x in tip for x in all_names), (now, tip))
    away, _ = _message_for(eq_screen, tmp_path, monkeypatch, _devices(n, D.UNPLUGGED))
    check(f"update a profile: {n} devices that are not connected: the first device and the count",
          away == "The app updated “Daily”. " + group(f" the new EQ when you connect {'it' if n == 1 else 'them'}.",
                                                       "use", "uses"), away)
    no_apo, _ = _message_for(eq_screen, tmp_path, monkeypatch, _devices(n, apo=False))
    check(f"update a profile: {n} devices with no Equalizer APO: the first device and the count",
          no_apo == "The app updated “Daily”. Equalizer APO is not installed on "
          + ("Dev 20 (Maker)" if n == 1 else f"Dev 20 (Maker) and {n - 1} more device{'' if n == 2 else 's'}")
          + " (refer to Devices).", no_apo)
    apo = "Equalizer APO does not use AutoEQ Studio: click Add AutoEQ Studio to APO… on the Devices screen."
    later, _ = _message_for(eq_screen, tmp_path, monkeypatch, _devices(n), unused=True)
    check(f"update a profile: {n} devices, Equalizer APO without the app: the first device and the count",
          later == f"The app updated “Daily”. {apo} " + group(" the new EQ after that.", "use", "uses"), later)


def test_the_message_of_twelve_devices(eq_screen, result, tmp_path, check, monkeypatch):
    eps = _devices(4) + _devices(4, D.UNPLUGGED, start=30) + _devices(4, apo=False, start=40)
    message, tip = _message_for(eq_screen, tmp_path, monkeypatch, eps)
    check("update a profile: 12 devices in three groups: a short message (each group: the first device and the "
          "count), and the tooltip names all 12",
          message == "The app updated “Daily”. Dev 20 (Maker) and 3 more devices use the new EQ immediately. Dev 30 "
                     "(Maker) and 3 more devices use the new EQ when you connect them. Equalizer APO is not installed "
                     "on Dev 40 (Maker) and 3 more devices (refer to Devices)."
          and all(f"Dev {k:02d} (Maker)" in tip for k in (*range(20, 24), *range(30, 34), *range(40, 44))),
          (message, tip))


def test_config_is_read_one_time_for_a_menu(eq_screen, result, tmp_path, check, monkeypatch):
    # (2026-11-11: includes_studio() read Equalizer APO's config.txt one time for each Update row when the menu filled)
    page, sw = eq_screen.page, eq_screen.sw
    eps = _devices(12)
    _two_devices(sw, monkeypatch, *eps)
    try:
        _profiles(sw, str(tmp_path), *[(f"EQ {k}", {f"{e.name}|{e.conn}": "on"}) for k, e in enumerate(eps)])
        real, reads = sw.apo.includes_studio, []
        with monkeypatch.context() as mp:
            mp.setattr(sw.apo, "includes_studio", lambda: reads.append(1) or real())
            page._fill_use_menu()
            fill = len(reads)
            rows = [r for r in _rows(page.use_menu) if r.startswith("Update “")]
            del reads[:]
            _row(page.use_menu, "Update “EQ 0”").trigger()
            message = len(reads)
    finally:
        _apart(sw, monkeypatch)
    check("update a profile: a menu with 12 Update rows (and 12 rows in Update a profile) reads config.txt one time; "
          "the message after an update one time", len(rows) == 12 and fill == 1 and message == 1,
          (len(rows), fill, message))


@pytest.mark.parametrize("letter", ["W", "i"])
def test_long_device_names_are_cut_in_their_rows(eq_screen, result, tmp_path, check, monkeypatch, letter):
    # (2026-11-11: only the Update rows were cut; a device name of 65 characters made the menu 760 px, W x 200 3,023 px.
    # "W" x 80 is wider than the room and is cut; "i" x 80 fits it and stays whole)
    from ui.eq_page_parts import UPDATE_ROOM
    page, sw = eq_screen.page, eq_screen.sw
    long = D.Endpoint("{50}", "Speakers", letter * 69, D.ACTIVE, True)  # ("Speakers (WWW…)": 80 characters)
    amp = D.Endpoint("{51}", "TV", "R&D " + letter * 69, D.ACTIVE, True)
    whole, whole_amp = f"Speakers ({letter * 69})", f"TV (R&D {letter * 69})"
    _two_devices(sw, monkeypatch, long, amp)
    try:
        _profiles(sw, str(tmp_path), ("Daily", {KEY: "on"}))
        page._fill_use_menu()
        menu, tries = page.use_menu, _sub(page, "Use for 5 minutes on")
        fm = menu.fontMetrics()
        rows = [_row(menu, "Speakers ("), _row(menu, "TV (R")]
        trial = [_row(tries, "Speakers ("), _row(tries, "TV (R")]
        wide = (menu.sizeHint().width(), tries.sizeHint().width())
        room = fm.averageCharWidth() * UPDATE_ROOM
        cut = fm.horizontalAdvance(whole) > room
        first = [a.text().split("\t")[0].replace("&&", "&") for a in rows]
        short = [a.text() for a in menu.actions() if a.text().startswith("Headset")]
    finally:
        _apart(sw, monkeypatch)
    names = (whole, whole_amp)
    check(f"use on device: device names of 80 characters ({letter}) wider than the room of the Update rows are cut in "
          "the middle with “…”, "
          "names that fit stay whole, and the two menus stay narrower than 700 px",
          len(whole) == 80 and cut == (letter == "W")
          and all(fm.horizontalAdvance(t) <= room and (("…" in t) if cut else t == n)
                  for t, n in zip(first, names))
          and first[0].startswith("Speakers (") and first[1].startswith("TV (R&D") and max(wide) < 700,
          (first, wide, room))
    tips = [a.toolTip() for a in rows] + [a.toolTip() for a in trial]
    check("use on device: the tooltip of a cut device row has the whole name (also in Use for 5 minutes on, then what "
          "the row does); a name with & shows && in the row and one & in the tooltip",
          (not cut or (tips[:2] == list(names) and tips[3].startswith(whole_amp)
                       and tips[2].startswith(whole + "\nThe EQ plays in all apps for 5 minutes.")))
          and "R&&D" in rows[1].text() and "R&&D" in trial[1].text(), (tips, [a.text() for a in rows + trial]))
    check("use on device: a short device name stays whole",
          short == ["Headset (EarPods)\tactive"], short)
