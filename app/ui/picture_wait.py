"""The wait for a picture from a website: Find…'s Use, or a link of Which measurement, on an entry of a database that
does not let other programs download its files (Hangout.Audio). The page (ui/eq_page_files.py's trace_from_website)
opens the entry in the user's browser, then this small dialog on top of the window that asked (window modal, opened
with open(): nothing blocks). The app has no browser in it and asks the website for nothing.

While it shows, it waits for the first new picture:
- the clipboard (Windows + Shift + S copies a part of the screen): QClipboard.dataChanged, which Qt sends for a copy by
  any program; a picture that was there before it opened sends nothing, so it does not count. The clipboard is read
  SETTLE_MS after the signal (the other program can still hold it), up to SETTLE_TRIES times while it says "picture"
  but gives none. A picture smaller than MIN_SIZE (an icon) does not count.
- the Downloads folder (the website's Screenshot button saves a file there): downloads_folder() gives it, and each
  POLL_MS one look in a thread (ui.tasks.background; a look that is not complete stops the next one from a start)
  only reads it: os.scandir, stat and QImage, never a write, a rename or a delete. The first look lists the old
  picture files {name: (time of change, size)}. A new file (a new name, or a new time or size) is read only when two
  looks in sequence gave the same time and size, and the size is more than 0 (browsers write to a .crdownload or
  .part name first: not picture suffixes). A file that does not read as a picture is tried again, READ_TRIES looks
  at most; then it is old. More than one new file: the newest first. No folder, or an error: no message, the
  clipboard still works. A test copy (AUTOEQSTUDIO_ROOT) with no AUTOEQSTUDIO_DOWNLOADS looks at no folder.
- "Paste the picture" (Enter, Ctrl+V): the picture that is on the clipboard at that time, old or new.
- TIMEOUT_MS: the wait stops (timed_out).
`got` is (QImage, jpeg) when a picture came; the dialog then closes with accept(). done() stops everything first (the
signal disconnected, the timers stopped), so a late copy does nothing. Its parent is the window that asked: given
before it shows (the tests' stray watch).
"""
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QVBoxLayout, QWidget

from ui import help_window, tasks, theme
from ui.window_parts import dialog_band, muted

SETTLE_MS = 150       # after a clipboard signal, before the read
SETTLE_TRIES = 5      # reads while the clipboard says "picture" but gives none
POLL_MS = 1000        # a look at the Downloads folder
READ_TRIES = 5        # looks that try to read a new file that is not (yet) a picture
TIMEOUT_MS = 600_000  # the wait stops (10 minutes)
MIN_SIZE = (300, 200)  # a smaller picture is not a graph (a copied icon)
JPEG_SUFFIXES = (".jpg", ".jpeg", ".jfif")


def big_enough(img):
    return img.width() >= MIN_SIZE[0] and img.height() >= MIN_SIZE[1]


def downloads_folder():
    """The folder that the wait looks at: AUTOEQSTUDIO_DOWNLOADS (the tests' stand-in) first; a test copy of the app
    (AUTOEQSTUDIO_ROOT set) without it looks at none (""), so that it never reads the user's real folder; else the
    Downloads folder that Windows gives."""
    if os.environ.get("AUTOEQSTUDIO_DOWNLOADS"):
        return os.environ["AUTOEQSTUDIO_DOWNLOADS"]
    if os.environ.get("AUTOEQSTUDIO_ROOT"):
        return ""
    from PySide6.QtCore import QStandardPaths
    return QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or ""


