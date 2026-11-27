"""Make an EQ's History and presets (a part of EqPage, ui/eq_page.py): what a result is in a line, an EQ kept in
History (after a run, saved or copied), "Previously EQ'd" (under Measurement), History's window
(ui/history_window.py) and an EQ from it shown again, Copy (the filters as Equalizer APO text), and the top bar's
Presets menu (a preset loaded, saved or deleted; Reset all settings…).
EqHistory is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts.
"""
import hashlib
import json

import paths
from PySide6.QtWidgets import QMessageBox

from ui.eq_page_parts import modal

# (the Presets menu's note with no presets; the Guide's demo menu shows the same words)
NO_PRESETS = "No presets yet: presets save all settings, not files"


class EqHistory:
    # ---------------------------------------------------------------- History (history.js)
    def run_label(self, run, r):
        """What a result is, in a line (results.js runLabel)."""
        lay = next((l for l in self.meta.get("layouts", []) if l["key"] == r.get("layout")), None)
        if run.get("mode") == "manual":  # (an EQ made by hand: where it began, and its filters)
            n = r.get("n_filters", len(r.get("filters") or []))
            # (no "Manually" at the start: the card's title, the report's title and History's Method column say it)
            return f"{run.get('source') or 'your filters'} · {n} filter{'' if n == 1 else 's'}"
        if r.get("engine") == "graphic":
            # (":g": the range and step of the sliders are kept as -12.0, 12.0 and 1.0, and Settings to try says
            # "-12 to +12 dB (1 dB steps)" on the same page. A value that is no number, an old entry: as it is)
            g = lambda v: f"{v:g}" if isinstance(v, (int, float)) and not isinstance(v, bool) else f"{v}"
            return (f"{lay['name'] if lay else 'Graphic EQ'}: {r['n_filters']} bands, {g(r.get('gain_min'))} to "
                    f"+{g(r.get('gain_max'))} dB ({g(r.get('step'))} dB steps)")
        if run["mode"] == "best_fit":
            yours, added = r.get("yours") or 0, max(0, r["n_filters"] - (r.get("yours") or 0))
            mine = ""
            if yours:  # (Best fit from your filters: kept as they are, or adjusted; with filters added, or yours alone)
                kept = "" if r.get("keep") else " (adjusted)"
                mine = (f"your {yours}{kept} + {added} added" if r.get("rows") else f"only your {yours}" if r.get("keep")
                        else f"your {yours}{kept}") + " · "
            return (mine + (f"{lay['name']} · " if lay and lay["key"] != "any" else "")
                    + f"{r['n_filters']} filter{'' if r['n_filters'] == 1 else 's'}, Q ≤ {r.get('q_max')}, gain ≤ "
                    f"+{r.get('gain_max')} dB")
        return (f"{r.get('rows')} row{'' if r.get('rows') == 1 else 's'} · {r.get('freq_low')}–{r.get('freq_high')} Hz · "
                f"{r.get('gain_min')} to {r.get('gain_max')} dB · Q {r.get('q_min')}–{r.get('q_max')}")

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
        """Into History: after a run (saved False: only when More settings › History keeps every run), or
        saved/copied."""
        run, r = self.current()
        if not r or not self.curves or (not saved and (self.S["history"]["keep"] != "all" or run.get("history"))):
            return
        res = self.svc.call("/api/history/add", {"entry": self.entry_now(saved)})
        if res.get("error"):
            self.status(f"Couldn't add EQ to History: {res['error']}", 8000)
            return
        by_key = {e["key"]: e for e in self.history}
        by_key[res["entry"]["key"]] = res["entry"]
        self.history = [by_key[k] for k in res.get("keys", []) if k in by_key]
        self.history_note()

    def history_note(self):
        """Under Measurement: when you've EQ'd it before (More settings › History can turn it off)."""
        mine = [e for e in self.history if self.curves and e.get("device") == self.curves["name"]]
        on = bool(self.S["history"].get("eqd_before")) and bool(mine)
        self.eqd_before.setVisible(on)
        self.eqd_show.setVisible(on)
        if on:
            from ui.history_window import day_of
            last = max(mine, key=lambda e: e["when"])
            self.eqd_before.setText(f"Previously EQ'd {'once' if len(mine) == 1 else f'{len(mine)} times'} · "
                                    f"Last: {day_of(last['when'])}")

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
        (say or self.status)("Copied filters")
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
            # (the entry's Website values, not its Which website to copy: your choice stays, and an entry from before
            # 2026-11-26 has a choice the list no longer has. The curves are made with the entry's values as they
            # are, "site_as_is", until the curves change: the critique of feature 5)
            for k in self.meta["defaults"]["site"]:
                if e.get("site") and k in e["site"] and k != "profile":
                    S["site"][k] = e["site"][k]
            if isinstance(e.get("rig_convert"), bool):
                S["rig_convert"]["enabled"] = e["rig_convert"]
            res = self.svc.call("/api/settings", {"settings": S})
            if res.get("inputs"):
                self.show_inputs(res["inputs"])
            self._curves_seq = getattr(self, "_curves_seq", 0) + 1  # (any load still on its way is dropped)
            self.site_as_is = bool(e.get("site"))
            curves = self.svc.call("/api/curves", {"settings": S, "site_as_is": self.site_as_is})
            self.curves_loaded(curves)
            self.show_settings()
        elif self.curves:
            self.status(f"{'Original target' if have_m else 'Original measurement files'} not found. Showing EQ "
                        "filters on your current measurement and target.", 10000)
        if not self.curves:  # (nothing to show its filters on: what's needed first, in a box: UI-RULES 25)
            if have_m and have_t:  # (both found, but the curves failed: their error, not "not found")
                QMessageBox.information(self, "Show", str((curves or {}).get("error")
                                                          or f"Couldn't calculate curves. Check {paths.LOG} for details."))
                return
            QMessageBox.information(self, "Show", f"{'Original target' if have_m else 'Original measurement files'} "
                                    "not found. Select a measurement and target, then try Show again.")
            return
        band = e.get("band")
        if band and list(band) != list(S["scoring"]["band_hz"]):
            # (:g: History keeps the range as numbers with decimals, "20.0–20000.0 Hz")
            now = S["scoring"]["band_hz"]
            self.status(f"Frequency range changed from {band[0]:g}–{band[1]:g} Hz to {now[0]:g}–{now[1]:g} Hz, so the "
                        "displayed error differs from History", 10000)
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
                    f"{time_of(e['when'])}", 8000)

    # ---------------------------------------------------------------- presets (AutoEQ Local's Presets menu)
    def preset_names(self):
        from eq import settings as eq_settings
        try:
            return eq_settings.list_presets()
        except OSError:
            return []

    def fill_presets(self, menu):
        """The top bar's Presets menu: each preset (click: load it), Save as a preset…, Delete a preset, and
        Reset all settings… A preset keeps every setting, not your files."""
        menu.clear()
        names = self.preset_names()
        if not names:
            a = menu.addAction(NO_PRESETS)
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
        menu.addAction("Reset all settings…", self.use_initial_settings)

    def preset_in_use(self, name):
        """Whether the preset has the settings in use: all of them but your files and, with the automatic settings on,
        the values that they set (they change with each new measurement)."""
        # (read only: /api/presets/load would save each preset in turn as settings.json while the menu opens)
        res = self.svc.call("/api/presets/read", {"name": name})
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
        self._use_settings(res["settings"], f"Loaded preset “{name}” (files unchanged)")

    def save_preset(self):
        from ui.window_parts import ask_text  # (looked up here: the tests answer it)
        name, ok = ask_text(self, "Save as a preset", "Name of the preset (all settings, not your files)",
                            "New preset", "Save")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.preset_names() and QMessageBox.question(  # (No the default: it can't be had back, UI-RULES 17)
                self, "Save as a preset", f"Preset “{name}” already exists. Replace it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        res = self.svc.call("/api/presets/save", {"name": name, "settings": self.S})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self.notify(f"Saved preset “{name}”")

    def delete_preset(self, name):
        if QMessageBox.question(self, "Delete", f"Delete preset “{name}”?", QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:  # (as every Delete asks: UI-RULES 17)
            return
        res = self.svc.call("/api/presets/delete", {"name": name})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self.notify(f"Deleted preset “{name}”")

    def use_initial_settings(self):
        if QMessageBox.question(self, "Reset all settings", "Reset all settings to defaults? Your files and "
                                "presets won't change.") \
                != QMessageBox.Yes:
            return
        res = self.svc.call("/api/reset")
        if res.get("error"):
            QMessageBox.warning(self, "Reset all settings", res["error"])
            return
        self._use_settings(res["settings"], "Settings reset to defaults (files unchanged)")
