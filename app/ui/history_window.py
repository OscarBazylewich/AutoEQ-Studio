"""History: your past EQs, kept between sessions (eq.service /api/history, eq/history.py; AutoEQ Local's history.js,
natively). An EQ goes in when it's saved or copied, or after every run if Advanced › History says so.

The window lists them by day, newest first (a search over IEM, target and method; "This IEM only"). Each: Show (the
EQ back on the graph and in the result card, with its files and curve settings when they're still in the app), Copy
(its filters as Equalizer APO text), ✕ (removed). Clear the history… removes them all (saved files stay).
Copy and Listen show Windows 11's symbols beside their words; ✕ is a subtle button (ui\\theme_sheet.py's eq_windows).
A row's target is in the theme's quieter colour, redone when Windows switches light/dark (follow_theme, which
Compare's graph uses too).
"""
import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from ui import help_window, icons, theme
from ui.theme_sheet import CARD

FIRST_ROWS, ROWS_AT_ONCE = 40, 15  # (rows made at once, then a batch at a time: as Find…)
MODE_SHORT = {"site_single": "Website AutoEQ", "site_sweep": "Website sweep", "best_fit": "Best fit", "autoeq": "AutoEq"}


def follow_theme(window, redraw):
    """redraw(window) each time the theme changes (Windows switched light/dark or its accent colour) while the window
    is shown: for what a window draws in the theme's colours by itself (a graph, a colour in a row's words). The
    window is held weakly, never kept by this; once it's gone the theme forgets this (theme.apply drops a listener
    that raises RuntimeError)."""
    import weakref

    import shiboken6
    ref = weakref.ref(window)

    def again():
        w = ref()
        if w is None or not shiboken6.isValid(w):
            raise RuntimeError("its window is gone")
        if w.isVisible():
            redraw(w)
    theme.on_change(again)


def day_of(t):
    d = datetime.datetime.fromtimestamp(t).date()
    today = datetime.date.today()
    days = (today - d).days
    if days == 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days < 7:
        return d.strftime("%A")
    return f"{d.day} {d.strftime('%B')}" + ("" if d.year == today.year else f" {d.year}")


def time_of(t):
    return datetime.datetime.fromtimestamp(t).strftime("%H:%M")


