"""Where Make an EQ's settings are (the control audit of 2026-11-27): AutoEQ TrebleStartFrom only with the Website
methods, and "Custom values" naming only the settings whose boxes show. A page of its own, offline, opened with Best
fit."""
import pytest

from helpers import eqpage, qt


@pytest.fixture(scope="module")
def places(tmp_path_factory):
    s = eqpage.open_screen(str(tmp_path_factory.mktemp("settings_places")), settings={"mode": "best_fit"})
    yield s
    eqpage.close_screen(s)


def _mode(s, mode):
    s.page.set_mode(mode)
    qt.settle(0.5, 60)
    s.page.settings.refresh()


def _applies(st, path):
    return any(f.applies(path) for f in st.forms())


def test_treble_start_from_only_with_the_website_methods(places, check):
    page, st = places.page, places.page.settings
    seen = {}
    try:
        for mode in ("best_fit", "site_single", "site_sweep"):
            _mode(places, mode)
            seen[mode] = (_applies(st, "site.treble_start_from"), _applies(st, "site.profile"))
    finally:
        _mode(places, "best_fit")
    check("settings: AutoEQ TrebleStartFrom shows only with the two Website methods; Which website to copy shows with "
          "every method", seen == {"best_fit": (False, True), "site_single": (True, True), "site_sweep": (True, True)},
          seen)
    page.S["auto"]["enabled"] = True
    st.changed("site.treble_start_from", 9000)
    try:
        with_bf = (not st.mine_box.isHidden(), st.mine_text.text())
        _mode(places, "site_single")
        with_site = (not st.mine_box.isHidden(), st.mine_text.text())
    finally:
        st.make_auto("site.treble_start_from")
        _mode(places, "best_fit")
    # (Custom values named AutoEQ TrebleStartFrom with Best fit, with no box in sight to reset it)
    check("settings: Custom values names AutoEQ TrebleStartFrom only while its box shows (a Website method)",
          not with_bf[0] and with_site[0] and "AutoEQ TrebleStartFrom" in with_site[1], (with_bf, with_site))
