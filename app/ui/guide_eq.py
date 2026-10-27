"""Make an EQ's Guide (AutoEQ Local's guide.js STEPS, told for AutoEQ Studio's window; ui/tour.py shows it):
eq_steps(page), every step in order (Overview, 1 · Choose, 2 · Settings, 3 · Run & review, More) with its words,
the controls it lights and its demo, and start_eq(page), the tour that shows them. The demos' helpers are in
guide_demos.py. Keep the steps in their order: the checks find steps by their titles.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from ui import tasks, theme, tour
from ui.guide_demos import (adjust_demo, bg, button, card, choose_row, demo_filters, eq_now, fold, mock_combo,
                            mock_menu, open_picker, pick, picker_rows, plot_value, show_on_graph, stage_hand,
                            stage_result, type_search)

# (A menu a demo draws is the Guide's own, guide_demos.mock_menu: as wide as its longest row and drawn as a real menu;
# a row ending in " ▸" is a submenu's, Windows 11's chevron at its right, as the app's menus draw it.)


# ---------------------------------------------------------------- Make an EQ's Guide
def eq_steps(page):
    """Make an EQ's Guide."""
    win = page.window()
    st = page.settings
    in_card = lambda w, text: (lambda: button(card(w), text))
    has_curves = lambda: bool(page.curves)
    settings_open, settings_close = fold(st.fold.btn, None)
    adjust_open, adjust_close = fold(st.adjust_btn, None)
    staged = {}

    def result_before():
        staged["undo"] = stage_result(page)

    def result_after():
        u = staged.pop("undo", None)
        if u:
            u()
    example = lambda: " (Before a run, this is an example worked out from your files.)" if staged.get("undo") else ""
    col = theme.graph_colours()

    # ------------------------------------------------ demos that open things
    norm = lambda s: "".join(ch for ch in s.lower() if ch.isalnum())

    def choose_target(api):
        pk = open_picker(page, api, "target")
        api.say("Type part of a name")
        active = page.inputs.get("active_target") or ""
        mine = [n for n in page.inputs.get("targets", []) if n != active]
        q = "harman" if any("harman" in n.lower() for n in mine) or not mine else \
            " ".join(w for w in mine[0].rsplit(".", 1)[0].replace("_", " ").split()[:2]).lower()
        yield from type_search(api, pk, q)
        api.say("Click the one you want: it becomes the target on the graph")
        now = norm(active.rsplit(".", 1)[0])
        got = yield from choose_row(page, api, pk, lambda r: "all" not in r["name"].lower().split()
                                     and norm(r["name"]) != now, page.target_combo)
        if got:
            yield from show_on_graph(page, api, "target", got[1], got[0], page.target_box)

    def model():
        n = (page.curves or {}).get("name") or ""
        import re
        w = re.sub(r"\s*\([^)]*\)", " ", n).replace("_", " ").replace("-", " ").split()[:2]
        return " ".join(w) if len(" ".join(w)) >= 3 else "Truthear Gate"
    same_model = lambda r: norm(r["name"]).startswith(norm(model()))

    def choose_meas(api):
        pk = open_picker(page, api, "measurement")
        api.say("Type the brand or model")
        yield from type_search(api, pk, model().lower())
        api.say("Click the one you want: it's shown on the graph")
        got = yield from choose_row(page, api, pk, same_model, page.measurement_combo)
        vals = got[1] if got else ((page.curves or {}).get("meas") if page.curves else None)
        yield from show_on_graph(page, api, "meas", vals, got[0] if got else model(), page.measurement_box)

    def many_results(api):
        pk = open_picker(page, api, "measurement")
        yield from type_search(api, pk, model().lower())
        rows = picker_rows(pk)
        tag = None
        for it, r in rows:
            if (r.get("rig") or "").replace("?", "") in (page.meta.get("rigs") or {}):
                w = pk.list.itemWidget(it)
                tag = next((x for x in w.findChildren(QLabel) if x.property("role") == "chip"), None)
                if tag is not None:
                    pk.list.scrollToItem(it)
                    break
        # (Find… draws its rows again while its lists are still loading: a tag kept across a pause may be deleted, so
        # its words are read first and it's pointed at only while it's there; it reached for a deleted row,
        # 2026-10-22)
        if tag is not None:
            tip = tag.toolTip()
            api.say("A result's rig tag: what it was measured on, and how that was worked out")
            yield from api.move_to(tag)
            tag = tag if tasks.alive(tag) else None
            api.hot(tag)
            yield from api.note(tip, tag, 2600)
            api.hot(None)
        found = next(((it, x) for it, _r in picker_rows(pk) if pk.list.itemWidget(it) is not None
                      for x in pk.list.itemWidget(it).findChildren(QLabel)
                      if x.property("role") == "chip" and "⇄" in x.text()), None)
        conv = found[1] if found else None
        if conv is not None:
            # (its row scrolled into sight first, as the first rig tag's: further down the list, the pointer and the
            # words went past the list's end, 2026-10-23)
            pk.list.scrollToItem(found[0])
            tip = conv.toolTip().split("\n")[-1]
            api.say("⇄: its database has a conversion of its own")
            yield from api.move_to(conv)
            yield from api.note(tip, conv if tasks.alive(conv) else None, 3000)
        api.say("Keep only one rig (or type, or source)")
        yield from api.move_to(pk.f_rig, 0.3, 0.5)
        yield from api.ripple()
        tr = pk.target_rig() if hasattr(pk, "target_rig") else ""
        pk.filters["measurement"]["rig"] = "fits" if tr else next(iter(page.meta.get("rigs") or {"5128": 1}))
        pk.render()
        yield from api.note("Only ones that fit your target's rig are listed now. Type, Source, “Stated rig” and "
                            "“Downloadable” narrow it further." if tr else "Only ones on that rig are listed now. "
                            "Type, Source, “Stated rig” and “Downloadable” narrow it further.", pk.f_rig, 2600)
        names = [pk.f_site.itemText(i) for i in range(1, pk.f_site.count())]
        word = "crin" if any("crin" in n.lower() for n in names) else (names[-1][:4].lower() if names else "")
        found = [n for n in names if word and word in n.lower()][:6]
        if found:  # (the Source list as it opens: its search box, a word typed, what's left)
            api.say("Many sources? Their list has a search box: type part of a name")
            yield from api.move_to(pk.f_site, 0.3, 0.5)
            yield from api.ripple()
            m = api.mock(pk.f_site, found, width=max(pk.f_site.width(), 300), search=word, typed=True)
            m.hover(0)
            yield 2200
            api.close(m)

    def compare_window(api):
        """Which measurement to use?, shown (its search isn't run: that would download measurements)."""
        from ui import compare_window as cw
        real = cw.CompareWindow.run
        cw.CompareWindow.run = lambda self, auto=False: None
        try:
            w = cw.CompareWindow(page)
        finally:
            cw.CompareWindow.run = real
        from PySide6.QtCore import QSize
        api.window(w, near=None, size=QSize(int(min(860, api.t.width() * 0.7)), int(min(680, api.t.height() * 0.7))))
        w.q.setCursorPosition(0)
        g = theme.graph_colours()
        w.chart.setBackground(g["bg"])
        if page.curves:
            import numpy as np
            import pyqtgraph as pg
            f = np.asarray(page.curves["f"])
            w.chart.plot(f, np.asarray(page.curves["target"]), pen=pg.mkPen(g["target"], width=1.6, style=Qt.DashLine))
            w.chart.plot(f, np.asarray(page.curves["meas"]), pen=pg.mkPen(g["with_eq"], width=2))
        w.status.setText(f"Every measurement of “{w.q.text() or model()}” in the online databases, this PC and the "
                         "app, ranked for your target (the Guide doesn't run it: it would download them).")
        api.spot_on(w.frame)
        api.say("Every measurement of your model, ranked for your target, with the reasons")
        yield from api.move_to(w.q, 0.3)
        yield 900
        api.say("Its rig, how well they agree, the bass seal and the seatings")
        yield from api.move_to(w.chart, 0.4, 0.5)
        yield 1100
        api.say("Search looks for them; Use makes one your measurement, or average several from one rig")
        yield from api.move_to(w.go)
        yield from api.ripple()
        yield 900

    def rig_demo(api):
        """The target as made for its own rig and converted to the measurement's, on the graph."""
        import copy
        c = page.curves
        rig = c.get("rig") if c and isinstance(c.get("rig"), dict) else {}
        if not rig.get("applied"):
            yield 400
            return
        s = copy.deepcopy(page.S)
        s["rig_convert"]["enabled"] = False
        res = yield from bg(lambda: page.svc.call("/api/curves", {"settings": s}))
        if not res or "target" not in res:
            yield 400
            return
        import numpy as np
        yield from api.pin_graph(page, page.measurement_box)
        conv, made = np.asarray(c["target"], dtype=float), np.asarray(res["target"], dtype=float)
        item = api.curve(page, conv, col["target"], 2.6, Qt.DashLine, name="Target (demo)")
        api.say("Rig conversion off: the target as made for its own rig")
        yield from api.morph(page, item, conv, made, 1200)
        yield 1300
        api.say("On (Settings › Target): converted to your measurement's rig")
        yield from api.morph(page, item, made, conv, 1200)
        yield 900

    def app_demo(api):
        combo = page.app_combo
        now = combo.currentData() or ""
        key = next((k for k in ("poweramp", "wavelet", "apo", "peace") if k != now and combo.findData(k) >= 0), None)
        i = combo.findData(key) if key else -1
        api.say("Apps and devices by name, each with its platforms")
        yield from mock_combo(api, combo, i)
        if key:
            api.stage(lambda: page.app_note.text(), page.app_note.setText, page.app_note_text(key))
        api.spot_on(page.app_note)
        api.say("Its limits are kept, and Save writes exactly its file")
        yield from api.at(page.app_note, 0.3, 0.5, 1700, say="Under the row: its limits, where they're from, how to "
                                                            "load the EQ")

    def mode_demo(api):
        combo = page.mode_combo
        keys = [combo.itemData(k) for k in range(combo.count())]
        to = "site_sweep" if page.S["mode"] == "best_fit" else "best_fit"
        api.say("Choose where you'll use the EQ")
        yield from mock_combo(api, combo, keys.index(to) if to in keys else 0)
        from ui.eq_page import MODE_HINT
        api.stage(page.mode_hint.text, page.mode_hint.setText, MODE_HINT.get(to, ""))
        yield from api.at(page.mode_hint, 0.2, 0.5, 1300, say="What it's for, in a line")

    def your_value(api):
        """A value of your own typed into the method's first box: it's marked “yours ↺” (shown, not kept)."""
        f = _first_box()
        if f is None:
            yield 300
            return
        api.say("Type your own value and press Enter")
        v = f.box.text().strip()
        try:
            n = float(v)
            new = str(int(n * 1.5) if n >= 10 else int(n) + 2)
        except ValueError:
            new = "1-8"
        yield from api.type(f.box, new, keep=True, hold=300)
        yield from api.key("Enter", 700)
        old = f.tag.text() if f.tag.isVisible() else None
        f.set_tag("yours")
        api.undo(lambda: f.set_tag(None if old is None else "yours" if old.startswith("yours") else "auto"))
        api.say("It's marked “yours ↺”: click it to hand it back")
        yield from api.at(f.tag, 0.5, 0.5, 1400)

    def _first_box():
        auto = set(st.auto_paths)
        fields = [f for p, f in st.form.fields.items() if f.kind in ("num", "intlist", "numlist", "ranges")
                  and f.box.isVisible() and not p.startswith("scoring")]
        return next((f for f in fields if f.path in auto), None) or (fields[0] if fields else None)

    def run_demo(api):
        was = (page.run_btn.isEnabled(), not page.cancel_btn.isHidden(), not page.progress.isHidden(),
               page.progress.maximum(), page.progress.value(), page.progress_text.text(),
               not page.progress_text.isHidden())

        def back():
            page.run_btn.setEnabled(was[0])
            page.cancel_btn.setVisible(was[1])
            page.progress.setVisible(was[2])
            page.progress.setMaximum(was[3])
            page.progress.setValue(was[4])
            page.progress_text.setText(was[5])
            page.progress_text.setVisible(was[6])
        api.undo(back)
        page.run_btn.setEnabled(False)
        page.cancel_btn.show()  # (at the Run row's end, where nothing moves for it)
        page.progress.show()
        page.progress.setMaximum(100)
        page.progress.setValue(0)
        page.progress_text.setText("Starting…")
        page.progress_text.show()  # (the line under Run shows only while it says something)
        api.spot_on(page.cancel_btn, page.progress, page.progress_text)
        yield 300
        yield from api.at(page.cancel_btn, 0.5, 0.5, 900, say="Cancel stops it at any time")
        api.say("Progress shows while it runs")
        n = len(demo_filters(page)) or 6
        yield from api.tween(1800, lambda p: (page.progress.setValue(int(p * 100)), page.progress_text.setText(
            f"Best fit: {max(1, round(n * p))} of {n} filter counts tried · {max(1, round(p * 4))} s")))
        if page.curves:
            api.say("Done: your IEM with the EQ (blue) on the graph")
            yield from api.pin_graph(page, page.run_btn)
            meas = page.curves["meas"]
            item = api.curve(page, meas, col["with_eq"], 2.6, name="With the EQ (demo)")
            yield from api.morph(page, item, meas, eq_now(page), 1500)
            yield from api.note("With the EQ: close to the target", api.t.pin or page.plot, 1500, below="inside")

    def graph_demo(api):
        if not page.curves:
            yield 300
            return
        api.say("With the EQ, your IEM (orange) becomes the blue curve, close to the dashed target")
        api.spot_on(page.plot)
        meas = page.curves["meas"]
        item = api.curve(page, meas, col["with_eq"], 2.6, name="With the EQ (demo)")
        yield from api.morph(page, item, meas, eq_now(page), 1500)
        yield 700

    def views_demo(api, view=None, y=None):
        combo = page.view_combo if view is not None else page.yrange_combo
        i = combo.findData(view if view is not None else y)
        yield from mock_combo(api, combo, i)
        api.undo(page.demo_graph(**({"view": view} if view is not None else {"y": y})))
        api.spot_on(page.plot)
        yield 1500

    def result_demo(api):
        api.say("“Fewer or more filters”: the best result for each count")
        if page.count_combo.count() > 1:
            yield from mock_combo(api, page.count_combo, max(0, page.count_combo.currentIndex() - 1))
        else:
            yield from api.at(page.count_combo, 0.5, 0.5, 900)

    def edit_demo(api):
        t = page.editor.table
        box = t.cellWidget(0, 4) if t.rowCount() else None
        if box is None:
            yield 300
            return
        api.say("Change any value: the numbers and the graph follow")
        old = [dict(x) for x in page.EDIT]
        try:
            v = float(box.text())
        except ValueError:
            v = 0.0
        new = round(v - 2 if v > 0 else v + 2, 1)
        yield from api.type(box, f"{new:g}", keep=True, hold=200)
        page.EDIT[0]["gain"] = new
        page.live_update()

        def back():
            page.EDIT[:] = old
            page.editor.rebuild()
            page.live_update()
        api.undo(back)
        yield 1400
        api.say("Or as sliders, like Poweramp's equalizer")
        yield from api.click(page.view_btns["sliders"])
        was = page.sw.s.get("filters_view", "table")
        page.set_view("sliders", remember=False)
        api.undo(lambda: page.set_view(was, remember=False))
        api.spot_on(page.editor)
        yield 1500

    def save_demo(api):
        api.say("Name it (or keep the automatic name)")
        yield from api.type(page.name_edit, "My EQ", keep=True, hold=300)
        yield from api.at(page.formats_line, 0.2, 0.5, 1100, say="The files it writes: your EQ app's")
        api.say("Save filters writes them in your Saved EQs folder")
        b = button(page.result_box, "Save filters")
        yield from api.click(b)
        yield from api.note("Saved “My EQ”. (Demo: nothing was saved.)", b, 1500)
        api.say("Use on device: the EQ becomes a device's, switched on (or try it for 5 minutes)")
        yield from api.click(page.use_btn)
        from switcher.core import shown
        sw = page.sw
        names = [f"{shown(sw.record(d.key))}  ·  " + ("playing now" if d.key == sw.playing_key else "connected"
                                                       if d.connected else "not connected") for d in sw.devices][:5]
        m = yield from mock_menu(api, page.use_btn, (names or ["Headphones  ·  playing now"])
                                 + [None, "Try for 5 minutes on ▸"])
        yield from pick(api, m, 0)
        api.close(m)
        yield from api.note("Its EQ now, switched on. (Demo: nothing was changed.)", page.use_btn, 1500)

    def drag_actions():
        """The EQ graph's step: the first filter's handle dragged (right and up or down: its frequency and gain, the
        table and the numbers following), then where a double-click adds one. Put back after."""
        from PySide6.QtCore import QPointF
        from ui.eq_page_handles import handle_y
        if not page.EDIT or not getattr(page, "_handles", None):
            return [{"at": lambda: page.eqplot, "say": "Each filter of the EQ shown has a handle on the EQ graph"}]
        old = [dict(x) for x in page.EDIT]
        import math
        x0, y0 = math.log10(old[0]["freq"]), handle_y(old[0])
        lo, hi = page.eqplot.getPlotItem().vb.viewRange()[1]
        x1 = min(x0 + 0.3, math.log10(16000))
        y1 = max(lo * 0.8, min(hi * 0.8, y0 + (3 if y0 < 1 else -3)))

        def frac(x, y):
            vb = page.eqplot.getPlotItem().vb
            p = page.eqplot.viewport().mapTo(page.eqplot, page.eqplot.mapFromScene(vb.mapViewToScene(QPointF(x, y))))
            return (p.x() / max(1, page.eqplot.width()), p.y() / max(1, page.eqplot.height()))

        def put(p):
            page.no_trial = True  # (a demo never reaches a device: an EQ tried there doesn't follow it)
            hs = getattr(page, "_handles", [])
            if hs:
                hs[0].setPos(x0 + (x1 - x0) * p, y0 + (y1 - y0) * p)
            if p >= 1:
                page.handle_let_go()

        def back():
            page.EDIT[:] = [dict(x) for x in old]
            page.editor.rebuild()
            page.live_update()
            page.no_trial = False

        def words(p):
            f = page.EDIT[0] if page.EDIT else old[0]
            return f"{f['freq'] / 1000:.2f} kHz · {f['gain']:+.1f} dB" if f["freq"] >= 1000 else \
                f"{f['freq']:g} Hz · {f['gain']:+.1f} dB"
        return [{"drag": lambda: page.eqplot, "from": frac(x0, y0), "to": frac(x1, y1), "set": put, "undo": back,
                 "label": words, "ms": 1300, "say": "Drag a handle: left and right its frequency, up and down its gain"},
                {"at": lambda: page.editor, "x": 0.5, "y": 0.15, "say": "The table, the numbers and Listen follow"},
                {"at": lambda: page.eqplot, "x": 0.9, "y": 0.2,
                 "say": "The mouse wheel over a handle: its Q; right-click: its type, on or off, Remove"},
                {"at": lambda: page.eqplot, "x": 0.12, "y": 0.8, "say": "Double-click where there's none: a new filter"}]

    def hand_demo(api):
        items = ["Start empty", "A copy of the selected EQ", "From an EQ file…", "Paste filters…",
                 "From a device's profile ▸"]
        m = yield from mock_menu(api, page.hand_btn, items)
        api.spot_on(m)
        api.say("Start empty, or from an EQ you have (a file, pasted lines, a profile)")
        yield from pick(api, m, 0)
        api.close(m)
        undo = stage_hand(page)  # (an EQ by hand on the result card, as Start empty makes it: put back after)
        if undo is None:  # (an ABX test running: left as it is)
            yield from api.note("An EQ of your own, on the result card: add filters, then save it or use it on a "
                                "device. (Demo: nothing was changed.)", page.hand_btn, 1700)
            return
        api.undo(undo)
        yield from api.at(page.res_title, 0.1, 0.5, 1500,
                          say="An EQ of your own, on the result card: add filters, then save it or use it on a device")
        yield from api.at(page.hand_close, 0.5, 0.5, 1500, say="Close: back to what was shown before")
        yield from api.note("(Demo: nothing was changed.)", page.hand_close, 1200)

    def listen_demo(api):
        L = page.listen
        api.undo(L.render_ab)  # (put back last: the version buttons as the choice is again)
        api.say("Music, noise, a sweep, a tone or your own file")
        k = next((n for n in range(L.src.count()) if "pink" in L.src.itemText(n).lower()), min(1, L.src.count() - 1))
        yield from mock_combo(api, L.src, k)
        api.say("Play (the demo stays quiet)")
        yield from api.click(L.play_btn)
        api.stage_text(L.play_btn, "Stop")
        yield 500
        api.say("The volume: start low")
        yield from api.at(L.vol, 0.3, 0.5, 900)
        btns = [b for b in L.ab_box.findChildren(QPushButton) if b.isVisible()]
        if len(btns) > 1:
            api.say("Switch versions (keys 1-9)")
            yield from api.click(btns[1])
            api.stage_checked(btns[1], True)
            yield 600
            yield from api.click(btns[0])
            api.stage_checked(btns[0], True)
        yield from api.at(L.lm, 0.1, 0.5, 900, say="Level-matched: the same loudness for every version")

    def compare_ear_demo(api):
        from PySide6.QtCore import QSignalBlocker
        L = page.listen
        api.undo(L.render_ab)  # (put back last: the version buttons as the boxes are again)
        api.say("Blind test: the versions as letters, until Reveal")
        yield from api.click(L.blind, 0.1)
        api.stage_checked(L.blind, True)
        L.render_ab()
        yield 1300
        with QSignalBlocker(L.blind):
            L.blind.setChecked(False)
        L.render_ab()
        k = L.ears.findData("split")
        if k >= 0:
            api.say("Or a different version in each ear (swap them too: your ears differ)")
            yield from mock_combo(api, L.ears, k)
            L.render_ab()
            api.spot_on(L.split_row)
            yield 1500

    def abx_demo(api):
        L = page.listen
        if not L.abx_start.isEnabled() or L.abx is not None:
            yield 300
            return
        before = (L.active, L.picked)

        def back():
            L.abx_end(finished=False, quiet=True)
            L.active, L.picked = before
            L._apply()
            L.render_ab()
        api.undo(back)
        yield from api.at(L.abx_a, 0.3, 0.5, 800, say="An ABX test: choose A and B (here EQ off and the EQ)")
        yield from api.click(L.abx_start)
        L.abx_begin()
        api.spot_on(L.abx_box)
        yield 900
        api.say("Each trial X is A or B at random: listen to A, B and X as often as you like")
        yield from api.click(L.abx_hear["A"])
        L.abx_listen("A")
        yield 300
        yield from api.click(L.abx_hear["X"])
        L.abx_listen("X")
        yield 300
        api.say("Then say which X is (nothing says if you were right until the end)")
        yield from api.click(L.abx_says["A"])
        L.abx_answer("A")
        yield 600
        yield from api.note("At the end: your score, and how often guessing alone does as well. (Demo: nothing kept.)",
                            L.abx_box, 1600)

    def preset_demo(api):
        b = win.presets_btn
        names = page.preset_names()
        items = (names[:5] or [("No presets yet", False)]) + [None, "Save current settings as…", "Delete a preset ▸",
                                                              None, "Reset all settings…"]
        api.say("Click Presets")
        yield from api.click(b)
        m = yield from mock_menu(api, b, items)
        api.spot_on(m)
        api.say("“Save current settings as…”")
        yield from pick(api, m, items.index("Save current settings as…"))
        api.close(m)
        f = api.prompt("Save a preset", "Save the current settings as the preset:", near=b)
        api.spot_on(f)
        api.say("…under a name")
        f.edit.setText("")
        yield from api.type(f.edit, "Equalizer APO", keep=True, hold=300)
        yield from api.click(f.ok)
        api.close(f)
        api.t.typed = []
        yield from api.note("Saved: every setting, not your files. (Demo: nothing was saved.)", b, 1500)
        api.say("Later, click it in Presets to load all those settings at once")
        yield from api.click(b)
        m = yield from mock_menu(api, b, ["Equalizer APO"] + [x for x in items if x != ("No presets yet", False)])
        yield from pick(api, m, 0)
        api.close(m)
        yield from api.note("Loaded: all its settings are back.", b, 1300)

    def history_demo(api):
        from PySide6.QtCore import QSize
        from ui.history_window import HistoryWindow
        w = HistoryWindow(page)
        api.window(w, near=page.hist_btn, size=QSize(int(min(700, api.t.width() * 0.6)),
                                                             int(min(520, api.t.height() * 0.6))))
        api.spot_on(w.frame)
        yield from api.at(w.scroll, 0.4, 0.25, 1500, say="Your past EQs by day: Show brings one back with its files, "
                                                         "Keep to compare adds it to your EQs to compare")
        yield from api.at(w.q, 0.2, 0.5, 900, say="Search by IEM, target or method")

    steps = [
        {"chapter": "Overview", "title": "How an EQ job goes", "target": lambda: [page.target_box, page.measurement_box],
         "text": "Top to bottom: the graph, the target and your IEM or headphone, the EQ, then the result to save. Each "
                 "step has a short demo; nothing of yours changes.",
         "demo": [{"spot": lambda: page.target_combo}, {"at": lambda: page.target_combo, "say": "Choose the target: the sound you want"},
                  {"spot": lambda: page.measurement_combo},
                  {"at": lambda: page.measurement_combo, "say": "Choose your IEM or headphone's measurement"},
                  {"spot": lambda: page.sa}, {"at": lambda: page.sa, "say": "What the run will try: the settings are fitted for you"},
                  {"spot": lambda: page.run_btn}, {"click": lambda: page.run_btn, "say": "Run"},
                  {"spot": lambda: page.plot}, {"at": lambda: page.plot, "y": 0.4, "say": "Check the result on the graph, then save it"}]},
        {"chapter": "1 · Choose", "title": "Choose a target", "target": lambda: page.target_box,
         "text": "The sound you want (e.g. Harman, or a diffuse-field curve). Find… searches the app, this PC and the "
                 "online databases: type part of a name. The list beside it has the app's targets; Add… takes a file.",
         "demo": [{"click": in_card(page.target_combo, "Find…"), "say": "Click Find… by Target", "then": choose_target}]},
        {"chapter": "1 · Choose", "title": "Fine-tune the target (optional)",
         "target": lambda: [st.adjust_row, st.adjust_panel], "before": adjust_open, "after": adjust_close,
         "text": "Adjust (under Target) tilts the target (Tilt; Half-tilt: only above a frequency) and raises or lowers its "
                 "bass, ear gain, treble and air, one row each: the amount with − and +, then where (Hz) and how steep (Q). Leave them at 0 if the target "
                 "sounds right; Save as a target… keeps an adjusted one as your own.",
         "demo": lambda: adjust_demo(page)},
        {"chapter": "1 · Choose", "title": "Choose your IEM or headphone", "target": lambda: page.measurement_box,
         "text": "Search by brand or model. An online entry downloads when you Use it, and its files (left, right, "
                 "seatings) are averaged. Add… takes your own files from this PC (L and R, or several seatings).",
         "demo": [{"click": in_card(page.measurement_combo, "Find…"), "say": "Click Find… by Measurement (or press /)",
                   "then": choose_meas}]},
        {"chapter": "1 · Choose", "title": "Many results?", "target": lambda: page.measurement_box,
         "text": "Each result's rig tag says what it was measured on; ⇄ after it: its database has a conversion of its "
                 "own. The filters over the list keep one rig, type or source (“Fits your target's rig” first); "
                 "their lists are A to Z and open with a search box: type part of a source's name to find it.",
         "demo": [{"click": in_card(page.measurement_combo, "Find…"), "say": "Search as before", "then": many_results}]},
        {"chapter": "1 · Choose", "title": "Several measurements of the same model?",
         "target": lambda: button(page, "Other measurements of this model…"),
         "text": "Ranks every measurement of your model for your target: the rig first, then how well they agree, "
                 "the bass seal and the seatings; it can average several from one rig.",
         "demo": [{"click": lambda: button(page, "Other measurements of this model…"),
                   "say": "Click “Other measurements of this model…”", "then": compare_window}]},
        {"chapter": "1 · Choose", "title": "Measured on a different rig?",
         "target": lambda: page.graph_note if getattr(page, "rig_note", "") else page.measurement_note,
         "text": lambda: ("The line under the graph says so: " + page.rig_note.rstrip(".") + ". The target is then "
                          "converted to your measurement's rig (Settings › Target › Rig conversion); the shaded band "
                          "shows how far off it may still be." if getattr(page, "rig_note", "") else
                          "The line under Measurement says which rig your IEM was measured on (B&K 5128, 711 coupler…). "
                          "A target is made for one rig: when it's another, the line under the graph says so and the "
                          "target is converted to your measurement's rig (Settings › Target › Rig conversion)."),
         "demo": lambda: [{"at": lambda: page.graph_note, "x": 0.3, "hold": 1300, "say": "The note: the rig of each"},
                          {"run": rig_demo, "say": "As made, and converted"}]
         if getattr(page, "rig_note", "") and ((page.curves or {}).get("rig") or {}).get("applied") else
         [{"at": lambda: page.measurement_note, "x": 0.3, "hold": 1500, "say": "Which rig it was measured on"}]},
        {"chapter": "2 · Settings", "title": "Your EQ app", "target": lambda: [page.app_combo, page.app_note],
         "text": "Say which app or device will play the EQ (Windows, Mac, Linux, Android, iPhone, a DAC or squig.link). "
                 "Its own limits are kept (bands, gain, Q, a graphic EQ's sliders) and Save filters writes exactly the "
                 "file it imports.",
         "demo": [{"click": lambda: page.app_combo, "say": "Click Your EQ app", "then": app_demo}]},
        {"chapter": "2 · Settings", "title": "Pick an EQ method", "target": lambda: [page.mode_combo, page.mode_hint],
         "text": "Choose by where the EQ goes. Best fit (the default) for EQ apps and devices: the closest match. The "
                 "website methods give the values to type into squiglink's or listener800's AutoEQ.",
         "demo": [{"click": lambda: page.mode_combo, "say": "Click the method", "then": mode_demo}]},
        {"chapter": "2 · Settings", "title": "Automatic settings",
         "target": lambda: [st.fold.btn, st.fold.summary, st.auto_on, st.why], "before": settings_open, "after": settings_close,
         "text": "The Settings fold holds what you'd change: the automatic settings, fitted to your files with a reason "
                 "for each; the filters; Scoring. The rest is set for you (Advanced, under it).",
         "demo": [{"at": lambda: st.fold.btn, "x": 0.1, "say": "Settings: what you'd change for the EQ"},
                  {"at": lambda: st.auto_on, "x": 0.1, "say": "They follow the measurement and target you chose"},
                  {"at": lambda: st.why, "x": 0.3, "y": 0.3, "say": "Each automatic value comes with its reason"}]},
        {"chapter": "2 · Settings", "title": "What a run tries", "target": lambda: [page.sa],
         "text": "Best fit adds filters one at a time under every boost and Q limit that suits your curves, until the "
                 "EQ sounds the same as the target. This says what the next run tries and how long it takes on this "
                 "PC: seconds for most IEMs.",
         "demo": [{"at": lambda: page.estimate, "x": 0.2, "say": "How long a run takes on this PC"},
                  {"at": lambda: page.sa_what, "x": 0.2, "say": "What the next run tries"}]},
        {"chapter": "2 · Settings", "title": "Your own values", "target": lambda: [st.form],
         "before": settings_open, "after": settings_close,
         "text": "Change a setting and it's marked “yours”: new files leave it alone. Click “yours ↺” "
                 "to hand it back, or untick Automatic settings.",
         "demo": [{"run": your_value, "say": "Type your own value and press Enter"},
                  {"at": lambda: st.auto_on, "x": 0.1, "say": "Or turn Automatic settings off"}]},
        {"chapter": "2 · Settings", "title": "Start from your own filters",
         "target": lambda: st.form.fields["best_fit.start_filters"] if st.form.fields["best_fit.start_filters"].isVisible() else None,
         "alt": lambda: page.mode_combo, "before": settings_open, "after": settings_close,
         "text": "Best fit can start from an EQ you already have: type its filters, edit them as a table, or load its "
                 "file. It adds filters to yours, or adjusts them too.",
         "alt_text": "With Best fit as the method (and an app that takes any filters), Settings › “Start from your own "
                     "filters” takes an EQ you already have; Best fit adds filters to it.",
         "demo": [{"type": lambda: st.form.fields["best_fit.start_filters"].box,
                   "text": "Filter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1", "keep": True, "hold": 300,
                   "say": "Type them as Equalizer APO lines…"},
                  {"at": lambda: button(st.fold, "Edit as a table…"), "say": "…or as a table or sliders"},
                  {"at": lambda: button(st.fold, "Load an EQ file…"), "say": "Or load an EQ file; with filters there, "
                   "“Keep them exactly” keeps them as they are, else the fit adjusts them too"}],
         "alt_demo": [{"at": lambda: page.mode_combo, "say": "Choose Best fit as the method to start from your own filters"}]},
        {"chapter": "3 · Run & review", "title": "Run", "target": lambda: [page.run_btn, page.queue_btn, page.estimate],
         "text": "Finds the filters. Longer runs show their progress and can be cancelled. Run several… makes EQs for "
                 "several IEMs or targets in one go (each saved and kept in History).",
         "demo": [{"click": lambda: page.run_btn, "say": "Click Run", "then": run_demo},
                  {"at": lambda: page.queue_btn, "say": "Run several…: several IEMs or targets in one go"}]},
        {"chapter": "3 · Run & review", "title": "Or make it by hand", "target": lambda: page.hand_btn,
         "text": "By hand makes an EQ yourself, shown as a result of its own: start empty, or from an EQ file "
                 "(Equalizer APO, AutoEq, Room EQ Wizard, Peace), pasted filters, a device's profile or a copy of the EQ "
                 "shown, then add and change its filters. Save, Use on device and Listen work as for a run; a "
                 "measurement and target are optional. Close goes back to what was shown before.",
         "demo": [{"click": lambda: page.hand_btn, "say": "Click By hand", "then": hand_demo}]},
        {"chapter": "3 · Run & review", "title": "Check it on the graph", "target": lambda: page.plot, "ready": has_curves,
         "text": "Orange: your IEM. Dashed: the target. Blue: with the EQ. Under it, pink: the EQ itself (above 0 "
                 "boosts, below cuts). Point at the graph for each curve's value; the shaded ends aren't scored.",
         "demo": lambda: [{"run": graph_demo, "say": "With the EQ, your IEM becomes the blue curve, close to the target"},
                          {"at": lambda: page.plot, "x": 0.3, "y": 0.35, "then": plot_value(page, 0.3, 0.35),
                           "say": "Point at the graph: its values show above it"},
                          {"at": lambda: page.plot, "x": 0.72, "y": 0.4, "then": plot_value(page, 0.72, 0.4),
                           "say": "Each curve's dB at that frequency"}] if page.curves else []},
        {"chapter": "3 · Run & review", "title": "Graph views", "ready": has_curves,
         "target": lambda: [page.view_combo, page.yrange_combo] + ([page.channels_chk] if page.channels_chk.isVisible() else []),
         "avoid": lambda: [page.plot],
         "text": "View › “Relative to target” shows only what's left to correct (0 dB = on target). Y range zooms in; "
                 "Channels shows each file's curve too.",
         "demo": lambda: [{"click": lambda: page.view_combo, "say": "Relative to target: what's left to correct",
                           "then": lambda api: views_demo(api, view="rel")},
                          {"click": lambda: page.yrange_combo, "say": "Y range: zoom in (e.g. 30 dB)",
                           "then": lambda api: views_demo(api, y="30")}]
         + ([{"click": lambda: page.channels_chk, "x": 0.1, "say": "Channels: each file's curve as well as their average",
              "then": lambda: page.demo_graph(channels=True)}] if page.channels_chk.isVisible() else [])},
        {"chapter": "3 · Run & review", "title": "Your result",
         "target": lambda: [page.res_title, page.res_sub] + list(page.chips.values()) + [page.count_combo, page.cmp_btn]
         + ([page.pick_lab] if page.pick_lab.isVisible() else []),
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "After a run the result appears under the settings: the error, the pre-amp to set in your EQ "
                         "app and the filters. The line under the numbers says whether it sounds the same as the target "
                         f"(within {page.S['scoring'].get('ear_db', 0.25):g} dB everywhere, as the ear hears it) or, when "
                         "your EQ app's limits can't get there, "
                         "how far off it is and where. “Fewer or more filters” shows the best result for each count; "
                         "Compare… puts two EQs side by side." + example(),
         "demo": lambda: [{"at": lambda: page.chips["error"], "say": "How far from the target, in the scored range"},
                          *([{"at": lambda: page.pick_lab, "x": 0.2,
                              "say": "Whether it sounds the same as the target, as the ear hears it"}]
                            if page.pick_lab.isVisible() else []),
                          {"at": lambda: page.chips["preamp"], "say": "Set this pre-amp in your EQ app"},
                          {"run": result_demo, "say": "The best result for each filter count"},
                          {"at": lambda: page.cmp_btn, "say": "Compare…: two EQs side by side"}]},
        {"chapter": "3 · Run & review", "title": "Edit the filters", "target": lambda: [page.editor, page.retry_btn],
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "Change any filter in the table or as sliders: the numbers and the graph follow. Revert brings "
                         "the run's filters back; Retry from these filters runs Best fit again from yours." + example(),
         "demo": [{"run": edit_demo, "say": "Change any value: the numbers and the graph follow"},
                  {"at": lambda: page.retry_btn, "say": "Retry: Best fit again, from your filters"}]},
        {"chapter": "3 · Run & review", "title": "Edit on the EQ graph", "target": lambda: page.eqplot,
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "Each filter has a handle on the EQ graph, under the graph, numbered as in the table. Drag it: "
                         "left and right its frequency, up and down its gain; the mouse wheel over it: its Q; "
                         "right-click: its type, on or off, Remove. Double-click where there's none for a new filter. "
                         "An EQ you're trying on a device plays each change there too." + example(),
         "demo": lambda: drag_actions()},
        {"chapter": "3 · Run & review", "title": "Save it, or use it on a device",
         "target": lambda: [page.name_edit, page.formats_line, button(page.result_box, "Save filters"), page.use_btn],
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "Save filters writes your EQ app's file under the File name; Copy puts the filters on the "
                         "clipboard; Use on device makes the EQ a device's profile and switches it on (or tries it there "
                         "for 5 minutes); Keep to compare adds it to your EQs to compare; Report makes an HTML page."
                         + example(),
         "demo": [{"run": save_demo, "say": "Name it, save it, or use it on a device"}]},
        {"chapter": "3 · Run & review", "title": "Listen", "target": lambda: page.listen, "ready": lambda: page.listen.isVisible(),
         "text": "Play music, noise, a sweep, a tone or your own song through the EQ on your IEM or headphone, and "
                 "switch between versions. Start quiet.",
         "demo": [{"run": listen_demo, "say": "Choose a sound, play, switch versions"}]},
        {"chapter": "3 · Run & review", "title": "Your EQs to compare", "target": lambda: page.listen.pins_box,
         "ready": lambda: page.listen.isVisible(),
         "text": "Keep the EQs you want to hear side by side: from the result card (Keep to compare), History, an "
                 "EQ file or pasted filters. Each IEM or headphone has its own list, kept between sessions; ticked "
                 "Graph: on the graph too.",
         "demo": [{"at": lambda: button(page.listen, "The selected EQ"), "say": "The EQ on the result card"},
                  {"at": lambda: button(page.listen, "From an EQ file…"),
                   "say": "An EQ file (Equalizer APO, Room EQ Wizard, Peace…)"},
                  {"at": lambda: button(page.listen, "Paste filters…"), "say": "Or filters pasted from anywhere"}]},
        {"chapter": "3 · Run & review", "title": "Compare by ear", "target": lambda: page.listen,
         "ready": lambda: page.listen.isVisible(),
         "text": "Level-matched so you compare the sound, not the volume. A blind test hides which is which; or put a "
                 "different version in each ear. An ABX test says whether you can really tell two apart: each trial X "
                 "is A or B at random, you say which, and at the end comes your score and how often guessing alone "
                 "does as well.",
         "demo": [{"run": compare_ear_demo, "say": "A blind test, or a version in each ear"},
                  {"run": abx_demo, "say": "An ABX test: can you really tell them apart?"}]},
        {"chapter": "More", "title": "Presets", "target": lambda: win.presets_btn, "top bar": True,
         "text": "Save all settings under a name and load them later, e.g. one for the website and one for Equalizer "
                 "APO. A preset keeps settings, not your files.",
         "demo": [{"run": preset_demo, "say": "Save the settings as a preset, load it later"}]},
        {"chapter": "More", "title": "History", "target": lambda: page.hist_btn,
         "text": "Your past EQs, kept after you close the app: the ones you save or copy (or every run: Advanced › "
                 "History). Show one to bring it back with its files, or Keep to compare to add it to your EQs to compare.",
         "demo": lambda: [{"click": lambda: page.hist_btn, "say": "History: your past EQs", "then": history_demo}]
         + ([{"at": lambda: page.eqd_show, "say": "Under Measurement: when you've EQ'd it before; Show in History… opens those"}]
            if page.eqd_show.isVisible() else [])},
        {"chapter": "More", "title": "Only have a picture of a graph?", "target": lambda: page.trace_btn,
         "text": "Trace a graph image… turns a graph's picture into a measurement or a target. It has its own Guide. You can "
                 "also paste or drop a picture on the window.",
         "demo": [{"at": lambda: page.trace_btn, "say": "A picture of a graph becomes a curve"}]},
        {"chapter": "More", "title": "Your devices", "target": lambda: win.nav["devices"], "top bar": True,
         "text": "Devices gives each playback device its own EQ through Equalizer APO, switched by itself when the "
                 "device plays, with a line saying whether it really plays; Profiles lists the EQs. Use on device puts "
                 "a result there in one click. Two hotkeys work in any program (Settings): one goes through the "
                 "playing device's EQs; the other switches its EQ off for now and back, level-matched, to compare.",
         "demo": [{"at": lambda: win.nav["devices"], "say": "Each device's own EQ"},
                  {"at": lambda: win.nav["profiles"], "say": "Your EQs, as profiles"},
                  {"at": lambda: win.nav["settings"], "say": "The hotkeys: through the EQs, and EQ off and on to compare"}]},
        {"chapter": "More", "title": "Settings", "target": lambda: st.adv.btn,
         "text": "Advanced, under Settings: what's set for you (Best fit's layout, limits and penalties, the website "
                 "sweep's lists, the website's own details, the files Save writes, History, CPU cores). A list of more "
                 "than 15 choices, like Layout, opens with a search box. The Settings screen (top bar) has where your "
                 "files are, backups, Online / Offline and Start with Windows.",
         "demo": lambda: [{"at": lambda: st.adv.btn, "x": 0.1, "say": "Advanced: what's set for you"}]
         + ([{"at": lambda: win.nav["settings"], "say": "The app's own settings"}] if hasattr(win, "nav") else [])},
        {"chapter": "More", "title": "Help, and that's it", "target": lambda: win.help_btn, "top bar": True,
         "text": "Help explains every term (Q, shelf, rig, pre-amp…) and answers common questions; point at a setting "
                 "for what it does, and F1 opens its entry. Open the Guide any time to see a step again.",
         "demo": [{"at": lambda: win.help_btn, "say": "Help: every term, and the questions that come up most"},
                  {"at": lambda: page.sa, "say": "Point at a setting for what it does; F1 opens its entry in Help"}],
         "buttons": [("Open Help", lambda: win.open_help())] if hasattr(win, "open_help") else []},
    ]
    # (the steps about the app window's top bar: only when the screen is in it, not on its own as in the checks)
    return [s for s in steps if not s.get("top bar") or hasattr(win, "nav")]


def start_eq(page):
    return tour.Tour(page, eq_steps(page))
