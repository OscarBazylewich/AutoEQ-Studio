"""The Target card's Adjust (ui\\eq_settings.py): it opens under the target; + and ↑ step the tilt and the target is
drawn again; a gain's Hz and Q stay in place, greyed while it's 0; Reset puts the adjustments back to 0 (Undo brings
them back). And Save as a target…: the adjusted target kept as a target of its own, in use, the adjustments back to
0, its rig kept; Undo puts it all back. Moved from eq_checks.py's adjust_checks (lines 2383-2425) and
target_save_checks (2428-2471), on a page opened as the old checks opened it (the eq_screen fixture), the target
unadjusted at the start of each (each puts it back after, as there)."""
import os


def test_adjust_on_the_target_card(eq_screen, check):
    import numpy as np
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication
    page, wait_for = eq_screen.page, eq_screen.wait_for
    st = page.settings
    was = dict(page.S["target_adjust"])
    on_card = st.adjust_btn.isVisibleTo(page) and st.adjust_panel.parentWidget() is page.target_box
    st.adjust_btn.setChecked(True)
    QApplication.processEvents()
    tilt = st.adjust_form.fields["target_adjust.tilt"]
    opened = tilt.box.isVisibleTo(page) and tilt.plus.isVisibleTo(page)
    wait_for(lambda: page.curves is not None, 30)
    before = np.asarray(page.curves["target"]).copy()
    tilt.plus.click()
    stepped = page.S["target_adjust"]["tilt"]
    wait_for(lambda: page.curves is not None and not np.allclose(np.asarray(page.curves["target"]), before), 30)
    redrawn = page.curves is not None and not np.allclose(np.asarray(page.curves["target"]), before)
    QApplication.sendEvent(tilt.box, QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier))
    keyed = (page.S["target_adjust"]["tilt"], tilt.box.text())
    summary = st.adjust_summary.text()
    shown = st.reset_adjust_btn.isEnabled() and st.save_target_btn.isEnabled()
    st.reset_adjust_btn.click()
    reset = (page.S["target_adjust"]["tilt"], tilt.box.text(), st.reset_adjust_btn.isEnabled())
    eq_screen.undo()  # (the message line's Undo)
    undone = page.S["target_adjust"]["tilt"]
    bass, bass_hz = st.adjust_form.fields["target_adjust.bass_gain"], st.adjust_form.fields["target_adjust.bass_freq"]
    hz_greyed = bass_hz.box.isVisibleTo(page) and not bass_hz.box.isEnabled()
    bass.plus.click()
    hz_usable = bass_hz.box.isVisibleTo(page) and bass_hz.box.isEnabled()
    bass.minus.click()
    # was eq_checks.py:2417
    check("target: Adjust, on the Target card, opens the adjustments; + and ↑ step the tilt and the target is drawn "
          "again; a gain's Hz and Q stay in place, greyed while it's 0; Reset puts them back to 0 (Undo brings them back)",
          on_card and opened and hz_greyed and hz_usable and stepped == 0.1 and redrawn and keyed == (0.2, "0.2") and "tilt +0.2" in summary
          and shown and reset == (0.0, "0", False) and undone == 0.2,
          (on_card, opened, hz_greyed, hz_usable, stepped, redrawn, keyed, summary, shown, reset, undone))
    page.S["target_adjust"] = was
    page.changed(curves=True)
    st.adjust_btn.setChecked(False)
    wait_for(lambda: page.curves is not None, 30)


def test_save_as_a_target(eq_screen, monkeypatch, check):
    import numpy as np
    from PySide6.QtWidgets import QInputDialog
    from eq import paths as eq_paths, rigs
    page, wait_for = eq_screen.page, eq_screen.wait_for
    S = page.S
    # (the target chosen by its name, as the old checks had it by then: History's Show had chosen it (line 1583),
    # which sets it and saves the settings at once, as here. On a fresh page none is chosen by name, the first is
    # used, and "its rig kept" would compare the new target's rig with no file's)
    if not S["files"].get("active_target"):
        S["files"]["active_target"] = page.inputs["active_target"]
        page.svc.call("/api/settings", {"settings": S})
    was_target, was_adj = S["files"]["active_target"], dict(S["target_adjust"])
    hidden = not page.settings.save_target_btn.isEnabled()  # (greyed until the target is adjusted)

    def reload_curves():
        """The curves loaded again, and waited for until the new ones are there (made firm 2026-10-22: the old
        check waited only for "some curves", which the page always had, so "drawn the same" compared the curves with
        themselves and could never fail)."""
        old = page.curves
        page.load_curves()
        return wait_for(lambda: page.curves is not None and page.curves is not old, 30)
    S["target_adjust"]["tilt"] = -0.5
    S["target_adjust"]["bass_gain"] = 4.0
    page.svc.call("/api/settings", {"settings": S})
    adjusted = reload_curves()
    shown_before = np.asarray(page.curves["target"]).copy()  # (the target as adjusted, drawn)
    with monkeypatch.context() as m:  # (the name asked for: "My bassy target")
        m.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("My bassy target", True)))
        page.save_adjusted_target()
    wait_for(lambda: page.curves is not None and page.S["files"]["active_target"] == "My bassy target.csv", 30)
    saved = reload_curves()  # (the saved target, drawn: its adjustments are in it now, and back to 0)
    now = page.S
    same = float(np.max(np.abs(np.asarray(page.curves["target"]) - shown_before))) if page.curves else 99
    rig_kept = rigs.target_rig("My bassy target.csv")[0] == rigs.target_rig(was_target)[0]
    state = (now["files"]["active_target"], now["target_adjust"]["tilt"], now["target_adjust"]["bass_gain"])
    made = os.path.exists(os.path.join(eq_paths.TARGET_DIR, "My bassy target.csv"))
    undo_shown = eq_screen.undo_offered()
    eq_screen.undo()
    wait_for(lambda: page.S["files"]["active_target"] == was_target, 30)
    back = (page.S["files"]["active_target"], page.S["target_adjust"]["bass_gain"],
            os.path.exists(os.path.join(eq_paths.TARGET_DIR, "My bassy target.csv")))
    # was eq_checks.py:2463
    check("target: Save as a target… (shown once the target is adjusted) keeps it as a target of its own, in use, the "
          "adjustments back to 0, drawn the same (its rig kept); Undo puts it all back",
          hidden and state == ("My bassy target.csv", 0.0, 0.0) and adjusted and saved and same < 0.05 and rig_kept
          and made and undo_shown and back == (was_target, 4.0, False),
          (hidden, state, adjusted, saved, same, rig_kept, made, back))
    page.S["target_adjust"] = was_adj
    page.S["files"]["active_target"] = was_target
    page.svc.call("/api/settings", {"settings": page.S})
    page.load_curves()
    wait_for(lambda: page.curves is not None, 30)
