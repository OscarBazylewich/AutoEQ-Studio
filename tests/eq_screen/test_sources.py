"""Find… › Sources (ui\\sources_window.py): a group with databases you added switched off asks first (No keeps them);
a database switched off and on, one added by its address (a wrong or repeated address said), removed again; This
PC's folders one per line; offline, squig.link's list isn't fetched. Moved from eq_checks.py's rest_checks (lines
2022-2076), on a page opened as the old checks opened it (the eq_screen fixture), offline. The two checks share one
Sources window and one list of what it said, as there, so they're one test: the second's two messages come from the
adds made before the first check."""
import json


def test_sources(eq_screen, monkeypatch, check):
    import net
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox
    from ui.sources_window import Sources
    page, qapp = eq_screen.page, eq_screen.qapp
    S = page.S
    kept_db, kept_folders = json.loads(json.dumps(S["databases"])), list(S["library"].get("folders") or [])
    was_off = net.offline()
    net.set_offline(True)
    said = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: said.append(a[2])))
    try:
        src = Sources(page)
        rows, _ = src.rows()
        builtin = next(r for r in rows if r["builtin"])
        src.set_on(builtin, False)
        off = builtin["name"] in S["databases"]["disabled"]
        src.set_on(builtin, True)
        on = builtin["name"] not in S["databases"]["disabled"]
        src.add("example.squig.link")
        src.add("https://example.squig.link/")
        src.add("https://example.squig.link")
        added = S["databases"]["extra"] == kept_db.get("extra", []) + ["https://example.squig.link/"]
        # (review 2) the added one's group switched off, answered No: nothing changes (it asked after removing them)
        src.render()
        grp = next(src.tree.topLevelItem(i) for i in range(src.tree.topLevelItemCount())
                   if any("example.squig.link" in src.tree.topLevelItem(i).child(j).text(0).lower()
                          or "example" in src.tree.topLevelItem(i).child(j).text(0).lower()
                          for j in range(src.tree.topLevelItem(i).childCount())))
        with monkeypatch.context() as m:
            m.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))
            grp.setCheckState(0, Qt.Unchecked)
        qapp.processEvents()
        asked_first = "https://example.squig.link/" in S["databases"]["extra"]
        # was eq_checks.py:2057
        check("sources: switching off a group with ones you added asks first; No keeps them", asked_first,
              S["databases"]["extra"])
        extra = next(r for r in src.rows()[0] if r["extra"] and "example.squig.link" in r["url"])
        src.set_on(extra, False)
        removed = S["databases"]["extra"] == kept_db.get("extra", [])
        src.folders.setPlainText("C:\\Music\n\n  D:\\Curves  ")
        folders = S["library"]["folders"]
        offline_note = "Offline" in src.dir_note.text()
        src._refresh_soon.stop()
        S["databases"].clear()
        S["databases"].update(kept_db)
        S["library"]["folders"] = kept_folders
        src.reject()
    finally:
        net.set_offline(was_off)
    # was eq_checks.py:2073
    check("sources: a database switched off and on, one added by its address (a wrong or repeated address said), "
          "removed again, the folders one per line; offline, squig.link's list isn't fetched",
          off and on and added and removed and folders == ["C:\\Music", "D:\\Curves"] and offline_note
          and len(said) == 2 and "https://" in said[0] and "already" in said[1], (off, on, added, removed, folders, said))
