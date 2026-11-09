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
            return f"Manually · {run.get('source') or 'your filters'} · {n} filter{'' if n == 1 else 's'}"
        if r.get("engine") == "graphic":
            return (f"{lay['name'] if lay else 'Graphic EQ'}: {r['n_filters']} bands, {r.get('gain_min')} to "
                    f"+{r.get('gain_max')} dB in {r.get('step')} dB steps")
        if run["mode"] == "best_fit":
            yours, added = r.get("yours") or 0, max(0, r["n_filters"] - (r.get("yours") or 0))
            mine = ""
            if yours:
                mine = (f"your {yours} + {added} added" if r.get("rows") else f"only your {yours}" if r.get("keep")
                        else f"your {yours}, adjusted") + ("" if r.get("keep") or not r.get("rows") else " (adjusted)") + " · "
            return (mine + (f"{lay['name']} · " if lay and lay["key"] != "any" else "")
                    + f"{r['n_filters']} filters, Q ≤ {r.get('q_max')}, gain ≤ +{r.get('gain_max')}")
        return (f"{r.get('rows')} rows · {r.get('freq_low')}–{r.get('freq_high')} · {r.get('gain_min')} to "
                f"{r.get('gain_max')} · Q {r.get('q_min')}–{r.get('q_max')}")

    @staticmethod
    def filters_fingerprint(filters):
        """A short fingerprint of filters: the same result saved as it is and edited are two entries (in another
        order, e.g. sorted, one). Public: the Queue window makes its History entries' keys with it too."""
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
        return {"key": f"{base}-{self.filters_fingerprint(filters)}", "base": base, "saved": saved,
                "device": run.get("device") or c.get("name"), "target": run.get("target_name") or c.get("target_name"),
                "target_file": run.get("target_file") or self.inputs.get("active_target"),
                "meas_files": run.get("meas_files") or [m["name"] for m in self.inputs["measurements"] if m["included"]],
                "adjust": S["target_adjust"], "mode": run["mode"],
                "label": self.run_label(run, r) + (" (edited)" if self.edited() else ""), "result": result,
                "filters": filters, "rms": st["rms"], "preamp": st["preamp_raw"], "n_filters": st["n"],
                "site": S["site"], "rig_convert": S["rig_convert"]["enabled"], "band": S["scoring"]["band_hz"]}

    def add_to_history(self, saved):
        """Into History: after a run (saved False: only when Advanced › History keeps every run), or saved/copied."""
        run, r = self.current()
        if not r or not self.curves or (not saved and (self.S["history"]["keep"] != "all" or run.get("history"))):
            return
        res = self.svc.call("/api/history/add", {"entry": self.entry_now(saved)})
        if res.get("error"):
            self.status(f"The app cannot add this EQ to History: {res['error']}", 8000)
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
            self.eqd_before.setText(f"History has {'1 EQ' if len(mine) == 1 else f'{len(mine)} EQs'} for this IEM · "
                                    f"the last EQ: {day_of(last['when'])}")

    def open_history(self, this_iem):
        from ui.history_window import HistoryWindow
        r = self.svc.call("/api/history")
        if "entries" in r:
            self.history = r["entries"]
        modal(HistoryWindow(self, this_iem))

    def copy_filters(self, filters, preamp_raw, record=True, say=None):
        """The filters as Equalizer APO text on the clipboard (kept in History when they're the result's). say: the
        message line to tell it in (a window's own, UI-RULES 7; none: the main window's)."""
        from PySide6.QtGui import QGuiApplication
        on = [f for f in filters if f.get("enabled", True) is not False]
        res = self.svc.call("/api/text", {"settings": self.S, "filters": on, "preamp": preamp_raw})
        if res.get("error"):
            QMessageBox.warning(self, "Copy", res["error"])
            return
        QGuiApplication.clipboard().setText(res["apo"])
        (say or self.status)("The app copied the filters (Equalizer APO / squiglink format).")
        if record:
            self.add_to_history(True)

    def show_history_entry(self, e):
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
            self.status(f"{'Its target is not' if have_m else 'Its measurement files are not'} in the app. Thus, the "
                        "graph shows its filters with your measurement and target.", 10000)
        if not self.curves:  # (nothing to show its filters on: what's needed first, in a box: UI-RULES 25)
            QMessageBox.information(self, "Show", f"{'Its target is not' if have_m else 'Its measurement files are not'} "
                                    "in the app: select a measurement and a target first. Then click Show again.")
            return
        band = e.get("band")
        if band and list(band) != list(S["scoring"]["band_hz"]):
            self.status(f"Its error range was {band[0]}–{band[1]} Hz and is {S['scoring']['band_hz'][0]}–"
                        f"{S['scoring']['band_hz'][1]} Hz at this time. Thus, its error here is different from the "
                        "error in History.", 10000)
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
        self.status(f"From History: {e.get('device')} → {e.get('target')}, {day_of(e['when'])} "
                    f"{time_of(e['when'])}.", 8000)

    # ---------------------------------------------------------------- presets (AutoEQ Local's Presets menu)
    def preset_names(self):
        from eq import settings as eq_settings
        try:
            return eq_settings.list_presets()
        except OSError:
            return []

    def fill_presets(self, menu):
        """The top bar's Presets menu: each preset (click: load it), Save as a preset…, Delete a preset, and
        Reset all settings…. A preset keeps every setting, not your files."""
        menu.clear()
        names = self.preset_names()
        if not names:
            a = menu.addAction("No presets: a preset keeps all your settings (not your files)")
            a.setEnabled(False)
        for n in names:  # (✓ at the preset with the settings in use: the UI audit, 2026-11-08)
            a = menu.addAction(n, lambda n=n: self.load_preset(n))
            if self.preset_in_use(n):
                a.setCheckable(True)
                a.setChecked(True)
        menu.addSeparator()
        menu.addAction("Save as a preset…", self.save_preset)  # (the window it opens says the same: UI-RULES 17)
        if names:
            d = menu.addMenu("Delete a preset")
            for n in names:
                d.addAction(n, lambda n=n: self.delete_preset(n))
        menu.addSeparator()
        menu.addAction("Use the initial settings…", self.use_initial_settings)

    def preset_in_use(self, name):
        """Whether the preset has the settings in use: all of them but your files and, with the automatic settings on,
        the values that they set (they change with each new measurement)."""
        res = self.svc.call("/api/presets/load", {"name": name})
        if res.get("error") or not isinstance(res.get("settings"), dict):
            return False
        from eq import settings as eq_settings
        a, b = json.loads(json.dumps(self.S)), json.loads(json.dumps(res["settings"]))
        for d in (a, b):
            d.pop("files", None)
        if self.S["auto"]["enabled"] and hasattr(self, "settings"):
            manual = set(self.S["auto"].get("manual") or [])
            for p in self.settings.auto_paths:
                if p not in manual:
                    for d in (a, b):
                        try:
                            eq_settings.set_path(d, p, None)
                        except (KeyError, IndexError, TypeError):
                            pass
        return a == b

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
        self._use_settings(res["settings"], f"The app loaded the preset “{name}”: all its settings (your files do not "
                                            "change).")

    def save_preset(self):
        from ui.window_parts import ask_text  # (looked up here: the tests answer it)
        name, ok = ask_text(self, "Save as a preset", "Name of the preset (all settings, not your files)",
                            "New preset", "Save")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.preset_names() and QMessageBox.question(  # (No the default: it can't be had back, UI-RULES 17)
                self, "Save as a preset", f"There is a preset with the name “{name}”. Replace it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        res = self.svc.call("/api/presets/save", {"name": name, "settings": self.S})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self.notify(f"The app saved the preset “{name}”: all settings, not your files. Presets (in the top bar) loads "
                    "it again.")

    def delete_preset(self, name):
        if QMessageBox.question(self, "Delete", f"Delete the preset “{name}”?", QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:  # (as every Delete asks: UI-RULES 17)
            return
        res = self.svc.call("/api/presets/delete", {"name": name})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self.notify(f"The app deleted the preset “{name}”.")

    def use_initial_settings(self):
        if QMessageBox.question(self, "Use the initial settings", "Change all settings to their initial values? Your "
                                "files and presets do not change. With Undo, you get your settings again.") \
                != QMessageBox.Yes:
            return
        res = self.svc.call("/api/reset")
        if res.get("error"):
            QMessageBox.warning(self, "Use the initial settings", res["error"])
            return
        self._use_settings(res["settings"], "All settings have their initial values (your files do not change).")
