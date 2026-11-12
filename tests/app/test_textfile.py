"""Reading and writing the app's files (textfile.py): text in the encodings Windows programs write, decimal commas and
semicolons in curves, file names Windows accepts (its reserved device names too), a write that fails leaving no
temporary file behind, a damaged file set aside a second time kept beside the first, and "inside a folder" never
meaning a folder beside it. Moved from eq_checks.py's module_checks; each works in its own temporary folder."""
import os

import textfile


def test_utf16_and_cp1252_decoded(check):
    # was eq_checks.py:143
    check("files: UTF-16 and cp1252 text decoded", textfile.decode("20 1\n".encode("utf-16")) == "20 1\n"
          and textfile.decode(b"20\xb05") == "20°5")


def test_decimal_commas_and_semicolons(check):
    # was eq_checks.py:145
    check("files: decimal commas and semicolons read", textfile.normalize_fr("20,5;85,3\n30,1;86\n") == "20.5\t85.3\n30.1\t86\n")


def test_windows_safe_names(check):
    # was eq_checks.py:146
    check("files: Windows-safe names", [textfile.safe_name(n) for n in ("CON", "a:b*c?.txt", "....")] == ["_CON", "a_b_c_.txt", "file"])


def test_failed_write_leaves_no_temporary_file(tmp_path, check):
    # (a folder where the file should go: the write's last step, the rename, is refused; textfile tries it again for
    # about a second before giving up. The old check did this in the test copy's data folder)
    data = os.path.join(tmp_path, "data")
    folder_as_file = os.path.join(data, "a folder")
    os.makedirs(folder_as_file, exist_ok=True)
    try:
        textfile.write_atomic(folder_as_file, "x")
    except OSError:
        pass
    left = [n for n in os.listdir(data) if n.startswith("a folder") and n.endswith(".tmp")]
    # was eq_checks.py:811
    check("files: a write that fails leaves no temporary file behind", not left, left)


def test_reserved_names_with_spaces(check):
    # was eq_checks.py:813
    check("files: reserved names with spaces or CONIN$ are made safe",
          [textfile.safe_name(n) for n in ("CON .txt", "conin$", "aux  .json")] == ["_CON .txt", "_conin$", "_aux  .json"])


_PAD = "abcdefghij klmnopqrst "


def _with_period(at, length):
    s = (_PAD * 20)[:length]
    return s[:at] + "." + s[at + 1:]


def test_long_names_with_a_period_obey_the_limit(check):
    # (2026-11-11: the text after the last period was kept as the "extension", so a long name with a period gave a
    # file name of 179 to 208 characters, or lost its middle)
    names = [_with_period(10, 100), _with_period(40, 120), "CON." + (_PAD * 10)[:90],
             "Sennheiser HD 600 Harman in-ear v2.1 - best fit 10 filters and more words for the length"]
    got = {n: [textfile.safe_name(n, "EQ", 80), textfile.safe_name(n, "EQ", 78),
               textfile.safe_name(n, "EQ", 80, keep_ext=False)] for n in names}
    check("files: a long name with a period gives a file name within the limit that keeps the start of the name",
          all(len(r) <= m and r.lstrip("_")[:60] == n[:60]
              for n, rs in got.items() for r, m in zip(rs, (80, 78, 80))), got)
    check("files: the cut name of \"CON.\" and 90 characters is not a reserved name",
          all(r.startswith("_CON.") for r in got[names[2]]), got[names[2]])


