"""F1 on Make an EQ and the tracer (ui\\help_window.py's tags): every control tagged for F1 has a help text. Moved
from eq_checks.py's guide_checks (lines 2632-2639), on a page opened as the old checks opened it (the eq_screen
fixture) with the tracer as the old checks had made it by then (trace_checks: the sample graph opened and traced,
helpers.eqpage.open_traced_sample), the page 1100x900 as there."""
import pytest

from helpers import eqpage


@pytest.mark.timeout(600)  # (the tracer's labels read and three Auto traces first)
def test_every_tagged_control_has_help(eq_screen, check):
    from PySide6.QtWidgets import QWidget
    from ui import help_window
    page = eq_screen.page
    eqpage.open_traced_sample(eq_screen)  # (page.tracer, as trace_checks left it: line 2772)
    page.resize(1100, 900)
    tagged = [w.property("help_key") for root in (page, page.tracer) for w in root.findChildren(QWidget)
              if w.property("help_key")]
    unknown = sorted({k for k in tagged if not help_window.help_key(k)})
    # was eq_checks.py:2638
    check("help: every control tagged for F1 (Make an EQ, the tracer) has a help text", len(tagged) > 60 and not unknown,
          (len(tagged), unknown))
