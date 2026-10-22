"""Several EQs in one go (Make an EQ › Run several…): tick IEMs (measurements in the app) and targets, and each pair
is run in turn with the settings and method you have now (the automatic settings worked out for each pair), the
picked result saved into your Saved EQs folder under its automatic name (never over a file: " (2)" …), kept in History
and in "Runs this session". Cancel stops the run going on and the rest. Your own choice of files is put back after: the runs
use their own copy of the settings.
"""
import copy
import os

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from ui import theme


def _checklist(items, on):
    lst = QListWidget()
    for name in items:
        it = QListWidgetItem(os.path.splitext(name)[0] if name.lower().endswith((".txt", ".csv")) else name)
        it.setData(Qt.UserRole, name)
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked if name in on else Qt.Unchecked)
        lst.addItem(it)
    return lst


def _ticked(lst):
    return [lst.item(i).data(Qt.UserRole) for i in range(lst.count()) if lst.item(i).checkState() == Qt.Checked]


class QueueWindow(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.setWindowTitle("Run several")
        self.resize(900, 720)
        self.jobs, self.i, self.running, self.stop = [], -1, False, False
        v = QVBoxLayout(self)
        lead = QLabel("Make an EQ for each IEM ticked with each target ticked, one after another, with the settings "
                      "and method you have now. Each picked result is saved into your Saved EQs folder and kept in "
                      "History; you can leave it running.")
        lead.setWordWrap(True)
        theme.mark(lead, role="muted")
        v.addWidget(lead)
        cols = QHBoxLayout()
        now_dev = page.measurement_combo.currentData()
        now_tgt = page.S["files"].get("active_target")
        left, right = QVBoxLayout(), QVBoxLayout()
        left.addWidget(QLabel("IEMs and headphones"))
        self.devs = _checklist(list(page.groups), {now_dev})
        self.devs.setAccessibleName("IEMs and headphones")
        left.addWidget(self.devs)
        right.addWidget(QLabel("Targets"))
        self.tgts = _checklist(list(page.inputs.get("targets") or []), {now_tgt})
        self.tgts.setAccessibleName("Targets")
        right.addWidget(self.tgts)
        cols.addLayout(left)
        cols.addLayout(right)
        v.addLayout(cols, 1)
        for lst in (self.devs, self.tgts):
            lst.itemChanged.connect(lambda _it: self.count())
        row = QHBoxLayout()
        self.count_lab = QLabel()
        row.addWidget(self.count_lab, 1)
        self.start_btn = QPushButton("Start")
        theme.mark(self.start_btn, primary=True)
        self.start_btn.clicked.connect(self.start)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        for b in (self.start_btn, self.cancel_btn, close):
            row.addWidget(b)
        v.addLayout(row)
        self.table = QTableWidget(0, 3)
        self.table.setAccessibleName("How each one went")
        self.table.setHorizontalHeaderLabels(["IEM", "Target", "How it went"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 220)
        v.addWidget(self.table, 1)
        self.timer = QTimer(self, interval=400, timeout=self.poll)
        self.count()

    def count(self):
        n = len(_ticked(self.devs)) * len(_ticked(self.tgts))
        self.count_lab.setText(f"{n} EQ{'s' if n != 1 else ''} to make" if n else "Tick at least one IEM and one target.")
        self.start_btn.setEnabled(bool(n) and not self.running)

    # ---------------------------------------------------------------- running
    def start(self):
        page = self.page
        self.jobs = [(d, t) for d in _ticked(self.devs) for t in _ticked(self.tgts)]
        if not self.jobs:
            return
        self.table.setRowCount(len(self.jobs))
        for i, (d, t) in enumerate(self.jobs):
            for j, text in enumerate((d, os.path.splitext(t)[0], "Waiting")):
                self.table.setItem(i, j, QTableWidgetItem(text))
        self.running, self.stop, self.i = True, False, -1
        self.before = copy.deepcopy(page.S)  # (your choice of files: put back at the end)
        for w in (self.devs, self.tgts, self.start_btn):
            w.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.next_job()

    def say(self, i, text):
        self.table.setItem(i, 2, QTableWidgetItem(text))

    def next_job(self):
        page = self.page
        self.i += 1
        if self.stop or self.i >= len(self.jobs):
            return self.finish()
        dev, tgt = self.jobs[self.i]
        cfg = copy.deepcopy(self.before)
        mine = {f["name"] for f in page.groups.get(dev, [])}
        cfg["files"]["active_target"] = tgt
        cfg["files"]["excluded"] = [m["name"] for m in page.inputs["measurements"] if m["name"] not in mine]
        r = page.svc.call("/api/run", {"settings": cfg, "mode": cfg["mode"]})
        if r.get("error"):
            self.say(self.i, "Couldn't start: " + r["error"])
            return QTimer.singleShot(0, self.next_job)
        self.say(self.i, "Running…")
        self.table.scrollToItem(self.table.item(self.i, 0))
        self.timer.start()

    def poll(self):
        page = self.page
        j = page.svc.call("/api/job")
        if j.get("status") == "running":
            self.say(self.i, f"Running: {j.get('message') or ''}" + (f" · {round(j['elapsed'])} s" if j.get("elapsed") else ""))
            return
        self.timer.stop()
        page.svc.call("/api/job", {"ack": True})
        if j.get("status") == "done":
            try:
                self.say(self.i, self.keep(j["result"]))
            except Exception as e:  # noqa: BLE001 - said in the row, the queue goes on
                self.say(self.i, f"Made, but not saved: {e}")
        elif j.get("status") == "cancelled":
            self.say(self.i, "Cancelled")
        else:
            self.say(self.i, "Failed: " + (j.get("message") or "the run failed"))
        self.next_job()

    def keep(self, payload):
        """The picked result: saved (EQ files under its automatic name, never over a file), in History and in Runs
        this session. Returns what to say."""
        from eq import engines
        from ui.eq_page import file_base_name
        page = self.page
        cfg = payload["settings"]
        r = next(x for x in payload["results"] if x["id"] == payload["pick"])
        filters = [{"enabled": True, "type": f.get("type") or "PK", "freq": f["freq"], "gain": f["gain"], "q": f["q"]}
                   for f in r["filters"]]
        g = engines.eq_gain(np.geomspace(20, 20000, 480), filters, cfg["site"]["sample_rate"])
        preamp = -float(np.max(g)) if filters else 0.0
        lay = next((l for l in page.meta.get("layouts", []) if l["key"] == r.get("layout") and l["key"] != "any"), None)
        base_name = file_base_name(payload.get("device") or "EQ", payload.get("target_name") or "target",
                                   lay["name"] if lay else "", payload["mode"], r["n_filters"])
        written = []
        from eq import exports
        if any(cfg["export"].get(k) for k in exports.FORMATS):
            for k in range(1, 50):
                name = base_name if k == 1 else f"{base_name} ({k})"
                res = page.svc.call("/api/export", {"settings": cfg, "filters": filters, "preamp": preamp, "name": name})
                if not res.get("exists"):
                    break
            if res.get("error"):
                raise ValueError(res["error"])
            written = [os.path.basename(p) for p in (res.get("written") or {}).values()]
        page.runs += 1
        run = dict(payload, n=page.runs)
        page.keep_run(run)
        page.render_runs()
        base = f"{page.session}-{run['n']}-{r['id']}"
        entry = {"key": f"{base}-{page._print(filters)}", "base": base, "saved": bool(written),
                 "device": payload.get("device"), "target": payload.get("target_name"),
                 "target_file": payload.get("target_file"), "meas_files": payload.get("meas_files"),
                 "adjust": cfg["target_adjust"], "mode": payload["mode"], "label": page.run_label(run, r),
                 "result": {k: v for k, v in r.items() if k != "filters"}, "filters": filters, "rms": r["rms"],
                 "preamp": preamp, "n_filters": len(filters),
                 "site": cfg["site"], "rig_convert": cfg["rig_convert"]["enabled"], "band": cfg["scoring"]["band_hz"]}
        h = page.svc.call("/api/history/add", {"entry": entry})
        if not h.get("error"):
            page.history = [e for e in page.history if e.get("key") != h["entry"]["key"]] + [h["entry"]]
        return (f"Done: {r['n_filters']} filters · {r['rms']:.2f} dB · "
                + (f"saved as {written[0]}" if written else "not saved (no file ticked in Advanced › Saved files)"))

    def cancel(self):
        self.stop = True
        self.page.svc.call("/api/cancel")
        self.cancel_btn.setEnabled(False)

    def finish(self):
        """The queue done: your settings back as they were (the runs saved theirs), the screen as it was."""
        page = self.page
        self.running = False
        page.svc.call("/api/settings", {"settings": page.S})
        page.history_note()
        for w in (self.devs, self.tgts):
            w.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.count()
        done = sum(1 for i in range(self.table.rowCount())
                   if (self.table.item(i, 2) or QTableWidgetItem("")).text().startswith("Done"))
        page.status(f"Run several: {done} of {len(self.jobs)} EQs made.", 10000)
        if page.run_result is None and page.session_runs:  # (the result card was hidden: Runs this session out of reach)
            page.choose_run(id(page.session_runs[-1]))

    def _closing(self):
        if self.running:  # (closing while it runs: the run going on is cancelled and the queue stops)
            self.cancel()
            self.timer.stop()
            self.page.svc.call("/api/settings", {"settings": self.page.S})
            self.running = False

    def closeEvent(self, e):
        self._closing()
        super().closeEvent(e)

    def reject(self):  # (Esc: Qt hides the window without a closeEvent; the queue went on out of sight)
        self._closing()
        super().reject()
