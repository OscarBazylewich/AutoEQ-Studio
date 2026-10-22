"""The settings boxes (ui\\forms.py): lists and ranges read and shown back as AutoEQ Local read and showed them, and
the limits (a value's range, whole numbers, a pair's order, clamping) as AutoEQ Local's limits.js. Moved from
selftest.py's qt_checks."""
from ui import forms


def test_lists_read_and_shown_back(check):
    got = (forms.parse_list("4-7", True), forms.parse_list("6, 4 4", True), forms.parse_list("1-99", True),
           forms.parse_list("2.5, x", False), forms.parse_ranges("-12..6, -10 to 20"), forms.parse_ranges("6..-12"),
           forms.fmt_list([4, 5, 6, 7]), forms.fmt_list([2, 3.5]), forms._num(5e-05))
    # was selftest.py:304
    check("settings boxes: lists read as AutoEQ Local reads them (\"4-10\", \"4, 6, 8\", ranges), and shown back",
          forms.parse_list("4-7", True) == [4, 5, 6, 7] and forms.parse_list("6, 4 4", True) == [4, 6]
          and forms.parse_list("1-99", True) is None and forms.parse_list("2.5, x", False) is None
          and forms.parse_ranges("-12..6, -10 to 20") == [[-12, 6], [-10, 20]] and forms.parse_ranges("6..-12") is None
          and forms.fmt_list([4, 5, 6, 7]) == "4-7" and forms.fmt_list([2, 3.5]) == "2, 3.5" and forms._num(5e-05) == "0.00005",
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
