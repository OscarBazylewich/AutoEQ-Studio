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
              "best_fit.layout", "scoring.pick",
              # (area 14: 6 boxes of the website methods, the 4 numbers of Your result, Number of filters, Calculate
              # from these filters, 8 file formats, Sample rate, Smoothing level and CPU cores)
              "site_single.freq_low", "site_sweep.freq_low", "site_sweep.freq_high", "site_sweep.q_min",
              "site_sweep.q_max", "res.error", "res.preamp", "res.maxq", "res.boost", "fcounts", "f_retry",
              "export.apo", "export.graphic", "export.poweramp", "export.uapp", "export.soundsource",
              "export.voicemeeter", "export.rockbox", "export.convolution", "site.sample_rate", "site.smooth_level",
              "performance.cores",
              # (area 15: Listen's Sound, Tone from … to, Volume, Same level, Hide the names, Ears, Left, Right and
              # Your EQs to compare)
              "#snd-src", "#tone-from", "#snd-vol", "#snd-lm", "#snd-blind", "#snd-ears", "#snd-left", "#snd-right",
              "snd_list",
              # (area 22: the source tabs of Find…, Targets and measurements, the Rig, Type and Source lists, Paste
              # the picture, Rig of your target, Folders to search and Online databases)
              "#pk-src", "#pk-anykind", "pk_filters", "#pw-paste", "#cmp-rig", "library.folders", "databases"}


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


def test_screen_reader_line_is_the_tooltip(eq_screen, check):
    # (the owner, 2026-11-24: Queue…, Adjust…, Close of a manual EQ and the EQ graph had a tooltip of their own
    # and a different line in HELP, which a screen reader got. The line is now the words of the tooltip)
    from PySide6.QtWidgets import QWidget
    from ui import help_window
    from ui.help_texts import HELP
    page = eq_screen.page
    want = {"#queue": "Batch-generate EQs for multiple IEMs or targets; saves each to History",
            "#target-adjust": "Fine-tune the target’s tilt, bass, half-tilt, ear gain, treble, and air",
            "#hand-close": "Return to previous EQ (edits stay in the list)",
            "#eq-graph": "Drag handle: frequency & gain · Scroll on handle: Q · Right-click: filter type or remove · "
                         "Double-click graph: add filter"}
    found = {}
    for w in page.findChildren(QWidget):
        if w.property("help_key") in want:
            h = HELP[help_window.help_key(w.property("help_key"))]
            found.setdefault(w.property("help_key"), []).append(
                (w.toolTip(), w.accessibleDescription(), h[0] if isinstance(h, list) else h))
    check("help: Queue…, Adjust…, Close of a manual EQ and the EQ graph: the line for a screen reader and the line "
          "in HELP are the words of the tooltip",
          set(found) == set(want) and all(got == (want[k],) * 3 for k, ws in found.items() for got in ws), found)


def test_gain_ranges_example_is_its_tooltips(eq_screen, check):
    # (the owner, 2026-11-24: the gray example in the Gain ranges box was "e.g. -12..6, -12..12", and its tooltip
    # gave "e.g., -12..6, -12..9")
    st = eq_screen.page.settings
    box = {**st.form.fields, **st.adv_form.fields}["site_sweep.gain_ranges"].box
    check("settings: the gray example in Gain ranges is the example of its tooltip",
          box.placeholderText() == "e.g., -12..6, -12..9" and "(" + box.placeholderText() + ")" in box.toolTip(),
          (box.placeholderText(), box.toolTip()))


def test_controls_without_a_tooltip(eq_screen, check):
    # (2026-11-24, the text survey: 9 short lines of Make an EQ removed, then 11 and 22 lines of its settings. Their
    # keys stay, so F1, the name for a screen reader and the links of the Help entry stay)
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


