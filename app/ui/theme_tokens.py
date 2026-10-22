"""The app's colours (AutoEQ Local's app.css tokens): LIGHT and DARK, one dictionary each, by token name ("bg"
the window, "card" a card, "ink" the text, "muted" secondary text, "line" borders, "c1" the accent, "sel" a
selected or checked background …). theme.py takes them from here (and Windows' own colours in a contrast theme)
and builds the look from them: a new palette is this file. Nothing is imported here.
"""
LIGHT = {"bg": "#f4f4f1", "card": "#ffffff", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#6b6a65",
         "line": "#e4e3de", "field": "#fbfbfa", "meas": "#eb6834", "tgt": "#52514e", "c1": "#1f68bf", "c2": "#1baf7a",
         "c3": "#4a3aa7", "c4": "#e34948", "c5": "#eda100", "sel": "#e3eefb", "shade": "#efeee9", "warn": "#b35a00",
         "err": "#c62828", "btn": "#226cc4", "good": "#107a55", "pill": "#eef5ea", "grid": "#e4e3de",
         "on_btn": "#ffffff", "on_sel": "#ffffff", "sel_ink": "#0b0b0b", "sel_accent": "#1f68bf"}
DARK = {"bg": "#111110", "card": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#9d9c94", "line": "#34332f",
        "field": "#141413", "meas": "#d95926", "tgt": "#c3c2b7", "c1": "#5a9cf0", "c2": "#199e70", "c3": "#9085e9",
        "c4": "#e66767", "c5": "#c98500", "sel": "#1c3350", "shade": "#1f1f1d", "warn": "#f0a050", "err": "#ef7b7b",
        "btn": "#2a70cc", "good": "#199e70", "pill": "#1f3325", "grid": "#2a2a27",
        "on_btn": "#ffffff", "on_sel": "#ffffff", "sel_ink": "#ffffff", "sel_accent": "#5a9cf0"}
# (sel_ink, sel_accent: text on sel, the selected or checked background; in a contrast theme Windows' HighlightText)
