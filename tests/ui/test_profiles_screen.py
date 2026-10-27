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
        named = ("Import EQ files…", "Rename", "Remove", "Show the files")
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
    win.prof_table.setCurrentCell(-1, -1)
    n = len(dialogs.DIALOGS.asked)
    win.prof_edit_btn.click()
    told = dialogs.DIALOGS.asked[n:]
    win.prof_table.setCurrentCell(0, 0)
    win.prof_edit_btn.click()
    check("profiles: Edit in Make an EQ (with Windows 11's edit symbol and its Help entry) asks for a profile first; "
          "with one chosen, it shows Make an EQ and opens the profile there once it has opened",
          not win.prof_edit_btn.icon().isNull() and help_window.entry_of_widget(win.prof_edit_btn)
          and told and "Choose a profile" in told[0][1] and shown == ["eq"] and len(asked) == 1, (told, shown, asked))
