"""Make an EQ's Settings fold (ui\\eq_settings.py over ui\\forms.py): a value of your own used and marked "yours", a
wrong one red and not used, one past a limit moved to it, a value handed back to the automatic settings, a website's
profile setting its values, the automatic settings off; and the Search line (one search, said with its time).

Moved from eq_checks.py's ui_checks (lines 1491-1527) and search_checks (2303-2321). The first five are one chain, as
there: they share Best fit's filter counts box (made yours, then handed back) and Scoring's "to" box (left red, then
shown again), so they run in this order on one page (the eq_screen fixture). Offline throughout: the old checks went
online here (line 1490), which nothing in them needs."""
import json

import pytest


@pytest.fixture(scope="module")
def fold(eq_screen):
    """The Settings fold as the old checks had it at line 1493: your EQ app back to Equalizer APO (line 1491), and the
    fields the chain shares (filled in by its tests)."""
    eq_screen.page.choose_app("apo")
    return {"st": eq_screen.page.settings}


def test_value_of_your_own_and_a_wrong_one(eq_screen, fold, check):
    page, st = eq_screen.page, fold["st"]
    st.auto_switched(True)  # (the starting settings have them off, as the old part's copy had)
    page.refresh_auto()
    f = fold["f"] = st.form.fields["best_fit.filter_counts"]
    f.box.setText("4-8")
    f._typed()
    yours = (page.S["best_fit"]["filter_counts"], "best_fit.filter_counts" in page.S["auto"]["manual"], f.tag.text())
    f.box.setText("4-x")
    f._typed()
    wrong = (f.box.property("bad"), page.S["best_fit"]["filter_counts"])
    # was eq_checks.py:1503
    check("ui: settings: a value of your own is used and marked yours; a wrong one is red and not used",
          yours == ([4, 5, 6, 7, 8], True, "yours ↺") and wrong == (True, [4, 5, 6, 7, 8]), (yours, wrong))


def test_past_a_limit_and_to_below_from(eq_screen, fold, check):
    page, st, said = eq_screen.page, fold["st"], eq_screen.said
    b = st.form.fields["scoring.band_hz.0"]
    b.box.setText("5")
    b._typed()
    b._left()
    hi = fold["hi"] = st.form.fields["scoring.band_hz.1"]
    hi.box.setText("10")
    hi._typed()
    # was eq_checks.py:1512
    check("ui: settings: past a limit it moves to the limit on leaving (said); a “to” below its “from” is red",
          page.S["scoring"]["band_hz"][0] == 20 and any("Changed to 20" in s for s in said) and hi.box.property("bad"),
          (page.S["scoring"]["band_hz"], said[-1:]))


def test_handing_a_value_back(eq_screen, fold, check):
    page, st, f, hi = eq_screen.page, fold["st"], fold["f"], fold["hi"]
    hi.show_value(page.S["scoring"]["band_hz"][1])
    st.hand_back("best_fit.filter_counts")
    # was eq_checks.py:1517
    check("ui: settings: handing a value back gives it to the automatic settings again (auto tag)",
          "best_fit.filter_counts" not in page.S["auto"]["manual"] and f.tag.text() == "auto", page.S["auto"]["manual"])


def test_website_profile(eq_screen, fold, check):
    page, st = eq_screen.page, fold["st"]
    st.changed("site.profile", "squig.link lab")
    sq = dict(page.S["site"])
    st.changed("site.smooth_level", sq["smooth_level"] + 1)
    # was eq_checks.py:1522
    check("ui: settings: a website's profile sets its values (a change makes it custom)",
          sq["profile"] == "squig.link lab" and sq["smooth_level"] == page.meta["profiles"]["squig.link lab"]["smooth_level"]
          and page.S["site"]["profile"] == "custom", (sq, page.S["site"]["profile"]))


def test_automatic_settings_off(eq_screen, fold, check):
    st, f = fold["st"], fold["f"]
    st.auto_switched(False)
    # was eq_checks.py:1526
    check("ui: settings: with automatic settings off, no tags and nothing in Why these values",
          not f.tag.isVisible() and "off" in st.why.text().lower(), st.why.text())


def test_one_search(eq_screen, check):
    from eq import settings
    page = eq_screen.page
    kept = json.loads(json.dumps(page.S["auto"]))  # (the steps before turned the automatic settings off and set values)
    page.S["auto"].update(enabled=True, manual=[])
    page.refresh_auto()
    bf = page.S["best_fit"]
    what, est = page.sa_what.text(), page.estimate.text()
    old = settings.with_auto({"auto": {"level": 100}, "best_fit": {"fight_penalty": 0.004}})
    page.S["auto"] = kept
    page.refresh_auto()
    # was eq_checks.py:2316
    check("search: one search, every limit with both fighting-filter penalties, said with its time; no buttons; an "
          "older copy's level dropped and its one penalty made a list",
          bf["fight_penalty"] == [0.003, 0.01] and len(bf["q_max"]) >= 4 and "fighting-filter penalties" in what
          and est.startswith("A run takes") and not hasattr(page, "sa_btns")
          and "level" not in old["auto"] and old["best_fit"]["fight_penalty"] == [0.004],
          (bf["fight_penalty"], bf["q_max"], what, est, old["auto"], old["best_fit"]["fight_penalty"]))
