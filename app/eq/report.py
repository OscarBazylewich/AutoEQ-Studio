"""Standalone HTML report: result cards, error tables and an interactive plot (no dependencies)."""
import html
import json
import math

import textfile

W, H = 880, 420
ML, MR, MT, MB = 52, 16, 16, 40
COLORS = ["var(--c1)", "var(--c2)", "var(--c3)"]


def filter_table(filters):
    rows = "".join(
        f"<tr><td>{i + 1}</td><td>{f.get('type', 'PK')}</td><td>{f['freq']}</td><td>{f['gain']:.1f}</td>"
        f"<td>{f['q']:g}</td></tr>" for i, f in enumerate(filters) if f.get("enabled", True))
    return ('<table class="ft"><thead><tr><th>#</th><th>Type</th><th>Frequency (Hz)</th><th>Gain (dB)</th>'
            f'<th>Q</th></tr></thead><tbody>{rows}</tbody></table>')


def grid_table(results, row_label, ear_db, sub):
    cells = {}
    for r in results:
        k = (r["rows"], r["q_max"])
        if k not in cells or r["rms"] < cells[k]["rms"]:
            cells[k] = r
    qs = sorted({r["q_max"] for r in results})
    head = "".join(f"<th>Q max {q:g}</th>" for q in qs)
    body = ""
    for rv in sorted({r["rows"] for r in results}):
        tds = ""
        for q in qs:
            c = cells.get((rv, q))
            if c is None:
                tds += "<td>–</td>"
                continue
            cls = ' class="ok"' if c.get("ear") is not None and c["ear"] <= ear_db else ""
            tds += f'<td{cls}>{c["rms"]:.2f}<span class="sub">{html.escape(sub(c))}</span></td>'
        body += f"<tr><th>{rv}</th>{tds}</tr>"
    return f'<table class="grid-t"><thead><tr><th>{row_label}</th>{head}</tr></thead><tbody>{body}</tbody></table>'


