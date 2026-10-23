"""Online databases: squig.link-style graph sites and the AutoEq repository on GitHub.

Each squig.link site (CrinGraph graph tool) has a page -> config*.js (DIR, PHONE_BOOK, channels, samples, targets)
-> phone_book.json -> "<file> L1.txt"... text files. The AutoEq repository lists its measurements/ and targets/
CSV files through the GitHub trees API. Indexes are cached for a few days; files are downloaded on demand into
downloads/<database>/ (the "This PC" search leaves it out: those are these entries, used from there when downloaded).
"""
import functools
import hashlib
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import paths
import net
import paths as studio_paths  # (the app's own: its version for the downloads' User-Agent)
import textfile

HERE = paths.APP
DOWNLOAD_DIR = paths.DOWNLOAD_DIR
CACHE_PATH = os.path.join(paths.CACHE, "databases.json")
MAX_AGE = 3 * 24 * 3600
RECHECK = 30 * 60  # (a refresh asked for within this of the last one, for the same databases, is skipped; not a forced one)
LIST_VERSION = 2  # lists made by an older version of the reading below are made again (2: modernGraphTool, comments)
UA = f"AutoEQ-Studio/{studio_paths.VERSION} (personal EQ tool)"

# The largest databases, with what's known about them (DATABASES.txt): rig: (ear simulator, stated by the source?) for
# "Which measurement to use"; browse: the site doesn't let other programs download its files, so entries are listed
# and open on the site; group: how Settings groups them (GROUPS). Every other database in squig.link's own list
# (directory_sites) is added after these and is on too; any of them can be turned off in Settings > Sources.
SITES = [
    {"group": "all", "name": "AutoEq (GitHub)", "short": "AutoEq", "url": "https://github.com/jaakkopasanen/AutoEq", "type": "autoeq"},
    {"group": "iem", "name": "Hangout.Audio IEMs (Crinacle, 711)", "short": "Hangout 711", "url": "https://graph.hangout.audio/iem/711/",
     "rig": ("711", True), "browse": True},
    {"group": "5128", "name": "Hangout.Audio IEMs (Crinacle, 5128)", "short": "Hangout 5128", "url": "https://graph.hangout.audio/iem/5128/",
     "rig": ("5128", True), "browse": True},
    {"group": "hp", "name": "Hangout.Audio headphones (Crinacle)", "short": "Hangout HP", "url": "https://graph.hangout.audio/headphones/",
     "rig": ("43AG", False), "browse": True},
    {"group": "iem", "name": "Aftersound IEMs", "short": "Aftersound", "url": "https://aftersound.squig.link/", "rig": ("711", False)},
    {"group": "iem", "name": "HBB", "short": "HBB", "url": "https://hbb.squig.link/", "rig": ("711", False)},
    {"group": "iem", "name": "Paul Wasabi IEMs", "short": "PW", "url": "https://pw.squig.link/", "rig": ("711", False)},
    {"group": "iem", "name": "Super* Review IEMs", "short": "Super", "url": "https://squig.link/", "rig": ("711", False)},
    {"group": "iem", "name": "Jaytiss IEMs", "short": "Jaytiss", "url": "https://jaytiss.squig.link/", "rig": ("711", False)},
    {"group": "iem", "name": "Audio Amigo IEMs", "short": "Amigo", "url": "https://audioamigo.squig.link/", "rig": ("711", False)},
    {"group": "5128", "name": "Earphones Archive IEMs (5128)", "short": "EA IEM", "url": "https://earphonesarchive.squig.link/",
     "rig": ("5128", True)},
    {"group": "5128", "name": "Earphones Archive headphones (5128)", "short": "EA HP", "url": "https://earphonesarchive.squig.link/headphones/",
     "rig": ("5128", True)},
    {"group": "hp", "name": "Unheard Lab headphones", "short": "Unheard", "url": "https://sai.squig.link/", "rig": (None, False)},
    {"group": "hp", "name": "Gadgetry Tech headphones", "short": "Gadgetry", "url": "https://gadgetrytech.squig.link/headsets/",
     "rig": (None, False)},
    {"group": "5128", "name": "listener800 5128 IEMs", "short": "L800 IEM", "url": "https://listener800.github.io/5128iem.html",
     "rig": ("5128", True)},
    {"group": "5128", "name": "listener800 5128 headphones", "short": "L800 HP", "url": "https://listener800.github.io/", "rig": ("5128", True)},
    # smaller ones, off unless turned on in Settings
    {"group": "iem", "name": "Precogvision", "short": "Precog", "url": "https://precog.squig.link/", "rig": ("711", False)},
    {"group": "iem", "name": "Audio Discourse IEMs", "short": "AD IEM", "url": "https://iems.audiodiscourse.com/", "rig": ("711", False)},
    {"group": "hp", "name": "Audio Discourse headphones", "short": "AD HP", "url": "https://headphones.audiodiscourse.com/"},
    {"group": "hp", "name": "Super* Review headphones", "short": "Super HP", "url": "https://squig.link/hp.html"},
]
GROUPS = {"all": "Collections (many measurers)", "iem": "IEMs · 711-type coupler", "5128": "IEMs and headphones · B&K 5128",
          "hp": "Headphones", "earbuds": "Earbuds", "added": "Added by you"}
