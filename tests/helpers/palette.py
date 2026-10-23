"""Chart colours checked, not eyeballed: the data-visualisation checks of Claude's dataviz skill
(scripts/validate_palette.js), ported line for line, for the graph's colours (ui\\theme_tokens.py's GRAPH).

check(colours, mode, surface, pairs="adjacent"|"all") -> (ok, report): each colour's OKLCH lightness inside the mode's
band and its chroma above the floor (below it a hue reads as grey); the pairs told apart under simulated protanopia
and deuteranopia (Machado, Oliveira and Fernandes 2009, severity 1.0: OKLab distance x 100, target 8, floor 6) and
under normal sight (floor 15); and each colour's contrast with the graph's background (3:1, else a WARN: the colour
then needs its name beside it, as the graph's legend gives). contrast(a, b): WCAG's ratio, for text colours (4.5:1).
"""
import math

BAND = {"light": (0.43, 0.77), "dark": (0.48, 0.67)}  # (OKLCH L)
CHROMA_FLOOR = 0.10
CVD_TARGET, CVD_FLOOR, NORMAL_FLOOR, CONTRAST_MIN = 8.0, 6.0, 15.0, 3.0
MACHADO = {
    "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def _srgb(h):
    h = h.strip().lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _lin(h):
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in _srgb(h)]


def luminance(h):
    r, g, b = _lin(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _oklab_lin(rgb):
    r, g, b = rgb
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def oklch(h):
    L, a, b = _oklab_lin(_lin(h))
    return L, math.hypot(a, b)


def _simulate(h, kind):
    r, g, b = _lin(h)
    return [max(0.0, min(1.0, m[0] * r + m[1] * g + m[2] * b)) for m in MACHADO[kind]]


def delta_e(a, b, kind=None):
    """OKLab distance x 100, under a simulated colour-blindness (kind) or normal sight (None)."""
    pa = _oklab_lin(_simulate(a, kind) if kind else _lin(a))
    pb = _oklab_lin(_simulate(b, kind) if kind else _lin(b))
    return 100 * math.dist(pa, pb)


def check(colours, mode, surface, pairs="adjacent"):
    """(ok, report): report is [(check, state, detail)], state PASS / WARN / FAIL as the skill's validator says."""
    lo, hi = BAND[mode]
    report, ok = [], True
    off = [(c, round(oklch(c)[0], 3)) for c in colours if not lo <= oklch(c)[0] <= hi]
    ok &= not off
    report.append(("lightness band", "FAIL" if off else "PASS", f"outside {lo}-{hi}: {off}" if off else ""))
    grey = [(c, round(oklch(c)[1], 3)) for c in colours if oklch(c)[1] < CHROMA_FLOOR]
    ok &= not grey
    report.append(("chroma floor", "FAIL" if grey else "PASS", f"reads grey: {grey}" if grey else ""))
    n = len(colours)
    pairlist = [(i, j) for i in range(n) for j in range(i + 1, n)] if pairs == "all" else \
        [(i, i + 1) for i in range(n - 1)]
    worst = min(((delta_e(colours[i], colours[j], k), k, colours[i], colours[j]) for k in ("protan", "deutan")
                 for i, j in pairlist), default=(99.0, "", "", ""))
    state = "PASS" if worst[0] >= CVD_TARGET else "WARN" if worst[0] >= CVD_FLOOR else "FAIL"
    ok &= state != "FAIL"
    report.append(("colour-blind separation", state, f"worst {worst[2]}-{worst[3]} {worst[0]:.1f} ({worst[1]})"))
    nworst = min(((delta_e(colours[i], colours[j]), colours[i], colours[j]) for i, j in pairlist),
                 default=(99.0, "", ""))
    ok &= nworst[0] >= NORMAL_FLOOR
    report.append(("normal-sight separation", "PASS" if nworst[0] >= NORMAL_FLOOR else "FAIL",
                   f"worst {nworst[1]}-{nworst[2]} {nworst[0]:.1f}"))
    low = [(c, round(contrast(c, surface), 2)) for c in colours if contrast(c, surface) < CONTRAST_MIN]
    report.append(("contrast with the background", "WARN" if low else "PASS",
                   f"below 3:1 (needs its name beside it): {low}" if low else ""))
    return ok, report