def test_a_cut_name_keeps_its_extension_and_ends_correctly(check):
    long = "Truthear GATe (Wide Bore Tips) (L800 IEM) L1 " + "x" * 120
    cut = textfile.safe_name(long + ".txt", max_len=100)
    check("files: a cut file name keeps its extension and has the limit's length",
          cut.endswith("x.txt") and len(cut) == 100 and cut.startswith("Truthear GATe"), cut)
    numbered = [textfile.safe_name("W" * 77 + c + " (2)", "EQ", 80, keep_ext=False) for c in "AB"]
    check("files: a name cut in \" (2)\" does not end in \" (\", and two names that differ at character 78 stay "
          "different", numbered == ["W" * 77 + "A", "W" * 77 + "B"], numbered)
    mk = textfile.safe_name("HD 600 Mk.II " + "y" * 100, "EQ", 80, keep_ext=False)
    check("files: keep_ext=False cuts the whole name (no \".II\" kept at the end)",
          mk == ("HD 600 Mk.II " + "y" * 100)[:80], mk)
    spaces = textfile.safe_name("CON" + " " * 200 + "x", max_len=150)
    check("files: a cut that leaves a reserved name gives a safe name", spaces == "_CON", spaces)
    # (2026-11-12: "HD 600 Mk.II" at the start had no period near the end, so keep_ext had no effect in the check above)
    mk2 = textfile.safe_name("y" * 100 + " HD 600 Mk.II", "EQ", 80, keep_ext=False)
    check("files: keep_ext=False keeps no short text after a period at the end", mk2 == ("y" * 100)[:80], mk2)
    mk3 = textfile.safe_name("y" * 100 + " HD 600 Mk.II", "EQ", 80)
    check("files: keep_ext=True keeps a short extension of letters", mk3.endswith(".II") and len(mk3) == 80, mk3)
    ext = "." + ("ab cd " * 7)[:39]  # (40 characters with spaces: not an extension)
    wide = [textfile.safe_name("a" * 100 + ext, "EQ", 80), textfile.safe_name("a" * 100 + ".abcdefgh", "EQ", 80)]
    check("files: a text after the last period with spaces, or of more than 5 characters, is not kept as an extension",
          wide == ["a" * 80, "a" * 80], wide)


def test_a_name_of_only_brackets_or_dashes_gets_the_fallback(check):
    # (2026-11-12: a name of only "(" or "-" characters, longer than the limit, with ".txt", gave ".txt": no name)
    got = [textfile.safe_name(c * 200 + ".txt", "EQ", 80) for c in "(-"]
    check("files: a cut name of only \"(\" or \"-\" characters keeps its extension after the fallback name",
          got == ["EQ.txt", "EQ.txt"], got)
    plain = [textfile.safe_name(c * 200, "EQ", 80, keep_ext=False) for c in "(-"]
    check("files: the same with no extension gives the fallback name", plain == ["EQ", "EQ"], plain)


def test_short_names_are_as_before(check):
    # (the results before the correction: names that fit are not changed)
    names = ["Daily", "EQ 2", "Truthear GATe (Wide Bore Tips) (L800 IEM) L1.txt", "HD 600 Mk.II", "v2.1",
             "Speakers (Realtek(R) High Definition Audio)", "Average.txt", "a.b.c.txt"]
    check("files: names that fit the limit are as before",
          [textfile.safe_name(n) for n in names] == names
          and [textfile.safe_name(n, "EQ", 80, keep_ext=False) for n in names] == names)


def test_second_damaged_copy_kept_beside_the_first(tmp_path, check):
    # (what textfile set aside is said once, to whoever asks first: the check takes it, as the window would. Other
    # tests' notices may be in it too; the check looks only for its own, then expects the list emptied)
    bad = os.path.join(tmp_path, "data", "twice.json")
    os.makedirs(os.path.dirname(bad))
    try:
        for text in ("{ first", "{ second"):
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write(text)
            textfile.read_json_kept(bad, list)
        said = textfile.take_set_aside()
        with open(bad + ".bad", encoding="utf-8") as fh:
            first_bad = fh.read()
        # was eq_checks.py:824
        check("files: a second damaged copy is kept beside the first (twice.json.2.bad), and the page is told",
              first_bad == "{ first" and os.path.exists(bad + ".2.bad") and "twice.json.2.bad" in said
              and textfile.take_set_aside() == "", said)
    finally:
        textfile.take_set_aside()  # (nothing of this test's left for another to find)


def test_inside_a_folder(tmp_path, check):
    top = str(tmp_path)  # (the old check's top: the test copy's folder; only the paths' text matters here)
    # was eq_checks.py:1043
    check("files: inside a folder, not one beside it with a longer name",
          textfile.inside(os.path.join(top, "inputs", "x"), os.path.join(top, "inputs"))
          and not textfile.inside(os.path.join(top, "inputs2", "x"), os.path.join(top, "inputs"))
          and textfile.inside(os.path.join(top, "inputs"), os.path.join(top, "inputs")))
