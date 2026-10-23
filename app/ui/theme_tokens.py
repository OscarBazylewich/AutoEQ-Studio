"""The app's colours: Windows 11's (Fluent's, as WinUI 3 has them over Windows 11's window and card colours), light and
dark, by token name: "bg" the window, "card" a card, "ink" the text, "ink2" secondary text, "muted" quieter text,
"line" a card's border, "stroke" a control's, "field" a control's fill, "subtle_*" a quiet fill (pointed at, chosen),
"accent" the main action and what's chosen (Windows' own accent colour: build() takes its palette), and the graph's.
theme.py builds the look from them (and from Windows' own colours in a contrast theme). Text keeps 4.5:1 on what it
sits on (tests\\ui\\test_theme.py checks). Nothing is imported here.

build(dark, accent) gives one theme's tokens: BASE_LIGHT or BASE_DARK, the accent's colours from Windows' accent
palette (its seven shades, Light 3 to Dark 3: Windows' default blue unless another is given), the graph's colours
(GRAPH_LIGHT, GRAPH_DARK: fixed, never the accent), and the older names the screens use mapped on them (c1 the
accent, btn, sel, shade …). LIGHT and DARK are the two with Windows' default blue. In a screen's code: "accent" (and
"on_accent", "accent_text") for what the window marks, never for a curve; a curve takes theme.graph_colours() or the
graph's own c2 to c5.

The graph's colours are Fluent's data-visualisation colours (the user's choice, 2026-10-23: orange measurement,
Windows blue with the EQ, pink EQ, a grey dashed target), checked as the dataviz skill says (tests\\ui\\test_theme.py):
told apart by colour-blind eyes and at a glance, on the cards of both themes."""

BASE_LIGHT = {
    "bg": "#f3f3f3", "card": "#fbfbfb", "menu": "#f9f9f9", "ink": "#1b1b1b", "ink2": "#5d5d5d", "muted": "#676767",
    "disabled": "#9e9e9e", "line": "#e5e5e5", "stroke": "#e3e3e3", "stroke_bottom": "#cfcfcf", "strong": "#8a8a8a",
    "field": "#fefefe", "field_hover": "#f9f9f9", "field_press": "#f5f5f5", "field_focus": "#ffffff",
    "field_disabled": "#f5f5f5", "subtle": "#f0f0f0", "subtle_hover": "#eaeaea", "subtle_press": "#e6e6e6",
    "subtle_sel": "#ececec", "alt_row": "#f7f7f7", "check_fill": "#f9f9f9", "check_hover": "#f0f0f0",
    "thumb": "#ffffff", "track": "#e0e0e0", "scroll": "#a0a0a0", "scroll_hover": "#8a8a8a",
    "warn": "#9d5d00", "warn_bg": "#fff4ce", "err": "#c42b1c", "good": "#0f7b0f", "pill": "#dff6dd",
    "accent_disabled": "#c5c5c5", "on_accent_disabled": "#ffffff",
}
BASE_DARK = {
    "bg": "#202020", "card": "#2b2b2b", "menu": "#2c2c2c", "ink": "#ffffff", "ink2": "#cecece", "muted": "#a8a8a8",
    "disabled": "#787878", "line": "#1c1c1c", "stroke": "#3d3d3d", "stroke_bottom": "#353535", "strong": "#9a9a9a",
    "field": "#373737", "field_hover": "#3c3c3c", "field_press": "#313131", "field_focus": "#1f1f1f",
    "field_disabled": "#303030", "subtle": "#323232", "subtle_hover": "#383838", "subtle_press": "#303030",
    "subtle_sel": "#3a3a3a", "alt_row": "#2f2f2f", "check_fill": "#272727", "check_hover": "#303030",
    "thumb": "#454545", "track": "#4a4a4a", "scroll": "#8a8a8a", "scroll_hover": "#a0a0a0",
    "warn": "#fce100", "warn_bg": "#433519", "err": "#ff99a4", "good": "#6ccb5f", "pill": "#393d1b",
    "accent_disabled": "#434343", "on_accent_disabled": "#a7a7a7",
}
# Windows' default accent palette (blue): Light 3, Light 2, Light 1, the accent, Dark 1, Dark 2, Dark 3
DEFAULT_ACCENT = ("#99ebff", "#4cc2ff", "#0091f8", "#0078d4", "#005fb8", "#003e92", "#001a68")
# the graph: measurement, target, with the EQ, the EQ; c3, c5, c4 the extra curves in turn (search previews, Listen's
# EQs, Compare's B; c4 the marker), then c2 the EQ again; the grid
GRAPH_LIGHT = {"meas": "#ca5010", "tgt": "#5d5d5d", "with_eq": "#0078d4", "c2": "#e3008c", "c3": "#57811b",
               "c5": "#9373c0", "c4": "#13a10e", "grid": "#e5e5e5"}
GRAPH_DARK = {"meas": "#e46831", "tgt": "#cecece", "with_eq": "#2e91ef", "c2": "#f92f9e", "c3": "#6e9a38",
              "c5": "#a080ce", "c4": "#2caf26", "grid": "#3a3a3a"}


def _rgb(c):
    return [int(c[i:i + 2], 16) for i in (1, 3, 5)]


def mix(a, b, f):
    """Colour a mixed with b: f of a (0 to 1)."""
    return "#" + "".join(f"{round(x * f + y * (1 - f)):02x}" for x, y in zip(_rgb(a), _rgb(b)))


def contrast(a, b):
    """WCAG's contrast ratio of two colours (1 to 21)."""
    def lum(c):
        r, g, b_ = (v / 255 for v in _rgb(c))
        lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in (r, g, b_)]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def build(dark, accent=DEFAULT_ACCENT):
    """One theme's tokens: dark or light, with Windows' accent palette (seven shades, Light 3 to Dark 3)."""
    light3, light2, _light1, _base, dark1, dark2, _dark3 = accent
    t = dict(BASE_DARK if dark else BASE_LIGHT)
    t.update(GRAPH_DARK if dark else GRAPH_LIGHT)
    surface = t["card"]
    fill = light2 if dark else dark1  # (as Windows 11: the dark theme's main buttons are its Light 2)
    on = "#ffffff" if contrast("#ffffff", fill) >= contrast("#000000", fill) else "#000000"
    text = light3 if dark else dark2  # (the accent as text: a link, a "yours" tag)
    if contrast(text, surface) < 4.5:
        text = t["ink"]
    t.update(accent=fill, on_accent=on, accent_hover=mix(fill, surface, 0.9), accent_press=mix(fill, surface, 0.8),
             accent_bottom=mix(fill, "#000000", 0.85 if dark else 0.75), accent_text=text,
             accent_soft=mix(fill, surface, 0.16), accent_soft_line=mix(fill, surface, 0.45))
    # the older names the screens use, on the new colours
    t.update(c1=fill, btn=fill, on_btn=on, sel=t["subtle_sel"], on_sel=on, sel_ink=t["ink"], sel_accent=text,
             shade=t["subtle"])
    return t


LIGHT = build(False)
DARK = build(True)
