"""Make an EQ's History and presets (a part of EqPage, ui/eq_page.py): what a result is in a line, an EQ kept in
History (after a run, saved or copied), "You've EQ'd this before", History's window (ui/history_window.py) and an EQ
from it shown again, Copy (the filters as Equalizer APO text), and the top bar's Presets menu (a preset loaded, saved
or deleted; Reset all settings…).
EqHistory is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts.
"""
import hashlib
import json

from PySide6.QtWidgets import QMessageBox

from ui.eq_page_parts import modal


class EqHistory:
    """Make an EQ's History and presets."""

    # ---------------------------------------------------------------- History (history.js)
    def run_label(self, run, r):
        """What a result is, in a line (results.js runLabel)."""
        lay = next((l for l in self.meta.get("layouts", []) if l["key"] == r.get("layout")), None)
        if run.get("mode") == "manual":  # (an EQ made by hand: where it began, and its filters)
            n = r.get("n_filters", len(r.get("filters") or []))
            return f"By hand · {run.get('source') or 'your own filters'} · {n} filter{'' if n == 1 else 's'}"
        if r.get("engine") == "graphic":
            return (f"{lay['name'] if lay else 'Fixed bands'}: {r['n_filters']} bands, {r.get('gain_min')} to "
                    f"+{r.get('gain_max')} dB in {r.get('step')} dB steps")
        if run["mode"] == "best_fit":
            yours, added = r.get("yours") or 0, max(0, r["n_filters"] - (r.get("yours") or 0))
            mine = ""
            if yours:
                mine = (f"your {yours} + {added} added" if r.get("rows") else f"your {yours} alone" if r.get("keep")
                        else f"your {yours}, fine-tuned") + ("" if r.get("keep") or not r.get("rows") else " (adjusted)") + " · "
            return (mine + (f"{lay['name']} · " if lay and lay["key"] != "any" else "")
                    + f"{r['n_filters']} filters, Q ≤ {r.get('q_max')}, boost ≤ +{r.get('gain_max')}")
        return (f"{r.get('rows')} rows · {r.get('freq_low')}–{r.get('freq_high')} · {r.get('gain_min')} to "
                f"{r.get('gain_max')} · Q {r.get('q_min')}–{r.get('q_max')}")

    @staticmethod
    def _print(filters):
        """A short fingerprint of filters: the same result saved as it is and edited are two entries (in another
        order, e.g. sorted, one)."""
        rows = sorted(json.dumps([f.get("type", "PK"), float(f["freq"]), float(f["gain"]), float(f["q"]),
                                  f.get("enabled", True) is not False]) for f in filters)
        return hashlib.sha1(json.dumps(rows).encode()).hexdigest()[:8]

    def entry_now(self, saved):
        run, r = self.current()
        st, c = self.stats(), self.curves or {}
        filters = [dict(f) for f in self.EDIT if f["freq"] and f["q"]]
        base = run.get("history") or f"{self.session}-{run.get('n', 1)}-{r['id']}"
        result = {k: v for k, v in r.items() if k not in ("filters", "start")}  # (by hand: shown again as saved)
        S = self.S
        return {"key": f"{base}-{self._print(filters)}", "base": base, "saved": saved,
                "device": run.get("device") or c.get("name"), "target": run.get("target_name") or c.get("target_name"),
                "target_file": run.get("target_file") or self.inputs.get("active_target"),
                "meas_files": run.get("meas_files") or [m["name"] for m in self.inputs["measurements"] if m["included"]],
                "adjust": S["target_adjust"], "mode": run["mode"],
                "label": self.run_label(run, r) + (" (edited)" if self.edited() else ""), "result": result,
                "filters": filters, "rms": st["rms"], "preamp": st["preamp_raw"], "n_filters": st["n"],
                "site": S["site"], "rig_convert": S["rig_convert"]["enabled"], "band": S["scoring"]["band_hz"]}

    def record(self, saved):
        """Into History: after a run (saved False: only when Advanced › History keeps every run), or saved/copied."""
        run, r = self.current()
        if not r or not self.curves or (not saved and (self.S["history"]["keep"] != "all" or run.get("history"))):
            return
        res = self.svc.call("/api/history/add", {"entry": self.entry_now(saved)})
        if res.get("error"):
            self.status(f"Couldn't add this EQ to the history: {res['error']}", 8000)
            return
        by_key = {e["key"]: e for e in self.history}
        by_key[res["entry"]["key"]] = res["entry"]
        self.history = [by_key[k] for k in res.get("keys", []) if k in by_key]
        self.history_note()

    def history_note(self):
        """Under Measurement: when you've EQ'd it before (Advanced › History can turn it off)."""
        mine = [e for e in self.history if self.curves and e.get("device") == self.curves["name"]]
        on = bool(self.S["history"].get("eqd_before")) and bool(mine)
        self.eqd_before.setVisible(on)
        self.eqd_show.setVisible(on)
        if on:
            from ui.history_window import day_of
            last = max(mine, key=lambda e: e["when"])
            self.eqd_before.setText(f"You've EQ'd this {'once' if len(mine) == 1 else f'{len(mine)} times'} before · "
                                    f"last {day_of(last['when']).lower()}")

    def open_history(self, this_iem):
        from ui.history_window import HistoryWindow
        r = self.svc.call("/api/history")
        if "entries" in r:
            self.history = r["entries"]
        modal(HistoryWindow(self, this_iem))

    def copy_filters(self, filters, preamp_raw, record=True):
        """The filters as Equalizer APO text on the clipboard (kept in History when they're the result's)."""
        from PySide6.QtGui import QGuiApplication
        on = [f for f in filters if f.get("enabled", True) is not False]
        res = self.svc.call("/api/text", {"settings": self.S, "filters": on, "preamp": preamp_raw})
        if res.get("error"):
            QMessageBox.warning(self, "Copy", res["error"])
            return
        QGuiApplication.clipboard().setText(res["apo"])
        self.status("Copied the filters (Equalizer APO / squiglink format).", 5000)
        if record:
            self.record(True)

    def bring_back(self, e):
        """Show: its files, target adjustments and curve settings back when they're still in the app, then the EQ as
        a run of its own on the result card."""
        from ui.history_window import day_of, time_of
        names = {m["name"] for m in self.inputs["measurements"]}
        have_m = bool(e.get("meas_files")) and all(n in names for n in e["meas_files"])
        have_t = e.get("target_file") in self.inputs["targets"]
        S = self.S
        if have_m and have_t:
            S["files"]["active_target"] = e["target_file"]
            S["files"]["excluded"] = [n for n in names if n not in e["meas_files"]]
            for k in self.meta["defaults"]["target_adjust"]:
                if e.get("adjust") and k in e["adjust"]:
                    S["target_adjust"][k] = e["adjust"][k]
            for k in self.meta["defaults"]["site"]:
                if e.get("site") and k in e["site"]:
                    S["site"][k] = e["site"][k]
            if isinstance(e.get("rig_convert"), bool):
                S["rig_convert"]["enabled"] = e["rig_convert"]
            res = self.svc.call("/api/settings", {"settings": S})
            if res.get("inputs"):
                self.show_inputs(res["inputs"])
            self._curves_seq = getattr(self, "_curves_seq", 0) + 1  # (any load still on its way is dropped)
            self.curves_loaded(self.svc.call("/api/curves", {"settings": S}))
            self.show_settings()
        elif self.curves:
            self.status(f"{'Its target isn’t' if have_m else 'Its measurement files aren’t'} in the app any more, so its "
                        "filters are shown on the graph you have now.", 10000)
        if not self.curves:  # (nothing to show its filters on: said, not "shown on the graph")
            self.status(f"{'Its target isn’t' if have_m else 'Its measurement files aren’t'} in the app any more: "
                        "choose a measurement and a target first, then Show it again.", 10000)
            return
        band = e.get("band")
        if band and list(band) != list(S["scoring"]["band_hz"]):
            self.status(f"It was scored over {band[0]}–{band[1]} Hz and is now over {S['scoring']['band_hz'][0]}–"
                        f"{S['scoring']['band_hz'][1]} Hz, so its error here differs from the one in History.", 10000)
        res = dict(e.get("result") or {}, id=1, filters=[dict(f) for f in e["filters"]])
        res.setdefault("n_filters", e.get("n_filters", len(e["filters"])))
        res.setdefault("rms", e.get("rms") or 0)
        res.setdefault("max_boost", 0)
        self.runs += 1
        self.run_result = {"mode": e.get("mode", "best_fit"), "results": [res], "pick": 1, "best": 1, "n": self.runs,
                           "settings": {}, "seconds": 0,
                           "when": f"{day_of(e['when'])} {time_of(e['when'])}", "history": e.get("base"),
                           "device": e.get("device"), "target_name": e.get("target"), "target_file": e.get("target_file"),
                           "meas_files": e.get("meas_files")}
        self.keep_run(self.run_result)
        self.name_edit.clear()
        self.show_result(1)
        self.history_note()
        self.status(f"From the history: {e.get('device')} → {e.get('target')}, {day_of(e['when']).lower()} "
                    f"{time_of(e['when'])}.", 8000)

    # ---------------------------------------------------------------- presets (AutoEQ Local's Presets menu)
    def preset_names(self):
        from eq import settings as eq_settings
        try:
            return eq_settings.list_presets()
        except OSError:
            return []

    def fill_presets(self, menu):
        """The top bar's Presets menu: each preset (click: load it), Save current settings as…, Delete a preset, and
        Reset all settings…. A preset keeps every setting, not your files."""
        menu.clear()
        names = self.preset_names()
        if not names:
            a = menu.addAction("No presets yet: a preset keeps all your settings (not your files)")
            a.setEnabled(False)
        for n in names:
            menu.addAction(n, lambda n=n: self.load_preset(n))
        menu.addSeparator()
        menu.addAction("Save current settings as…", self.save_preset)
        if names:
            d = menu.addMenu("Delete a preset")
            for n in names:
                d.addAction(n, lambda n=n: self.delete_preset(n))
        menu.addSeparator()
        menu.addAction("Reset all settings…", self.reset_settings)

    def _use_settings(self, s, said):
        """Settings from a preset (or the defaults) in use, your files as they are; Undo in the notice puts the ones
        before back."""
        before = json.loads(json.dumps(self.S))
        s["files"] = before["files"]
        self.S = s
        self._save_settings()
        self.show_settings()
        self.load_curves()

        def undo():
            self.S = before
            self._save_settings()
            self.show_settings()
            self.load_curves()
        self.notify(said, undo)

    def load_preset(self, name):
        res = self.svc.call("/api/presets/load", {"name": name})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self._use_settings(res["settings"], f"Loaded the preset “{name}”: all its settings (your files stay as they are).")

    def save_preset(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save a preset", "Save the current settings as the preset:",
                                        text="My settings")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.preset_names() and QMessageBox.question(
                self, "Save a preset", f"There's a preset called “{name}” already. Replace it?") != QMessageBox.Yes:
            return
        res = self.svc.call("/api/presets/save", {"name": name, "settings": self.S})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self.notify(f"Saved the preset “{name}”: every setting, not your files. Presets, in the top bar, loads it "
                    "again.")

    def delete_preset(self, name):
        if QMessageBox.question(self, "Presets", f"Delete the preset “{name}”?") != QMessageBox.Yes:
            return
        res = self.svc.call("/api/presets/delete", {"name": name})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self.notify(f"Deleted the preset “{name}”.")

    def reset_settings(self):
        if QMessageBox.question(self, "Reset all settings", "Every setting back to its default? Your files and your "
                                "presets are kept, and Undo brings your settings back.") != QMessageBox.Yes:
            return
        res = self.svc.call("/api/reset")
        if res.get("error"):
            QMessageBox.warning(self, "Reset all settings", res["error"])
            return
        self._use_settings(res["settings"], "Every setting is back to its default (your files stay as they are).")