class HistoryWindow(QDialog):
    def __init__(self, page, this_iem=False):
        super().__init__(page)
        self.page = page
        self.setWindowTitle("History")
        self.resize(760, 640)
        # (smaller, no row was readable; this still fits the Guide's frame, which shows it beside its card)
        self.setMinimumSize(520, 380)
        v = QVBoxLayout(self)
        v.setContentsMargins(CARD, CARD, CARD, CARD)  # (Windows 11's roomier edges, as a card's)
        top = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search: IEM, target, method…")
        # (each key waits a moment: a full History, 1,000 entries, took 2 s a key drawn at once)
        self._later = QTimer(self, singleShot=True, interval=80, timeout=self.render)
        self._more = QTimer(self, singleShot=True, interval=0, timeout=self._make_more)
        self._todo, self._lay = [], None
        self._heads = []  # ((label, entry)): the rows' first lines, coloured again when the theme changes
        self.q.textChanged.connect(lambda: self._later.start())
        top.addWidget(self.q, 1)
        self.only = QCheckBox("This IEM only", self)  # (the window its parent at once: see setVisible below)
        help_window.tag(self.only, "#hist-this")
        self.only.setChecked(this_iem and bool(page.curves))
        self.only.toggled.connect(lambda: self.render())
        top.addWidget(self.only)
        self.only.setVisible(bool(page.curves))  # (with no parent yet it flashed as a window of its own)
        v.addLayout(top)
        self.keep = QLabel()
        theme.mark(self.keep, role="muted")
        v.addWidget(self.keep)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # (rows wrap their words instead)
        v.addWidget(self.scroll, 1)
        bottom = QHBoxLayout()
        clear = QPushButton("Clear the history…")
        clear.clicked.connect(self.clear_all)
        bottom.addWidget(clear)
        bottom.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        bottom.addWidget(close)
        v.addLayout(bottom)
        self.render()
        follow_theme(self, lambda w: w._recolour())

    def render(self, keep=False):
        """The entries, newest first: the first ones at once, the rest a batch at a time. keep: the place in the list
        stays (after ✕)."""
        page = self.page
        bar = self.scroll.verticalScrollBar()
        pos = bar.value() if keep else 0
        words = [w for w in self.q.text().lower().split() if w]
        only = self.only.isChecked() and page.curves
        name = page.curves["name"] if page.curves else None
        entries = [e for e in reversed(page.history)
                   if (not only or e.get("device") == name)
                   and all(w in f"{e.get('device')} {e.get('target')} {MODE_SHORT.get(e.get('mode'), '')} {e.get('label')}".lower()
                           for w in words)]
        self.keep.setText(("Keeps every run's result, and the EQs you save or copy." if page.S["history"]["keep"] == "all"
                           else "Keeps the EQs you save or copy.") + " Change it in Advanced › History.")
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setSpacing(6)
        if not entries:
            lab = QLabel("Nothing matches: try other words, or untick “This IEM only”." if page.history else
                         "No EQs yet. Save or copy one and it's kept here.")
            theme.mark(lab, role="muted")
            lay.addWidget(lab)
        todo, day = [], ""
        for e in entries:
            d = day_of(e["when"])
            if d != day:
                day = d
                todo.append(lambda d=d: self._heading(d))
            todo.append(lambda e=e: self._row(e))
        lay.addStretch(1)
        self._more.stop()
        self._lay, self._todo, self._heads = lay, todo, []
        self._make_more(len(todo) if keep else FIRST_ROWS)
        self.scroll.setWidget(body)
        if keep:
            QTimer.singleShot(0, lambda: bar.setValue(pos))

    @staticmethod
    def _heading(d):
        h = QLabel(d)
        theme.mark(h, role="section")
        return h

    def _make_more(self, n=None):
        todo, self._todo = self._todo[:n or ROWS_AT_ONCE], self._todo[n or ROWS_AT_ONCE:]
        for make in todo:
            self._lay.insertWidget(self._lay.count() - 1, make())  # (before the stretch)
        if self._todo:
            self._more.start()

    def _row(self, e):
        row = QFrame()
        theme.mark(row, card=True)
        h = QHBoxLayout(row)
        text = QVBoxLayout()
        head = QLabel(self._head_text(e))
        head.setTextFormat(Qt.RichText)
        head.setWordWrap(True)
        self._heads.append((head, e))
        text.addWidget(head)
        rms = e.get("rms")
        sub = QLabel(f"{time_of(e['when'])} · {MODE_SHORT.get(e.get('mode'), e.get('mode'))} · {e.get('n_filters')} filter"
                     f"{'' if e.get('n_filters') == 1 else 's'} · error {'–' if rms is None else f'{rms:.2f} dB'} · "
                     f"pre-amp {self.page.preamp_text(e.get('preamp') or 0)} dB")
        theme.mark(sub, role="muted")
        sub.setWordWrap(True)
        text.addWidget(sub)
        h.addLayout(text, 1)
        show = QPushButton("Show")
        theme.mark(show, primary=True)
        show.clicked.connect(lambda: (self.page.bring_back(e), self.accept()))
        copy = QPushButton("Copy")
        icons.put(copy, "copy")  # (Windows 11's symbols beside the words of the common verbs)
        copy.setToolTip("Copy its filters (Equalizer APO / squiglink format)")
        copy.clicked.connect(lambda: self.page.copy_filters(e["filters"], e.get("preamp") or 0, record=False))
        listen = QPushButton("Listen")
        icons.put(listen, "listen")
        listen.setToolTip("Add it to your EQs to compare for the IEM on the graph: hear it in Listen")
        listen.clicked.connect(lambda: self.listen_to(e))
        x = QPushButton("✕")
        x.setObjectName("eqwDelete")  # (a subtle button: ui\theme_sheet.py's eq_windows)
        x.setToolTip("Remove from the history")
        x.clicked.connect(lambda: self.remove([e["key"]]))
        for b in (show, copy, listen, x):
            h.addWidget(b)
        return row

    @staticmethod
    def _head_text(e):
        """A row's first line: the IEM in bold, then the target in the theme's quieter colour (as it is now)."""
        return (f"<b>{_esc(e.get('device'))}</b> <span style='color:{theme.tokens()['muted']}'>→ {_esc(e.get('target'))}"
                "</span>" + ("  · saved" if e.get("saved") else "")
                + ("  · edited" if str(e.get("label", "")).endswith("(edited)") else ""))

    def _recolour(self):
        """The rows' first lines in the theme's colours again (Windows switched light/dark)."""
        for head, e in self._heads:
            head.setText(self._head_text(e))

    def listen_to(self, e):
        """Into the list of the IEM on the graph (an EQ made for another one goes in with a note saying so)."""
        page = self.page
        if not page.curves:
            QMessageBox.information(self, "Listen", "Choose a measurement first: each IEM or headphone has its own list "
                                    "of EQs to compare.")
            return
        other = e.get("device") != page.curves["name"]
        ok = page.listen.add(f"{MODE_SHORT.get(e.get('mode'), 'EQ')}, {e.get('n_filters')} filters "
                             f"({day_of(e['when']).lower()} {time_of(e['when'])})", [dict(f) for f in e["filters"]],
                             f"made for {e.get('device')}" if other else
                             "from History" + (f" · error {e['rms']:.2f} dB" if e.get("rms") is not None else ""))
        if ok and other:
            page.status(f"That EQ was made for {e.get('device')}: on the {page.curves['name']} it won't sound as intended.", 10000)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):  # (never a row's button Qt made the default: the search is live)
            return
        super().keyPressEvent(e)

    def remove(self, keys):
        r = self.page.svc.call("/api/history/remove", {"names": keys})
        if r.get("error"):
            QMessageBox.warning(self, "History", r["error"])
            return
        self.page.history = r.get("entries", [])
        self.page.history_note()
        self.render(keep=True)  # (the place in the list stays)

    def clear_all(self):
        n = len(self.page.history)
        if not n:
            self.page.status("The history is already empty.")
            return
        if QMessageBox.question(self, "Clear the history",
                                f"Remove all {n} EQs from the history? Files you saved stay in your Saved EQs folder.") != QMessageBox.Yes:
            return
        r = self.page.svc.call("/api/history/remove", {"all": True})
        if r.get("error"):  # (history.json couldn't be written: nothing is said cleared)
            QMessageBox.warning(self, "Clear the history", r["error"])
            return
        self.page.history = r.get("entries", [])
        self.page.history_note()
        self.render()
        self.page.status("History cleared.")


def _esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;")
