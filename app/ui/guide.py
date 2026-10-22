"""The Guides (AutoEQ Local's guide.js STEPS and the tracer's TOUR, told for AutoEQ Studio's window; ui/tour.py shows
them): eq_steps(page) for Make an EQ, trace_steps(tracer) for Trace image.

Make an EQ's Guide walks through a whole EQ job, as AutoEQ Local's did: choose, check the automatic settings, run,
review, save, listen. Its demos work the real window: Find… opens (inside the tour) and a search is typed into it, a
row is picked and shown on the graph; a drop-down's list opens and a choice shows in its box; the target changes on
the graph as the adjustments are typed; Run shows its progress and the EQ'd curve grows on the graph (kept in sight
while the page scrolls under it); before a run there's an example result (filters worked out from your files, as
AutoEQ Local's demo did). Everything is put back when a demo ends, and nothing is chosen, run, saved or downloaded.
When a control is renamed, moved or added, its step changes with it: eq_checks.py checks that every step's control
is there and can be seen (tour.problems()), and plays every demo.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton

from ui import tasks, theme, tour


def _button(root, text):
    return next((b for b in root.findChildren(QPushButton) if b.text() == text and b.isVisible()), None) or \
        next((b for b in root.findChildren(QPushButton) if b.text() == text), None)


def _card(w):
    """The card (group box) a control sits in."""
    p = w
    while p is not None and not isinstance(p, QGroupBox):
        p = p.parentWidget()
    return p or w


def _fold(btn, before):
    """A step's before/after that open a fold (by its button: a Fold's btn, Adjust) for it and close it again if it
    was closed."""
    was = {}

    def b():
        was["open"] = btn.isChecked()
        btn.setChecked(True)
        if before:
            before()

    def a():
        btn.setChecked(was.get("open", False))
    return b, a


def _slide(slider, to, say, back=None, label=None):
    """A demo action: the pointer drags a slider's handle to a value (and back), the slider following; put back."""
    from PySide6.QtCore import QSignalBlocker
    lo, hi = slider.minimum(), slider.maximum()
    span = (hi - lo) or 1
    was = {}
    frac = lambda v: 0.04 + 0.92 * (v - lo) / span

    def at(p):
        a = was["v"] if back is None else back
        return round(a + (to - a) * p)

    def set_(p):
        was.setdefault("v", slider.value())
        with QSignalBlocker(slider):
            slider.setValue(at(p))

    def undo():
        if "v" in was:
            with QSignalBlocker(slider):
                slider.setValue(was.pop("v"))
    start = slider.value() if back is None else back
    a = {"drag": lambda: slider, "from": (frac(start), 0.5), "to": (frac(to), 0.5), "set": set_, "undo": undo,
         "say": say}
    if label:
        a["label"] = lambda p: label(at(p))
    return a


def _plot_value(page, fx, fy):
    """A demo's "then": the graph's values at a point of it, as when the pointer is there (put back after)."""
    from PySide6.QtCore import QPoint

    def then():
        pl = page.plot
        page._hover(pl.mapToScene(QPoint(int(pl.width() * fx), int(pl.height() * fy))))
        return lambda: page.hover_lab.setText("")
    return then


def _bg(fn):
    """A demo waits (up to a few seconds) for work done off the window's thread: r = yield from _bg(fn)."""
    box = {}
    tasks.background(fn, lambda r, e: box.update(r=r, e=e))
    for _ in range(200):
        if box:
            break
        yield 30
    return box.get("r") if not box.get("e") else None


# ---------------------------------------------------------------- an example EQ before a run (AutoEQ Local's)
def demo_filters(page):
    """Example filters for your measurement (AutoEQ Local's demoFilters): up to 8 peaking filters, each placed where
    it's furthest from the target, levelled at 300 Hz – 3 kHz, so the demo's result is like a run's."""
    import numpy as np
    from eq import engines
    c = page.curves
    if not c:
        return []
    f, m, t = (np.asarray(c[k], dtype=float) for k in ("f", "meas", "target"))
    top = page.S["scoring"]["band_hz"][1]
    mid = (f >= 300) & (f <= 3000)
    off = float(np.mean(t[mid] - m[mid])) if mid.any() else 0.0
    want = np.convolve(np.pad(t - m - off, 3, mode="edge"), np.ones(7) / 7, mode="valid")
    sr = page.S["site"]["sample_rate"]
    out = []
    for _ in range(8):
        free = (f >= 20) & (f <= top)
        for o in out:
            free &= np.abs(np.log2(f / o["freq"])) > 0.6
        if not free.any():
            break
        i = int(np.argmax(np.where(free, np.abs(want), -1)))
        v = float(want[i])
        if abs(v) < 0.7:
            break
        half = lambda k, v=v, w=want: np.sign(w[k]) == np.sign(v) and abs(w[k]) > abs(v) / 2
        a = b = i
        while a > 0 and half(a - 1):
            a -= 1
        while b < len(f) - 1 and half(b + 1):
            b += 1
        bw = 2 ** max(0.2, float(np.log2(f[b] / f[a])))
        flt = {"type": "PK", "freq": int(round(f[i])), "gain": round(max(-12.0, min(6.0, v)), 1),
               "q": round(min(5.0, max(0.5, np.sqrt(bw) / (bw - 1))), 2)}
        want = want - engines.eq_gain(f, [flt], sr)
        out.append(flt)
    return sorted(out, key=lambda x: x["freq"])


