"""The tests' helpers (tests\\helpers, importable as `helpers`: pytest.ini puts tests\\ on the path).

Plain modules: session (the temporary folders and variables), paths (the project's own places), checks (check() and
the check log), guard (blocks writes outside the test folders, the internet, the registry), dialogs (message boxes
answered by themselves), qt (Qt off-screen), apo (a stand-in Equalizer APO folder), studio (the session's "your
files" and the EQ part's data), eq (the EQ part's helpers), eqpage (Make an EQ on the session), subproc (other
processes), capabilities (what this PC has). Three are pytest plugins (fixtures_core, fixtures_eq, fixtures_screen),
loaded by tests\\conftest.py.

None imports an app module at its top (only inside functions), so the session's variables are always set first.
session, guard, checks, dialogs, qt, apo, paths, subproc, capabilities and fixtures_core are loaded by every test: they
import no helpers.studio, helpers.eq or helpers.eqpage, and no app or tools module but net, ui.theme and ui.ocr
(tests\\infra\\test_isolation.py checks it), so app\\tools\\relevant_tests.py can tell which tests a change needs.
"""
