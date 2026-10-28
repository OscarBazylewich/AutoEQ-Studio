"""The "Make an EQ" screen: AutoEQ Local's page, natively. One column, as there:
- the graph: your measurement, the target and the measurement with the EQ; under it the EQ itself (0 dB = no change)
- Target, then Measurement: what's in the app (your Targets and Measurements folders), and Add… for files on this PC
- Make the EQ: your EQ app (its limits are kept, its file is what Save writes), the method, the search (what a run
  tries and how long it takes), Run, and the run's progress
- the result: its numbers, its filters (Fewer or more filters: the best result for each count), Save filters (the
  files your EQ app needs, under the File name), and Use on device: the EQ becomes a device's profile, switched on
- by the graph's title: Trace a graph image… (ui/trace_window.py: a picture of a graph becomes a measurement or
  target) and History…; under the result, Listen (ui/listen.py)

Everything it does goes through eq.service (AutoEQ Local's page's requests, called directly); slow ones run off the
window's thread (ui.tasks). The EQ part is loaded when this screen is first opened, or ahead of that while the window
is open for someone who has opened it before (the window makes the page then, hidden: ui/preload.py), never while the
app is only in the tray (it stays light); AutoEQ Local's files are brought over first (eq.bring_over: once, on the
first opening).
Opening (start()): the EQ part loads off the window's thread, then the page is made in steps, one per turn of the
window's event loop, each a few ms, so the window never freezes (ui/eq_page_cards.py); `ready` is True once the page
is whole and its files are shown (the window, the Guide and Presets wait for it). Made ahead while you're on another
screen, it says nothing (no message box, no status line) until you first see it: what it would have said then is
said when it's first shown. This PC is searched once you've seen the page (Find… asks again as it opens).
Its Guide: ui\\guide.py (the top bar's Guide); F1 on a control: its entry in Help.

The page is one object, EqPage, made of parts, one file each: plain classes (no __init__, no signals) that share the
page's controls and data, joined here with QWidget last:
- ui/eq_page_cards.py, EqCards: the cards (how the page is laid out: the file to restyle it in; its own style rules
  are ui/theme_sheet.py's eq_screen part)
- ui/eq_page_graph.py, EqGraph: the curves, the analysis and automatic settings, the graph, the curves shown from
  Find…, Listen's marker
- ui/eq_page_handles.py, EqHandles: the EQ graph's handles (drag a filter, the wheel for its Q, right-click, a
  double-click for a new one) and an EQ tried on a device following the edits
- ui/eq_page_files.py, EqFiles: the files, Find…'s call-backs, a picture pasted, the tracer, Which measurement
- ui/eq_page_result.py, EqResult: running, the result, this session's runs, editing, Save, Report, Use on device
- ui/eq_page_history.py, EqHistory: History and presets
- ui/eq_page_parts.py: the names and small helpers they share
This file keeps the opening, the settings and Qt's own handlers (a picture dropped, Listen's keys 1-9).
"""
import gc
import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from ui import tasks, theme
from ui.eq_page_cards import EqCards
from ui.eq_page_files import EqFiles
from ui.eq_page_graph import EqGraph
from ui.eq_page_handles import EqHandles
from ui.eq_page_history import EqHistory
from ui.eq_page_live import EqLive
from ui.eq_page_parts import FORMAT_NAMES, MODE_HINT, Notices, label
from ui.eq_page_result import EqResult

# (not used here: other files still import them from here, as before the split: listen.py MODE_SHORT, queue_window.py
# and the tests (tests\eq_screen\test_run_and_result.py) file_base_name; TICKS too)
from ui.eq_page_parts import MODE_SHORT, TICKS, file_base_name  # noqa: F401

_FROZEN = set()  # (the moments of the opening gc.freeze() has run at in this process: once each)


