"""The "Make an EQ" screen: AutoEQ Local's page, natively. One column, as there:
- the graph: your measurement, the target and the measurement with the EQ; under it the EQ itself (0 dB = no change)
- Target | Measurement: what's in the app (your Targets and Measurements folders), and Add… for files on this PC
- Make the EQ: your EQ app (its limits are kept, its file is what Save writes), the method, the search (what a run
  tries and how long it takes), Run, and the run's progress
- the result: its numbers, its filters (Fewer or more filters: the best result for each count), Save filters (the
  files your EQ app needs, under the File name), and Use on device: the EQ becomes a device's profile, switched on
- by the graph's title: Trace image (ui/trace_window.py: a picture of a graph becomes a measurement or target) and
  History; under the result, Listen (ui/listen.py)

Everything it does goes through eq.service (AutoEQ Local's page's requests, called directly); slow ones run off the
window's thread (ui.tasks). The EQ part is imported only when this screen is first opened (the tray stays light),
after AutoEQ Local's files are brought over (eq.bring_over: once, on the first opening).
Its Guide: ui\\guide.py (the top bar's Guide); F1 on a control: its entry in Help.

The page is one object, EqPage, made of parts, one file each: plain classes (no __init__, no signals) that share the
page's controls and data, joined here with QWidget last:
- ui/eq_page_cards.py, EqCards: the cards (how the page is laid out: the file to restyle it in)
- ui/eq_page_graph.py, EqGraph: the curves, the analysis and automatic settings, the graph, the curves shown from
  Find…, Listen's marker
- ui/eq_page_files.py, EqFiles: the files, Find…'s call-backs, a picture pasted, the tracer, Which measurement
- ui/eq_page_result.py, EqResult: running, the result, this session's runs, editing, Save, Report, Use on device
- ui/eq_page_history.py, EqHistory: History and presets
- ui/eq_page_parts.py: the names and small helpers they share
This file keeps the opening, the settings and Qt's own handlers (a picture dropped, Listen's keys 1-9).
"""
import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from ui import tasks, theme
from ui.eq_page_cards import EqCards
from ui.eq_page_files import EqFiles
from ui.eq_page_graph import EqGraph
from ui.eq_page_history import EqHistory
from ui.eq_page_parts import FORMAT_NAMES, MODE_HINT, Notices, label
from ui.eq_page_result import EqResult

# (not used here: other files still import them from here, as before the split: listen.py MODE_SHORT, queue_window.py
# and the tests (tests\eq_screen\test_run_and_result.py) file_base_name; TICKS too)
from ui.eq_page_parts import MODE_SHORT, TICKS, file_base_name  # noqa: F401


class EqPage(EqCards, EqGraph, EqFiles, EqResult, EqHistory, QWidget):
    def __init__(self, sw, status):
        super().__init__()
        self.sw, self.status = sw, status  # (the per-device part, for Use on device; status(text): the window's line)
        self.svc = None
        self.S = self.meta = self.curves = self.analysis = self.auto = self.run_result = None
        self.sel = None  # the result shown (its id)
        self.session_runs = []  # this session's runs (and EQs shown from History), newest last: chosen again on the card
        self.history, self.session, self.runs = [], format(int(time.time()), "x"), 0
        self.previews = []  # [(key, name, values)]: curves shown from the search, not in use
        self.preview_bodies = {}  # key: what /api/preview was asked (to work them out again with new settings)
        self.started = False
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
        # (in a text box, "/" and Ctrl+V type and paste as usual: they take their keys first)
        QShortcut(QKeySequence("/"), self, lambda: self.svc and self.find("measurement"),
                  context=Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.Paste, self, self.paste_picture, context=Qt.WidgetWithChildrenShortcut)
        theme.on_change(self._recolour)

    # ---------------------------------------------------------------- opening (once)
    def start(self):
        """The first time the screen is shown: bring AutoEQ Local's files over (once), load the EQ part, its state."""
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

        def load():
            from eq import bring_over
            brought = bring_over.bring_over() if bring_over.needed() else []
            from eq import databases, library, settings as eq_settings
            cfg = eq_settings.load()
            # (as AutoEQ Local did at launch: the saved lists, which also say which rig a target was made for; online
            # new ones every few days. Offline nothing is fetched: net.check in databases)
            library.start_scan(cfg)
            databases.start_refresh(cfg)
            from eq import service
            return brought, service, service.call("/api/state"), service.call("/api/history").get("entries", [])

        def loaded(res, err):
            if err:
                self.loading.setText(f"The EQ part couldn't open: {err}\nThe details are in data\\app.log.")
                return
            brought, self.svc, st, self.history = res
            from eq import service
            self._notices = Notices()
            self._notices.said.connect(lambda t: QMessageBox.warning(self, "AutoEQ Studio", t))
            service.SET_ASIDE.append(self._notices.said.emit)
            if st.get("set_aside"):
                self._notices.said.emit(st["set_aside"])
            if "error" in st:
                self.loading.setText(f"The EQ part couldn't open: {st['error']}")
                return
            self.meta, self.S = st, st["settings"]
            self._build()
            if brought:
                self.status(f"Brought over {len(brought)} files from AutoEQ Local (your settings, History, targets, "
                            "measurements and saved EQs); AutoEQ Local keeps its own.", 12000)
            self.show_inputs(st["inputs"])
            self.load_curves()
            self._lists_timer = QTimer(self, interval=500, timeout=self._lists_loaded)
            self._lists_timer.start()
        tasks.background(load, loaded)

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
        tasks.background(lambda: self.svc.call("/api/settings", {"settings": s}), done)

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
            own = self.S["best_fit"].get("layout") == a.get("layout") or a.get("kind") == "site"                 or key != (self.S.get("eq_app") or "")  # (another app, as the Guide shows it: its own limits)
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
        from ui.trace_window import IMAGE_SUFFIXES
        md = e.mimeData()
        if md.hasImage() or any(u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_SUFFIXES
                                for u in md.urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        if self._picture_in(e.mimeData()):
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
