"""Stand-ins for the tracer's automatic read (trace_core.auto_read), and 3 Save's row of buttons, for the tests of
the tracer's window (tests\\tracer). A stand-in is fast and needs no text reader: monkeypatch it onto
trace_core.auto_read. (One place for the copies that were in several files, the test audit of 2026-11-25.)"""


def ok_read(target_line=False, only=False):
    """A stand-in read that is OK: the picture as it is, the sample's dB values, a part of a curve, all checks OK;
    target_line: also a target line, marked; only: the one curve is the target line (target_only)."""
    def read(rgb, ocr_words=None, jpeg=False, name="Traced graph", want=None):
        import numpy as np
        from ui import trace_core
        from ui.trace_auto import AutoRead, Check
        t = trace_core.Tracer()
        t.load(np.array(rgb, np.uint8, copy=True), name, jpeg)
        t.v.update(d1="90", d2="40")
        t.curves[0]["ys"][100:200] = 300.0  # (a traced curve)
        line = None
        if only:
            t.curves[0].update(label="Target", target=True)
        elif target_line:
            ys = np.full_like(t.curves[0]["ys"], np.nan)
            ys[100:200] = 350.0
            line = {"label": "Target", "colour": (136, 136, 136), "ys": ys, "target": True}
            t.curves.append(line)
        return AutoRead(True, t, [Check("axes_plot", True, "The app found the graph in the image.")], t.curves[0],
                        line, None, None, None, 0.01, "", only)
    return read


def not_ok_read(rgb, ocr_words=None, jpeg=False, name="Traced graph", want=None):
    """A stand-in read that is not OK: the picture as it is, and the curve check failed ("No curve.")."""
    import numpy as np
    from ui import trace_auto, trace_core
    t = trace_core.Tracer()
    t.load(np.array(rgb, np.uint8, copy=True), name, jpeg)
    return trace_auto.AutoRead(False, t, [trace_auto.Check("trace_curve", False, "No curve.")], None, None, None,
                               None, None, 0.01)


def save_row(tw):
    """3 Save's buttons in their order, each with whether it is the accent button."""
    from helpers import qt
    # (found with indexOf, not itemAt: no Python object of a layout item is made, app\ui\__init__.py)
    return [(w.text(), w.property("primary") in (True, "true")) for w in qt.layout_parts(tw.save_btns)
            if w is not None and w.isWidgetType()]
