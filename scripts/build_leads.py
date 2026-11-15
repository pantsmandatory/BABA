#!/usr/bin/env python3
"""Build leads.html: Buy America clues that are NOT yet a state DOT Phase 2 statement for an exact model number.

Reads data/leads.json. Nothing on this page appears on the fixture pages; each row says what the source
literally states and what is still missing. Rows are two lines tall; tap a row to open it, tap a header to sort.

Usage: python3 scripts/build_leads.py [--date YYYY-MM-DD]
Standard library only.
"""

import argparse
import datetime as dt
import json
import pathlib

from build_site import CSS, STATE_NAMES, e, link, site_nav

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

EXTRA_CSS = """
table.ld{font-size:var(--fx,12.5px)}
table.ld th,table.ld td{white-space:normal;overflow:visible;max-width:none;min-width:0;vertical-align:top}
table.ld .cl{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;overflow:hidden;height:2.6em;line-height:1.3}
table.ld tr.open .cl{display:block;height:auto;min-height:2.6em;overflow:visible}
table.ld td.code .cl{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.92em;overflow-wrap:anywhere}
table.ld td.code{min-width:clamp(13ch,17vw,34ch)}
table.ld td.code .cl{word-break:break-all}
table.ld td.wide{width:24%}
table.ld th{cursor:pointer;user-select:none}
table.ld th[data-dir]::after{content:" ▲";font-size:.8em;color:var(--accent)}
table.ld th[data-dir="desc"]::after{content:" ▼"}
body.compact main{padding:8px 8px 32px}
body.compact table.ld th,body.compact table.ld td{padding:2px 4px}
body.compact table.ld th{font-size:9.5px;letter-spacing:0}
@media (max-height:520px){.table-wrap{max-height:none}th{position:static}}
"""

JS = """
const q=document.getElementById('q'),sf=document.getElementById('st');
function apply(){const t=q.value.trim().toLowerCase(),s=sf.value;let n=0;
document.querySelectorAll('tbody tr[data-search]').forEach(r=>{const ok=(!t||r.dataset.search.includes(t))&&(!s||r.dataset.state===s);r.hidden=!ok;if(ok)n++;});
document.getElementById('count').textContent=n;}
q.addEventListener('input',apply);sf.addEventListener('change',apply);
document.querySelectorAll('tbody tr[data-search]').forEach(r=>r.addEventListener('click',ev=>{if(ev.target.closest('a'))return;r.classList.toggle('open');}));
function sortKey(td){const t=(td?td.textContent:'').trim();if(!t||t==='—')return null;
const m=t.replace(/[,≈]/g,'').match(/^([0-9]+([.][0-9]+)?)(V|K|W)?$/);return m?parseFloat(m[1]):t.toLowerCase();}
document.querySelectorAll('table.ld thead th').forEach(th=>th.addEventListener('click',()=>{
const tr=th.parentElement,i=th.cellIndex,tb=th.closest('table').tBodies[0],dir=th.dataset.dir==='asc'?'desc':'asc';
tr.querySelectorAll('th').forEach(x=>delete x.dataset.dir);th.dataset.dir=dir;
const rows=[...tb.rows].map((r,n)=>({r,n,k:sortKey(r.cells[i])}));
rows.sort((a,b)=>{if(a.k===null||b.k===null)return a.k===b.k?a.n-b.n:(a.k===null?1:-1);
if(typeof a.k!==typeof b.k)return typeof a.k==='number'?-1:1;
let c=typeof a.k==='number'?a.k-b.k:String(a.k).localeCompare(String(b.k),undefined,{numeric:true});
return (dir==='asc'?c:-c)||a.n-b.n;});rows.forEach(x=>tb.appendChild(x.r));}));
function fit(){const w=window.innerWidth,h=window.innerHeight;const c=w<1000||h<=560;document.body.classList.toggle('compact',c);
const sizes=c?[11,10.5,10]:[12.5,12,11.5,11];const wraps=[...document.querySelectorAll('table.ld')].map(t=>t.parentElement);
for(const fs of sizes){document.body.style.setProperty('--fx',fs+'px');if(wraps.every(x=>x.scrollWidth<=x.clientWidth+1))break;}}
let ft;window.addEventListener('resize',()=>{clearTimeout(ft);ft=setTimeout(fit,120);});fit();
"""


def cell(content, cls=""):
    return f'<td class="{cls}"><div class="cl">{content}</div></td>'


def src_cell(row):
    parts = []
    if row.get("source_url"):
        parts.append(link(row["source_url"], row.get("source_short") or "source"))
    for f in row.get("files", []):
        if (ROOT / f["file"]).exists():
            parts.append(f'<a href="{e(f["file"])}" download>⬇ {e(f.get("label", ".ies"))}</a>')
    return " · ".join(parts) or "—"


