"""The messages of Your files (ui\\your_files.py): "file" or "files" and "was" or "were" chosen by the count, and
"(2), (3) …" when a renamed copy got (3) or more (the user, 2026-11-25; before, "file(s)" and "were renamed with (2)"
for any count). The folders and the moves are stood in: no file of yours is read or moved."""
from PySide6.QtWidgets import QMessageBox

import paths
import userfiles


def _texts(monkeypatch, qapp, dialogs, counts, highest):
    """The texts of the offer to move (Found …), of Change… (Move … to …?) and of the message after the move, for the
    numbers of files `counts` (found, moved, renamed) and the highest copy number given."""
    from ui import your_files
    found, moved, renamed = counts
    asked = []

    def exec_(box):  # (the box as it shows: its words, then its move button, Move them or Move and start again)
        asked.append(box.text() + "\n" + box.informativeText())
        next(b for b in box.buttons() if b.text().startswith("Move")).click()
        return 0
    monkeypatch.setattr(QMessageBox, "exec", exec_)
    monkeypatch.setattr(userfiles, "old_places", lambda: ([("C:\\old\\inputs\\target", "C:\\new\\Targets")], []))
    monkeypatch.setattr(userfiles, "count_files", lambda pairs: found)
    monkeypatch.setattr(userfiles, "move_all", lambda pairs, sources=(): (moved, renamed, highest))
    monkeypatch.setattr(userfiles, "same_folder", lambda a, b: False)
    monkeypatch.setattr(userfiles, "change_pairs", lambda d: [("C:\\from", "C:\\to")])
    monkeypatch.setattr(your_files, "_choose", lambda parent, start: "D:\\Mine")
    monkeypatch.setattr(paths, "locate", lambda: None)
    saved = {}
    your_files.offer_move(None, saved.__setitem__)
    your_files.change_location(None, saved.__setitem__, lambda: None)
    infos = [t for kind, t in dialogs.asked if kind == "information"]
    return asked, infos


def test_one_file_says_file_and_was(monkeypatch, qapp, dialogs, check):
    asked, infos = _texts(monkeypatch, qapp, dialogs, (1, 1, 1), 2)
    check("your files: one file is “1 file” in Found …, in Move … to …? and in Moved …, and one renamed copy “was "
          "renamed with (2)”",
          len(asked) == 2 and "Found 1 file from a previous version in:" in asked[0]
          and asked[1].startswith("Move 1 file to D:\\Mine?")
          and infos == [f"Moved 1 file to {paths.ROOT}.\n\n1 had duplicate names and was renamed with (2) to keep both "
                        "copies."] * 2
          and "file(s)" not in " ".join(asked + infos), (asked, infos))


def test_two_files_say_files_and_were(monkeypatch, qapp, dialogs, check):
    asked, infos = _texts(monkeypatch, qapp, dialogs, (2, 2, 2), 2)
    check("your files: two files are “2 files”, and two renamed copies “were renamed with (2)”",
          len(asked) == 2 and "Found 2 files from a previous version in:" in asked[0]
          and asked[1].startswith("Move 2 files to D:\\Mine?")
          and infos == [f"Moved 2 files to {paths.ROOT}.\n\n2 had duplicate names and were renamed with (2) to keep "
                        "both copies."] * 2, (asked, infos))


def test_a_third_copy_says_2_3(monkeypatch, qapp, dialogs, check):
    asked, infos = _texts(monkeypatch, qapp, dialogs, (3, 3, 2), 3)
    check("your files: when a renamed copy got (3), the message says “renamed with (2), (3) …”",
          infos == [f"Moved 3 files to {paths.ROOT}.\n\n2 had duplicate names and were renamed with (2), (3) … to keep "
                    "both copies."] * 2, infos)


def test_move_gives_the_highest_copy_number(tmp_path, check):
    # (the number that the message needs: a file with "name.txt" and "name (2).txt" already there becomes "(3)")
    old, new = tmp_path / "old", tmp_path / "new"
    old.mkdir()
    new.mkdir()
    (old / "M.txt").write_text("20 1", encoding="utf-8")
    (old / "N.txt").write_text("20 5", encoding="utf-8")
    (new / "M.txt").write_text("20 2", encoding="utf-8")
    (new / "M (2).txt").write_text("20 3", encoding="utf-8")
    (new / "N.txt").write_text("20 6", encoding="utf-8")
    got = userfiles.move_tree(str(old), str(new))
    names = sorted(p.name for p in new.iterdir())
    check("your files: a move gives the highest copy number that a renamed file got (3 when (2) was taken)",
          got == (2, 2, 3) and names == ["M (2).txt", "M (3).txt", "M.txt", "N (2).txt", "N.txt"], (got, names))
