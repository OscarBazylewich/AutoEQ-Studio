"""Asking about your files' folder (userfiles.py moves them; paths.py says where they are):
- offer_move(): your targets, measurements, saved EQs and presets still where an older copy kept them (the program's
  folder): move them into your files' folder (Documents\\AutoEQ Studio), or choose another, or not now (asked again
  next time). Asked when Make an EQ first opens, before the EQ part loads (it takes the folders then)
- change(): Settings > Your files > Change…: another folder; your files moved there if you like; the app starts again
"""
import os

from PySide6.QtWidgets import QFileDialog, QMessageBox

import paths
import userfiles

TITLE = "Your AutoEQ Studio files"
KINDS_LINE = ", ".join((paths.TARGETS_NAME, paths.MEASUREMENTS_NAME, paths.SAVED_EQS_NAME, paths.PRESETS_NAME))


def _choose(parent, start):
    """A folder chosen in Windows' folder picker, checked (None: cancelled, or said why it can't be used)."""
    while True:
        d = QFileDialog.getExistingDirectory(parent, "Select a folder for your AutoEQ Studio files", start)
        if not d:
            return None
        d = os.path.normpath(d)
        why = userfiles.problem_with(d)
        if not why:
            return d
        QMessageBox.warning(parent, TITLE, why)
        start = d


def _said(parent, moved, renamed):
    if moved or renamed:
        QMessageBox.information(parent, TITLE, f"AutoEQ Studio moved {moved} file{'s' if moved != 1 else ''} into "
                                f"{paths.ROOT}." + (f"\n\n{renamed} of them had the same name as a different file in "
                                                    "that folder. AutoEQ Studio kept the two files and added (2) "
                                                    "after the name of the moved file." if renamed else ""))


def offer_move(parent, save):
    """The one-time offer (save(key, value): the app's settings). True when files were moved."""
    pairs, sources = userfiles.old_places()
    if not pairs and not sources:
        return False
    n = userfiles.count(pairs)
    where = sorted({os.path.dirname(old) if os.path.basename(os.path.dirname(old)).lower() == "inputs"
                    else old for old, _new in pairs}) or [os.path.dirname(s) for s in sources]
    box = QMessageBox(parent)
    box.setWindowTitle(TITLE)
    box.setIcon(QMessageBox.Question)
    box.setText("AutoEQ Studio keeps your targets, measurements, saved EQs and presets in the folder where Windows "
                "apps keep your files, each in a different folder:")
    box.setInformativeText(f"{paths.ROOT}\n({KINDS_LINE})\n\n{n} of your files are in the folders of a previous "
                           f"version of AutoEQ Studio:\n" + "\n".join(where) + "\n\nMove them to the new folder? "
                           "AutoEQ Studio does not replace a file.")
    move = box.addButton("Move them", QMessageBox.AcceptRole)
    other = box.addButton("Select a different folder…", QMessageBox.ActionRole)
    box.addButton("Not at this time", QMessageBox.RejectRole)
    box.setDefaultButton(move)
    box.exec()
    if box.clickedButton() is other:
        d = _choose(parent, os.path.dirname(paths.DEFAULT_FILES))
        if not d:
            return False
        save(paths.FILES_KEY, d)
        paths.locate()
        pairs, sources = userfiles.old_places()
    elif box.clickedButton() is not move:
        return False
    try:
        moved, renamed = userfiles.move_all(pairs, sources)
    except OSError as e:
        QMessageBox.warning(parent, TITLE, f"AutoEQ Studio did not move all the files ({e}). The next time that "
                                           "AutoEQ Studio starts, it shows this message again for the other files.")
        return True
    _said(parent, moved, renamed)
    return True


def change(parent, save, restart):
    """Settings > Your files > Change…: save(key, value) keeps the choice; restart() starts the app again."""
    d = _choose(parent, paths.ROOT)
    if not d or userfiles.same_folder(d, paths.ROOT):
        return False
    pairs = userfiles.change_pairs(d)
    n = userfiles.count(pairs)
    if n:
        box = QMessageBox(parent)
        box.setWindowTitle(TITLE)
        box.setIcon(QMessageBox.Question)
        box.setText(f"Move your {n} file{'s' if n != 1 else ''} to {d}?")
        box.setInformativeText(f"They go into {KINDS_LINE} in that folder. AutoEQ Studio does not replace a file. Then "
                               "AutoEQ Studio starts again and uses the new folder.")
        move = box.addButton("Move and start again", QMessageBox.AcceptRole)
        keep = box.addButton("Use it and do not move them", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(move)
        box.exec()
        if box.clickedButton() not in (move, keep):
            return False
        if box.clickedButton() is move:
            try:
                moved, renamed = userfiles.move_all(pairs)
            except OSError as e:
                QMessageBox.warning(parent, TITLE, f"AutoEQ Studio did not move all the files ({e}). It continues to "
                                                   f"use {paths.ROOT}. The files that it moved are in {d}.")
                return False
            save(paths.FILES_KEY, d)
            paths.locate()
            _said(parent, moved, renamed)
            restart()
            return True
    elif QMessageBox.question(parent, TITLE, f"Use {d} for your files? Then AutoEQ Studio starts again and uses it.") \
            != QMessageBox.Yes:
        return False
    save(paths.FILES_KEY, d)
    restart()
    return True
