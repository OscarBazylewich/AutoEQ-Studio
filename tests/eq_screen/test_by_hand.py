"""Make an EQ's By hand (ui\\eq_page_result.py, 2026-10-26): an EQ you make yourself, on the result card as a run of its
own: begun empty, from an EQ file (a Room EQ Wizard export here: read as Equalizer APO plays it, what an EQ here can't
have said in a box), from pasted lines, from a device's profile (Use on device › Update puts it back; refused for a
profile with parts it can't show) or as a copy of the EQ shown; saved, kept in History and listed in this session's
runs as any result; with no measurement chosen, the EQ graph still shows it and Report says what it needs. One page
for the file (the eq_screen fixture: a stand-in APO folder and one stand-in device)."""
import os

from helpers import eqpage

REW = """Filter Settings file

Room EQ V5.31.3
Equaliser: Generic
Filter  1: ON  PK       Fc   48.00 Hz  Gain  -7.50 dB  Q  4.200
Filter  2: ON  LS 12dB  Fc   150.0 Hz  Gain   3.00 dB
Filter  3: ON  LP       Fc   18000 Hz
"""


def _start(page, what):
    """By hand (Make the EQ's tab), as you'd use it: `what` chosen in Start from (empty, copy, file or paste; else a
    profile's name), then Start."""
    page.set_way("hand", remember=False)
    page.fill_hand_sources()
    c = page.hand_source
    i = c.findData(what) if what in ("empty", "copy", "file", "paste") else next(
        (k for k in range(c.count()) if c.itemText(k).startswith(f"Profile: {what}")), -1)
    if i < 0:
        raise LookupError(what)
    c.setCurrentIndex(i)
    page.hand_start.click()


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def test_start_empty_and_add_a_filter(eq_screen, check):
    page = eq_screen.page
    _start(page, "empty")
    run, r = page.current()
    empty = (run["mode"], page.res_title.text(), page.count_combo.isVisible(), page.count_lab.isVisible(),
             page.pick_lab.text(), list(page.EDIT), page.listen.isVisible(), page.result_box.isVisible())
    page.add_filter()
    check("by hand: Start empty puts an EQ of your own on the result card (titled By hand, no filter counts to choose "
          "from, a line saying how to add one, Listen there); Add filter adds one, the numbers and the name following",
          empty[0] == "manual" and empty[1] == "By hand" and not empty[2] and not empty[3] and "No filters yet" in empty[4]
          and empty[5] == [] and empty[6] and empty[7] and len(page.EDIT) == 1 and page.chips["filters"].text() == "Filters  1"
          and page.name_edit.text().endswith(" - by hand 1f") and "edited" in page.res_title.text(),
          (empty, page.chips["filters"].text(), page.name_edit.text()))


def test_from_a_room_eq_wizard_file(eq_screen, tmp_path, dialogs, check):
    page = eq_screen.page
    path = _write(os.path.join(str(tmp_path), "Room fix.txt"), REW)
    dialogs.answer("getOpenFileName", (path, ""))
    _start(page, "file")
    run, r = page.current()
    box = [t for kind, t in dialogs.asked if kind == "information"]
    got = [(f["type"], f["enabled"]) for f in page.EDIT]
    check("by hand: From an EQ file… reads a Room EQ Wizard export (its peak and its LS 12dB shelf, moved to its "
          "centre); the low-pass it can't have is said in a box; the source and its name follow",
          got == [("PK", True), ("LSQ", True)] and page.EDIT[1]["freq"] > 150 and box and "low-pass" in box[-1]
          and run["source"] == "from Room fix.txt" and "from Room fix.txt" in page.res_sub.text(),
          (got, box, run.get("source"), page.res_sub.text()))


def test_pasted_filters(eq_screen, check, monkeypatch):
    from ui import eq_page_parts
    page = eq_screen.page
    monkeypatch.setattr(eq_page_parts, "paste_dialog", lambda *a: ("Mine", "Filter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n"
                                                                     "Filter 2: OFF HSC Fc 8000 Hz Gain -2 dB Q 0.7"))
    _start(page, "paste")
    run, _ = page.current()
    check("by hand: Paste filters… takes Equalizer APO lines, a switched-off filter staying off",
          [(f["type"], f["enabled"]) for f in page.EDIT] == [("PK", True), ("HSQ", False)] and run["source"] == "pasted",
          page.EDIT)


