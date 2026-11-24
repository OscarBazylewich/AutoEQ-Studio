"""F1 on Make an EQ and the tracer (ui\\help_window.py's tags): every control tagged for F1 has a help text. Moved
from eq_checks.py's guide_checks (lines 2632-2639), on a page opened as the old checks opened it (the eq_screen
fixture) with the tracer as the old checks had made it by then (trace_checks: the sample graph opened and traced,
helpers.eqpage.open_traced_sample), the page 1100x900 as there. And (2026-10-23) each tagged button's entry named in
Help as the button reads."""
import pytest

from helpers import eqpage

# The keys of HELP whose line is empty on purpose: the text survey of 2026-11-24 removed the tooltip of their
# controls (ui\help_texts.py tells the mechanism). This is the one list of them: a key whose tooltip is removed
# later is added here, and a line that becomes empty by accident fails test_controls_without_a_tooltip.
NO_TOOLTIP = {"#opt-view", "#target-save", "#compare-results", "#make-way", "#by-hand", "#hand-start",
              "#use-device", "#use-try", "#use-update",
              # (area 13 of the survey: the row Settings to try, and 10 settings boxes of Make an EQ)
              "sa", "best_fit.filter_counts", "best_fit.freq_range", "best_fit.gain_min", "best_fit.gain_max",
              "best_fit.q_min", "best_fit.q_max", "best_fit.low_shelf_freq", "best_fit.start_filters",
              "best_fit.layout", "scoring.pick"}


@pytest.mark.timeout(600)  # (the tracer's labels read and three Auto traces first)
def test_every_tagged_control_has_help(eq_screen, check):
    from PySide6.QtWidgets import QWidget
    from ui import help_window
    page = eq_screen.page
    eqpage.open_traced_sample(eq_screen)  # (page.tracer, as trace_checks left it: line 2772)
    page.resize(1100, 900)
    tagged = [w.property("help_key") for root in (page, page.tracer) for w in root.findChildren(QWidget)
              if w.property("help_key")]
    unknown = sorted({k for k in tagged if not help_window.help_key(k)})
    # was eq_checks.py:2638
    check("help: every control tagged for F1 (Make an EQ, the tracer) has a help text", len(tagged) > 60 and not unknown,
          (len(tagged), unknown))
    # (2026-11-24: a control gets its tooltip from the line of its key, so a tagged control with a line must show
    # words; only the keys of NO_TOOLTIP have none)
    from ui.help_texts import HELP

    def line(key):
        h = HELP[help_window.help_key(key)]
        return h[0] if isinstance(h, list) else h
    silent = sorted({w.property("help_key") for root in (page, page.tracer) for w in root.findChildren(QWidget)
                     if w.property("help_key") and help_window.help_key(w.property("help_key"))
                     and line(w.property("help_key")) and not w.toolTip()})
    check("help: every tagged control whose Help line has words shows a tooltip", not silent, silent)


