"""Make an EQ opening (ui\\eq_page.py): the app's files drawn (the curves, the automatic settings), and your EQ app
setting the method and what Save writes. Moved from eq_checks.py's ui_checks (the page opened as the old checks
opened it: helpers.eqpage.open_screen, on the settings they started from)."""

# was eq_checks.py:1642 (eqb-031, "ui: no control is ever shown as a window of its own (...)"): not a test of its own
# here. The stray watch (helpers.qt) watches every Qt test of the session, from before the page is made: the
# stray_check fixture fails the test in which a control was shown as a window of its own, naming it, and at the end
# of a session in which none ever was, the check is logged once as ok (tests\conftest.py).


def test_opens_with_the_apps_files(eq_screen, check):
    page = eq_screen.page
    loaded = page.curves is not None and page.auto is not None  # (open_screen waited up to 90 s for them)
    # was eq_checks.py:1372
    check("ui: the EQ screen opens with the app's files and draws them (the curves, the automatic settings)",
          loaded and page.target_combo.count() >= 1 and page.measurement_combo.count() >= 1
          and "→" in page.graph_title.text(), (loaded, page.graph_note.text()))


def test_eq_app_sets_method_and_files(eq_screen, check):
    page = eq_screen.page
    page.choose_app("poweramp")
    try:
        # was eq_checks.py:1376
        check("ui: your EQ app sets the method and Save writes exactly its file",
              page.S["eq_app"] == "poweramp" and page.S["mode"] == "best_fit"
              and [k for k in ("apo", "poweramp", "graphic") if page.S["export"][k]] == ["poweramp"]
              and "Poweramp" in page.formats_line.text(), page.S["export"])
    finally:
        page.choose_app("apo")  # (back as the old checks put it, line 1491)
