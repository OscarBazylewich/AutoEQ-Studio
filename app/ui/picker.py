"""Finding a target or a measurement (AutoEQ Local's picker.js, natively): one search over three sources:
- In the app: your files (a measurement is a set: its files can be ticked or unticked one by one; moved to the other
  side, or deleted)
- This PC: curve files found in your Downloads, Documents, Desktop and Music (scanned when the window opens, unless
  it was in the last minute; the online lists are loaded again only after half an hour)
- Online databases: the measurers' lists (about 55,000 entries): Use downloads the curve into downloads\\ first

Filters (kept for the next search, for targets and measurements apart): Rig (or "Fits your target's rig": on it, or
its database has a conversion of its own for it), Type, Source, Stated rig (not the usual rig of a database, a "?"),
Downloadable (not a list-only database's). Each choice says how many results it would leave.
Each row: Show (its curve on the graph, without using it; again to take it off) and Use (double-click too).

Offline (net.py): the lists the app has are searched as usual; a curve downloaded before is used from this PC, any
other online one says it needs the internet. A list-only database's entry opens on its site (online only).
"""
import os

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

import net
from ui import help_window, tasks, theme
from ui.search_combo import SearchCombo, natural_key

LIMIT_ALL, LIMIT_ONE = {"pc": 40, "db": 120}, 400
FIRST_ROWS, ROWS_AT_ONCE = 30, 8  # rows made at once when the list changes, then a batch at a time
FORMS = {"iem": "IEM", "hp": "Headphone", "earbud": "Earbud"}
SOURCES = [("", "All"), ("app", "In the app"), ("pc", "This PC"), ("db", "Online databases")]
ANY = {"rig": "", "form": "", "site": "", "sure": False, "dl": False}
_DB_MADE = {}  # (kind, any kind) -> (the online list, the page's meta, its rows): kept from one Find… to the next
_DB_SORTED = {}  # "items" -> (the online list as it came, the same A to Z): sorted once, off the window's thread


def name_form(s):
    import re
    s = s or ""
    for form, rx in (("earbud", r"earbud"), ("iem", r"\biems?\b|in-ear|\bie\b"), ("hp", r"headphone|over-ear|on-ear|\bhp\b|\boe\b")):
        if re.search(rx, s, re.I):
            return form
    return ""