def test_controls_without_a_tooltip(eq_screen, check):
    # (2026-11-24, the text survey: 9 short lines of Make an EQ removed, then 11 lines of its settings. Their keys
    # stay, so F1, the name for a screen reader and the links of the Help entry stay)
    from ui import help_window
    from ui.help_texts import HELP
    page = eq_screen.page
    empty = {k for k, h in HELP.items() if not (h[0] if isinstance(h, list) else h)}
    entries = {k: help_window.entry_for(k) for k in NO_TOOLTIP}
    check("help: the keys with an empty line are the listed ones, and each still has its entry in Help",
          empty == NO_TOOLTIP and all(entries.values()), (sorted(empty ^ NO_TOOLTIP), entries))
    check("help: Use for 5 minutes on and Update a profile keep the links of their entries",
          HELP["#use-try"] == ["", "q-try", "set-use-device", "set-use-update"]
          and HELP["#use-update"] == ["", "set-use-device", "set-use-try", "set-prof-edit"],
          (HELP["#use-try"], HELP["#use-update"]))
    bare = {"View": page.view_combo, "Start from": page.hand_source, "Start": page.hand_start,
            "Use on device": page.use_btn}
    got = {n: (w.toolTip(), w.accessibleName(), w.accessibleDescription(), w.property("help_key"))
           for n, w in bare.items()}
    check("help: View, Start from, Start and Use on device show no tooltip, and keep their name for a screen reader "
          "and their tag for F1",
          got == {"View": ("", "View", "", "#opt-view"), "Start from": ("", "Start from", "", "#by-hand"),
                  "Start": ("", "Start (Manually)", "", "#hand-start"),
                  "Use on device": ("", "Use on device (Make an EQ)", "", "#use-device")}, got)
    own = {"Compare…": page.cmp_btn, "Automatically": page.way_btns["auto"], "Manually": page.way_btns["hand"]}
    got = {n: (bool(w.toolTip()), bool(w.accessibleName()), w.accessibleDescription()) for n, w in own.items()}
    check("help: Compare… and the tabs Automatically and Manually keep the tooltip of their own, and a screen reader "
          "reads only their name (no line of Help after it)",
          all(v == (True, True, "") for v in got.values()), got)


def test_settings_boxes_without_a_help_line(eq_screen, check):
    # (2026-11-24, the text survey, area 13: the line of 10 settings boxes and of the row Settings to try removed.
    # A box with limits then shows only its limits, with no empty first line; a list or a text box and each label
    # show no tooltip; a box whose line has words shows the line, then its limits)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    from ui import help_window
    page, st = eq_screen.page, eq_screen.page.settings
    fields ={**st.form.fields, **st.adv_form.fields}

    def label(path):  # (the label above the box: the one label that the cell itself has; "to" is in the boxes' row)
        cell = fields[path].parentWidget().parentWidget()
        own = cell.findChildren(QLabel, options=Qt.FindDirectChildrenOnly)
        return own[0] if len(own) == 1 else None
    limits = ["best_fit.filter_counts", "best_fit.freq_range.0", "best_fit.freq_range.1", "best_fit.gain_min",
              "best_fit.gain_max", "best_fit.q_min", "best_fit.q_max", "best_fit.low_shelf_freq.0",
              "best_fit.low_shelf_freq.1"]
    got = {p: fields[p].box.toolTip() for p in limits}
    check("help: a settings box whose Help line is removed shows only its limits, on one line",
          all(t.startswith("Allowed: ") and "\n" not in t for t in got.values()), got)
    got = {p: fields[p].box.toolTip() for p in ("best_fit.start_filters", "best_fit.layout", "scoring.pick")}
    check("help: Start from your filters, Layout and Best result (no limits) show no tooltip",
          set(got.values()) == {""}, got)
    labels = {p: label(p) for p in limits + list(got) if not p.endswith(".1")}
    got = {p: (w.text(), w.toolTip()) if w is not None else None for p, w in labels.items()}
    check("help: the label of each of these boxes shows no tooltip",
          all(v and v[0] and v[1] == "" for v in got.values()), got)
    got = {p: (fields[p].box.property("help_key"), help_window.entry_for(p), bool(fields[p].box.accessibleName()))
           for p in limits + ["best_fit.start_filters", "best_fit.layout", "scoring.pick"]}
    check("help: each of these boxes keeps its tag for F1, its entry in Help and its name for a screen reader",
          all(k == p and e and named for p, (k, e, named) in got.items()), got)
    got = (page.sa.toolTip(), page.sa.accessibleName(), page.sa.accessibleDescription(), bool(page.estimate.toolTip()))
    check("help: the row Settings to try has no tooltip of its own and a screen reader reads only its name; the "
          "text of the row keeps its tooltip", got == ("", "Settings to try", "", True), got)
    got = {p: fields[p].box.toolTip().split("\n") for p in ("scoring.band_hz.0", "scoring.band_hz.1",
                                                              "best_fit.bands.gain_min", "best_fit.bands.gain_max")}
    check("help: a settings box whose Help line has words shows the line, then its limits",
          [t[0] for t in got.values()] == ["Frequency range used to measure EQ error"] * 2
          + ["Minimum slider gain (dB)", "Maximum slider gain (dB)"]
          and all(len(t) == 2 and t[1].startswith("Allowed: ") for t in got.values()), got)
    adj = st.adjust()  # (the page's own window, made hidden at its first use)
    rows = {w.text(): w.toolTip().split("\n") for w in adj.dlg.findChildren(QLabel)
            if w.text() in ("Tilt", "Bass", "Half-tilt", "Ear gain", "Treble", "Air")}
    boxes = {k: adj.form.fields["target_adjust." + k].box.toolTip().split("\n")
             for k in ("tilt", "bass_freq", "bass_q", "ear_q")}
    check("help: Adjust the target: the name of a row and its value box show the same line and limits",
          rows["Tilt"] == boxes["tilt"] and rows["Tilt"][0] == "Tilts the full target: − gives more bass, + gives "
          "more treble" and [len(v) for v in rows.values()] == [2] * 6
          and rows["Air"][0] == "Boosts (+) or cuts (−) upper treble (“air”) above ~10 kHz", rows)
    check("help: Adjust the target: an Hz box shows its line and limits, a Q list only its line",
          boxes["bass_freq"][0] == "Corner frequency for the bass shelf" and len(boxes["bass_freq"]) == 2
          and boxes["bass_q"] == ["Slope of the bass shelf"] and boxes["ear_q"] == ["Width of the ear-gain filter"],
          boxes)