def eq_now(page):
    """The measurement with the EQ: the result shown (as edited), or the example filters before a run."""
    import numpy as np
    from eq import engines
    c = page.curves
    filters = page.active() if page.current()[1] else demo_filters(page)
    f = np.asarray(c["f"])
    return np.asarray(c["meas"], dtype=float) + engines.eq_gain(f, filters, page.S["site"]["sample_rate"])


def stage_result(page):
    """Before a run: an example result on the result card (the example filters; the Guide's, nothing was run), so
    the result steps show the real card. The function it returns puts the card back as it was."""
    if page.current()[1] or not page.curves:
        return None
    fl = demo_filters(page)
    if not fl:
        return None
    keep = (page.run_result, page.sel, page.EDIT, page.ORIG, page.name_edit.text(), page.name_edit.property("auto"))
    import numpy as np
    from eq import engines
    c = page.curves
    f = np.asarray(c["f"])
    band = page.S["scoring"]["band_hz"]
    inside = (f >= band[0]) & (f <= band[1])
    full = np.asarray(c["meas"]) + engines.eq_gain(f, fl, page.S["site"]["sample_rate"]) - np.asarray(c["target"])
    d = full[inside]
    ear, ear_at = engines.ear_error(f, full, band) if d.size else (None, None)  # (how it sounds: the pick's line)
    limit = page.S["scoring"].get("ear_db", 0.25)
    r = {"id": "guide", "filters": fl, "n_filters": len(fl), "rms": float(np.sqrt(np.mean(d * d))) if d.size else 0.0,
         "layout": page.S["best_fit"].get("layout"), "q_max": 5, "gain_max": 6, "ear": ear, "ear_at": ear_at}
    page.run_result = {"mode": "best_fit", "results": [r], "pick": "guide", "best": "guide", "n": 1,
                       "device": page.curves.get("name"), "target_name": page.curves.get("target_name"),
                       # (the line under the numbers only when it's true of the example: "out of reach" would be
                       # about the example's rough filters, not your IEM)
                       "pick_case": "target" if ear is not None and ear <= limit else None,
                       "ear_db": limit}
    page.show_result("guide")
    page.res_sub.setText("An example for the Guide, from your files (nothing was run): a run's result looks like this")

    def undo():
        page.run_result, page.sel, page.EDIT, page.ORIG = keep[:4]
        page.name_edit.setText(keep[4])
        page.name_edit.setProperty("auto", keep[5])
        page.result_box.hide()
        page.render_runs()
        if hasattr(page, "listen"):
            page.listen.refresh()
        page.draw()
    return undo


