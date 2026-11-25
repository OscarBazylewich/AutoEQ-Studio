"""Asking about your files' folder (userfiles.py moves them; paths.py says where they are):
- offer_move(): your targets, measurements, saved EQs and presets still where an older copy kept them (the program's
  folder): move them into your files' folder (Documents\\AutoEQ Studio), or choose another, or not now (asked again
  next time). Asked when Make an EQ first opens, before the EQ part loads (it takes the folders then)
- change_location(): Settings > Your files > Change…: another folder; your files moved there if you like; the app starts again
"""
import os

from PySide6.QtWidgets import QFileDialog, QMessageBox

import paths
import userfiles

TITLE = "Your AutoEQ Studio files"
# (the messages below: the user's words of the text survey, 2026-11-24, with "file" or "files" and "was" or "were"
# chosen by the count, and "(2), (3) …" when a copy got (3) or more: the user, 2026-11-25)


def files(n):
    """The count with its noun: "1 file", "2 files"."""
    return f"{n} file" + ("" if n == 1 else "s")


def moved_words(moved, renamed, highest=2):
    """The message after a move. highest: the highest copy number that a renamed file got (userfiles.move_all)."""
    words = f"Moved {files(moved)} to {paths.ROOT}."
    if renamed:
        copies = "(2)" if highest <= 2 else "(2), (3) …"
        words += (f"\n\n{renamed} had duplicate names and {'was' if renamed == 1 else 'were'} renamed with {copies} "
                  "to keep both copies.")
    return words


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


def _tell_moved(parent, moved, renamed, highest):
    if moved or renamed:
        QMessageBox.information(parent, TITLE, moved_words(moved, renamed, highest))


def offer_move(parent, save):
    """The one-time offer (save(key, value): the app's settings). True when files were moved."""
    pairs, sources = userfiles.old_places()
    if not pairs and not sources:
        return False
    n = userfiles.count_files(pairs)
    where = sorted({os.path.dirname(old) if os.path.basename(os.path.dirname(old)).lower() == "inputs"
                    else old for old, _new in pairs}) or [os.path.dirname(s) for s in sources]
    box = QMessageBox(parent)
    box.setWindowTitle(TITLE)
    box.setIcon(QMessageBox.Question)
    box.setText("Your targets, measurements, saved EQs, and presets are stored in:")
    box.setInformativeText(f"{paths.ROOT}\n\nFound {files(n)} from a previous version in:\n" + "\n".join(where)
                           + "\n\nMove them to the current folder? Existing files won't be overwritten.")
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
        moved, renamed, highest = userfiles.move_all(pairs, sources)
    except OSError as e:
        QMessageBox.warning(parent, TITLE, f"Couldn't move all files ({e}). You'll be prompted for the remaining "
                                           "files next time AutoEQ Studio starts.")
        return True
    _tell_moved(parent, moved, renamed, highest)
    return True


def change_location(parent, save, restart):
    """Settings > Your files > Change…: save(key, value) keeps the choice; restart() starts the app again."""
    d = _choose(parent, paths.ROOT)
    if not d or userfiles.same_folder(d, paths.ROOT):
        return False
    pairs = userfiles.change_pairs(d)
    n = userfiles.count_files(pairs)
    if n:
        box = QMessageBox(parent)
        box.setWindowTitle(TITLE)
        box.setIcon(QMessageBox.Question)
        box.setText(f"Move {files(n)} to {d}?")
        box.setInformativeText("Existing files won't be overwritten. AutoEQ Studio will restart to apply the change.")
        move = box.addButton("Move and start again", QMessageBox.AcceptRole)
        keep = box.addButton("Use it and do not move them", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(move)
        box.exec()
        if box.clickedButton() not in (move, keep):
            return False
        if box.clickedButton() is move:
            try:
                moved, renamed, highest = userfiles.move_all(pairs)
            except OSError as e:
                QMessageBox.warning(parent, TITLE, f"Couldn't move all files ({e}). Still using {paths.ROOT}; files "
                                                   f"already moved are in {d}.")
                return False
            save(paths.FILES_KEY, d)
            paths.locate()
            _tell_moved(parent, moved, renamed, highest)
            restart()
            return True
    elif QMessageBox.question(parent, TITLE, f"Use {d} for your files? AutoEQ Studio will restart to apply the change.") \
            != QMessageBox.Yes:
        return False
    save(paths.FILES_KEY, d)
    restart()
    return True