def test_buttons_named_in_help_as_they_read(eq_screen, check):
    # (2026-10-23, the restyle's checkers: Help's entry for Retry from these filters was titled “↻ Retry from these
    # filters”, the button's words before the restyle; F1 opens that entry, and a screen reader names the button by it)
    from PySide6.QtWidgets import QAbstractButton, QCheckBox, QRadioButton
    from ui import help_text_eq, help_window
    page = eq_screen.page
    titles = {it["key"]: it["title"] for section in help_text_eq.SETTINGS_EQ for it in section["items"]}
    named = {}
    for b in page.findChildren(QAbstractButton):
        key = help_window.help_key(b.property("help_key") or "")
        if key in titles and not isinstance(b, (QCheckBox, QRadioButton)):  # (a tick box's words say more)
            named[b.text()] = titles[key]
    wrong = {words: title for words, title in named.items() if not title.startswith(words)}
    check("help: each button on Make an EQ that F1 explains has its entry in Help named as the button reads (“↻ Retry "
          "from these filters” kept a symbol the button no longer has)", len(named) >= 5 and not wrong, (named, wrong))


def test_handle_tooltip_names_its_menu(check):
    # (2026-11-10, the review: the graph's handle tooltip still named an On item its menu does not have)
    import os
    import re
    from types import SimpleNamespace

    from helpers import paths
    from ui.eq_page_handles import EqHandles
    tip = EqHandles.handle_tip(SimpleNamespace(EDIT=[{"freq": 1000, "gain": 3.0, "q": 1.0, "type": "PK"}]), 0)
    with open(os.path.join(paths.PROJECT_APP, "ui", "eq_page_handles.py"), encoding="utf-8") as fh:
        menu = re.search(r"def handle_menu.*?\n    def ", fh.read(), re.S).group(0)
    check("help: a graph handle's tooltip names the items of its right-click menu (its type, Remove; no On)",
          tip.endswith("\nDrag: freq & gain · Scroll: Q · Right-click: filter type or remove") and 'addAction("Remove"' in menu and '"On"' not in menu, tip)


