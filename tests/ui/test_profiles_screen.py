"""Profiles (the window's profiles screen, ui\\window.py; ui\\profiles_screen.py once the window is split): every
profile listed. Moved from selftest.py's qt_checks: after Set up (tests\\ui\\conftest.py's set_up_window), the two
EQ files config.txt used are the two profiles. Then its look in Windows 11's (the restyle, 2026-10-23): the table
and the symbols beside its buttons' words."""


def test_the_profiles_list(set_up_window, check):
    win = set_up_window.win
    win.render_all()
    names = [win.prof_table.item(r, 0).text() for r in range(win.prof_table.rowCount())]
    # was selftest.py:593
    check("window: the profiles list", win.prof_table.rowCount() == 2, names)


def test_the_profiles_table_as_windows_11(set_up_window, qapp, check):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton
    win = set_up_window.win
    win.show_page("profiles", remember=False)
    try:
        win.render_all()
        qapp.processEvents()
        t, h = win.prof_table, win.prof_table.horizontalHeader()
        cut = [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())
               if t.columnWidth(c) < max(t.sizeHintForColumn(c), h.sectionSizeHint(c))]
        buttons = {b.text(): b for b in win.pages["profiles"].findChildren(QPushButton)}
        named = ("Import EQ files…", "Rename…", "Delete…", "Open the profiles folder")
        look = (t.showGrid(), bool(h.defaultAlignment() & Qt.AlignLeft), t.verticalHeader().defaultSectionSize())
        plain = [n for n in named if n not in buttons or buttons[n].icon().isNull()]
    finally:
        win.show_page("devices", remember=False)
    check("profiles: the table as Windows 11 draws one (headings at the left, no grid, rows of 36 px), no column's "
          "words cut, and Windows 11's symbols beside its buttons' words",
          look[0] is False and look[1] and look[2] >= 36 and not cut and not plain, (look, cut, plain))


def test_edit_in_make_an_eq(set_up_window, qapp, check, monkeypatch):
    # (2026-10-26: a profile's filters changed by hand in Make an EQ, then put back with Use on device › Update. The
    # window here never opens Make an EQ: what it's asked to do there is recorded instead)
    from helpers import dialogs
    from ui import help_window
    win = set_up_window.win
    asked, shown = [], []
    monkeypatch.setattr(win, "eq_then", lambda fn, said: asked.append(said))
    monkeypatch.setattr(win, "show_page", lambda key, remember=True: shown.append(key))
    win.render_all()
    win.prof_table.clearSelection()
    off_without = [b.text() for b in win.prof_needs_one if b.isEnabled()]
    win.prof_table.selectRow(0)
    chosen = win._selected_profile()
    win.render_profiles()  # (drawn again, as after any change: the profile chosen stays chosen)
    kept = (win._selected_profile() == chosen, all(b.isEnabled() for b in win.prof_needs_one))
    n = len(dialogs.DIALOGS.asked)
    win.prof_edit_btn.click()
    told = dialogs.DIALOGS.asked[n:]
    # (2026-10-27, UI-RULES 19: the chosen profile's commands are off until one is chosen, as File Explorer's; Edit
    # asked for one in a box, Rename and Delete did nothing without a word)
    check("profiles: Edit in Make an EQ, Rename… and Delete… are off until a profile is chosen (Edit with Windows 11's "
          "edit symbol and its Help entry), and stay on when the table is drawn again; with one chosen, Edit shows "
          "Make an EQ and opens the profile there once it has opened",
          not win.prof_edit_btn.icon().isNull() and help_window.entry_of_widget(win.prof_edit_btn)
          and off_without == [] and kept == (True, True) and not told and shown == ["eq"] and len(asked) == 1,
          (off_without, kept, told, shown, asked))
