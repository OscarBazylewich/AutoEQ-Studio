"""Make an EQ's Guide (AutoEQ Local's guide.js STEPS, told for AutoEQ Studio's window; ui/tour.py shows it):
eq_steps(page), every step in order (Overview, 1 · Choose, 2 · Settings, 3 · Run & review, More) with its words,
the controls it lights and its demo, and start_eq(page), the tour that shows them. The demos' helpers are in
guide_demos.py. Keep the steps in their order: the checks find steps by their titles.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from ui import tasks, theme, tour
from ui.guide_demos import (adjust_demo, button, choose_row, point_at_menu_row, demo_filters, fold_before_after,
                            meas_with_eq, mock_combo, mock_menu, open_picker, picker_rows, plot_value, show_on_graph,
                            stage_manual, stage_result, type_search, wait_for_background, way_before_after)

# (A menu a demo draws is the Guide's own, guide_demos.mock_menu: as wide as its longest row and drawn as a real menu;
# a row ending in " ▸" is a submenu's, Windows 11's chevron at its right, as the app's menus draw it.)


# ---------------------------------------------------------------- Make an EQ's Guide
def eq_steps(page):
    """Make an EQ's Guide."""
    win = page.window()
    st = page.settings
    has_curves = lambda: bool(page.curves)
    settings_open, settings_close = fold_before_after(st.fold.btn, None)
    about_open, about_close = fold_before_after(st.why_fold.btn, settings_open)  # (About these settings: in Settings)
    more_open, more_close = fold_before_after(st.adv.btn, None)

    was_tab = {}

    def best_fit_tab():  # (More settings, open on its Best fit tab: Start from your filters is there)
        more_open()
        was_tab["i"] = st.adv_form.pages.currentIndex()
        st.adv_form.show_tab(0)

    def tab_back():  # (your tab of More settings back, then the fold as it was: it stayed on Best fit, 2026-11-10)
        if "i" in was_tab:
            st.adv_form.show_tab(was_tab.pop("i"))
        more_close()
    # (Make the EQ shows one way's steps: a step about the other's shows its tab, then the one that was shown)
    auto_on, auto_off = way_before_after(page, "auto")
    auto_settings_open, auto_settings_close = way_before_after(page, "auto", (best_fit_tab, tab_back))
    hand_on, hand_off = way_before_after(page, "hand")
    staged = {}

    def result_before():
        staged["undo"] = stage_result(page)

    def result_after():
        u = staged.pop("undo", None)
        if u:
            u()
    example = lambda: " (Before you calculate, this is an example from your files.)" if staged.get("undo") else ""
    col = theme.graph_colours()

    # ------------------------------------------------ demos that open things
    norm = lambda s: "".join(ch for ch in s.lower() if ch.isalnum())

    def find_target_demo(api):
        pk = open_picker(page, api, "target")
        api.say("Type a part of a name")
        active = page.inputs.get("active_target") or ""
        mine = [n for n in page.inputs.get("targets", []) if n != active]
        q = "harman" if any("harman" in n.lower() for n in mine) or not mine else \
            " ".join(w for w in mine[0].rsplit(".", 1)[0].replace("_", " ").split()[:2]).lower()
        yield from type_search(api, pk, q)
        api.say("Click the target that you want. The graph shows it")
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

    def find_meas_demo(api):
        pk = open_picker(page, api, "measurement")
        api.say("Type the name of the manufacturer or of the model")
        yield from type_search(api, pk, model().lower())
        api.say("Click the measurement that you want. The graph shows it")
        got = yield from choose_row(page, api, pk, same_model, page.measurement_combo)
        vals = got[1] if got else ((page.curves or {}).get("meas") if page.curves else None)
        yield from show_on_graph(page, api, "meas", vals, got[0] if got else model(), page.measurement_box)

    def many_results_demo(api):
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
            api.say("The rig tag of a result: the rig of the measurement, and how the app found it")
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
            api.say("⇄: a rig change by its database")
            yield from api.move_to(conv)
            yield from api.note(tip, conv if tasks.alive(conv) else None, 3000)
        api.say("Show only one rig (or type, or source)")
        yield from api.move_to(pk.f_rig, 0.3, 0.5)
        yield from api.ripple()
        tr = pk.target_rig() if hasattr(pk, "target_rig") else ""
        pk.filters["measurement"]["rig"] = "fits" if tr else next(iter(page.meta.get("rigs") or {"5128": 1}))
        pk.render()
        yield from api.note("The list shows only the measurements on the same rig as your target, or changed for it. "
                            "Type, Source, "
                            "“Known rig” and “Available to download” make the list shorter." if tr else
                            "The list shows only the measurements on that rig. Type, Source, “Known rig” and "
                            "“Available to download” make the list shorter.", pk.f_rig, 2600)
        names = [pk.f_site.itemText(i) for i in range(1, pk.f_site.count())]
        word = "crin" if any("crin" in n.lower() for n in names) else (names[-1][:4].lower() if names else "")
        found = [n for n in names if word and word in n.lower()][:6]
        if found:  # (the Source list as it opens: its search box, a word typed, what's left)
            api.say("Many sources? Their list has a search box. Type a part of a name")
            yield from api.move_to(pk.f_site, 0.3, 0.5)
            yield from api.ripple()
            m = api.mock(pk.f_site, found, width=max(pk.f_site.width(), 300), search=word, typed=True)
            m.hover(0)
            yield 2200
            api.close(m)

    def compare_window_demo(api):
        """Which measurement to use?, shown (its search isn't run: that would download measurements)."""
        from ui import compare_window as cw
        real = cw.CompareWindow.search_measurements
        cw.CompareWindow.search_measurements = lambda self, auto=False: None
        try:
            w = cw.CompareWindow(page)
        finally:
            cw.CompareWindow.search_measurements = real
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
        w.status.setText(f"All measurements of “{w.q.text() or model()}” in the online databases, this PC and the "
                         "app, sorted for your target. (The Guide does not download them.)")
        api.spot_on(w.frame)
        api.say("All measurements of your model, sorted for your target. The window shows how it sorts them")
        yield from api.move_to(w.q, 0.3)
        yield 900
        api.say("The rig, how much they agree, the bass seal and the seatings")
        yield from api.move_to(w.chart, 0.4, 0.5)
        yield 1100
        api.say("Search finds them. Use gives you one measurement, or the average of some measurements on one rig")
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
        res = yield from wait_for_background(lambda: page.svc.call("/api/curves", {"settings": s}))
        if not res or "target" not in res:
            yield 400
            return
        import numpy as np
        yield from api.pin_graph(page, page.measurement_box)
        conv, made = np.asarray(c["target"], dtype=float), np.asarray(res["target"], dtype=float)
        item = api.curve(page, conv, col["target"], 2.6, Qt.DashLine, name="Target (demo)")
        api.say("Rig change off: the target for its rig")
        yield from api.morph(page, item, conv, made, 1200)
        yield 1300
        api.say("On (Settings › Target): the target for the rig of your measurement")
        yield from api.morph(page, item, made, conv, 1200)
        yield 900

    def app_demo(api):
        combo = page.app_combo
        now = combo.currentData() or ""
        key = next((k for k in ("poweramp", "wavelet", "apo", "peace") if k != now and combo.findData(k) >= 0), None)
        i = combo.findData(key) if key else -1
        api.say("Apps and devices by name, each with its systems")
        yield from mock_combo(api, combo, i)
        if key:
            api.stage(lambda: page.app_note.text(), page.app_note.setText, page.app_note_text(key))
        api.spot_on(page.app_note)
        api.say("The EQ stays in its limits, and Save filters saves the file that the app imports")
        yield from api.at(page.app_note, 0.5, 0.5, 1700, say="The ⓘ after its label: its limits, their source, and how "
                                                            "to load the EQ")

    def mode_demo(api):
        combo = page.mode_combo
        keys = [combo.itemData(k) for k in range(combo.count())]
        to = "site_sweep" if page.S["mode"] == "best_fit" else "best_fit"
        api.say("Select where you will use the EQ")
        yield from mock_combo(api, combo, keys.index(to) if to in keys else 0)
        from ui.eq_page import MODE_HINT
        api.stage(page.mode_hint.text, page.mode_hint.setText, MODE_HINT.get(to, ""))
        yield from api.at(page.mode_hint, 0.5, 0.5, 1300, say="The ⓘ after its label: its function")

    def your_value_demo(api):
        """A value of your own typed into the method's first box: it's marked “yours ↺” (shown, not kept)."""
        f = _first_box()
        if f is None:
            yield 300
            return
        api.say("Type your value. Press Enter")
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
        # (the tag's words: "yours ↺" before the STE words, "your value ↺" after; "auto" / "automatic" otherwise)
        api.undo(lambda: f.set_tag(None if old is None else "yours" if old.startswith("your") else "auto"))
        api.say("It shows “your value ↺”. Click it to make it automatic again")
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
        page.progress_text.setText("In progress…")
        page.progress_text.show()  # (the line under Run shows only while it says something)
        api.spot_on(page.cancel_btn, page.progress, page.progress_text)
        yield 300
        yield from api.at(page.cancel_btn, 0.5, 0.5, 900, say="Cancel stops it")
        api.say("The bar and the line show how much is completed while the app calculates")
        n = len(demo_filters(page)) or 6
        yield from api.tween(1800, lambda p: (page.progress.setValue(int(p * 100)), page.progress_text.setText(
            f"Best fit adds one filter at a time: {max(1, round(n * p))}/{n} · {max(1, round(p * 4))} s")))
        if page.curves:
            api.say("The graph shows your IEM with the EQ (blue)")
            yield from api.pin_graph(page, page.run_btn)
            meas = page.curves["meas"]
            item = api.curve(page, meas, col["with_eq"], 2.6, name="With the EQ (demo)")
            yield from api.morph(page, item, meas, meas_with_eq(page), 1500)
            yield from api.note("With the EQ: near the target", api.t.pin or page.plot, 1500, below="inside")

    def graph_demo(api):
        if not page.curves:
            yield 300
            return
        api.say("With the EQ, your IEM (orange) changes to the blue curve, near the dashed target")
        api.spot_on(page.plot)
        meas = page.curves["meas"]
        item = api.curve(page, meas, col["with_eq"], 2.6, name="With the EQ (demo)")
        yield from api.morph(page, item, meas, meas_with_eq(page), 1500)
        yield 700

    def views_demo(api, view=None, y=None):
        combo = page.view_combo if view is not None else page.yrange_combo
        i = combo.findData(view if view is not None else y)
        yield from mock_combo(api, combo, i)
        api.undo(page.demo_graph(**({"view": view} if view is not None else {"y": y})))
        api.spot_on(page.plot)
        yield 1500

    def result_demo(api):
        api.say("“Number of filters”: the best result for each number of filters")
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
        api.say("Change a value: the numbers and the graph change with it")
        old = [dict(x) for x in page.EDIT]
        try:
            v = float(box.text())
        except ValueError:
            v = 0.0
        new = round(v - 2 if v > 0 else v + 2, 1)
        yield from api.type(box, f"{new:g}", keep=True, hold=200)
        page.EDIT[0]["gain"] = new
        page.live_update()
        page.request_live_graph()  # (as an edit by hand: the graph floats over the page while it's out of sight)

        def back():
            page.EDIT[:] = old
            page.editor.rebuild()
            page.live_update()
            page.hide_live_graph()
        api.undo(back)
        lg = getattr(page, "live_graph", None)
        if lg is not None and lg.isVisible():
            api.spot_on(lg)
            api.keep_clear(lg)  # (the card off it: it sat over the floating graph)
            yield from api.at(lg, 0.5, 0.4, 1600, say="If you cannot see the graph, a copy of it shows on the page while you edit")
        else:
            yield 1400
        api.say("Or as sliders: a graphic EQ, with the gain of each filter filled from 0 dB")
        yield from api.click(page.view_btns["sliders"])
        was = page.sw.s.get("filters_view", "table")
        page.set_view("sliders", remember=False)
        api.undo(lambda: page.set_view(was, remember=False))
        api.spot_on(page.editor)
        yield 1500

    def save_demo(api):
        api.say("Type a name (or keep the automatic name)")
        yield from api.type(page.name_edit, "New EQ", keep=True, hold=300)
        yield from api.at(page.formats_line, 0.2, 0.5, 1100, say="The files that it saves: for your EQ app")
        api.say("Save filters saves them in your Saved EQs folder")
        b = button(page.result_box, "Save filters")
        yield from api.click(b)
        yield from api.note("The app saves “New EQ”. (Demo: the app did not save a file.)", b, 1500)
        api.say("Use on device: the EQ becomes a new profile of a device, or it goes into a profile that you have")
        yield from api.click(page.use_btn)
        from switcher.core import shown
        from ui.eq_page_parts import row_name, update_row_words, use_menu_order
        sw = page.sw
        # (the real menu's rows, in its sequence (one function for the two): the devices, then the profiles that are
        # on, then Update a profile; the mock's rows have no keys' column; the words cut as the real menu cuts them)
        keys, seen = use_menu_order(sw)
        page.use_menu.ensurePolished()
        fm = page.use_menu.fontMetrics()
        names = []
        for k in keys[:5]:
            d = sw.device(k)
            names.append(f"{row_name(fm, shown(sw.record(k)))[0]}  ·  " + ("active" if k == sw.playing_key else
                                                                          "connected" if d and d.connected else
                                                                          "not connected"))
        ups = []
        for pid in seen[:2]:
            text, where, _ = update_row_words(fm, sw.profiles()[pid]["name"],
                                              [shown(sw.record(k)) for k in sw.on_for(pid)])
            ups.append(f"{text}  ·  {where}")
        rows = (names or ["Headphones  ·  active"]) + [None] + ups + ["Update a profile ▸", None, "Use for 5 minutes on ▸"]
        # (only Use on device lit, and the typed name taken away, while its menu shows: with the Update rows the menu is
        # wider, so at 1000 x 900 the card's only room is over File name, and the field's light and the typed “New EQ”
        # showed over the card's words and buttons, 2026-11-11)
        api.spot_to(page.use_btn)
        api.untype(page.name_edit)
        m = yield from mock_menu(api, page.use_btn, rows)
        api.say("Update a profile: the EQ goes into a profile that you have, and the profile keeps its devices")
        yield from point_at_menu_row(api, m, rows.index("Update a profile ▸"), hold=900)
        api.say("A device: the EQ becomes its new profile, and it is on")
        yield from point_at_menu_row(api, m, 0)
        api.close(m)
        yield from api.note("It is the EQ of the device, and it is on. (Demo: the device did not change.)",
                            page.use_btn, 1500)

    def drag_actions():
        """The EQ graph's step: the first filter's handle dragged (right and up or down: its frequency and gain, the
        table and the numbers following), then where a double-click adds one. Put back after."""
        from PySide6.QtCore import QPointF
        from ui.eq_page_handles import handle_y
        if not page.EDIT or not getattr(page, "_handles", None):
            return [{"at": lambda: page.eqplot, "say": "Each filter of the EQ has a handle on the EQ graph"}]
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
                 "label": words, "ms": 1300,
                 "say": "Drag a handle: left and right for its frequency, up and down for its gain"},
                {"at": lambda: page.editor, "x": 0.5, "y": 0.15, "say": "The table, the numbers and Listen change with it"},
                {"at": lambda: page.eqplot, "x": 0.9, "y": 0.2,
                 "say": "The mouse wheel on a handle: its Q. Right-click: its type, on or off, Remove"},
                {"at": lambda: page.eqplot, "x": 0.12, "y": 0.8,
                 "say": "Double-click where there is no handle: a new filter"}]

    def way_demo(api):
        """Each tab in turn: the card shows that way's steps; the way shown before, back after."""
        was = getattr(page, "way", "auto")
        api.undo(lambda: page.set_way(was, remember=False))
        for key, say in (("hand", "Manually: Start from, then Start"), ("auto", "Automatically: the method, then Calculate")):
            api.say(say)
            yield from api.click(page.way_btns[key])
            page.set_way(key, remember=False)
            api.spot_on(page.hand_w if key == "hand" else page.auto_w)
            yield 1300

    def manual_demo(api):
        api.undo(page.manual_source_changed)  # (put back last: the note and Start's words for the choice as it is again)
        api.say("Start from: an empty EQ, or an EQ that you have (a file, pasted lines, a profile, a copy)")
        yield from mock_combo(api, page.hand_source, 0)
        page.manual_source_changed()
        yield from api.click(page.hand_start)
        undo = stage_manual(page)  # (an EQ by hand on the result card, as Start empty makes it: put back after)
        if undo is None:  # (an ABX test running: left as it is)
            yield from api.note("A manual EQ on the result card: you add filters, then you save it or use it on a "
                                "device. (Demo: your work does not change.)", page.hand_start, 1700)
            return
        api.undo(undo)
        yield from api.at(page.res_title, 0.1, 0.5, 1500, say="A manual EQ on the result card: you add filters, then "
                                                              "you save it or use it on a device")
        yield from api.at(page.hand_close, 0.5, 0.5, 1500, say="Close: the result card shows the previous EQ again")
        yield from api.note("(Demo: your work does not change.)", page.hand_close, 1200)

    def listen_demo(api):
        L = page.listen
        api.undo(L.render_versions)  # (put back last: the version buttons as the choice is again)
        api.say("Music, noise, a sweep, a tone or your audio file")
        k = next((n for n in range(L.src.count()) if "pink" in L.src.itemText(n).lower()), min(1, L.src.count() - 1))
        yield from mock_combo(api, L.src, k)
        api.say("Play (the demo makes no sound)")
        yield from api.click(L.play_btn)
        api.stage_text(L.play_btn, "Stop")
        yield 500
        api.say("The volume: start at a low value")
        yield from api.at(L.vol, 0.3, 0.5, 900)
        btns = [b for b in L.ab_box.findChildren(QPushButton) if b.isVisible()]
        if len(btns) > 1:
            api.say("Change the version (keys 1-9)")
            yield from api.click(btns[1])
            api.stage_checked(btns[1], True)
            yield 600
            yield from api.click(btns[0])
            api.stage_checked(btns[0], True)

    def compare_ear_demo(api):
        from PySide6.QtCore import QSignalBlocker
        L = page.listen
        api.undo(L.render_versions)  # (put back last: the version buttons as the boxes are again)
        # (Same level is in the row of how you compare, with the ears and Hide the names: the UI audit, 2026-11-08)
        yield from api.at(L.lm, 0.1, 0.5, 900, say="Same level: the same loudness for each version")
        api.say("Hide the names: the versions show as A, B, C… until you click Show the names")
        yield from api.click(L.blind, 0.1)
        api.stage_checked(L.blind, True)
        L.render_versions()
        yield 1300
        with QSignalBlocker(L.blind):
            L.blind.setChecked(False)
        L.render_versions()
        k = L.ears.findData("split")
        if k >= 0:
            api.say("Or a different version in each ear (also interchange them, because your ears are different)")
            yield from mock_combo(api, L.ears, k)
            L.render_versions()
            api.spot_on(L.split_row)
            yield 1500

    def abx_demo(api):
        L = page.listen
        if len(L.versions()) < 2 or L.abx is not None:  # (two versions to test: else nothing to show)
            yield 300
            return
        before = (L.active, L.picked)

        def back():
            L.abx_end(finished=False, quiet=True)
            L.active, L.picked = before
            L._apply_to_engine()
            L.render_versions()
        api.undo(back)
        yield from api.at(L.abx_a, 0.3, 0.5, 800, say="An ABX test: select A and B (here, EQ off and the EQ)")
        yield from api.click(L.abx_start)
        L.abx_begin()
        api.spot_on(L.abx_box)
        yield 900
        api.say("In each trial, X is A or B, randomly. Listen to A, B and X as frequently as necessary")
        yield from api.click(L.abx_hear["A"])
        L.abx_listen("A")
        yield 300
        yield from api.click(L.abx_hear["X"])
        L.abx_listen("X")
        yield 300
        api.say("Then click “X is A” or “X is B” (the app shows the results only at the end)")
        yield from api.click(L.abx_says["A"])
        L.abx_answer("A")
        yield 600
        yield from api.note("At the end: your result, and how frequently random selections get the same result. "
                            "(Demo: the app keeps no result.)", L.abx_box, 1600)

    def preset_demo(api):
        b = win.presets_btn
        names = page.preset_names()
        items = (names[:5] or [("No presets", False)]) + [None, "Save as a preset…", "Delete a preset ▸",
                                                          None, "Use the initial settings…"]
        api.say("Click Presets")
        yield from api.click(b)
        m = yield from mock_menu(api, b, items)
        api.spot_on(m)
        api.say("“Save as a preset…”")
        yield from point_at_menu_row(api, m, items.index("Save as a preset…"))
        api.close(m)
        f = api.prompt("Save as a preset", "Name of the preset (all settings, not your files)", near=b, verb="Save")
        api.spot_on(f)
        api.say("…with a name")
        f.edit.setText("")
        yield from api.type(f.edit, "Equalizer APO", keep=True, hold=300)
        yield from api.click(f.ok)
        api.close(f)
        api.t.typed = []
        yield from api.note("The preset keeps all settings, not your files. (Demo: the app did not save it.)", b, 1500)
        api.say("Then, click it in Presets to load all its settings")
        yield from api.click(b)
        m = yield from mock_menu(api, b, ["Equalizer APO"] + [x for x in items if x != ("No presets", False)])
        yield from point_at_menu_row(api, m, 0)
        api.close(m)
        yield from api.note("The app loads all its settings again.", b, 1300)

    def history_demo(api):
        from PySide6.QtCore import QSize
        from ui.history_window import HistoryWindow
        w = HistoryWindow(page)
        api.window(w, near=page.hist_btn, size=QSize(int(min(700, api.t.width() * 0.6)),
                                                             int(min(520, api.t.height() * 0.6))))
        api.spot_on(w.frame)
        yield from api.at(w.scroll, 0.4, 0.25, 1500, say="Your previous EQs, by date. Show opens one with its files. "
                                                         "Its ⋯ has Copy, Keep to compare and Remove from the history")
        yield from api.at(w.q, 0.2, 0.5, 900, say="Search by IEM, target or method")

    steps = [
        {"chapter": "The parts of AutoEQ Studio", "title": "How to make an EQ",
         "target": lambda: [page.target_box, page.measurement_box],
         "text": "From top to bottom: the target and your IEM or headphone, the graph, the EQ, and the result to save. "
                 "Each step has a short demo. The demo does not change your work. The list of steps (at the top of "
                 "this box) has Play all steps and the speed of the demos.",
         "demo": [{"spot": lambda: page.target_combo},
                  {"at": lambda: page.target_combo, "say": "Select the target: the sound that you want"},
                  {"spot": lambda: page.measurement_combo},
                  {"at": lambda: page.measurement_combo, "say": "Select the measurement of your IEM or headphone"},
                  {"spot": lambda: page.sa},
                  {"at": lambda: page.sa, "say": "The settings that the app tries. The app adjusts them for you"},
                  {"spot": lambda: page.run_btn}, {"click": lambda: page.run_btn, "say": "Calculate"},
                  {"spot": lambda: page.plot},
                  {"at": lambda: page.plot, "y": 0.4, "say": "Examine the result on the graph. Then save it"}]},
        {"chapter": "1 · Select", "title": "Select a target", "target": lambda: page.target_box,
         "text": "The target is the sound that you want (for example, Harman, or a diffuse-field curve). Find… searches "
                 "the app, this PC and the online databases for a part of a name. The list adjacent to it has the targets "
                 "of the app. Add… adds a file. Some databases do not let the app download their targets. For their "
                 "targets, Use opens the website, and the tracer makes the target from a picture of the graph.",
         "demo": [{"click": lambda: button(page.target_box, "Find…"), "say": "Click Find… on the Target row",
                   "then": find_target_demo}]},
        {"chapter": "1 · Select", "title": "Adjust the target (optional)", "target": lambda: st.adjust_btn,
         "text": "Adjust… (on the Target row) opens a window. It gives the target a tilt (Half-tilt: only above a "
                 "frequency). It also increases or decreases the bass, ear gain, treble and air. Each row has a value (− "
                 "and +), a frequency (Hz) and a width (Q), and the graph of the window shows the target. If the target "
                 "is satisfactory, keep the values at 0. Save as a target… keeps the adjusted target.",
         "demo": lambda: adjust_demo(page)},
        {"chapter": "1 · Select", "title": "Select your IEM or headphone", "target": lambda: page.measurement_box,
         "text": "Find… searches by the name of the manufacturer or of the model. When you click Use, the app "
                 "downloads an online measurement and uses the average of its files (left, right, seatings). Add… adds "
                 "your files from this PC (L and R, or more than one seating). Some databases do not let the app "
                 "download their files. For their entries, Use opens the website, and the tracer makes the "
                 "measurement from a picture of the graph.",
         "demo": [{"click": lambda: button(page.measurement_box, "Find…"),
                   "say": "Click Find… on the Measurement row (or press /)", "then": find_meas_demo}]},
        {"chapter": "1 · Select", "title": "Many results?", "target": lambda: page.measurement_box,
         "text": "The rig tag of each result shows the rig of the measurement. A ⇄ after it: a rig change by its "
                 "database. The lists above the results show only one rig, type or source (“Same rig as your target” "
                 "first). Their items are from A to Z, with a search box that finds a source from a part of its name.",
         "demo": [{"click": lambda: button(page.measurement_box, "Find…"), "say": "Search again",
                   "then": many_results_demo}]},
        {"chapter": "1 · Select", "title": "More than one measurement of the same model?",
         "target": lambda: button(page, "Other measurements of this model…"),
         "text": "This window sorts all measurements of your model for your target: first the rig, then how much they "
                 "agree, the bass seal and the seatings. It can also use the average of some measurements on one rig.",
         "demo": [{"click": lambda: button(page, "Other measurements of this model…"),
                   "say": "Click “Other measurements of this model…”", "then": compare_window_demo}]},
        {"chapter": "1 · Select", "title": "Measured on a different rig?",
         "target": lambda: page.graph_note if getattr(page, "rig_note", "") else page.measurement_note,
         "text": lambda: ("The line below the graph tells you: " + page.rig_note.rstrip(".") + ". The app then "
                          "changes the target for the rig of your measurement (Settings › Target › Rig change). The "
                          "band around the target shows how large the error can be after this change."
                          if getattr(page, "rig_note", "") else
                          "The line below Measurement shows the rig of the measurement of your IEM (B&K 5128, 711 "
                          "coupler…). A target is for one rig. If the rigs are different, the line below the graph "
                          "tells you. The app then changes the target for the rig of your measurement (Settings › "
                          "Target › Rig change)."),
         "demo": lambda: [{"at": lambda: page.graph_note, "x": 0.3, "hold": 1300, "say": "The line: the rig of each curve"},
                          {"run": rig_demo, "say": "Without and with the rig change"}]
         if getattr(page, "rig_note", "") and ((page.curves or {}).get("rig") or {}).get("applied") else
         [{"at": lambda: page.measurement_note, "x": 0.3, "hold": 1500, "say": "The rig of the measurement"}]},
        {"chapter": "2 · Settings", "title": "Automatically or manually", "target": lambda: list(page.way_btns.values()),
         "text": "Make the EQ has two tabs, below Your EQ app. Automatically: AutoEQ adjusts the filters to the target "
                 "for your EQ app (select the method, then click Calculate). Manually: you set the filters, from an "
                 "empty EQ or from an EQ that you have. The card shows the steps of that tab, and opens on the tab that "
                 "you selected last. Settings and More settings are for the two tabs.",
         "demo": [{"run": way_demo, "say": "Each tab shows its steps"}]},
        {"chapter": "2 · Settings", "title": "Your EQ app", "target": lambda: [page.app_combo, page.app_note],
         "text": "Select the app or device that will use the EQ (Windows, Mac, Linux, Android, iPhone, a DAC or "
                 "squig.link). It is above the tabs, because it is for the two tabs. The EQ stays in its limits (bands, "
                 "gain, Q, the sliders of a graphic EQ). Save filters saves the file that the app or device imports. The "
                 "ⓘ after its label shows the limits.",
         "demo": [{"click": lambda: page.app_combo, "say": "Click Your EQ app", "then": app_demo}]},
        {"chapter": "2 · Settings", "title": "Select an EQ method", "target": lambda: [page.mode_combo, page.mode_hint],
         "before": auto_on, "after": auto_off,
         "text": "Select a method for where you use the EQ. Best fit (the initial method) for EQ apps and devices: the "
                 "nearest EQ to the target. The website methods give the values that you type in the AutoEQ of "
                 "squiglink or listener800.",
         "demo": [{"click": lambda: page.mode_combo, "say": "Click the method", "then": mode_demo}]},
        {"chapter": "2 · Settings", "title": "Automatic settings",
         "target": lambda: [st.fold.btn, st.fold.summary, st.auto_on, st.why_fold.btn], "before": about_open,
         "after": lambda: (about_close(), settings_close()),
         "text": "Settings (a row in Make the EQ, above Calculate) has the settings that you can change. They are the "
                 "automatic settings (adjusted for your files), the filters, and Error and selection. About these "
                 "settings (a row that opens) tells you how the app adjusts each value. The app sets the other "
                 "settings for you (More settings, below it).",
         "demo": [{"at": lambda: st.fold.btn, "x": 0.1, "say": "Settings: the settings that you can change"},
                  {"at": lambda: st.auto_on, "x": 0.1,
                   "say": "They change with the measurement and the target that you selected"},
                  {"at": lambda: st.why, "x": 0.3, "y": 0.3,
                   "say": "About these settings tells you how the app adjusts each value"}]},
        {"chapter": "2 · Settings", "title": "The settings that the app tries", "target": lambda: [page.sa],
         "before": auto_on, "after": auto_off,
         "text": "Best fit adds filters one at a time, with each maximum gain and maximum Q for your curves. It stops "
                 "when the EQ has the same sound as the target. This line shows the number of EQs that the app tries, "
                 "and how long the app calculates on this PC: seconds for most IEMs. Its tooltip and Help give the "
                 "settings that the app tries.",
         "demo": [{"at": lambda: page.estimate, "x": 0.2, "say": "The number of EQs, and how long the app calculates"},
                  {"at": lambda: page.estimate, "x": 0.6, "say": "Its tooltip gives the settings that the app tries"}]},
        {"chapter": "2 · Settings", "title": "Your values", "target": lambda: [st.form],
         "before": settings_open, "after": settings_close,
         "text": "If you change a setting, it shows “your value”, and new files do not change it. Click “your value ↺” "
                 "to make it automatic again, or disable Automatic settings.",
         "demo": [{"run": your_value_demo, "say": "Type your value. Press Enter"},
                  {"at": lambda: st.auto_on, "x": 0.1, "say": "Or disable Automatic settings"}]},
        {"chapter": "2 · Settings", "title": "Start from your filters",
         "target": lambda: st.adv_form.fields["best_fit.start_filters"] if st.adv_form.fields["best_fit.start_filters"].isVisible() else None,
         "alt": lambda: page.mode_combo, "before": auto_settings_open, "after": auto_settings_close,
         "text": "More settings › Best fit: Best fit can start from an EQ that you have. Type its filters, edit them as "
                 "a table, or load its file. It adds filters to your filters, and it can also adjust them.",
         "alt_text": "If the method is Best fit (and your EQ app has parametric filters), More settings › Best fit › "
                     "“Start from your filters” uses an EQ that you have. Best fit adds filters to it.",
         "demo": [{"type": lambda: st.adv_form.fields["best_fit.start_filters"].box,
                   "text": "Filter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1", "keep": True, "hold": 300,
                   "say": "Type them as Equalizer APO lines…"},
                  {"at": lambda: button(st.adv, "Edit as a table…"), "say": "…or edit them as a table or sliders"},
                  {"at": lambda: button(st.adv, "Load an EQ file…"), "say": "Or load an EQ file. If you do not select "
                   "“Keep them as they are”, Best fit also adjusts them"}],
         "alt_demo": [{"at": lambda: page.mode_combo, "say": "Select Best fit as the method to start from your filters"}]},
        {"chapter": "3 · Calculate and examine", "title": "Calculate",
         "target": lambda: [page.run_btn, page.queue_btn, page.estimate],
         "before": auto_on, "after": auto_off,
         "text": "Calculate finds the filters. If the app calculates for a long time, it shows how much is completed, "
                 "and you can cancel it. Queue… makes EQs for more than one IEM or target, one after the other (the app "
                 "saves each EQ and keeps it in History).",
         "demo": [{"click": lambda: page.run_btn, "say": "Click Calculate", "then": run_demo},
                  {"at": lambda: page.queue_btn, "say": "Queue…: more than one IEM or target, one after the other"}]},
        {"chapter": "3 · Calculate and examine", "title": "Or make it manually",
         "target": lambda: [page.way_btns["hand"], page.hand_source, page.hand_start],
         "before": hand_on, "after": hand_off,
         "text": "With Manually (the tab adjacent to Automatically), you make an EQ, and it shows as a result. Start from "
                 "has an empty EQ, a copy of the selected EQ, an EQ file, pasted filters and profiles. The EQ file can "
                 "be from Equalizer APO, AutoEq, Room EQ Wizard or Peace. After Start, you add and change its filters, "
                 "and Save filters, Use on device and Listen operate as for a calculated EQ. A measurement and a "
                 "target are optional. Close shows the previous EQ again.",
         "demo": [{"click": lambda: page.way_btns["hand"], "say": "Click Manually", "then": manual_demo}]},
        {"chapter": "3 · Calculate and examine", "title": "Examine it on the graph", "target": lambda: page.plot,
         "ready": has_curves,
         "text": "Orange: your IEM. Dashed: the target. Blue: with the EQ. Below it, pink: the EQ (above 0: more gain, "
                 "below 0: less gain). Move the mouse on the graph to see the value of each curve. The app does not "
                 "calculate the error at the two ends of the graph (in a different color).",
         "demo": lambda: [{"run": graph_demo, "say": "With the EQ, your IEM changes to the blue curve, near the target"},
                          {"at": lambda: page.plot, "x": 0.3, "y": 0.35, "then": plot_value(page, 0.3, 0.35),
                           "say": "Move the mouse on the graph: its values show above it"},
                          {"at": lambda: page.plot, "x": 0.72, "y": 0.4, "then": plot_value(page, 0.72, 0.4),
                           "say": "The dB of each curve at that frequency"}] if page.curves else []},
        {"chapter": "3 · Calculate and examine", "title": "Graph views", "ready": has_curves,
         "target": lambda: [page.view_combo, page.yrange_combo] + ([page.channels_chk] if page.channels_chk.isVisible() else []),
         "avoid": lambda: [page.plot],
         "text": "View › “Difference from target” shows only the difference that the EQ must correct (0 dB = on the "
                 "target). Y range zooms in. Channels also shows the curve of each file. The line below them gives the "
                 "name of each curve, in its color.",
         "demo": lambda: [{"click": lambda: page.view_combo, "say": "Difference from target: the difference to correct",
                           "then": lambda api: views_demo(api, view="rel")},
                          {"click": lambda: page.yrange_combo, "say": "Y range: zoom in (for example, 30 dB)",
                           "then": lambda api: views_demo(api, y="30")}]
         + ([{"click": lambda: page.channels_chk, "x": 0.1, "say": "Channels: the curve of each file and their average",
              "then": lambda: page.demo_graph(channels=True)}] if page.channels_chk.isVisible() else [])},
        {"chapter": "3 · Calculate and examine", "title": "Your result",
         "target": lambda: [page.res_title, page.res_sub] + list(page.chips.values()) + [page.count_combo, page.cmp_btn]
         + ([page.pick_lab] if page.pick_lab.isVisible() else []),
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "After you calculate, the result shows below the settings: the error, the pre-amp for your EQ "
                         "app, and the filters. The line below the numbers tells if the sound is the same as the "
                         f"target. The limit is {page.S['scoring'].get('ear_db', 0.25):g} dB at all frequencies, as "
                         "the ear hears it. If the limits of your EQ app prevent this, the line shows how large the "
                         "difference is, and where. “Number of filters” shows the best result for each number of "
                         "filters, and Compare… shows two EQs at the same time." + example(),
         "demo": lambda: [{"at": lambda: page.chips["error"], "say": "The difference from the target, in the error range"},
                          *([{"at": lambda: page.pick_lab, "x": 0.2,
                              "say": "If the sound is the same as the target, as the ear hears it"}]
                            if page.pick_lab.isVisible() else []),
                          {"at": lambda: page.chips["preamp"], "say": "Set this pre-amp in your EQ app"},
                          {"run": result_demo, "say": "The best result for each number of filters"},
                          {"at": lambda: page.cmp_btn, "say": "Compare…: two EQs at the same time"}]},
        {"chapter": "3 · Calculate and examine", "title": "Edit the filters",
         "target": lambda: [page.editor, page.live_check, page.retry_btn],
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "Change a filter in the table or with the sliders: the numbers and the graph change with it. "
                         "If you cannot see the graph, a copy of it shows on the page while you edit (“Show the graph "
                         "while you edit” disables it). Undo all (enabled after you edit) shows the calculated filters again. Calculate from "
                         "these filters starts Best fit again from your filters." + example(),
         "demo": [{"run": edit_demo, "say": "Change a value: the numbers and the graph change with it"},
                  {"at": lambda: page.retry_btn, "say": "Calculate from these filters: Best fit again, from your filters"}]},
        {"chapter": "3 · Calculate and examine", "title": "Edit on the EQ graph", "target": lambda: page.eqplot,
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "Each filter has a handle on the EQ graph, below the graph, with the number from the table. "
                         "Drag it left or right for its frequency, and up or down for its gain. The mouse wheel on a "
                         "handle changes its Q, and a right-click shows its type and Remove (On in the table disables "
                         "a filter). Double-click where there is no handle to add a filter. If you use the EQ "
                         "on a device for 5 minutes, the device also plays each change."
                         + example(),
         "demo": lambda: drag_actions()},
        {"chapter": "3 · Calculate and examine", "title": "Save it, or use it on a device",
         "target": lambda: [page.name_edit, page.formats_line, button(page.result_box, "Save filters"), page.use_btn],
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "Two rows of buttons, below File name. The files: Save filters saves the file for your EQ app "
                         "with the File name. Copy copies the filters to the clipboard, and Open the Saved EQs folder "
                         "opens that folder. Then: "
                         "Use on device makes the EQ a new profile of a device and enables it. It can also update a "
                         "profile that you have (the profile keeps its devices), or use the EQ on a device for 5 "
                         "minutes. Keep to compare adds it to your EQs to compare, and Report makes an HTML page."
                         + example(),
         "demo": [{"run": save_demo, "say": "Give it a name, save it, or use it on a device"}]},
        {"chapter": "3 · Calculate and examine", "title": "Listen", "target": lambda: page.listen,
         "ready": lambda: page.listen.isVisible(),
         "text": "Play music, noise, a sweep, a tone or your audio file through the EQ on your IEM or headphone. Change "
                 "between versions. Start with a low volume.",
         "demo": [{"run": listen_demo, "say": "Select a sound, play it, and change the version"}]},
        {"chapter": "3 · Calculate and examine", "title": "Your EQs to compare", "target": lambda: page.listen.pins_box,
         "ready": lambda: page.listen.isVisible(),
         "text": "Keep the EQs that you want to compare: from the result card (Keep to compare), History, an EQ file "
                 "or pasted filters. Each IEM or headphone has its list, and the app keeps it when you close the app. "
                 "If you select Graph, the graph also shows the EQ.",
         "demo": [{"at": lambda: button(page.listen, "The selected EQ"), "say": "The EQ on the result card"},
                  {"at": lambda: button(page.listen, "From an EQ file…"),
                   "say": "An EQ file (Equalizer APO, Room EQ Wizard, Peace…)"},
                  {"at": lambda: button(page.listen, "Paste filters…"), "say": "Or filters that you paste"}]},
        {"chapter": "3 · Calculate and examine", "title": "Compare by ear", "target": lambda: page.listen,
         "ready": lambda: page.listen.isVisible(),
         "text": "Same level: you compare the sound, not the volume. Hide the names hides the names of the versions. "
                 "You can also put a different version in each ear. An ABX test shows if you can hear a difference "
                 "between two EQs. In each trial, X is A or B, randomly, and you select one. At the end, it shows your "
                 "result, and how frequently random selections get the same result.",
         "demo": [{"run": compare_ear_demo, "say": "Hide the names, or a version in each ear"},
                  {"run": abx_demo, "say": "An ABX test: can you hear a difference?"}]},
        {"chapter": "More", "title": "Presets", "target": lambda: win.presets_btn, "top bar": True,
         "text": "A preset keeps all settings with a name, for example a preset for the website and a preset for "
                 "Equalizer APO. "
                 "You can load it again when necessary. It keeps settings, not your files.",
         "demo": [{"run": preset_demo, "say": "Save the settings as a preset, and load it again"}]},
        {"chapter": "More", "title": "History", "target": lambda: page.hist_btn,
         "text": "Your previous EQs. The app keeps them after you close it: the EQs that you save or copy (or all "
                 "results: More settings › History). Show opens an EQ again with its files. Its ⋯ menu has Copy, Keep "
                 "to compare (it adds the EQ to your EQs to compare) and Remove from the history.",
         "demo": lambda: [{"click": lambda: page.hist_btn, "say": "History: your previous EQs", "then": history_demo}]
         + ([{"at": lambda: page.eqd_show, "say": "Below Measurement: a message if History has an EQ for it. "
                                                  "Show in History… opens these EQs"}]
            if page.eqd_show.isVisible() else [])},
        {"chapter": "More", "title": "Do you have only a picture of a graph?", "target": lambda: page.trace_btn,
         "text": "Trace a graph image… changes the picture of a graph into a measurement or a target. It also has a "
                 "Guide. You can also paste or drag a picture on the window.",
         "demo": [{"at": lambda: page.trace_btn, "say": "A picture of a graph becomes a curve"}]},
        {"chapter": "More", "title": "Your devices", "target": lambda: win.nav["devices"], "top bar": True,
         "text": "Devices gives each playback device its EQ through Equalizer APO, and Profiles shows the EQs. The EQ "
                 "changes automatically when the device becomes active, and a line shows if Equalizer APO uses the EQ. "
                 "Use on device puts a result there with one click. Two hotkeys operate in all programs (Settings). One "
                 "changes the EQ of the active device to the next EQ. The other disables its EQ and enables it again, "
                 "at the same level, to compare.",
         "demo": [{"at": lambda: win.nav["devices"], "say": "The EQ of each device"},
                  {"at": lambda: win.nav["profiles"], "say": "Your EQs, as profiles"},
                  {"at": lambda: win.nav["settings"], "say": "The hotkeys: the next EQ, and EQ off and on to compare"}]},
        {"chapter": "More", "title": "Settings", "target": lambda: st.adv.btn,
         "text": "More settings (below Settings, in Make the EQ) has the settings that the app sets for you, with a tab "
                 "for each part. The Best fit tab has its layout, limits, penalties and your filters. The Website best "
                 "settings tab has its lists (with that method only). The other tabs are the website settings, Saved "
                 "files, History and This PC. A list of more than 15 items, for example Layout, opens with a "
                 "search box. The Settings screen (top bar) has the location of your files, backups, Online / Offline "
                 "and Start with Windows.",
         "demo": lambda: [{"at": lambda: st.adv.btn, "x": 0.1, "say": "More settings: the settings that the app sets for you"}]
         + ([{"at": lambda: win.nav["settings"], "say": "The settings of the app"}] if hasattr(win, "nav") else [])},
        {"chapter": "More", "title": "Help, and the end of the Guide", "target": lambda: win.help_btn, "top bar": True,
         "text": "Help gives information about the words of the app (Q, shelf, rig, pre-amp…) and the solutions to "
                 "frequent problems. Move the "
                 "mouse to a setting to see its function. F1 opens its entry in Help. You can open the Guide again to "
                 "see a step.",
         "demo": [{"at": lambda: win.help_btn, "say": "Help: information about the app, and the frequent problems"},
                  {"at": lambda: page.sa, "say": "Move the mouse to a setting to see its function. F1 opens its entry "
                                                 "in Help"}],
         "buttons": [("Open Help", lambda: win.open_help())] if hasattr(win, "open_help") else []},
    ]
    # (the steps about the app window's top bar: only when the screen is in it, not on its own as in the checks)
    return [s for s in steps if not s.get("top bar") or hasattr(win, "nav")]


def start_eq(page):
    return tour.Tour(page, eq_steps(page))