def test_use_on_device_has_its_own_help(eq_screen, check):
    # (2026-11-11: the button had the tag of Use for 5 minutes on, so its tooltip and F1 told only one of its 3
    # functions)
    from ui import help_window
    btn = eq_screen.page.use_btn
    entry = help_window.entry_for(btn.property("help_key") or "")
    e = help_window._by_id().get(entry or "", {})  # (as tests/ui/test_help.py reads the entries)
    # (2026-11-24, the text survey: the button has no tooltip any more; its entry tells its 3 functions)
    check("help: Use on device has its own Help entry, which links to Update a profile and Use for 5 minutes on, and "
          "no tooltip",
          btn.property("help_key") == "#use-device" and entry == "set-use-device" and btn.toolTip() == ""
          and e.get("title") == "Use on device (Make an EQ)" and e.get("see") == ["set-use-update", "set-use-try"],
          (btn.property("help_key"), entry, btn.toolTip(), e.get("title"), e.get("see")))


def test_update_words_are_true_for_each_device(check):
    # (2026-11-11: the short help of Update and the Guide said that the devices that have the profile on use the new
    # EQ, with no condition: untrue for a device that is not connected or has no Equalizer APO)
    import os

    from helpers import paths
    from ui.help_texts import HELP
    with open(os.path.join(paths.PROJECT_APP, "ui", "guide_eq.py"), encoding="utf-8") as fh:
        guide = fh.read()
    # (2026-11-24, the text survey: Update a profile has no short help any more, so no short line can be untrue)
    short = HELP["#use-update"][0]
    check("help: Update a profile has no short help, and the Guide does not say that all its devices use the new EQ",
          short == "" and "have it on use the new" not in guide, (short,))
    # (2026-11-12: only the short help was checked; the long help can lose its conditions, and the message rule)
    from ui.help_text_devices import SETTINGS_DEVICES
    body = next(e["body"] for g in SETTINGS_DEVICES for e in g["items"] if e["key"] == "#use-update")
    text = " ".join(p for p in body if isinstance(p, str))
    items = next(p for p in body if isinstance(p, list))
    late = [s for s in " ".join(items).split(". ") if "immediately" in s]
    check("help: the long help of Update a profile gives each condition first, and says “immediately” only with it",
          items == ["If Equalizer APO does not use AutoEQ Studio, no device uses the new EQ immediately. The devices "
                    "use it after you click Add AutoEQ Studio to APO… on the Devices screen.",
                    # (2026-11-12: Keep it makes the EQ for 5 minutes a new profile that is on, so that device does
                    # not use the new EQ after the 5 minutes: the two states are said apart, as switcher.core does.
                    # Do not keep it stops the EQ for 5 minutes before the 5 minutes: "when it stops", not "after")
                    "While a device uses an EQ for 5 minutes, it does not change. If you click Keep it, the EQ for 5 "
                    "minutes becomes a new profile of the device, and this profile is on. If you do not click Keep "
                    "it, the device uses the new EQ when the EQ for 5 minutes stops.",
                    "While a device has its EQ off to compare, it does not change. When its EQ is on again, the "
                    "device uses the new EQ.",
                    "A device that is not connected uses the new EQ when you connect it.",
                    "A device on which Equalizer APO is not installed does not use the EQ (refer to Devices).",
                    "In all other conditions, a connected device uses the new EQ immediately."]
          and all(s.startswith(("If ", "In all other conditions, ")) for s in late), (items, late))
    check("help: the long help of Update a profile tells the rule of the message (a maximum of 3 names for each group)",
          "The message after the update shows each group of devices with a maximum of 3 names, and the number of "
          "other devices." in text and "first device of each group" not in text, text)


