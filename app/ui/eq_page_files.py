"""Make an EQ's files (a part of EqPage, ui/eq_page.py): Target and Measurement filled from the app's files and
chosen, Add… (files from this PC), Find… (ui/picker.py) and what it calls back (a file used or moved: said with
Undo), a target saved as adjusted, a picture pasted or dropped (into the tracer, ui/trace_window.py) and Which
measurement (ui/compare_window.py).
EqFiles is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts. (Qt's own
handlers for a dropped picture stay in EqPage: they hand it to _picture_in here.)
"""
import json
import os

from PySide6.QtWidgets import QFileDialog, QMessageBox

import textfile
from ui import tasks
from ui.eq_page_parts import modal, note


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
        note(self.target_note, "" if inputs["targets"] else "No targets yet: Add… one from this PC.")
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
            note(self.measurement_note, "No measurements yet: Add… one from this PC (L and R, or several seatings).")
        else:
            on = [f["name"] for f in groups.get(current, []) if f["included"]]
            rigs = {inputs.get("rigs", {}).get(n) for n in on} - {None, ""}
            note(self.measurement_note, f"{len(on)} file{'s' if len(on) != 1 else ''} used"
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

    def _save_files(self, after=None):
        def done(res, err):
            if err or (res or {}).get("error"):
                self.status(f"Couldn't use that file: {err or res['error']}", 8000)
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
        self._picture_in(md)

    def _picture_in(self, md):
        """A picture in dragged or pasted data: into the tracer. Returns whether there was one."""
        if self.svc is None or md is None:
            return False
        from ui.trace_window import IMAGE_SUFFIXES
        for u in md.urls() if md.hasUrls() else []:
            if u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_SUFFIXES:
                self.open_trace()
                self.tracer.open_file(u.toLocalFile())
                return True
        if md.hasImage():
            from PySide6.QtGui import QImage
            self.open_trace()
            self.tracer.load_image(QImage(md.imageData()))
            return True
        return False

    def open_trace(self):
        """The tracer (one window, kept while the screen is open: what's traced stays when it's closed)."""
        from ui.trace_window import TraceWindow
        if getattr(self, "tracer", None) is None:
            self.tracer = TraceWindow(self)
        self.tracer.fill_comp()
        self.tracer.show()
        self.tracer.raise_()
        self.tracer.activateWindow()

    # ---------------------------------------------------------------- finding files (ui/picker.py)
    def find(self, kind):
        from ui.picker import Picker
        modal(Picker(self, kind))

    def save_files(self, after=None):
        self._save_files(after)

    def save_adjusted_target(self):
        """Target › Adjust › Save as a target…: the target as adjusted becomes a target of your own, in
        use, the adjustments back to 0 (eq.service /api/target/save); Undo puts it all back."""
        from PySide6.QtWidgets import QInputDialog
        base = os.path.splitext(self.S["files"].get("active_target") or "Target")[0]
        name, ok = QInputDialog.getText(self, "Save as a target", "Name of your target", text=f"{base} (mine)")
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
        self.notify(f"Saved “{os.path.splitext(res['name'])[0]}” as a target, now in use (the adjustments are in it, "
                    "so they're back to 0).", undo)

    # ---------------------------------------------------------------- what Find… calls back (ui/picker.py)
    def use_target(self, name):
        self.S["files"]["active_target"] = name
        self._save_files()

    def use_device(self, device):
        """A measurement in the app (a set of files) in use: its files ticked, the others not."""
        mine = {f["name"] for f in self.groups.get(device, [])}
        self.S["files"]["excluded"] = [m["name"] for m in self.inputs["measurements"] if m["name"] not in mine]
        self._save_files()

    def used(self, res):
        """A file from this PC or the online databases (or an average) is in the app and in use (eq.service /api/use's
        answer), said with Undo."""
        if res.get("settings"):
            self.S = res["settings"]
        if res.get("inputs"):
            self.show_inputs(res["inputs"])
        self.show_settings()
        self.load_curves()
        n = len(res.get("names") or [])
        self.notify(f"“{res.get('name')}” is now the target." if res.get("kind") == "target" else
                    f"Now measuring “{res.get('name')}”" + (f" ({n} file{'s' if n != 1 else ''})." if n else "."),
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

    def moved(self, kind, name, before):
        """A file moved between Target and Measurement (Find…), said with Undo (it goes back, the choice too)."""
        def undo():
            r = self.svc.call("/api/files/move", {"kind": "measurement" if kind == "target" else "target", "name": name,
                                                  "settings": self.S})
            if r.get("error"):
                QMessageBox.warning(self, "Undo", r["error"])
                return
            self.S["files"] = before
            self._save_files()
        self.notify(f"Moved “{name}” to {'Measurement' if kind == 'target' else 'Target'}.", undo)

    def reload_state(self):
        st = self.svc.call("/api/state")
        if "inputs" in st:
            self.S = st["settings"]
            self.show_inputs(st["inputs"])
            self.show_settings()
            self.load_curves()

    # ---------------------------------------------------------------- Which measurement (ui/compare_window.py)
    def compare(self):
        """Which measurement to use? (ui/compare_window.py)"""
        from ui.compare_window import CompareWindow
        modal(CompareWindow(self))
