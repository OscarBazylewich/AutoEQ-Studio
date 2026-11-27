"""Makes app\\eq\\site_values.json, the table of each graph website's Website values and AutoEQ panel (eq.site_values),
from the websites' own files. Run by hand, never by the app or the tests (it can go online).

    ".venv\\Scripts\\python.exe" "app\\tools\\site_values_survey.py" --fetch <folder>
        reads every graph website the app knows (its lists; not AutoEq on GitHub): each one's page and its config*.js,
        graphtool*.js and equalizer*.js (at most 5 requests a website, one website at a time, a pause between two;
        through the app's own download, which asks net.check first and sends the app's name only), into
        <folder>\\<n>\\ with a meta.json (name, url). A folder already there is kept: run it again to carry on.
    ".venv\\Scripts\\python.exe" "app\\tools\\site_values_survey.py" --from <folder> [--read YYYY-MM-DD] [--out <file>]
        makes the table from such a folder (also the survey's of 2026-11-24, raw\\<n>\\: the same files), and says
        its counts. --read: the day the files were fetched (default: today). --out: default app\\eq\\site_values.json.

Only the values read from the files go into the table: the websites' code (third-party) is never copied into the
app. The folder and its files are yours to delete afterwards.
"""
import argparse
import datetime
import json
import os
import sys
import time

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

FILES = {"page": "page.html", "config": "config.js", "graphtool": "graphtool.js", "equalizer": "equalizer.js"}
PAUSE = 0.3  # seconds between two websites


def read_folder(folder):
    """[{"name", "url", "texts"}] of a folder of fetched websites (<n>\\meta.json and the files)."""
    out = []
    for d in sorted(os.listdir(folder)):
        meta = os.path.join(folder, d, "meta.json")
        if not os.path.isfile(meta):
            continue
        with open(meta, encoding="utf-8") as fh:
            m = json.load(fh)
        texts = {}
        for key, name in FILES.items():
            p = os.path.join(folder, d, name)
            if os.path.isfile(p):
                with open(p, encoding="utf-8", errors="ignore") as fh:
                    texts[key] = fh.read()
        out.append({"name": m.get("name") or m["url"], "url": m["url"], "texts": texts})
    return out


def rows_of(sites):
    """The table's rows: what eq.site_values.parse reads in each website's files."""
    from eq import site_values
    return [dict(name=s["name"], url=s["url"], **site_values.parse(s["texts"])) for s in sites]


def counts(rows):
    """The table's counts, as lines."""
    from collections import Counter
    panels = [r["panel"] for r in rows if r["panel"]]
    lines = [f"websites: {len(rows)}",
             f"all 7 values read: {sum(not r['missing'] for r in rows)}",
             f"AutoEQ code: {dict(Counter(r['code'] for r in rows).most_common())}",
             f"classic AutoEQ panel: {len(panels)} (none or another panel: {len(rows) - len(panels)})",
             f"  with gain boxes: {sum(p['gain_boxes'] for p in panels)}; with Q boxes: {sum(p['q_boxes'] for p in panels)}",
             f"  gain fixed (no gain boxes): {sum(not p['gain_boxes'] for p in panels)}; "
             f"Q fixed (no Q boxes): {sum(not p['q_boxes'] for p in panels)}; "
             f"either: {sum(not (p['gain_boxes'] and p['q_boxes']) for p in panels)}",
             f"  most filter rows below 20: {sum(p['rows_max'] < 20 for p in panels)}",
             f"  fixed gain ranges: {dict(Counter(str(p['gain_range']) for p in panels if not p['gain_boxes']))}",
             f"  fixed Q ranges: {dict(Counter(str(p['q_range']) for p in panels if not p['q_boxes']))}",
             f"  panel clamps where there are boxes (gain, Q): "
             f"{dict(Counter((p['gain_cap'], p['q_cap']) for p in panels if p['gain_boxes'] or p['q_boxes']))}"]
    keys = ("treble_start_from", "scale_smoothing", "smooth_level", "normalization", "norm_hz", "norm_db", "phon_table")
    combos = Counter(tuple(r["values"][k] for k in keys) for r in rows if not r["missing"])
    lines.append(f"different complete sets of the 7 values: {len(combos)}")
    return lines


def make_table(folder, read, out):
    from eq import site_values
    rows = rows_of(read_folder(folder))
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(site_values.table_json(rows, read))
    return rows


def fetch(folder):
    """Every graph website the app knows into folder (see the module's words)."""
    from eq import databases
    os.makedirs(folder, exist_ok=True)
    databases.directory()  # (squig.link's list, saved: the websites beyond the app's own)
    sites = [s for s in databases.all_sites() if s.get("type") != "autoeq"]
    for i, site in enumerate(sites):
        where = os.path.join(folder, f"{i:03d}")
        if os.path.isfile(os.path.join(where, "meta.json")):
            continue
        os.makedirs(where, exist_ok=True)
        meta = {"name": site["name"], "url": site["url"], "error": None}
        try:
            texts = databases.graph_tool_files(site)
            for key, name in FILES.items():
                if texts.get(key):
                    with open(os.path.join(where, name), "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(texts[key])
        except Exception as e:  # noqa: BLE001 - said, and the next website follows
            meta["error"] = f"{type(e).__name__}: {e}"[:200]
        with open(os.path.join(where, "meta.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(meta, fh, indent=1)
        print(i, site["name"], meta["error"] or "ok", flush=True)
        time.sleep(PAUSE)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Makes app\\eq\\site_values.json from the graph websites' files.")
    ap.add_argument("--fetch", metavar="FOLDER")
    ap.add_argument("--from", dest="source", metavar="FOLDER")
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    ap.add_argument("--out", default=os.path.join(APP, "eq", "site_values.json"))
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.fetch:
        fetch(a.fetch)
    if a.source:
        rows = make_table(a.source, a.read, a.out)
        print("\n".join(counts(rows)))
        print("written:", a.out)
    if not (a.fetch or a.source):
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
