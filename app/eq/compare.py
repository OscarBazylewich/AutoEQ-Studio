"""Which measurement of a model to use: every measurement of it (online databases, this PC, the app), ranked.

The biggest factor is the measurement rig: a target is made for one kind of ear simulator (B&K 5128, a 711-type
coupler, GRAS 43AG, HMS), and a measurement from another rig differs from it systematically, mostly above ~2 kHz,
however good it is. The target can be converted for it (rigconv.py: the rigs' average, or the measurement's database's
own conversion), so the rig counts by how much error is left after that, above the usual spread between units and
seatings on one rig. Then: agreement with the other measurements on the same rig (an odd one out usually had a
fit problem), bass that isn't low compared with them (a poor seal loses bass), how many seatings/channels were
averaged, and data quality. The ranking is a recommendation with its reasons shown, not a guarantee: units vary,
and your own fit and tips matter too.
"""
import hashlib
import os
import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import databases
from . import engines
from . import inputs
from . import library
from . import rigconv
from . import rigmap
from . import rigs
import textfile
from .rigs import RIGS


# ---------------------------------------------------------------- finding every measurement of a model
def _tokens(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def matches(query, name):
    """All the words of the query appear in the name (spacing and capitals ignored: "Blessing 2" = "Blessing2"; that
    only for a query of two words or four letters: "S12" alone is inside "KZ ZS12" and many more)."""
    q, n = _tokens(query), _tokens(name)
    return bool(q) and (all(t in n for t in q) or ((len(q) > 1 or len(q[0]) >= 4) and "".join(q) in "".join(n)))


def clean_query(name):
    """A device name without channel/seating suffixes or a trailing "(source)"."""
    name = re.sub(r"\s*\((?:[^()]*)\)\s*$", "", name).strip()
    m = inputs.CHANNEL_RE.match(name)
    return (m.group(1) if m and m.group(1).strip() else name).strip()


def files_rig(group, recorded):
    """(rig key or None, sure) of your own files of a measurement (in the app or on this PC), worked out as Make an
    EQ's Measurement card and Find…'s rig tags work it out (rigs.file_rig: where the app downloaded a file, else its
    database's download folder or "(database)" tag in its name, else a rig its name says): the one rig its files have
    (any not known left out), or none when they have more than one. recorded: rigs.sources().
    (The recheck, 2026-10-23: only the record of where the app downloaded a file counted here, so the app's own
    sample measurement, from listener800's 5128 IEMs, was "rig not known", and Which measurement warned that none was
    measured on the B&K 5128 while the Measurement card said "measured on 5128".)"""
    found = [rigs.file_rig(os.path.basename(f), group["folder"], recorded) for f in group.get("files") or []]
    known = {rig for rig, _sure in found if rig}
    if len(known) != 1:
        return None, False
    rig = known.pop()
    return rig, all(sure for r, sure in found if r == rig)


def candidates(query, limit=40, links=None):
    """Every measurement whose name matches: online database entries, then files on this PC and in the app (not the
    copies of database entries in the downloads folder), yours with the rig the rest of the app gives them
    (files_rig). Entries that can't be downloaded go into links (their page) instead. At most `limit`: yours all, the
    database's (whole-word matches first) up to the rest."""
    out = []
    for it in databases.items():
        if it["kind"] == "measurement" and matches(query, it["name"]):
            if it.get("link"):  # can't be downloaded: listed with its page link instead
                if links is not None:
                    links.append({"name": it["name"], "site": it["site"], "rig": RIGS.get(rigs.source_rig(it)[0]), "link": it["link"]})
                continue
            rig, sure = rigs.source_rig(it)
            f = (it.get("ref") or {}).get("file")
            nt = _tokens(it["name"])
            extra = [w for w in _tokens(f or "") if w.isalpha() and len(w) >= 3 and not any(n.startswith(w) or w.startswith(n) for n in nt)]
            variant = f if extra else ""
            out.append({"src": "db", "id": it["id"], "name": it["name"], "source": it.get("tag") or it["site"],
                        "site": it["site"], "rig": rig, "sure": sure, "variant": variant, "unit": rigmap.unit_key(it)})
    whole = lambda c: all(t in _tokens(c["name"]) for t in _tokens(query))
    out.sort(key=lambda c: not whole(c))  # (whole-word matches first, then "Blessing2" for "Blessing 2")
    local = []
    recorded = rigs.sources()
    for g in library.status(with_items=True).get("items", []):
        if g["kind"] != "measurement" or not matches(query, g["name"]):
            continue
        if textfile.inside(g["folder"], databases.DOWNLOAD_DIR):
            continue  # copies of database entries, found above
        rig, sure = files_rig(g, recorded)
        unit = rigs.file_unit(os.path.basename(g["files"][0]), g["folder"], recorded) if g.get("files") else None
        local.append({"src": "pc", "id": g["id"], "name": g["name"], "source": "in the app" if g.get("in_app") else "this PC",
                      "site": g["folder"], "rig": rig, "sure": sure, "files": g["files"], "variant": "", "unit": unit})
    # (yours never cut: past 40 database matches they were, the one in use too)
    return out[:max(0, limit - len(local))] + local


# ---------------------------------------------------------------- analysis
def _grid():  # squiglink's frequency grid (graphtool.js f_values), which preview_curve returns values on
    f = [20.0]
    while f[-1] < 20000:
        f.append(f[-1] * 2 ** (1 / 48))
    return np.array(f)


F = _grid()


def _band(lo, hi):
    return (F >= lo) & (F <= hi)


def _fetch(c):
    if c["src"] == "db":
        paths, _ = databases.download(c["id"], lambda text: (library.sniff_text(text) or {"points": 0})["points"])
    else:
        paths = c["files"]
    return {**c, "paths": paths}


def _load(c, cfg):
    paths = c["paths"]
    texts = [inputs.read_text(p) for p in paths]
    info = [library.sniff_text(t) or {"points": 0, "fmin": 0, "fmax": 0} for t in texts]
    chans = set()
    for p in paths:
        m = inputs.CHANNEL_RE.match(os.path.splitext(os.path.basename(p))[0])
        if m:
            chans.add(m.group(2)[0].upper())
    vals = np.array(engines.preview_curve(cfg, texts), dtype=float)
    return {**c, "hash": hashlib.sha1("".join(sorted(texts)).encode()).hexdigest(), "vals": vals,
            "n_files": len(paths), "channels": "".join(sorted(chans)),
            "points": min(i["points"] for i in info), "fmin": min(i["fmin"] for i in info),
            "fmax": max(i["fmax"] for i in info)}


def compare(cfg, query, target, rig_override=None, progress=None):
    """Every measurement of the model, levelled together and ranked for the target (score()). rig_override: the
    target's rig chosen by the user ("none": ignore the rig)."""
    tgt_rig, how = (rig_override, "chosen by you") if rig_override else rigs.target_rig(target or "")
    if rig_override == "none":
        tgt_rig, how = None, "chosen by you"
    links = []
    cands = candidates(query, links=links)
    if not cands:
        return {"query": query, "target": target, "target_rig": tgt_rig, "how": how, "items": [], "links": links,
                "note": "No measurements with that name were found" + (" that the app can download." if links else ".")}
    loaded, errors = [], []
    with ThreadPoolExecutor(6) as ex:  # downloads in parallel; the levelling (V8) one at a time
        futs = [ex.submit(_fetch, c) for c in cands]
        for i, f in enumerate(futs):
            try:
                loaded.append(_load(f.result(), cfg))
            except Exception as e:  # noqa: BLE001 - one bad entry shouldn't stop the rest
                errors.append(f"{cands[i]['name']} ({cands[i]['source']}): {e}")
            if progress:
                progress(i + 1, len(futs))
    # the same file in several places (a database copy in the app, on this PC …) counts once
    seen, items = {}, []
    for c in loaded:
        if c["hash"] in seen:
            seen[c["hash"]]["also"].append(c["source"])
            continue
        c["also"] = []
        seen[c["hash"]] = c
        items.append(c)
    # align levels (the site's own levelling, then the 200 Hz - 2 kHz average), compare within each rig
    mid = _band(200, 2000)
    for c in items:
        c["vals"] = c["vals"] - np.mean(c["vals"][mid])
    groups = {}
    for c in items:
        groups.setdefault(c["rig"], []).append(c)
    body, bass = _band(20, 8000), _band(20, 150)
    for rig, g in groups.items():
        med = np.median(np.array([c["vals"] for c in g]), axis=0) if len(g) >= 2 else None
        for c in g:
            c["peers"] = len(g) - 1
            if med is None or rig is None:
                c["dev"] = c["bass"] = None
                continue
            others = np.median(np.array([o["vals"] for o in g if o is not c]), axis=0)  # (a pair: the other one)
            c["dev"] = float(np.sqrt(np.mean((c["vals"][body] - others[body]) ** 2)))
            c["bass"] = float(np.mean(c["vals"][bass] - others[bass]))
    enabled = bool(cfg.get("rig_convert", {}).get("enabled", True))
    for c in items:  # how close each can get to the target's rig (converted for it, when it can be)
        dev = rigconv.device(c["rig"], tgt_rig, os.path.basename(target or ""), c["site"])
        c["conv"] = rigconv.expected(dev, tgt_rig, c["rig"], c.get("unit"), enabled) if tgt_rig else None
        score(c, tgt_rig)
    items.sort(key=lambda c: -c["score"])
    _LAST.clear()
    _LAST.update({c["hash"]: c for c in items})  # for averaging some of them afterwards
    out = []
    for c in items:
        body_ = {"src": "db", "id": c["id"]} if c["src"] == "db" else {"src": "pc", "id": c["id"]}
        out.append({k: c[k] for k in ("src", "id", "name", "source", "site", "rig", "sure", "n_files", "channels",
                                      "points", "dev", "bass", "score", "reasons", "also", "peers", "variant", "hash")}
                   | {"rig_name": RIGS.get(c["rig"], "unknown rig"), "body": body_,
                      "vals": [round(float(v), 2) for v in c["vals"][::2]]})
    same = sum(1 for c in items if tgt_rig and c["rig"] == tgt_rig)
    conv = sum(1 for c in items if (c.get("conv") or {}).get("how") in ("own", "rigs"))
    note = ""
    if not items:  # (every one failed to load: offline with nothing downloaded before, or their sites didn't answer)
        note = ("None of them could be loaded (the reasons are below). Measurements from the online databases are "
                "downloaded when compared: that needs the internet (Online, at the top right), and their sites must "
                "answer. Try again later.")
    elif tgt_rig and not same and conv:
        note = (f"None of these was measured on the {RIGS[tgt_rig]}, the rig your target is made for. The target is converted "
                f"for {conv} of them; the error that leaves is in their reasons.")
    elif tgt_rig and not same:
        note = (f"None of these was measured on the {RIGS[tgt_rig]}, the rig your target is made for, so every one will "
                f"be off above about 2 kHz. A target made for {items[0]['rig'] and RIGS.get(items[0]['rig']) or 'their rig'} "
                "would suit them better.")
    return {"query": query, "target": target, "target_rig": tgt_rig, "target_rig_name": RIGS.get(tgt_rig), "how": how,
            "items": out, "errors": errors, "note": note, "f": [round(f, 2) for f in F[::2]], "links": links}


# ---------------------------------------------------------------- averaging measurements made on the same rig
_LAST = {}  # the last comparison's measurements by file hash, with their levelled curves


def average(keys, name):
    """One measurement from several of the last comparison's, all made on the same rig: each one levelled (the site's
    levelling, then the 200 Hz - 2 kHz average), then averaged in dB with equal weight per measurement (a source with
    ten seatings counts once, like one with two). Returns (file name, text, rig, what it's made of)."""
    got = [_LAST[k] for k in keys if k in _LAST]
    if len(got) < 2:
        raise ValueError("Choose at least two measurements (compare again if the list has changed).")
    found = {c["rig"] for c in got}
    if len(found) != 1 or None in found:
        raise ValueError("Only measurements made on the same, known rig can be averaged.")
    rig = found.pop()
    vals = np.mean(np.array([c["vals"] for c in got]), axis=0)
    of = [f"{c['name']} ({c['source']})" for c in got]
    fname = textfile.safe_name(f"{name} (average of {len(got)}, {rig}).txt", "Average.txt")  # (as add_file will)
    text = (f"* Average of {len(got)} measurements on the {RIGS[rig]}, made with AutoEQ Studio\n"
            + "".join(f"*   {o}\n" for o in of)
            + "* each levelled over 200 Hz - 2 kHz first, then averaged in dB with equal weight\n"
            + "".join(f"{f:.2f}\t{v:.3f}\n" for f, v in zip(F, vals)))
    return fname, text, rig, of


def score(c, tgt_rig):
    """0-100 with the reasons: rig 40, agreement 25, bass/seal 15, averaging 10, data 10."""
    r, pts = [], 0.0
    if tgt_rig is None:
        pts += 20
        r.append(("·", "Target's rig unknown: rig not scored"))
    elif (c.get("conv") or {}).get("how") in ("own", "rigs"):
        # converted for the target's rig: full points when that leaves no more than the usual spread between units on
        # one rig, none when the rig still adds 4 dB; a little under a measurement on the target's own rig
        x = c["conv"]
        p = min(38.0, 40 * max(0.0, 1 - x["rig_part"] / 4))
        pts += p
        with_ = f"a conversion made for {c['source']}" if x["how"] == "own" else f"the rigs' average ({x['models']} models)"
        head = ("Same rig as your target, but its source measures a little differently; the target is converted for it with" if c["rig"] == tgt_rig
                else f"Measured on {'a ' + RIGS[c['rig']] if c['rig'] else 'a rig the app doesn’t know'}; the target is converted for it with")
        left = f"about {x['error']:.1f} dB left, 1–10 kHz" + ("" if x["enabled"] else ", without converting (it's off)")
        r.append(("+" if p >= 30 else "·" if p >= 15 else "−", f"{head} {with_} ({left})"))
    elif c["rig"] == tgt_rig:
        pts += 40
        r.append(("+", f"Same rig as your target ({RIGS[tgt_rig]})" + ("" if c["sure"] else ", as usual for this source")))
    elif c["rig"] is None:
        pts += 12
        r.append(("·", "Rig not known"))
    else:
        r.append(("−", f"Different rig ({RIGS[c['rig']]}) from your target's ({RIGS[tgt_rig]}), and no data to convert between them"))
    if c["dev"] is None:
        pts += 12.5
        if c["rig"] is not None:
            r.append(("·", "No other measurement on the same rig to compare with"))
    else:
        pts += 25 * max(0.0, 1 - c["dev"] / 3)
        word = "close to" if c["dev"] < 1 else "fairly close to" if c["dev"] < 2 else "unlike"
        r.append(("+" if c["dev"] < 1.5 else "−", f"{word.capitalize()} the other {c['peers']} on its rig ({c['dev']:.1f} dB apart)"))
    if c["bass"] is None:
        pts += 10
    else:
        pts += 15 * max(0.0, 1 - max(0.0, -c["bass"] - 0.5) / 4)
        if c["bass"] < -1.5:
            r.append(("−", f"Bass {-c['bass']:.1f} dB below the others: probably a poor seal"))
        elif c["bass"] > -0.5:
            r.append(("+", "Full bass (good seal)"))
    pts += 10 * min(1.0, np.log2(c["n_files"] + 1) / np.log2(11))
    if c["n_files"] >= 4:
        r.append(("+", f"{c['n_files']} seatings/channels averaged"))
    elif c["n_files"] == 1:
        r.append(("·", "One file (a single seating, or already averaged by the source)"))
    q = 0.0
    q += 5 if c["fmin"] <= 25 and c["fmax"] >= 16000 else 2 if c["fmax"] >= 12000 else 0
    q += 3 if c["points"] >= 200 else 1 if c["points"] >= 64 else 0
    q += 2 if ("L" in c["channels"] and "R" in c["channels"]) or c["n_files"] == 1 else 0
    pts += q
    if c["fmax"] and c["fmax"] < 16000:
        r.append(("−", f"Stops at {c['fmax'] / 1000:.0f} kHz"))
    c["score"] = round(pts, 1)
    c["reasons"] = r