def write(path, *, title, subtitle, curves, band, cards, grids=(), notes=""):
    """cards: [{"title", "badge", "fields": [(k, v)], "text", "filters", "eq", "rms"}]; grids: [(title, html, note)]"""
    f = curves["f"]
    series = [("m", "Measured", curves["meas"], "var(--meas)", True),
              ("t", "Target", curves["target"], "var(--tgt)", True)]
    for i, c in enumerate(cards[:3]):
        series.append((f"r{i}", f"{c['title']} ({c['rms']:.2f} dB)", c["eq"], COLORS[i], False))

    allv = [v for s in series for v in s[2]]
    y1 = 5 * math.ceil((max(allv) + 2) / 5)
    y0 = max(5 * math.floor((min(allv) - 2) / 5), y1 - 60)
    x0, x1 = math.log10(20), math.log10(20000)
    X = lambda fr: ML + (math.log10(fr) - x0) / (x1 - x0) * (W - ML - MR)
    Y = lambda v: MT + (y1 - min(max(v, y0), y1)) / (y1 - y0) * (H - MT - MB)
    path_d = lambda vals: "M" + " L".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(f, vals))
    grid = []
    for fr in [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]:
        lab = f"{fr // 1000}k" if fr >= 1000 else str(fr)
        grid.append(f'<line class="grid" x1="{X(fr):.1f}" x2="{X(fr):.1f}" y1="{MT}" y2="{H - MB}"/>'
                    f'<text class="tick" x="{X(fr):.1f}" y="{H - MB + 16}" text-anchor="middle">{lab}</text>')
    for v in range(y0, y1 + 1, 5):
        grid.append(f'<line class="grid" x1="{ML}" x2="{W - MR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                    f'<text class="tick" x="{ML - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    shade = ""
    if band[1] < 20000:
        shade = (f'<rect class="shade" x="{X(band[1]):.1f}" y="{MT}" width="{X(20000) - X(band[1]):.1f}" '
                 f'height="{H - MT - MB}"/><text class="tick" x="{(X(band[1]) + X(20000)) / 2:.1f}" y="{MT + 14}" '
                 f'text-anchor="middle">not scored</text>')
    dash = ' stroke-dasharray="6 4"'  # (outside the f-string: Python before 3.12 allows no backslash in one)
    paths = "".join(f'<path class="s" id="p-{k}" d="{path_d(c)}" stroke="{col}"'
                    f'{dash if k == "t" else ""}/>' for k, _, c, col, _ in series)
    legend = "".join(f'<label><input type="checkbox" data-s="{k}" checked><span class="sw" style="border-color:{col};'
                     f'{"border-top-style:dashed" if k == "t" else ""}"></span>{html.escape(lbl)}</label>'
                     for k, lbl, _, col, _ in series)
    data_js = json.dumps({"f": [round(float(v), 2) for v in f],
                          **{k: [round(float(v), 2) for v in c] for k, _, c, _, _ in series},
                          "names": {k: lbl.rsplit(" (", 1)[0] if k.startswith("r") else lbl for k, lbl, _, _, _ in series}}).replace("</", "<\\/")
    # (a name with "</script>" in it can't end the script: "<\/" is the same text to JavaScript)

    card_html = ""
    for c in cards:
        fields = "".join(f'<div class="field"><div class="k">{html.escape(k)}</div><div class="v">{html.escape(str(v))}'
                         f'</div></div>' for k, v in c.get("fields", []))
        badge = f' <span class="pill">{html.escape(c["badge"])}</span>' if c.get("badge") else ""
        card_html += (f'<div class="card"><h3>{html.escape(c["title"])}{badge}</h3>'
                      f'{f"<div class=fields>{fields}</div>" if fields else ""}'
                      f'<p class="note">{c.get("text", "")}</p>{filter_table(c["filters"])}</div>')
    grid_html = "".join(f'<h2>{html.escape(t)}</h2><div class="card scroll">{g}<p class="note">{n}</p></div>'
                        for t, g, n in grids)

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: light; --bg:#fcfcfb; --card:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --muted:#8a8984; --line:#e4e3de;
  --meas:#eb6834; --c1:#2a78d6; --c2:#1baf7a; --c3:#4a3aa7; --tgt:#52514e; --ok:#e3eefb; --shade:#f3f2ee; --pill:#eef5ea; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ color-scheme: dark; --bg:#141413; --card:#1a1a19; --ink:#ffffff;
  --ink2:#c3c2b7; --muted:#8f8e86; --line:#34332f; --meas:#d95926; --c1:#3987e5; --c2:#199e70; --c3:#9085e9; --tgt:#c3c2b7; --ok:#1c3350; --shade:#20201e; --pill:#1f3325; }} }}
:root[data-theme="dark"] {{ color-scheme: dark; --bg:#141413; --card:#1a1a19; --ink:#ffffff; --ink2:#c3c2b7; --muted:#8f8e86; --line:#34332f;
  --meas:#d95926; --c1:#3987e5; --c2:#199e70; --c3:#9085e9; --tgt:#c3c2b7; --ok:#1c3350; --shade:#20201e; --pill:#1f3325; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:960px; margin:0 auto; padding:24px 16px 48px; }}
h1 {{ font-size:24px; margin:0 0 4px }} h2 {{ font-size:18px; margin:32px 0 8px }} h3 {{ font-size:16px; margin:0 0 8px }}
p.lead {{ color:var(--ink2); margin:0 0 20px }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }}
.two {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px }}
.fields {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-bottom:8px }}
.field .k {{ color:var(--ink2); font-size:13px }} .field .v {{ font-size:18px; font-weight:600; font-variant-numeric:tabular-nums }}
.pill {{ font-size:12px; font-weight:500; background:var(--pill); color:var(--ink2); border-radius:99px; padding:2px 8px; margin-left:6px }}
table {{ border-collapse:collapse; font-variant-numeric:tabular-nums; }}
.ft th, .ft td {{ padding:4px 12px; text-align:right; border-bottom:1px solid var(--line) }}
.ft th {{ color:var(--ink2); font-weight:500; font-size:13px }}
.grid-t th, .grid-t td {{ padding:6px 10px; text-align:center; border:1px solid var(--line) }}
.grid-t td.ok {{ background:var(--ok) }} .sub {{ display:block; font-size:11px; color:var(--muted) }}
.note {{ color:var(--ink2); font-size:14px }}
svg {{ width:100%; height:auto; display:block }}
.grid {{ stroke:var(--line); stroke-width:1 }} .tick {{ fill:var(--muted); font-size:11px }} .shade {{ fill:var(--shade) }}
path.s {{ fill:none; stroke-width:2; stroke-linejoin:round }}
.legend {{ display:flex; flex-wrap:wrap; gap:16px; margin:0 0 8px; font-size:13px; color:var(--ink2) }}
.legend label {{ display:flex; align-items:center; gap:6px; cursor:pointer }}
.sw {{ width:18px; height:0; border-top:2px solid }}
#tip {{ position:absolute; pointer-events:none; background:var(--card); border:1px solid var(--line); border-radius:6px;
  padding:6px 8px; font-size:12px; font-variant-numeric:tabular-nums; display:none; white-space:nowrap; box-shadow:0 2px 8px rgba(0,0,0,.12) }}
