#!/usr/bin/env python3
"""Build fixtures.html: BABA-compliant fixtures from state DOT lists, with .ies files and cut sheets.

Reads data/fixtures.json and shows only the fixtures that match its "filter" block
(for now 3000K, 480V, 70 CRI). Photometric files live in ies/<manufacturer>/.

Usage: python3 scripts/build_fixtures.py [--date YYYY-MM-DD]
Standard library only.
"""

import argparse
import datetime as dt
import json
import pathlib

from build_site import CSS, STATE_NAMES, e, link

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

STATUS_BADGE = {
    "Compliant v5": ("Compliant v5 · Phase 2", "ok"),
    "Compliant v4": ("Compliant v4 · Phase 1", "warn"),
}

EXTRA_CSS = """
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.chip{background:var(--info-bg);color:var(--info);border-radius:999px;padding:2px 10px;font-size:.82rem;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}
@media (max-width:420px){.grid{grid-template-columns:1fr}}
.fx{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px;min-width:0}
.fx h3{margin:0;font-size:1.02rem}
.cat{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.82rem;word-break:break-all;
background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 8px}
.kv{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;font-size:.85rem}
.kv dt{color:var(--muted)}.kv dd{margin:0;min-width:0;overflow-wrap:anywhere}
.files{display:flex;flex-direction:column;gap:4px;font-size:.88rem}
.files a.dl{font-weight:600}
.caveat{font-size:.82rem;color:var(--warn);background:var(--warn-bg);border-radius:6px;padding:6px 8px}
details summary{cursor:pointer;color:var(--muted);font-size:.82rem}
"""

JS = """
const q=document.getElementById('q'),ty=document.getElementById('type');
function apply(){const t=q.value.trim().toLowerCase(),y=ty.value;let n=0;
document.querySelectorAll('.fx[data-search]').forEach(c=>{
const ok=(!t||c.dataset.search.includes(t))&&(!y||c.dataset.type===y);c.hidden=!ok;if(ok)n++;});
document.getElementById('count').textContent=n;}
q.addEventListener('input',apply);ty.addEventListener('change',apply);
"""


def matches(fx, flt):
    return all(fx.get(k) == v for k, v in flt.items())


def ies_links(fx):
    out = []
    for f in fx.get("ies", []):
        local = f.get("file")
        label = pathlib.Path(local).name if local else (f.get("label") or "IES file")
        if local and (ROOT / local).exists():
            main = f'<a class="dl" href="{e(local)}" download>⬇ {e(label)}</a>'
        else:
            main = link(f.get("source_url"), label)
        meta = " · ".join(x for x in [
            f.get("lumcat") and f"LUMCAT {f['lumcat']}",
            f.get("lumens") and f"{f['lumens']:,} lm",
            f.get("watts") and f"{f['watts']} W",
        ] if x)
        src = f' · {link(f["source_url"], "source")}' if f.get("source_url") and local else ""
        note = f'<div class="muted small">{e(f["note"])}</div>' if f.get("note") else ""
        out.append(f"<div>{main}<div class='muted small'>{e(meta)}{src}</div>{note}</div>")
    if not out:
        out.append('<div class="muted">No 3000K .ies published — request from manufacturer.</div>')
    return "".join(out)


def card(fx, sources):
    d = fx["dot"]
    src = sources.get(d["source"], {})
    label, tone = STATUS_BADGE.get(d.get("status"), (d.get("status"), "muted"))
    sheet = fx.get("cut_sheet") or {}
    search = " ".join([fx.get("manufacturer", ""), fx.get("brand", ""), fx.get("family", ""),
                       fx.get("catalog", ""), d.get("listed_catalog", ""), d.get("application", ""),
                       src.get("state", ""), STATE_NAMES.get(src.get("state", ""), "")]).lower()
    specs = [
        ("DOT use", d.get("application")),
        ("Optics", fx.get("distribution")),
        ("Input", fx.get("watts") and f"{fx['watts']} W"),
        ("Output", fx.get("lumens") and f"{fx['lumens']:,} lm"),
        ("CCT / CRI", f"{fx['cct']}K · {fx['cri']} CRI"),
        ("Voltage", f"{fx['voltage']}V"),
    ]
    kv = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in specs if v)
    caveats = "".join(f'<div class="caveat">{e(c)}</div>' for c in fx.get("caveats", []))
    return f"""<article class="fx" data-search="{e(search)}" data-type="{e(fx.get('product_type'))}">
<div class="muted small">{e(fx.get('manufacturer'))}{' · ' + e(fx['brand']) if fx.get('brand') else ''}</div>
<h3>{e(fx.get('family'))}</h3>
<div><span class="badge {tone}">{e(label)}</span> <span class="small"><strong>{e(src.get('state'))}</strong> {link(src.get('url'), src.get('short_name') or 'DOT list')}{(' · ' + e(d['table'])) if d.get('table') else ''}</span></div>
<div><div class="muted small">Order as (3000K · 480V · 70 CRI)</div><div class="cat">{e(fx.get('catalog'))}</div></div>
<dl class="kv">{kv}</dl>
<div class="files"><div class="muted small">Downloads</div>
{link(sheet.get('url'), '📄 ' + (sheet.get('title') or 'Cut sheet')) if sheet.get('url') else '<div class="muted">Cut sheet not found</div>'}
{ies_links(fx)}</div>
{caveats}
<details><summary>DOT-listed catalog number ({e(d.get('listed_cct', ''))})</summary><div class="cat">{e(d.get('listed_catalog'))}</div></details>
</article>"""


