"""The words of the tracer's Guide (ui\\guide_trace.py): the first step, "How to trace a graph", keeps all its facts
(2026-11-12: its text was made shorter). The steps are made from the window, as the Guide makes them."""

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.guide_trace", "ui.eq_page")


def test_trace_guide_first_step_keeps_its_facts(eq_screen, check):
    from ui import guide_trace
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    tw.close()
    first = guide_trace.trace_steps(tw)[0]["text"]
    check("tracer's Guide: the first step keeps all its facts (open, examine the axes that the app found, trace, "
          "Trace automatically, save as a measurement or a target)",
          all(w in first for w in ("open a picture", "examine the axes that the app found", "trace the curve",
                                   "Trace automatically", "as a measurement or a target")), first)
