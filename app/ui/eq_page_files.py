"""Make an EQ's files (a part of EqPage, ui/eq_page.py): Target and Measurement filled from the app's files and
chosen, Add… (files from this PC), Find… (ui/picker.py) and what it calls back (a file used or moved: said with
Undo), a target saved as adjusted, a picture pasted or dropped (into the tracer, ui/trace_window.py) and Which
measurement (ui/compare_window.py); an entry that the app cannot download traced from a picture of its website
(trace_from_website: the browser, the wait for a picture, ui/picture_wait.py, then the tracer).
EqFiles is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts. (Qt's own
handlers for a dropped picture stay in EqPage: they hand it to _picture_to_tracer here.)
"""
import json
import os

from PySide6.QtWidgets import QFileDialog, QMessageBox

import textfile
from ui import tasks
from ui.eq_page_parts import modal, set_note


class EqFiles:
    """Make an EQ's files."""

    # ---------------------------------------------------------------- the files
    def show_inputs(self, inputs):
        self.inputs = inputs
        t = self.target_combo
        t.clear()
        from ui.search_combo import natural_key
        for n in sorted(inputs["targets"], key=lambda n: natural_key(os.path.splitext(n)[0])):  # (A to Z)
            t.addItem(os.path.splitext(n)[0], n)
        t.setCurrentIndex(max(0, t.findData(inputs["active_target"])))
        set_note(self.target_note, "" if inputs["targets"] else "No targets: click Add… to add a target from this PC.")
        from eq import inputs as eq_inputs
        groups = {}
        for m in sorted(inputs["measurements"], key=lambda m: natural_key(m["name"])):
            groups.setdefault(eq_inputs.device_name([m["name"]]), []).append(m)
        self.groups = groups = dict(sorted(groups.items(), key=lambda kv: natural_key(kv[0])))  # (A to Z)
        mc = self.measurement_combo
        mc.clear()
        current = None
        for dev, files in groups.items():
            mc.addItem(f"{dev}  ({len(files)} file{'s' if len(files) > 1 else ''})", dev)
            if any(f["included"] for f in files):
                current = current or dev
        mc.setCurrentIndex(max(0, mc.findData(current)))
        if not groups:
            set_note(self.measurement_note, "No measurements: click Add… to add a measurement from this PC (L and R, or more "
                 "than one seating).")
        else:
            on = [f["name"] for f in groups.get(current, []) if f["included"]]
            rigs = {inputs.get("rigs", {}).get(n) for n in on} - {None, ""}
            set_note(self.measurement_note, f"{len(on)} file{'s' if len(on) != 1 else ''} used"
                 + (f" · measured on {', '.join(sorted(rigs))}" if rigs else ""))

    def _file_chosen(self, kind):
        S = self.S
        if kind == "target":
            S["files"]["active_target"] = self.target_combo.currentData()
        else:
            dev = self.measurement_combo.currentData()
            mine = {f["name"] for f in self.groups.get(dev, [])}
            S["files"]["excluded"] = [m["name"] for m in self.inputs["measurements"] if m["name"] not in mine]
        self._save_files()

    def _save_files(self, after=None, say=None):
        """The files in use saved, then shown again. say: where a window of its own (Find…) says a file couldn't be
        used (the page's line by itself: UI-RULES 7)."""
        def done(res, err):
            if err or (res or {}).get("error"):
                (say or self.status)(f"The app cannot use that file: {err or res['error']}")
                return
            if res.get("inputs"):
                self.show_inputs(res["inputs"])
            self.load_curves()
            if after:
                after()
        s = self.S
        tasks.background(lambda: self.svc.call("/api/settings", {"settings": s}), done, owner=self)

    def add_files(self, kind):
        start = os.path.expanduser("~")
        files, _ = QFileDialog.getOpenFileNames(self, "Add target files" if kind == "target" else "Add measurement files",
                                                start, "Frequency response (*.txt *.csv *.frd *.tsv);;All files (*)")
        if not files:
            return
        said, read = [], []
        for f in files:
            try:
                read.append({"name": os.path.basename(f), "content": textfile.read(f)})
            except OSError as e:
                said.append(f"{os.path.basename(f)}: {e}")
        # (a measurement's files as one set: one number for all when names are taken, so they stay one device;
        # targets each on their own)
        for batch in ([read] if kind == "measurement" else [[x] for x in read]) if read else []:
            r = self.svc.call("/api/files/add", {"kind": kind, "files": batch, "settings": self.S})
            if r.get("error"):
                said.append(f"{', '.join(x['name'] for x in batch)}: {r['error']}")
            elif r.get("settings"):
                self.S = r["settings"]
        if said:
            QMessageBox.warning(self, "Add", "\n\n".join(said))  # (a question's title names its command: UI-RULES 17)
        st = self.svc.call("/api/state")
        if "inputs" in st:
            self.S = st["settings"]
            self.show_inputs(st["inputs"])
            self.show_settings()
            self.load_curves()

    # ---------------------------------------------------------------- a picture pasted or dropped: into the tracer
    def paste_picture(self):
        """Ctrl+V with a picture (or a picture file) on the clipboard: the tracer opens with it (as AutoEQ Local's
        paste anywhere)."""
        from PySide6.QtWidgets import QApplication
        md = QApplication.clipboard().mimeData()
        self._picture_to_tracer(md)

    def _picture_to_tracer(self, md):
        """A picture in dragged or pasted data: into the tracer. Returns whether there was one."""
        if self.svc is None or md is None:
            return False
        from ui.trace_window import IMAGE_SUFFIXES
        # (a better picture after a poor automatic read of a picture from a website keeps its entry, as the same
        # paste in the tracer: TraceWindow.kept_entry)
        for u in md.urls() if md.hasUrls() else []:
            if u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_SUFFIXES:
                self.open_trace()
                self.tracer.open_file(u.toLocalFile(), self.tracer.kept_entry())
                return True
        if md.hasImage():
            from PySide6.QtGui import QImage
            self.open_trace()
            self.tracer.load_image(QImage(md.imageData()), entry=self.tracer.kept_entry())
            return True
        return False

    def open_trace(self):
        """The tracer (one window, kept while the screen is open: what's traced stays when it's closed), in front. A
        minimized tracer comes back as it was (maximized or not): it stayed minimized when a new picture came,
        2026-11-11. (Trace a graph image…, a picture pasted or dropped on the page and a picture from a website all
        come here.)"""
        from PySide6.QtCore import Qt
        from ui.trace_window import TraceWindow
        if getattr(self, "tracer", None) is None:
            self.tracer = TraceWindow(self)
        tw = self.tracer
        tw.fill_comp()
        tw.show()
        tw.setWindowState(tw.windowState() & ~Qt.WindowMinimized)
        tw.raise_()
        tw.activateWindow()

    # ---------------------------------------------------------------- a picture from a website (ui/picture_wait.py)
    def trace_from_website(self, entry_id, over, say, want=None):
        """Find…'s Use (or Which measurement's link) on an entry that the app cannot download: the entry opens in the
        user's browser, then the wait window on top of `over` waits for a picture of its graph, which goes to the
        tracer. Returns whether the wait started. `say`: the message line of `over` (UI-RULES 7)."""
        wait = getattr(self, "picture_wait", None)
        if wait is not None and tasks.alive(wait) and wait.isVisible():  # (one wait at a time)
            wait.raise_()
            wait.activateWindow()
            return False
        from ui import bubble
        r = self.svc.call("/api/db/entry", {"id": entry_id})  # (the lists in memory: no internet)
        if r.get("error"):  # ("do this first": update the lists. A bubble, its words whole: Find…'s line cut them)
            bubble.tell(None, r["error"], near=over)
            return False
        from ui.picture_wait import PictureWait, clean_entry
        entry = clean_entry(r["entry"])  # (its words come from a website's list: each on one line)
        if want:  # ("target" or "measurement": Find… for the other kind; the tracer's note names that add)
            entry["as"] = want
        import net
        if net.offline():  # (the words fit Find…'s line at its opening width)
            say("Offline: to open this entry, change to Online (top right).")
            return False
        tw = getattr(self, "tracer", None)
        n = tw.unadded_curves() if tw is not None else 0
        if n or (tw is not None and tw.changed_picture()):
            # (the new picture replaces the one in the tracer, and the user is then in the browser: "do this first",
            # a bubble at the control that was used, UI-RULES 25. The automatic read's own curves do not stop it.
            # With no curve, the user's work is on 1 Axes or 3 Save: words that are true for each change.)
            bubble.tell(None, (
                "The tracer has a curve that you did not add. To keep it, add it in the tracer. To remove it, click "
                "Remove image in the tracer. Then select the entry again." if n == 1 else
                "The tracer has curves that you did not add. To keep them, add them in the tracer. To remove them, "
                "click Remove image in the tracer. Then select the entry again." if n else
                "The tracer has a picture with your changes. To remove it, click Remove image in the tracer. Then "
                "select the entry again."), near=over)
            return False
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        if not QDesktopServices.openUrl(QUrl(entry.get("link") or "")):
            say("Windows cannot open the website of this entry.")
            return False
        wait = self.picture_wait = PictureWait(over, entry)
        wait.finished.connect(lambda _code: self._wait_done(wait, entry, over, say))
        wait.open()  # (window modal on `over`; it does not block)
        return True

    def _wait_done(self, wait, entry, over, say):
        """The wait window closed: with a picture, `over` closes (the tracer cannot get input under a modal window)
        and the tracer opens with it once `over`'s own loop has ended; after the time limit, `over` says so."""
        if getattr(self, "picture_wait", None) is wait:
            self.picture_wait = None
        got, timed_out = wait.got, wait.timed_out
        wait.deleteLater()
        if got is None:
            if timed_out:
                say("No new picture came in 10 minutes. Select the entry again.", 60000)  # (whole in Find…'s line)
            return
        over.reject()
        img, jpeg = got
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._picture_from_website(entry, img, jpeg))

    def _picture_from_website(self, entry, img, jpeg):
        self.open_trace()
        self.tracer.load_image(img, jpeg=jpeg, entry=entry)
        self._tracer_to_front(entry)

    def _tracer_to_front(self, entry):
        """The tracer in front. Windows does not give the keyboard to a program that is not active (the browser is):
        then the taskbar button flashes and a tray message (the main window's) says where the picture is."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        tw = self.tracer
        if QApplication.applicationState() == Qt.ApplicationActive:
            return
        QApplication.alert(tw)
        app = getattr(self.window(), "app", None)
        if app is not None and hasattr(app, "tray_message"):
            from ui.picture_wait import short_words  # (a name of 600 words: NAME_MAX characters, then "…")
            app.tray_message("AutoEQ Studio has the picture", f"The tracer shows the graph of "
                             f"“{short_words(entry['name'])}”. Go to the window of the tracer.")

    # ---------------------------------------------------------------- finding files (ui/picker.py)
    def find(self, kind):
        from ui.picker import Picker
        modal(Picker(self, kind))

    def save_files(self, after=None, say=None):
        self._save_files(after, say)

    def save_adjusted_target(self):
        """Target › Adjust › Save as a target…: the target as adjusted becomes a target of your own, in
        use, the adjustments back to 0 (eq.service /api/target/save); Undo puts it all back."""
        from ui.window_parts import ask_text  # (looked up here: the tests answer it)
        base = os.path.splitext(self.S["files"].get("active_target") or "Target")[0]
        name, ok = ask_text(self, "Save as a target", "Name of your target", f"{base} (adjusted)", "Save")
        if not ok or not name.strip():
            return
        res = self.svc.call("/api/target/save", {"settings": self.S, "name": name.strip()})
        if res.get("error"):
            QMessageBox.warning(self, "Save as a target", res["error"])
            return
        before = res["before"]
        self.S = res["settings"]
        self.show_inputs(res["inputs"])
        self.show_settings()
        self.load_curves()

        def undo():
            self.S["files"]["active_target"] = before["files"]["active_target"]
            self.S["target_adjust"] = before["target_adjust"]
            r = self.svc.call("/api/files/remove", {"kind": "target", "names": [res["name"]], "settings": self.S})
            if r.get("inputs"):
                self.show_inputs(r["inputs"])
            self.show_settings()
            self._save_files()
        self.notify(f"The app saved “{os.path.splitext(res['name'])[0]}” as a target and uses it. The target has the "
                    "adjustments in it. Thus, the adjustments are 0 again.", undo)

    # ---------------------------------------------------------------- what Find… calls back (ui/picker.py)
    def use_target(self, name):
        self.S["files"]["active_target"] = name
        self._save_files()

    def use_device(self, device):
        """A measurement in the app (a set of files) in use: its files ticked, the others not."""
        mine = {f["name"] for f in self.groups.get(device, [])}
        self.S["files"]["excluded"] = [m["name"] for m in self.inputs["measurements"] if m["name"] not in mine]
        self._save_files()

    def file_used(self, res):
        """A file from this PC or the online databases (or an average) is in the app and in use (eq.service /api/use's
        answer), said with Undo."""
        if res.get("settings"):
            self.S = res["settings"]
        if res.get("inputs"):
            self.show_inputs(res["inputs"])
        self.show_settings()
        self.load_curves()
        n = len(res.get("names") or [])
        self.notify(f"“{res.get('name')}” is the target." if res.get("kind") == "target" else
                    f"The measurement is “{res.get('name')}”" + (f" ({n} file{'s' if n != 1 else ''})." if n else "."),
                    self._undo_use(res) if res.get("before") and res.get("settings") else None)

    def _undo_use(self, res):
        """Undo of a Use or an average (files.js undoUse): the files it made go, and what it chose goes back while
        it's as it left it (a file chosen since stays)."""
        back = "active_target" if res.get("kind") == "target" else "excluded"
        made = json.dumps(res["settings"]["files"][back])
        before = json.loads(json.dumps(res["before"][back]))  # (as it was, whatever changes the settings later)

        def undo():
            if json.dumps(self.S["files"][back]) == made:  # (the choice back first: never none ticked meanwhile)
                self.S["files"][back] = before
            if res.get("created"):
                r = self.svc.call("/api/files/remove", {"kind": res["kind"], "names": res["created"], "settings": self.S})
                if r.get("error"):
                    QMessageBox.warning(self, "Undo", r["error"])
            self._save_files()
        return undo

    def file_moved(self, kind, name, before, say=None):
        """A file moved between Target and Measurement (Find…), said with Undo (it goes back, the choice too); in Find…'s
        own line when it passes `say` (said in the main window's, it was behind Find…: UI-RULES 7)."""
        def undo():
            r = self.svc.call("/api/files/move", {"kind": "measurement" if kind == "target" else "target", "name": name,
                                                  "settings": self.S})
            if r.get("error"):
                QMessageBox.warning(self, "Undo", r["error"])
                return
            self.S["files"] = before
            self._save_files()
        (say or self.notify)(f"The app moved “{name}” to {'Measurement' if kind == 'target' else 'Target'}.", undo)

    def reload_state(self):
        st = self.svc.call("/api/state")
        if "inputs" in st:
            self.S = st["settings"]
            self.show_inputs(st["inputs"])
            self.show_settings()
            self.load_curves()

    # ---------------------------------------------------------------- Which measurement (ui/compare_window.py)
    def open_other_measurements(self):
        """Which measurement to use? (ui/compare_window.py)"""
        from ui.compare_window import CompareWindow
        modal(CompareWindow(self))