class Picker(QDialog):
    def __init__(self, page, kind):
        super().__init__(page)
        self.page, self.kind = page, kind
        self.svc, self.meta = page.svc, page.meta
        self.setWindowTitle("Find a target" if kind == "target" else "Find a measurement")
        self.resize(900, 720)
        saved = page.sw.s.get("picker") or {}
        self.filters = {k: dict(ANY, **(saved.get(k) or {})) for k in ("target", "measurement")}
        self.src, self.expanded, self.busy, self._fetching = "", set(), None, False
        self._fails, self._tr = {}, ""
        self.db, self.lib = {"items": [], "loading": True}, {"items": [], "scanning": True}

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search: a model, a maker, a database…")
        self.q.textChanged.connect(lambda _t: self._later.start())
        top.addWidget(self.q, 1)
        self.anykind = QCheckBox("Targets and measurements")
        self.anykind.setToolTip("Also list the other kind (an entry may be filed as the other)")
        self.anykind.toggled.connect(self.render)
        top.addWidget(self.anykind)
        v.addLayout(top)
        srcs = QHBoxLayout()
        self.src_btns = QButtonGroup(self)
        for key, name in SOURCES:
            b = QPushButton(name)
            b.setCheckable(True)
            theme.mark(b, nav=True)
            b.setChecked(key == "")
            b.clicked.connect(lambda _=False, k=key: self.set_src(k))
            self.src_btns.addButton(b)
            srcs.addWidget(b)
        srcs.addStretch(1)
        v.addLayout(srcs)
        fl = QHBoxLayout()
        # (the filters' lists open with a search box: the sources alone are over 150)
        self.f_rig, self.f_form, self.f_site = SearchCombo(), SearchCombo(), SearchCombo()
        for box, key in ((self.f_rig, "rig"), (self.f_form, "form"), (self.f_site, "site")):
            box.setAccessibleName({"rig": "Rig", "form": "Type", "site": "Source"}[key])
            box.setMinimumContentsLength(14)
            box.activated.connect(lambda _i, box=box, key=key: self.set_filter(key, box.currentData()))
            fl.addWidget(box, 1)
        self.f_sure = QCheckBox("Stated rig")
        self.f_sure.setToolTip("Only those whose source states the rig (not a database's usual rig: a “?”)")
        self.f_sure.toggled.connect(lambda on: self.set_filter("sure", on))
        self.f_dl = QCheckBox("Downloadable")
        for w, key in ((self.anykind, "#pk-anykind"), (self.f_rig, "pk_filters"), (self.f_form, "pk_filters"),
                       (self.f_site, "pk_filters"), (self.f_sure, "#pk-f-sure"), (self.f_dl, "#pk-f-dl")):
            help_window.tag(w, key)
        self.f_dl.setToolTip("Leave out list-only databases (they don't let other programs download their files)")
        self.f_dl.toggled.connect(lambda on: self.set_filter("dl", on))
        self.f_clear = QPushButton("Clear filters")
        self.f_clear.clicked.connect(self.clear_filters)
        for w in (self.f_sure, self.f_dl, self.f_clear):
            fl.addWidget(w)
        v.addLayout(fl)
        self.list = QListWidget()
        self.list.setAccessibleName("Found")
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemDoubleClicked.connect(lambda it: it.data(Qt.UserRole) and self.choose(it.data(Qt.UserRole)))
        v.addWidget(self.list, 1)
        bottom = QHBoxLayout()
        self.status = QLabel()
        theme.mark(self.status, role="muted")
        bottom.addWidget(self.status, 1)
        sources = QPushButton("Sources…")
        sources.setToolTip("Which folders on this PC and which online databases Find… searches; add a database")
        sources.clicked.connect(self.open_sources)
        bottom.addWidget(sources)
        trace = QPushButton("✎ Trace a graph image…")
        trace.setToolTip("Only a picture of the graph? Trace it into a curve (as picker.js's link)")
        trace.clicked.connect(lambda: (self.reject(), self.page.open_trace()))
        bottom.addWidget(trace)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        bottom.addWidget(close)
        v.addLayout(bottom)
        self._later = QTimer(self, singleShot=True, interval=80, timeout=self.render)
        self._pending, self._more = [], QTimer(self, singleShot=True, interval=0, timeout=self._make_more)
        self._poll = QTimer(self, interval=500, timeout=self._load)
        self._load(first=True)
        self._poll.start()
        self.render()
        self.q.setFocus()

    # ---------------------------------------------------------------- data
    def _load(self, first=False):
        """The online lists (the saved ones at once; online, refreshed in the background) and this PC's files (a
        scan of your folders), asked for until both have finished."""
        if first:
            self.svc.call("/api/db/refresh", {"settings": self.page.S})
            self.svc.call("/api/library/scan", {"settings": self.page.S})
        if self._fetching:  # (the last one still going: not another on top)
            return
        self._fetching = True
        have_db = (len(self.db["items"]), self.db.get("loading"))
        have_lib = (len(self.lib["items"]), self.lib.get("scanning"))

        def fetch():
            # the counts first (cheap); a whole list (55,000 rows) only when it changed: every half second it was
            # built again while the lists loaded
            db, lib = self.svc.call("/api/db"), self.svc.call("/api/library")
            if first or (db.get("count"), db.get("loading")) != have_db:
                db = self.svc.call("/api/db", {"items": True})
                src = db.get("items")
                if src:  # (55,000 rows A to Z: half a second, so here, once per list; the same list after)
                    had = _DB_SORTED.get("items")
                    if not had or had[0] is not src:
                        _DB_SORTED["items"] = (src, sorted(src, key=lambda it: (not str(it[2]).strip(), natural_key(it[2]),
                                                                           str(it[3]).casefold())))  # (nameless last)
                    db = dict(db, items=_DB_SORTED["items"][1])
            if first or (lib.get("count"), lib.get("scanning")) != have_lib:
                lib = self.svc.call("/api/library", {"items": True})
            return db, lib

        def got(res, err):
            self._fetching = False
            if err or not res:
                return
            db, lib = res
            # (a list comes only when it or its loading changed: the counts alone, without rows, aren't a change. They
            # were taken for one, and the whole list was drawn again every half second while this PC was searched)
            changed = db.get("items") is not None or lib.get("items") is not None
            if db.get("items") is not None:
                self.db = db
            if lib.get("items") is not None:
                self.lib = lib
            if not db.get("loading") and not lib.get("scanning"):
                self._poll.stop()
            elif not self._poll.isActive():  # (loading again: Sources changed the lists, a refresh)
                self._poll.start()
            if changed:
                self.render()
        tasks.background(fetch, got, owner=self)

    def app_rig(self, n):
        return (self.page.inputs.get("rigs") or {}).get(n, "")

    def target_rig(self):
        return self.app_rig(self.page.inputs.get("active_target")).replace("?", "")

    def devices(self):
        """The measurements in the app, as devices (sets of files)."""
        out = []
        for name, files in self.page.groups.items():
            out.append({"name": name, "files": files, "on": sum(1 for f in files if f["included"])})
        return out

    def device_rig(self, d):
        rs = list(dict.fromkeys(self.app_rig(f["name"]) for f in d["files"]))
        if len(rs) == 1:
            return rs[0]
        return rs[0].replace("?", "") + "?" if all(r.replace("?", "") == rs[0].replace("?", "") for r in rs) else "mixed"

    def site_of_folder(self, p):
        dl = (self.meta.get("downloads_dir") or "").lower()
        if not dl or not p.lower().startswith(dl):
            return None
        name = p[len(dl) + 1:].replace("/", "\\").split("\\")[0]
        return next((s for s in self.meta.get("database_sites", []) if s.get("folder") == name), None)

    def short_path(self, p):
        dl = self.meta.get("downloads_dir") or ""
        if dl and p.lower().startswith(dl.lower()):
            return "downloaded from " + p[len(dl) + 1:].replace("/", "\\").split("\\")[0]
        home = self.meta.get("home") or ""
        return "~" + p[len(home):] if home and p.lower().startswith(home.lower()) else p

    def want_kind(self, k):
        return self.anykind.isChecked() or k == self.kind

    # ---------------------------------------------------------------- the rows of each source (picker.js)
    def app_rows(self, ws):
        hit = lambda hay: all(w in hay for w in ws)
        inp = self.page.inputs
        if self.kind == "target":
            return sorted(({"src": "app", "key": "app:t:" + n, "name": os.path.splitext(n)[0], "file": n,
                            "sub": "current target" if n == inp["active_target"] else "in the app",
                            "current": n == inp["active_target"], "rig": self.app_rig(n), "form": name_form(n), "site": "app"}
                           for n in inp["targets"] if hit(n.lower())), key=lambda r: natural_key(r["name"]))
        out = []
        for d in self.devices():
            if not hit(d["name"].lower() + " " + " ".join(f["name"].lower() for f in d["files"])):
                continue
            n = len(d["files"])
            on = f" · {'in use' if d['on'] == n else str(d['on']) + ' ticked'}" if d["on"] else ""
            out.append({"src": "app", "key": "app:m:" + d["name"], "name": d["name"], "device": d,
                        "sub": f"{n} file{'s' if n > 1 else ''}{on}", "current": d["on"] > 0, "rig": self.device_rig(d),
                        "form": name_form(d["name"]), "site": "app"})
        return sorted(out, key=lambda r: natural_key(r["name"]))

    def pc_rows(self, ws):
        out = []
        for g in self.lib.get("items") or []:
            if g.get("in_app") or not self.want_kind(g["kind"]):
                continue
            hay = g.setdefault("hay", (g["name"] + " " + g["folder"]).lower())
            if not all(w in hay for w in ws):
                continue
            site, is_t = self.site_of_folder(g["folder"]), g["kind"] == "target"
            out.append({"src": "pc", "key": "pc:" + g["folder"] + "|" + g["name"], "id": g["id"], "name": g["name"],
                        "other": g["kind"] != self.kind, "is_target": is_t, "rig": g.get("rig") or "",
                        "sub": f"{'target' if is_t else str(len(g['files'])) + ' files' if len(g['files']) > 1 else 'measurement'}"
                               f" · {self.short_path(g['folder'])}",
                        "site": site["short"] if site else "pc",
                        "form": (name_form(g["name"]) or (site or {}).get("form", "")) if is_t else
                                ((site or {}).get("form") or name_form(g["name"]))})
        return sorted(out, key=lambda r: (natural_key(r["name"]), natural_key(r["sub"])))

    def db_rows(self, ws):
        """The online entries matching the words. Their rows are made once per list (and kind), then only searched:
        55,000 of them were made again at every key and each time Find… opened (the list stays the same object
        until the lists are loaded again: databases.status)."""
        items, anykind = self.db.get("items") or [], self.anykind.isChecked()
        made = _DB_MADE.get((self.kind, anykind))
        if not (made and made[0] is items and made[1] is self.meta):
            for k in [k for k, m in _DB_MADE.items() if m[0] is not items]:  # (rows of an older list: let go)
                del _DB_MADE[k]
            base, notes, convs = [], self.meta.get("rig_notes") or {}, self.meta.get("unit_convs") or {}
            for it in items:  # [id, "t"|"m", name, sub, site, link|None, rig, form]
                is_t = it[1] == "t"
                if not self.want_kind("target" if is_t else "measurement"):
                    continue
                base.append(((it[2] + " " + it[3] + " " + it[4]).lower(),
                             {"src": "db", "key": f"db:{it[4]}|{it[2]}|{it[3]}", "id": it[0], "name": it[2],
                              "other": is_t != (self.kind == "target"), "sub": f"{it[3]} · {it[4]}", "link": it[5],
                              "rig": it[6] or "", "is_target": is_t, "form": it[7] or "", "site": it[4],
                              "how": "" if is_t else notes.get(f"{it[4]}|{it[3]}") or notes.get(it[4]) or "",
                              "convs": None if is_t else convs.get(f"{it[4]}|{it[3]}") or convs.get(it[4])}))
            made = _DB_MADE[(self.kind, anykind)] = (items, self.meta, base)
        out = [r for hay, r in made[2] if all(w in hay for w in ws)] if ws else [r for _h, r in made[2]]
        if ws:  # (names that start with what's typed first, each part still A to Z)
            out.sort(key=lambda r: not r["name"].lower().startswith(ws[0]))
        return out

    # ---------------------------------------------------------------- the filters
    def rig_of(self, r):
        return "mixed" if r["rig"] == "mixed" else (r["rig"] or "").replace("?", "") or "-"

    def fits(self, r, tr=None):
        tr = self.target_rig() if tr is None else tr
        return bool(tr) and (self.rig_of(r) == tr or any(c.get("from") == tr for c in r.get("convs") or []))

    def failed(self, r, f):
        """The filters a row doesn't pass (their keys). Worked out once per row in a render (self._fails): each
        choice's count asks for every row again, and with 55,000 online entries that was half a million tests a key."""
        out = self._fails.get(id(r))
        if out is not None:
            return out
        out = []
        if f["rig"] and not (self.fits(r, self._tr) if f["rig"] == "fits" else self.rig_of(r) == f["rig"]):
            out.append("rig")
        if f["form"] and (r["form"] or "-") != f["form"]:
            out.append("form")
        if f["site"] and r["site"] != f["site"]:
            out.append("site")
        if f["sure"] and not (r["rig"] and r["rig"] != "mixed" and not r["rig"].endswith("?")):
            out.append("sure")
        if f["dl"] and r.get("link"):
            out.append("dl")
        self._fails[id(r)] = out
        return out

    def passes(self, r, f, skip=None):
        return all(k == skip for k in self.failed(r, f))

    def set_filter(self, key, value):
        self.filters[self.kind][key] = value
        self._save_filters()
        self.render()

    def clear_filters(self):
        self.filters[self.kind] = dict(ANY)
        self._save_filters()
        self.render()

    def _save_filters(self):
        self.page.sw.set("picker", self.filters)

    def set_src(self, s):
        self.src = s
        self.render()

    def _render_filters(self, rows, f):
        rigs = self.meta.get("rigs") or {}
        rig_name = lambda v: "Rig not known" if v == "-" else "Mixed rigs" if v == "mixed" else rigs.get(v, v).split(" (")[0]
        site_name = lambda v: "In the app" if v == "app" else "Your files on this PC" if v == "pc" else v
        facets = [(self.f_rig, "rig", self.rig_of, rig_name, "Any rig"),
                  (self.f_form, "form", lambda r: r["form"] or "-",
                   lambda v: "Type not known" if v == "-" else FORMS.get(v, v),
                   "Made for any type" if self.kind == "target" else "Any type"),
                  (self.f_site, "site", lambda r: r["site"], site_name, "Any source")]
        # each box counts what the other filters leave, all three in one pass (a row failing two filters counts in
        # none; failing one, only in that one's box)
        tr = self._tr
        want_fits = self.kind == "measurement" and bool(tr)
        tally, fits_n = {key: {} for _b, key, *_r in facets}, 0
        for r in rows:
            fl = self.failed(r, f)
            if len(fl) > 1:
                continue
            for _b, key, value_of, *_r in facets:
                if not fl or fl[0] == key:
                    v = value_of(r)
                    tally[key][v] = tally[key].get(v, 0) + 1
            if want_fits and (not fl or fl[0] == "rig") and self.fits(r, tr):
                fits_n += 1
        for box, key, _value_of, name_of, any_ in facets:
            counts = tally[key]
            if f[key] and f[key] not in counts and f[key] != "fits":
                counts[f[key]] = 0
            # A to Z (numbers as numbers); "In the app" and "Your files on this PC" first, "not known" and mixed last
            first = {"app": 0, "pc": 1} if key == "site" else {}
            values = sorted(counts.items(), key=lambda kv: (first.get(kv[0], 2), kv[0] in ("-", "mixed"),
                                                             natural_key(name_of(kv[0]))))
            box.blockSignals(True)
            box.clear()
            box.addItem(any_, "")
            if key == "rig" and self.kind == "measurement" and (self.target_rig() or f[key] == "fits"):
                # (chosen before, for a target whose rig is known: still the filter, so still shown, saying why it
                # leaves nothing)
                n = fits_n
                if n or f[key] == "fits":
                    box.addItem(f"Fits your target's rig: {rig_name(self.target_rig())} or converted for it ({n:,})"
                                if self.target_rig() else "Fits your target's rig (not known for this target: none)", "fits")
            for val, n in values:
                box.addItem(f"{name_of(val)} ({n:,})", val)
            box.setCurrentIndex(max(0, box.findData(f[key])))
            box.blockSignals(False)
        for chk, key in ((self.f_sure, "sure"), (self.f_dl, "dl")):
            chk.blockSignals(True)
            chk.setChecked(bool(f[key]))
            chk.blockSignals(False)
        self.f_dl.setVisible(self.kind != "target")
        self.f_clear.setVisible(any(f.values()))

    # ---------------------------------------------------------------- the list
    def render(self):
        ws = [w for w in self.q.text().lower().split() if w]
        f = self.filters[self.kind]
        self._fails, self._tr = {}, self.target_rig()
        sections = [(s, title, fn(ws)) for s, title, fn in (("app", "In the app", self.app_rows),
                                                             ("pc", "This PC", self.pc_rows),
                                                             ("db", "Online databases", self.db_rows))
                    if not self.src or self.src == s]
        self._render_filters([r for _, _, rows in sections for r in rows], f)
        lst = self.list
        # (the same search and filters: Show, ticking a file, a list loaded… keep the place in the list and the row)
        view = (self.kind, self.src, self.q.text(), repr(sorted(f.items())), self.anykind.isChecked())
        keep = view == getattr(self, "_view", None)
        place = (lst.count(), lst.verticalScrollBar().value(), lst.currentRow()) if keep else None
        self._view = view
        lst.setUpdatesEnabled(False)
        self._more.stop()
        self._pending = []
        lst.clear()
        later = []  # (the rows past the first ones: made a few at a time after, so a key never waits for them all)
        shown = hidden = 0
        for s, title, found in sections:
            rows = [r for r in found if self.passes(r, f)]
            lim = LIMIT_ONE if self.src else LIMIT_ALL.get(s, 10 ** 9)
            hidden += len(found) - len(rows)
            if not rows and not self.src:
                continue
            if not self.src:
                heading = f"{title.upper()}  ·  {len(rows):,}"
                later.append(lambda t=heading: self._note(t, heading=True))
            for r in rows[:lim]:
                later.append(lambda r=r: self._row(r))
                if r.get("device") and r["device"]["name"] in self.expanded:
                    for fl in r["device"]["files"]:
                        later.append(lambda r=r, fl=fl: self._file_row(r, fl))
            shown += min(len(rows), lim)
            if len(rows) > lim:
                more = f"{len(rows) - lim:,} more. Type to narrow the list" + \
                    ("" if self.src else f", or show only {title.lower()} (above).")
                later.append(lambda t=more: self._note(t))
            if not rows and s == "db" and self.db.get("loading"):
                later.append(lambda: self._note("Loading the database lists…"))
        if not shown:
            later.append(lambda: self._note(("Nothing matches." if ws or hidden else "Nothing here yet.")
                                            + (" (Online lists are still loading.)" if self.db.get("loading") else "")))
        if hidden:
            later.append(lambda: self._note(f"{hidden:,} more hidden by the filters: Clear filters (above) shows them."))
        self._pending = later
        self._make_more(max(FIRST_ROWS, place[0]) if place else FIRST_ROWS)
        if place:
            if 0 <= place[2] < lst.count():
                lst.setCurrentRow(place[2])
            lst.verticalScrollBar().setValue(place[1])
            QTimer.singleShot(0, lambda v=place[1]: lst.verticalScrollBar().setValue(v))  # (once laid out)
        lst.setUpdatesEnabled(True)
        self._fails = {}  # (by id: only while these rows are alive)
        n_app = len(self.page.inputs["targets"]) if self.kind == "target" else len(self.devices())
        n_pc = len([g for g in self.lib.get("items") or [] if not g.get("in_app")])
        off = "  ·  Offline: online entries you've downloaded before still work" if net.offline() else ""
        self.status.setText(("Loading online lists…" if self.db.get("loading") else
                             f"{n_app} in the app · {n_pc} on this PC"
                             + (" (still looking)" if self.lib.get("scanning") else "")
                             + f" · {len(self.db.get('items') or []):,} online") + off)

    def _make_more(self, n=None):
        """The next rows of the list (each row is a few widgets, about 2 ms: 120 of them held every key for a
        quarter of a second); the rest a batch at a time while nothing else waits."""
        n = n or ROWS_AT_ONCE
        todo, self._pending = self._pending[:n], self._pending[n:]
        for make in todo:
            make()
        if self._pending:
            self._more.start()

    def finish_list(self):
        """Every row made now (for checks)."""
        self._more.stop()
        while self._pending:
            self._make_more()

    def _note(self, text, heading=False):
        it = QListWidgetItem(text)
        it.setFlags(Qt.NoItemFlags)
        if heading:
            f = it.font()
            f.setBold(True)
            f.setPointSizeF(f.pointSizeF() * 0.9)
            it.setFont(f)
        self.list.addItem(it)

    def _rig_tag(self, r):
        rigs = self.meta.get("rigs") or {}
        tag, key = r["rig"] or "", (r["rig"] or "").replace("?", "")
        made = r.get("is_target") or (r["src"] == "app" and not r.get("device"))
        what = "Made for" if made else "Measured on"
        if tag == "mixed":
            return "mixed", "Its files come from different rigs"
        if key not in rigs:
            return "rig ?", ("Which rig it is made for isn't known" if made else "Which rig it was measured on isn't known") \
                + (f": {r['how']}" if r.get("how") else "")
        guess = tag.endswith("?")
        tip = f"{what}: {rigs[key]}" + (" (probably: the usual rig for its source, not stated by it)" if guess else "") \
            + (f": {r['how']}" if r.get("how") else "")
        convs = r.get("convs") or []
        label = key + ("?" if guess else "")
        if convs:
            short = lambda x: rigs.get(x, x).split(" (")[0]
            label += " ⇄"
            tip += ("\nIts database has a conversion of its own (errors 1–10 kHz): " +
                    "; ".join(f"for {short(c['from'])} targets ({c['models']} models: about {c['error']:.1f} dB left, "
                              f"{c['before']:.1f} without)" for c in convs))
        return label, tip

    def _row(self, r):
        it = QListWidgetItem()
        it.setData(Qt.UserRole, r)
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(6, 3, 6, 3)
        prev = self.page.preview_on(r["key"])
        eye = QPushButton("Hide" if prev else "Show")
        eye.setToolTip("Take it off the graph" if prev else "Show it on the graph (without using it)")
        eye.clicked.connect(lambda _=False, r=r: self.preview(r))
        h.addWidget(eye)
        # (only once it's in the row: shown before, a button with no parent is a window of its own, and every row
        # flashed one on the screen while the lists loaded: the user saw them, and each cost the window's time)
        eye.setVisible(not r.get("link"))
        text = QVBoxLayout()
        text.setSpacing(0)
        name = QLabel(("✓ " if r.get("current") else "") + r["name"])
        name.setStyleSheet("font-weight: 600;")
        name.setToolTip(r["name"])
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)  # (a long name is cut, never the buttons)
        text.addWidget(name)
        sub = QLabel("Downloading…" if self.busy == r["key"] else r["sub"])
        theme.mark(sub, role="muted")
        sub.setToolTip(r["sub"])
        sub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        text.addWidget(sub)
        h.addLayout(text, 1)
        label, tip = self._rig_tag(r)
        tag = QLabel(label)
        theme.mark(tag, role="chip")
        tag.setToolTip(tip)
        h.addWidget(tag)
        if r.get("other"):
            other = QLabel("measurement?" if self.kind == "target" else "target?")
            theme.mark(other, role="muted")
            other.setToolTip(f"Filed as a {'measurement' if self.kind == 'target' else 'target'}")
            h.addWidget(other)
        if r["src"] == "app":
            if r.get("device"):
                b = QPushButton("Files ▴" if r["device"]["name"] in self.expanded else "Files ▾")
                b.setToolTip("Tick or untick single files (seatings, left and right)")
                b.clicked.connect(lambda _=False, d=r["device"]["name"]: self.toggle_expand(d))
                h.addWidget(b)
                x = QPushButton("✕")
                x.setToolTip(f"Delete {r['device']['name']} from the app")
                x.clicked.connect(lambda _=False, d=r["device"]: self.remove("measurement", [f["name"] for f in d["files"]], d["name"]))
                h.addWidget(x)
            else:
                mv = QPushButton("→ Measurement")
                mv.setToolTip("It's a measurement: move it to Measurement")
                mv.clicked.connect(lambda _=False, n=r["file"]: self.move("target", n))
                h.addWidget(mv)
                x = QPushButton("✕")
                x.setToolTip("Delete from the app")
                x.clicked.connect(lambda _=False, n=r["file"]: self.remove("target", [n], n))
                h.addWidget(x)
        elif r.get("link"):
            ext = QLabel("open on site ↗")
            theme.mark(ext, role="muted")
            ext.setToolTip("This site doesn't let other programs download its files: Use opens it on the site")
            h.addWidget(ext)
        elif r["src"] == "db":
            dl = QLabel("⬇")
            dl.setToolTip("Downloads when used")
            h.addWidget(dl)
        use = QPushButton("Use")
        theme.mark(use, primary=True)
        use.setEnabled(self.busy is None)
        use.clicked.connect(lambda _=False, r=r: self.choose(r))
        h.addWidget(use)
        it.setSizeHint(w.sizeHint())
        self.list.addItem(it)
        self.list.setItemWidget(it, w)

    def _file_row(self, r, fl):
        it = QListWidgetItem()
        it.setFlags(Qt.NoItemFlags)
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(46, 0, 6, 0)
        cb = QCheckBox(fl["name"])
        cb.setChecked(fl["included"])
        cb.setToolTip("Include in the average")
        cb.toggled.connect(lambda on, n=fl["name"]: self.toggle_file(n, on))
        h.addWidget(cb, 1)
        mv = QPushButton("→ Target")
        mv.setToolTip("It's a target: move it to Target")
        mv.clicked.connect(lambda _=False, n=fl["name"]: self.move("measurement", n))
        h.addWidget(mv)
        x = QPushButton("✕")
        x.setToolTip("Delete from the app")
        x.clicked.connect(lambda _=False, n=fl["name"]: self.remove("measurement", [n], n))
        h.addWidget(x)
        it.setSizeHint(w.sizeHint())
        self.list.addItem(it)
        self.list.setItemWidget(it, w)

    # ---------------------------------------------------------------- actions
    def body(self, r):
        if r["src"] == "app":
            if r.get("device"):
                return {"src": "app", "kind": "measurement", "names": [f["name"] for f in r["device"]["files"]], "name": r["name"]}
            return {"src": "app", "kind": "target", "names": [r["file"]]}
        return {"src": r["src"], "id": r["id"]}

    def open_sources(self):
        """Sources (ui/sources_window.py): where Find… looks; the lists and this PC's files again after."""
        from ui.sources_window import Sources
        dlg = Sources(self.page)
        dlg.exec()
        dlg.deleteLater()  # (closed windows let go of their rows)
        self._load(first=True)
        self._poll.start()  # (until the lists, now loading again, are in)
        self.render()

    def keyPressEvent(self, e):
        """In the search box (as picker.js): ↑ ↓ move through the results, Enter uses the one picked (the first when
        none is); Enter never presses a button Qt made the dialog's default."""
        k = e.key()
        if k in (Qt.Key_Return, Qt.Key_Enter):
            if self._later.isActive():  # (typed faster than the list: the list for what's typed)
                self._later.stop()
                self.render()
            rows = [self.list.item(i) for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole)]
            it = self.list.currentItem() if self.list.currentItem() in rows else (rows[0] if rows else None)
            if it is not None and (self.q.hasFocus() or self.list.hasFocus()):
                self.choose(it.data(Qt.UserRole))
            return
        if k in (Qt.Key_Up, Qt.Key_Down) and self.q.hasFocus():
            rows = [i for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole)]
            if rows:
                now = self.list.currentRow()
                later = [i for i in rows if (i > now if k == Qt.Key_Down else i < now)]
                self.list.setCurrentRow((later[0] if k == Qt.Key_Down else later[-1]) if later else
                                        (rows[0] if now < 0 else now))
            return
        super().keyPressEvent(e)

    def choose(self, r):
        if self.busy:
            return
        if r.get("link"):
            if net.offline():
                QMessageBox.information(self, "Offline", "This database's entries open on its website, and AutoEQ "
                                        "Studio is offline. Switch to Online (top right) to open it.")
                return
            QDesktopServices.openUrl(QUrl(r["link"]))
            self.page.status(f"{r['sub'].split(' · ')[-1]} doesn't let other programs download its files, so it opened "
                             "on the site.", 10000)
            return
        if r["src"] == "app":
            if r.get("device"):
                self.page.use_device(r["device"]["name"])
            else:
                self.page.use_target(r["file"])
            self.accept()
            return
        self.busy = r["key"]
        self.render()
        body = dict(self.body(r), kind=self.kind, settings=self.page.S, **({"as": self.kind} if r.get("other") else {}))

        page = self.page

        def done(res, err):
            here = tasks.alive(self)  # (closed meanwhile: what was downloaded is still used)
            if err or (res or {}).get("error"):
                if here:
                    self.busy = None
                    QMessageBox.warning(self, "Couldn't use it", str(err or res["error"]))
                    self.render()
                return
            page.used(res)
            if here:
                self.busy = None
                self.accept()
        tasks.background(lambda: self.svc.call("/api/use", body), done)

    def preview(self, r):
        if self.page.preview_on(r["key"]):
            self.page.remove_preview(r["key"])
            self.render()
            return
        if not self.page.curves:
            QMessageBox.information(self, "Show", "Choose a target and a measurement first: a curve is shown beside them.")
            return
        loading = self.__dict__.setdefault("_showing", set())
        if r["key"] in loading:  # (pressed again while it loads)
            return
        loading.add(r["key"])
        body = dict(self.body(r), settings=self.page.S)

        def done(res, err):
            loading.discard(r["key"])
            if err or (res or {}).get("error"):
                QMessageBox.warning(self, "Couldn't show it", str(err or res["error"]))
            else:
                self.page.add_preview(r["key"], res["name"], res["vals"], self.body(r))
            self.render()
        tasks.background(lambda: self.svc.call("/api/preview", body), done, owner=self)

    def toggle_expand(self, name):
        self.expanded.symmetric_difference_update({name})
        self.render()

    def toggle_file(self, name, on):
        ex = set(self.page.S["files"]["excluded"])
        ex.discard(name) if on else ex.add(name)
        self.page.S["files"]["excluded"] = sorted(ex)
        self.page.save_files(after=self.render)

    def move(self, kind, name):
        import json
        before = json.loads(json.dumps(self.page.S["files"]))
        r = self.svc.call("/api/files/move", {"kind": kind, "name": name, "settings": self.page.S})
        if r.get("error"):
            QMessageBox.warning(self, "Move", r["error"])
            return
        self.page.reload_state()
        self.page.moved(kind, name, before)
        self.render()

    def remove(self, kind, names, label):
        if QMessageBox.question(self, "Delete", f"Delete “{label}” ({len(names)} file{'s' if len(names) != 1 else ''}) "
                                "from the app? (A copy you have elsewhere stays.)") != QMessageBox.Yes:
            return
        r = self.svc.call("/api/files/remove", {"kind": kind, "names": names, "settings": self.page.S})
        if r.get("error"):
            QMessageBox.warning(self, "Delete", r["error"])
            return
        self.page.reload_state()
        self.render()

    def done(self, r=0):
        self._poll.stop()
        super().done(r)