def render(build_date):
    data = json.loads((DATA / "fixtures.json").read_text(encoding="utf-8"))
    flt = data.get("filter", {})
    sources = {s["id"]: s for s in data.get("sources", [])}
    shown = [f for f in data.get("fixtures", []) if matches(f, flt)]
    shown.sort(key=lambda f: (f.get("product_type") != "LED roadway luminaire",
                              f.get("manufacturer", "").lower(), f.get("family", ""), f.get("watts") or 0))
    types = sorted({f.get("product_type") for f in shown})
    type_opts = "".join(f'<option value="{e(t)}">{e(t)}</option>' for t in types)
    n_ies = sum(1 for f in shown for i in f.get("ies", []) if i.get("file") and (ROOT / i["file"]).exists())
    chips = "".join(f'<span class="chip">{e(c)}</span>' for c in data.get("filter_labels", []))
    src_items = "".join(
        f"<li><strong>{e(s['state'])}</strong> – {link(s.get('url'), s.get('name'))} "
        f"<span class='muted'>({e(s.get('edition', ''))})</span>"
        f"<div class='small muted'>{e(s.get('status_note', ''))}</div></li>"
        for s in sources.values()
    )
    cards = "\n".join(card(f, sources) for f in shown) or '<div class="empty">No fixtures match the filter.</div>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Fixture Downloads</title>
<meta name="description" content="BABA-compliant roadway and high mast luminaires from state DOT approved lists, with .ies photometric files and manufacturer cut sheets. Showing 3000K, 480V, 70 CRI variants.">
<style>{CSS}{EXTRA_CSS}</style>
</head>
<body>
<main>
<h1>BABA Fixture Downloads</h1>
<div class="muted">Luminaires a state DOT lists as Buy America (BABA) compliant, with photometry and cut sheets · Updated {e(build_date)} · <a href="index.html">Compliance index</a></div>
<div class="chips">{chips}</div>

<div class="stats">
  <div class="stat"><b id="count">{len(shown)}</b>Fixtures shown</div>
  <div class="stat"><b>{n_ies}</b>.ies files to download</div>
  <div class="stat"><b>{len(sources)}</b>DOT source list{'s' if len(sources) != 1 else ''}</div>
</div>

<div class="card small">
<strong>How to read this.</strong> Each card is a luminaire configuration that a state DOT lists as
<strong>Compliant v5</strong>, meaning the manufacturer certified it for federal-aid projects obligated on or after
Oct 1, 2026 (US final assembly and more than 55% domestic component cost). DOT lists usually qualify one color
temperature; the catalog number shown here swaps in the 3000K / 70 CRI option of the same listed configuration.
{e(data.get('cct_note', ''))}
<ul>{src_items}</ul>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, family, or catalog number" aria-label="Search">
  <select id="type" aria-label="Filter by type"><option value="">All types</option>{type_opts}</select>
</div>

<div class="grid">
{cards}
</div>

<footer>
Generated by <code>scripts/build_fixtures.py</code> from <code>data/fixtures.json</code>. Photometric files are copies of
the manufacturers' published .ies files, kept here for convenience; each links to its source. This page is a research
aid, not a certification: get the manufacturer's project-specific Buy America certification for the exact catalog
number you order.
</footer>
</main>
<script>{JS}</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    ROOT.joinpath("fixtures.html").write_text(render(args.date), encoding="utf-8")
    print(f"Built fixtures.html for {args.date}")


if __name__ == "__main__":
    main()
