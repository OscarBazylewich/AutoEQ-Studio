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


def test_handle_tooltip_names_its_menu(check):
    # (2026-11-10, the review: the graph's handle tooltip still named an On item its menu does not have)
    import os
    import re
    from types import SimpleNamespace

    from helpers import paths
    from ui.eq_page_handles import EqHandles
    tip = EqHandles.handle_tip(SimpleNamespace(EDIT=[{"freq": 1000, "gain": 3.0, "q": 1.0, "type": "PK"}]), 0)
    with open(os.path.join(paths.PROJECT_APP, "ui", "eq_page_handles.py"), encoding="utf-8") as fh:
        menu = re.search(r"def handle_menu.*?\n    def ", fh.read(), re.S).group(0)
    check("help: a graph handle's tooltip names the items of its right-click menu (its type, Remove; no On)",
          tip.endswith("right-click: type, Remove") and 'addAction("Remove"' in menu and '"On"' not in menu, tip)


def test_use_on_device_has_its_own_help(eq_screen, check):
    # (2026-11-11: the button had the tag of Use for 5 minutes on, so its tooltip and F1 told only one of its 3
    # functions)
    from ui import help_window
    btn = eq_screen.page.use_btn
    entry = help_window.entry_for(btn.property("help_key") or "")
    e = help_window._by_id().get(entry or "", {})  # (as tests/ui/test_help.py reads the entries)
    check("help: Use on device has its own Help entry, whose tooltip names its 3 functions and whose entry links to "
          "Update a profile and Use for 5 minutes on",
          btn.property("help_key") == "#use-device" and entry == "set-use-device"
          and btn.toolTip().startswith("Uses the EQ on a device: as a new profile of the device, in a profile that you "
                                       "have (Update a profile), or for 5 minutes.")
          and e.get("title") == "Use on device (Make an EQ)" and e.get("see") == ["set-use-update", "set-use-try"],
          (btn.property("help_key"), entry, btn.toolTip(), e.get("title"), e.get("see")))


def test_update_words_are_true_for_each_device(check):
    # (2026-11-11: the short help of Update and the Guide said that the devices that have the profile on use the new
    # EQ, with no condition: untrue for a device that is not connected or has no Equalizer APO)
    import os

    from helpers import paths
    from ui.help_texts import HELP
    with open(os.path.join(paths.PROJECT_APP, "ui", "guide_eq.py"), encoding="utf-8") as fh:
        guide = fh.read()
    short = HELP["#use-update"][0]
    check("help: the short help of Update a profile says what is true for each device, and Help gives the conditions",
          short == "Puts the EQ into a profile that you have. The profile keeps its name and its devices. Help tells "
                   "when each device uses the new EQ." and "have it on use the new" not in guide, (short,))
