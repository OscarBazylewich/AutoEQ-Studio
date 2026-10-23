"""Make an EQ's run and result (a part of EqPage, ui/eq_page.py): Run (Retry, Cancel) and its progress, the result
shown (its numbers, Fewer or more filters, All results…, Compare…, Run several…), this session's runs, the filters
being edited (Table, Sliders, Add filter, Sort, Revert), Save filters, Report, and Use on device (or Try for 5
minutes on).
EqResult is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts.
"""
import os
import tempfile

import numpy as np
from PySide6.QtWidgets import QMessageBox

import textfile
from ui.eq_page_parts import MODE_SHORT, file_base_name, modal


class EqResult:
    """Make an EQ's run and result."""

    # ---------------------------------------------------------------- running
    def run(self, retry=None):
        """Run with the settings; retry: {"filters", "add"} (Best fit from the filters shown, this run only)."""
        if not self.curves:
            QMessageBox.information(self, "Run", "Add a target and at least one measurement first.")
            return
        if retry is not None and not retry["filters"]:
            QMessageBox.information(self, "Retry", "There are no filters to start from: add one, or switch one on.")
            return
        if self.S["auto"]["enabled"]:
            self.refresh_auto()  # (the values for exactly these settings)
        body = {"settings": self.S, "mode": "best_fit" if retry else self.S["mode"], "analysis": self.analysis}
        if retry:
            body["retry"] = retry
        r = self.svc.call("/api/run", body)
        if r.get("error"):
            QMessageBox.warning(self, "Run", r["error"])
            return
        self.run_btn.setEnabled(False)
        self.queue_btn.setEnabled(False)  # (a queue started now failed every pair: one run at a time)
        self.retry_btn.setEnabled(False)
        self.cancel_btn.show()
        self.progress.setValue(0)
        self.progress.show()
        self.progress_text.setText("Starting…")
        self._poll.start()

    def _poll_job(self):
        j = self.svc.call("/api/job")
        total = j.get("total") or 0
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(j.get("done") or 0)
        self.progress_text.setText(f"{j.get('message') or ''}" + (f" · {round(j['elapsed'])} s" if j.get("elapsed") else ""))
        if j.get("status") == "running":
            return
        self._poll.stop()
        self.svc.call("/api/job", {"ack": True})
        self.run_btn.setEnabled(True)
        self.queue_btn.setEnabled(True)
        self.retry_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress.hide()
        if j.get("status") == "done":
            self.runs += 1
            self.run_result = dict(j["result"], n=self.runs)
            self.keep_run(self.run_result)
            self.progress_text.setText(f"Done in {j['result'].get('seconds')} s.")
            self.name_edit.clear()
            self.show_result(j["result"]["pick"])
            self.record(False)
        elif j.get("status") == "error":
            self.progress_text.setText("")
            QMessageBox.warning(self, "Run failed", j.get("message") or "The run failed.")
        elif j.get("status") == "cancelled":
            self.progress_text.setText("Cancelled.")

    # ---------------------------------------------------------------- the result
    def show_result(self, rid):
        run = self.run_result
        if not run:
            return
        self.sel = run["_sel"] = rid
        r = next(x for x in run["results"] if x["id"] == rid)
        self.ORIG = [{"enabled": True, "type": f.get("type") or "PK", "freq": f["freq"], "gain": f["gain"], "q": f["q"]}
                     for f in r["filters"]]
        self.EDIT = [dict(f) for f in self.ORIG]
        self.res_sub.setText((f"From History ({run['when']})" if run.get("history") else f"Run {run.get('n', 1)}")
                             + f" · {self.run_label(run, r)} · made for {run.get('device')} → {run.get('target_name')}")
        note = self.pick_note(run, r)
        self.pick_lab.setText(note)
        self.pick_lab.setVisible(bool(note))
        self.chips["error"].setToolTip("How far the EQ'd measurement stays from the target, on average, in the scored "
                                       "range (lower is closer)")
        self.chips["preamp"].setToolTip("How much the whole EQ is turned down so its boosts never clip: the filters' "
                                        "boosts added up where they overlap")
        # the best result for each filter count (the pick for its own count), as AutoEQ Local's chips
        by_n = {}
        for x in run["results"]:
            had = by_n.get(x["n_filters"])
            if not had or x["id"] == run["pick"] or (had["id"] != run["pick"] and x["rms"] < had["rms"]):
                by_n[x["n_filters"]] = x
        shown = next((x for x in run["results"] if x["id"] == rid), None)
        if shown:  # (one chosen in All results… or Compare: its own count's entry, so the list says what's shown)
            by_n[shown["n_filters"]] = shown
        self.count_combo.clear()
        for n, x in sorted(by_n.items()):
            self.count_combo.addItem(f"{n} filters  ·  {x['rms']:.2f} dB" + ("  ✓ picked for you" if x["id"] == run["pick"] else ""),
                                     x["id"])
        self.count_combo.setCurrentIndex(max(0, self.count_combo.findData(rid)))
        self.count_combo.sort_items()
        self.count_combo.setEnabled(len(by_n) > 1)
        self.all_btn.setText(f"All {len(run['results'])} results…")
        self.all_btn.setVisible(len(run["results"]) > 1)
        self.result_box.show()
        self.render_runs()
        self.set_view(self.sw.s.get("filters_view", "table"), remember=False)
        self.live_update()

    @staticmethod
    def pick_note(run, r):
        """Under the result's numbers: how it sounds next to the target (the audible pick, engines.pick)."""
        case, lim = run.get("pick_case"), run.get("ear_db") or 0.25
        hz = lambda v: (f"{v / 1000:.1f} kHz" if v >= 1000 else f"{v:.0f} Hz") if v else ""
        if r.get("ear") is None or not case:
            return ""
        if r["id"] != run.get("pick"):
            return f"Sounds within {r['ear']:.2f} dB of the target everywhere (as the ear hears it)" + (
                f"; most off around {hz(r['ear_at'])}." if r.get("ear_at") and r["ear"] > lim else ".")
        if case == "target":
            return (f"Sounds the same as the target: within {r['ear']:.2f} dB everywhere, as the ear hears it (the "
                    f"limit: {lim:g} dB), with the fewest filters that do.")
        best = min((x for x in run["results"] if x.get("ear") is not None), key=lambda x: x["ear"], default=r)
        return (f"The target is out of reach here (your EQ app's limits, or detail filters can't follow): even the "
                f"closest EQ is {best['ear']:.2f} dB off around {hz(best.get('ear_at'))}. "
                + ("This is that closest one." if best["id"] == r["id"] else
                   "This one sounds the same as that closest one, with fewer filters."))

    # ---------------------------------------------------------------- runs this session (results.js RUNS)
    def use_in_single_run(self):
        """A sweep's chosen values into Website AutoEQ: one run (results.js "Use in single run")."""
        run, r = self.current()
        if not r:
            return
        self.S["site_single"].update({k: r[k] for k in ("rows", "freq_low", "freq_high", "gain_min", "gain_max", "q_min",
                                                        "q_max") if r.get(k) is not None})
        manual = self.S["auto"].setdefault("manual", [])
        for k in ("rows", "freq_high", "gain_min", "gain_max", "q_max"):  # (these exact values: yours)
            if "site_single." + k not in manual:
                manual.append("site_single." + k)
        self.S["mode"] = "site_single"
        self.changed()
        self.settings.refresh()
        self.status("Copied into Website AutoEQ: one run.", 6000)

    def open_all_results(self):
        """Every result of the run shown, and the error grid (ui/all_results.py)."""
        from ui.all_results import AllResults
        if self.current()[1]:
            modal(AllResults(self))

    def open_queue(self):
        """Several EQs in one go (ui/queue_window.py)."""
        from ui.queue_window import QueueWindow
        if not self.groups or not self.inputs.get("targets"):
            QMessageBox.information(self, "Run several", "Add a target and at least one measurement first.")
            return
        modal(QueueWindow(self))

    def open_compare(self):
        """Two EQs side by side (ui/compare_results.py)."""
        from ui.compare_results import CompareResults, options
        if len(options(self)) < 2:
            self.status("Nothing else to compare with yet: another run, another filter count or History.", 6000)
            return
        modal(CompareResults(self))

    def keep_run(self, run):
        self.session_runs = [x for x in self.session_runs if x is not run][-19:] + [run]  # (the last 20)

    def render_runs(self):
        c = self.runs_combo
        c.clear()
        for run in reversed(self.session_runs):
            best = min((x["rms"] for x in run["results"] if x.get("rms") is not None), default=None)
            c.addItem((f"From History ({run['when']})" if run.get("history") else f"Run {run.get('n', 1)}")
                      + f"  ·  {MODE_SHORT.get(run['mode'], run['mode'])}"
                      + (f"  ·  {best:.2f} dB" if best is not None else "")
                      + f"  ·  {run.get('device')} → {run.get('target_name')}", id(run))
        c.setCurrentIndex(max(0, c.findData(id(self.run_result))))
        c.sort_items()
        self.runs_row.setVisible(len(self.session_runs) > 1)

    def choose_run(self, key):
        run = next((x for x in self.session_runs if id(x) == key), None)
        if run is None or run is self.run_result:
            return
        self.run_result = run
        self.name_edit.clear()
        self.show_result(run["_sel"] if run.get("_sel") is not None else run["pick"])  # (result 0 is a result)

    def remove_run(self):
        self.session_runs = [x for x in self.session_runs if x is not self.run_result]
        if self.session_runs:
            last = self.session_runs[-1]
            self.run_result = last
            self.name_edit.clear()
            self.show_result(last["_sel"] if last.get("_sel") is not None else last["pick"])
        else:
            self.run_result, self.sel = None, None
            self.result_box.hide()

    # ---------------------------------------------------------------- the filters being edited
    def active(self):
        """The filters switched on, as the run, Save and Use take them."""
        return [{"type": f.get("type", "PK"), "freq": f["freq"], "gain": f["gain"], "q": f["q"]}
                for f in self.EDIT if f.get("enabled", True) is not False]

    def edited(self):
        key = lambda fl: sorted((f.get("enabled", True) is not False, f.get("type", "PK"), float(f["freq"]),
                                 float(f["gain"]), float(f["q"])) for f in fl)
        return key(self.EDIT) != key(self.ORIG)  # (the same filters in another order, e.g. after Sort, aren't)

    def stats(self):
        """The filters' numbers as AutoEQ Local's plot.js worked them out: the error in the scored range, the pre-amp
        (the EQ's highest point, turned down), the biggest Q and boost."""
        from eq import engines
        act, c = self.active(), self.curves
        f = np.asarray(c["f"]) if c else np.geomspace(20, 20000, 480)
        g = engines.eq_gain(f, act, self.S["site"]["sample_rate"])
        rms = ear = None
        if c:
            band = self.S["scoring"]["band_hz"]
            inside = (f >= band[0]) & (f <= band[1])
            full = np.asarray(c["meas"]) + g - np.asarray(c["target"])
            d = full[inside]
            rms = float(np.sqrt(np.mean(d * d))) if d.size else None
            ear = engines.ear_error(f, full, band)[0] if d.size else None  # (how it sounds: the pick's line)
        return {"rms": rms, "ear": ear, "preamp_raw": -float(np.max(g)) if act else 0.0, "n": len(act),
                "max_q": max([0] + [x["q"] for x in act]), "max_boost": max([0] + [x["gain"] for x in act])}

    def preamp_text(self, raw):
        """The pre-amp as saved: less the extra headroom, rounded (safe: down; site: as squiglink)."""
        e = self.S["export"]
        p = raw - float(e.get("extra_headroom") or 0)
        v = round(p * 10) / 10 if e.get("preamp_rounding") == "site" else np.floor(p * 10 + 1e-9) / 10
        return f"{(0.0 if v == 0 else v):.1f}"

    def live_update(self):
        """After an edit (or a new result): the numbers, the title, the file name, the graph."""
        run, r = self.current()
        if not r:
            return
        st, ed = self.stats(), self.edited()
        tag = "recommended" if r["id"] == run["pick"] else "lowest error" if r["id"] == run["best"] else ""
        self.res_title.setText(MODE_SHORT.get(run["mode"], run["mode"]) + (f"  ·  {tag}" if tag else "")
                               + ("  ·  edited" if ed else ""))
        if ed:  # (the run's line was about the filters before the edit)
            note = (f"As edited: sounds within {st['ear']:.2f} dB of the target everywhere, as the ear hears it (the "
                    f"limit: {run.get('ear_db') or 0.25:g} dB)." if run.get("pick_case") and st["ear"] is not None else "")
        else:
            note = self.pick_note(run, r)
        self.pick_lab.setText(note)
        self.pick_lab.setVisible(bool(note))
        self.chips["filters"].setText(f"Filters  {st['n']}")
        self.chips["error"].setText(f"Error  {st['rms']:.2f} dB" if st["rms"] is not None else "Error  –")
        self.chips["preamp"].setText(f"Pre-amp  {self.preamp_text(st['preamp_raw'])} dB")
        self.chips["boost"].setText(f"Max boost  +{st['max_boost']:.1f} dB")
        self.chips["maxq"].setText(f"Max Q  {st['max_q']:g}" if st["max_q"] else "Max Q  –")
        site = run["mode"].startswith("site") and r.get("rows") is not None
        self.site_row.setVisible(site)
        if site:
            self.site_text.setText(
                "Type into squiglink's AutoEQ panel: Filter rows <b>{rows}</b> · Frequency Range <b>{freq_low}</b> to "
                "<b>{freq_high}</b> · Gain Range <b>{gain_min}</b> to <b>{gain_max}</b> · Q Range <b>{q_min}</b> to "
                "<b>{q_max}</b> → the site shows Pre-amp <b>{pre:.1f} dB</b>".format(
                    pre=float(r.get("preamp") or 0), **{k: r.get(k, "–") for k in ("rows", "freq_low", "freq_high",
                                                                                      "gain_min", "gain_max", "q_min", "q_max")})
                + (" <i>(you edited the filters, so the site won't produce these exact values)</i>" if ed else ""))
            self.site_use.setVisible(run["mode"] == "site_sweep")
        self.revert_btn.setVisible(ed)
        self.editor.set_preamp_text(self.preamp_text(st["preamp_raw"]))
        if hasattr(self, "listen"):
            self.listen.refresh()
        if not self.name_edit.text().strip() or self.name_edit.property("auto") is not False:
            self.name_edit.setText(self.auto_name())
            self.name_edit.setProperty("auto", True)
        self.draw()

    def set_view(self, view, remember=True):
        for k, b in self.view_btns.items():
            b.setChecked(k == view)
        self.editor.set_filters(self.EDIT, self.preamp_text(self.stats()["preamp_raw"]) if self.current()[1] else "0.0")
        self.editor.set_view(view)
        if remember and self.sw.s.get("filters_view") != view:
            self.sw.set("filters_view", view)

    def add_filter(self):
        self.EDIT.append({"enabled": True, "type": "PK", "freq": 1000, "gain": 0.0, "q": 1.0})
        self.editor.rebuild()
        self.live_update()

    def sort_filters(self):
        self.EDIT.sort(key=lambda f: f["freq"])
        self.editor.rebuild()
        self.live_update()

    def revert(self):
        self.EDIT[:] = [dict(f) for f in self.ORIG]
        self.editor.rebuild()
        self.live_update()

    def auto_name(self):
        run, r = self.current()
        lay = next((l for l in self.meta.get("layouts", []) if l["key"] == r.get("layout") and l["key"] != "any"), None)
        return file_base_name(run.get("device") or "EQ", run.get("target_name") or "target", lay["name"] if lay else "",
                              run["mode"], len(self.active()) if self.EDIT else r["n_filters"]) + \
            (" edited" if self.EDIT and self.edited() else "")

    def save(self):
        run, r = self.current()
        if not r:
            return
        if not self.active():
            QMessageBox.information(self, "Save filters", "There are no filters switched on to save.")
            return
        from eq import exports
        files = any(self.S["export"].get(k) for k in exports.FORMATS)
        if not files and not self.S["export"].get("report"):
            QMessageBox.information(self, "Save filters", "No file is ticked to save: choose your EQ app, or tick the "
                                    "files under Advanced › Saved files.")
            return
        name = self.name_edit.text().strip() or self.auto_name()
        written, notes, kept = [], "", False
        if files:
            # (switched-off filters go too: an Equalizer APO file keeps them as OFF lines, as AutoEQ Local's did)
            body = {"settings": self.S, "filters": [dict(f) for f in self.EDIT if f.get("freq") and f.get("q")],
                    "preamp": self.stats()["preamp_raw"], "name": name}
            res = self.svc.call("/api/export", body)
            if res.get("exists"):
                if not self._replace_ok(res["exists"]):
                    return
                res = self.svc.call("/api/export", {**body, "replace": True})
            if res.get("error"):
                QMessageBox.warning(self, "Save filters", res["error"])
                return
            written = [os.path.basename(p) for p in (res.get("written") or {}).values()]
            notes = " ".join(res.get("notes") or [])
        if self.S["export"].get("report"):
            path = self.report(open_it=False)
            if path:
                written.append(os.path.basename(path))
            else:
                kept = True
        if not written:
            return
        self.record(True)
        self.status(f"Saved {', '.join(written)} in your Saved EQs folder." + (f" {notes}" if notes else "")
                    + (" The report of that name was kept: change the File name to save another beside it." if kept else ""),
                    10000)

    def _replace_ok(self, names):
        return QMessageBox.question(self, "Replace?", "Already in your Saved EQs folder:\n\n" + "\n".join(names)
                                    + "\n\nReplace? (No keeps them: change the File name to save beside them.)") == QMessageBox.Yes

    def report(self, open_it=True):
        """The HTML report of the result shown (and of up to two of your EQs to compare on the graph), as AutoEQ
        Local's export.js reportBody: its path, or None when one of that name was kept or it failed."""
        run, r = self.current()
        if not r:
            return None
        title = MODE_SHORT.get(run["mode"], "EQ") + (" (edited)" if self.edited() else "")
        fields = [["Filter rows", r.get("rows")], ["Frequency Range", f"{r.get('freq_low')} to {r.get('freq_high')}"],
                  ["Gain Range", f"{r.get('gain_min')} to {r.get('gain_max')}"],
                  ["Q Range", f"{r.get('q_min')} to {r.get('q_max')}"]] if run["mode"].startswith("site") else []
        # (the report is drawn on the files the EQ was made for, while they're in the app; else on the measurement
        # chosen now, and it says so)
        mf, tf = run.get("meas_files"), run.get("target_file")
        names = {m["name"] for m in self.inputs["measurements"]}
        own_files = bool(mf) and all(n in names for n in mf) and tf in self.inputs["targets"]
        made_for, here = run.get("device"), (self.curves or {}).get("name")
        other = (f" Made for the {made_for}: shown here on the {here}." if not own_files and made_for and here
                 and made_for != here else "")
        cards = [{"title": title, "badge": "recommended" if r["id"] == run.get("pick") else "", "fields": fields,
                  "text": self.run_label(run, r) + "." + other, "filters": self.active()}]
        for p in [p for p in self.listen.pins if p.get("shown", True)][:2]:
            cards.append({"title": p["name"], "text": "", "filters": [f for f in p["filters"] if f.get("enabled", True) is not False]})
        own = self.name_edit.text().strip() if self.name_edit.property("auto") is False else ""
        body = {"settings": self.S, "cards": cards, "open": open_it, "name": own,
                **({"meas_files": mf, "target_file": tf} if own_files else {})}
        if run["mode"] in ("site_sweep", "best_fit") and len(run["results"]) > 1:
            body.update(grid_mode=run["mode"], grid_results=[{k: x.get(k) for k in ("rows", "q_max", "rms", "freq_high",
                                                                                     "n_filters", "max_boost", "ear")}
                                                             for x in run["results"]])
        res = self.svc.call("/api/report", body)
        if res.get("exists"):
            if not self._replace_ok(res["exists"]):
                return None
            res = self.svc.call("/api/report", {**body, "replace": True})
        if res.get("error"):
            QMessageBox.warning(self, "Report", res["error"])
            return None
        if open_it:
            self.status(f"Report: {os.path.basename(res['path'])} (in your Saved EQs folder).", 8000)
        return res.get("path")

    # ---------------------------------------------------------------- Use on device
    def _fill_use_menu(self):
        m = self.use_menu
        m.clear()
        _, r = self.current()
        if not r:
            m.addAction("Run first").setEnabled(False)
            return
        if not self.sw.apo.found:
            m.addAction("Equalizer APO isn't installed (see Devices)").setEnabled(False)
            return
        from switcher.core import shown
        keys = [d.key for d in self.sw.devices] + [k for k in self.sw.s["devices"] if not self.sw.device(k)]
        for key in keys:
            rec, d = self.sw.record(key), self.sw.device(key)
            where = "playing now" if key == self.sw.playing_key else "connected" if d and d.connected else "not connected"
            a = m.addAction(f"{shown(rec)}  ·  {where}")
            a.triggered.connect(lambda _=False, k=key: self.use_on(k))
        if not keys:
            m.addAction("No playback devices found").setEnabled(False)
        live = [d.key for d in self.sw.devices if d.connected]
        if live:  # (hear it in every app for a few minutes before keeping it)
            m.addSeparator()
            t = m.addMenu("Try for 5 minutes on")
            t.setToolTipsVisible(True)
            for key in live:
                a = t.addAction(shown(self.sw.record(key)) + ("  ·  playing now" if key == self.sw.playing_key else ""))
                a.setToolTip("Plays in every app for 5 minutes; then Keep it, or the device's own EQ comes back")
                a.triggered.connect(lambda _=False, k=key: self.try_on(k))

    def _apo_text(self, title):
        """The EQ shown, as Equalizer APO text (as edited, with its pre-amp), or None (said)."""
        res = self.svc.call("/api/text", {"settings": self.S, "filters": self.active(),
                                          "preamp": self.stats()["preamp_raw"]})
        if res.get("error"):
            QMessageBox.warning(self, title, res["error"])
            return None
        return res["apo"]

    def try_on(self, key, minutes=5):
        """The EQ shown plays on a device for a few minutes, in every app (Devices' trial: switcher/core.py)."""
        from switcher.core import shown
        text = self._apo_text("Try on device")
        if text is None:
            return
        name = (self.name_edit.text().strip() or self.auto_name())[:80]
        try:
            self.sw.try_eq(key, text, name, minutes)
        except OSError as e:
            QMessageBox.warning(self, "Try on device", str(e))
            return
        extra = "" if self.sw.apo.set_up() else " (Equalizer APO isn't using AutoEQ Studio yet: Set up… on Devices.)"
        self.window().render_all() if hasattr(self.window(), "render_trial") else None
        self.status(f"Trying “{name}” on {shown(self.sw.record(key))} for {minutes} minutes: Keep it or Stop now in "
                    f"the bar at the top, or the tray icon's menu.{extra}", 10000)

    def use_on(self, key):
        """The EQ shown becomes a profile of this device, switched on (APO applies it while the device plays)."""
        from switcher.core import shown
        run, r = self.current()
        text = self._apo_text("Use on device")
        if text is None:
            return
        name = (self.name_edit.text().strip() or self.auto_name())[:80]
        path = os.path.join(tempfile.mkdtemp(prefix="autoeq-studio-"), textfile.safe_name(name, "EQ", 80) + ".txt")
        try:
            textfile.write_atomic(path, text)
            pid = self.sw.import_profile(path, name)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Use on device", str(e))
            return
        finally:
            try:
                os.remove(path)
                os.rmdir(os.path.dirname(path))
            except OSError:
                pass
        self.sw.add_to_device(key, pid, switch_on=True)
        rec, d = self.sw.record(key), self.sw.device(key)
        extra = ""
        if not self.sw.apo.set_up():
            extra = " Equalizer APO isn't using AutoEQ Studio yet: Set up… on the Devices screen."
        elif d and not d.apo:
            extra = " Equalizer APO isn't installed on this device yet (see Devices)."
        self.status(f"“{self.sw.profile_name(pid)}” is now on for {shown(rec)}.{extra}", 10000)
