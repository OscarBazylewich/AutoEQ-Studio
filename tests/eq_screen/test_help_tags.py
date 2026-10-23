"""F1 on Make an EQ and the tracer (ui\\help_window.py's tags): every control tagged for F1 has a help text. Moved
from eq_checks.py's guide_checks (lines 2632-2639), on a page opened as the old checks opened it (the eq_screen
fixture) with the tracer as the old checks had made it by then (trace_checks: the sample graph opened and traced,
helpers.eqpage.open_traced_sample), the page 1100x900 as there. And (2026-10-23) each tagged button's entry named in
Help as the button reads."""
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


def test_buttons_named_in_help_as_they_read(eq_screen, check):
    # (2026-10-23, the restyle's checkers: Help's entry for Retry from these filters was titled “↻ Retry from these
    # filters”, the button's words before the restyle; F1 opens that entry, and a screen reader names the button by it)
    from PySide6.QtWidgets import QAbstractButton, QCheckBox, QRadioButton
    from ui import help_text_eq, help_window
    page = eq_screen.page
    titles = {it["key"]: it["title"] for section in help_text_eq.SETTINGS_EQ for it in section["items"]}
    named = {}
    for b in page.findChildren(QAbstractButton):
        key = help_window.help_key(b.property("help_key") or "")
        if key in titles and not isinstance(b, (QCheckBox, QRadioButton)):  # (a tick box's words say more)
            named[b.text()] = titles[key]
    wrong = {words: title for words, title in named.items() if not title.startswith(words)}
    check("help: each button on Make an EQ that F1 explains has its entry in Help named as the button reads (“↻ Retry "
          "from these filters” kept a symbol the button no longer has)", len(named) >= 5 and not wrong, (named, wrong))
