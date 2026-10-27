"""Finding a target or a measurement (AutoEQ Local's picker.js, natively): one search over three sources:
- In the app: your files (a measurement is a set: its files can be ticked or unticked one by one; moved to the other
  side, or deleted)
- This PC: curve files found in your Downloads, Documents, Desktop and Music (scanned when the window opens, unless
  it was in the last minute; the online lists are loaded again only after half an hour)
- Online databases: the measurers' lists (about 55,000 entries): Use downloads the curve into downloads\\ first

Filters (kept for the next search, for targets and measurements apart): Rig (or "Fits your target's rig": on it, or
its database has a conversion of its own for it), Type, Source, Stated rig (not the usual rig of a database, a "?"),
Downloadable (not a list-only database's). Each choice says how many results it would leave.
Each row's buttons at its right end, as every list's (.claude/notes/UI-RULES.md 18): Preview (its curve on the graph,
dotted, without using it; Hide takes it off), the row's own (Files, → the other side), Use (the main one, last;
double-click too), then the bin apart (your own files: deleted for good, asked first). A button a row hasn't got keeps
its room, so every Use is in one column.

Offline (net.py): the lists the app has are searched as usual; a curve downloaded before is used from this PC, any
other online one says it needs the internet. A list-only database's entry opens on its site (online only).

The look (Windows 11's, ui\\theme_sheet.py's find_windows part matches the names given here): a row's name in
semibold (findRowName), ending in "…" when it's longer than its room (never cut mid-letter), the download mark as
Windows 11's symbol (findMark, read as "Downloads when used"); only one Use has the accent, the one Enter presses (the
chosen row's, or the first row's when none is chosen); a row's ✕ quiet (no fill until pointed at, as every ✕); Files
with Windows 11's chevron after its word (findFiles: down while its files are hidden, up while they're shown); the
chosen and pointed-at rows as every list, laid out again whenever the window changes size. Narrower than its filters
on one line (the Guide's frame for it), the filters take two lines, the ticks under the boxes (Lines); a box's choice
too long for it ends in "…". How many there are where is said under the filters; the footer is every window's
(window_parts.Footer: Sources… and Trace a graph image… at the left, the window's own message line, Close).

Find… is kept within the screen's free room (ui\\window_parts.fit_to_screen, as every window of the app: a laptop at
150 % has about 672 px above the taskbar), so its bottom row is never out of reach.
"""
import os

from PySide6.QtCore import QRect, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QFontMetrics
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSizePolicy, QStyle,
                               QStyleOptionComboBox, QVBoxLayout, QWidget)

import net
from ui import help_window, icons, tasks, theme
from ui.eq_page_parts import Elided, NameCombo
from ui.search_combo import natural_key
from ui.theme_sheet import CARD
from ui.window_parts import Footer, fit_to_screen

LIMIT_ALL, LIMIT_ONE = {"pc": 40, "db": 120}, 400
FIRST_ROWS, ROWS_AT_ONCE = 30, 8  # rows made at once when the list changes, then a batch at a time
CHOICE_MOST = 220   # (px: a filter's box asks for at most this much to show its choice whole; a longer one ends in "…")
FORMS = {"iem": "IEM", "hp": "Headphone", "earbud": "Earbud"}
SOURCES = [("", "All"), ("app", "In the app"), ("pc", "This PC"), ("db", "Online databases")]
ANY = {"rig": "", "form": "", "site": "", "sure": False, "dl": False}
_DB_MADE = {}  # (kind, any kind) -> (the online list, the page's meta, its rows): kept from one Find… to the next
_DB_SORTED = {}  # "items" -> (the online list as it came, the same A to Z): sorted once, off the window's thread


def _keeping_room(w):
    """w, keeping its room when it's hidden (a row without that button: the next ones stay in their column)."""
    keep = w.sizePolicy()
    keep.setRetainSizeWhenHidden(True)
    w.setSizePolicy(keep)
    return w


def name_form(s):
    import re
    s = s or ""
    for form, rx in (("earbud", r"earbud"), ("iem", r"\biems?\b|in-ear|\bie\b"), ("hp", r"headphone|over-ear|on-ear|\bhp\b|\boe\b")):
        if re.search(rx, s, re.I):
            return form
    return ""


def choice_room(box):
    """The width a filter's box needs to show its choice whole (at most CHOICE_MOST: a longer one ends in "…"), never
    under its own smallest size: what Lines gives it on one line (a target's "Made for any type" read "Made for any
    ty" at the Guide's frame's width)."""
    opt = QStyleOptionComboBox()
    box.initStyleOption(opt)
    fm = box.fontMetrics()
    words = QSize(fm.horizontalAdvance(box.currentText()) + 6, fm.height())  # (6: as NameCombo leaves room)
    need = box.style().sizeFromContents(QStyle.CT_ComboBox, opt, words, box).width()
    return max(box.minimumSizeHint().width(), min(need, CHOICE_MOST))