def test_from_a_profile_then_update_it(eq_screen, tmp_path, check):
    page, sw = eq_screen.page, eq_screen.sw
    pid = sw.import_profile(_write(os.path.join(str(tmp_path), "Daily.txt"),
                                   "Preamp: -3 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n"), "Daily")
    sw.add_to_device(eqpage.DEVICE, pid, switch_on=True)
    _start(page, "Daily")
    page.EDIT[0]["gain"] = 4.5
    page.live_update()
    page._fill_use_menu()
    update = next(a for a in page.use_menu.actions() if a.text().startswith("Update “Daily”"))
    update.trigger()
    p = sw.profiles()[pid]
    with open(os.path.join(sw.apo.profiles, p["file"]), encoding="utf-8") as fh:
        text = fh.read()
    rec = sw.record(eqpage.DEVICE)
    check("by hand: a device's profile opens as an EQ by hand; Use on device › Update puts the edit back into it (its "
          "name and device kept, still on)",
          "Gain 4.5 dB" in text and p["name"] == "Daily" and rec["active"] == pid
          and any("Updated “Daily”" in t for t in eq_screen.said[-2:]), (text, rec, eq_screen.said[-2:]))
    graphic = sw.import_profile(_write(os.path.join(str(tmp_path), "Graphic.txt"),
                                       "Filter 1: ON PK Fc 500 Hz Gain 1 dB Q 1\nGraphicEQ: 20 0; 1000 2; 20000 0\n"),
                                "Graphic one")
    _start(page, "Graphic one")
    page._fill_use_menu()
    refused = next(a for a in page.use_menu.actions() if a.text().startswith("Update “Graphic one”"))
    check("by hand: a profile with parts an EQ here can't show (a graphic EQ) can't be updated from it (said why); "
          "using it as a new profile stays open",
          not refused.isEnabled() and "graphic EQ" in refused.toolTip() and sw.profiles().get(graphic)
          and any(a.isEnabled() and "Headset" in a.text() for a in page.use_menu.actions()), refused.toolTip())


def test_a_copy_of_the_eq_shown(eq_screen, check):
    page = eq_screen.page
    page.start_by_hand([{"type": "PK", "freq": 200, "gain": -2, "q": 1.2}], "pasted", "Base")
    page.EDIT.append({"enabled": True, "type": "LSQ", "freq": 100, "gain": 3, "q": 0.7})
    page.live_update()
    before = len(page.session_runs)
    _start(page, "copy")
    run, _ = page.current()
    check("by hand: A copy of the selected EQ starts another EQ by hand with its filters as they are now, the one before "
          "kept in this session's runs",
          len(page.session_runs) == before + 1 and run["source"] == "a copy of your EQ by hand" and len(page.EDIT) == 2
          and not page.edited(), (run.get("source"), page.EDIT))


def test_saved_and_kept_as_a_result(eq_screen, check):
    page = eq_screen.page
    page.start_by_hand([{"type": "PK", "freq": 1000, "gain": 2, "q": 1}], "pasted", "Kept")
    entry = eqpage.save_result(eq_screen, "By hand check")
    runs = [page.runs_combo.itemText(i) for i in range(page.runs_combo.count())]
    check("by hand: Save filters writes it and keeps it in History (By hand); this session's runs list it",
          entry["mode"] == "manual" and entry["label"].startswith("By hand · pasted") and any("By hand" in t for t in runs)
          and "Saved" in eq_screen.said[-1], (entry.get("label"), runs, eq_screen.said[-1:]))


def test_with_no_measurement(eq_screen, dialogs, check):
    page = eq_screen.page
    page.start_by_hand([{"type": "PK", "freq": 1000, "gain": 4, "q": 1}], "pasted", "Alone")
    curves = page.curves
    try:
        page.curves = None
        page.draw()
        eq_items, main_items = len(page.eqplot.listDataItems()), len(page.plot.listDataItems())
        report = page.report(open_it=True)
        box = [t for kind, t in dialogs.asked if kind == "information"]
    finally:
        page.curves = curves
        page.draw()
    check("by hand: with no measurement chosen, the EQ graph still shows the EQ (the graph above it is empty), and "
          "Report says it needs a measurement and a target",
          eq_items == 1 and main_items == 0 and report is None and box and "choose" in box[-1], (eq_items, main_items, box))


