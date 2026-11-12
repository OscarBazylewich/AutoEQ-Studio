"""The words of the tracer's Guide (ui\\guide_trace.py): each step text has 6 sentences or fewer (with the note of
the sample graph too) and each sentence 25 words or fewer (ASD-STE100 rules 6.1 and 7.3; 2026-11-12: the steps "How
to trace a graph" and "The picture" had 7 sentences). The steps are made from the window, as the Guide makes them;
the sentences are split as tests\\eq_screen\\test_guide_words.py splits those of Make an EQ."""
import re

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.guide_trace", "ui.eq_page")


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z“(])", text.strip()) if s.strip()]


def _words(sentence):
    return len(re.findall(r"[A-Za-z0-9][\w'’.,+×/-]*", sentence))


def test_trace_guide_sentences(eq_screen, check):
    from ui import guide_trace
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    seen = {}
    for sample in (False, True):
        tw.sample_open = sample  # (the step "How to trace a graph" has one sentence more on the sample graph)
        for step in guide_trace.trace_steps(tw):
            text = step["text"]
            seen[(sample, step["title"])] = (len(_sentences(text)), max(_words(s) for s in _sentences(text)))
    tw.sample_open = False
    tw.close()
    check("tracer's Guide: each step text has 6 sentences or fewer, also with the note of the sample graph",
          len(seen) >= 20 and all(n <= 6 for n, _w in seen.values()), {k: v for k, v in seen.items() if v[0] > 6})
    check("tracer's Guide: each sentence of a step text has 25 words or fewer",
          all(w <= 25 for _n, w in seen.values()), {k: v for k, v in seen.items() if v[1] > 25})
    first = guide_trace.trace_steps(tw)[0]["text"]
    check("tracer's Guide: the first step keeps all its facts (open, examine the axes that the app found, trace, "
          "Trace automatically, save as a measurement or a target)",
          all(w in first for w in ("open a picture", "examine the axes that the app found", "trace the curve",
                                   "Trace automatically", "as a measurement or a target")), first)