def folder_pictures(folder):
    """{name: (st_mtime_ns, st_size)} of the picture files in the folder; {} with no folder. Read only."""
    from ui.trace_window import IMAGE_SUFFIXES
    out = {}
    if not folder:
        return out
    try:
        with os.scandir(folder) as found:
            for e in found:
                if e.name.lower().endswith(IMAGE_SUFFIXES) and e.is_file():
                    st = e.stat()
                    out[e.name] = (st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    return out


def new_picture(folder, old, pending, tries):
    """One look at the folder (it runs in a thread): (QImage or None, jpeg). old: {name: stamp} of the files that do
    not count; pending: {name: stamp} of the new files at the last look; tries: {name: reads that gave no picture}.
    The caller's three dicts are changed here (the caller does not touch them while a look runs). Read only."""
    now = folder_pictures(folder)
    ready = []
    for name, stamp in now.items():
        if old.get(name) == stamp:
            pending.pop(name, None)
            continue
        if pending.get(name) == stamp and stamp[1] > 0:  # (two looks in sequence gave the same: complete)
            ready.append((stamp[0], name))
        else:
            pending[name] = stamp
            tries.pop(name, None)  # (it changed: a new try)
    for name in [n for n in pending if n not in now]:
        del pending[name]
    for _t, name in sorted(ready, reverse=True):  # (the newest first)
        img = QImage(os.path.join(folder, name))
        if not img.isNull() and big_enough(img):
            return img, os.path.splitext(name)[1].lower() in JPEG_SUFFIXES
        tries[name] = tries.get(name, 0) + 1
        if not img.isNull() or tries[name] >= READ_TRIES:  # (a small picture, or not a picture: old from now on)
            old[name] = pending.pop(name)
            tries.pop(name, None)
    return None, False


def clipboard_picture():
    """(QImage or None, jpeg): the clipboard's picture, or a copied picture file (as the page's paste reads it)."""
    from ui.trace_window import IMAGE_SUFFIXES
    md = QApplication.clipboard().mimeData()
    if md is None:
        return None, False
    for u in md.urls() if md.hasUrls() else []:
        if u.isLocalFile():
            path = u.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in IMAGE_SUFFIXES:
                img = QImage(path)
                if not img.isNull():
                    return img, ext in JPEG_SUFFIXES
    if md.hasImage():
        img = QImage(md.imageData())
        if not img.isNull():
            return img, False
    return None, False


class PictureWait(QDialog):
    """The wait window (see the module's docstring). entry: /api/db/entry's ("name", "site", …)."""

    def __init__(self, parent, entry):
        super().__init__(parent)
        self.entry = entry
        self.got = None
        self.timed_out = False
        self._started = self._stopped = False
        self._tries = 0
        self.folder = downloads_folder()
        self._old, self._pending, self._read_tries = None, {}, {}  # (the looks' lists: new_picture)
        self._looking = False
        self.setWindowTitle("Picture from the website")
        theme.mark(self, dialog=True)  # (Windows 11's dialog: the words on the card's colour, UI-RULES 2)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QWidget()
        body.setMinimumWidth(520)  # (the words wrap at this width at least)
        v = QVBoxLayout(body)
        v.setContentsMargins(24, 24, 24, 20)  # (Windows 11's dialog padding)
        v.setSpacing(8)
        head = QLabel(f"The app waits for a picture of “{entry.get('name', '')}”…")
        head.setWordWrap(True)
        theme.mark(head, role="heading")
        v.addWidget(head)
        v.addWidget(self._words(f"Your browser shows this entry on {entry.get('site', 'its website')}. Give the app "
                                "a picture of its graph:"))
        steps = QGridLayout()  # (a step's number in a column of its own: its words wrap under its words)
        steps.setHorizontalSpacing(6)
        steps.setVerticalSpacing(6)
        steps.setColumnStretch(1, 1)
        for n, text in enumerate(self.steps()):
            steps.addWidget(QLabel(f"{n + 1}."), n, 0, Qt.AlignTop)
            steps.addWidget(self._words(text), n, 1)
        v.addLayout(steps)
        self.where = muted(self.where_text())
        v.addWidget(self.where)
        self.note = QLabel("")  # (M2: no picture on the clipboard)
        self.note.setWordWrap(True)
        self.note.hide()
        v.addWidget(self.note)
        outer.addWidget(body, 1)
        band, self.paste_btn = dialog_band(self, "Paste the picture", self.paste)
        self.paste_btn.setToolTip("Uses the picture that is on the clipboard at this time (also Ctrl+V).")
        help_window.tag(self.paste_btn, "#pw-paste")
        outer.addWidget(band)
        QShortcut(QKeySequence.Paste, self, self.paste)
        self._settle = QTimer(self, singleShot=True, timeout=self._read_clipboard)
        self._limit = QTimer(self, singleShot=True, timeout=self._time_up)
        self._poll = QTimer(self, timeout=self._look)

    @staticmethod
    def _words(text):
        lab = QLabel(text)
        lab.setWordWrap(True)
        return lab

    def steps(self):
        """The procedure, one step for each line."""
        copy = ("Press Windows + Shift + S. Then select the area of the graph. Windows copies the picture to the "
                "clipboard.")
        return ["Maximize the window of your browser. Larger pictures give better results.",
                copy + "\nOr click Screenshot on the website. Your browser saves the picture in the Downloads folder."
                if self.folder else copy]

    def where_text(self):
        if not self.folder:
            return "The app uses the first new picture on the clipboard."
        return (f"The app uses the first new picture on the clipboard or in {os.path.normpath(self.folder)}. It only "
                "reads the files of that folder.")

    # ---------------------------------------------------------------- the wait
    def showEvent(self, e):
        super().showEvent(e)
        if not self._started:
            self.start()

    def start(self):
        """The signal, the looks at the folder (the first one at once: the old files) and the time limit (one time;
        POLL_MS and TIMEOUT_MS read now, so that a test can set them)."""
        self._started = True
        QApplication.clipboard().dataChanged.connect(self._clipboard_changed)
        self._limit.start(TIMEOUT_MS)
        if self.folder:
            self._poll.start(POLL_MS)
            self._look()

    def _look(self):
        """One look at the folder, in a thread (the first one lists the old files)."""
        if self._looking or self._stopped or self.got is not None or not self.folder:
            return
        self._looking = True
        folder, old, pending, tries = self.folder, self._old, self._pending, self._read_tries
        first = old is None

        def look():
            return folder_pictures(folder) if first else new_picture(folder, old, pending, tries)

        def done(res, err):
            self._looking = False
            if self._stopped or self.got is not None or err is not None:  # (an error: no message, the clipboard works)
                return
            if first:
                self._old = res
            elif res[0] is not None:
                self._take(*res)
        tasks.background(look, done, owner=self)

    def stop(self):
        """Everything stopped: no signal, no timer, a late answer dropped."""
        if self._stopped:
            return
        self._stopped = True
        if self._started:
            try:
                QApplication.clipboard().dataChanged.disconnect(self._clipboard_changed)
            except (RuntimeError, TypeError):  # (not connected)
                pass
        self._settle.stop()
        self._limit.stop()
        self._poll.stop()

    def done(self, code):
        self.stop()
        super().done(code)

    def _clipboard_changed(self):
        if self._stopped or self.got is not None:
            return
        self._tries = 0
        self._settle.start(SETTLE_MS)

    def _read_clipboard(self):
        if self._stopped or self.got is not None:
            return
        img, jpeg = clipboard_picture()
        if img is None:
            md = QApplication.clipboard().mimeData()
            if md is not None and md.hasImage() and self._tries < SETTLE_TRIES:  # (it says "picture", gives none yet)
                self._tries += 1
                self._settle.start(SETTLE_MS)
            return
        if big_enough(img):
            self._take(img, jpeg)

    def _take(self, img, jpeg):
        """The first picture: the window closes with it (only one counts)."""
        if self._stopped or self.got is not None:
            return
        self.got = (img, jpeg)
        self.accept()

    def _time_up(self):
        self.timed_out = True
        self.reject()

    def paste(self):
        """Paste the picture (Enter, Ctrl+V): the picture on the clipboard at this time, old or new."""
        img, jpeg = clipboard_picture()
        if img is None:
            self.note.setText("There is no picture on the clipboard. Copy a picture of the graph first.")
            self.note.show()
            self.adjustSize()  # (its room for the note)
            return
        self._take(img, jpeg)