def _freeze(moment):
    """What's alive now (the app's code, the window, the EQ part's state, the page's controls) taken out of Python's
    full garbage collections for good: each walked every object (~255,000) and took 50-60 ms of the window's time
    while the curves were worked out. Once per moment in a process: the app makes the page once (the tests make many,
    and what's frozen is never collected)."""
    if moment not in _FROZEN:
        _FROZEN.add(moment)
        gc.freeze()


class _Held:
    """ui.preload held while the page opens (its imports in the background share Python's lock with the window's
    thread: each step of the build took about twice as long), and let go once: when the page is whole, when the
    opening fails, or when the page is deleted half-way."""

    def __init__(self):
        from ui import preload
        preload.hold()
        self.held = True

    def release(self):
        if self.held:
            self.held = False
            from ui import preload
            preload.release()


class EqPage(EqCards, EqGraph, EqHandles, EqFiles, EqResult, EqHistory, EqLive, QWidget):
    def __init__(self, sw, status):
        super().__init__()
        self.sw, self._window_status = sw, status  # (the per-device part, for Use on device; the window's line)
        self.svc = None
        self.S = self.meta = self.curves = self.analysis = self.auto = self.run_result = None
        self.sel = None  # the result shown (its id)
        self.session_runs = []  # this session's runs (and EQs shown from History), newest last: chosen again on the card
        self.history, self.session, self.runs = [], format(int(time.time()), "x"), 0
        self.previews = []  # [(key, name, values)]: curves shown from the search, not in use
        self.preview_bodies = {}  # key: what /api/preview was asked (to work them out again with new settings)
        self.started = False
        self.ready = False  # (built and its files shown: the Guide, Presets and the window wait for it)
        self._seen = self._seeing = self._searched = False  # (first shown; This PC searched)
        self._kept = []  # what it would have said before it was first seen: ("status", text, ms, undo) or ("warning", text)
        self._hold = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.loading = label("Opening the EQ part…", "muted")
        self.loading.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.loading)
        self._save_timer = QTimer(self, singleShot=True, interval=400, timeout=self._save_settings)
        self.save_settings_soon = self._save_timer.start  # (for other windows: Sources)
        self._auto_timer = QTimer(self, singleShot=True, interval=150, timeout=self.refresh_auto)
        self._poll = QTimer(self, interval=400, timeout=self._poll_job)
        self.setAcceptDrops(True)
        # (in a text box, "/" and Ctrl+V type and paste as usual: they take their keys first; nothing until the page
        # is whole: while it's made, Find… or the tracer would open over half a page)
        QShortcut(QKeySequence("/"), self, lambda: self.ready and self.find("measurement"),
                  context=Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.Paste, self, lambda: self.ready and self.paste_picture(),
                  context=Qt.WidgetWithChildrenShortcut)
        theme.on_change(self._recolour)

    # ---------------------------------------------------------------- what it says (once it's been seen)
    def status(self, text, ms=None, undo=None):
        """A message in the window's line at the bottom, for ms milliseconds (None: the line's own time); undo: what Undo
        beside it does (window_parts.MessageLine). Before the page is first seen (made ahead while you're on another
        screen) it's kept, and said when it's first shown."""
        if self._seen:
            self._say(text, ms, undo)
        else:
            self._kept.append(("status", text, ms, undo))

    def _say(self, text, ms, undo):
        # (Undo only when there is one: a window's line that takes none, as some checks' stand-ins, still works)
        if undo is None:
            self._window_status(text, ms)
        else:
            self._window_status(text, ms, undo)

    def _warn(self, text):
        """A file set aside (it couldn't be read: kept as .bad), said in a box over the page; before the page is first
        seen, when it's first shown."""
        if self._seen:
            QMessageBox.warning(self, "AutoEQ Studio", text)
        else:
            self._kept.append(("warning", text))

    def showEvent(self, e):
        super().showEvent(e)
        if not self._seen and not self._seeing:
            self._seeing = True
            QTimer.singleShot(0, self, self._first_seen)  # (once it's drawn: a box then comes over the page)

    def _first_seen(self):
        """Shown for the first time: what it kept until now said (the boxes as one), and This PC searched if the page
        is whole."""
        self._seen = True
        kept, self._kept = self._kept, []
        warnings = [said[1] for said in kept if said[0] == "warning"]
        for said in kept:
            if said[0] == "status":
                self._say(*said[1:])
        if warnings:
            QMessageBox.warning(self, "AutoEQ Studio", "\n\n".join(warnings))
        self._search_this_pc()

    # ---------------------------------------------------------------- opening (once)
    def start(self):
        """The first time the screen is shown (or made ahead by the window): bring AutoEQ Local's files over (once),
        load the EQ part and its state off the window's thread, then make the page in steps (_step)."""
        if self.started:
            return
        self.started = True
        # your files still where an older copy kept them: a move offered before the EQ part takes its folders; then a
        # new copy's (or a new folder's) samples and database lists put in place
        import paths
        from ui import your_files
        try:
            your_files.offer_move(self, self.sw.set)
            paths.first_start()
        except OSError:  # (said in the log; the EQ part opens with what's there)
            import traceback
            traceback.print_exc()
        held = self._hold = _Held()  # (ui.preload paused until the page is whole)
        self.destroyed.connect(lambda: held.release())  # (the page deleted half-way: let go too)

        def load():
            from eq import bring_over
            brought = bring_over.bring_over() if bring_over.needed() else []
            from eq import databases, service
            state, history = service.call("/api/state"), service.call("/api/history")
            # (as AutoEQ Local did at launch: the saved lists, which also say which rig a target was made for; online
            # new ones every few days. Offline nothing is fetched: net.check in databases. Here, while the window
            # shows "Opening the EQ part…", and waited for (up to a second) before the page is made: loading their
            # 55,000 entries holds Python's lock most of its ~0.3 s, and the window's drawing of the page or the graph
            # took ~0.35 s instead of ~0.03 s meanwhile, 2026-10-24. The curves need them too: a target's rig. After
            # the state: by then the window has drawn "Opening the EQ part…")
            if "settings" in state:
                import copy
                databases.start_refresh(copy.deepcopy(state["settings"]))  # (a copy: the page changes its own)
            waited = time.monotonic()
            while databases.status()["loading"] and time.monotonic() - waited < 1.0:  # (online: they may take longer)
                time.sleep(0.01)
            return brought, service, state, history

        def loaded(res, err):
            if err:
                self._not_opened(f"The EQ part couldn't open: {err}\nThe details are in data\\app.log.")
                return
            try:
                brought, self.svc, st, hist = res
                self.history = hist.get("entries", [])
                _freeze("loaded")  # (the EQ part's code and state)
                from eq import service
                self._notices = Notices()
                self._notices.said.connect(self._warn)
                service.SET_ASIDE.append(self._notices.said.emit)
                # (settings.json or history.json damaged, set aside as the state and History were read: said, as one
                # box; History's went unsaid until 2026-10-24, its answer's notice dropped)
                aside = " ".join(t for t in (st.get("set_aside"), hist.get("set_aside")) if t)
                if aside:
                    self._warn(aside)
                if "error" in st:
                    self._not_opened(f"The EQ part couldn't open: {st['error']}")
                    return
                self.meta, self.S = st, st["settings"]
                self._brought = brought
                self._steps = self._build_steps()
            except Exception as e:
                self._not_opened(f"The EQ part couldn't open: {e}\nThe details are in data\\app.log.")
                raise
            self._step()
        tasks.background(load, loaded, owner=self)

    def _step(self):
        """One step of the page's build (ui/eq_page_cards.py: the screen-reader naming filter out of Qt's way
        meanwhile, theme.building), the next one in the next turn of the event loop (the page is its timer's context:
        once the page is deleted, the rest never runs)."""
        try:
            with theme.building(self):
                more = next(self._steps, None) is not None
        except Exception as e:
            self._not_opened(f"The EQ part couldn't open: {e}\nThe details are in data\\app.log.")
            raise
        if more:
            QTimer.singleShot(0, self, self._step)
        else:  # (the page whole and shown, in this same turn: so it's never seen, nor used, before it's ready)
            self._built()

    def _built(self):
        """The page whole and shown: the rest of the opening, then ready."""
        try:
            _freeze("built")  # (the page's controls too)
            if self._brought:
                self.status(f"Brought over {len(self._brought)} files from AutoEQ Local (your settings, History, "
                            "targets, measurements and saved EQs); AutoEQ Local keeps its own.", 12000)
            self.load_curves()
            # (the database lists, asked as the EQ part loaded: once they're in, the rig tags and the curves again)
            self._lists_timer = QTimer(self, interval=500, timeout=self._lists_loaded)
            self._lists_timer.start()
            self.ready = True
        finally:
            self._hold.release()
        # (This PC: once the window has drawn the page, a frame later; searched meanwhile, it made that drawing longer)
        QTimer.singleShot(16 if self.isVisible() else 0, self, self._search_this_pc)

    def _not_opened(self, text):
        """The EQ part couldn't open, or its page couldn't be made: said where the page would be."""
        from PySide6.QtWidgets import QScrollArea
        for w in self.findChildren(QScrollArea, options=Qt.FindDirectChildrenOnly):
            w.hide()
        self.loading.setText(text)
        self.loading.show()
        self._hold.release()

    def _search_this_pc(self):
        """This PC searched for frequency responses (eq.library) once the page is whole and you've seen it: not while
        it's made (the search shares Python's lock with the window's thread: each step took longer), nor while it's
        made ahead unseen. Find… asks for a search again as it opens."""
        if self._searched or not (self.ready and self._seen):
            return
        self._searched = True
        from eq import library
        library.start_scan(self.S)

    def _lists_loaded(self):
        """Once the database lists are in: the rig tags and the curves again (a target's rig may only be known from
        them, and with it the rig conversion)."""
        from eq import databases
        if databases.status()["loading"]:
            return
        self._lists_timer.stop()
        st = self.svc.call("/api/state")
        if "inputs" in st:
            self.show_inputs(st["inputs"])
        self.load_curves()

    # ---------------------------------------------------------------- settings
    def _save_settings(self):
        def done(res, err):
            if err or (res or {}).get("error"):
                self.status(f"Couldn't save the settings: {err or res['error']}", 8000)
        s = self.S
        tasks.background(lambda: self.svc.call("/api/settings", {"settings": s}), done, owner=self)

    def changed(self, curves=False):
        """A setting changed: save it soon, show it, ask the automatic settings again (and reload the curves)."""
        self._save_timer.start()
        self.show_settings()
        if curves:
            self.load_curves()
        else:
            self._auto_timer.start()
        if self.current()[1]:
            self.live_update()  # (e.g. the pre-amp's rounding and headroom: the result's numbers follow at once)
        elif self.curves and not curves:
            self.draw()  # (e.g. your own filters, drawn as “With your filters”)

    def show_settings(self):
        S = self.S
        i = self.app_combo.findData(S.get("eq_app") or "")
        self.app_combo.setCurrentIndex(max(0, i))
        self.app_note.setText(self.app_note_text(S.get("eq_app") or ""))
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(S["mode"])))
        self.mode_hint.setText(MODE_HINT.get(S["mode"], ""))
        on = [FORMAT_NAMES[k] for k in list(FORMAT_NAMES) if S["export"].get(k)]
        if hasattr(self, "formats_line"):
            self.formats_line.setText("Save filters writes: " + ", ".join(on) + "." if on else
                                      "Save filters writes nothing yet: choose your EQ app, or tick a file in "
                                      "Advanced › Saved files.")
        if hasattr(self, "settings"):
            self.settings.refresh()

    def app_note_text(self, key):
        """The line under Your EQ app for an app (its limits, how to load its file, its source), as rich text."""
        a = self.eq_app(key) if key not in ("", "other") else None
        if a:
            import html
            own = self.S["best_fit"].get("layout") == a.get("layout") or a.get("kind") == "site" \
                or key != (self.S.get("eq_app") or "")  # (another app, as the Guide shows it: its own limits)
            text = html.escape(f"{a.get('note') or a.get('summary')}"
                               + (" Its band shapes aren't stated, so the app's result can differ a little." if a.get("approx") else "")
                               + f" {a.get('how', '')}"
                               + ("" if own else " (You've changed Best fit's layout since, so its limits aren't the app's "
                                  "any more.)")).strip()
            return text + (f' <a href="{html.escape(a["source"])}">Source</a>' if a.get("source") else "")
        return ("Any filters, as many as needed, saved as an Equalizer APO file, which many apps can read."
                if key == "other" else
                "Which app or device will play the EQ? Its limits (bands, gain, Q) are kept, and Save writes its file.")

    def open_link(self, url):
        """A website link (online only: offline the app never connects, net.py)."""
        import net
        if net.offline():
            self.status("Offline: switch to Online (top right) to open websites.", 6000)
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))

    def eq_app(self, key=None):
        key = self.S.get("eq_app") if key is None else key
        return next((a for a in self.meta.get("eq_apps", []) if a["key"] == key), None)

    def choose_app(self, key):
        """Your EQ app: its limits and its file (AutoEQ Local's settings.js applyEqApp): the method that makes its
        EQ, its layout, a graphic EQ's slider range and steps, and Save writing exactly its file."""
        S, a = self.S, self.eq_app(key)
        S["eq_app"] = key
        S["mode"] = "site_sweep" if a and a["kind"] == "site" else "best_fit"
        S["best_fit"]["layout"] = a["layout"] if a else "any"
        if a and a["kind"] == "graphic":
            self.apply_bands(a)
        file = a["file"] if a else "apo"
        from eq import exports
        for f in exports.FORMATS:
            S["export"][f] = f == file
        self.changed()

    def apply_bands(self, a):
        """A graphic EQ app's sliders: its range and steps, or the defaults when it states none (settings.js)."""
        S, lim = self.S, self.meta.get("limits", {})
        d = self.meta["defaults"]["best_fit"]["bands"]
        g = a.get("bands_gain") or [d["gain_min"], d["gain_max"]]
        S["best_fit"]["bands"]["gain_min"] = max(g[0], lim.get("best_fit.bands.gain_min", {}).get("min", -1e9))
        S["best_fit"]["bands"]["gain_max"] = min(g[1], lim.get("best_fit.bands.gain_max", {}).get("max", 1e9))
        S["best_fit"]["bands"]["step"] = a.get("bands_step") or d["step"]

    def set_mode(self, mode):
        self.S["mode"] = mode
        self.changed()

    # ---------------------------------------------------------------- a picture dropped on the page (Qt's own handlers)
    def dragEnterEvent(self, e):
        if not self.ready:  # (still being made: nothing to drop it on yet)
            return
        from ui.trace_window import IMAGE_SUFFIXES
        md = e.mimeData()
        if md.hasImage() or any(u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_SUFFIXES
                                for u in md.urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        if self.ready and self._picture_in(e.mimeData()):
            e.acceptProposedAction()

    # ---------------------------------------------------------------- Listen (ui/listen.py)
    def keyPressEvent(self, e):
        """1-9: Listen's versions (not while typing in a box)."""
        from PySide6.QtWidgets import QLineEdit, QPlainTextEdit
        if hasattr(self, "listen") and Qt.Key_1 <= e.key() <= Qt.Key_9 and not e.modifiers() \
                and not isinstance(self.focusWidget(), (QLineEdit, QPlainTextEdit)):
            self.listen.choose_number(e.key() - Qt.Key_1)
            return
        super().keyPressEvent(e)

    def stop_sound(self):
        if hasattr(self, "listen") and self.listen.playing:
            self.listen.stop()
