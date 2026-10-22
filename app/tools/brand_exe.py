"""AutoEQ Studio's own launcher, runtime\\AutoEQ Studio.exe (the user's ask, 2026-10-12: Task Manager's Startup apps
called it "Python"). It's Python's pythonw.exe with AutoEQ Studio's name, version and icon in its resources: Windows
names a program by its description (Task Manager's Startup apps and Processes, the volume mixer while Listen plays,
"Open with"), and shows its icon. Changing a signed file breaks its signature, which Windows trusts less than none:
the copy's signature (the Python Software Foundation's) is taken off, as the rest of the unsigned installer.

    launcher_bytes(pythonw, ico, version)  the branded copy, as bytes (make_share_zip.runtime_entries uses it)
    icon_file(dest)                        the app's icon (ui\\icons.app_icon) as a Windows .ico
    describe(path)                         a program's {FileDescription, ProductName, …}, for checks
"""
import ctypes
import os
import shutil
import struct
import tempfile
from ctypes import wintypes

RT_ICON, RT_GROUP_ICON, RT_VERSION = 3, 14, 16
LANG = 0x0409  # (English, United States: the language the version strings are listed under)
NAME = "AutoEQ Studio"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.BeginUpdateResourceW.restype = wintypes.HANDLE
_k32.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
_k32.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_void_p,
                                 wintypes.DWORD]
_k32.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
_k32.LoadLibraryExW.restype = wintypes.HMODULE
_k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
_k32.FreeLibrary.argtypes = [wintypes.HMODULE]
_ENUM_NAMES = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
_ENUM_LANGS = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD,
                                 ctypes.c_void_p)
_k32.EnumResourceNamesW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, _ENUM_NAMES, ctypes.c_void_p]
_k32.EnumResourceLanguagesW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, _ENUM_LANGS,
                                        ctypes.c_void_p]


def _resources(path, types):
    """[(type, name: int id or str, language)] of these types in a program."""
    found = []
    mod = _k32.LoadLibraryExW(path, None, 0x2)  # (LOAD_LIBRARY_AS_DATAFILE: only read)
    if not mod:
        raise OSError(ctypes.get_last_error(), f"can't read {path}")

    def names(m, rtype, name, _p):
        key = name if name < 0x10000 else ctypes.wstring_at(name)

        def langs(m2, t2, n2, lang, _p2):
            found.append((rtype, key, lang))
            return True
        _k32.EnumResourceLanguagesW(m, ctypes.c_void_p(rtype), ctypes.c_void_p(name), _ENUM_LANGS(langs), None)
        return True
    try:
        for t in types:
            _k32.EnumResourceNamesW(mod, ctypes.c_void_p(t), _ENUM_NAMES(names), None)
    finally:
        _k32.FreeLibrary(mod)
    return found


def _node(key, value=b"", wtype=0, children=(), value_len=None):
    """One block of a version resource: its length, its value's length, type, key, value, children (4-byte aligned)."""
    k = (key + "\0").encode("utf-16-le")
    head = 6 + len(k)
    body = b"\0" * ((-head) % 4) + value
    body += b"\0" * ((-(head + len(body))) % 4)
    for c in children:
        body += c + b"\0" * ((-len(c)) % 4)
    length = head + len(body)
    vlen = value_len if value_len is not None else len(value)
    return struct.pack("<HHH", length, vlen, wtype) + k + body


