"""The Guides (AutoEQ Local's guide.js STEPS and the tracer's TOUR, told for AutoEQ Studio's window; ui/tour.py shows
them): eq_steps(page) for Make an EQ, trace_steps(tracer) for Trace image.

Make an EQ's Guide walks through a whole EQ job, as AutoEQ Local's did: choose, check the automatic settings, run,
review, save, listen. Its demos work the real window: Find… opens (inside the tour) and a search is typed into it, a
row is picked and shown on the graph; a drop-down's list opens and a choice shows in its box; the target changes on
the graph as the adjustments are typed; Run shows its progress and the EQ'd curve grows on the graph (kept in sight
while the page scrolls under it); before a run there's an example result (filters worked out from your files, as
AutoEQ Local's demo did). Everything is put back when a demo ends, and nothing is chosen, run, saved or downloaded.
When a control is renamed, moved or added, its step changes with it: the tests (tests\\eq_screen\\test_guide.py)
check that every step's control is there and can be seen (tour.problems()), and play every demo.

The steps are in guide_eq.py (Make an EQ's) and guide_trace.py (the tracer's), the demos' helpers in
guide_demos.py; the window, the tracer and the checks take eq_steps, start_eq, trace_steps and start_trace from
here.
"""
from ui.guide_eq import eq_steps, start_eq  # noqa: F401 - (the window and the checks take them from here)
from ui.guide_trace import start_trace, trace_steps  # noqa: F401 - (the tracer and the checks take them from here)