def test_edits_kept_when_another_run_is_shown(eq_screen, check):
    page = eq_screen.page
    page.start_by_hand([{"type": "PK", "freq": 300, "gain": 1, "q": 1}], "pasted", "First")
    first = page.run_result
    page.EDIT[0]["gain"] = 5
    page.live_update()
    page.start_by_hand([], "started empty")
    page.choose_run(id(first))
    check("by hand: an EQ by hand keeps your changes when another run is shown and it's chosen again in Runs this "
          "session (Revert still goes back to how it began)",
          page.run_result is first and page.EDIT[0]["gain"] == 5 and page.ORIG[0]["gain"] == 1 and page.edited(),
          (page.EDIT, page.ORIG))


def _nothing_shown(page):
    """No result: the card hidden, no EQ on the EQ graph (its curve, its handles), none in Listen's versions."""
    return (page.result_box.isVisible(), page.current(), len(page.eqplot.listDataItems()), len(page._handles),
            "sel" in [k for k, *_ in page.listen.versions()])


def test_remove_the_last_run(eq_screen, check):
    page = eq_screen.page
    page.start_by_hand([{"type": "PK", "freq": 1000, "gain": 3, "q": 1}], "pasted", "Last")
    page.session_runs = [page.run_result]
    page.remove_run()
    check("by hand: Remove on this session's last run takes its EQ off the graph (its curve and handles) and out of "
          "Listen too, not only the card", _nothing_shown(page) == (False, (None, None), 0, 0, False),
          _nothing_shown(page))


def test_close_goes_back(eq_screen, check):
    page = eq_screen.page
    page.session_runs = []  # (nothing shown before it: the page as it opens)
    page.show_run(None)
    _start(page, "empty")
    shown = (page.hand_close.isVisible(), page.result_box.isVisible())
    page.hand_close.click()
    alone = (_nothing_shown(page), page.session_runs, page.name_edit.text())
    first = eqpage.quick_run(eq_screen)
    _start(page, "empty")
    page.hand_close.click()
    back = (page.run_result is first, page.res_title.text().startswith("Best fit"), page.hand_close.isVisible(),
            [x["mode"] for x in page.session_runs])
    _start(page, "empty")
    mine = page.run_result
    page.add_filter()
    page.hand_close.click()
    kept = (page.run_result is first, any(x is mine for x in page.session_runs), page.runs_row.isVisible())
    page.choose_run(id(mine))
    again = (page.run_result is mine, len(page.EDIT))
    check("by hand: Close (an EQ by hand's only) goes back to what was shown before it: with nothing before, the page "
          "as it was (no card, no EQ on the graph or in Listen, nothing left in this session's runs); after a run, that "
          "run (Close hidden again); one you changed stays in Runs this session, to come back to as you left it",
          shown == (True, True) and alone == ((False, (None, None), 0, 0, False), [], "")
          and back == (True, True, False, ["best_fit"]) and kept == (True, True, True) and again == (True, 1),
          (shown, alone, back, kept, again))


def test_close_on_pasted_filters_offers_undo(eq_screen, check):
    # (2026-10-27, the code's review: Close on an EQ by hand as it began took it off this session's runs for good,
    # pasted filters too; an empty one has nothing to lose, so nothing is said)
    page = eq_screen.page
    page.session_runs = []
    page.show_run(None)
    n = len(eq_screen.said)
    _start(page, "empty")
    page.hand_close.click()
    empty = eq_screen.said[n:]
    page.start_by_hand([{"type": "PK", "freq": 1000, "gain": 3, "q": 1}], "pasted", "Mine")
    pasted = page.run_result
    page.hand_close.click()
    offered = (eq_screen.undo_offered(), (eq_screen.said or [""])[-1], pasted in page.session_runs)
    eq_screen.undo()
    back = (page.run_result is pasted, any(x is pasted for x in page.session_runs), len(page.EDIT))
    page.session_runs = []
    page.show_run(None)
    check("by hand: Close on an EQ by hand as it began (pasted) takes it off this session's runs with Undo in the "
          "window's line, and Undo brings it back as it was; an empty one goes without a word",
          empty == [] and offered[0] and offered[1].startswith("Closed “Run") and not offered[2]
          and back == (True, True, 1), (empty, offered, back))
