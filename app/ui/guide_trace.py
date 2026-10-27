"""Trace image's Guide (AutoEQ Local's tracer TOUR, told for AutoEQ Studio's window; ui/tour.py shows it):
trace_steps(tw), every step in order, and start_trace(tw), the tour, on the sample graph when no picture is
open. Keep the steps in their order: the checks find the Auto trace step by its place (t.go(7)).
"""
from ui import tour


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
        {"chapter": "2 · Axes", "title": "Read labels / Find axes again", "target": lambda: [tw.ocr_btn, tw.detect_btn],
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
         "text": "Each traced curve with its name (L, R…); its coloured dot selects it, ✕ deletes it, and the tools "
                 "change the selected one. Add a curve starts a new one; saved together they become one device.",
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