DIRECTORY_URL = "https://squig.link/squigsites.json"   # the list behind squig.link's "More squiglinks" menu
DIRECTORY_PATH = os.path.join(paths.CACHE, "squigsites.json")
RETRY_AFTER = 600  # seconds before squig.link's list is asked for again after a try that failed (offline, slow network)
_dir_failed = {"at": 0.0}
_TYPE_GROUP = {"IEMs": "iem", "5128": "5128", "Headphones": "hp", "Earbuds": "earbuds"}
BROWSE_NOTE = ("{site} doesn't let other programs download its measurement files, so the app can only list them. "
               "It opens on the site instead.")

_lock = threading.Lock()
_state = {"loading": False, "sites": [], "items": [], "updated": None}
_by_id = {}


# ---------------------------------------------------------------- helpers
def _get(url, timeout=20, limit=20_000_000):
    net.check("Getting files from the online databases")  # (offline: nothing goes out; net.Offline is an OSError)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(limit + 1)
        if len(data) > limit:
            raise ValueError("file too large")
        return data.decode("utf-8", "ignore"), r.geturl()


@functools.lru_cache(maxsize=8192)  # (asked for every database for each file found: 2.9 million times a list)
def folder_name(name):
    """The folder in the downloads folder for a database (or a file name part): a name Windows accepts, not too long."""
    return textfile.safe_name(name, "file", max_len=110)  # (reserved names like CON, and Windows' path length)


def norm_url(u):
    """A site address as compared with others (no trailing /, lower case)."""
    return u.strip().rstrip("/").lower()