def render_table(rows, columns):
    head = "".join(f"<th>{e(h)}</th>" for h, _, _ in columns)
    body = []
    for r in rows:
        search = (" ".join(str(r.get(k, "")) for k in ("state", "manufacturer", "model", "product", "part", "material", "says", "missing", "source"))
                  + " " + STATE_NAMES.get(r.get("state", ""), "")).lower()
        tds = "".join(cell(src_cell(r), cls) if key == "_src" else
                      cell(f"<strong>{e(r.get(key) or '—')}</strong>" if key in ("state", "manufacturer") else e(r.get(key) or "—"), cls)
                      for _, key, cls in columns)
        body.append(f'<tr data-search="{e(search)}" data-state="{e(r.get("state", ""))}">{tds}</tr>')
    return (f'<div class="table-wrap"><table class="ld"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


LUM_COLS = [("State", "state", ""), ("Manufacturer", "manufacturer", ""), ("Model as printed", "model", "code"),
            ("Voltage", "voltage", ""), ("What the source says", "says", "wide"), ("What is missing", "missing", "wide"),
            ("Source / files", "_src", "")]
FIB_COLS = [("State", "state", ""), ("Manufacturer", "manufacturer", ""), ("Product", "product", ""),
            ("Part number as printed", "part", "code"), ("Fiber", "fiber", ""), ("What the source says", "says", "wide"),
            ("What is missing", "missing", "wide"), ("Source", "_src", "")]


CON_COLS = [("State", "state", ""), ("Manufacturer", "manufacturer", ""), ("Product", "product", ""),
            ("Order code as printed", "part", "code"), ("Material", "material", ""), ("What the source says", "says", "wide"),
            ("What is missing", "missing", "wide"), ("Source", "_src", "")]


def render(build_date, data):
    lum, fib, con = data.get("luminaires", []), data.get("fiber", []), data.get("conduit", [])
    states = sorted({r.get("state") for r in lum + fib + con if r.get("state")})
    state_opts = "".join(f'<option value="{e(s)}">{e(s)} – {e(STATE_NAMES.get(s, s))}</option>' for s in states)
    blocked = "".join(f"<li><strong>{e(b.get('state'))}</strong> – {link(b.get('url'), b.get('name'))}: {e(b.get('why'))}</li>"
                      for b in data.get("blocked", []))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Leads to Verify</title>
<meta name="description" content="Buy America clues for luminaires and 62.5 micron multimode fiber products that are not yet a state DOT Phase 2 statement for an exact model number.">
<style>{CSS}{EXTRA_CSS}</style>
</head>
<body>
<main>
<h1>BABA Leads to Verify</h1>
<div class="muted">Clues from state DOT lists and manufacturers that are not Phase 2 statements · Updated {e(build_date)}</div>
<div class="small">{site_nav("leads.html")}</div>

<div class="stats">
  <span><b id="count">{len(lum) + len(fib) + len(con)}</b>leads</span>
  <span><b>{len(lum)}</b>luminaire</span>
  <span><b>{len(fib)}</b>fiber</span>
  <span><b>{len(con)}</b>conduit</span>
  <span><b>{len(states)}</b>states</span>
</div>

<div class="card"><strong>Not a compliance list.</strong> {e(data.get("intro", ""))}</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, model, part number, or wording" aria-label="Search">
  <select id="st" aria-label="Filter by state"><option value="">State</option>{state_opts}</select>
</div>

<h2 id="luminaires">Luminaire leads</h2>
{render_table(lum, LUM_COLS)}

<h2 id="fiber">Fiber leads (62.5 µm multimode and related)</h2>
<p class="small muted">{e(data.get("fiber_intro", ""))}</p>
{render_table(fib, FIB_COLS)}

<h2 id="conduit">Conduit leads (HDPE and rigid metal)</h2>
<p class="small muted">{e(data.get("conduit_intro", ""))}</p>
{render_table(con, CON_COLS)}

{('<h2 id="blocked">Lists that could not be read</h2><div class="card"><ul>' + blocked + '</ul></div>') if blocked else ''}

<footer>
Generated by <code>scripts/build_leads.py</code> from <code>data/leads.json</code>. Rows are two lines each; tap a row to open it and a
column header to sort. Rule: <a href="compliance.html#cfr">23 CFR 635.410(c) references</a>. This page is a research aid, not a certification.
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
    data = json.loads((DATA / "leads.json").read_text(encoding="utf-8"))
    ROOT.joinpath("leads.html").write_text(render(args.date, data), encoding="utf-8")
    print(f"Built leads.html for {args.date}")


if __name__ == "__main__":
    main()