def test_find_which_measurement_history_and_sources_lines(eq_screen, check):
    # (2026-11-24, the text survey, area 22: the lines of Find…'s filter lists, Rig of your target, Folders to search
    # and Online databases removed: no tooltip and no line for a screen reader, their name and F1 tag stay. Targets
    # and measurements keeps the tooltip of its own code; the others show the owner's new words. Known rig: its
    # tooltip and its line for a screen reader are one text, the Help line (the owner's decision of 2026-11-24: the
    # screen-reader line of a control is its tooltip; area 16 gave the tooltip other words, area 22's fit the filter))
    from helpers import qt
    from ui import help_window
    from ui.compare_window import CompareWindow
    from ui.history_window import HistoryWindow
    from ui.picker import Picker
    from ui.sources_window import Sources
    page = eq_screen.page
    seen = {}
    pk = Picker(page, "measurement")
    try:
        for n, w in (("Rig", pk.f_rig), ("Type", pk.f_form), ("Source", pk.f_site), ("Known rig", pk.f_sure),
                     ("Available to download", pk.f_dl), ("Targets and measurements", pk.anykind)):
            seen[n] = (w.toolTip(), w.accessibleDescription(), bool(w.accessibleName()), help_window.entry_of_widget(w))
    finally:
        qt.close(pk)
    cw = CompareWindow(page)
    try:
        for n, w in (("Model", cw.q), ("Rig of your target", cw.rig)):
            seen[n] = (w.toolTip(), w.accessibleDescription(), bool(w.accessibleName()), help_window.entry_of_widget(w))
    finally:
        qt.close(cw)
    hw = HistoryWindow(page)
    try:
        seen["This IEM only"] = (hw.only.toolTip(), hw.only.accessibleDescription(), bool(hw.only.accessibleName()),
                                 help_window.entry_of_widget(hw.only))
    finally:
        qt.close(hw)
    src = Sources(page)
    try:
        for n, w in (("Folders to search", src.folders), ("Online databases", src.tree)):
            seen[n] = (w.toolTip(), w.accessibleDescription(), bool(w.accessibleName()), help_window.entry_of_widget(w))
    finally:
        qt.close(src)
    want = {"Rig": ("", "", True, "set-pk-filters"), "Type": ("", "", True, "set-pk-filters"),
            "Source": ("", "", True, "set-pk-filters"),
            "Known rig": ("Hide entries with an unknown, guessed, or mixed rig",
                          "Hide entries with an unknown, guessed, or mixed rig", True, "set-pk-f-sure"),
            "Available to download": ("Shows only entries that can be downloaded directly",
                                      "Shows only entries that can be downloaded directly", True, "set-pk-f-dl"),
            "Targets and measurements": ("Shows both targets and measurements", "", True, "set-pk-anykind"),
            "Model": ("All words must match the measurement name", "All words must match the measurement name", True,
                      "set-cmp-q"),
            "Rig of your target": ("", "", True, "set-cmp-rig"),
            "This IEM only": ("Show only EQs for the selected measurement", "Show only EQs for the selected measurement",
                              True, "set-hist-this"),
            "Folders to search": ("", "", True, "set-library-folders"),
            "Online databases": ("", "", True, "set-databases")}
    check("help: Find…, Which measurement, History and Sources show the lines of the text survey (area 22), and the "
          "controls whose line went keep their name and their Help entry", seen == want,
          {n: (seen.get(n), want[n]) for n in want if seen.get(n) != want[n]})


def test_settings_boxes_without_a_help_line(eq_screen, check):
    # (2026-11-24, the text survey, area 13: the line of 10 settings boxes and of the row Settings to try removed.
    # A box with limits then shows only its limits, with no empty first line; a list or a text box and each label
    # show no tooltip; a box whose line has words shows the line, then its limits)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    from ui import help_window
    page, st = eq_screen.page, eq_screen.page.settings
    fields = {**st.form.fields, **st.adv_form.fields}

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


def test_more_settings_without_a_help_line(eq_screen, check):
    # (2026-11-24, the text survey, area 14: 22 more lines removed. A number box shows only its limits; a list, a
    # tick box of a file format and Number of filters show no tooltip; Calculate from these filters keeps the tooltip
    # that the page gives it, and a screen reader reads that one)
    from ui import help_window
    from ui.help_texts import HELP
    page, st = eq_screen.page, eq_screen.page.settings
    fields = {**st.form.fields, **st.adv_form.fields}
    limits = ["site_single.freq_low", "site_single.freq_high", "site_sweep.freq_low", "site_sweep.freq_high",
              "site_sweep.q_min", "site_sweep.q_max", "site.smooth_level", "performance.cores"]
    got = {p: fields[p].box.toolTip() for p in limits}
    check("help: a box of the website methods, Smoothing level and CPU cores show only their limits, on one line",
          all(t.startswith("Allowed: ") and "\n" not in t for t in got.values()), got)
    formats = ["export." + k for k in ("apo", "graphic", "poweramp", "uapp", "soundsource", "voicemeeter", "rockbox",
                                       "convolution")]
    got = {p: (fields[p].box.toolTip(), bool(fields[p].box.text()), fields[p].box.accessibleDescription())
           for p in formats}
    check("help: the tick box of each of the 8 file formats shows no tooltip; its words stay",
          all(v == ("", True, "") for v in got.values()), got)
    got = fields["site.sample_rate"].box.toolTip()
    check("help: the list Sample rate shows no tooltip", got == "", got)
    got = {p: (fields[p].box.property("help_key"), help_window.entry_for(p), bool(fields[p].box.accessibleName() or fields[p].box.text()))
           for p in limits + formats + ["site.sample_rate"]}
    check("help: each of these boxes keeps its tag for F1, its entry in Help and its name for a screen reader",
          all(k == p and e and named for p, (k, e, named) in got.items()), got)
    combo, retry = page.count_combo, page.retry_btn
    got = (combo.toolTip(), combo.accessibleName(), combo.accessibleDescription(), combo.property("help_key"),
           retry.toolTip(), retry.accessibleDescription(), retry.property("help_key"))
    check("help: Number of filters shows no tooltip; Calculate from these filters keeps the tooltip of its own; a "
          "screen reader reads no line of Help for them",
          got == ("", "Number of filters", "", "fcounts", "Recalculate Best fit starting from these filters", "",
                  "f_retry"), got)
    # (the lines that the survey changed: on the box with its limits after it, and on a list alone)
    got = {p: fields[p].box.toolTip().split("\n") for p in ("site_single.gain_min", "site_single.gain_max",
                                                            "site_single.q_max", "export.extra_headroom")}
    check("help: a number box whose line the survey changed shows the new line, then its limits",
          [t[0] for t in got.values()] == ["Minimum and maximum allowed gain per filter"] * 2
          + ["Minimum and maximum allowed Q per filter", "Extra negative pre-amp applied for more clipping headroom"]
          and all(len(t) == 2 and t[1].startswith("Allowed: ") for t in got.values()), got)
    got = {p: fields[p].box.toolTip() for p in ("site.profile", "export.preamp_rounding", "export.report")}
    check("help: a list or a tick box whose line the survey changed shows only the new line",
          got == {p: HELP[p][0] for p in got}
          and got["export.report"] == "Standalone HTML report with the response graph and filter table", got)
    got = (page.name_edit.toolTip(), page.name_edit.accessibleName())
    check("help: File name shows its new line", got == ("Base name for exported files", "File name"), got)


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


