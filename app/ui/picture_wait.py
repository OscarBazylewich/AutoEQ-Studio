"""The wait for a picture from a website: Find…'s Use, or a link of Other measurements of this model, on an entry of
a database that does not let other programs download its files (Hangout.Audio, or a website that refused a
download), a measurement or a target. The page (ui/eq_page_files.py's trace_from_website) opens the entry in the
user's browser (or the page of the database when the app knows no link to the entry: "site_page", and step 1 then
tells the user to select it; else step 1 tells what to do when the website does not show it: its share link is not
verified on each website), then this small dialog on top of the window that asked (window modal, opened with open():
nothing blocks). For a target entry it also says that the website can change a target with its settings
(TARGET_SETTINGS). The app has no browser in it and asks the website for nothing.

While it shows, it waits for the first new picture:
- the clipboard (Windows + Shift + S): QClipboard.dataChanged, which Qt sends for a copy by any program, so a picture
  that was there before does not count; read SETTLE_MS after the signal (the other program can still hold it), up to
  SETTLE_TRIES times; smaller than MIN_SIZE does not count.
- the Downloads folder (the website's Screenshot button saves a file there; downloads_folder(): a test copy looks at
  none): one look each POLL_MS in a thread, read only (folder_pictures, new_picture give the rules for a new file;
  browsers write to a .crdownload or .part name first, not a picture suffix, so a download in progress is not read).
  No folder, or an error: no message, the clipboard still works.
- "Paste the image" (Enter, Ctrl+V): the picture that is on the clipboard at that time, old or new.
- TIMEOUT_MS: the wait stops (timed_out).
`got` is (QImage, jpeg) when a picture came (accept()). done() stops everything first, so a late copy does nothing.
Its parent is the window that asked, given before it shows (the tests' stray watch). An entry's words come from a
website's list: one_line/clean_entry clean them, short_words/heading_name shorten them, and they always show as
plain text (plain_tip). The window is as high as its words need (fit_height).
"""
import html
import os
import re
import unicodedata

from PySide6 import QtGui
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QVBoxLayout, QWidget

from ui import help_window, placed, tasks, theme
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
# (the first sentence of step 1, steps(): a large browser window, and no window of the website in front of the
# graph. The owner's words for the whole step 1 (the text survey, 2026-11-24); the survey also gave "Close any popups
# covering the graph" for this part alone, but the step is one text, so the words of the whole step are used)
FRONT_WINDOW = "Maximize your browser for better accuracy, and close any popups over the graph."
# (step 1 too: the share link of an entry is not verified on each website, and a page link shows no entry. The
# period ends the step, as in the owner's words for the whole step 1)
NOT_SHOWN = "If this entry isn't shown, select it from the site's list."
SELECT = "Select this entry from the site's list."
# (a target entry: the website changes a target with its settings, "(Tilt: -0.4dB/Oct, Bass: 8dB)" in its legend,
# seen by the owner on graph.hangout.audio, 2026-11-12; the app does not read or change them)
TARGET_SETTINGS = "Site target adjustments (like tilt or bass) are captured in the screenshot"
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