def version_resource(version, description=NAME, product=NAME, company=NAME, original="AutoEQ Studio.exe"):
    nums = [int(x) for x in (version.split(".") + ["0", "0", "0"])[:4]]
    ms, ls = (nums[0] << 16) | nums[1], (nums[2] << 16) | nums[3]
    fixed = struct.pack("<13I", 0xFEEF04BD, 0x00010000, ms, ls, ms, ls, 0x3F, 0, 0x4, 0x1, 0, 0, 0)

    def string(k, v):
        s = (v + "\0").encode("utf-16-le")
        return _node(k, s, 1, value_len=len(s) // 2)
    strings = [string(k, v) for k, v in (("CompanyName", company), ("FileDescription", description),
                                         ("FileVersion", version), ("InternalName", NAME),
                                         ("OriginalFilename", original), ("ProductName", product),
                                         ("ProductVersion", version))]
    table = _node("040904B0", wtype=1, children=strings)
    sfi = _node("StringFileInfo", wtype=1, children=[table])
    var = _node("Translation", struct.pack("<HH", LANG, 0x04B0), 0)
    vfi = _node("VarFileInfo", wtype=1, children=[var])
    return _node("VS_VERSION_INFO", fixed, 0, children=[sfi, vfi])


def _ico_images(ico):
    """[(width, height, bit count, image bytes)] of a .ico file."""
    with open(ico, "rb") as fh:
        data = fh.read()
    _r, _t, n = struct.unpack_from("<HHH", data, 0)
    out = []
    for i in range(n):
        w, h, _c, _res, _planes, bits, size, at = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        out.append((w, h, bits, data[at:at + size]))
    return out


def _strip_signature(path):
    """Take a program's (now broken) signature off: its certificate table and the header's pointer to it."""
    with open(path, "r+b") as fh:
        data = bytearray(fh.read())
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        opt = pe + 24
        magic = struct.unpack_from("<H", data, opt)[0]
        dirs = opt + (112 if magic == 0x20B else 96)
        sec = dirs + 4 * 8  # (IMAGE_DIRECTORY_ENTRY_SECURITY)
        at, size = struct.unpack_from("<II", data, sec)
        if not at:
            return
        struct.pack_into("<II", data, sec, 0, 0)
        if at + size >= len(data):  # (the certificates are at the end of the file: cut off)
            del data[at:]
        fh.seek(0)
        fh.write(data)
        fh.truncate()


def launcher_bytes(pythonw, ico, version):
    """pythonw.exe as AutoEQ Studio's launcher: its version resource and icons replaced, its signature taken off."""
    tmp = tempfile.mkdtemp(prefix="aeqs-brand-")
    try:
        exe = os.path.join(tmp, "AutoEQ Studio.exe")
        shutil.copyfile(pythonw, exe)
        old = _resources(exe, (RT_ICON, RT_GROUP_ICON, RT_VERSION))
        h = _k32.BeginUpdateResourceW(exe, False)
        if not h:
            raise OSError(ctypes.get_last_error(), "can't change the launcher's resources")
        keep = []  # (ctypes buffers alive until the update ends)

        def put(rtype, name, lang, data):
            buf = ctypes.create_string_buffer(data, len(data)) if data else None
            keep.append(buf)
            nm = ctypes.c_void_p(name) if isinstance(name, int) else ctypes.c_wchar_p(name)
            keep.append(nm)
            if not _k32.UpdateResourceW(h, ctypes.c_void_p(rtype), nm, lang, buf, len(data) if data else 0):
                raise OSError(ctypes.get_last_error(), f"can't write resource {rtype}/{name}")
        try:
            for rtype, name, lang in old:  # (Python's own: its version and icons)
                put(rtype, name, lang, b"")
            images = _ico_images(ico)
            group = struct.pack("<HHH", 0, 1, len(images))
            for i, (w, hgt, bits, img) in enumerate(images, start=1):
                put(RT_ICON, i, LANG, img)
                group += struct.pack("<BBBBHHIH", w, hgt, 0, 0, 1, bits, len(img), i)
            put(RT_GROUP_ICON, 1, LANG, group)
            put(RT_VERSION, 1, LANG, version_resource(version))
        except Exception:
            _k32.EndUpdateResourceW(h, True)  # (nothing written)
            raise
        if not _k32.EndUpdateResourceW(h, False):
            raise OSError(ctypes.get_last_error(), "can't save the launcher's resources")
        _strip_signature(exe)
        with open(exe, "rb") as fh:
            return fh.read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def icon_file(dest):
    """The app's icon as a Windows .ico: each size a PNG (Windows Vista and later read them)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QGuiApplication
    from ui import icons
    _app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841 - (drawing needs one)
    pngs = []
    for s in SIZES:
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.WriteOnly)
        icons.app_icon().pixmap(s, s).save(buf, "PNG")
        pngs.append(bytes(data))
    out = struct.pack("<HHH", 0, 1, len(SIZES))
    at = 6 + 16 * len(SIZES)
    for s, png in zip(SIZES, pngs):
        out += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(png), at)
        at += len(png)
    with open(dest, "wb") as fh:
        fh.write(out + b"".join(pngs))


def describe(path):
    """A program's version strings: {"FileDescription", "ProductName", "FileVersion", "CompanyName"} ({} if none)."""
    ver = ctypes.WinDLL("version")
    size = ver.GetFileVersionInfoSizeW(path, None)
    if not size:
        return {}
    buf = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(path, 0, size, buf):
        return {}
    ptr, n = ctypes.c_void_p(), wintypes.UINT()
    if not ver.VerQueryValueW(buf, "\\VarFileInfo\\Translation", ctypes.byref(ptr), ctypes.byref(n)) or not n.value:
        return {}
    lang, cp = struct.unpack("<HH", ctypes.string_at(ptr.value, 4))
    out = {}
    for k in ("FileDescription", "ProductName", "FileVersion", "CompanyName"):
        if ver.VerQueryValueW(buf, f"\\StringFileInfo\\{lang:04x}{cp:04x}\\{k}", ctypes.byref(ptr), ctypes.byref(n)) \
                and n.value:
            out[k] = ctypes.wstring_at(ptr.value, n.value).rstrip("\0")
    return out
