"""Make an EQ's run and result (a part of EqPage, ui/eq_page.py): Run (Retry, Cancel) and its progress, the result
shown (its numbers, Number of filters, All results…, Compare…; Queue… on Make the EQ), the EQs that you made, the
filters being edited (Table, Sliders, Add filter, Sort, Undo all), Save filters, Report, and Use on device (a new
profile of a device; Update a profile: into a profile you have, with Undo; or Use for 5 minutes on).
By hand (Make the EQ's second way, set_way: its tab beside Automatically): an EQ of your own, begun empty, from an EQ
file (Equalizer APO's lines, a Room EQ Wizard export, a Peace preset: read as Equalizer APO plays them,
eq\\eqtext.py), from pasted lines, from a device's profile or as a copy of the EQ shown (Start from, then Start). It's a
run of its own ("manual", one result), so everything a result has works for it; begun from a profile, Use on device
can update that profile.
EqResult is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts.
"""
import os
import tempfile

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

import textfile
from ui import bubble
from ui.eq_page_parts import MODE_SHORT, and_list, file_base_name, modal, update_row_words, use_menu_order

# By hand's Start from: an EQ's sources in the order every such list has (.claude/notes/UI-RULES.md 16), each with the
# note under the box; then each device's profile ("profile:<id>"; "profile:" when there's none yet)
HAND_SOURCES = (("empty", "An empty EQ", "Add filters on the EQ graph (double-click where you want a filter) or with "
                 "Add filter."),
                ("copy", "A copy of the selected EQ", "A copy of the EQ on the result card: you change the copy, not the "
                 "EQ."),
                ("file", "An EQ file", "Equalizer APO, AutoEq, Room EQ Wizard or Peace: you select the file when you "
                 "click Start."),
                ("paste", "Pasted filters", "Equalizer APO lines, Room EQ Wizard filters, or one filter on each line: "
                 "you paste them when you click Start."))


