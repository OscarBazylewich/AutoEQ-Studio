"""The Guides' demo helpers (guide_eq.py's and guide_trace.py's steps use them; ui/tour.py plays the demos): a
button found by its text, the card a control sits in, a fold opened for a step and closed after it, the graph's
values at a point, work waited for off the window's thread; an example EQ before a run (AutoEQ Local's demo
filters, shown on the result card); the app's own lists as the demos open them (a drop-down's list, a menu, a
row picked); Find… opened inside the tour, a search typed into it and a row used, its curve shown on the graph;
the target adjusted on the graph. A demo only shows: what it changes is put back when it ends, and nothing is
chosen, run, saved or downloaded.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton

from ui import tasks, theme


def button(root, text):
    return next((b for b in root.findChildren(QPushButton) if b.text() == text and b.isVisible()), None) or \
        next((b for b in root.findChildren(QPushButton) if b.text() == text), None)


def card(w):
    """The card (group box) a control sits in."""
    p = w
    while p is not None and not isinstance(p, QGroupBox):
        p = p.parentWidget()
    return p or w


def fold(btn, before):
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


def plot_value(page, fx, fy):
    """A demo's "then": the graph's values at a point of it, as when the pointer is there (put back after)."""
    from PySide6.QtCore import QPoint

    def then():
        pl = page.plot
        page._hover(pl.mapToScene(QPoint(int(pl.width() * fx), int(pl.height() * fy))))
        return lambda: page.hover_lab.setText("")
    return then


def bg(fn):
    """A demo waits (up to a few seconds) for work done off the window's thread: r = yield from bg(fn)."""
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
def mock_combo(api, combo, to_index, say_rows=None, rows=9):
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


def mock_menu(api, near, items):
    m = api.mock(near, items, width=max(near.width(), 280))
    yield 300
    return m


def pick(api, m, i, hold=350):
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
def open_picker(page, api, kind):
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


def type_search(api, pk, text):
    yield from api.move_to(pk.q, 0.1, 0.5)
    yield from api.ripple()
    for n in range(1, len(text) + 1):
        pk.q.setText(text[:n])
        yield 110
    pk._later.stop()
    pk.render()
    yield 600


def picker_rows(pk):
    out = []
    for k in range(pk.list.count()):
        it = pk.list.item(k)
        r = it.data(Qt.UserRole)
        if r and not r.get("current") and not r.get("link") and not r.get("other"):
            out.append((it, r))
    return out


def row_now(pk, r):
    """The list's item and row for result r as Find…'s list is now, or (None, None). Find… draws its rows again while
    its lists and This PC's search are still loading (it asks every half second), so a row kept across a demo's pause
    may be deleted: a demo finds it again after each pause (it reached for a deleted row, 2026-10-23)."""
    key = (r.get("src"), r.get("id"), r.get("name"))
    for k in range(pk.list.count()):
        it = pk.list.item(k)
        d = it.data(Qt.UserRole)
        if d and (d.get("src"), d.get("id"), d.get("name")) == key:
            return it, pk.list.itemWidget(it)
    return None, None


def choose_row(page, api, pk, prefer, combo):
    """A row of the real list hovered and its Use clicked; the window closes and the box shows it; its curve (a file
    in the app or on this PC: read there, nothing downloaded) is returned."""
    rows = picker_rows(pk)
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
    _it, w = row_now(pk, r)  # (its row may have been drawn again during the pause)
    use = next((b for b in w.findChildren(QPushButton) if b.text() == "Use"), w) if w is not None else None
    if use is not None:  # (gone from the list meanwhile: the demo goes on without pointing at its Use)
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
    res = yield from bg(lambda: page.svc.call("/api/preview", body))
    vals = (res or {}).get("vals")
    return (r["name"], vals) if vals and page.curves and len(vals) == len(page.curves["f"]) else None


def show_on_graph(page, api, key, vals, label, keep):
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


def adjust_demo(page):
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