.plotwrap {{ position:relative }} .scroll {{ overflow-x:auto }}
</style></head><body><main>
<h1>{html.escape(title)}</h1>
<p class="lead">{subtitle}</p>
<div class="two">{card_html}</div>
<h2>Frequency response</h2>
<div class="card">
  <div class="legend" id="legend">{legend}</div>
  <div class="plotwrap">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Frequency response: measurement, target and EQ results">
    {shade}{"".join(grid)}
    <text class="tick" x="{ML}" y="{H - 4}">Hz</text><text class="tick" x="4" y="{MT + 4}">dB</text>
    {paths}
    <line id="cross" y1="{MT}" y2="{H - MB}" stroke="var(--muted)" stroke-width="1" style="display:none"/>
    <rect id="hit" x="{ML}" y="{MT}" width="{W - ML - MR}" height="{H - MT - MB}" fill="transparent"/>
  </svg>
  <div id="tip"></div>
  </div>
  <p class="note">EQ'd curves shown before pre-amp.</p>
</div>
{grid_html}
{f'<h2>Notes</h2><div class="card note">{notes}</div>' if notes else ""}
</main>
<script>
const D = {data_js};
const W={W},H={H},ML={ML},MR={MR},MT={MT},MB={MB},x0=Math.log10(20),x1=Math.log10(20000);
const vis = {{}}; Object.keys(D.names).forEach(k=>vis[k]=true);
document.querySelectorAll('#legend input').forEach(cb=>cb.addEventListener('change',()=>{{
  vis[cb.dataset.s]=cb.checked; document.getElementById('p-'+cb.dataset.s).style.display=cb.checked?'':'none'; }}));
const svg=document.querySelector('svg'), hit=document.getElementById('hit'), cross=document.getElementById('cross'), tip=document.getElementById('tip');
hit.addEventListener('mousemove', ev => {{
  const pt=svg.createSVGPoint(); pt.x=ev.clientX; pt.y=ev.clientY; const p=pt.matrixTransform(svg.getScreenCTM().inverse());
  const fr=Math.pow(10, x0+(p.x-ML)/(W-ML-MR)*(x1-x0));
  let i=0; while(i<D.f.length-1 && D.f[i+1]<fr) i++;
  const X=ML+(Math.log10(D.f[i])-x0)/(x1-x0)*(W-ML-MR);
  cross.setAttribute('x1',X); cross.setAttribute('x2',X); cross.style.display='';
  tip.textContent=''; const b=document.createElement('b');  // (as text: the names are yours, "<" and "&" included)
  b.textContent=D.f[i]>=1000?(D.f[i]/1000).toFixed(2)+' kHz':D.f[i].toFixed(0)+' Hz'; tip.appendChild(b);
  for(const k of Object.keys(D.names)) if(vis[k]) {{ tip.appendChild(document.createElement('br'));
    tip.appendChild(document.createTextNode(D.names[k]+': '+D[k][i].toFixed(1)+' dB')); }}
  tip.style.display='block';
  const box=svg.getBoundingClientRect(), px=(X/W)*box.width;
  tip.style.left=(px>box.width*0.6? px-tip.offsetWidth-10 : px+10)+'px'; tip.style.top='10px';
}});
hit.addEventListener('mouseleave',()=>{{tip.style.display='none';cross.style.display='none';}});
</script>
</body></html>"""
    textfile.write_atomic(path, page)  # (in one step, like the EQ files)


def site_fields(r):
    return [("Filter rows", r["rows"]), ("Frequency Range", f"{r['freq_low']} to {r['freq_high']}"),
            ("Gain Range", f"{r['gain_min']} to {r['gain_max']}"), ("Q Range", f"{r['q_min']:g} to {r['q_max']:g}")]


def grids_for(mode, results, ear_db, best_rms):
    """The error grid for the report; shaded: the results that sound the same as the target (ear error within
    ear_db, the audible pick's rule)."""
    same = (f"Shaded = sounds the same as the target (within {ear_db:g} dB, as the ear hears it); the best "
            f"{best_rms:.2f} dB.")
    if mode == "site_sweep":
        return [("Website AutoEQ: error by filter rows and max Q",
                 grid_table(results, "Rows", ear_db, lambda c: f"{c['freq_high'] // 1000}k · {c['n_filters']}f"),
                 "Lowest error per cell across the frequency and gain ranges tried; small print = high end of the "
                 "frequency range and filters produced. " + same)]
    if mode == "best_fit":
        return [("Best fit: error by filter count and max Q",
                 grid_table(results, "Filters", ear_db, lambda c: f"max +{c['max_boost']:g} dB"),
                 "Lowest error per cell across the max-boost limits tried; small print = largest boost used. " + same)]
    return []
