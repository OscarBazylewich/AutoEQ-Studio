"""Online / Offline (net.py): offline, the EQ part's one place that downloads (eq\\databases.py's _get) refuses before
it connects to anything, saying plainly that AutoEQ Studio is offline and how to go Online, and a download asked for
through eq.service is answered rather than attempted. Moved from eq_checks.py's studio_checks."""
import contextlib
import io

import net


def test_offline_nothing_fetched(check):
    # The switch is one for the whole process. The tests run offline from start to end (tests\helpers\fixtures_core.py's
    # offline fixture; a test that goes online does it only through the online fixture, and is put back), so this
    # test uses that state instead of turning the switch on and off itself as the old check did (lines 1294-1304).
    # What it proves: while the app is offline, the download function raises net.Offline before any connection is
    # opened, with a message that says the app is offline and that Online (top right) turns it back on; and the
    # service's download request comes back as an answer (an error the window shows), not a crash or a download. Had the
    # switch let it through, the only address tried would be 127.0.0.1:9, on this PC, refused at once.
    from eq import databases, service
    was_offline = net.offline()
    try:
        databases._get("https://127.0.0.1:9/never")
        said = ""
    except net.Offline as e:
        said = str(e)
    with contextlib.redirect_stderr(io.StringIO()):  # (an unknown entry: its error's details go to the log)
        r = service.call("/api/db/download", {"id": "x", "settings": {}})
    # was eq_checks.py:1305
    check("studio: offline, nothing is fetched from the internet (said plainly, before any connection)",
          was_offline and "offline" in said and "Online" in said and isinstance(r, dict), (was_offline, said, r))
