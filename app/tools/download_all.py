"""Download every curve of every online database AutoEQ Studio lists into its downloads folder (the user's ask,
2026-10-09), so Find… and Use have them all offline. Run it again to fetch what's new or failed: a complete copy
already there is reused, not fetched again.

    ".venv\\Scripts\\python.exe" "app\\tools\\download_all.py" [--only <text>] [--dry-run]

It uses the database lists the app already has (data\\eq\\cache\\databases.json: refresh them in Find… › Sources
first for the newest), and the app's own download (eq\\databases.download): the same files and names as Use. Kind to
the sites: one entry at a time per website (each address: every reviewer's *.squig.link is a site of its own), a
short pause between entries, three websites at once. List-only databases (sites that don't let other programs download, "link" entries) are
skipped. Progress and what failed go to data\\download_all.log; Ctrl+C stops it (run it again to carry on).
"""
import collections
import os
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

PAUSE = 0.3      # seconds between two entries of one website
AT_ONCE = 3      # websites downloaded from at the same time (each entry fetches its few files together)


def domain(url):
    return urllib.parse.urlparse(url).hostname or url


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from eq import databases, engines
    import paths
    log_path = os.path.join(paths.DATA, "download_all.log")
    cache = databases.load_cache()
    names = {databases.norm_url(s["url"]): s["name"] for s in databases.all_sites()}
    entries = []
    for url, c in cache.items():
        if not isinstance(c, dict):
            continue
        name = names.get(databases.norm_url(url)) or url
        entries += [dict(it, site=name, site_url=url) for it in c.get("items") or []]
    databases.assign_ids(entries)
    databases.keep_confs(cache)
    databases.set_items(entries)
    only = sys.argv[sys.argv.index("--only") + 1].lower() if "--only" in sys.argv else ""
    todo = [it for it in entries if not it.get("link") and only in (it["site"] + " " + it["site_url"]).lower()]
    by_domain = collections.defaultdict(list)
    for it in todo:
        by_domain[domain(it["site_url"])].append(it)
    print(f"{len(entries)} entries in {len(cache)} databases; {len(entries) - len(todo)} skipped (list-only"
          f"{' or not matching --only' if only else ''}); {len(todo)} to get, from {len(by_domain)} websites.")
    if "--dry-run" in sys.argv:
        for d, its in sorted(by_domain.items(), key=lambda x: -len(x[1]))[:20]:
            print(f"  {len(its):6}  {d}")
        return 0
    count = collections.Counter()
    failed = []
    lock = threading.Lock()
    stop = threading.Event()
    t0 = time.time()
    log = open(log_path, "a", encoding="utf-8", buffering=1)
    log.write(f"\n==== {time.strftime('%Y-%m-%d %H:%M')}: {len(todo)} entries from {len(by_domain)} websites\n")

    def say_progress():
        n = sum(count.values())
        rate = n / max(1, time.time() - t0)
        left = (len(todo) - n) / rate if rate else 0
        line = (f"{n}/{len(todo)}  got {count['got']}, failed {count['failed']}  ·  "
                f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))} so far, about "
                f"{time.strftime('%H:%M', time.gmtime(left))} (h:m) to go")
        print(line, flush=True)
        log.write(line + "\n")

    def one_site(its):
        for it in its:
            if stop.is_set():
                return
            try:
                databases.download(it["id"], engines.count_points)
                kind = "got"
            except Exception as e:  # noqa: BLE001 - said in the log, the rest goes on
                kind = "failed"
                with lock:
                    failed.append(f"{it['site']} · {it['name']}: {e}")
                    log.write(f"FAILED {it['site']} · {it['name']}: {e}\n")
            with lock:
                count[kind] += 1
                if sum(count.values()) % 250 == 0:
                    say_progress()
            time.sleep(PAUSE)

    ex = ThreadPoolExecutor(AT_ONCE)  # (not "with": its exit waited for every site's whole list before Ctrl+C stopped)
    try:
        list(ex.map(one_site, sorted(by_domain.values(), key=len, reverse=True)))
    except KeyboardInterrupt:
        stop.set()  # (first: each worker stops after the entry it's on)
        print("Stopping: run it again to carry on (what's downloaded is kept).")
    finally:
        ex.shutdown(wait=True, cancel_futures=True)
    say_progress()
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(databases.DOWNLOAD_DIR) for f in fs)
    summary = (f"Done: {count['got']} entries downloaded or already there, {count['failed']} failed (listed in "
               f"{log_path}). The downloads folder holds {size / 2**20:.0f} MB.")
    print(summary)
    log.write(summary + "\n")
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
