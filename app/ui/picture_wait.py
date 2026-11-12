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
  only reads it: os.scandir, stat, an open for reading and QImage, never a write, a rename or a delete. The first
  successful look lists the old picture files {name: (time of change, size)}: until then (no folder yet, an error)
  no file is new, so an old picture never ends the wait. A new file (a new name, or a new time or size) is read only
  when two looks in sequence gave the same time and size, and the size is more than 0 (browsers write to a
  .crdownload or .part name first: not picture suffixes). A file that another program holds (it does not open) is
  read again at the next look; one that opens and does not read as a picture is tried again, READ_TRIES looks at
  most; then it is old. A JPEG file without its end mark (a program still writes it: Qt reads the part as a
  picture) is tried again too, and after READ_TRIES looks it is taken as it is. More than one new file: the newest
  first. No folder, or an error: no message, the clipboard still works. A test copy (AUTOEQSTUDIO_ROOT or
  AUTOEQSTUDIO_DATA set, as userfiles.py's) with no AUTOEQSTUDIO_DOWNLOADS looks at no folder. The folder shows in a
  line of its own, cut in its middle with "…" when it is longer than the line (its tooltip has all of it).
- "Paste the picture" (Enter, Ctrl+V): the picture that is on the clipboard at that time, old or new.
- TIMEOUT_MS: the wait stops (timed_out).
`got` is (QImage, jpeg) when a picture came; the dialog then closes with accept(). done() stops everything first (the
signal disconnected, the timers stopped), so a late copy does nothing. Its parent is the window that asked: given
before it shows (the tests' stray watch). A screen reader reads the heading and the steps as the dialog's description.
one_line() and clean_entry(): an entry's words come from a website's list, so a line end or a control character in
them becomes a space, and a format character (a direction mark, a zero-width space) goes, before they go into a
window or a file's first line. They show as plain text (never rich text; in a tooltip too: plain_tip), and the
heading shows NAME_MAX characters of the name at most (heading_name: also the tracer's note on 3 Save), and the
intro the same of the site (short_words without a font: the tray message), the whole words in a tooltip. The
window is as high as its words need (fit_height: also on a small screen at 150 %), never higher than the room of its
screen, and moved up when its bottom is past that room.
"""
import html
import os
import re
import unicodedata

from PySide6 import QtGui
from PySide6.QtCore import QSize, Qt, QTimer
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
NAME_MAX = 80  # (the characters of an entry's name in the heading: then "…", the whole name in its tooltip)
WIDTH, PAD = 520, 24  # (the words' width at least, and the dialog's padding: Windows 11's)
# (line ends, tabs and the other control characters: each run becomes one space)
_CONTROL = re.compile(r"[\s\x00-\x1f\x7f-\x9f]+")


def one_line(text):
    """text with no format character (Unicode's category Cf: the zero-width spaces and joiners, the direction marks
    and overrides, the word joiner and the isolates, the byte order mark, the soft hyphen …: removed with no space,
    as they have no width; a space showed in a word, "Ga te", 2026-11-11), and each run of line ends, control
    characters and spaces as one space (an entry's words come from a website's list: a line end in a name made data
    lines in a traced file's first line, and a right-to-left override showed the name and the words after it in
    reverse)."""
    if not isinstance(text, str):
        return text
    # (also U+2065: not given yet, in the block of the invisible format characters)
    kept = "".join(c for c in text if unicodedata.category(c) != "Cf" and not "\N{WORD JOINER}" <= c <= chr(0x206F))
    return _CONTROL.sub(" ", kept).strip()


def short_words(text):
    """An entry's words (its name, its site) with NAME_MAX characters at most, then "…": where no font is known (a
    tray message). In a window: heading_name, which also cuts a word wider than the line. The whole words go in a
    tooltip (plain_tip)."""
    return text if len(text) <= NAME_MAX else text[:NAME_MAX].rstrip() + "…"


def heading_name(name, fm, room):
    """An entry's name (or its site) for the wait window: NAME_MAX characters at most (then "…"), and on one line
    when a word of it (with the quotation marks) is wider than the line (a damaged list's name of 500 characters cut
    the window's words; a site of 600 words made the window higher than the screen). fm: the label's font metrics;
    room: the line's width."""
    shown = short_words(name)
    marks = fm.horizontalAdvance("“”…")
    if any(fm.horizontalAdvance(w) + marks > room for w in shown.split(" ")):
        shown = fm.elidedText(shown, Qt.ElideRight, room - marks)
    return shown


def plain_tip(text):
    """A tooltip's words that show as their characters: Qt shows a tooltip that looks like rich text as rich text (a
    name "<b>Gate</b> & <img src=x>" from a damaged list showed bold, with a picture), so such words go in escaped,
    in <qt>; other words go in as they are. For the wait window's heading and the tracer's top row."""
    return f"<qt>{html.escape(text)}</qt>" if QtGui.Qt.mightBeRichText(text) else text


def clean_entry(entry):
    """A copy of a database entry with its words on one line each (one_line), or None."""
    return {k: one_line(v) for k, v in entry.items()} if entry else None


def big_enough(img):
    return img.width() >= MIN_SIZE[0] and img.height() >= MIN_SIZE[1]


def downloads_folder():
    """The folder that the wait looks at: AUTOEQSTUDIO_DOWNLOADS (the tests' stand-in) first; a test copy of the app
    (AUTOEQSTUDIO_ROOT or AUTOEQSTUDIO_DATA set: userfiles.py's rule) without it looks at none (""), so that it never
    reads the user's real folder; else the Downloads folder that Windows gives."""
    if os.environ.get("AUTOEQSTUDIO_DOWNLOADS"):
        return os.environ["AUTOEQSTUDIO_DOWNLOADS"]
    if os.environ.get("AUTOEQSTUDIO_ROOT") or os.environ.get("AUTOEQSTUDIO_DATA"):
        return ""
    from PySide6.QtCore import QStandardPaths
    return QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or ""


def folder_pictures(folder):
    """{name: (st_mtime_ns, st_size)} of the picture files in the folder; None with no folder, a folder that is not
    there or an error of the look (not known: not "no files", which would make each old file new). Read only. A
    symbolic link is not a file of the folder (follow_symlinks=False: a link with a picture's name let the wait read
    a file outside the folder, and the window says that it only reads the files of this folder, 2026-11-11)."""
    from ui.trace_window import IMAGE_SUFFIXES
    if not folder:
        return None
    out = {}
    try:
        with os.scandir(folder) as found:
            for e in found:
                if e.name.lower().endswith(IMAGE_SUFFIXES) and e.is_file(follow_symlinks=False):
                    st = e.stat(follow_symlinks=False)
                    out[e.name] = (st.st_mtime_ns, st.st_size)
    except OSError:
        return None
    return out


def _opens(path):
    """The file opens for reading (a different program that holds it with no sharing, a browser or a scanner, stops
    this; the read is then not a try)."""
    try:
        with open(path, "rb"):
            return True
    except OSError:
        return False


def _jpeg_whole(path):
    """The JPEG file has its end mark (FF D9): Qt reads a file that is cut (a program still writes it) as a
    picture, with gray below the cut."""
    try:
        with open(path, "rb") as fh:
            fh.seek(-2, os.SEEK_END)
            return fh.read(2) == bytes((0xFF, 0xD9))
    except OSError:
        return False


def new_picture(folder, old, pending, tries):
    """One look at the folder (it runs in a thread): (QImage or None, jpeg). old: {name: stamp} of the files that do
    not count (None: not known yet, nothing is new); pending: {name: stamp} of the new files at the last look; tries:
    {name: reads that gave no picture}. The caller's three dicts are changed here (the caller does not touch them
    while a look runs). A look with an error changes nothing. Read only."""
    now = folder_pictures(folder)
    if now is None or old is None:
        return None, False
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
        path = os.path.join(folder, name)
        if not _opens(path):  # (held by a different program: read again at the next look, not a try)
            continue
        img = QImage(path)
        jpeg = os.path.splitext(name)[1].lower() in JPEG_SUFFIXES
        tries[name] = tries.get(name, 0) + 1
        # (a JPEG with no end mark is not complete: tried again; after READ_TRIES looks it is taken as it is)
        if not img.isNull() and big_enough(img) and (not jpeg or tries[name] >= READ_TRIES or _jpeg_whole(path)):
            tries.pop(name, None)
            return img, jpeg
        small = not img.isNull() and not big_enough(img)
        if small or tries[name] >= READ_TRIES:  # (a small picture, or not a picture: old from now on)
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


class PathLine(QLabel):
    """A folder's path on one line that never makes the window wider: cut in its middle with "…" when it is longer
    than its room (a long Downloads path with no space went out at the dialog's right edge, and cut the steps above
    it). text() and the tooltip have all of it."""

    def __init__(self, path):
        super().__init__(path)
        self.setToolTip(path)
        self.setTextInteractionFlags(Qt.NoTextInteraction)

    def sizeHint(self):
        return QSize(0, super().sizeHint().height())

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def shown_text(self):
        """The path as drawn: all of it, or its start and end with "…" between."""
        return self.fontMetrics().elidedText(self.text(), Qt.ElideMiddle, max(0, self.contentsRect().width()))

    def paintEvent(self, e):
        from PySide6.QtWidgets import QStylePainter
        p = QStylePainter(self)
        p.drawItemText(self.contentsRect(), int(self.alignment().value), self.palette(), self.isEnabled(),
                       self.shown_text(), self.foregroundRole())


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
        body.setMinimumWidth(WIDTH)  # (the words wrap at this width at least)
        v = QVBoxLayout(body)
        v.setContentsMargins(PAD, PAD, PAD, 20)  # (Windows 11's dialog padding)
        v.setSpacing(8)
        entry = clean_entry(entry) or {}
        self.entry = entry
        # (the entry's words are plain text: a name with "<b>" or "<img>" from a list showed bold or a picture)
        self.head = head = self._words("")
        theme.mark(head, role="heading")
        v.addWidget(head)
        self.intro = self._words("")  # (its words below, with the heading's)
        v.addWidget(self.intro)
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
        self.path = None
        if self.folder:  # (the folder in a line of its own: a long path with no space is cut in its middle)
            self.path = PathLine(os.path.normpath(self.folder))
            theme.mark(self.path, role="muted")
            v.addWidget(self.path)
        self.note = QLabel("")  # (M2: no picture on the clipboard)
        self.note.setWordWrap(True)
        self.note.hide()
        v.addWidget(self.note)
        outer.addWidget(body, 1)
        head.ensurePolished()  # (the heading's font, from the style sheet: its width decides the name's length)
        name = entry.get("name", "")
        shown = heading_name(name, head.fontMetrics(), WIDTH - 2 * PAD)
        head.setText(f"The app waits for a picture of “{shown}”…")
        if shown != name:
            head.setToolTip(plain_tip(name))
        # (the site by the same rule: a site of 600 words made the window higher than the screen, 2026-11-11)
        site = entry.get("site") or ""
        self.intro.ensurePolished()
        shown_site = heading_name(site, self.intro.fontMetrics(), WIDTH - 2 * PAD) if site else "its website"
        intro = f"Your browser shows this entry on {shown_site}. Give the app a picture of its graph:"
        self.intro.setText(intro)
        if site and shown_site != site:
            self.intro.setToolTip(plain_tip(site))
        band, self.paste_btn = dialog_band(self, "Paste the picture", self.paste)
        help_window.tag(self.paste_btn, "#pw-paste")
        # (set after tag(): no "F1 opens Help." in it, F1 does nothing in this window, as Find…'s "Available to
        # download")
        self.paste_btn.setToolTip("Uses the picture that is on the clipboard at this time (also Ctrl+V).")
        outer.addWidget(band)
        # (a screen reader: the focus is on Paste the picture when the window opens, and the words are labels only)
        self.setAccessibleName(self.windowTitle())
        self.setAccessibleDescription(" ".join(
            [head.text(), intro] + [f"{n + 1}. {s}" for n, s in enumerate(self.steps())] + [self.where.text()]
            + ([self.path.text()] if self.path is not None else [])).replace("\n", " "))
        QShortcut(QKeySequence.Paste, self, self.paste)
        self._settle = QTimer(self, singleShot=True, timeout=self._read_clipboard)
        self._limit = QTimer(self, singleShot=True, timeout=self._time_up)
        self._poll = QTimer(self, timeout=self._look)

    @staticmethod
    def _words(text):
        lab = QLabel(text)
        lab.setTextFormat(Qt.PlainText)  # (never rich text: the intro has the site's name from a list)
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
        return ("The app uses the first new picture on the clipboard or in the Downloads folder. "
                "It only reads the files of this folder:")

    # ---------------------------------------------------------------- the wait
    def showEvent(self, e):
        super().showEvent(e)
        self.fit_height()
        if not self._started:
            self.start()

    def fit_height(self):
        """The window as high as its words need at its width: Qt's own size (adjustSize, the first showing) is two
        thirds of the screen at most, and on a small screen at 150 % that cut the last line of step 2. (The size hint's
        height is for the size hint's width: at a different width, a label of wrapped words needs more or less.) Not
        higher than the room of its screen (its words have NAME_MAX characters of a name or a site at most), and
        moved up when its bottom is past that room."""
        h = self.heightForWidth(self.width())
        h = h if h > 0 else self.sizeHint().height()
        # (never higher than the room of its screen, with its title bar: the frame's, or the style's before it shows)
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            from PySide6.QtWidgets import QStyle
            bar = max(self.frameGeometry().height() - self.height(), self.style().pixelMetric(QStyle.PM_TitleBarHeight))
            h = min(h, screen.availableGeometry().height() - bar)
        self.resize(self.width(), h)
        if screen is not None and self.isVisible():  # (its bottom on the screen: it went 1 px past at 150 %)
            room, frame = screen.availableGeometry(), self.frameGeometry()
            if frame.bottom() > room.bottom():
                self.move(self.x(), max(room.top(), self.y() - (frame.bottom() - room.bottom())))

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
            # (the tracer's words)
            self.note.setText("There is no picture on the clipboard. First, copy a picture of a graph.")
            self.note.show()
            self.fit_height()  # (its room for the note)
            return
        self._take(img, jpeg)