def _js_literal_to_json(src):
    """A plain JS array/object literal (quoted or bare keys, ' or " strings, comments, trailing commas) -> JSON."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'`":
            j, buf = i + 1, []
            esc = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
            while j < n and src[j] != c:
                if src[j] == "\\" and j + 1 < n:
                    e = src[j + 1]
                    if e == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", src[j + 2:j + 6]):
                        buf.append(chr(int(src[j + 2:j + 6], 16))); j += 6
                    else:
                        buf.append(esc.get(e, e)); j += 2
                else:
                    buf.append(src[j]); j += 1
            out.append(json.dumps("".join(buf), ensure_ascii=False)); i = j + 1
        elif src.startswith("//", i):
            i = src.find("\n", i) if src.find("\n", i) >= 0 else n
        elif src.startswith("/*", i):
            i = src.find("*/", i) + 2 if src.find("*/", i) >= 0 else n
        elif c.isalpha() or c in "_$":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            word = src[i:j]
            k = j
            while k < n and src[k].isspace():
                k += 1
            out.append(f'"{word}"' if k < n and src[k] == ":" else word)
            i = j
        else:
            out.append(c); i += 1
    return re.sub(r",(\s*[\]}])", r"\1", "".join(out))


def _skip_string(src, i):
    """The index after the JS string literal starting at src[i]."""
    q, j = src[i], i + 1
    while j < len(src) and src[j] != q:
        j += 2 if src[j] == "\\" else 1
    return j + 1


def _strip_comments(src):
    """JS source without its comments (strings kept whole: a URL's // isn't one). A config's commented-out
    `// PHONE_BOOK = "phone_book.json"` line (the graph tool's template has one) was read as if it were set."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'`":
            j = _skip_string(src, i)
            out.append(src[i:j]); i = j
        elif src.startswith("//", i):
            i = src.find("\n", i) if src.find("\n", i) >= 0 else n
        elif src.startswith("/*", i):
            i = src.find("*/", i) + 2 if src.find("*/", i) >= 0 else n
        else:
            out.append(c); i += 1
    return "".join(out)


def _bracketed(src, i):
    """The [...] or {...} starting at src[i], to its matching bracket (strings skipped)."""
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c in "\"'`":
            j = _skip_string(src, j); continue
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    raise ValueError("unbalanced brackets")


def site_on(s, cfg):
    db = cfg.get("databases", {})
    if s.get("on", True):
        return s["name"] not in set(db.get("disabled") or [])
    return s["name"] in set(db.get("enabled") or [])


def _web(items):
    """Only entries whose address is a web page (http or https): the list comes from another site, and its addresses
    become links and downloads."""
    return [d for d in items if isinstance(d, dict) and str(d.get("url", "")).lower().startswith(("http://", "https://"))]


def directory(refresh=False):
    """squig.link's list of databases: [{name, type, group, url}], saved for a few days."""
    c = textfile.read_json(DIRECTORY_PATH)
    if not isinstance(c, dict) or "items" not in c or "time" not in c:
        c = None
    elif not refresh and time.time() - c["time"] < MAX_AGE:
        return _web(c["items"])
    if not refresh and time.time() - _dir_failed["at"] < RETRY_AFTER:  # (each call would wait up to 20 s again)
        return _web(c["items"]) if c else []
    try:
        sites = json.loads(_get(DIRECTORY_URL)[0])
    except net.Offline:  # (the app is offline: not a failed try, so going online asks again at once)
        return _web(c["items"]) if c else []
    except Exception:
        _dir_failed["at"] = time.time()
        return _web(c["items"]) if c else []
    items = []
    for s in sites:
        kind = s.get("urlType")
        base = ("https://squig.link" if kind == "root" else s.get("altDomain", "") if kind == "altDomain"
                else f"https://{s['username']}.squig.link" if kind == "subdomain" else f"https://squig.link/lab/{s['username']}")
        dbs = s.get("dbs") or []
        for d in dbs:
            name = s.get("name", s.get("username", "?")) + (f" ({d.get('type')})" if len(dbs) > 1 else "")
            items.append({"name": name, "type": d.get("type", ""), "group": _TYPE_GROUP.get(d.get("type"), "added"),
                          "url": base.rstrip("/") + d.get("folder", "/")})
    items = _web(items)
    textfile.write_json(DIRECTORY_PATH, {"time": time.time(), "items": items})
    return items


def saved_directory():
    """squig.link's list as last saved, never fetched: for lookups the window may wait on (fetching, up to 20 s, is
    left to the background refresh: review 2)."""
    c = textfile.read_json(DIRECTORY_PATH)
    return _web(c["items"]) if isinstance(c, dict) and isinstance(c.get("items"), list) else []


_extra_sites = {}  # url -> site, for sites the user added (so their rig and name are known elsewhere)


def added_sites():
    """The sites the user added (Find… › Sources…) that are in use."""
    return list(_extra_sites.values())


def added_site(u):
    """A site the user added: named and grouped from squig.link's list when it's there."""
    known = {norm_url(d["url"]): d for d in saved_directory()}
    d = known.get(norm_url(u))
    p = urllib.parse.urlparse(u)
    s = {"name": d["name"] if d else p.netloc + p.path.rstrip("/"), "short": (d["name"] if d else p.netloc.split(".")[0])[:12],
         "url": u.strip(), "group": d["group"] if d else "added", "extra": True,
         "rig": ("5128", True) if d and d["type"] == "5128" else ("711", False) if d and d["type"] == "IEMs" else (None, False)}
    _extra_sites[norm_url(u)] = s
    return s


_DIR_RIG = {"5128": ("5128", True), "IEMs": ("711", False)}  # squig.link lists 5128 databases as such; its other
# IEM databases almost all use 711-type couplers (or clones); headphone and earbud rigs vary, so they stay unknown
_dir_sites = {"mtime": None, "sites": [], "by_url": {}}


def directory_sites():
    """Every database in squig.link's list that isn't one of SITES, as a site (named and grouped as squig.link lists
    it). The list is read from its saved copy (refreshed with the database lists), again only when that changes."""
    now = time.time()
    if now - _dir_sites.get("checked", 0) < 5:  # (looked up for every entry of the lists: the file is checked now and then)
        return _dir_sites["sites"]
    _dir_sites["checked"] = now
    try:
        mtime = os.path.getmtime(DIRECTORY_PATH)
    except OSError:
        mtime = None
    # (built the first time too: without squig.link's saved list, a first start offline, its time stayed "none", as
    # at the start, so the index, the built-in databases' included, was never built: no device type or rig for
    # AutoEq's entries; fixed 2026-10-22)
    if mtime != _dir_sites["mtime"] or not _dir_sites["by_url"]:
        items = saved_directory() if mtime else []
        have = {norm_url(s["url"]) for s in SITES}
        out, shorts = [], {s["short"] for s in SITES}
        for d in items:
            if norm_url(d["url"]) in have:
                continue
            have.add(norm_url(d["url"]))
            short = d["name"][:24]
            while short in shorts:
                short += "+"
            shorts.add(short)
            out.append({"group": d["group"], "name": d["name"], "short": short, "url": d["url"], "dir": True,
                        "rig": _DIR_RIG.get(d["type"], (None, False))})
        _dir_sites.update(mtime=mtime, sites=out, by_url={norm_url(s["url"]): s for s in SITES + out})
    return _dir_sites["sites"]


def all_sites():
    """The databases the app knows: SITES, then the rest of squig.link's list."""
    return SITES + directory_sites()


def find_site(url):
    n = norm_url(url or "")
    directory_sites()  # (the index, kept up to date)
    return _dir_sites["by_url"].get(n) or _extra_sites.get(n)


def sites_for(cfg):
    db = cfg.get("databases", {})
    known = all_sites()
    have = {norm_url(s["url"]) for s in known}
    extra = [added_site(u) for u in (db.get("extra") or []) if u.strip().startswith(("http://", "https://"))
             and norm_url(u) not in have]
    return [s for s in known if site_on(s, cfg)] + extra


# ---------------------------------------------------------------- indexing
def _index_autoeq(site):
    api = "https://api.github.com/repos/jaakkopasanen/AutoEq/git/trees/"
    root = json.loads(_get(api + "master")[0])
    subs = {e["path"]: e["sha"] for e in root["tree"]}
    items = []

    def tree(sha, prefix=""):
        """Every file under a folder. GitHub cuts a recursive answer past 100,000 entries or 7 MB (and says so):
        then the folder is walked one folder at a time."""
        t = json.loads(_get(api + sha + "?recursive=1", timeout=60)[0])
        if not t.get("truncated"):
            return [dict(e, path=prefix + e["path"]) for e in t["tree"]]
        out = []
        for e in json.loads(_get(api + sha, timeout=60)[0])["tree"]:
            out += tree(e["sha"], prefix + e["path"] + "/") if e["type"] == "tree" else [dict(e, path=prefix + e["path"])]
        return out
    for folder, kind in (("measurements", "measurement"), ("targets", "target")):
        for e in tree(subs[folder]):
            p = e["path"]
            if e["type"] != "blob" or not p.lower().endswith(".csv"):
                continue
            parts = p.split("/")
            name = os.path.splitext(parts[-1])[0]
            if kind == "measurement":
                source = parts[0]
                form = parts[2] if len(parts) > 3 else ""
                sub = f"{source}{' · ' + form if form else ''}"
                tag = source
            else:
                sub, tag = "target", "AutoEq"
            items.append({"kind": kind, "name": name, "sub": sub, "tag": tag,
                          "ref": {"url": "https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/"
                                         + urllib.parse.quote(f"{folder}/{p}")}})
    return items, {}


def _page(url):
    """A page's HTML and its final address, also after a <meta http-equiv="refresh"> redirect (DHRME's headphones
    page moved to its own domain that way)."""
    html, final = _get(url)
    for _ in range(3):
        if re.search(r'<script[^>]+src=["\'][^"\']*config[^/"\']*\.js', html):
            break
        meta = [m for m in re.findall(r"<meta\b[^>]*>", html, re.I) if re.search(r"http-equiv=[\"']?refresh", m, re.I)]
        to = re.search(r"content=[\"']?\s*\d*\s*;?\s*url=([^\"'>\s]+)", meta[0], re.I) if meta else None
        if not to:
            break
        html, final = _get(urllib.parse.urljoin(final, to.group(1)))
    return html, final


def _modern_config(cfg_text, final):
    """modernGraphTool (a newer graph tool, e.g. Doltonius, SilicaGel): `const CONFIG = {PATH: {PHONE_MEASUREMENT,
    TARGET_MEASUREMENT, PHONE_BOOK}, TARGET_MANIFEST: [...] or {default: [...]}}`; measurements "<file> L.txt" in
    their own folder, targets "<name> Target.txt" in theirs."""
    val = lambda key, default: (re.search(rf'\b{key}\s*:\s*["\']([^"\']*)["\']', cfg_text) or [None, default])[1]
    folder = lambda key, default: urllib.parse.urljoin(final, val(key, default).rstrip("/") + "/")
    targets = []
    m = re.search(r"\bTARGET_MANIFEST\s*:\s*([\[{])", cfg_text)
    if m:
        try:
            block = _bracketed(cfg_text, m.start(1))
            if block[0] == "{":
                d = re.search(r"\bdefault\s*:\s*\[", block)
                block = _bracketed(block, d.end() - 1) if d else "[]"
            targets = json.loads(_js_literal_to_json(block))
        except (ValueError, AttributeError):
            targets = []
    return {"base": folder("PHONE_MEASUREMENT", "./data/phones"), "targets_base": folder("TARGET_MEASUREMENT", "./data/target"),
            "phone_book": urllib.parse.urljoin(final, val("PHONE_BOOK", "./data/phone_book.json")),
            "samples": 0, "channels": ["L", "R"], "targets": [t for t in targets if isinstance(t, dict)]}


def _squig_config(site):
    html, final = _page(site["url"])
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    cfgs = [s for s in scripts if re.search(r"config[^/]*\.js", s)]
    if not cfgs:
        raise ValueError("no graph-tool config found on that page")
    cfg_text = _strip_comments(_get(urllib.parse.urljoin(final, cfgs[0]))[0])
    if re.search(r"\bCONFIG\s*=\s*\{", cfg_text) and not re.search(r"\bDIR\s*=", cfg_text):
        return _modern_config(cfg_text, final)
    val = lambda pat: (re.search(pat, cfg_text) or [None, None])[1]
    d = val(r'\bDIR\s*=\s*["\']([^"\']*)["\']') or "data/"
    pb = val(r'\bPHONE_BOOK\s*=\s*["\']([^"\']*)["\']')
    ns = val(r'\bnum_samples\s*=\s*(\d+)')
    ch = val(r'\bdefault_channels\s*=\s*(\[[^\]]*\])')
    base = urllib.parse.urljoin(final, d)
    targets = []
    m = re.search(r'\btargets\s*=\s*(\[.*?\])\s*;', cfg_text, re.S)
    if m:
        try:
            targets = json.loads(_js_literal_to_json(m.group(1)))
        except ValueError:
            targets = []
    channels = re.findall(r'["\']([^"\']+)["\']', ch) if ch else ["L", "R"]
    return {"base": base, "phone_book": urllib.parse.urljoin(final, pb) if pb else base + "phone_book.json",
            "samples": int(ns) if ns else 0, "channels": channels or ["L", "R"], "targets": targets}


def _phone_variants(p):
    """[(name shown, ref)] for one phone-book entry. ref: {"file"} ("<file> L.txt"...), with "samples": n when the
    entry has its own numbered samples ("<file> L1.txt"...), or {"file", "files"} for a set of files averaged
    together (modernGraphTool's seating positions, "hptfs")."""
    if isinstance(p, str):
        return [(p, {"file": p})]
    if not isinstance(p, dict):
        return []
    # (as squig.link's own page reads them: a name given as a list, "sufix"/"Sufix" for suffix)
    p = dict(p)
    if isinstance(p.get("name"), list):
        p["name"] = str(p["name"][0]) if p["name"] else ""
    p["name"] = str(p.get("name") or "")
    for k in ("sufix", "Sufix", "Suffix"):
        if k in p and "suffix" not in p:
            p["suffix"] = p[k]
    if isinstance(p.get("suffix"), str):
        p["suffix"] = [p["suffix"]]
    n = p.get("samples") if isinstance(p.get("samples"), int) and p["samples"] > 0 else 0
    ref = lambda f, **more: dict({"file": f}, **({"samples": n} if n else {}), **more)
    extra = [e for e in (p.get("hptfs") or []) + (p.get("variants") or []) if isinstance(e, dict)]
    f = p.get("file") or (None if extra else p["name"])
    if isinstance(f, str):
        out = [(p["name"] or f, ref(f))]
    elif isinstance(f, list):
        f = [str(x) for x in f]
        if p.get("suffix"):
            names = [p["name"] + (" " + s if s else "") for s in p["suffix"]]
        elif p.get("prefix"):
            reg = re.compile("^" + re.escape(p["prefix"]) + r"\s*", re.I)
            names = [p["name"] + (" " + reg.sub("", x) if reg.sub("", x) else "") for x in f]
        else:
            names = list(f)
        out = [(nm, ref(x)) for nm, x in zip(names, f)]
    else:
        out = []
    for e in extra:  # modernGraphTool's own keys: hptfs [{suffix, files}], variants [{suffix, file, samples}]
        smp = e.get("samples") if isinstance(e.get("samples"), dict) else {"count": e.get("samples")}
        files = e.get("files") or smp.get("files")
        name = (p["name"] + " " + str(e.get("suffix") or "")).strip()
        if isinstance(files, list) and files and not e.get("file"):
            r = {"file": str(files[0]), "files": [str(x) for x in files]}
        else:
            r = {"file": str(e.get("file") or p["name"])}
            if isinstance(smp.get("count"), int) and smp["count"] > 1:
                r["samples"] = smp["count"]
        same = [i for i, (_, o) in enumerate(out) if o["file"] == r["file"]]
        if same:  # (a variant naming a file the entry already has replaces it, as modernGraphTool does)
            out[same[0]] = (name, r)
        else:
            out.append((name, r))
    return out


def _index_squig(site):
    conf = _squig_config(site)
    book = json.loads(_get(conf["phone_book"])[0])
    items = []
    for b in book:
        brand = b.get("name", "")
        for p in b.get("phones", []):
            for disp, ref in _phone_variants(p):
                full = disp if disp.lower().startswith(brand.lower()) else f"{brand} {disp}".strip()
                it = {"kind": "measurement", "name": full, "sub": brand, "tag": site["short"], "ref": ref}
                if site.get("browse"):  # the page's own share link (as squig.link's database explorer makes it)
                    it["link"] = site["url"] + "?share=" + urllib.parse.quote(ref["file"].replace(" ", "_"))
                items.append(it)
    for group in ([] if site.get("browse") else conf["targets"]):
        for t in group.get("files", []):
            items.append({"kind": "target", "name": t, "sub": group.get("type", "target"), "tag": site["short"],
                          "ref": {"file": t + " Target"}})
    return items, conf


_confs = {}  # site url -> its graph tool's config, from the lists as last loaded


def load_cache():
    """{site url: {"time", "items", "conf"}}: every database's list as last downloaded."""
    return textfile.read_json(CACHE_PATH, {})


def refresh_now(sites, force=False):
    """Load the lists of these sites (from the cache while it's recent, unless force), in this thread."""
    cache = load_cache()

    def one(site):  # (site, its cache entry, error)
        c = cache.get(site["url"])
        if c and not force and c.get("v") == LIST_VERSION and time.time() - c["time"] < MAX_AGE:
            return site, c, None
        try:
            found, conf = (_index_autoeq if site.get("type") == "autoeq" else _index_squig)(site)
            return site, {"time": time.time(), "items": found, "conf": conf, "v": LIST_VERSION}, None
        except Exception as e:  # noqa: BLE001 - a site that's down: an older list is kept if there is one
            return site, c, f"{type(e).__name__}: {e}"

    with ThreadPoolExecutor(10) as ex:
        results = {site["url"]: (c, err) for site, c, err in ex.map(one, sites)}
    downloaded = any(c is not None and c is not cache.get(url) for url, (c, _) in results.items())
    status, entries = [], []
    for site in sites:
        c, err = results[site["url"]]
        n = 0
        if c:
            cache[site["url"]] = c
            for it in c["items"]:
                entries.append(dict(it, site=site["name"], site_url=site["url"]))
                n += 1
        status.append({"name": site["name"], "url": site["url"], "count": n, "error": err, "group": site.get("group", "added"),
                       "extra": bool(site.get("extra")), "updated": c["time"] if c else None})
    assign_ids(entries)
    if downloaded:  # (only then: writing every list takes a while and slowed the app's start)
        textfile.write_json(CACHE_PATH, cache)
    keep_confs(cache)
    set_items(entries)  # (before "loading" ends: the page asks for the entries as soon as it does)
    with _lock:
        _state.update(loading=False, sites=status, updated=time.time())


def keep_confs(cache):
    """Each site's graph tool config from these lists (load_cache()'s), kept in memory: each download needs its
    site's, and the lists file is 8 MB. (The rig builds, which read the lists themselves, use it too.)"""
    _confs.clear()
    _confs.update({url: c.get("conf") for url, c in cache.items() if isinstance(c, dict)})


def assign_ids(entries):
    """Each entry's id (download() and item() find it by it): one that stays the same through a refresh (a position
    changed with every database added: a Use button still holding one got another entry). Entries of one database
    with the same name are told apart ("dup": their files get their own local names). (The rig builds use it too.)"""
    seen, names = {}, {}
    for it in entries:
        names[(it["site_url"], it["kind"], it["name"])] = names.get((it["site_url"], it["kind"], it["name"]), 0) + 1
    for it in entries:
        base = hashlib.sha1(json.dumps([it["site_url"], it["kind"], it["name"], it.get("ref")], sort_keys=True)
                            .encode()).hexdigest()[:12]
        seen[base] = seen.get(base, 0) + 1
        it["id"] = base if seen[base] == 1 else f"{base}-{seen[base]}"
        if names[(it["site_url"], it["kind"], it["name"])] > 1:
            it["dup"] = True


def set_items(entries):
    """The entries every search uses (each with its "id", "site" and "site_url")."""
    with _lock:
        _state["items"] = entries
        _by_id.clear()
        _by_id.update({it["id"]: it for it in entries})


def items():
    """Every entry of every database in use (a copy of the list; the entries themselves are shared)."""
    with _lock:
        return list(_state["items"])


def start_refresh(cfg, force=False):
    """The lists, loaded in a background thread (squig.link's list first: it can wait on the network, and the app's
    window, opened after this, mustn't). Not again when these databases' lists were loaded a short while ago
    (RECHECK) without errors (offline, errors are expected): each Find… asked, and loading 55,000 entries again
    held the window up."""
    urls = sorted(s["url"] for s in sites_for(cfg))
    with _lock:
        if _state["loading"]:  # (a database added meanwhile: loaded by another refresh right after this one)
            _state["again"] = (cfg, force)
            return False
        if not force and _state["updated"] and time.time() - _state["updated"] < RECHECK \
                and sorted(s.get("url") or "" for s in _state["sites"]) == urls \
                and (net.offline() or not any(s.get("error") for s in _state["sites"])):
            return False
        _state["loading"] = True

    def run(cfg, force):
        while True:
            try:
                try:
                    directory(refresh=force)  # (squig.link's list: new databases join the next lists)
                except Exception:  # noqa: BLE001 - offline: the saved list is used
                    pass
                refresh_now(sites_for(cfg), force)
            except Exception as e:
                with _lock:
                    _state.update(loading=False, sites=[{"name": "all", "error": str(e), "count": 0}])
            with _lock:
                again = _state.pop("again", None)
                if not again:
                    return
                (cfg, force), _state["loading"] = again, True
    threading.Thread(target=run, args=(cfg, force), daemon=True).start()
    return True


def status(with_items=False, rig=None):
    with _lock:
        out = {"loading": _state["loading"], "sites": list(_state["sites"]), "count": len(_state["items"]),
               "updated": _state["updated"]}
        if with_items:  # compact rows for the picker: id, kind, name, sub, site, the page link for list-only sites
            # (or null), the rig tag (rig(item), e.g. "5128", "711?" or ""), the device type ("iem", "hp", "earbud", "")
            # Made once per list (the same list object back until a refresh replaces it: Find… then knows its rows
            # are made already); not to be changed by the caller
            made = _rows_made.get("rows") if _rows_made.get("of") is _state["items"] and _rows_made.get("rig") == bool(rig) else None
            if made is None:
                for it in _state["items"]:
                    if "form" not in it:  # (worked out once per list)
                        it["form"] = item_form(it)
                made = [[it["id"], it["kind"][0], it["name"], it["sub"], it["site"], it.get("link"), rig(it) if rig else "",
                         it["form"]] for it in _state["items"]]
                _rows_made.update(of=_state["items"], rig=bool(rig), rows=made)
            out["items"] = made
    return out


_rows_made = {}  # status()'s rows of the list in use


# ---------------------------------------------------------------- device type (IEM, headphone, earbud)
_FORM_OF_GROUP = {"iem": "iem", "hp": "hp", "earbuds": "earbud"}
_AUTOEQ_FORMS = {"in-ear": "iem", "over-ear": "hp", "earbud": "earbud"}
_FORM_WORDS = [("earbud", re.compile(r"earbud", re.I)),
               ("iem", re.compile(r"\biems?\b|in-ear|\bie\b", re.I)),
               ("hp", re.compile(r"headphone|over-ear|on-ear|\bhp\b|\boe\b", re.I))]


def name_form(text):
    """"iem", "hp" or "earbud" when a name says so ("Harman IE 2019", "… (headphones)"), else ""."""
    return next((form for form, rx in _FORM_WORDS if rx.search(text or "")), "")


def site_form(site):
    """What a database measures: from its group, else its name or address (the 5128 ones hold either)."""
    site = site or {}
    return _FORM_OF_GROUP.get(site.get("group")) or name_form(site.get("name", "") + " " + site.get("url", "").replace("/", " "))


def item_form(it):
    """An entry's device type (a target: the kind it's made for): AutoEq says it by folder, a target's name usually
    does, else its database's kind; "" when nothing says."""
    site = find_site(it.get("site_url")) or {}
    if site.get("short") == "AutoEq" and it.get("kind") == "measurement":
        return _AUTOEQ_FORMS.get((it.get("sub") or "").partition(" · ")[2], "")
    if it.get("kind") == "target":
        return name_form(it.get("name")) or ("" if site.get("short") == "AutoEq" else site_form(site))
    return site_form(site) or name_form(it.get("name"))


def item(item_id):
    with _lock:
        it = _by_id.get(str(item_id))
    if not it:
        raise ValueError("That database entry is gone - refresh the database lists and try again.")
    return it


# ---------------------------------------------------------------- downloading
def _conf_for(it):
    conf = _confs.get(it["site_url"])
    if not conf:
        raise ValueError("Database details missing - refresh the database lists.")
    return conf


_found_in = {}  # site url -> the folder under its data folder its measurements turned out to be in


def download(item_id, count_points):
    """Download one entry into downloads/<database>/. Returns the local file paths (existing copies are reused)."""
    it = item(item_id)
    if it.get("link"):
        raise ValueError(BROWSE_NOTE.format(site=it["site"]))
    folder = os.path.join(DOWNLOAD_DIR, folder_name(it["site"]))
    os.makedirs(folder, exist_ok=True)
    # (another entry of that database has this name: told apart by its file, or for AutoEq's by its address)
    own = (it["ref"].get("file") or hashlib.sha1(it["ref"].get("url", "").encode()).hexdigest()[:6]) if it.get("dup") \
        else ""
    label = folder_name(f"{it['name']}{' [' + own + ']' if own else ''} ({it['tag']})")
    if "url" in it["ref"]:  # AutoEq: one CSV
        tries = [(None, [(it["ref"]["url"], os.path.join(folder, label + ".csv"))])]
    elif it["kind"] == "target":
        conf = _conf_for(it)
        f = urllib.parse.quote(it["ref"]["file"])
        path = os.path.join(folder, folder_name(f"{it['name']} Target ({it['tag']})") + ".txt")
        # (modernGraphTool: targets in their own folder; the graph tool: in targets/ or next to the measurements)
        tries = [(None, [(conf["targets_base"] + f + ".txt", path)])] if conf.get("targets_base") else []
        tries += [(None, [(conf["base"] + "targets/" + f + ".txt", path)]), (None, [(conf["base"] + f + ".txt", path)])]
    else:
        conf = _conf_for(it)
        ref = it["ref"]
        n = ref.get("samples") or conf["samples"]
        samples = [str(k) for k in range(1, n + 1)] or [""]
        # (the channel names come from the site's config: made safe for the local name, like the label)
        mk = lambda sub, smp: [(conf["base"] + sub + urllib.parse.quote(f"{f} {ch}{s}") + ".txt",
                                os.path.join(folder, f"{label}{' ' + str(i + 1) if len(files) > 1 else ''} "
                                                     f"{textfile.safe_name(str(ch), '', max_len=20)}{s}.txt"))
                               for i, f in enumerate(files) for ch in conf["channels"] for s in smp]
        files = ref.get("files") or [ref["file"]]
        # (numbered samples, else one file per channel; some sites' graph tool keeps them in a measurements/ folder)
        subs = sorted(("", "measurements/"), key=lambda sub: sub != _found_in.get(it["site_url"], ""))
        tries = [(sub, mk(sub, smp)) for sub in subs for smp in ([samples, [""]] if samples != [""] else [[""]])]
    if not all(textfile.inside(path, folder) for _, jobs in tries for _, path in jobs):
        raise ValueError(f"{it['site']}'s settings name files outside its download folder: not downloaded.")
    missing = []

    def fetch(job):
        url, path = job
        if os.path.exists(path):  # (a copy from before: used when it's a whole curve, else fetched again)
            try:
                if count_points(textfile.read(path)) >= 32:
                    return path
            except OSError:
                pass
        try:
            text, _ = _get(url)
        except Exception as e:  # noqa: BLE001
            missing.append(getattr(e, "code", None) == 404)
            return None
        if count_points(text) < 32:
            return None
        textfile.write_atomic(path, text)  # (in one step: an interrupted download leaves no half file)
        return path

    with ThreadPoolExecutor(8) as ex:
        for sub, jobs in tries:
            got = [p for p in ex.map(fetch, jobs) if p]
            if got:
                if sub is not None:
                    _found_in[it["site_url"]] = sub  # (tried first next time)
                break
    if not got:
        if net.offline():  # (no copy from before on this PC, and the app may not go online for it)
            raise net.Offline(f"{it['name']} from {it['site']} hasn't been downloaded before, and AutoEQ Studio is "
                              "offline. Switch to Online (top right) to download it.")
        if missing and all(missing):
            raise ValueError(f"{it['site']} lists {it['name']}, but its file isn't on the site (its own graph can't "
                             "show it either). Try another database's measurement of it.")
        raise ValueError(f"Couldn't download {it['name']} from {it['site']}.")
    return sorted(got), it