def spoken(text):
    """The words of a label for the window's description (a screen reader reads it as one text): its lines joined
    with a space, each ending with a period when it has no end mark (".", ":", "…", "!" or "?")."""
    lines = [s.strip() for s in text.split("\n") if s.strip()]
    return " ".join(s if s[-1] in ".:…!?" else s + "." for s in lines)


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
    for _t, name in sorted(ready, reverse=True):
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
        self.setWindowTitle("Image from the website")
        theme.mark(self, dialog=True)  # (Windows 11's dialog: the words on the card's colour, UI-RULES 2)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QWidget()
        body.setMinimumWidth(WIDTH)
        v = QVBoxLayout(body)
        v.setContentsMargins(PAD, PAD, PAD, 20)  # (Windows 11's dialog padding)
        v.setSpacing(8)
        entry = clean_entry(entry) or {}
        self.entry = entry
        # (the entry's words are plain text: a name with "<b>" or "<img>" from a list showed bold or a picture)
        self.head = head = self._words("")
        theme.mark(head, role="heading")
        v.addWidget(head)
        self.intro = self._words("")
        v.addWidget(self.intro)
        steps = placed(v, QGridLayout())  # (a step's number in a column of its own: its words wrap under its words)
        steps.setHorizontalSpacing(6)
        steps.setVerticalSpacing(6)
        steps.setColumnStretch(1, 1)
        for n, text in enumerate(self.steps()):
            steps.addWidget(QLabel(f"{n + 1}."), n, 0, Qt.AlignTop)
            steps.addWidget(self._words(text), n, 1)
        self.target_note = None
        if entry.get("kind") == "target":
            self.target_note = self._words(TARGET_SETTINGS)
            v.addWidget(self.target_note)
        self.where = muted(self.where_text())
        v.addWidget(self.where)
        self.path = None
        if self.folder:
            self.path = PathLine(os.path.normpath(self.folder))
            theme.mark(self.path, role="muted")
            v.addWidget(self.path)
        self.note = QLabel("")  # (paste()'s message when the clipboard has no picture)
        self.note.setWordWrap(True)
        self.note.hide()
        v.addWidget(self.note)
        outer.addWidget(body, 1)
        head.ensurePolished()  # (the heading's font, from the style sheet: its width decides the name's length)
        name = entry.get("name", "")
        shown = heading_name(name, head.fontMetrics(), WIDTH - 2 * PAD)
        head.setText(f"Waiting for a graph screenshot of “{shown}”…")
        if shown != name:
            head.setToolTip(plain_tip(name))
        # (the site by the same rule: a site of 600 words made the window higher than the screen, 2026-11-11)
        site = entry.get("site") or ""
        self.intro.ensurePolished()
        # (the site in quotation marks: a cut site ended in "…" and then the period of the sentence, 2026-11-12)
        shown_site = (f"“{heading_name(site, self.intro.fontMetrics(), WIDTH - 2 * PAD)}”" if site
                      else "the website")
        # (a link to the page of the database, not to the entry: eq.service's site_page. The steps follow the ":")
        intro = (f"Opened {shown_site}. Capture this entry's graph:"
                 if entry.get("site_page") else
                 f"Opened on {shown_site}. Capture its graph:")
        self.intro.setText(intro)
        if site and shown_site != f"“{site}”":
            self.intro.setToolTip(plain_tip(site))
        band, self.paste_btn = dialog_band(self, "Paste the image", self.paste)
        # (no tooltip: the owner removed the button's own tooltip and the first line of its Help entry, the text
        # survey, 2026-11-24; the tag stays for F1 and the button's name for a screen reader. F1 opens Help in a window that blocks the others, as this one does, since such
        # a window gets an F1 shortcut of its own (ui\window.py's F1Anywhere), 2026-11-12)
        help_window.tag(self.paste_btn, "#pw-paste")
        outer.addWidget(band)
        # (a screen reader: the focus is on Paste the image when the window opens, and the words are labels only)
        self.setAccessibleName(self.windowTitle())
        # (the owner's words of the text survey, 2026-11-24, have no period at the end of some lines (step 2, the
        # target note): on the screen each is a line of its own, but in one description they ran together, "drag
        # over the graph Or click …", so each line ends with a period there. The path gets none: it is a file name)
        self.setAccessibleDescription(" ".join(
            [spoken(head.text()), spoken(intro)] + [f"{n + 1}. {spoken(s)}" for n, s in enumerate(self.steps())]
            + ([spoken(TARGET_SETTINGS)] if self.target_note is not None else []) + [spoken(self.where.text())]
            + ([self.path.text()] if self.path is not None else [])))
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
        copy = "Press Win+Shift+S and drag over the graph"
        # (a website can show a window in front of its graph at the first visit, "Welcome to Squiglink": the screen
        # copy then had no graph, 2026-11-11)
        find = SELECT if (self.entry or {}).get("site_page") else NOT_SHOWN
        return [" ".join(s for s in (FRONT_WINDOW, find) if s),
                copy + "\nOr click Screenshot on the site to save it to Downloads" if self.folder else copy]

    def where_text(self):
        if not self.folder:
            return "Auto-imports the next image copied to your clipboard"
        return "Auto-imports the next image from your clipboard or Downloads (watches only this folder):"

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
        higher than the room of its screen (its words have NAME_MAX characters of a name or a site at most; on a
        screen with less room than the words need, the window has that room, but not less than its layout's minimum),
        and moved up when its bottom is past that room."""
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
        """Paste the image (Enter, Ctrl+V): the picture on the clipboard at this time, old or new."""
        img, jpeg = clipboard_picture()
        if img is None:
            # (the tracer's words)
            self.note.setText("No image on clipboard. Copy a graph image first.")
            self.note.show()
            self.fit_height()  # (its room for the note)
            return
        self._take(img, jpeg)
