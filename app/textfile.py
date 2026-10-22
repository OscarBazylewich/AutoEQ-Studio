"""Reading and writing the app's files: text the way different Windows PCs and programs write it, JSON, and writes
that never leave a half-written file behind.

Encodings: UTF-8 (with or without the byte-order mark Notepad adds), UTF-16 (Notepad's "Unicode", PowerShell's
">" redirect, some measurement software) and Windows-1252 (older programs, e.g. with "°" or "µ" in a header).

Frequency-response files: the parser (squiglink's) reads numbers separated by spaces, tabs or commas, with decimal
points. Files saved on a PC set to a European language often use decimal commas and semicolons instead
("20,5;85,3" or "20,5<tab>85,3", as Excel and REW write them there); those lines are rewritten so they read the
same. Lines that aren't numbers (headers, comments) are left as they are.
"""
import json
import os
import re
import threading
import time

_DATA = re.compile(r"\s*[-+]?(\d|\.\d)")                        # a line that starts with a number
_COMMA_DECIMAL = re.compile(r"\s*[-+]?\d+,\d+\s*[;\t ]\s*[-+]?\d")  # "20,5;85,3", "20,5<tab>85,3", "20,5 85,3"
RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))}


def decode(raw):
    """The text in a file's bytes."""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw[2:].decode("utf-16-le" if raw[:2] == b"\xff\xfe" else "utf-16-be", "replace")
    head = raw[:512]
    if len(head) >= 8 and head.count(0) > len(head) // 4:  # UTF-16 without the mark (plain text: every other byte 0)
        return raw.decode("utf-16-le" if head[1::2].count(0) >= head[0::2].count(0) else "utf-16-be", "replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def read(path):
    with open(path, "rb") as fh:
        return decode(fh.read())


def encoding_of(path, default="utf-8"):
    """The encoding to write a file back in, so a program that wrote it with a byte-order mark still reads it:
    "utf-16" (with its mark), "utf-8-sig", or default (no mark, or no file)."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(3)
    except OSError:
        return default
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"
    return "utf-8-sig" if head == b"\xef\xbb\xbf" else default


def normalize_fr(text):
    """Frequency-response text with decimal points and no semicolons (see above); anything else is unchanged."""
    text = text.replace("\0", "")
    lines = text.split("\n")
    data = [ln for ln in lines if _DATA.match(ln)]
    if not data:
        return text
    comma = sum(1 for ln in data if _COMMA_DECIMAL.match(ln)) >= len(data) / 2
    if not comma and not any(";" in ln for ln in data):
        return text
    out = []
    for ln in lines:
        if _DATA.match(ln):
            if comma:
                ln = re.sub(r"(?<=\d),(?=\d)", ".", ln)
            ln = ln.replace(";", "\t")
        out.append(ln)
    return "\n".join(out)


def read_fr(path):
    return normalize_fr(read(path))


def safe_name(name, fallback="file", max_len=150):
    """A file name Windows accepts: no \\ / : * ? " < > | or control characters, no trailing dots or spaces, not a
    reserved device name (CON, NUL, COM1…), and not too long."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "").strip().rstrip(". ")
    stem, dot, ext = name.rpartition(".") if "." in name else (name, "", "")
    if stem.split(".")[0].rstrip(" ").upper() in RESERVED:  # ("CON .txt" is the console too)
        name = "_" + name
    if len(name) > max_len:  # (well within Windows' 260-character paths, with the app's folder in front)
        name = name[:max_len - len(dot + ext)].rstrip(". ") + dot + ext
    return name or fallback


# ---------------------------------------------------------------- writing, and JSON
def write_atomic(path, text, encoding="utf-8", newline=None, errors="strict"):
    """Write text (or bytes) in one step (a temporary file, then a rename), so a reader never sees half a file: another
    request reading settings.json, Equalizer APO reading its config. Windows refuses the rename while someone reads the
    file, so it is tried again for about a second."""
    tmp = f"{path}.{os.getpid()}-{threading.get_ident()}.tmp"  # (each writer its own: two at once never mix)
    try:
        with (open(tmp, "wb") if isinstance(text, bytes) else
              open(tmp, "w", encoding=encoding, newline=newline, errors=errors)) as fh:
            fh.write(text)
        for _ in range(40):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                time.sleep(0.025)
        os.replace(tmp, path)
    except BaseException:  # (a disk full, the file kept open by another program: no temporary file left behind)
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def read_json(path, default=None):
    """A JSON file's contents, or default when it is missing or unreadable (a cache that can be rebuilt). Any
    encoding decode() knows (e.g. a settings file re-saved in Notepad as "Unicode")."""
    try:
        return json.loads(read(path))
    except (OSError, ValueError):
        return default


def inside(path, folder):
    """Is path this folder or somewhere in it? (Not a folder beside it whose name starts the same: "inputs2".)"""
    p, f = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(folder))
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def read_json_kept(path, kind):
    """A data file of the user's (history, EQs to compare) that is written back whole: its contents (a `kind`: list or
    dict), or an empty one when it isn't there. One that isn't that (a hand edit gone wrong, a cut-off copy) is kept as
    <file>.bad, said in the log, instead of being written over; one another program has open right now raises
    OSError, so nothing is written over it either."""
    if not os.path.exists(path):
        return kind()
    try:
        data = json.loads(read(path))
    except ValueError:
        data = None
    if isinstance(data, kind):
        return data
    set_aside(path)
    return kind()


_SET_ASIDE = []  # what set_aside() said, until the page is told (api.handle adds it to the next answer)


def set_aside(path):
    """A file that can't be read, kept beside it as <file>.bad (<file>.2.bad … when there is one already: an
    earlier copy is never replaced), said in the log and to the page. Returns where it went."""
    bad, n = path + ".bad", 2
    while os.path.exists(bad):
        bad, n = f"{path}.{n}.bad", n + 1
    os.replace(path, bad)
    print(f"{path} couldn't be read: it is kept as {bad} and a new one is started.")
    _SET_ASIDE.append(f"{os.path.basename(path)} couldn't be read, so a new one was started: the old one is kept as "
                      f"{os.path.basename(bad)} in the data folder.")
    return bad


def take_set_aside():
    """What set_aside() said since it was last asked ("" when nothing)."""
    said = " ".join(_SET_ASIDE)
    _SET_ASIDE.clear()
    return said


def write_json(path, data, indent=None, quiet=True):
    """Save data as JSON (its folder made if needed). quiet: a cache that couldn't be written is simply not kept."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write_atomic(path, json.dumps(data, indent=indent))
    except OSError:
        if not quiet:
            raise