class EqResult:
    """Make an EQ's run and result."""

    # ---------------------------------------------------------------- running
    def run(self, retry=None):
        """Run with the settings; retry: {"filters", "add"} (Best fit from the filters shown, this run only)."""
        if not self.curves:
            bubble.tell(None, "Add a target and one or more measurements first.", near=self.run_btn)
            return
        if retry is not None and not retry["filters"]:
            bubble.tell(None, "There are no filters to start from: add a filter, or enable a filter.",
                        near=self.retry_btn)
            return
        if self.S["auto"]["enabled"]:
            self.refresh_auto()  # (the values for exactly these settings)
        self.set_way("auto", remember=False)  # (its progress and Cancel are Automatically's: a Retry from an EQ by hand)
        body = {"settings": self.S, "mode": "best_fit" if retry else self.S["mode"], "analysis": self.analysis}
        if retry:
            body["retry"] = retry
        r = self.svc.call("/api/run", body)
        if r.get("error"):
            QMessageBox.warning(self, "Calculate", r["error"])
            return
        self.run_btn.setEnabled(False)
        self.queue_btn.setEnabled(False)  # (a queue started now failed every pair: one run at a time)
        self.retry_btn.setEnabled(False)
        self.cancel_btn.show()
        self.progress.setValue(0)
        self.progress.show()
        self.say_progress("In progress…")
        if retry:  # (the page follows the job, UI-RULES 30: Retry is on the result card, its progress under Run)
            self._scroll_to(self.progress)
        self._run_view = self._scroll_value()  # (moved from here meanwhile: the result isn't scrolled to after)
        self._poll.start()

    def say_progress(self, text):
        """The line under Run: shown only while it says something (empty, it was a band of room under Run)."""
        self.progress_text.setText(text)
        self.progress_text.setVisible(bool(text))

    def _poll_job(self):
        j = self.svc.call("/api/job")
        total = j.get("total") or 0
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(j.get("done") or 0)
        self.say_progress(f"{j.get('message') or ''}" + (f" · {round(j['elapsed'])} s" if j.get("elapsed") else ""))
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
            self.say_progress(f"Done in {j['result'].get('seconds')} s.")
            self.name_edit.clear()
            self.show_result(j["result"]["pick"])
            self.add_to_history(False)
            if self._scroll_value() == getattr(self, "_run_view", None):  # (not if you scrolled meanwhile: a run
                QTimer.singleShot(0, self, lambda: self._scroll_to(self.result_box))  # takes 7-20 s, UI-RULES 30)
        elif j.get("status") == "error":
            self.say_progress("")
            QMessageBox.warning(self, "Calculate", j.get("message") or "The app did not make an EQ.")
        elif j.get("status") == "cancelled":
            self.say_progress("Canceled.")

    # ---------------------------------------------------------------- the result
    def show_result(self, rid):
        run = self.run_result
        if not run:
            return
        self.sel = run["_sel"] = rid
        r = next(x for x in run["results"] if x["id"] == rid)
        manual = run.get("mode") == "manual"
        # (a filter switched off stays off: an EQ by hand can begin with some, from its file or a copy. An EQ by hand
        # keeps its filters as you left them, shown again from Runs this session; Revert goes back to how it began)
        same = lambda fs: [{"enabled": f.get("enabled", True) is not False, "type": f.get("type") or "PK",
                            "freq": f["freq"], "gain": f["gain"], "q": f["q"]} for f in fs]
        self.ORIG = same(r.get("start", r["filters"]) if manual else r["filters"])
        self.EDIT = same(r["filters"])
        made_for = f" · made for {run.get('device')} → {run.get('target_name')}"
        if manual:
            self.res_sub.setText((f"From History ({run['when']}) · " if run.get("history") else "")
                                 + self.run_label(run, r) + (made_for if run.get("device") and run.get("target_name") else ""))
        else:
            self.res_sub.setText((f"From History ({run['when']})" if run.get("history") else f"#{run.get('n', 1)}")
                                 + f" · {self.run_label(run, r)}" + made_for)
        self.count_lab.setVisible(not manual)  # (one EQ: no other filter counts to choose from)
        self.count_combo.setVisible(not manual)
        self.hand_close.setVisible(manual)
        self.revert_btn.setToolTip("Use the initial filters again (the filters that you started with)" if manual else
                                   "Use the initial filters again (as the app made them)")
        self.listen.show()  # (an EQ by hand can be heard without a measurement too)
        note = self.pick_note(run, r)
        self.pick_lab.setText(note)
        self.pick_lab.setVisible(bool(note))
        self.chips["error"].setToolTip("The average difference between the measurement with the EQ and the target, in "
                                       "the error range (a lower value is better)")
        self.chips["preamp"].setToolTip("To prevent clipping, the app decreases the gain of the full EQ by this value "
                                        "(the sum of the filter gains where they overlap)")
        # the best result for each filter count (the pick for its own count), as AutoEQ Local's chips (an EQ by hand
        # has one result, and no error worked out by a run: none to list)
        by_n = {}
        for x in [] if manual else run["results"]:
            had = by_n.get(x["n_filters"])
            if not had or x["id"] == run["pick"] or (had["id"] != run["pick"] and x["rms"] < had["rms"]):
                by_n[x["n_filters"]] = x
        shown = next((x for x in run["results"] if x["id"] == rid), None)
        if shown and not manual:  # (one chosen in All results… or Compare: its own count's entry, so the list says what's shown)
            by_n[shown["n_filters"]] = shown
        self.count_combo.clear()
        for n, x in sorted(by_n.items()):
            self.count_combo.addItem(f"{n} filter{'' if n == 1 else 's'}  ·  {x['rms']:.2f} dB"
                                     + ("  ✓ selected for you" if x["id"] == run["pick"] else ""), x["id"])
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
            return f"The sound is {r['ear']:.2f} dB or less from the target at all frequencies (as the ear hears it)" + (
                f". The largest difference is near {hz(r['ear_at'])}." if r.get("ear_at") and r["ear"] > lim else ".")
        if case == "target":
            return (f"The same sound as the target: {r['ear']:.2f} dB or less from it at all frequencies, as the ear hears "
                    f"it (the limit: {lim:g} dB). This EQ has the minimum number of filters for this sound.")
        best = min((x for x in run["results"] if x.get("ear") is not None), key=lambda x: x["ear"], default=r)
        return (f"No EQ can be the same as the target here: your EQ app has limits, or the filters cannot follow small "
                f"changes in the target. The nearest EQ is {best['ear']:.2f} dB from the target near "
                f"{hz(best.get('ear_at'))}. "
                + ("This EQ is the nearest one." if best["id"] == r["id"] else
                   "This EQ has the same sound as the nearest one, with a smaller number of filters."))

    # ---------------------------------------------------------------- runs this session (results.js RUNS)
    def use_these_settings(self):
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
        self.status("The app copied the values into Website AutoEQ: one set.", 6000)

    def open_all_results(self):
        """Every result of the run shown, and the error grid (ui/all_results.py)."""
        from ui.all_results import AllResults
        if self.current()[1]:
            modal(AllResults(self))

    def open_queue(self):
        """Several EQs in one go (ui/queue_window.py)."""
        from ui.queue_window import QueueWindow
        if not self.groups or not self.inputs.get("targets"):
            bubble.tell(None, "Add a target and one or more measurements first.", near=self.queue_btn)
            return
        modal(QueueWindow(self))

    def open_compare(self):
        """Two EQs side by side (ui/compare_results.py)."""
        from ui.compare_results import CompareResults, options
        if len(options(self)) < 2:  # (what's needed first: a bubble at the button, as Calculate's, UI-RULES 25)
            bubble.tell(None, "There is no other EQ to compare with. Calculate again, or select a different number of "
                        "filters or an EQ from History.", near=self.cmp_btn)
            return
        modal(CompareResults(self))

    def keep_run(self, run):
        self.session_runs = [x for x in self.session_runs if x is not run][-19:] + [run]  # (the last 20)

    def render_runs(self):
        c = self.runs_combo
        c.clear()
        for run in reversed(self.session_runs):
            best = min((x["rms"] for x in run["results"] if x.get("rms") is not None), default=None)
            c.addItem((f"From History ({run['when']})" if run.get("history") else f"#{run.get('n', 1)}")
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
        self.show_run(run)

    def show_run(self, run):
        """A run of this session on the result card again, or none (run None): the card hidden and the graph and Listen
        without an EQ, as before any run (the card alone was hidden: its EQ stayed on the graph, handles and all, and in
        Listen)."""
        if run is not None:
            self.run_result = run
            self.name_edit.clear()
            self.show_result(run["_sel"] if run.get("_sel") is not None else run["pick"])  # (result 0 is a result)
            return
        self.run_result, self.sel, self.EDIT, self.ORIG = None, None, [], []
        self.name_edit.clear()
        self.result_box.hide()
        self.render_runs()
        if not self.curves:  # (an EQ by hand showed Listen without a measurement; with neither, as the page opened)
            self.listen.stop()
            self.listen.hide()
        self.listen.refresh()
        self.draw()

    def remove_run(self):
        """Remove: the run shown off this session's runs, with Undo in the window's line (UI-RULES 20: an EQ by hand
        you'd changed went with it, for good)."""
        run = self.run_result
        at = next((i for i, x in enumerate(self.session_runs) if x is run), None)
        self.session_runs = [x for x in self.session_runs if x is not run]
        self.show_run(self.session_runs[-1] if self.session_runs else None)
        if run is not None and at is not None:
            what = "From History" if run.get("history") else f"#{run.get('n', 1)}"
            self.status(f"You removed “{what} · {MODE_SHORT.get(run['mode'], run['mode'])}” from EQs that you made.",
                        undo=lambda: self._put_run_back(run, at))

    def _put_run_back(self, run, at):
        self.session_runs.insert(min(at, len(self.session_runs)), run)
        self.show_run(run)

    def close_manual(self):
        """Close, on an EQ by hand: back to what was shown when it began (that run, else the last one left, else none:
        the page as it was). Changed, it stays in Runs this session to come back to; empty, it goes (nothing in it to
        lose); as it began (pasted, from a file, a profile or a copy), it goes with Undo in the window's line, as
        Remove's (UI-RULES 20: pasted filters were gone for good)."""
        run, _r = self.current()
        if not run or run.get("mode") != "manual":
            return
        at = next((i for i, x in enumerate(self.session_runs) if x is run), None)
        dropped, had = not self.EDIT or not self.edited(), bool(self.EDIT)
        if dropped:
            self.session_runs = [x for x in self.session_runs if x is not run]
        mine, before = getattr(self, "hand_before", None) or (None, None)
        others = [x for x in self.session_runs if x is not run]
        back = before if mine is run and any(x is before for x in others) else (others[-1] if others else None)
        self.show_run(back)
        if dropped and had and at is not None:
            self.status(f"You closed “#{run.get('n', 1)} · {MODE_SHORT['manual']}”.",
                        undo=lambda: self._put_run_back(run, at))

    # ---------------------------------------------------------------- the filters being edited
    def enabled_filters(self):
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
        act, c = self.enabled_filters(), self.curves
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
        manual = run.get("mode") == "manual"
        # (the pick's one name everywhere: "picked for you", as the filter counts' list says it; it was "recommended"
        # here, "pick" and "(picked)" in the windows)
        tag = "" if manual else "selected for you" if r["id"] == run["pick"] else "lowest error" if r["id"] == run["best"] else ""
        self.res_title.setText(MODE_SHORT.get(run["mode"], run["mode"]) + (f"  ·  {tag}" if tag else "")
                               + ("  ·  edited" if ed else ""))
        if manual:  # (its filters as they are now: kept when another run is shown, and on its lines in the lists)
            r["filters"], r["n_filters"] = [dict(f) for f in self.EDIT], st["n"]
            note = self.manual_note(st)
        elif ed:  # (the run's line was about the filters before the edit)
            note = (f"Edited: the sound is {st['ear']:.2f} dB or less from the target at all frequencies, as the ear "
                    f"hears it (the limit: {run.get('ear_db') or 0.25:g} dB)." if run.get("pick_case") and st["ear"] is not None else "")
        else:
            note = self.pick_note(run, r)
        self.pick_lab.setText(note)
        self.pick_lab.setVisible(bool(note))
        self.show_numbers(st)
        site = run["mode"].startswith("site") and r.get("rows") is not None
        self.site_row.setVisible(site)
        if site:
            self.site_text.setText(
                "Type in the AutoEQ panel of squiglink: Filter rows <b>{rows}</b> · Frequency Range <b>{freq_low}</b> to "
                "<b>{freq_high}</b> · Gain Range <b>{gain_min}</b> to <b>{gain_max}</b> · Q Range <b>{q_min}</b> to "
                "<b>{q_max}</b> → the website shows Pre-amp <b>{pre:.1f} dB</b>".format(
                    pre=float(r.get("preamp") or 0), **{k: r.get(k, "–") for k in ("rows", "freq_low", "freq_high",
                                                                                      "gain_min", "gain_max", "q_min", "q_max")})
                + (" <i>(because you edited the filters, the website will not make these values)</i>" if ed else ""))
            self.site_use.setVisible(run["mode"] == "site_sweep")
        self.revert_btn.setEnabled(ed)  # (always there, off until an edit: nothing moves when you edit, UI-RULES 25)
        if hasattr(self, "listen"):
            self.listen.refresh()
        if not self.name_edit.text().strip() or self.name_edit.property("auto") is not False:
            self.name_edit.setText(self.auto_name())
            self.name_edit.setCursorPosition(0)  # (the name's start in sight: a long one showed only its end)
            self.name_edit.setProperty("auto", True)
        self.draw()
        self.sync_trial()  # (the EQ shown being tried on a device: the change plays there too)

    def show_numbers(self, st):
        """The result's numbers (its chips) and the sliders' pre-amp, from stats(): after any edit, and while a handle
        on the EQ graph is held (ui/eq_page_handles.py)."""
        self.chips["error"].setText(f"Error  {st['rms']:.2f} dB" if st["rms"] is not None else "Error  –")
        c = self.curves or {}
        self.err_noeq.setText(f"Without EQ: {c['no_eq_rms']:.2f} dB" if c.get("no_eq_rms") is not None else "")
        self.chips["preamp"].setText(f"Pre-amp  {self.preamp_text(st['preamp_raw'])} dB")
        self.chips["boost"].setText(f"Maximum gain  +{st['max_boost']:.1f} dB")
        self.chips["maxq"].setText(f"Maximum Q  {st['max_q']:g}" if st["max_q"] else "Maximum Q  –")
        self.editor.set_preamp_text(self.preamp_text(st["preamp_raw"]))

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
        self.request_live_graph()

    def sort_filters(self):
        self.EDIT.sort(key=lambda f: f["freq"])
        self.editor.rebuild()
        self.live_update()
        self.request_live_graph()

    def undo_all(self):
        self.EDIT[:] = [dict(f) for f in self.ORIG]
        self.editor.rebuild()
        self.live_update()
        self.request_live_graph()

    def auto_name(self):
        run, r = self.current()
        if run.get("mode") == "manual":  # ("<IEM> to <target> - by hand 5f", or what it began from: "KZ ZSN - by hand 5f")
            base = (f"{run['device']} to {run['target_name']}" if run.get("device") and run.get("target_name")
                    else run.get("source_name") or "New EQ")
            return f"{base} - manual {len(self.enabled_filters())}f"
        lay = next((l for l in self.meta.get("layouts", []) if l["key"] == r.get("layout") and l["key"] != "any"), None)
        return file_base_name(run.get("device") or "EQ", run.get("target_name") or "target", lay["name"] if lay else "",
                              run["mode"], len(self.enabled_filters()) if self.EDIT else r["n_filters"]) + \
            (" edited" if self.EDIT and self.edited() else "")

    def save_filters(self):
        run, r = self.current()
        if not r:
            return
        if not self.enabled_filters():
            bubble.tell(None, "There are no filters to save: all the filters are off.", near=self.save_btn)
            return
        from eq import exports
        files = any(self.S["export"].get(k) for k in exports.FORMATS)
        if not files and not self.S["export"].get("report"):
            bubble.tell(None, "No file type is selected: select your EQ app, or select the file types in More settings "
                        "› Saved files.", near=self.save_btn)
            return
        name = self.name_edit.text().strip() or self.auto_name()
        written, notes, kept = [], "", False
        if files:
            # (switched-off filters go too: an Equalizer APO file keeps them as OFF lines, as AutoEQ Local's did)
            body = {"settings": self.S, "filters": [dict(f) for f in self.EDIT if f.get("freq") and f.get("q")],
                    "preamp": self.stats()["preamp_raw"], "name": name}
            res = self.svc.call("/api/export", body)
            if res.get("exists"):
                if not self._replace_ok(res["exists"], "Save filters"):
                    return
                res = self.svc.call("/api/export", {**body, "replace": True})
            if res.get("error"):
                QMessageBox.warning(self, "Save filters", res["error"])
                return
            written = [os.path.basename(p) for p in (res.get("written") or {}).values()]
            notes = " ".join(res.get("notes") or [])
        if self.S["export"].get("report") and self.curves:  # (by hand, with no measurement: no report to make)
            path = self.report(open_it=False)
            if path:
                written.append(os.path.basename(path))
            else:
                kept = True
        if not written:
            return
        self.add_to_history(True)
        self.status(f"The app saved {', '.join(written)} in your Saved EQs folder." + (f" {notes}" if notes else "")
                    + (" The report with that name did not change: change the File name to save a different report "
                       "in the same folder." if kept else ""),
                    10000)

    def _replace_ok(self, names, command):
        """Replace files already in Saved EQs? Titled by the command asking (Save filters, Report); No the default, as a
        file replaced can't be had back (.claude/notes/UI-RULES.md 17; the tracer's Save .txt asks the same way)."""
        return QMessageBox.question(self, command, "These files are in your Saved EQs folder:\n\n" + "\n".join(names)
                                    + "\n\nReplace them? (No keeps them. To save new files in the same folder, change the File name.)",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def report(self, open_it=True):
        """The HTML report of the result shown (and of up to two of your EQs to compare on the graph), as AutoEQ
        Local's export.js reportBody: its path, or None when one of that name was kept or it failed."""
        run, r = self.current()
        if not r:
            return None
        if not self.curves:  # (an EQ by hand with no measurement chosen: nothing to draw it on)
            bubble.tell(None, "A report shows the EQ on a measurement and its target: select them first (Target and "
                        "Measurement, above).", near=self.report_btn)
            return None
        title = MODE_SHORT.get(run["mode"], "EQ") + (" (edited)" if self.edited() else "")
        fields = [["Filter rows", r.get("rows")], ["Frequency range", f"{r.get('freq_low')} to {r.get('freq_high')}"],
                  ["Gain range", f"{r.get('gain_min')} to {r.get('gain_max')}"],
                  ["Q range", f"{r.get('q_min')} to {r.get('q_max')}"]] if run["mode"].startswith("site") else []
        # (the report is drawn on the files the EQ was made for, while they're in the app; else on the measurement
        # chosen now, and it says so)
        mf, tf = run.get("meas_files"), run.get("target_file")
        names = {m["name"] for m in self.inputs["measurements"]}
        own_files = bool(mf) and all(n in names for n in mf) and tf in self.inputs["targets"]
        made_for, here = run.get("device"), (self.curves or {}).get("name")
        other = (f" Made for the {made_for}. This report shows it on the {here}." if not own_files and made_for and here
                 and made_for != here else "")
        cards = [{"title": title, "badge": "selected for you" if r["id"] == run.get("pick") else "", "fields": fields,
                  "text": self.run_label(run, r) + "." + other, "filters": self.enabled_filters()}]
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
            if not self._replace_ok(res["exists"], "Report"):
                return None
            res = self.svc.call("/api/report", {**body, "replace": True})
        if res.get("error"):
            QMessageBox.warning(self, "Report", res["error"])
            return None
        if open_it:
            self.status(f"Report: {os.path.basename(res['path'])} (in your Saved EQs folder).", 8000)
        return res.get("path")

    # ---------------------------------------------------------------- an EQ made by hand
    # ---------------------------------------------------------------- Make the EQ's two ways
    def set_way(self, way, remember=True):
        """Make the EQ's way: "auto" (Automatically: Method, Search, Run) or "hand" (By hand: Start from, Start), its
        tab marked and only its steps shown. remember: kept for the next start (a tab you click; not a switch the app
        makes as it shows what you did: an EQ by hand begun elsewhere, a run started from the result card)."""
        way = way if way in ("auto", "hand") else "auto"
        self.way = way
        for key, b in self.way_btns.items():
            b.setChecked(key == way)
        self.way_stack.setCurrentWidget(self.auto_w if way == "auto" else self.hand_w)
        self.go_stack.setCurrentIndex(0 if way == "auto" else 1)
        if way == "hand":
            self.fill_manual_sources()  # (the profiles as they are now)
        if remember and self.sw is not None and self.sw.s.get("make_way") != way:
            self.sw.set("make_way", way, tell=False)

    def fill_manual_sources(self):
        """By hand's Start from: HAND_SOURCES, then each device's profile, A to Z, with the devices that have it (one
        line saying there's none yet when there isn't). The choice stays when it's still there."""
        c = self.hand_source
        keep = c.currentData()
        c.blockSignals(True)
        try:
            c.clear()
            for key, words, _note in HAND_SOURCES:
                c.addItem(words, key)
            profiles = list(self.sw.profiles().items()) if self.sw else []
            for pid, p in profiles:
                used = self.sw.used_by(pid)
                c.addItem(f"Profile: {p['name']}" + (f"  ·  {', '.join(used)}" if used else ""), f"profile:{pid}")
            if not profiles:
                c.addItem("A device's profile (none)", "profile:")
            # (the sources in their order on top, the profiles under them A to Z: as every list pins its special
            # choices, UI-RULES 22)
            c.sort_items(pinned=len(HAND_SOURCES))
            i = c.findData(keep) if keep is not None else -1
            c.setCurrentIndex(i if i >= 0 else 0)
        finally:
            c.blockSignals(False)
        self.manual_source_changed()

    def manual_source_changed(self):
        """The words about the source chosen (behind the ⓘ after Start from), and Start's words ("Start…" when it asks
        first: a file, pasted lines, UI-RULES 11)."""
        key = self.hand_source.currentData() or "empty"
        note = next((n for k, _w, n in HAND_SOURCES if k == key), "")
        if key == "profile:":
            note = "No profiles: add a profile in Devices (Add a profile). Then start from it here."
        elif key.startswith("profile:"):
            note = "A device's profile: Use on device › Update writes your changes into it."
        self.hand_src_note.setText(note + " Then change its filters on the EQ graph (drag a handle) or in the table below "
                                   "Your result.")
        self.hand_start.setText("Start…" if key in ("file", "paste") else "Start")

    def start_from_source(self):
        """Start (By hand): an EQ by hand from the source chosen in Start from. What's needed first is said in a box
        (UI-RULES 25: no EQ on the result card to copy, no profile yet)."""
        key = self.hand_source.currentData() or "empty"
        if key == "empty":
            self.start_manual([], "from an empty EQ")
        elif key == "copy":
            if not self.current()[1]:
                bubble.tell(None, "There is no EQ on the result card: calculate an EQ, or start from a different item.",
                            near=self.hand_start)
                return
            self.manual_from_shown()
        elif key == "file":
            self.manual_from_file()
        elif key == "paste":
            self.manual_from_paste()
        elif key == "profile:":
            bubble.tell(None, "No profiles: add a profile in Devices (Add a profile). Then start from it here.",
                        near=self.hand_start)
        else:
            self.manual_from_profile(key.split(":", 1)[1])

    def start_manual(self, filters, source, name="", profile=None, left_out=()):
        """An EQ of your own on the result card, made by hand from these filters (none: start empty), as a run of its
        own in this session's runs: Save, Use on device, Listen and the rest take it as they take a run's. It's for
        the measurement and target chosen, if any (its error then shows); source: where it began ("from an empty EQ",
        "from KZ.txt"); profile: the profile it was read from (Use on device can then update it)."""
        c = self.curves or {}
        self.runs += 1
        filters = [{"enabled": f.get("enabled", True) is not False, "type": f.get("type") or "PK", "freq": f["freq"],
                    "gain": f["gain"], "q": f["q"]} for f in filters]
        res = {"id": 1, "filters": filters, "start": [dict(f) for f in filters],
               "n_filters": sum(1 for f in filters if f["enabled"]), "rms": None, "max_boost": 0}
        run = {"mode": "manual", "results": [res], "pick": 1, "best": 1, "n": self.runs, "settings": {}, "seconds": 0,
               "source": source, "source_name": name, "profile": profile, "left_out": list(left_out),
               "device": c.get("name"), "target_name": c.get("target_name")}
        if c:
            run["target_file"] = self.inputs.get("active_target")
            run["meas_files"] = [m["name"] for m in self.inputs["measurements"] if m["included"]]
        self.hand_before = (run, self.run_result)  # (what its Close goes back to)
        self.set_way("hand", remember=False)  # (begun from Profiles or the Guide too: the card shows how it was made)
        self.run_result = run
        self.keep_run(run)
        self.name_edit.clear()
        self.show_result(1)
        QTimer.singleShot(0, self, lambda: self._scroll_to(self.result_box))

    def _scroll_to(self, w):
        from PySide6.QtWidgets import QScrollArea
        area = next(iter(self.findChildren(QScrollArea)), None)
        if area is not None and w.isVisible():
            area.ensureWidgetVisible(w, 0, 40)

    def _scroll_value(self):
        """Where the page is scrolled to now (None before it's made)."""
        from PySide6.QtWidgets import QScrollArea
        area = next(iter(self.findChildren(QScrollArea)), None)
        return area.verticalScrollBar().value() if area is not None else None

    def manual_note(self, st):
        """Under an EQ by hand's numbers: how to add a filter while it has none, and how it sounds next to the target."""
        parts = []
        if not self.EDIT:
            parts.append("No filters: double-click the EQ graph (below the graph) where you want a filter, or click Add "
                         "filter.")
        if st["ear"] is not None:
            parts.append(f"The sound is {st['ear']:.2f} dB or less from the target at all frequencies, as the ear hears "
                         "it.")
        return " ".join(parts)

    def manual_from_file(self):
        import paths
        start = paths.SAVED_EQS if os.path.isdir(paths.SAVED_EQS) else os.path.expanduser("~")
        f, _ = QFileDialog.getOpenFileName(self, "An EQ file", start, "EQ files (*.txt *.peace *.cfg *.csv);;All files (*)")
        if not f:
            return
        try:
            text = textfile.read(f)
        except OSError as e:  # (no rights, an offline OneDrive file, one another program holds)
            QMessageBox.warning(self, "Manually", f"AutoEQ Studio cannot read the file: {e}")
            return
        self._manual_from_text(text, f"from {os.path.basename(f)}", os.path.splitext(os.path.basename(f))[0])

    def manual_from_paste(self):
        from ui.eq_page_parts import paste_dialog
        got = paste_dialog(self, "Paste filters", "For example, New EQ", "Equalizer APO lines, Room EQ Wizard "
                           "filters, or one filter on each line as “frequency gain Q”", "Start")
        if got:
            self._manual_from_text(got[1], "pasted", got[0] or "Pasted EQ")

    def manual_from_profile(self, pid):
        """A device's profile as an EQ by hand (Profiles' Edit in Make an EQ too); Use on device can update it."""
        p = self.sw.profiles().get(pid)
        if not p:
            return
        try:
            text = textfile.read(os.path.join(self.sw.apo.profiles, p["file"]))
        except OSError as e:
            QMessageBox.warning(self, "Manually", f"AutoEQ Studio cannot read the profile's file: {e}")
            return
        self._manual_from_text(text, f"from the profile “{p['name']}”", p["name"], profile=pid)

    def manual_from_shown(self):
        run, r = self.current()
        if not r:
            return
        what = "your manual EQ" if run.get("mode") == "manual" else \
            f"#{run.get('n', 1)} ({MODE_SHORT.get(run['mode'], 'EQ')})"
        own = self.name_edit.text().strip() if self.name_edit.property("auto") is False else ""
        self.start_manual([dict(f) for f in self.EDIT], f"a copy of {what}", own or (run.get("source_name") or ""))

    def _manual_from_text(self, text, source, name, profile=None):
        """An EQ by hand from a file's or pasted text, read as Equalizer APO plays it (eq\\eqtext.py): what it has that
        an EQ here can't (other filter types, a graphic EQ …) is said, never dropped without a word."""
        r = self.svc.call("/api/filters/read", {"text": text, "settings": self.S})
        if r.get("error"):
            QMessageBox.warning(self, "Manually", r["error"])
            return
        left = r.get("left_out") or []
        if not r.get("filters"):
            QMessageBox.information(self, "Manually", (f"This EQ has no items that you can edit here: {' · '.join(left)}."
                                    if left else
                                    "It has no filters. AutoEQ Studio can read:\n"
                                    "• Equalizer APO lines (Filter 1: ON PK Fc 100 Hz Gain 3 dB Q 1)\n"
                                    "• Room EQ Wizard filters\n• a Peace preset\n"
                                    "• one filter on each line as frequency, gain and Q.") + "\n\nAn EQ here has peaking "
                                    "and shelf filters.")
            return
        self.start_manual(r["filters"], source, name, profile, left)
        if left:
            QMessageBox.information(self, "Manually", f"These items are not in “{name}” (an EQ here has only peaking and "
                                    f"shelf filters): {' · '.join(left)}.")
        else:
            n = len(r["filters"])
            self.status(f"“{name}”: {n} filter{'' if n == 1 else 's'}, read as Equalizer APO reads "
                        f"{'it' if n == 1 else 'them'}. The app calculates the pre-amp for you.", 8000)

    # ---------------------------------------------------------------- Use on device
    def _fill_use_menu(self):
        m = self.use_menu
        m.clear()
        run, r = self.current()
        if not r:
            m.addAction("Calculate first").setEnabled(False)
            return
        if not self.sw.apo.found:
            m.addAction("Equalizer APO is not installed (refer to Devices)").setEnabled(False)
            return
        m.setToolTipsVisible(True)
        pid = run.get("profile")
        profiles = self.sw.profiles()
        if pid in profiles:  # (an EQ by hand from a profile: back into it, or as a new one below)
            self._update_row(m, pid)
            m.addSeparator()
        from switcher.core import shown
        keys, ups = use_menu_order(self.sw, pid)  # (as the Devices screen lists them; the Guide's picture the same)
        for key in keys:
            rec, d = self.sw.record(key), self.sw.device(key)
            where = "active" if key == self.sw.playing_key else "connected" if d and d.connected else "not connected"
            # (the condition in a column at the right, as a menu's keys: the UI audit, 2026-11-08; Qt reads one "&" as
            # a key's mark, so "TV (R&D Audio)" showed as "TV (RD Audio)")
            a = m.addAction(f"{shown(rec).replace('&', '&&')}\t{where}")
            a.triggered.connect(lambda _=False, k=key: self.use_on(k))
        if not keys:
            m.addAction("No playback devices").setEnabled(False)
        if profiles:  # (into a profile you have: the ones that are on, one click; all of them, A to Z, in a submenu)
            m.addSeparator()
            for on in ups:  # (every device's, in the device rows' sequence)
                self._update_row(m, on)
            u = m.addMenu("Update a profile")
            u.setToolTipsVisible(True)
            for other, _ in sorted(profiles.items(), key=lambda x: x[1]["name"].lower()):
                self._update_row(u, other, quoted=False)
        live = [d.key for d in self.sw.devices if d.connected]
        if live:  # (hear it in every app for a few minutes before keeping it)
            m.addSeparator()
            t = m.addMenu("Use for 5 minutes on")
            t.setToolTipsVisible(True)
            for key in live:
                a = t.addAction(shown(self.sw.record(key)).replace("&", "&&")
                                + ("\tactive" if key == self.sw.playing_key else ""))
                a.setToolTip("The EQ plays in all apps for 5 minutes. Then, if you do not select Keep it, the device "
                             "uses its usual EQ again.")
                a.triggered.connect(lambda _=False, k=key: self.start_trial(k))

    def _update_row(self, menu, pid, quoted=True):
        """One row that puts the EQ shown into this profile (Use on device): Update “its name” (quoted; the submenu's
        rows: the name only), where it's on in the keys' column (the two cut to their room: update_row_words), what it
        does in its tooltip (the whole name when it was cut, every device); off for the profile this EQ came from when
        it can't show all of it."""
        from switcher.core import shown
        from ui.window_parts import profile_line
        run, _ = self.current()
        keys = self.sw.on_for(pid)
        name = self.sw.profiles()[pid]["name"]
        menu.ensurePolished()  # (the menu's own font, as it shows)
        text, where, cut = update_row_words(menu.fontMetrics(), name, [shown(self.sw.record(k)) for k in keys], quoted)
        a = menu.addAction(f"{text}\t{where}".replace("&", "&&"))  # (Qt reads one "&" as a key's mark)
        if pid == run.get("profile") and run.get("left_out"):
            a.setEnabled(False)
            why = ("its file has items that this EQ cannot show (" + " · ".join(run["left_out"]) + "): use this EQ as a "
                   "new profile below")
            a.setToolTip(f"The profile “{name}”: {why}" if cut else why[0].upper() + why[1:])  # (cut: its whole name)
            return a
        who = self._on_sentences(keys) or "No device has this profile on."
        a.setToolTip((f"The profile “{name}” changes to this EQ." if cut else "The profile changes to this EQ.")
                     + f" {who} The EQ of the profile at this time: {profile_line(self.sw.profiles()[pid])}.")
        a.triggered.connect(lambda _=False, pid=pid: self.update_profile(pid))
        return a

    def _on_sentences(self, keys):
        """What the devices that have a profile on (keys) do after its update, a sentence for each group, true for
        each device (the same words in the message and in the row's tooltip, each sentence with "the new EQ", so no
        "it" can be the EQ or the device): the ones that use it immediately, the ones with an EQ for 5 minutes or
        their EQ off to compare (APO's file keeps that EQ for them), the ones not connected, and the ones without
        Equalizer APO (as use_on says). When Equalizer APO doesn't include the app, no device uses it immediately: that
        comes first, and the others use it "after that" (the ones not connected "after that, when you connect it"). ""
        with no keys."""
        from switcher.core import shown
        if not keys:
            return ""
        held = {x["key"] for x in (self.sw.trial, self.sw.compare) if x}
        now, later, away, no_apo = [], [], [], []
        for k in keys:
            d = self.sw.device(k)
            (later if k in held else away if not (d and d.connected) else no_apo if not d.apo else now).append(
                shown(self.sw.record(k)))
        out = []
        unused = not self.sw.apo.includes_studio()
        if unused:  # (APO reads none of the app's files: as use_on says it)
            out.append("Equalizer APO does not use AutoEQ Studio: click Add AutoEQ Studio to APO… on the Devices screen.")
        if now:
            out.append(f"{and_list(now)} {'uses' if len(now) == 1 else 'use'} the new EQ "
                       f"{'after that' if unused else 'immediately'}.")
        if later:
            one = len(later) == 1
            out.append(f"{and_list(later)} {'has' if one else 'have'} an EQ for 5 minutes, or "
                       f"{'its' if one else 'their'} EQ off to compare. {'It uses' if one else 'They use'} the new EQ "
                       "after that.")
        if away:
            one = len(away) == 1
            out.append(f"{and_list(away)} {'uses' if one else 'use'} the new EQ {'after that, ' if unused else ''}"
                       f"when you connect {'it' if one else 'them'}.")
        if no_apo:
            out.append(f"Equalizer APO is not installed on {and_list(no_apo)} (refer to Devices).")
        return " ".join(out)

    def _apo_text(self, title):
        """The EQ shown, as Equalizer APO text (as edited, with its pre-amp), or None (said)."""
        res = self.svc.call("/api/text", {"settings": self.S, "filters": self.enabled_filters(),
                                          "preamp": self.stats()["preamp_raw"]})
        if res.get("error"):
            QMessageBox.warning(self, title, res["error"])
            return None
        return res["apo"]

    def start_trial(self, key, minutes=5):
        """The EQ shown plays on a device for a few minutes, in every app (Devices' trial: switcher/core.py); while it
        does, your changes to it play there at once (ui/eq_page_handles.py's sync_trial)."""
        from switcher.core import shown
        run, r = self.current()
        text = self._apo_text("Use for 5 minutes")
        if text is None:
            return
        name = (self.name_edit.text().strip() or self.auto_name())[:80]
        try:
            self.sw.try_eq(key, text, name, minutes)
        except OSError as e:
            QMessageBox.warning(self, "Use for 5 minutes", str(e))
            return
        self._trying = {"key": key, "run": id(run), "rid": r["id"]}
        extra = "" if self.sw.apo.includes_studio() else (" (Equalizer APO does not use AutoEQ Studio: click Add AutoEQ Studio "
                                                  "to APO… on Devices.)")
        self.window().render_all() if hasattr(self.window(), "render_trial") else None
        self.status(f"“{name}” plays on {shown(self.sw.record(key))} for {minutes} minutes, with your changes while you "
                    f"make them. Select Keep it or Do not keep it in the bar at the top, or in the menu of the tray "
                    f"icon.{extra}", 10000)

    def use_on(self, key):
        """The EQ shown becomes a profile of this device, switched on (APO applies it while the device plays)."""
        from switcher.core import shown
        run, r = self.current()
        text = self._apo_text("Use on device")
        if text is None:
            return
        name = (self.name_edit.text().strip() or self.auto_name())[:80]
        try:
            pid = self._with_temp_file(text, name, lambda path: self.sw.import_profile(path, name))
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Use on device", str(e))
            return
        self.sw.add_to_device(key, pid, switch_on=True)
        rec, d = self.sw.record(key), self.sw.device(key)
        extra = ""
        if not self.sw.apo.includes_studio():
            extra = " Equalizer APO does not use AutoEQ Studio: click Add AutoEQ Studio to APO… on the Devices screen."
        elif d and not d.apo:
            extra = " Equalizer APO is not installed on this device (refer to Devices)."
        self.status(f"“{self.sw.profile_name(pid)}” is on for {shown(rec)}.{extra}", 10000)

    def update_profile(self, pid):
        """The EQ shown (a result, or an EQ by hand begun from this profile) written into a profile that you have: its
        name, its file's name and its devices stay, and the devices that have it switched on hear it at once (Equalizer
        APO reads the file again). No question first: the message has Undo (20 s, Ctrl+Z), which puts the old file and
        record back. From a different result, the profile's From becomes that result's name (as Use on device's new
        profiles); its own EQ by hand keeps it. The message says what each device that has it on does
        (_on_sentences)."""
        run, _ = self.current()
        text = self._apo_text("Update the profile")
        if text is None:
            return
        name = self.sw.profile_name(pid) or "EQ"
        own = pid == run.get("profile")  # (this EQ came from the profile: its From stays)
        file_name = name if own else (self.name_edit.text().strip() or self.auto_name())[:80]
        try:
            before = self._with_temp_file(text, file_name, lambda path: self.sw.update_profile(
                pid, path, source=None if own else os.path.abspath(path)))
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Update the profile", str(e))
            return
        words = f"The app updated “{name}”. " + (self._on_sentences(self.sw.on_for(pid)) or "No device has it on.")

        def undo():
            now = self.sw.profile_name(pid) or name  # (renamed meanwhile: its name now)
            try:
                why = self.sw.restore_profile(pid, before)
            except OSError as e:
                QMessageBox.warning(self, "Update the profile", str(e))
                return
            self.status({"": f"“{now}” has its previous EQ again.",
                         "deleted": f"You deleted “{now}” in Profiles: Undo is not possible.",
                         "changed": f"The file of “{now}” changed after the update: Undo is not possible."}[why])
        self.status(words, undo=undo)

    @staticmethod
    def _with_temp_file(text, name, fn):
        """fn(path) with the EQ's text in a file of its own for a moment (a profile is made from a file)."""
        path = os.path.join(tempfile.mkdtemp(prefix="autoeq-studio-"), textfile.safe_name(name, "EQ", 80) + ".txt")
        try:
            textfile.write_atomic(path, text, newline="")  # (its own CRLF: text mode wrote CR CR LF into profiles)
            return fn(path)
        finally:
            try:
                os.remove(path)
                os.rmdir(os.path.dirname(path))
            except OSError:
                pass