def test_help_names_the_info_mark_of_your_eq_app(eq_screen, check):
    # (2026-11-12: Help said “the line below” Your EQ app; the words are in the ⓘ after its label, bubble.InfoMark)
    from ui import help_window
    from ui.bubble import InfoMark
    note = eq_screen.page.app_note
    # (the text survey, 2026-11-23: the ⓘ shows the limits of the app only, so Help no longer says that it tells how
    # to load the EQ; the question “How do you put the EQ into your app?” lost that sentence)
    entries = [str(e) for e in help_window._by_id().values()]
    words = [w for w in entries if "after the label Your EQ app" in w]
    check("help: each Help text about the limits of Your EQ app names the ⓘ after the label Your EQ app, not a line "
          "below it, and no Help text says that the ⓘ tells how to load the EQ",
          isinstance(note, InfoMark) and len(words) == 2
          and all("The ⓘ after the label Your EQ app tells" in w and "its limits" in w and "line below" not in w
                  for w in words) and not [w for w in entries if "how to load the EQ" in w], words)


def test_every_eq_app_has_its_steps_in_help(eq_screen, check):
    # (2026-11-24: the steps to load an EQ in each EQ app left the ⓘ after Your EQ app with the text survey; they are
    # in Help now, in one entry. ui\help_text_apps.py cannot import the EQ part, so its keys, names and platforms
    # are compared with eq\eq_apps.py here)
    from eq import eq_apps
    from ui import help_window
    from ui.help_text_apps import LOAD_EQ
    listed = {key: (name, platform) for platform, apps in LOAD_EQ for key, name, _steps in apps}
    real = {key: (a["name"], a["platforms"][0]) for key, a in eq_apps.APPS.items()}
    steps = {key: steps for _platform, apps in LOAD_EQ for key, _name, steps in apps}
    order = [platform for platform, _apps in LOAD_EQ]
    check("help: each app of the Your EQ app list has steps to load the EQ, by its name as the list shows it, in "
          "the list of its first platform (the platforms in the order of the app's list)",
          listed == real and sum(len(apps) for _p, apps in LOAD_EQ) == len(real)
          and order == [p for p in eq_apps.PLATFORMS if p in order]
          and all(s.strip() == s and s.endswith(".") and len(s) > 20 for s in steps.values()),
          ({k: (listed.get(k), real.get(k)) for k in set(listed) | set(real) if listed.get(k) != real.get(k)}, order))
    by = help_window._by_id()
    entry = by.get("load-eq", {})
    lines = [x for part in entry.get("body", []) if isinstance(part, list) for x in part]
    question = by.get("q-load", {})
    check("help: the entry “Load the EQ in your EQ app” has one line for each app (its name, then its steps), the "
          "question “How do you put the EQ into your app?” opens it as its first link, and the entry refers to "
          "Saved file formats for the files",
          entry.get("title") == "Load the EQ in your EQ app"
          and sorted(lines) == sorted(f"{real[k][0]}: {steps[k]}" for k in real)
          and (question.get("see") or [None])[0] == "load-eq" and "file-formats" in entry.get("see", [])
          and "F1" not in str(entry), (entry.get("title"), len(lines), question.get("see")))


def test_help_search_finds_an_eq_app_by_its_name(eq_screen, check):
    # (2026-11-24: the name of an app typed in Search Help… shows the entry with its steps)
    from eq import eq_apps
    from ui import help_window
    w = help_window.open_at()
    missed = []
    try:
        for a in eq_apps.APPS.values():
            w.q.setText(a["name"])
            if w.items["load-eq"].isHidden() or w.found < 1:
                missed.append(a["name"])
        w.q.setText("Qudelix-T71")  # (a name that only this entry has: the page shows the entry)
        shown = (w.found, w.page_now, "Qudelix-T71: In the PEQ of the Qudelix app" in w.view.toPlainText())
        w.q.setText("")
    finally:
        w.close()
    check("help: the search finds the entry “Load the EQ in your EQ app” by the name of each app of the Your EQ app "
          "list, and a name that only this entry has shows the entry on the page",
          not missed and shown == (1, "load-eq", True), (missed, shown))
