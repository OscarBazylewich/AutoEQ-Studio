"""The settings boxes (ui\\forms.py): lists read and shown back as AutoEQ Local read and showed them, and
the limits (a value's range, whole numbers, a pair's order, clamping) as AutoEQ Local's limits.js. Moved from
selftest.py's qt_checks. Then their look in Windows 11's (the checkers' findings, 2026-10-23), drawn themed in a Python
of their own: a fold's chevrons and its fill when pointed at, its chevron and content at a card's inset, and one label
column for a whole form. And a form made in two halves (Form.add_sections, 2026-10-24: Make an EQ makes Advanced so,
one half per step of its build) the same as one made at once. Last, a form with tabs (More settings, the review of
2026-11-10): the tab it starts on, each tab's height, the names a screen reader says, a pair's width and its tags.
Then Gain ranges as rows of two boxes (RangeRows, feature 4, the owner's decisions of 2026-11-24 and 2026-11-25): only
valid values go in, with no message; Add a range and ✕; the focus; the tag; the Tab sequence; the names."""
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from helpers import qt, session, subproc
from ui import forms

COVERS = ("ui.forms", "ui.theme_sheet")  # (reached through another Python: its code names them as text)


def test_lists_read_and_shown_back(check):
    got = (forms.parse_list("4-7", True), forms.parse_list("6, 4 4", True), forms.parse_list("1-99", True),
           forms.parse_list("2.5, x", False), forms.fmt_list([4, 5, 6, 7]), forms.fmt_list([2, 3.5]),
           forms.number_text(5e-05))
    # was selftest.py:304 (the ranges' text went, 2026-11-25: a list of ranges is rows of two boxes, RangeRows)
    check("settings boxes: lists read as AutoEQ Local reads them (\"4-10\", \"4, 6, 8\"), and shown back",
          forms.parse_list("4-7", True) == [4, 5, 6, 7] and forms.parse_list("6, 4 4", True) == [4, 6]
          and forms.parse_list("1-99", True) is None and forms.parse_list("2.5, x", False) is None
          and forms.fmt_list([4, 5, 6, 7]) == "4-7" and forms.fmt_list([2, 3.5]) == "2, 3.5"
          and forms.number_text(5e-05) == "0.00005",
          got)


def test_limits(check):
    L = forms.Limits({"a.0": {"min": 20, "max": 20000, "unit": "Hz"}, "a.1": {"min": 20, "max": 20000, "unit": "Hz"},
                      "n": {"min": 1, "max": 32, "int": True, "list": True}}, [("a.0", "a.1", True)])
    get = {"a.0": 100, "a.1": 1000}.get
    got = (L.check("a.0", 10, get), L.check("n", [1.5], get), L.check("a.0", 1000, get), L.check("a.1", 100, get),
           L.check("a.0", 500, get), L.clamp("n", [0, 40, 5]), L.clamp("a.0", 5))
    # was selftest.py:312
    check("settings boxes: limits as AutoEQ Local's limits.js (range, whole numbers, a pair's order, clamping)",
          L.check("a.0", 10, get)[0] == "range" and L.check("n", [1.5], get)[0] == "range"
          and L.check("a.0", 1000, get)[0] == "pair" and L.check("a.1", 100, get)[0] == "pair" and L.check("a.0", 500, get) is None
          and L.clamp("n", [0, 40, 5]) == [1, 5, 32] and L.clamp("a.0", 5) == 20, got)


# A fold (as Settings) holding a form in three sections (as Advanced: one row hidden until it applies, its label the
# longest), and a button marked as a fold (as the Target card's Adjust), themed, dark and light, read back from pictures
FOLD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QLabel, QToolButton, QVBoxLayout, QWidget
qapp = QApplication([])
from ui import theme, theme_sheet, theme_tokens
from ui.forms import Fold, Form, Limits
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT
''' + "{shapes}" + r'''


def pump():
    for _ in range(5):
        qapp.processEvents()