def _share(room, least, low):
    """`room` px shared by controls in equal widths, none under its least; when there isn't room for every least, each
    gets its smallest (low) and what's left in proportion to how much more it wanted."""
    if room >= sum(least):
        out, todo, left = [0] * len(least), list(range(len(least))), room
        while todo:
            each = left // len(todo)
            big = [i for i in todo if least[i] > each]
            if not big:
                for k, i in enumerate(todo):  # (the odd pixels to the first ones)
                    out[i] = each + (1 if k < left - each * len(todo) else 0)
                break
            for i in big:
                out[i] = least[i]
                left -= least[i]
                todo.remove(i)
        return out
    more = [a - b for a, b in zip(least, low)]
    spare, wanted = max(0, room - sum(low)), sum(more) or 1
    return [b + spare * m // wanted for b, m in zip(low, more)]


class Lines(QLayout):
    """A row of controls that takes two lines when there isn't room for it on one (Find…'s filters: the three boxes,
    then the ticks under them): on one line while each control has at least what it asks for (add's least: a box
    what its choice needs, a tick or a button its words), else the `first` ones on a line and the others under them. The room a line has over goes to the
    controls that stretch, in equal widths (none under what it asks for), else, with right, before them (a window's
    buttons at its right). It says how tall it is at a width (height for width), so a window as narrow as the Guide's
    frame for Find… (598 px wide at the app's own size and 523 at its smallest) gives both lines their room; words
    that wrap, alone on their line, can keep room for more lines than they have now (add's rows). (The recheck,
    2026-10-23: squeezed into that frame, Find…'s boxes read "Any sour", "Any ri", its tick "Downloadal", and its
    status line stopped mid-sentence.)"""

    def __init__(self, right=False):
        super().__init__()
        self.right, self._items, self._next = right, [], None

    def add(self, w, first=False, stretch=False, least=None, rows=0):
        """w at the end of the row: on the first line when there are two (first), sharing the room over (stretch),
        asking for least px on one line (a number, or a function of w; else its own: a stretching control's smallest
        size, another's whole size); words that wrap, alone on their line, given room for at least `rows` lines."""
        self._next = (first, stretch, least, rows)
        self.addWidget(w)  # (Qt makes its item and hands it to addItem)

    # ---------------------------------------------------------------- Qt's own: what's in it
    def addItem(self, item):
        self._items.append((item, self._next or (False, False, None, 0)))
        self._next = None

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i][0] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i)[0] if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation.Horizontal

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._place(QRect(0, 0, width, 0), False)

    def sizeHint(self):
        shown, m = self._shown(), self.contentsMargins()
        w = sum(x[0].sizeHint().width() for x in shown) + self._gap() * max(0, len(shown) - 1) + m.left() + m.right()
        return QSize(w, self.heightForWidth(w))

    def minimumSize(self):
        """Its narrowest: on two lines, each control at its smallest; and, as a label whose words wrap, one line's
        height (how tall it is at a width: heightForWidth). The layout it's in asks its height at no less than this
        width: the one-line width here left the ticks' line under the list in the Guide's frame."""
        shown, m, gap = self._shown(), self.contentsMargins(), self._gap()
        lines = [line for line in ([x for x in shown if x[1]], [x for x in shown if not x[1]]) if line]
        w = max((sum(x[3] for x in line) + gap * (len(line) - 1) for line in lines), default=0)
        h = max((x[0].minimumSize().height() for x in shown), default=0)
        return QSize(w + m.left() + m.right(), h + m.top() + m.bottom())

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._place(rect, True)

    # ---------------------------------------------------------------- the lines
    def _gap(self):
        return self.spacing() if self.spacing() >= 0 else 6  # (its window's spacing, once it's in its layout)

    def _shown(self):
        """[(item, first, stretch, smallest, asked for, rows)] of the controls in sight (a hidden one takes no
        room)."""
        out = []
        for item, (first, stretch, least, rows) in self._items:
            if item.isEmpty():
                continue
            low = item.minimumSize().width() if stretch else item.sizeHint().width()
            want = least(item.widget()) if callable(least) else least if least is not None else low
            out.append((item, first, stretch, low, max(low, want), rows))
        return out

    def _lines(self, shown, width):
        if sum(x[4] for x in shown) + self._gap() * max(0, len(shown) - 1) <= width:
            return [shown] if shown else []
        return [line for line in ([x for x in shown if x[1]], [x for x in shown if not x[1]]) if line]

    def _place(self, rect, move):
        """The controls placed in rect (move), or only measured: the height they need there. Given less (a window
        shorter than its parts need), the first line gives up the room and the last stays whole: the buttons stay in
        sight, as in a row of Qt's own (they went under the window's edge), and words that wrap show whole lines."""
        m, gap = self.contentsMargins(), self._gap()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        laid = []  # [(the line, each one's width, each one's own height, the line's height)]
        for line in self._lines(self._shown(), r.width()):
            widths = [x[4] for x in line]
            stretch = [k for k, x in enumerate(line) if x[2]]
            if stretch:
                room = r.width() - sum(w for k, w in enumerate(widths) if k not in stretch) - gap * (len(line) - 1)
                for k, w in zip(stretch, _share(room, [line[k][4] for k in stretch], [line[k][3] for k in stretch])):
                    widths[k] = w
            own = []
            for x, w in zip(line, widths):
                h = x[0].heightForWidth(w) if x[0].hasHeightForWidth() else x[0].sizeHint().height()
                if x[5] and len(line) == 1:  # (alone on its line: room for its rows of words)
                    h = max(h, x[5] * x[0].widget().fontMetrics().lineSpacing())
                own.append(h)
            laid.append((line, widths, own, max(own)))
        need = sum(tall for *_, tall in laid) + gap * max(0, len(laid) - 1)
        if move:
            y, short, between = r.y(), need - r.height(), gap
            if short > 0 and len(laid) > 1:  # (the room between the lines goes first: the Guide's frame gives its
                between = max(0, gap - short)  # window a pixel less than it measured)
                short -= gap - between
            for n, (line, widths, own, tall) in enumerate(laid):
                if n == 0 and short > 0 and len(laid) > 1:
                    tall = max(0, tall - short)
                left = r.width() - sum(widths) - gap * (len(line) - 1)
                x0 = r.x() + (left if self.right and not any(x[2] for x in line) else 0)
                for x, w, h in zip(line, widths, own):
                    # (words that wrap: as tall as they are, in the line's middle; when the line is shorter, as many
                    # whole lines of them as it has room for)
                    if x[0].hasHeightForWidth():
                        if h > tall:
                            spacing = x[0].widget().fontMetrics().lineSpacing()
                            h = tall // spacing * spacing or tall
                        x[0].setGeometry(QRect(x0, y + (tall - h) // 2, w, h))
                    else:
                        x[0].setGeometry(QRect(x0, y, w, tall))  # (in the middle of its line's height)
                    x0 += w + gap
                y += tall + between
        return need + m.top() + m.bottom()


class FoundList(QListWidget):
    """Find…'s list (findList), its rows' widgets laid out again, as wide as the list, whenever it changes size: Qt
    places them before it takes the list's new width, so a window made narrower left every row as wide as before,
    its rig tag, Files, ✕ and Use out of sight with no way to scroll to them, until the list was drawn again (the
    recheck, 2026-10-23: from 900 px to its smallest, 680, each row's Use ended at 855 in a list 644 wide)."""

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.updateGeometries()  # (once more, the list's new width known now)


class FilesButton(QPushButton):
    """Show files / Hide files: a measurement's files under its row (to tick or untick one by one), or hidden again.
    In words, as wide either way: a chevron on a button opens a menu (.claude/notes/UI-RULES.md 12), and this one, drawn
    as a menu button's (the recheck, 2026-10-23, from typed triangles), opened rows."""

    WORDS = ("Show files", "Hide files")

    def __init__(self, shown):
        super().__init__(self.WORDS[1] if shown else self.WORDS[0])
        self.setObjectName("findFiles")

    def sizeHint(self):
        # (room for the longer of its two words, in the font it's drawn in: the row doesn't move as it changes)
        s, fm = super().sizeHint(), self.fontMetrics()
        more = max(fm.horizontalAdvance(w) for w in self.WORDS) - fm.horizontalAdvance(self.text())
        return QSize(s.width() + max(0, more), s.height())

    def minimumSizeHint(self):
        return self.sizeHint()


class Picker(QDialog):
    def __init__(self, page, kind):
        super().__init__(page)
        self.page, self.kind = page, kind
        self.svc, self.meta = page.svc, page.meta
        self.setWindowTitle("Find a target" if kind == "target" else "Find a measurement")
        # (its smallest: 680 wide, where its filters still fit on one line (narrower, as in the Guide's frame for it,
        # they take two: Lines), and four rows or so of the list in sight; both within the screen's free room)
        fit_to_screen(self, (900, 720), (680, 420))
        saved = page.sw.s.get("picker") or {}
        self.filters = {k: dict(ANY, **(saved.get(k) or {})) for k in ("target", "measurement")}
        self.src, self.expanded, self.busy, self._fetching = "", set(), None, False
        self._fails, self._tr = {}, ""
        self.db, self.lib = {"items": [], "loading": True}, {"items": [], "scanning": True}

        v = QVBoxLayout(self)
        v.setContentsMargins(CARD, CARD, CARD, CARD)  # (Windows 11's roomier edges, as every window's: UI-RULES 5)
        top = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search models, makers and databases…")
        self.q.setClearButtonEnabled(True)
        self.q.textChanged.connect(lambda _t: self._later.start())
        top.addWidget(self.q, 1)
        self.anykind = QCheckBox("Targets and measurements")
        self.anykind.setToolTip("Also list the other kind (an entry may be filed as the other)")
        self.anykind.toggled.connect(self.render)
        top.addWidget(self.anykind)
        v.addLayout(top)
        srcs = QHBoxLayout()
        self.src_btns = QButtonGroup(self)
        for key, name in SOURCES:
            b = QPushButton(name)
            b.setCheckable(True)
            theme.mark(b, nav=True)
            b.setChecked(key == "")
            b.clicked.connect(lambda _=False, k=key: self.set_src(k))
            self.src_btns.addButton(b)
            srcs.addWidget(b)
        srcs.addStretch(1)
        v.addLayout(srcs)
        # (on one line, or on two when the window is narrower than that: the boxes, then the ticks under them)
        self.filter_lines = fl = Lines()
        # (the filters' lists open with a search box: the sources alone are over 150; a choice longer than its box
        # ends in "…")
        self.f_rig, self.f_form, self.f_site = NameCombo(), NameCombo(), NameCombo()
        for box, key in ((self.f_rig, "rig"), (self.f_form, "form"), (self.f_site, "site")):
            box.setAccessibleName({"rig": "Rig", "form": "Type", "site": "Source"}[key])
            box.setMinimumContentsLength(10)  # (at 10.5 pt, 14 kept the window wider than the Guide's room for it)
            box.activated.connect(lambda _i, box=box, key=key: self.set_filter(key, box.currentData()))
            fl.add(box, first=True, stretch=True, least=choice_room)
        self.f_sure = QCheckBox("Stated rig")
        self.f_sure.setToolTip("Only those whose source states the rig (not a database's usual rig: a “?”)")
        self.f_sure.toggled.connect(lambda on: self.set_filter("sure", on))
        self.f_dl = QCheckBox("Downloadable")
        for w, key in ((self.anykind, "#pk-anykind"), (self.f_rig, "pk_filters"), (self.f_form, "pk_filters"),
                       (self.f_site, "pk_filters"), (self.f_sure, "#pk-f-sure"), (self.f_dl, "#pk-f-dl")):
            help_window.tag(w, key)
        self.f_dl.setToolTip("Leave out list-only databases (they don't let other programs download their files)")
        self.f_dl.toggled.connect(lambda on: self.set_filter("dl", on))
        self.f_clear = QPushButton("Clear filters")  # (always there, off with no filter on: it made the row jump)
        self.f_clear.clicked.connect(self.clear_filters)
        for w in (self.f_sure, self.f_dl, self.f_clear):
            fl.add(w)
        v.addLayout(fl)
        # (how many there are where, under the filters, over the list: UI-RULES 21; it was in the footer, where the
        # window's messages go now)
        self.status = QLabel()
        self.status.setWordWrap(True)
        theme.mark(self.status, role="muted")
        v.addWidget(self.status)
        self.list = FoundList()  # (its rows laid out again whenever it changes size)
        self.list.setObjectName("findList")  # (its rows' widgets get the whole row: theme_sheet's find_windows)
        self.list.setAccessibleName("Found")
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemDoubleClicked.connect(lambda it: it.data(Qt.UserRole) and self.choose(it.data(Qt.UserRole)))
        self.list.currentItemChanged.connect(lambda *_: self._mark_use())
        v.addWidget(self.list, 1)
        # (every window's footer, window_parts.Footer: its other actions at the left, its own message line, Close)
        sources = QPushButton("Sources…")
        icons.put(sources, "list")
        sources.setToolTip("Which folders on this PC and which online databases Find… searches; add a database")
        sources.clicked.connect(self.open_sources)
        trace = QPushButton("Trace a graph image…")
        icons.put(trace, "trace")
        trace.setToolTip("Only a picture of the graph? Trace it into a curve (as picker.js's link)")
        trace.clicked.connect(lambda: (self.reject(), self.page.open_trace()))
        for b in (sources, trace):
            b.setAutoDefault(False)
        self.footer = Footer(self, [sources, trace])
        v.addWidget(self.footer)
        self._later = QTimer(self, singleShot=True, interval=80, timeout=self.render)
        self._pending, self._more = [], QTimer(self, singleShot=True, interval=0, timeout=self._make_more)
        self._poll = QTimer(self, interval=500, timeout=self._load)
        self._load(first=True)
        self._poll.start()
        self.render()
        self.q.setFocus()

    # ---------------------------------------------------------------- data
    def _load(self, first=False):
        """The online lists (the saved ones at once; online, refreshed in the background) and this PC's files (a
        scan of your folders), asked for until both have finished."""
        if first:
            self.svc.call("/api/db/refresh", {"settings": self.page.S})
            self.svc.call("/api/library/scan", {"settings": self.page.S})
        if self._fetching:  # (the last one still going: not another on top)
            return
        self._fetching = True
        have_db = (len(self.db["items"]), self.db.get("loading"))
        have_lib = (len(self.lib["items"]), self.lib.get("scanning"))

        def fetch():
            # the counts first (cheap); a whole list (55,000 rows) only when it changed: every half second it was
            # built again while the lists loaded
            db, lib = self.svc.call("/api/db"), self.svc.call("/api/library")
            if first or (db.get("count"), db.get("loading")) != have_db:
                db = self.svc.call("/api/db", {"items": True})
                src = db.get("items")
                if src:  # (55,000 rows A to Z: half a second, so here, once per list; the same list after)
                    had = _DB_SORTED.get("items")
                    if not had or had[0] is not src:
                        _DB_SORTED["items"] = (src, sorted(src, key=lambda it: (not str(it[2]).strip(), natural_key(it[2]),
                                                                           str(it[3]).casefold())))  # (nameless last)
                    db = dict(db, items=_DB_SORTED["items"][1])
            if first or (lib.get("count"), lib.get("scanning")) != have_lib:
                lib = self.svc.call("/api/library", {"items": True})
            return db, lib

        def got(res, err):
            self._fetching = False
            if err or not res:
                return
            db, lib = res
            # (a list comes only when it or its loading changed: the counts alone, without rows, aren't a change. They
            # were taken for one, and the whole list was drawn again every half second while this PC was searched)
            changed = db.get("items") is not None or lib.get("items") is not None
            if db.get("items") is not None:
                self.db = db
            if lib.get("items") is not None:
                self.lib = lib
            if not db.get("loading") and not lib.get("scanning"):
                self._poll.stop()
            elif not self._poll.isActive():  # (loading again: Sources changed the lists, a refresh)
                self._poll.start()
            if changed:
                self.render()
        tasks.background(fetch, got, owner=self)

    def app_rig(self, n):
        return (self.page.inputs.get("rigs") or {}).get(n, "")

    def target_rig(self):
        return self.app_rig(self.page.inputs.get("active_target")).replace("?", "")

    def devices(self):
        """The measurements in the app, as devices (sets of files)."""
        out = []
        for name, files in self.page.groups.items():
            out.append({"name": name, "files": files, "on": sum(1 for f in files if f["included"])})
        return out

    def device_rig(self, d):
        rs = list(dict.fromkeys(self.app_rig(f["name"]) for f in d["files"]))
        if len(rs) == 1:
            return rs[0]
        return rs[0].replace("?", "") + "?" if all(r.replace("?", "") == rs[0].replace("?", "") for r in rs) else "mixed"

    def site_of_folder(self, p):
        dl = (self.meta.get("downloads_dir") or "").lower()
        if not dl or not p.lower().startswith(dl):
            return None
        name = p[len(dl) + 1:].replace("/", "\\").split("\\")[0]
        return next((s for s in self.meta.get("database_sites", []) if s.get("folder") == name), None)

    def short_path(self, p):
        dl = self.meta.get("downloads_dir") or ""
        if dl and p.lower().startswith(dl.lower()):
            return "downloaded from " + p[len(dl) + 1:].replace("/", "\\").split("\\")[0]
        home = self.meta.get("home") or ""
        return "~" + p[len(home):] if home and p.lower().startswith(home.lower()) else p

    def want_kind(self, k):
        return self.anykind.isChecked() or k == self.kind

    # ---------------------------------------------------------------- the rows of each source (picker.js)
    def app_rows(self, ws):
        hit = lambda hay: all(w in hay for w in ws)
        inp = self.page.inputs
        if self.kind == "target":
            return sorted(({"src": "app", "key": "app:t:" + n, "name": os.path.splitext(n)[0], "file": n,
                            "sub": "current target" if n == inp["active_target"] else "in the app",
                            "current": n == inp["active_target"], "rig": self.app_rig(n), "form": name_form(n), "site": "app"}
                           for n in inp["targets"] if hit(n.lower())), key=lambda r: natural_key(r["name"]))
        out = []
        for d in self.devices():
            if not hit(d["name"].lower() + " " + " ".join(f["name"].lower() for f in d["files"])):
                continue
            n = len(d["files"])
            on = f" · {'in use' if d['on'] == n else str(d['on']) + ' ticked'}" if d["on"] else ""
            out.append({"src": "app", "key": "app:m:" + d["name"], "name": d["name"], "device": d,
                        "sub": f"{n} file{'s' if n > 1 else ''}{on}", "current": d["on"] > 0, "rig": self.device_rig(d),
                        "form": name_form(d["name"]), "site": "app"})
        return sorted(out, key=lambda r: natural_key(r["name"]))

    def pc_rows(self, ws):
        out = []
        for g in self.lib.get("items") or []:
            if g.get("in_app") or not self.want_kind(g["kind"]):
                continue
            hay = g.setdefault("hay", (g["name"] + " " + g["folder"]).lower())
            if not all(w in hay for w in ws):
                continue
            site, is_t = self.site_of_folder(g["folder"]), g["kind"] == "target"
            out.append({"src": "pc", "key": "pc:" + g["folder"] + "|" + g["name"], "id": g["id"], "name": g["name"],
                        "other": g["kind"] != self.kind, "is_target": is_t, "rig": g.get("rig") or "",
                        "sub": f"{'target' if is_t else str(len(g['files'])) + ' files' if len(g['files']) > 1 else 'measurement'}"
                               f" · {self.short_path(g['folder'])}",
                        "site": site["short"] if site else "pc",
                        "form": (name_form(g["name"]) or (site or {}).get("form", "")) if is_t else
                                ((site or {}).get("form") or name_form(g["name"]))})
        return sorted(out, key=lambda r: (natural_key(r["name"]), natural_key(r["sub"])))

    def db_rows(self, ws):
        """The online entries matching the words. Their rows are made once per list (and kind), then only searched:
        55,000 of them were made again at every key and each time Find… opened (the list stays the same object
        until the lists are loaded again: databases.status)."""
        items, anykind = self.db.get("items") or [], self.anykind.isChecked()
        made = _DB_MADE.get((self.kind, anykind))
        if not (made and made[0] is items and made[1] is self.meta):
            for k in [k for k, m in _DB_MADE.items() if m[0] is not items]:  # (rows of an older list: let go)
                del _DB_MADE[k]
            base, notes, convs = [], self.meta.get("rig_notes") or {}, self.meta.get("unit_convs") or {}
            for it in items:  # [id, "t"|"m", name, sub, site, link|None, rig, form]
                is_t = it[1] == "t"
                if not self.want_kind("target" if is_t else "measurement"):
                    continue
                base.append(((it[2] + " " + it[3] + " " + it[4]).lower(),
                             {"src": "db", "key": f"db:{it[4]}|{it[2]}|{it[3]}", "id": it[0], "name": it[2],
                              "other": is_t != (self.kind == "target"), "sub": f"{it[3]} · {it[4]}", "link": it[5],
                              "rig": it[6] or "", "is_target": is_t, "form": it[7] or "", "site": it[4],
                              "how": "" if is_t else notes.get(f"{it[4]}|{it[3]}") or notes.get(it[4]) or "",
                              "convs": None if is_t else convs.get(f"{it[4]}|{it[3]}") or convs.get(it[4])}))
            made = _DB_MADE[(self.kind, anykind)] = (items, self.meta, base)
        out = [r for hay, r in made[2] if all(w in hay for w in ws)] if ws else [r for _h, r in made[2]]
        if ws:  # (names that start with what's typed first, each part still A to Z)
            out.sort(key=lambda r: not r["name"].lower().startswith(ws[0]))
        return out

    # ---------------------------------------------------------------- the filters
    def rig_of(self, r):
        return "mixed" if r["rig"] == "mixed" else (r["rig"] or "").replace("?", "") or "-"

    def fits(self, r, tr=None):
        tr = self.target_rig() if tr is None else tr
        return bool(tr) and (self.rig_of(r) == tr or any(c.get("from") == tr for c in r.get("convs") or []))

    def failed(self, r, f):
        """The filters a row doesn't pass (their keys). Worked out once per row in a render (self._fails): each
        choice's count asks for every row again, and with 55,000 online entries that was half a million tests a key."""
        out = self._fails.get(id(r))
        if out is not None:
            return out
        out = []
        if f["rig"] and not (self.fits(r, self._tr) if f["rig"] == "fits" else self.rig_of(r) == f["rig"]):
            out.append("rig")
        if f["form"] and (r["form"] or "-") != f["form"]:
            out.append("form")
        if f["site"] and r["site"] != f["site"]:
            out.append("site")
        if f["sure"] and not (r["rig"] and r["rig"] != "mixed" and not r["rig"].endswith("?")):
            out.append("sure")
        if f["dl"] and r.get("link"):
            out.append("dl")
        self._fails[id(r)] = out
        return out

    def passes(self, r, f, skip=None):
        return all(k == skip for k in self.failed(r, f))

    def set_filter(self, key, value):
        self.filters[self.kind][key] = value
        self._save_filters()
        self.render()

    def clear_filters(self):
        self.filters[self.kind] = dict(ANY)
        self._save_filters()
        self.render()

    def _save_filters(self):
        self.page.sw.set("picker", self.filters)

    def set_src(self, s):
        self.src = s
        self.render()

    def _render_filters(self, rows, f):
        rigs = self.meta.get("rigs") or {}
        rig_name = lambda v: "Rig not known" if v == "-" else "Mixed rigs" if v == "mixed" else rigs.get(v, v).split(" (")[0]
        site_name = lambda v: "In the app" if v == "app" else "Your files on this PC" if v == "pc" else v
        facets = [(self.f_rig, "rig", self.rig_of, rig_name, "Any rig"),
                  (self.f_form, "form", lambda r: r["form"] or "-",
                   lambda v: "Type not known" if v == "-" else FORMS.get(v, v),
                   "Made for any type" if self.kind == "target" else "Any type"),
                  (self.f_site, "site", lambda r: r["site"], site_name, "Any source")]
        # each box counts what the other filters leave, all three in one pass (a row failing two filters counts in
        # none; failing one, only in that one's box)
        tr = self._tr
        want_fits = self.kind == "measurement" and bool(tr)
        tally, fits_n = {key: {} for _b, key, *_r in facets}, 0
        for r in rows:
            fl = self.failed(r, f)
            if len(fl) > 1:
                continue
            for _b, key, value_of, *_r in facets:
                if not fl or fl[0] == key:
                    v = value_of(r)
                    tally[key][v] = tally[key].get(v, 0) + 1
            if want_fits and (not fl or fl[0] == "rig") and self.fits(r, tr):
                fits_n += 1
        for box, key, _value_of, name_of, any_ in facets:
            counts = tally[key]
            if f[key] and f[key] not in counts and f[key] != "fits":
                counts[f[key]] = 0
            # A to Z (numbers as numbers); "In the app" and "Your files on this PC" first, "not known" and mixed last
            first = {"app": 0, "pc": 1} if key == "site" else {}
            values = sorted(counts.items(), key=lambda kv: (first.get(kv[0], 2), kv[0] in ("-", "mixed"),
                                                             natural_key(name_of(kv[0]))))
            box.blockSignals(True)
            box.clear()
            box.addItem(any_, "")
            if key == "rig" and self.kind == "measurement" and (self.target_rig() or f[key] == "fits"):
                # (chosen before, for a target whose rig is known: still the filter, so still shown, saying why it
                # leaves nothing)
                n = fits_n
                if n or f[key] == "fits":
                    box.addItem(f"Fits your target's rig: {rig_name(self.target_rig())} or converted for it ({n:,})"
                                if self.target_rig() else "Fits your target's rig (not known for this target: none)", "fits")
            for val, n in values:
                box.addItem(f"{name_of(val)} ({n:,})", val)
            box.setCurrentIndex(max(0, box.findData(f[key])))
            box.blockSignals(False)
        for chk, key in ((self.f_sure, "sure"), (self.f_dl, "dl")):
            chk.blockSignals(True)
            chk.setChecked(bool(f[key]))
            chk.blockSignals(False)
        self.f_dl.setVisible(self.kind != "target")
        self.f_clear.setEnabled(any(f.values()))
        self.filter_lines.invalidate()  # (the boxes' choices changed: the room they ask for too)

    # ---------------------------------------------------------------- the list
    def render(self):
        ws = [w for w in self.q.text().lower().split() if w]
        f = self.filters[self.kind]
        self._fails, self._tr = {}, self.target_rig()
        sections = [(s, title, fn(ws)) for s, title, fn in (("app", "In the app", self.app_rows),
                                                             ("pc", "This PC", self.pc_rows),
                                                             ("db", "Online databases", self.db_rows))
                    if not self.src or self.src == s]
        self._render_filters([r for _, _, rows in sections for r in rows], f)
        lst = self.list
        # (the same search and filters: Show, ticking a file, a list loaded… keep the place in the list and the row)
        view = (self.kind, self.src, self.q.text(), repr(sorted(f.items())), self.anykind.isChecked())
        keep = view == getattr(self, "_view", None)
        place = (lst.count(), lst.verticalScrollBar().value(), lst.currentRow()) if keep else None
        self._view = view
        lst.setUpdatesEnabled(False)
        self._more.stop()
        self._pending = []
        lst.clear()
        later = []  # (the rows past the first ones: made a few at a time after, so a key never waits for them all)
        shown = hidden = 0
        for s, title, found in sections:
            rows = [r for r in found if self.passes(r, f)]
            lim = LIMIT_ONE if self.src else LIMIT_ALL.get(s, 10 ** 9)
            hidden += len(found) - len(rows)
            if not rows and not self.src:
                continue
            if not self.src:
                heading = f"{title}  ·  {len(rows):,}"
                later.append(lambda t=heading: self._note(t, heading=True))
            for r in rows[:lim]:
                later.append(lambda r=r: self._row(r))
                if r.get("device") and r["device"]["name"] in self.expanded:
                    for fl in r["device"]["files"]:
                        later.append(lambda r=r, fl=fl: self._file_row(r, fl))
            shown += min(len(rows), lim)
            if len(rows) > lim:
                more = f"{len(rows) - lim:,} more. Type to narrow the list" + \
                    ("" if self.src else f", or show only {title.lower()} (above).")
                later.append(lambda t=more: self._note(t))
            if not rows and s == "db" and self.db.get("loading"):
                later.append(lambda: self._note("Loading the database lists…"))
        if not shown:
            later.append(lambda: self._note(("Nothing matches." if ws or hidden else "Nothing here yet.")
                                            + (" (Online lists are still loading.)" if self.db.get("loading") else "")))
        if hidden:
            later.append(lambda: self._note(f"{hidden:,} more hidden by the filters: Clear filters (above) shows them."))
        self._pending = later
        self._make_more(max(FIRST_ROWS, place[0]) if place else FIRST_ROWS)
        if place:
            if 0 <= place[2] < lst.count():
                lst.setCurrentRow(place[2])
            lst.verticalScrollBar().setValue(place[1])
            # (once laid out; the list its owner, so a window closed and deleted meanwhile drops it: without one it
            # reached for the deleted list, 2026-10-23)
            QTimer.singleShot(0, lst, lambda v=place[1]: lst.verticalScrollBar().setValue(v))
        self._mark_use()
        lst.setUpdatesEnabled(True)
        self._fails = {}  # (by id: only while these rows are alive)
        n_app = len(self.page.inputs["targets"]) if self.kind == "target" else len(self.devices())
        n_pc = len([g for g in self.lib.get("items") or [] if not g.get("in_app")])
        off = "  ·  Offline: online entries you've downloaded before still work" if net.offline() else ""
        self.status.setText(("Loading online lists…" if self.db.get("loading") else
                             f"{n_app} in the app · {n_pc} on this PC"
                             + (" (still looking)" if self.lib.get("scanning") else "")
                             + f" · {len(self.db.get('items') or []):,} online") + off)

    def _make_more(self, n=None):
        """The next rows of the list (each row is a few widgets, about 2 ms: 120 of them held every key for a
        quarter of a second); the rest a batch at a time while nothing else waits."""
        n = n or ROWS_AT_ONCE
        todo, self._pending = self._pending[:n], self._pending[n:]
        for make in todo:
            make()
        if self._pending:
            self._more.start()

    def finish_list(self):
        """Every row made now (for checks)."""
        self._more.stop()
        while self._pending:
            self._make_more()

    def _note(self, text, heading=False):
        it = QListWidgetItem(text)
        it.setFlags(Qt.NoItemFlags)
        if heading:  # (as Windows 11's group headings: the list's own text, semibold; only the weight is set here)
            f = QFont()
            f.setWeight(QFont.Weight.DemiBold)
            it.setFont(f)
        it.setSizeHint(QSize(0, 36 if heading else 32))  # (the list's rows have no padding of their own: findList)
        self.list.addItem(it)

    def _mark_use(self):
        """The accent on one Use only, the one Enter presses: the chosen row's, or the first row's when none is chosen
        (as Windows 11 keeps the accent for the one main action; the other rows' Use are plain buttons)."""
        if not tasks.alive(self.list):  # (the window going away)
            return
        lst, it = self.list, self.list.currentItem()
        if it is None or not it.data(Qt.UserRole):
            it = next((lst.item(i) for i in range(lst.count()) if lst.item(i).data(Qt.UserRole)), None)
        w = lst.itemWidget(it) if it is not None else None
        use = w.findChild(QPushButton, "findUse") if w is not None else None
        was = getattr(self, "_use_on", None)
        if was is use:
            return
        if was is not None and tasks.alive(was):  # (a row drawn again since is gone with its button)
            theme.mark(was, primary=False)
        if use is not None:
            theme.mark(use, primary=True)
        self._use_on = use

    def _rig_tag(self, r):
        rigs = self.meta.get("rigs") or {}
        tag, key = r["rig"] or "", (r["rig"] or "").replace("?", "")
        made = r.get("is_target") or (r["src"] == "app" and not r.get("device"))
        what = "Made for" if made else "Measured on"
        if tag == "mixed":
            return "mixed", "Its files come from different rigs"
        if key not in rigs:
            return "rig ?", ("Which rig it is made for isn't known" if made else "Which rig it was measured on isn't known") \
                + (f": {r['how']}" if r.get("how") else "")
        guess = tag.endswith("?")
        tip = f"{what}: {rigs[key]}" + (" (probably: the usual rig for its source, not stated by it)" if guess else "") \
            + (f": {r['how']}" if r.get("how") else "")
        convs = r.get("convs") or []
        label = key + ("?" if guess else "")
        if convs:
            short = lambda x: rigs.get(x, x).split(" (")[0]
            label += " ⇄"
            tip += ("\nIts database has a conversion of its own (errors 1–10 kHz): " +
                    "; ".join(f"for {short(c['from'])} targets ({c['models']} models: about {c['error']:.1f} dB left, "
                              f"{c['before']:.1f} without)" for c in convs))
        return label, tip

    def _row(self, r):
        it = QListWidgetItem()
        it.setData(Qt.UserRole, r)
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 3, 8, 3)  # (8: clear of the accent's bar beside a chosen row, level with the headings)
        text = QVBoxLayout()
        text.setSpacing(0)
        # (a long name ends in "…", never the buttons cut: it was cut mid-letter, "…(L800 IEI", in the Guide's frame)
        name = Elided(("✓ " if r.get("current") else "") + r["name"])
        name.setObjectName("findRowName")  # (semibold: theme_sheet's find_windows)
        name.setToolTip(r["name"])
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)  # (the room left for it, whatever its length)
        text.addWidget(name)
        sub = Elided("Downloading…" if self.busy == r["key"] else r["sub"])
        theme.mark(sub, role="muted")
        sub.setToolTip(r["sub"])
        sub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        text.addWidget(sub)
        h.addLayout(text, 1)
        label, tip = self._rig_tag(r)
        tag = QLabel(label)
        theme.mark(tag, role="chip")
        tag.setToolTip(tip)
        h.addWidget(tag, 0, Qt.AlignVCenter)  # (a tag's own height, not the buttons')
        if r.get("other"):
            other = QLabel("measurement?" if self.kind == "target" else "target?")
            theme.mark(other, role="muted")
            other.setToolTip(f"Filed as a {'measurement' if self.kind == 'target' else 'target'}")
            h.addWidget(other)
        if r.get("link"):
            ext = QLabel("open on site ↗")
            theme.mark(ext, role="muted")
            ext.setToolTip("This site doesn't let other programs download its files: Use opens it on the site")
            h.addWidget(ext)
        elif r["src"] == "db":
            dl = QLabel(chr(int(icons.GLYPHS["download"], 16)))  # (Windows 11's symbol, from its icon font: findMark)
            dl.setObjectName("findMark")
            dl.setToolTip("Downloads when used")
            dl.setAccessibleName("Downloads when used")  # (a screen reader read its symbol's character, as nothing)
            h.addWidget(dl)
        # (the row's buttons at its right end as every list's, UI-RULES 18: Preview, the row's own, Use (the main one)
        # last, then the ✕ apart; a button a row hasn't got keeps its room, so every Use is in one column)
        prev = self.page.preview_on(r["key"])
        eye = QPushButton("Hide" if prev else "Preview")  # ("Show" puts an EQ on the result card: UI-RULES 16)
        eye.setMinimumWidth(QFontMetrics(eye.font()).horizontalAdvance("Preview") + 2 * 12 + 2)
        eye.setToolTip("Take it off the graph" if prev else "Show it on the graph, dotted, without using it")
        eye.clicked.connect(lambda _=False, r=r: self.preview(r))
        h.addWidget(_keeping_room(eye))
        # (only once it's in the row: shown before, a button with no parent is a window of its own, and every row
        # flashed one on the screen while the lists loaded: the user saw them, and each cost the window's time)
        eye.setVisible(not r.get("link"))
        x = QPushButton()  # (deleted for good: the bin, UI-RULES 10; quiet, no fill until pointed at, as every row's)
        icons.put(x, "delete")
        theme.mark(x, quiet=True)
        if r["src"] == "app":
            if r.get("device"):
                b = FilesButton(r["device"]["name"] in self.expanded)  # (Windows 11's chevron after "Files")
                b.setToolTip("Tick or untick single files (seatings, left and right)")
                b.clicked.connect(lambda _=False, d=r["device"]["name"]: self.toggle_expand(d))
                h.addWidget(b)
                x.setToolTip(f"Delete {r['device']['name']} from the app")
                x.clicked.connect(lambda _=False, d=r["device"]: self.remove("measurement", [f["name"] for f in d["files"]], d["name"]))
            else:
                mv = QPushButton("→ Measurement")
                mv.setToolTip("It's a measurement: move it to Measurement")
                mv.clicked.connect(lambda _=False, n=r["file"]: self.move("target", n))
                h.addWidget(mv)
                x.setToolTip("Delete from the app")
                x.clicked.connect(lambda _=False, n=r["file"]: self.remove("target", [n], n))
        x.setAccessibleName(x.toolTip() or "Delete from the app")
        use = QPushButton("Use")
        use.setObjectName("findUse")  # (the accent only on the one Enter presses: _mark_use)
        use.setEnabled(self.busy is None)
        use.clicked.connect(lambda _=False, r=r: self.choose(r))
        h.addWidget(use)
        h.addSpacing(8)  # (the ✕ apart from Use, the main action: UI-RULES 14)
        h.addWidget(_keeping_room(x))
        x.setVisible(r["src"] == "app")
        self._place(it, w)

    def _place(self, it, w):
        """A row's widgets into the list, its height from them in the theme's text (worked out before the theme's
        10.5 pt reached them, it was too low). Qt puts them inside a row's padding, so Find…'s list has none
        (findList in theme_sheet's find_windows): the lists' 7 px took 14 px off each row, cutting its names'
        lower parts and its buttons."""
        self.list.addItem(it)
        self.list.setItemWidget(it, w)
        w.ensurePolished()
        it.setSizeHint(w.sizeHint())

    def _file_row(self, r, fl):
        it = QListWidgetItem()
        it.setFlags(Qt.NoItemFlags)
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(46, 2, 6, 2)
        cb = QCheckBox(fl["name"])
        cb.setChecked(fl["included"])
        cb.setToolTip("Include in the average")
        cb.toggled.connect(lambda on, n=fl["name"]: self.toggle_file(n, on))
        h.addWidget(cb, 1)
        mv = QPushButton("→ Target")
        mv.setToolTip("It's a target: move it to Target")
        mv.clicked.connect(lambda _=False, n=fl["name"]: self.move("measurement", n))
        h.addWidget(mv)
        h.addSpacing(8)  # (the bin apart, as every row's: UI-RULES 14)
        x = QPushButton()  # (deleted for good: the bin, UI-RULES 10)
        icons.put(x, "delete")
        theme.mark(x, quiet=True)
        x.setToolTip("Delete from the app")
        x.setAccessibleName(f"Delete {fl['name']} from the app")
        x.clicked.connect(lambda _=False, n=fl["name"]: self.remove("measurement", [n], n))
        h.addWidget(x)
        self._place(it, w)

    # ---------------------------------------------------------------- actions
    def body(self, r):
        if r["src"] == "app":
            if r.get("device"):
                return {"src": "app", "kind": "measurement", "names": [f["name"] for f in r["device"]["files"]], "name": r["name"]}
            return {"src": "app", "kind": "target", "names": [r["file"]]}
        return {"src": r["src"], "id": r["id"]}

    def open_sources(self):
        """Sources (ui/sources_window.py): where Find… looks; the lists and this PC's files again after."""
        from ui.sources_window import Sources
        dlg = Sources(self.page)
        dlg.exec()
        dlg.deleteLater()  # (closed windows let go of their rows)
        self._load(first=True)
        self._poll.start()  # (until the lists, now loading again, are in)
        self.render()

    def keyPressEvent(self, e):
        """In the search box (as picker.js): ↑ ↓ move through the results, Enter uses the one picked (the first when
        none is); Enter never presses a button Qt made the dialog's default."""
        k = e.key()
        if k in (Qt.Key_Return, Qt.Key_Enter):
            if self._later.isActive():  # (typed faster than the list: the list for what's typed)
                self._later.stop()
                self.render()
            rows = [self.list.item(i) for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole)]
            it = self.list.currentItem() if self.list.currentItem() in rows else (rows[0] if rows else None)
            if it is not None and (self.q.hasFocus() or self.list.hasFocus()):
                self.choose(it.data(Qt.UserRole))
            return
        if k in (Qt.Key_Up, Qt.Key_Down) and self.q.hasFocus():
            rows = [i for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole)]
            if rows:
                now = self.list.currentRow()
                later = [i for i in rows if (i > now if k == Qt.Key_Down else i < now)]
                self.list.setCurrentRow((later[0] if k == Qt.Key_Down else later[-1]) if later else
                                        (rows[0] if now < 0 else now))
            return
        super().keyPressEvent(e)

    def choose(self, r):
        if self.busy:
            return
        if r.get("link"):
            if net.offline():  # (said in this window's line, as every "Offline: …", UI-RULES 7)
                self.footer.say("Offline: this database's entries open on its website. Switch to Online (top right) "
                                "to open it.", 10000)
                return
            QDesktopServices.openUrl(QUrl(r["link"]))
            self.footer.say(f"{r['sub'].split(' · ')[-1]} doesn't let other programs download its files, so it opened "
                            "on the site.", 10000)
            return
        if r["src"] == "app":
            if r.get("device"):
                self.page.use_device(r["device"]["name"])
            else:
                self.page.use_target(r["file"])
            self.accept()
            return
        self.busy = r["key"]
        self.render()
        body = dict(self.body(r), kind=self.kind, settings=self.page.S, **({"as": self.kind} if r.get("other") else {}))

        page = self.page

        def done(res, err):
            here = tasks.alive(self)  # (closed meanwhile: what was downloaded is still used)
            if err or (res or {}).get("error"):
                if here:
                    self.busy = None
                    QMessageBox.warning(self, "Use", str(err or res["error"]))
                    self.render()
                return
            page.used(res)
            if here:
                self.busy = None
                self.accept()
        tasks.background(lambda: self.svc.call("/api/use", body), done)

    def preview(self, r):
        if self.page.preview_on(r["key"]):
            self.page.remove_preview(r["key"])
            self.render()
            return
        if not self.page.curves:  # ("do this first": the button on, a box saying what's needed, UI-RULES 25)
            QMessageBox.information(self, "Preview", "Choose a target and a measurement first: a preview is drawn "
                                    "beside them.")
            return
        loading = self.__dict__.setdefault("_showing", set())
        if r["key"] in loading:  # (pressed again while it loads)
            return
        loading.add(r["key"])
        body = dict(self.body(r), settings=self.page.S)

        def done(res, err):
            loading.discard(r["key"])
            if err or (res or {}).get("error"):
                QMessageBox.warning(self, "Preview", str(err or res["error"]))
            else:
                self.page.add_preview(r["key"], res["name"], res["vals"], self.body(r))
            self.render()
        tasks.background(lambda: self.svc.call("/api/preview", body), done, owner=self)

    def toggle_expand(self, name):
        self.expanded.symmetric_difference_update({name})
        self.render()

    def toggle_file(self, name, on):
        ex = set(self.page.S["files"]["excluded"])
        ex.discard(name) if on else ex.add(name)
        self.page.S["files"]["excluded"] = sorted(ex)
        self.page.save_files(after=self.render)

    def move(self, kind, name):
        import json
        before = json.loads(json.dumps(self.page.S["files"]))
        r = self.svc.call("/api/files/move", {"kind": kind, "name": name, "settings": self.page.S})
        if r.get("error"):
            QMessageBox.warning(self, "Move", r["error"])
            return
        self.page.reload_state()
        self.page.moved(kind, name, before)
        self.render()

    def remove(self, kind, names, label):
        if QMessageBox.question(self, "Delete", f"Delete “{label}” ({len(names)} file{'s' if len(names) != 1 else ''}) "
                                "from the app? (A copy you have elsewhere stays.)",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return  # (No the default: it can't be undone, UI-RULES 17)
        r = self.svc.call("/api/files/remove", {"kind": kind, "names": names, "settings": self.page.S})
        if r.get("error"):
            QMessageBox.warning(self, "Delete", r["error"])
            return
        self.page.reload_state()
        self.render()

    def done(self, r=0):
        self._poll.stop()
        super().done(r)