# ---------------------------------------------------------------- the app's own lists, shown by the demos
def _mock_combo(api, combo, to_index, say_rows=None, rows=9):
    """A drop-down's list as it opens under its box (the same rows, a part of a long one), the pointer down it to a
    row and a click: the box then shows that row (signals blocked: nothing is chosen). Yields."""
    n = combo.count()
    if n == 0 or to_index < 0:
        yield 300
        return
    lo = max(0, min(to_index - rows // 2, n - rows))
    hi = min(n, lo + rows)
    items = [combo.itemText(k) for k in range(lo, hi)]
    m = api.mock(combo, items, combo.currentIndex() - lo, width=max(combo.width(), 260))
    yield 250
    start = combo.currentIndex() - lo if lo <= combo.currentIndex() < hi else 0
    path = range(start, to_index - lo + 1) if to_index - lo >= start else range(start, to_index - lo - 1, -1)
    for k in path:
        m.hover(k)
        yield from api.move_to(m.row(k), 0.3, 0.5, ms=220)
        yield 90
    yield from api.ripple()
    yield 150
    api.close(m)
    api.stage_index(combo, to_index)
    yield 300


def _mock_menu(api, near, items):
    m = api.mock(near, items, width=max(near.width(), 280))
    yield 300
    return m


def _pick(api, m, i, hold=350):
    m.hover(i)
    yield from api.move_to(m.row(i), 0.3, 0.5, ms=420)
    yield hold
    yield from api.ripple()
    yield 200


def _stage_choice(api, combo, text):
    """The box shows a choice (one it doesn't list yet is added for the demo); nothing is chosen."""
    from PySide6.QtCore import QSignalBlocker
    i = combo.findText(text, Qt.MatchContains)
    if i < 0:
        with QSignalBlocker(combo):
            combo.insertItem(0, text)

        def out():
            with QSignalBlocker(combo):
                combo.removeItem(0)
        api.undo(out)
        i = 0
    api.stage_index(combo, i)


# ---------------------------------------------------------------- Find…, opened in the tour
def _open_picker(page, api, kind):
    """Find… opened for real (inside the tour, only looked at), with your filters off for the search (yours come
    back after: the window is made for the demo and never saves them)."""
    from PySide6.QtCore import QSize
    from ui.picker import ANY, Picker
    pk = Picker(page, kind)
    pk.filters = {k: dict(ANY) for k in ("target", "measurement")}
    W, H = api.t.width(), api.t.height()
    api.window(pk, near=getattr(page, f"{kind}_box"), size=QSize(int(min(820, W * 0.74)), int(min(560, H * 0.6))))
    pk.render()
    api.spot_on(pk.frame)
    return pk


def _type_search(api, pk, text):
    yield from api.move_to(pk.q, 0.1, 0.5)
    yield from api.ripple()
    for n in range(1, len(text) + 1):
        pk.q.setText(text[:n])
        yield 110
    pk._later.stop()
    pk.render()
    yield 600


def _rows(pk):
    out = []
    for k in range(pk.list.count()):
        it = pk.list.item(k)
        r = it.data(Qt.UserRole)
        if r and not r.get("current") and not r.get("link") and not r.get("other"):
            out.append((it, r))
    return out


def _choose_row(page, api, pk, prefer, combo):
    """A row of the real list hovered and its Use clicked; the window closes and the box shows it; its curve (a file
    in the app or on this PC: read there, nothing downloaded) is returned."""
    rows = _rows(pk)
    local = lambda r: r["src"] in ("app", "pc")
    pick = next(((it, r) for it, r in rows if prefer(r) and local(r)), None) or \
        next(((it, r) for it, r in rows if prefer(r)), None) or (rows[0] if rows else None)
    if pick is None:
        yield 400
        return None
    it, r = pick
    pk.list.scrollToItem(it)
    pk.list.setCurrentItem(it)
    w = pk.list.itemWidget(it)
    name = next((x for x in w.findChildren(QLabel) if x.text().endswith(r["name"])), w)
    yield from api.move_to(name, 0.2, 0.5)
    yield 450
    use = next((b for b in w.findChildren(QPushButton) if b.text() == "Use"), w)
    yield from api.move_to(use)
    api.hot(use)
    yield from api.ripple()
    yield 250
    api.hot(None)
    body = dict(pk.body(r), settings=page.S) if local(r) else None
    api.close(pk)
    _stage_choice(api, combo, r["name"])
    api.spot_to(combo)
    api.hot(combo)
    yield 700
    api.hot(None)
    if body is None:
        return None
    res = yield from _bg(lambda: page.svc.call("/api/preview", body))
    vals = (res or {}).get("vals")
    return (r["name"], vals) if vals and page.curves and len(vals) == len(page.curves["f"]) else None


def _show_on_graph(page, api, key, vals, label, keep):
    """A curve chosen in the demo shown on the graph: from the one there now to the new one (kept in sight above
    the card the demo is about)."""
    import numpy as np
    if vals is None or not page.curves:
        yield 500
        return
    yield from api.pin_graph(page, keep)
    col = theme.graph_colours()
    now = np.asarray(page.curves["target" if key == "target" else "meas"], dtype=float)
    new = np.asarray(vals, dtype=float)
    if key == "meas":  # (levelled as the graph levels it: the same loudness at 300 Hz – 3 kHz)
        f = np.asarray(page.curves["f"])
        mid = (f >= 300) & (f <= 3000)
        new = new - float(np.mean(new[mid] - now[mid])) if mid.any() else new
    item = api.curve(page, now, col["target"] if key == "target" else col["meas"], 2.6,
                     Qt.DashLine if key == "target" else Qt.SolidLine, name=f"{label} (demo)")
    yield from api.morph(page, item, now, new, 1300)
    yield from api.note(f"{label}: on the graph" + (" (dashed)" if key == "target" else ""), api.t.pin or page.plot, 1500,
                        below="inside")


# ---------------------------------------------------------------- the target adjusted on the graph
ADJ = [("tilt", "-0.5", lambda a: "Tilt −0.5 dB/oct: warmer overall (bass up, treble down, around 1 kHz)"),
       ("bass_gain", "4", lambda a: f"Bass shelf +4 dB: more bass below about {_hz(a['bass_freq'])}"),
       ("treble_gain", "-1.5", lambda a: f"Treble −1.5 dB: less brightness above about {_hz(a['treble_freq'])}")]


def _hz(v):
    return f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"


def _adj_shape(page, key, v):
    """An adjustment's change to the target at each frequency, in dB (the app's own maths: shelves and a tilt)."""
    import numpy as np
    from eq import engines
    f = np.asarray(page.curves["f"])
    a = page.S["target_adjust"]
    if key == "tilt":
        return v * np.log2(f / 1000)
    kind = {"bass_gain": ("LSQ", "bass"), "treble_gain": ("HSQ", "treble")}[key]
    return engines.eq_gain(f, [{"type": kind[0], "freq": a[kind[1] + "_freq"], "gain": v, "q": a[kind[1] + "_q"]}],
                           page.S["site"]["sample_rate"])


def _adjust_demo(page):
    st = page.settings
    if not page.curves:
        return [{"at": lambda: st.adjust_btn, "say": "Adjust, under the target, holds these controls"}]
    col = theme.graph_colours()
    hold = {}

    def start(api):
        import numpy as np
        yield from api.pin_graph(page, st.adjust_panel)
        hold["base"] = np.asarray(page.curves["target"], dtype=float)
        hold["item"] = api.curve(page, hold["base"], col["target"], 2.6, name="Target, adjusted (demo)")
        yield 300

    def morph(api, key, text):
        v = float(text)
        d = _adj_shape(page, key, v)
        b = hold.get("base")
        if b is None:
            yield 300
            return
        yield from api.morph(page, hold["item"], b, b + d, 900)
        yield 1300
        api.t.typed = [e for e in api.t.typed if e[0] is not st.adjust_form.fields["target_adjust." + key].box]
        yield from api.morph(page, hold["item"], b + d, b, 450)
    acts = [{"at": lambda: st.adjust_btn, "say": "Adjust (under Target) opens these; the graph shows the target as "
             "you change them", "then": start}]
    for key, text, say in ADJ:
        acts += [{"type": (lambda k=key: st.adjust_form.fields["target_adjust." + k].box), "text": text, "keep": True,
                  "hold": 250, "say": say(page.S["target_adjust"])},
                 {"run": (lambda api, k=key, t=text: morph(api, k, t))}]
    acts.append({"at": lambda: st.reset_adjust_btn, "say": "Reset adjustments sets them all back to 0"})
    return acts


# ---------------------------------------------------------------- Make an EQ's Guide
def eq_steps(page):
    """Make an EQ's Guide."""
    win = page.window()
    st = page.settings
    in_card = lambda w, text: (lambda: _button(_card(w), text))
    has_curves = lambda: bool(page.curves)
    settings_open, settings_close = _fold(st.fold.btn, None)
    adjust_open, adjust_close = _fold(st.adjust_btn, None)
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
        pk = _open_picker(page, api, "target")
        api.say("Type part of a name")
        active = page.inputs.get("active_target") or ""
        mine = [n for n in page.inputs.get("targets", []) if n != active]
        q = "harman" if any("harman" in n.lower() for n in mine) or not mine else \
            " ".join(w for w in mine[0].rsplit(".", 1)[0].replace("_", " ").split()[:2]).lower()
        yield from _type_search(api, pk, q)
        api.say("Click the one you want: it becomes the target on the graph")
        now = norm(active.rsplit(".", 1)[0])
        got = yield from _choose_row(page, api, pk, lambda r: "all" not in r["name"].lower().split()
                                     and norm(r["name"]) != now, page.target_combo)
        if got:
            yield from _show_on_graph(page, api, "target", got[1], got[0], page.target_box)

    def model():
        n = (page.curves or {}).get("name") or ""
        import re
        w = re.sub(r"\s*\([^)]*\)", " ", n).replace("_", " ").replace("-", " ").split()[:2]
        return " ".join(w) if len(" ".join(w)) >= 3 else "Truthear Gate"
    same_model = lambda r: norm(r["name"]).startswith(norm(model()))

    def choose_meas(api):
        pk = _open_picker(page, api, "measurement")
        api.say("Type the brand or model")
        yield from _type_search(api, pk, model().lower())
        api.say("Click the one you want: it's shown on the graph")
        got = yield from _choose_row(page, api, pk, same_model, page.measurement_combo)
        vals = got[1] if got else ((page.curves or {}).get("meas") if page.curves else None)
        yield from _show_on_graph(page, api, "meas", vals, got[0] if got else model(), page.measurement_box)

    def many_results(api):
        pk = _open_picker(page, api, "measurement")
        yield from _type_search(api, pk, model().lower())
        rows = _rows(pk)
        tag = None
        for it, r in rows:
            if (r.get("rig") or "").replace("?", "") in (page.meta.get("rigs") or {}):
                w = pk.list.itemWidget(it)
                tag = next((x for x in w.findChildren(QLabel) if x.property("role") == "chip"), None)
                if tag is not None:
                    pk.list.scrollToItem(it)
                    break
        if tag is not None:
            api.say("A result's rig tag: what it was measured on, and how that was worked out")
            yield from api.move_to(tag)
            api.hot(tag)
            yield from api.note(tag.toolTip(), tag, 2600)
            api.hot(None)
        conv = next((x for it, _r in rows for x in pk.list.itemWidget(it).findChildren(QLabel)
                     if x.property("role") == "chip" and "⇄" in x.text()), None)
        if conv is not None:
            api.say("⇄: its database has a conversion of its own")
            yield from api.move_to(conv)
            yield from api.note(conv.toolTip().split("\n")[-1], conv, 3000)
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
            m = api.mock(pk.f_site, [f"🔍  {word}"] + found, width=max(pk.f_site.width(), 300))
            m.hover(1)
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
        api.window(w, near=None, size=QSize(int(min(860, api.t.width() * 0.7)), int(min(640, api.t.height() * 0.7))))
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
        api.say("Compare looks for them; Use makes one your measurement, or average several from one rig")
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
        res = yield from _bg(lambda: page.svc.call("/api/curves", {"settings": s}))
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
        yield from _mock_combo(api, combo, i)
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
        yield from _mock_combo(api, combo, keys.index(to) if to in keys else 0)
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
               page.progress.maximum(), page.progress.value(), page.progress_text.text())

        def back():
            page.run_btn.setEnabled(was[0])
            page.cancel_btn.setVisible(was[1])
            page.progress.setVisible(was[2])
            page.progress.setMaximum(was[3])
            page.progress.setValue(was[4])
            page.progress_text.setText(was[5])
        api.undo(back)
        page.run_btn.setEnabled(False)
        page.cancel_btn.show()
        page.progress.show()
        page.progress.setMaximum(100)
        page.progress.setValue(0)
        page.progress_text.setText("Starting…")
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
        yield from _mock_combo(api, combo, i)
        api.undo(page.demo_graph(**({"view": view} if view is not None else {"y": y})))
        api.spot_on(page.plot)
        yield 1500

    def result_demo(api):
        api.say("“Fewer or more filters”: the best result for each count")
        if page.count_combo.count() > 1:
            yield from _mock_combo(api, page.count_combo, max(0, page.count_combo.currentIndex() - 1))
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
        b = _button(page.result_box, "Save filters")
        yield from api.click(b)
        yield from api.note("Saved “My EQ”. (Demo: nothing was saved.)", b, 1500)
        api.say("Use on device: the EQ becomes a device's, switched on (or try it for 5 minutes)")
        yield from api.click(page.use_btn)
        from switcher.core import shown
        sw = page.sw
        names = [f"{shown(sw.record(d.key))}  ·  " + ("playing now" if d.key == sw.playing_key else "connected"
                                                       if d.connected else "not connected") for d in sw.devices][:5]
        m = yield from _mock_menu(api, page.use_btn, (names or ["Headphones  ·  playing now"]) + [None, "Try for 5 minutes on ▸"])
        yield from _pick(api, m, 0)
        api.close(m)
        yield from api.note("Its EQ now, switched on. (Demo: nothing was changed.)", page.use_btn, 1500)

    def listen_demo(api):
        L = page.listen
        api.undo(L.render_ab)  # (put back last: the version buttons as the choice is again)
        api.say("Music, noise, a sweep, a tone or your own file")
        k = next((n for n in range(L.src.count()) if "pink" in L.src.itemText(n).lower()), min(1, L.src.count() - 1))
        yield from _mock_combo(api, L.src, k)
        api.say("Play (the demo stays quiet)")
        yield from api.click(L.play_btn)
        api.stage_text(L.play_btn, "■ Stop")
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
            yield from _mock_combo(api, L.ears, k)
            L.render_ab()
            api.spot_on(L.split_row)
            yield 1500

    def preset_demo(api):
        b = win.presets_btn
        names = page.preset_names()
        items = (names[:5] or [("No presets yet", False)]) + [None, "Save current settings as…", "Delete a preset ▸",
                                                              None, "Reset all settings…"]
        api.say("Click Presets")
        yield from api.click(b)
        m = yield from _mock_menu(api, b, items)
        api.spot_on(m)
        api.say("“Save current settings as…”")
        yield from _pick(api, m, items.index("Save current settings as…"))
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
        m = yield from _mock_menu(api, b, ["Equalizer APO"] + [x for x in items if x != ("No presets yet", False)])
        yield from _pick(api, m, 0)
        api.close(m)
        yield from api.note("Loaded: all its settings are back.", b, 1300)

    def history_demo(api):
        from PySide6.QtCore import QSize
        from ui.history_window import HistoryWindow
        w = HistoryWindow(page)
        api.window(w, near=_button(page, "History"), size=QSize(int(min(700, api.t.width() * 0.6)),
                                                             int(min(520, api.t.height() * 0.6))))
        api.spot_on(w.frame)
        yield from api.at(w.scroll, 0.4, 0.25, 1500, say="Your past EQs by day: Show brings one back with its files, "
                                                         "Listen adds it to your EQs to compare")
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
         "demo": lambda: _adjust_demo(page)},
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
         "target": lambda: _button(page, "Other measurements of this model…"),
         "text": "Ranks every measurement of your model for your target: the rig first, then how well they agree, "
                 "the bass seal and the seatings; it can average several from one rig.",
         "demo": [{"click": lambda: _button(page, "Other measurements of this model…"),
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
                  {"at": lambda: _button(st.fold, "Edit as a table…"), "say": "…or as a table or sliders"},
                  {"at": lambda: _button(st.fold, "Load an EQ file…"), "say": "Or load an EQ file; with filters there, "
                   "“Keep them exactly” keeps them as they are, else the fit adjusts them too"}],
         "alt_demo": [{"at": lambda: page.mode_combo, "say": "Choose Best fit as the method to start from your own filters"}]},
        {"chapter": "3 · Run & review", "title": "Run", "target": lambda: [page.run_btn, page.queue_btn, page.estimate],
         "text": "Finds the filters. Longer runs show their progress and can be cancelled. Run several… makes EQs for "
                 "several IEMs or targets in one go (each saved and kept in History).",
         "demo": [{"click": lambda: page.run_btn, "say": "Click Run", "then": run_demo},
                  {"at": lambda: page.queue_btn, "say": "Run several…: several IEMs or targets in one go"}]},
        {"chapter": "3 · Run & review", "title": "Check it on the graph", "target": lambda: page.plot, "ready": has_curves,
         "text": "Orange: your IEM. Dashed: the target. Blue: with the EQ, and under it the EQ itself (above 0 boosts, "
                 "below cuts). Point at the graph for each curve's value; the shaded ends aren't scored.",
         "demo": lambda: [{"run": graph_demo, "say": "With the EQ, your IEM becomes the blue curve, close to the target"},
                          {"at": lambda: page.plot, "x": 0.3, "y": 0.35, "then": _plot_value(page, 0.3, 0.35),
                           "say": "Point at the graph: its values show above it"},
                          {"at": lambda: page.plot, "x": 0.72, "y": 0.4, "then": _plot_value(page, 0.72, 0.4),
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
        {"chapter": "3 · Run & review", "title": "Save it, or use it on a device",
         "target": lambda: [page.name_edit, page.formats_line, _button(page.result_box, "Save filters"), page.use_btn],
         "before": result_before, "after": result_after, "ready": has_curves,
         "text": lambda: "Save filters writes your EQ app's file under the File name; Copy puts the filters on the "
                         "clipboard; Use on device makes the EQ a device's profile and switches it on (or tries it there "
                         "for 5 minutes); 📌 Keep to compare adds it to your EQs to compare; Report makes an HTML page."
                         + example(),
         "demo": [{"run": save_demo, "say": "Name it, save it, or use it on a device"}]},
        {"chapter": "3 · Run & review", "title": "Listen", "target": lambda: page.listen, "ready": lambda: page.listen.isVisible(),
         "text": "Play music, noise, a sweep, a tone or your own song through the EQ on your IEM or headphone, and "
                 "switch between versions. Start quiet.",
         "demo": [{"run": listen_demo, "say": "Choose a sound, play, switch versions"}]},
        {"chapter": "3 · Run & review", "title": "Your EQs to compare", "target": lambda: page.listen.pins_box,
         "ready": lambda: page.listen.isVisible(),
         "text": "Keep the EQs you want to hear side by side: from the result card (📌 Keep to compare), History, an "
                 "EQ file or pasted filters. Each IEM or headphone has its own list, kept between sessions; ticked "
                 "Graph: on the graph too.",
         "demo": [{"at": lambda: _button(page.listen, "+ The selected EQ"), "say": "The EQ on the result card"},
                  {"at": lambda: _button(page.listen, "+ An EQ file…"), "say": "An EQ file (Equalizer APO, squiglink…)"},
                  {"at": lambda: _button(page.listen, "+ Paste filters…"), "say": "Or filters pasted from anywhere"}]},
        {"chapter": "3 · Run & review", "title": "Compare by ear", "target": lambda: page.listen,
         "ready": lambda: page.listen.isVisible(),
         "text": "Level-matched so you compare the sound, not the volume. A blind test hides which is which; or put a "
                 "different version in each ear.",
         "demo": [{"run": compare_ear_demo, "say": "A blind test, or a version in each ear"}]},
        {"chapter": "More", "title": "Presets", "target": lambda: win.presets_btn, "top bar": True,
         "text": "Save all settings under a name and load them later, e.g. one for the website and one for Equalizer "
                 "APO. A preset keeps settings, not your files.",
         "demo": [{"run": preset_demo, "say": "Save the settings as a preset, load it later"}]},
        {"chapter": "More", "title": "History", "target": lambda: _button(page, "History"),
         "text": "Your past EQs, kept after you close the app: the ones you save or copy (or every run: Advanced › "
                 "History). Show one to bring it back with its files, or Listen to add it to your EQs to compare.",
         "demo": lambda: [{"click": lambda: _button(page, "History"), "say": "History: your past EQs", "then": history_demo}]
         + ([{"at": lambda: page.eqd_show, "say": "Under Measurement: when you've EQ'd it before; Show opens those"}]
            if page.eqd_show.isVisible() else [])},
        {"chapter": "More", "title": "Only have a picture of a graph?", "target": lambda: _button(page, "✎ Trace image"),
         "text": "Trace image turns a graph's picture into a measurement or a target. It has its own Guide. You can "
                 "also paste or drop a picture on the window.",
         "demo": [{"at": lambda: _button(page, "✎ Trace image"), "say": "A picture of a graph becomes a curve"}]},
        {"chapter": "More", "title": "Your devices", "target": lambda: win.nav["devices"], "top bar": True,
         "text": "Devices gives each playback device its own EQ through Equalizer APO, switched by itself when the "
                 "device plays, with a line saying whether it really plays; Profiles lists the EQs. Use on device puts "
                 "a result there in one click.",
         "demo": [{"at": lambda: win.nav["devices"], "say": "Each device's own EQ"},
                  {"at": lambda: win.nav["profiles"], "say": "Your EQs, as profiles"}]},
        {"chapter": "More", "title": "Settings", "target": lambda: st.adv.btn,
         "text": "Advanced, under Settings: what's set for you (Best fit's layout, limits and penalties, the website "
                 "sweep's lists, the website's own details, the files Save writes, History, CPU cores). A list of more "
                 "than 15 choices, like Layout, opens with a search box. The Settings screen (top bar) has where your "
                 "files are, backups, Online / Offline and Start with Windows.",
         "demo": lambda: [{"at": lambda: st.adv.btn, "x": 0.1, "say": "Advanced: what's set for you"}]
         + ([{"at": lambda: win.nav["settings"], "say": "The app's own settings"}] if hasattr(win, "nav") else [])},
        {"chapter": "More", "title": "Help, and that's it", "target": lambda: _button(win, "? Help"), "top bar": True,
         "text": "Help explains every term (Q, shelf, rig, pre-amp…) and answers common questions; point at a setting "
                 "for what it does, and F1 opens its entry. Open the Guide any time to see a step again.",
         "demo": [{"at": lambda: _button(win, "? Help"), "say": "Help: every term, and the questions that come up most"},
                  {"at": lambda: page.sa, "say": "Point at a setting for what it does; F1 opens its entry in Help"}],
         "buttons": [("Open Help", lambda: win.open_help())] if hasattr(win, "open_help") else []},
    ]
    # (the steps about the app window's top bar: only when the screen is in it, not on its own as in the checks)
    return [s for s in steps if not s.get("top bar") or hasattr(win, "nav")]


def start_eq(page):
    return tour.Tour(page, eq_steps(page))


# ---------------------------------------------------------------- the tracer's own Guide
def trace_steps(tw):
    """Trace image's Guide (on the sample graph when no picture is open: start_trace opens it)."""
    t = tw.t
    traced = lambda: any(t.has_data(c) for c in t.curves)

    def show_traces():  # (the sample: its curves traced for the steps that show them)
        if getattr(tw, "sample_open", False) and not traced():
            t.auto_trace()
            t.auto_trace()
            tw.changed()
    steps = [
        {"chapter": "Overview", "title": "How tracing a graph goes", "target": lambda: tw.stage,
         "text": "Open a graph's picture, check the axes it read, trace the curve (Auto trace does it), and save it as "
                 "a measurement or a target." + (" This is a sample graph: yours comes back when the tour ends."
                                                 if getattr(tw, "sample_open", False) else "")},
        {"chapter": "1 · Picture", "title": "The picture", "target": lambda: tw.stage,
         "text": "Drop a graph's picture here, paste it (Ctrl+V) or use Open image… (Remove image takes a wrong one "
                 "away). The mouse wheel zooms, the right button (or Space) moves it, F fits it; the box at the top "
                 "left says the frequency and dB under the pointer.",
         "demo": [{"at": lambda: tw.stage, "x": 0.5, "y": 0.5, "say": "Drop, paste or open a picture here"},
                  {"drag": lambda: tw.stage, "from": (0.35, 0.6), "to": (0.55, 0.45),
                   "say": "The right button (or Space) moves it; the wheel zooms"}]},
        {"chapter": "1 · Picture", "title": "Automatic settings", "target": lambda: tw.auto_on.parentWidget(),
         "text": "Fitted to the picture: colour tolerance, points per octave, the range to save, dashed lines. Labels "
                 "are read large, the trace sits between pixels and stopped traces are retried. A setting you change "
                 "is marked “yours” until ↺."},
        {"chapter": "2 · Axes", "title": "Check the axes", "target": lambda: tw.boxes["d1"].parentWidget(),
         "text": "Red lines mark two dB gridlines, blue lines two frequency gridlines. They're placed and their labels "
                 "read by themselves (green boxes: the labels used). If one's off, drag it onto another gridline and "
                 "type its value.",
         "demo": [{"at": lambda: tw.boxes["d1"], "say": "The top red line's dB"},
                  {"at": lambda: tw.boxes["d2"], "say": "The bottom red line's dB"},
                  {"at": lambda: tw.boxes["f1"], "say": "The left blue line's Hz"},
                  {"at": lambda: tw.boxes["f2"], "say": "The right blue line's Hz"}]},
        {"chapter": "2 · Axes", "title": "Snap and follow gridlines", "target": lambda: [tw.snap, tw.every],
         "text": "Snap keeps dragged lines on gridlines. Follow every gridline uses all those in between, which reads "
                 "unevenly drawn axes right. Leave both ticked."},
        {"chapter": "2 · Axes", "title": "Read labels / Find axes again", "target": lambda: [tw.ocr_btn, _button(tw, "Find axes again")],
         "text": "Read the labels or find the gridlines again, e.g. to undo changes made by hand."},
        {"chapter": "3 · Trace", "title": "Tools", "target": lambda: list(tw.tool_btns.values()),
         "text": "Click curve: click a curve to follow it. Draw: drag along it by hand. Erase: drag a box over a bad "
                 "part. Move: drag the picture. Keys T, D, E, H.",
         "demo": lambda: [{"at": (lambda b=b: b), "say": b.toolTip()} for b in tw.tool_btns.values()]},
        {"chapter": "3 · Trace", "title": "Auto trace", "target": lambda: [tw.auto_btn, tw.tol, tw.swatch],
         "before": show_traces,
         "text": "Finds and follows a curve; press again for the next (e.g. the other channel). A curve that stops "
                 "early is tried again as dashed, or with more tolerance. The swatch shows the colour traced.",
         "demo": [{"click": lambda: tw.auto_btn, "say": "Finds and follows a curve"},
                  {"at": lambda: tw.swatch, "say": "The colour it traced"}]},
        {"chapter": "3 · Trace", "title": "Several curves", "target": lambda: [tw.curves_box, tw.add_btn],
         "before": show_traces,
         "text": "Each traced curve with its name (L, R…). The tools change the selected one; ✕ deletes it. + Another "
                 "curve starts a new one; saved together they become one device.",
         "demo": [{"at": lambda: tw.curves_box, "say": "Each traced curve and its name"},
                  {"at": lambda: tw.add_btn, "say": "Start another one (the other channel)"}]},
        {"chapter": "3 · Trace", "title": "Dashed or dotted lines", "target": lambda: tw.dashed,
         "text": "The trace carries on across the gaps of a dashed or dotted curve. The automatic settings tick it "
                 "when a trace stops at gaps."},
        {"chapter": "3 · Trace", "title": "Fixing up", "target": lambda: list(tw.edit_btns.values()),
         "text": "Smooth evens out pixel steps. Undo and Redo (Ctrl+Z, Ctrl+Shift+Z) cover every curve. Clear empties "
                 "the selected one.",
         "demo": lambda: [{"at": (lambda b=b: b), "say": b.toolTip()} for b in tw.edit_btns.values()]},
        {"chapter": "4 · Save", "title": "Compensated graphs", "target": lambda: tw.comp,
         "text": "If the graph is drawn relative to a target (e.g. “compensated to DF”), choose it here and it's added "
                 "back when saving. The target must be in the app."},
        {"chapter": "4 · Save", "title": "Save", "target": lambda: [tw.save_meas, tw.save_tgt, tw.download_btn],
         "text": "Add as measurement puts it in the app and in use. Add as target saves the selected curve. Save .txt… "
                 "is for use elsewhere.",
         "demo": [{"click": lambda: tw.save_meas, "say": "Into the app, in use"},
                  {"at": lambda: tw.save_tgt, "say": "Or as a target"},
                  {"at": lambda: tw.download_btn, "say": "A .txt file for elsewhere"}]},
        {"chapter": "4 · Save", "title": "That's it", "target": lambda: tw.guide_btn,
         "text": "Tips: crop loosely so the labels stay in, bigger pictures read better, and check the green boxes and "
                 "the lines before saving."},
    ]
    return steps


def start_trace(tw):
    """The tracer's tour; with no picture open, on the sample graph (closed again at the end, the tracer as it was)."""
    t = tw.t
    if not t.has_image:
        from ui.trace_window import sample_image
        kept = {"v": dict(t.v), "ta": {k: (set(v) if isinstance(v, set) else dict(v) if isinstance(v, dict) else v)
                                         for k, v in t.ta.items()}}
        img, _s = sample_image()
        tw.load_image(img, "Sample graph")
        tw.sample_open = True

        def close():
            if not getattr(tw, "sample_open", False):  # (a picture of yours loaded during the tour: kept)
                return
            tw.sample_open = False
            t.unload()
            t.v.update(kept["v"])
            t.ta.update(kept["ta"])
            tw.reading = False
            tw.stage.clear_image()
            tw.file_lab.setText("")
            tw.show_values()
            tw.changed()
            tw.status.setText("")
        return tour.Tour(tw, trace_steps(tw), on_end=close)
    return tour.Tour(tw, trace_steps(tw))
