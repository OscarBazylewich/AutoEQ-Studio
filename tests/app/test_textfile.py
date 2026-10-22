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
