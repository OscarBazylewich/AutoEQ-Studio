"""What every setting does, in a line (HELP: the tooltips), and the Help page's words (WIKI: questions, terms and
every setting in full). Brought from AutoEQ Local's gui\\help.js and gui\\wiki.js (2026-10-05), then told in
AutoEQ Studio's controls (2026-10-06: where things are, what they're called; no browser or presets here):
HELP[key] is the text, or [text, ...ids of WIKI entries]; a key is a setting's path ("best_fit.filter_counts"; a
"to" field shares its "from" field's: ".1" -> ".0"), or a name for a part of the window ("slot:target", "sa").
A control with NO tooltip keeps its key with an empty text ("" or ["", ...ids]): the text survey of 2026-11-24
removed the tooltip, but the key must stay, because F1 on the control, its name for a screen reader and the "See
also" links of its Help entry are all found through the key. Never delete the key to remove a tooltip.
tests\\eq_screen\\test_help_tags.py lists these keys (NO_TOOLTIP). A settings box (forms.Field) adds its
"Allowed: …" line to the text: emptying the text of a settings box does not yet take that line away.

The words themselves are kept per screen and joined here: help_text_terms.py (what every screen shares: the
introduction, the steps, the terms, the questions), help_text_eq.py (Make an EQ and its windows),
help_text_devices.py (Devices, Settings, Presets) and help_text_trace.py (Trace image). WIKI keeps the Help
page's order; HELP is only ever looked up by key, so its order doesn't matter.
"""
from ui.help_text_devices import HELP_DEVICES, SETTINGS_DEVICES
from ui.help_text_eq import HELP_EQ, SETTINGS_EQ
from ui.help_text_terms import INTRO, QUESTIONS, STEPS, TERMS
from ui.help_text_trace import HELP_TRACE, SETTINGS_TRACE

HELP = {**HELP_EQ, **HELP_DEVICES, **HELP_TRACE}
WIKI = {"intro": INTRO, "steps": STEPS, "groups": TERMS, "settings": SETTINGS_EQ + SETTINGS_DEVICES + SETTINGS_TRACE,
        "questions": QUESTIONS}