def test_listen_without_help_lines(eq_screen, check):
    # (2026-11-24, the text survey, area 15: the Help lines of 9 controls of Listen removed, and the line of the ABX
    # test changed. A list, a slider, the two Hz boxes and the title Your EQs to compare show no tooltip; Same level
    # and Hide the names keep the tooltip that Listen gives them; a screen reader reads their name only. The row of
    # the ABX test, its lists and the panel of the test show the new line)
    from PySide6.QtWidgets import QLabel
    from ui import help_window
    lis = eq_screen.page.listen
    head = next(w for w in lis.findChildren(QLabel) if w.text() == "Your EQs to compare")
    bare = {"Sound": lis.src, "Volume": lis.vol, "from": lis.tone_from, "to": lis.tone_to, "Ears": lis.ears,
            "Left": lis.left, "Right": lis.right, "Your EQs to compare": head}
    got = {n: (w.toolTip(), w.accessibleName(), w.accessibleDescription(), bool(help_window.entry_of_widget(w)))
           for n, w in bare.items()}
    check("help: Sound, Volume, Tone from … to, Ears, Left, Right and Your EQs to compare of Listen show no tooltip, "
          "and keep their name for a screen reader and their entry in Help",
          got == {"Sound": ("", "Sound", "", True), "Volume": ("", "Volume", "", True),
                  "from": ("", "Tone: from … to", "", True), "to": ("", "Tone: from … to", "", True),
                  "Ears": ("", "Ears", "", True), "Left": ("", "Left", "", True), "Right": ("", "Right", "", True),
                  "Your EQs to compare": ("", "Your EQs to compare", "", True)}, got)
    got = {n: (w.toolTip(), w.accessibleDescription()) for n, w in (("Same level", lis.lm), ("Hide the names", lis.blind))}
    check("help: Same level and Hide the names keep the tooltip of their own, and a screen reader reads no line of Help",
          got == {"Same level": ("Matches loudness across all versions so volume doesn't skew comparisons", ""),
                  "Hide the names": ("Labels versions A, B, C… in random order until you click “Show the names”", "")},
          got)
    line = "Blind test to see if you can tell two versions apart"
    got = [(w.toolTip(), w.accessibleDescription()) for w in (lis.abx_row, lis.abx_a, lis.abx_b, lis.abx_n, lis.abx_box)]
    check("help: the row of the ABX test, its 3 lists and the panel of the test show the new line, which a screen "
          "reader reads too", got == [(line, line)] * 5, got)


def test_numbers_of_your_result_without_a_help_line(eq_screen, check):
    # (2026-11-24, the text survey, area 14: the Help lines of the 4 numbers of Your result removed. Maximum gain and
    # Maximum Q show no tooltip; Error and Pre-amp show the tooltip that the page gives them with a result. The last
    # test of this file, because it calculates an EQ on the shared page)
    from ui import help_window
    page = eq_screen.page
    eqpage.quick_run(eq_screen)
    chips = page.chips
    got = {k: (c.toolTip(), c.accessibleName(), c.accessibleDescription(), help_window.entry_for(c.property("help_key")))
           for k, c in chips.items()}
    check("help: Maximum gain and Maximum Q of Your result show no tooltip, and a screen reader reads only their name",
          got["boost"] == ("", "Maximum gain", "", "set-res-boost") and got["maxq"] == ("", "Maximum Q", "", "set-res-maxq"),
          got)
    check("help: Error and Pre-amp of Your result keep the tooltip of their own, with no line of Help for a screen "
          "reader, and their entry in Help",
          got["error"] == ("Average difference between the EQ'd response and target (lower is better)", "Error", "",
                           "set-res-error")
          and got["preamp"] == ("Volume reduction to prevent clipping (highest EQ boost plus extra headroom)", "Pre-amp",
                                "", "set-res-preamp"), got)
