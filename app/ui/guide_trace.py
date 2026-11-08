"""Trace image's Guide (AutoEQ Local's tracer TOUR, told for AutoEQ Studio's window; ui/tour.py shows it):
trace_steps(tw), every step in order, and start_trace(tw), the tour, on the sample graph when no picture is
open. Keep the steps in their order: the checks find the Auto trace step by its place (t.go_to_step(7)).
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
        {"chapter": "The parts of AutoEQ Studio", "title": "How to trace a graph", "target": lambda: tw.stage,
         "text": "Open a picture of a graph. Examine the axes that the app found. Trace the curve (Trace automatically "
                 "does this). Save it as a measurement or a target." + (" This is a sample graph. It closes at the end "
                                                                       "of the Guide."
                                                 if getattr(tw, "sample_open", False) else "")},
        {"chapter": "1 · Picture", "title": "The picture", "target": lambda: tw.stage,
         "text": "Drag a picture of a graph here, paste it (Ctrl+V), or click Open image…. To remove an incorrect "
                 "picture, click Remove image. Zoom in and out with the mouse wheel. Move the picture with the right mouse button "
                 "(or Space). F shows all the picture. The box at the top left shows the frequency and dB at the "
                 "mouse.",
         "demo": [{"at": lambda: tw.stage, "x": 0.5, "y": 0.5, "say": "Drag, paste or open a picture here"},
                  {"drag": lambda: tw.stage, "from": (0.35, 0.6), "to": (0.55, 0.45),
                   "say": "The right mouse button (or Space) moves the picture. The mouse wheel zooms in and out."}]},
        {"chapter": "1 · Picture", "title": "Automatic settings", "target": lambda: tw.auto_on.parentWidget(),
         "text": "The app adjusts these settings for the picture: color tolerance, points in each octave, the range to "
                 "save and dashed lines. It makes the labels larger before it reads them, and puts the traced line "
                 "between pixels. If a traced line stops before the end of the curve, the app tries again. If "
                 "you change a setting, it shows “your value” until you click ↺."},
        {"chapter": "2 · Axes", "title": "Examine the axes", "target": lambda: tw.boxes["d1"].parentWidget(),
         "text": "The red lines show two dB grid lines, and the blue lines show two frequency grid lines. The app puts "
                 "them on grid lines and reads their labels (the green boxes show the labels that it used). If a line "
                 "is not correct, drag it to a different grid line. Then type its value.",
         "demo": [{"at": lambda: tw.boxes["d1"], "say": "The top red line's dB"},
                  {"at": lambda: tw.boxes["d2"], "say": "The bottom red line's dB"},
                  {"at": lambda: tw.boxes["f1"], "say": "The left blue line's Hz"},
                  {"at": lambda: tw.boxes["f2"], "say": "The right blue line's Hz"}]},
        {"chapter": "2 · Axes", "title": "Align with grid lines and follow them", "target": lambda: [tw.snap, tw.every],
         "text": "Align with grid lines keeps the lines that you drag on grid lines. Follow all grid lines uses all the "
                 "grid lines between them, for irregular axes. Keep the two selected."},
        {"chapter": "2 · Axes", "title": "Read labels / Find axes again", "target": lambda: [tw.ocr_btn, tw.detect_btn],
         "text": "These buttons read the labels or find the grid lines again, for example to undo your manual changes."},
        {"chapter": "3 · Trace", "title": "Tools", "target": lambda: list(tw.tool_btns.values()),
         "text": "Click curve: click a curve to follow it. Make a line: drag along the curve to make a line manually. "
                 "Erase: drag a box around an incorrect part. Move: drag the picture. The keys are T, D, E and H.",
         "demo": lambda: [{"at": (lambda b=b: b), "say": b.toolTip()} for b in tw.tool_btns.values()]},
        {"chapter": "3 · Trace", "title": "Trace automatically", "target": lambda: [tw.auto_btn, tw.tol, tw.swatch],
         "before": show_traces,
         "text": "This button finds a curve and follows it. Click it again for the next curve (for example, the other "
                 "channel). If a traced line stops before the end of the curve, the app tries again as a dashed "
                 "line, or with more tolerance. The color box shows the color that you trace.",
         "demo": [{"click": lambda: tw.auto_btn, "say": "It finds and follows a curve"},
                  {"at": lambda: tw.swatch, "say": "The color that it traced"}]},
        {"chapter": "3 · Trace", "title": "More than one curve", "target": lambda: [tw.curves_box, tw.add_btn],
         "before": show_traces,
         "text": "Each traced curve has its name (L, R…). Its colored dot selects it, and ✕ removes it. The tools "
                 "change the selected curve. Add a curve starts a new curve. If you save the curves together, they "
                 "become one device.",
         "demo": [{"at": lambda: tw.curves_box, "say": "Each traced curve and its name"},
                  {"at": lambda: tw.add_btn, "say": "Start a new curve (the other channel)"}]},
        {"chapter": "3 · Trace", "title": "Dashed or dotted lines", "target": lambda: tw.dashed,
         "text": "The traced line continues across the spaces in a dashed or dotted curve. If a traced line stops at "
                 "spaces, the automatic settings select this tick box."},
        {"chapter": "3 · Trace", "title": "Correct the curve", "target": lambda: list(tw.edit_btns.values()),
         "text": "Make smooth makes the pixel steps smooth. Undo and Redo (Ctrl+Z, Ctrl+Shift+Z) are for all curves. "
                 "Clear removes the traced line of the selected curve.",
         "demo": lambda: [{"at": (lambda b=b: b), "say": b.toolTip()} for b in tw.edit_btns.values()]},
        {"chapter": "4 · Save", "title": "Compensated graphs", "target": lambda: tw.comp,
         "text": "If the graph shows the difference from a target (for example, “compensated to DF”), select that "
                 "target here. The app adds the target to the curve when you save it. The target must be in the "
                 "app."},
        {"chapter": "4 · Save", "title": "Save", "target": lambda: [tw.save_meas, tw.save_tgt, tw.download_btn],
         "text": "Add as measurement adds the curves to the app and uses them. Add as target saves the selected curve. "
                 "Save .txt… makes a file for other apps.",
         "demo": [{"click": lambda: tw.save_meas, "say": "It adds the curves to the app and uses them"},
                  {"at": lambda: tw.save_tgt, "say": "Or as a target"},
                  {"at": lambda: tw.download_btn, "say": "A .txt file for other apps"}]},
        {"chapter": "4 · Save", "title": "The end", "target": lambda: tw.guide_btn,
         "text": "Make sure that the picture includes the labels. Larger pictures give better results. Before you "
                 "save, examine the green boxes and the lines."},
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