shown = {"wide": False}
out = {"card": theme_sheet.CARD}
for dark in (True, False):
    theme.apply(qapp, dark=dark, contrast=False)
    t = theme.tokens()
    holder = QWidget()
    lay = QVBoxLayout(holder)
    fold = Fold("Settings")
    form = Form([("Best fit", [("Filter counts to try", [("best_fit.filter_counts", "intlist")]),
                               ("Shelf", [("best_fit.low_shelf", "check")])]),
                 ("Website", [("Which website to copy", [("site.profile", "choice", [("a", "listener800")])]),
                              ("Around (Hz)", [("site.norm_hz", "num")])]),
                 ("Saved files", [("Extra headroom (dB)", [("export.extra_headroom", "num")]),
                                  ("Impulse response sample rate", [("export.convolution_rate", "num")],
                                   lambda: shown["wide"])])],
                Limits({}, []), lambda p: None, lambda p, v: None, lambda p: None, lambda s: None)
    fold.add(form)
    adjust = QToolButton()
    adjust.setText("Adjust")
    adjust.setCheckable(True)
    adjust.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    theme.mark(adjust, fold=True)
    lay.addWidget(fold)
    lay.addWidget(adjust, 0, Qt.AlignLeft)
    holder.resize(700, 400)
    shown["wide"] = False
    form.refresh()
    holder.show()
    pump()
    res = out["dark" if dark else "light"] = {}
    # the chevrons, closed and open (the fold's, and the Adjust button's arrow, set as eq_settings sets it)
    for name, btn, set_open in (("fold", fold.btn, fold.btn.setChecked),
                                ("adjust", adjust, lambda on: adjust.setArrowType(Qt.DownArrow if on else Qt.RightArrow))):
        for on in (False, True):
            set_open(on)
            pump()
            img = holder.grab().toImage()
            at = btn.mapTo(holder, QPoint(0, 0))
            bg = img.pixelColor(at.x() + btn.width() - 2, at.y() + 2)
            found = runs(img, at.x(), at.x() + btn.width(), at.y() + 2, at.y() + btn.height() - 2, bg)
            box = ink_box(img, found[0][0], at.y(), found[0][1] + 1, at.y() + btn.height(), bg) if found else None
            res[f"{name} {'open' if on else 'closed'}"] = open_side(img, box, bg, "down" if on else "right")
    # pointed at: Windows 11's fill
    fold.btn.setChecked(True)
    fold.btn.setAttribute(Qt.WA_UnderMouse, True)
    fold.btn.update()
    pump()
    img = holder.grab().toImage()
    at = fold.btn.mapTo(holder, QPoint(0, 0))
    res["pointed"] = [img.pixelColor(at.x() + 1, at.y() + fold.btn.height() // 2).name(), t["subtle_hover"]]
    fold.btn.setAttribute(Qt.WA_UnderMouse, False)
    fold.btn.update()
    pump()
    # where the chevron and the content start, from the fold's own left edge
    img = fold.grab().toImage()
    bg = img.pixelColor(fold.width() // 2, 3)
    at = fold.btn.mapTo(fold, QPoint(0, 0))
    found = runs(img, at.x(), at.x() + fold.btn.width(), at.y() + 2, at.y() + fold.btn.height() - 2, bg)
    labels = {}
    for lab in form.findChildren(QLabel):
        if lab.isVisible() and lab.text():
            p = lab.mapTo(fold, QPoint(0, 0))
            box = ink_box(img, p.x(), p.y(), p.x() + lab.width(), p.y() + lab.height(), bg)
            labels[lab.text()] = box and box[0]
    boxes = {path: f.box.mapTo(fold, QPoint(0, 0)).x() for path, f in form.fields.items() if f.isVisible()}
    shown["wide"] = True  # (the hidden row shows: nothing else moves)
    form.refresh()
    pump()
    res.update(chevron_x=found and found[0][0], labels=labels, boxes=boxes,
               boxes_after=[f.box.mapTo(fold, QPoint(0, 0)).x() for f in form.fields.values() if f.isVisible()])
    holder.close()
    holder.deleteLater()
    pump()
print(json.dumps(out))
'''


def test_folds_as_windows_11(check, shapes):
    out = subproc.run_python(FOLD.replace("{shapes}", shapes), session.SESSION.app)
    d = out.data or {}
    seen = [d.get(m) or {} for m in ("dark", "light")]
    # (2026-10-23: Qt's small filled triangles, and no fill when pointed at)
    check("folds: Windows 11's chevrons (pointing right when closed, down when open), the fold's and the Target "
          "card's Adjust's, and a fill when pointed at, as Windows 11's expanders; light and dark",
          len(seen) == 2 and all(all(m.get(f"{n} {s}") is True for n in ("fold", "adjust") for s in ("closed", "open"))
                                 and m.get("pointed", [0, 1])[0] == m.get("pointed", [0, 1])[1] for m in seen),
          d or out.stderr[-300:])
    inset = d.get("card", 0) + 1  # (inside its 1 px border)
    # (the card's padding, the fold's margins and its button's put the arrow 10 px in and the content 8 px further)
    check("folds: a fold's chevron and its content start at a card's inset (theme_sheet's CARD), as a card's title and "
          "content do; light and dark",
          len(seen) == 2 and all(0 <= (m.get("chevron_x") or -9) - inset <= 4
                                 and all(abs(x - inset) <= 2 for x in (m.get("labels") or {"": -9}).values())
                                 for m in seen), d or out.stderr[-300:])
    # (the section headings sat 3 px right of the labels under them: Qt's own indent for a label with padding. The UI
    # audit, 2026-11-08: each label directly above its box, the boxes in columns that start at the same places, so a
    # row that shows moves no box before it)
    check("settings boxes: each label is directly above its box, a section's first box starts where the form's first "
          "does, a row that shows moves no other box, the section headings in line with the labels under them",
          len(seen) == 2 and all(abs(m["labels"]["Filter counts to try"] - m["boxes"]["best_fit.filter_counts"]) <= 2
                                 and abs(m["labels"]["Which website to copy"] - m["boxes"]["site.profile"]) <= 2
                                 and m["boxes"]["best_fit.filter_counts"] == m["boxes"]["site.profile"]
                                 == m["boxes"]["export.extra_headroom"]
                                 and set(m["boxes"].values()) <= set(m.get("boxes_after") or [])
                                 and all(abs(m["labels"][h] - m["labels"][first]) <= 1
                                         for h, first in (("Best fit", "Filter counts to try"),
                                                          ("Website", "Which website to copy"),
                                                          ("Saved files", "Extra headroom (dB)")))
                                 for m in seen), d or out.stderr[-300:])


def test_a_form_made_in_two_halves(qapp, check):
    from PySide6.QtWidgets import QLabel, QWidget
    shown = {"rate": False}
    sections = [("Best fit", [("Filter counts to try", [("best_fit.filter_counts", "intlist")]),
                              ("Q from", [("best_fit.q_min", "num")])]),
                ("Website", [("Which website to copy", [("site.profile", "choice", [("a", "listener800")])]),
                             ("Frequency from", [("site.freq_low", "num"), ("site.freq_high", "num")])]),
                ("Saved files", [("", [("export.apo", "check")]),
                                 ("Impulse response sample rate", [("export.convolution_rate", "num")],
                                  lambda: shown["rate"])]),
                ("History", [("History keeps", [("history.keep", "choice", [("saved", "Saved")])],
                              lambda: shown["rate"])])]
    told = []

    def make(parts):
        form = forms.Form(parts[0], forms.Limits({}, []), lambda p: None, lambda p, v: told.append((p, v)),
                          lambda p: told.append(("back", p)), lambda s: None)
        for more in parts[1:]:
            form.add_sections(more)
        form.refresh()
        return form

    def seen(form):
        labels = [lab.text() for lab in form.findChildren(QLabel)]
        return {"fields": list(form.fields), "names": [f.box.accessibleName() for f in form.fields.values()],
                "labels": labels, "rows": len(form.rows), "widgets": len(form.findChildren(QWidget)),
                "shown": [w.isVisibleTo(form) for widgets, _show in form.rows for w in widgets]}
    whole, halves = make([sections]), make([sections[:2], sections[2:]])
    try:
        a, b = seen(whole), seen(halves)
        halves.fields["export.apo"].box.setChecked(True)  # (a box of the second half, ticked: said to the form's owner)
        check("settings boxes: a form made in two halves (add_sections) is the one made at once: the same boxes, names "
              "for a screen reader, labels, rows shown and hidden, and its boxes' changes said to the form's owner",
              a == b and b["rows"] == 8 and told == [("export.apo", True)], (a, b, told))
    finally:
        from helpers import qt
        qt.close(whole)
        qt.close(halves)


def _tab_form(sections, shown=None):
    """A form with tabs (as More settings) in a closed fold, in a window of its own (a dialog: never a stray)."""
    from PySide6.QtWidgets import QDialog, QVBoxLayout
    dlg = QDialog()
    lay = QVBoxLayout(dlg)
    fold = forms.Fold("More settings", sub=True)
    form = forms.Form(sections, forms.Limits({}, []), lambda p: None, lambda p, v: None, lambda p: None,
                      lambda s: None, tabs=True)
    fold.add(form)
    lay.addWidget(fold)
    lay.addStretch(1)  # (as the page: the room under the cards is a stretch)
    return dlg, fold, form


def test_tabs_start_on_a_tab_that_applies(qapp, check):
    from helpers import qt
    method = {"best_fit": False}
    dlg, fold, form = _tab_form([("Best fit", [("Q from", [("best_fit.q_min", "num")], lambda: method["best_fit"])]),
                                 ("Website", [("Around (Hz)", [("site.norm_hz", "num")])])])
    try:
        form.refresh()  # (as the page's build does: the fold closed, nothing shown yet)
        closed = (form.pages.currentIndex(), [b.text() for b in form.tab_btns.values() if b.isChecked()])
        dlg.show()
        fold.btn.setChecked(True)
        qt.pump(50)
        opened = (form.pages.currentIndex(), [b.text() for b in form.tab_btns.values() if b.isChecked()],
                  form.pages.currentWidget().isVisible())
        # (2026-11-10: with a saved method other than Best fit, More settings opened on Best fit's empty page, no tab
        # selected: the form changed tab only while it showed, and it is closed at the start)
        check("settings boxes: a form with tabs, refreshed while its fold is closed, goes to the first tab that applies: "
              "opened, that tab is selected and its page shows",
              closed == (1, ["Website"]) and opened == (1, ["Website"], True), (closed, opened))
    finally:
        qt.close(dlg)


def test_a_tab_as_high_as_its_own_page(qapp, check):
    from helpers import qt
    tall = [(f"Value {i}", [(f"best_fit.v{i}", "num")]) for i in range(12)]
    dlg, fold, form = _tab_form([("Best fit", tall), ("This PC", [("CPU cores", [("performance.cores", "num")])])])
    try:
        form.refresh()
        fold.btn.setChecked(True)
        dlg.resize(600, 400)
        dlg.show()
        qt.pump(50)
        tall_h = form.pages.height()
        form.show_tab(1)
        qt.pump(50)
        page = form.pages.currentWidget()
        own = page.layout().totalHeightForWidth(form.pages.width())
        short_h = form.pages.height()
        form.show_tab(0)
        qt.pump(50)
        back = form.pages.height()
        # (2026-11-10: Qt's stack is as high as its highest page, so History and This PC had up to 330 px of empty room
        # above Calculate)
        check("settings boxes: each tab's page is as high as its own settings (a short tab is not as high as the "
              "highest), and the tall tab is as high as before when it shows again",
              abs(short_h - own) <= 2 and short_h < tall_h / 3 and back == tall_h, (tall_h, short_h, own, back))
    finally:
        qt.close(dlg)


def test_tick_boxes_named_by_their_words(qapp, check):
    from PySide6.QtGui import QAccessible
    from helpers import qt
    form = forms.Form([("Saved files", [("", [("export.apo", "check")]),
                                        ("Shelf", [("best_fit.low_shelf", "check")]),
                                        ("Around (Hz)", [("site.norm_hz", "num")])])],
                      forms.Limits({}, []), lambda p: None, lambda p, v: None, lambda p: None, lambda s: None)
    try:
        form.fields["export.apo"].box.setText("Equalizer APO / squiglink filters (.txt)")
        form.fields["best_fit.low_shelf"].box.setText("Low shelf (a wide bass change)")

        def said(path):
            iface = QAccessible.queryAccessibleInterface(form.fields[path].box)
            return iface.text(QAccessible.Name) if iface is not None else ""
        names = {p: said(p) for p in form.fields}
        # (2026-11-10: a tick box without a label was named by its setting's path, "export.apo")
        check("settings boxes: a screen reader says a tick box's own words (never the setting's path), and a box's "
              "label",
              names == {"export.apo": "Equalizer APO / squiglink filters (.txt)",
                        "best_fit.low_shelf": "Low shelf (a wide bass change)", "site.norm_hz": "Around (Hz)"}, names)
    finally:
        qt.close(form)


def test_pairs_and_long_words(qapp, check):
    from PySide6.QtCore import QPoint
    from helpers import qt
    long_words = "Convolution impulse response: Viper4Android, JamesDSP, EasyEffects, Roon, foobar2000 (.wav)"
    dlg, fold, form = _tab_form([("Best fit", [("Filters from (Hz)", [("a.0", "num"), ("a.1", "num")]),
                                               ("Layout", [("best_fit.layout", "choice", [("x", "Parametric")])]),
                                               ("", [("export.convolution", "check")])])])
    try:
        form.fields["export.convolution"].box.setText(long_words)
        form.refresh({"a.0": "yours", "a.1": "auto", "best_fit.layout": "auto"})  # (both of the pair's tags shown)
        fold.btn.setChecked(True)
        dlg.resize(1100, 400)
        dlg.show()
        qt.pump(50)
        x = lambda w, right=False: w.mapTo(form, QPoint(w.width() if right else 0, 0)).x()
        a, b = form.fields["a.0"], form.fields["a.1"]
        long_box = form.fields["best_fit.layout"].box
        pair = x(b.box, True) - x(a.box)
        tags = sorted((x(t), x(t, True)) for t in (a.tag, b.tag))
        boxes = [(x(f.box), x(f.box, True)) for f in (a, b)]
        on_box = [t for t in tags for bx in boxes if t[0] < bx[1] and bx[0] < t[1]]
        conv = form.fields["export.convolution"].box
        # (UI-RULES 26: a pair as wide as a LONG box, so the tags are in one column; it was 11 px narrower, and a
        # "from" box's tag sat between its box and "to", 2026-11-10)
        check("settings boxes: a \"from … to\" pair is exactly as wide as one long box, its tags after it in the tags' "
              "column (never on a box), and a tick box's long words are not cut when the form is wide enough",
              pair == forms.LONG == x(long_box, True) - x(long_box) and not on_box
              and tags[0][0] >= boxes[1][1] and tags[0][0] - boxes[1][1] == x(form.fields["best_fit.layout"].tag) - x(long_box, True)
              and conv.width() >= conv.sizeHint().width(),
              (pair, forms.LONG, tags, boxes, conv.width(), conv.sizeHint().width()))
    finally:
        qt.close(dlg)


def test_a_box_is_described_by_its_tooltip(qapp, check):
    # (the owner's rule of 2026-11-24: a screen reader reads a control's tooltip after its name. A box of the settings
    # had its line of Help as the description, without the limits of its tooltip, a review of the text survey found.
    # The box sets no description, and Qt gives the tooltip: helpers.qt.description)
    from helpers import qt
    form = forms.Form([("Saved files", [("", [("export.apo", "check")]),
                                        ("Shelf", [("best_fit.low_shelf", "check")]),
                                        ("Around (Hz)", [("site.norm_hz", "num")]),
                                        ("Fit from (Hz)", [("scoring.band_hz.0", "num"), ("scoring.band_hz.1", "num")]),
                                        ("Layout", [("best_fit.layout", "choice", [("x", "Parametric")])])])],
                      forms.Limits({"site.norm_hz": {"min": 20, "max": 20000, "unit": "Hz"}}, []), lambda p: None,
                      lambda p, v: None, lambda p: None, lambda s: None)
    try:
        lines = {p: forms.help_of(p) for p in form.fields}
        got = {p: qt.description(f.box) for p, f in form.fields.items()}
        tips = {p: f.box.toolTip() for p, f in form.fields.items()}
        check("settings boxes: a screen reader reads the tooltip of a box, with its limits, after its name; nothing for "
              "a box with no tooltip",
              got == tips and lines["site.norm_hz"] and lines["scoring.band_hz.1"] and lines["export.apo"] == ""
              and tips["export.apo"] == "" and lines["best_fit.layout"] == ""
              and tips["site.norm_hz"].startswith(lines["site.norm_hz"] + "\nAllowed: "), (got, tips))
    finally:
        qt.close(form)


# ---------------------------------------------------------------- Gain ranges: rows of two boxes (RangeRows)
GAIN = "site_sweep.gain_ranges"
THREE = [[-12, 6], [-12, 9], [-16, 16]]  # (eq.settings' default)


class _Ranges:
    """Gain ranges between two other settings (a list box and a number box), in a form with eq.settings' limits, in
    a dialog of its own, shown and active. Like the page: a value set is stored and the form refreshed with its tag
    "custom ↺"; a click on the tag stores the automatic value again, the tag "automatic"."""

    def __init__(self, value, auto=None):
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        from eq import settings
        self.auto = {GAIN: [[-12, 6]], "best_fit.filter_counts": [1, 2, 3], **(auto or {})}
        self.S = {GAIN: value, "best_fit.filter_counts": [4, 5, 6], "site_sweep.q_min": 0.5}
        self.told, self.tags = [], {GAIN: "auto", "best_fit.filter_counts": "auto"}
        self.dlg = QDialog()
        lay = QVBoxLayout(self.dlg)
        self.form = forms.Form([("Website best settings", [
            ("Filter counts to try", [("best_fit.filter_counts", "intlist")]),
            ("Gain ranges", [(GAIN, "ranges")]),
            ("Q from", [("site_sweep.q_min", "num")])])],
            forms.Limits(settings.LIMITS, settings.LIMIT_PAIRS), self.S.get, self.changed, self.make_auto,
            lambda s: None)
        lay.addWidget(self.form)
        self.form.refresh(self.tags)
        self.f = self.form.fields[GAIN]
        self.rows = self.f.box
        self.dlg.resize(600, 400)
        self.dlg.show()
        self.dlg.activateWindow()
        qt.pump(100)

    def changed(self, path, value):
        if self.S.get(path) == value:  # (as the page: the same value is no change)
            return
        self.told.append(value)
        self.S[path] = value
        self.tags[path] = "yours"
        self.form.refresh(self.tags)

    def make_auto(self, path):
        self.S[path] = self.auto[path]
        self.tags[path] = "auto"
        self.form.refresh(self.tags)

    def shown(self):
        return [[r.lo.text(), r.hi.text()] for r in self.rows.rows if r.widget.isVisible()]

    def typed(self, box, keys, select=True):
        """The caret in box (all its text selected), then keys typed as real keys."""
        box.setFocus(Qt.TabFocusReason)
        if select:
            box.selectAll()
        QTest.keyClicks(box, keys)
        qt.pump(20)

    def leave(self):
        """The caret to the next setting's box (Q from)."""
        self.form.fields["site_sweep.q_min"].box.setFocus(Qt.TabFocusReason)
        qt.pump(20)


@pytest.fixture
def ranges(qapp):
    made = []

    def make(value, auto=None):
        made.append(_Ranges(value, auto))
        return made[-1]
    yield make
    for r in made:
        qt.close(r.dlg)


def test_ranges_rows_shown(ranges, check):
    three, one = ranges([list(x) for x in THREE]), ranges([[-12, 6]])
    seen = {}
    for name, r in (("three", three), ("one", one)):
        seen[name] = (r.shown(), [x.x.isVisible() for x in r.rows.rows if x.widget.isVisible()],
                      [x.widget.width() for x in r.rows.rows if x.widget.isVisible()], r.f.box.width(), r.rows.text(),
                      r.rows.add_btn.isVisible(), r.rows.add_btn.text())
    check("gain ranges: a row of two boxes for each range, with its ✕; one range left: its ✕ hidden and the row still "
          "as wide as a long box; Add a range under the rows; the rows' words “-12 to 6, -12 to 9”",
          seen["three"][:5] == ([["-12", "6"], ["-12", "9"], ["-16", "16"]], [True] * 3, [forms.LONG] * 3, forms.LONG,
                                "-12 to 6, -12 to 9, -16 to 16")
          and seen["one"][:5] == ([["-12", "6"]], [False], [forms.LONG], forms.LONG, "-12 to 6")
          and all(s[5:] == (True, "Add a range") for s in seen.values()), seen)


def test_ranges_typed_and_refused(ranges, check):
    r = ranges([list(x) for x in THREE])
    second = r.rows.rows[1]
    r.typed(second.hi, "10")
    used = (r.told[-1:], r.S[GAIN], r.f.tag.text())
    refused = {}
    for keys in ("5", "a", ".", " "):  # (-125 is past -20; a letter; a fraction; a space)
        second.lo.setFocus(Qt.TabFocusReason)
        second.lo.end(False)
        QTest.keyClicks(second.lo, keys)
        refused[keys] = second.lo.text()
    r.typed(second.hi, "25")  # (the 5 refused: 2 stays)
    refused["25"] = second.hi.text()
    check("gain ranges: a number typed in a box is used at once, the other ranges as they were, and the tag says "
          "“custom ↺”",
          used == ([[[-12, 6], [-12, 10], [-16, 16]]], [[-12, 6], [-12, 10], [-16, 16]], "custom ↺"), used)
    check("gain ranges: a key that would make a number past a limit (-20 to 20), a letter, a point or a space is "
          "refused: the box keeps its text",
          refused == {"5": "-12", "a": "-12", ".": "-12", " ": "-12", "25": "2"}, refused)


def test_ranges_put_right_on_leaving(ranges, check):
    r = ranges([list(x) for x in THREE])
    first = r.rows.rows[0]
    r.typed(first.lo, "9")  # (9 to 6: the wrong order)
    typing = (len(r.told), r.rows.ranges(), r.S[GAIN][0])
    r.leave()
    ordered = (r.shown()[0], r.S[GAIN][0], r.f.tag.text())
    r.typed(first.hi, "7")
    first.hi.setFocus(Qt.TabFocusReason)
    first.hi.selectAll()
    QTest.keyClick(first.hi, Qt.Key_Backspace)  # (emptied)
    emptied_while = (first.hi.text(), r.S[GAIN][0])
    r.leave()
    emptied = r.shown()[0]
    r.typed(first.lo, "-")  # (a lone "-")
    lone_while = first.lo.text()
    r.leave()
    lone = r.shown()[0]
    check("gain ranges: a row whose order is wrong is not used while you type (the list in use stays); leaving the "
          "box puts it right, with no message: the box you left takes the other box's value",
          typing == (0, None, [-12, 6]) and ordered == (["6", "6"], [6, 6], "custom ↺"), (typing, ordered))
    check("gain ranges: an emptied box, or a lone “-”, gets back the number that its row had when the caret leaves it",
          emptied_while == ("", [6, 7]) and emptied == ["6", "7"] and lone_while == "-" and lone == ["6", "7"],
          (emptied_while, emptied, lone_while, lone))


def test_ranges_add(ranges, check):
    r = ranges([list(x) for x in THREE])
    r.rows.add_btn.click()
    qt.pump(20)
    f = QApplication.focusWidget()
    added = (r.shown(), r.S[GAIN], r.f.tag.text(), f is r.rows.rows[3].lo, f.selectedText() if f else None)
    five = ranges([[-12, 6], [-12, 9], [-12, 12], [-16, 16], [-20, 20]])
    five.rows.add_btn.click()
    qt.pump(20)
    mid = ranges([list(x) for x in THREE])
    mid.typed(mid.rows.rows[1].lo, "10")  # (10 to 9, not left yet: put right before the row is added)
    QTest.mouseClick(mid.rows.add_btn, Qt.LeftButton)
    qt.pump(20)
    check("gain ranges: Add a range adds a row with the first usual range that the list does not have (-12 to 12), "
          "used at once (“custom ↺”), the caret in its first box with its text selected",
          added == ([["-12", "6"], ["-12", "9"], ["-16", "16"], ["-12", "12"]], [[-12, 6], [-12, 9], [-16, 16], [-12, 12]],
                    "custom ↺", True, "-12"), added)
    check("gain ranges: with the five usual ranges, Add a range copies the last row; a row being typed in is put "
          "right first",
          five.S[GAIN][-1] == [-20, 20] and len(five.S[GAIN]) == 6
          and mid.S[GAIN] == [[-12, 6], [9, 9], [-16, 16], [-12, 9]], (five.S[GAIN], mid.S[GAIN]))


def test_ranges_remove(ranges, check):
    r = ranges([[-12, 6], [-12, 9], [-16, 16], [-20, 20]])
    QTest.mouseClick(r.rows.rows[1].x, Qt.LeftButton)  # (the second row)
    qt.pump(20)
    middle = r.S[GAIN]
    QTest.mouseClick(r.rows.rows[2].x, Qt.LeftButton)  # (the last row)
    qt.pump(20)
    last = r.S[GAIN]
    QTest.mouseClick(r.rows.rows[0].x, Qt.LeftButton)
    qt.pump(20)
    one = (r.S[GAIN], r.shown(), r.rows.rows[0].x.isVisible(), r.rows.rows[0].widget.width(), r.f.tag.text())
    check("gain ranges: ✕ removes its row (the middle one, the last one), the rows under it move up, used at once; "
          "with one row left its ✕ is hidden and the row keeps its width",
          middle == [[-12, 6], [-16, 16], [-20, 20]] and last == [[-12, 6], [-16, 16]]
          and one == ([[-16, 16]], [["-16", "16"]], False, forms.LONG, "custom ↺"), (middle, last, one))


def test_ranges_remove_and_the_focus(ranges, check):
    r = ranges([list(x) for x in THREE])
    rows = r.rows.rows
    r.typed(rows[0].lo, "-1")  # (the caret in the first row, typing)
    QTest.mouseClick(rows[2].x, Qt.LeftButton)  # (the mouse: the ✕ takes no focus)
    qt.pump(20)
    mouse = (QApplication.focusWidget() is rows[0].lo, rows[0].lo.text(), r.S[GAIN])
    keys = ranges([list(x) for x in THREE])
    rows = keys.rows.rows
    rows[2].x.setFocus(Qt.TabFocusReason)
    QTest.keyClick(rows[2].x, Qt.Key_Space)  # (the keyboard on the last row's ✕: it goes)
    qt.pump(20)
    k1 = QApplication.focusWidget() is rows[1].x
    QTest.keyClick(rows[1].x, Qt.Key_Space)  # (one row left: its ✕ goes too)
    qt.pump(20)
    k2 = QApplication.focusWidget() is rows[0].hi
    check("gain ranges: after a mouse click on ✕ the caret stays in the box where it was, with its text",
          mouse == (True, "-1", [[-1, 6], [-12, 9]]), mouse)
    check("gain ranges: ✕ pressed with the keyboard on the last row gives the focus to the ✕ of the row above; with "
          "one row left, to its second box (an adjacent control, UI-RULES 30)", k1 and k2 and keys.S[GAIN] == [[-12, 6]],
          (k1, k2, keys.S[GAIN]))


def test_ranges_refresh_keeps_what_you_type(ranges, check):
    r = ranges([list(x) for x in THREE])
    r.typed(r.rows.rows[1].lo, "-")
    r.S[GAIN] = [[-12, 6]]  # (the automatic settings changed meanwhile)
    r.form.refresh(r.tags)
    typing = r.shown()
    r.rows.rows[1].lo.setText("-12")
    r.leave()
    r.S[GAIN] = [[-12, 6]]
    r.form.refresh(r.tags)
    after = r.shown()
    check("gain ranges: a refresh does not write over the rows while you type in one; with the caret out of them, a "
          "refresh shows the list in use (its number of rows)",
          typing == [["-12", "6"], ["-", "9"], ["-16", "16"]] and after == [["-12", "6"]], (typing, after))


def test_custom_tag_clicked_with_the_caret_in_the_box(ranges, check):
    r = ranges([list(x) for x in THREE])
    r.typed(r.rows.rows[1].hi, "8")
    before = (r.f.tag.text(), r.S[GAIN])
    QTest.mouseClick(r.f.tag, Qt.LeftButton)
    qt.pump(20)
    rows = (r.S[GAIN], r.shown(), r.f.tag.text(), r.rows.editing())
    one = r.form.fields["best_fit.filter_counts"]
    r.typed(one.box, "4-9")
    QTest.mouseClick(one.tag, Qt.LeftButton)
    qt.pump(20)
    box = (r.S["best_fit.filter_counts"], one.box.text(), one.tag.text(), one.box.hasFocus())
    # (the critique of feature 4, 2026-11-24: the tag takes no focus on a click, and the box kept your value under
    # "automatic", so your next key made it yours again)
    check("gain ranges: a mouse click on “custom ↺” with the caret in a box shows the automatic rows (their number "
          "too)", before[0] == "custom ↺" and rows == ([[-12, 6]], [["-12", "6"]], "automatic", True), (before, rows))
    check("settings boxes: a mouse click on “custom ↺” with the caret in a list's box shows the automatic value in "
          "the box", box == ([1, 2, 3], "1-3", "automatic", True), box)


def test_custom_tag_clicked_in_a_number_box(qapp, check):
    from PySide6.QtWidgets import QDialog, QVBoxLayout
    S, tags = {"site.norm_hz": 1000}, {"site.norm_hz": "yours"}
    dlg = QDialog()
    lay = QVBoxLayout(dlg)
    form = None

    def make_auto(p):
        S[p] = 500
        tags[p] = "auto"
        form.refresh(tags)
    form = forms.Form([("Website", [("Around (Hz)", [("site.norm_hz", "num")])])], forms.Limits({}, []), S.get,
                      lambda p, v: S.__setitem__(p, v), make_auto, lambda s: None)
    lay.addWidget(form)
    try:
        form.refresh(tags)
        dlg.show()
        dlg.activateWindow()
        qt.pump(50)
        f = form.fields["site.norm_hz"]
        f.box.setFocus(Qt.TabFocusReason)
        f.box.selectAll()
        QTest.keyClicks(f.box, "123")
        QTest.mouseClick(f.tag, Qt.LeftButton)
        qt.pump(20)
        got = (S["site.norm_hz"], f.box.text(), f.tag.text(), f.box.hasFocus())
        check("settings boxes: a mouse click on “custom ↺” with the caret in a number box shows the automatic value",
              got == (500, "500", "automatic", True), got)
    finally:
        qt.close(dlg)


def test_ranges_tag_in_the_tags_column(ranges, check):
    r = ranges([list(x) for x in THREE])
    x = lambda w, right=False: w.mapTo(r.form, QPoint(w.width() if right else 0, 0)).x()
    mid = lambda w: w.mapTo(r.form, QPoint(0, w.height() // 2)).y()
    one = r.form.fields["best_fit.filter_counts"]
    got = (x(r.f.tag) - x(r.f.box, True), x(one.tag) - x(one.box, True), x(r.f.tag), x(one.tag),
           mid(r.f.tag) - mid(r.rows.rows[0].lo), r.f.tag.isVisible())
    check("gain ranges: the tag is in the tags' column (as far after the rows as a list box's tag after its box) and "
          "at the height of the first row", got[0] == got[1] and got[2] == got[3] and abs(got[4]) <= 1 and got[5], got)


def test_ranges_tab_row_by_row(ranges, check):
    r = ranges([list(x) for x in THREE])
    r.typed(r.rows.rows[0].lo, "-11")  # ("custom ↺": the tag takes Tab)
    r.rows.add_btn.click()  # (a fourth row, made now: after the third in the sequence)
    qt.pump(20)
    rows = r.rows.rows
    want = [w for row in rows for w in (row.lo, row.hi, row.x)] + [r.rows.add_btn, r.f.tag,
                                                                     r.form.fields["site_sweep.q_min"].box]
    names = {id(w): n for n, w in enumerate(want)}
    seq = []
    rows[0].lo.setFocus(Qt.TabFocusReason)
    for _ in range(len(want) - 1):
        QTest.keyClick(QApplication.focusWidget(), Qt.Key_Tab)
        seq.append(names.get(id(QApplication.focusWidget()), "other"))
    check("gain ranges: Tab goes row by row (first box, second box, ✕), then Add a range, the tag and the next "
          "setting; a row added later is in its place", seq == list(range(1, len(want))), seq)


def test_ranges_names_for_a_screen_reader(ranges, check):
    r = ranges([list(x) for x in THREE])
    rows = r.rows.rows
    names = [(x.lo.accessibleName(), x.hi.accessibleName(), x.x.accessibleName(), x.x.toolTip()) for x in rows[:2]]
    tips = {w.toolTip() for x in rows for w in (x.lo, x.hi)}
    keys = {w.property("help_key") for x in rows for w in (x.lo, x.hi, x.x)} | {r.rows.add_btn.property("help_key")}
    check("gain ranges: a screen reader's names (“Gain ranges, range 1, from (dB)”, “Remove gain range 1”), ✕'s "
          "tooltip, Add a range's, the boxes' tooltip (Help's line and the limits, no F1), and each control's Help entry",
          names == [("Gain ranges, range 1, from (dB)", "Gain ranges, range 1, to (dB)", "Remove gain range 1",
                     "Remove this range"),
                    ("Gain ranges, range 2, from (dB)", "Gain ranges, range 2, to (dB)", "Remove gain range 2",
                     "Remove this range")]
          and r.rows.add_btn.toolTip() == "Add another gain range to try" and tips == {r.f.base_tip}
          and r.f.base_tip.endswith("\nAllowed: each value -20 to 20 dB") and "F1" not in r.f.base_tip
          and ".." not in r.f.base_tip and keys == {GAIN}, (names, tips, keys))
