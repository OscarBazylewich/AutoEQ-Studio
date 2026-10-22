"""Message boxes and dialogs answered by themselves (helpers.dialogs, PLAN.md 3.8): every replaced one answers at once
and is recorded, a test can give its own answer, and exec() never waits for a click."""
import time

import pytest


def test_message_boxes(qapp, dialogs, check):
    from PySide6.QtWidgets import QMessageBox
    got = [QMessageBox.information(None, "T", "an information"), QMessageBox.warning(None, "T", "a warning"),
           QMessageBox.critical(None, "T", "a critical"), QMessageBox.question(None, "T", "a question?"),
           QMessageBox.about(None, "T", "about")]
    check("dialogs: message boxes answer at once (OK; Yes to a question) and are recorded with their words",
          got == [QMessageBox.Ok, QMessageBox.Ok, QMessageBox.Ok, QMessageBox.Yes, None]
          and dialogs.asked == [("information", "an information"), ("warning", "a warning"),
                                ("critical", "a critical"), ("question", "a question?"), ("about", "about")],
          (got, dialogs.asked))


def test_own_answer(qapp, dialogs, check):
    from PySide6.QtWidgets import QMessageBox
    dialogs.answer("question", QMessageBox.No)
    check("dialogs: a test gives its own answer (No), kept until the test ends",
          QMessageBox.question(None, "T", "first?") == QMessageBox.No
          and QMessageBox.question(None, "T", "second?") == QMessageBox.No, dialogs.asked)


def test_answers_reset_between_tests(qapp, dialogs, check):
    from PySide6.QtWidgets import QMessageBox
    check("dialogs: each test starts with nothing asked and the usual answers",
          not dialogs.asked and QMessageBox.question(None, "T", "again?") == QMessageBox.Yes, dialogs.asked)


def test_input_and_file_dialogs_cancelled(qapp, dialogs, check):
    from PySide6.QtWidgets import QFileDialog, QInputDialog
    got = [QInputDialog.getText(None, "T", "a name"), QInputDialog.getItem(None, "T", "an item", ["a", "b"]),
           QInputDialog.getInt(None, "T", "a number", 7), QInputDialog.getDouble(None, "T", "a value", 2.5),
           QInputDialog.getMultiLineText(None, "T", "some lines"),
           QFileDialog.getOpenFileName(None, "Open one"), QFileDialog.getOpenFileNames(None, "Open some"),
           QFileDialog.getSaveFileName(None, "Save as"), QFileDialog.getExistingDirectory(None, "A folder")]
    check("dialogs: input and file dialogs are cancelled at once and recorded",
          got == [("", False), ("", False), (7, False), (2.5, False), ("", False), ("", ""), ([], ""), ("", ""), ""]
          and [k for k, _ in dialogs.asked] == ["getText", "getItem", "getInt", "getDouble", "getMultiLineText",
                                                "getOpenFileName", "getOpenFileNames", "getSaveFileName",
                                                "getExistingDirectory"]
          and dialogs.asked[0][1] == "a name" and dialogs.asked[5][1] == "Open one", (got, dialogs.asked))


@pytest.mark.timeout(60)
def test_exec_never_waits(qapp, dialogs, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QDialog, QMenu, QMessageBox
    dlg = QDialog()
    dlg.setWindowTitle("A dialog")
    box = QMessageBox()
    box.setWindowTitle("A box")
    one = QAction("one", dlg)
    t = time.monotonic()
    # (a menu's exec() called on the menu itself can't be answered: PySide6 looks it up past the class, and the app
    # never calls it: its menus open with popup() or from their buttons, inside Qt. QMenu.exec(actions, place) can)
    got = [dlg.exec(), box.exec(), QMenu.exec([one], QPoint(0, 0))]
    took = time.monotonic() - t
    check("dialogs: exec() of a dialog, a message box and a menu returns at once (closed, nothing chosen) and is "
          "recorded with its kind and title",
          got[0] == QDialog.Rejected and got[1] == QDialog.Rejected and got[2] is None and took < 5
          and dialogs.asked == [("exec", "QDialog: A dialog"), ("exec", "QMessageBox: A box"), ("menu", "QMenu: ")],
          (got, took, dialogs.asked))
