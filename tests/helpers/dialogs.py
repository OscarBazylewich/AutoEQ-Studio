"""Message boxes and dialogs answered by themselves, so no test can wait for a click that never comes (the app runs
dialogs with exec() in your_files.py, window.py, picker.py, listen.py, eq_page.py and eq_settings.py).

install() (called by helpers.qt.app(), once per process) replaces, for the whole process:
- QMessageBox.information, warning, critical, about: recorded, answered OK;
- QMessageBox.question: recorded, answered Yes (as the old EQ checks did);
- QInputDialog.getText, getItem, getInt, getDouble, getMultiLineText: recorded, cancelled;
- QFileDialog.getOpenFileName, getOpenFileNames, getSaveFileName, getExistingDirectory: recorded, cancelled;
- QDialog.exec, QMessageBox.exec, QMenu.exec: recorded with the window's kind and title, closed at once (Rejected;
  a menu: nothing chosen).
What can't be answered (Qt runs it inside its own code, or PySide6 looks it up past the class): a menu's own exec()
(menu.exec(), as opposed to QMenu.exec(actions, place)) and the menu a button opens when it's clicked. The app opens
its menus with popup() or from their buttons, so a test triggers the menu's action instead of clicking the button.
DIALOGS.asked is what was asked, in order: (kind, text). A test gives its own answer with
dialogs.answer("question", QMessageBox.No) (kept until the test ends: the `dialogs` fixture resets it), or with
monkeypatch.
"""


class Dialogs:
    """What the app asked (asked: [(kind, text)]) and the answers a test chose."""

    def __init__(self):
        self.asked: list[tuple[str, str]] = []
        self._answers = {}

    def answer(self, kind, value):
        """The answer to every `kind` asked from now until the test ends ("question", "information", "getText",
        "getOpenFileName", "exec", "menu", ...)."""
        self._answers[kind] = value

    def reset(self):
        self.asked.clear()
        self._answers.clear()

    def ask(self, kind, text, default):
        """Recorded, said in the test's output, answered."""
        self.asked.append((kind, str(text)))
        print(f"({kind}: {text})")
        return self._answers.get(kind, default)


DIALOGS = Dialogs()
_installed = []


def install():
    """The replacements above, once per process."""
    if _installed:
        return
    from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QMenu, QMessageBox
    d = DIALOGS

    def static(kind, default, text_at=2):
        def fn(*a, **k):
            text = a[text_at] if len(a) > text_at else k.get("text", k.get("label", k.get("caption", "")))
            return d.ask(kind, text, default(a) if callable(default) else default)
        return staticmethod(fn)

    for kind in ("information", "warning", "critical"):
        setattr(QMessageBox, kind, static(kind, QMessageBox.Ok))
    QMessageBox.about = static("about", None)
    QMessageBox.question = static("question", QMessageBox.Yes)
    QInputDialog.getText = static("getText", ("", False))
    QInputDialog.getItem = static("getItem", ("", False))
    QInputDialog.getMultiLineText = static("getMultiLineText", ("", False))
    QInputDialog.getInt = static("getInt", lambda a: (a[3] if len(a) > 3 else 0, False))
    QInputDialog.getDouble = static("getDouble", lambda a: (a[3] if len(a) > 3 else 0.0, False))
    QFileDialog.getOpenFileName = static("getOpenFileName", ("", ""), 1)
    QFileDialog.getOpenFileNames = static("getOpenFileNames", ([], ""), 1)
    QFileDialog.getSaveFileName = static("getSaveFileName", ("", ""), 1)
    QFileDialog.getExistingDirectory = static("getExistingDirectory", "", 1)

    def dialog_exec(self, *a, **k):
        return d.ask("exec", f"{type(self).__name__}: {self.windowTitle()}", QDialog.Rejected)

    def menu_exec(*a, **k):
        menu = a[0] if a and isinstance(a[0], QMenu) else None
        return d.ask("menu", f"QMenu: {menu.title() if menu is not None else ''}", None)

    QDialog.exec = dialog_exec
    QMessageBox.exec = dialog_exec
    QMenu.exec = menu_exec
    _installed.append(True)
