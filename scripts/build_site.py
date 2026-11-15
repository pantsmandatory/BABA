#!/usr/bin/env python3
"""Build the BABA luminaire index page from the JSON files in data/.

Writes:
  index.html                 - the current list
  archive/YYYY-MM-DD.html    - a dated copy of the same page (weekly snapshot)
  archive/index.html         - list of past snapshots

Usage: python3 scripts/build_site.py [--date YYYY-MM-DD] [--no-archive]
Standard library only, so it runs the same locally and in GitHub Actions.
"""

import argparse
import datetime as dt
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARCHIVE = ROOT / "archive"

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def load(name, default):
    path = DATA / name
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def e(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def link(url, text=None):
    if not url:
        return e(text or "")
    return f'<a href="{e(url)}" rel="noopener" target="_blank">{e(text or url)}</a>'


def is_compliant(item):
    """Both FHWA tests must be documented: US final assembly and >55% domestic component cost."""
    return item.get("final_assembly_us") == "stated" and item.get("domestic_content_55") == "stated"


BADGE = {
    "dot-flagged": ("DOT-flagged", "ok"),
    "manufacturer-declared": ("Manufacturer-declared", "info"),
    "yes": ("Yes", "ok"),
    "no": ("No", "muted"),
    "unclear": ("Unclear", "warn"),
    "stated": ("Stated", "ok"),
    "not stated": ("Not stated", "warn"),
    "changed": ("Changed", "warn"),
    "unchanged": ("Unchanged", "ok"),
    "error": ("Unreachable", "bad"),
    "new": ("First check", "info"),
}


def badge(key):
    label, tone = BADGE.get(key, (key or "—", "muted"))
    return f'<span class="badge {tone}">{e(label)}</span>'


def td(content, cls="", full=None):
    """One spreadsheet cell. `full` becomes the hover text when the cell is cut off."""
    title = f' title="{e(full)}"' if full else ""
    return f'<td class="{cls}"{title}>{content}</td>'


def numbered_links(items):
    return " ".join(link(i.get("url"), f"[{n + 1}]") for n, i in enumerate(items) if i.get("url"))


def product_rows(items):
    rows = []
    for it in items:
        states = it.get("states", [])
        state_codes = sorted({s.get("state", "") for s in states})
        state_cell = "; ".join(
            f'<strong>{e(s.get("state"))}</strong> '
            + link(s.get("dot_list_url"), s.get("listing_id") or s.get("list_name") or "list")
            for s in states
        )
        state_full = "; ".join(f'{s.get("state")}: {s.get("list_name")} {s.get("listing_id", "")}' for s in states)
        ev = it.get("evidence", [])
        search_blob = " ".join(
            [it.get("manufacturer", ""), it.get("model", ""), it.get("product_type", ""), it.get("notes", "")]
            + state_codes
            + [STATE_NAMES.get(c, "") for c in state_codes]
        ).lower()
        rows.append(
            f'<tr data-search="{e(search_blob)}" data-states="{e(" ".join(state_codes))}">'
            + vtd(f'<strong>{e(it.get("manufacturer"))}</strong>', "", "", it.get("manufacturer"))
            + vtd(e(it.get("model")), "", "", it.get("model"))
            + vtd(state_cell, "1", "", state_full)
            + vtd(badge(it.get("final_assembly_us")), "1", "c-b")
            + vtd(badge(it.get("domestic_content_55")), "1", "c-b")
            + vtd(e(it.get("product_type")), "2", "", it.get("product_type"))
            + vtd(badge(it.get("evidence_level")), "2", "c-b")
            + vtd(numbered_links(ev), "2", "", " | ".join(x.get("summary", "") for x in ev))
            + vtd(e(it.get("last_verified")), "2", "muted")
            + vtd(e(it.get("notes", "")), "3", "wide muted", it.get("notes"))
            + "</tr>"
        )
    return "\n".join(rows)


def source_rows(sources, status):
    rows = []
    for s in sorted(sources, key=lambda x: (STATE_NAMES.get(x.get("state"), x.get("state", "")))):
        st = status.get(s.get("url"), {})
        state = s.get("state", "")
        guide = link(s.get("buy_america_guidance_url"), "Guidance") if s.get("buy_america_guidance_url") else "—"
        check = (badge(st.get("state")) + f' <span class="muted">{e(st.get("checked", ""))}</span>') if st else "—"
        rows.append(
            f'<tr data-search="{e((state + " " + STATE_NAMES.get(state, "") + " " + s.get("agency", "")).lower())}" data-states="{e(state)}">'
            + vtd(f'<strong>{e(state)}</strong> <span class="muted">{e(STATE_NAMES.get(state, ""))}</span>')
            + vtd(link(s.get("url"), s.get("list_name") or "Product list"), "", "", s.get("list_name"))
            + vtd(badge(s.get("baba_flag")), "1", "c-b")
            + vtd(check, "1")
            + vtd(e(s.get("luminaire_category")), "2", "muted", s.get("luminaire_category"))
            + vtd(guide, "2")
            + vtd(e(s.get("baba_notes")), "3", "wide muted", s.get("baba_notes"))
            + "</tr>"
        )
    return "\n".join(rows)


CSS = """
:root{--bg:#f7f8fa;--surface:#fff;--text:#1a1d23;--muted:#5d6573;--border:#dde1e7;--grid:#e8ebf0;--stripe:#fafbfc;--hover:#eef3fb;--accent:#1f5fbf;
--ok-bg:#e3f4e8;--ok:#1d6b35;--warn-bg:#fdf1dc;--warn:#8a5300;--bad-bg:#fde4e4;--bad:#a32020;--info-bg:#e4edfb;--info:#1f4f9a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121418;--surface:#1b1e24;--text:#e7e9ee;--muted:#9aa3b2;
--border:#2e333c;--grid:#262a31;--stripe:#1f2229;--hover:#22304a;--accent:#7fb0ff;--ok-bg:#16351f;--ok:#8fdca6;--warn-bg:#3a2c12;--warn:#f2c374;--bad-bg:#3d1818;--bad:#ff9d9d;--info-bg:#172a48;--info:#9cc2ff}}
:root[data-theme="dark"]{--bg:#121418;--surface:#1b1e24;--text:#e7e9ee;--muted:#9aa3b2;
--border:#2e333c;--grid:#262a31;--stripe:#1f2229;--hover:#22304a;--accent:#7fb0ff;--ok-bg:#16351f;--ok:#8fdca6;--warn-bg:#3a2c12;--warn:#f2c374;--bad-bg:#3d1818;--bad:#ff9d9d;--info-bg:#172a48;--info:#9cc2ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1600px;margin:0 auto;padding:16px 16px 48px}
h1{font-size:1.4rem;margin:0 0 2px}h2{font-size:1.05rem;margin:24px 0 6px}
a{color:var(--accent)}
.muted{color:var(--muted)}.small{font-size:.85rem}.nowrap{white-space:nowrap}
.card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin:10px 0;font-size:.85rem}
.card ul{margin:4px 0;padding-left:20px}
.stats{display:flex;flex-wrap:wrap;gap:6px 18px;margin:8px 0;font-size:.85rem;color:var(--muted)}
.stats b{color:var(--text);font-size:1rem;margin-right:3px}
.controls{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
input,select{font:inherit;padding:5px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text)}
input{flex:1;min-width:200px}
.table-wrap{overflow:auto;max-height:80vh;background:var(--surface);border:1px solid var(--border);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:12.5px;line-height:1.3}
th,td{text-align:left;vertical-align:middle;padding:3px 8px;border-bottom:1px solid var(--grid);border-right:1px solid var(--grid);
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
th{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.03em;color:var(--muted);background:var(--surface);
position:sticky;top:0;z-index:1;box-shadow:inset 0 -1px var(--border)}
tbody tr:nth-child(even){background:var(--stripe)}
tbody tr:hover{background:var(--hover)}
tbody tr[data-search]{cursor:pointer}
tbody tr.open td{white-space:normal;overflow:visible}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.c-m{max-width:200px}.c-l{max-width:280px}.c-s{max-width:170px}.c-x{max-width:380px;min-width:160px}.c-cat{max-width:470px}.c-b,.c-d,.c-n{max-width:none}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11.5px}
.badge{display:inline-block;padding:0 6px;border-radius:999px;font-size:11px;font-weight:600;white-space:nowrap;line-height:1.5}
.ok{background:var(--ok-bg);color:var(--ok)}.warn{background:var(--warn-bg);color:var(--warn)}
.bad{background:var(--bad-bg);color:var(--bad)}.info{background:var(--info-bg);color:var(--info)}
.muted.badge{background:var(--border);color:var(--muted)}
.empty{padding:12px;color:var(--muted)}
table.cfr td{white-space:normal;overflow:visible;vertical-align:top}table.cfr td.nowrap{white-space:nowrap}
footer{margin-top:28px;color:var(--muted);font-size:.8rem}
"""

# Row click expands a row to show its full text; links still work as links.
ROW_JS = """
document.querySelectorAll('tbody tr[data-search]').forEach(r=>r.addEventListener('click',ev=>{
if(ev.target.closest('a'))return;r.classList.toggle('open');}));
"""

JS = """
const q=document.getElementById('q'),st=document.getElementById('state');
function apply(){const t=q.value.trim().toLowerCase(),s=st.value;
document.querySelectorAll('tbody tr[data-search]').forEach(r=>{
const ok=(!t||r.dataset.search.includes(t))&&(!s||r.dataset.states.split(' ').includes(s));r.hidden=!ok;});}
q.addEventListener('input',apply);st.addEventListener('change',apply);
""" + ROW_JS


# Three-view tables (index and fiber pages): a slider picks which columns show; every row is two text lines tall.
SV_CSS = """
table.sv{font-size:var(--fx,12.5px)}
table.sv th,table.sv td{white-space:normal;overflow:visible;max-width:none;min-width:0}
table.sv .cl{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;overflow:hidden;height:2.6em;line-height:1.3}
table.sv tr.open .cl{display:block;height:auto;min-height:2.6em;overflow:visible}
table.sv .v1,table.sv .v2,table.sv .v3{display:none}
body.view1 table.sv .v1,body.view2 table.sv .v2,body.view3 table.sv .v3{display:table-cell}
table.sv td.mono .cl{overflow-wrap:anywhere}
table.sv td.c-b .cl{display:flex;align-items:center}
table.sv td.wide{width:55%}
table.sv thead th{cursor:pointer;user-select:none}
table.sv thead th[data-dir]::after{content:" ▲";font-size:.8em;color:var(--accent)}
table.sv thead th[data-dir="desc"]::after{content:" ▼"}
.views{flex:1 1 100%;max-width:560px;margin-top:2px}
section .views{max-width:none;margin:6px 0}
body.compact .views{max-width:none}
.vlabels{display:flex;justify-content:space-between;gap:8px;font-size:12px;font-weight:600;color:var(--muted)}
.vlabels span{flex:1;cursor:pointer;line-height:1.2}
.vlabels span:nth-child(2){text-align:center}.vlabels span:nth-child(3){text-align:right}
.vlabels span.on{color:var(--accent)}
input.view{display:block;flex:none;width:100%;min-width:0;padding:0;margin:4px 0 0;border:0;background:transparent;accent-color:var(--accent);height:26px}
body.compact main{padding:8px 8px 32px}
body.compact table.sv th,body.compact table.sv td{padding:2px 4px}
body.compact table.sv th{font-size:9.5px;letter-spacing:0}
@media (max-height:520px){.table-wrap{max-height:none}th{position:static}}
"""

SV_JS = """
const vws=[...document.querySelectorAll('input.view')],vl=[...document.querySelectorAll('.vlabels span')];
function setView(v){vws.forEach(x=>{x.value=v;});document.body.classList.remove('view1','view2','view3');document.body.classList.add('view'+v);
vl.forEach(x=>x.classList.toggle('on',x.dataset.v==v));fit();}
vws.forEach(x=>x.addEventListener('input',()=>setView(+x.value)));
vl.forEach(x=>x.addEventListener('click',()=>setView(+x.dataset.v)));
function sortKey(td){const t=(td?td.textContent:'').trim();if(!t||t==='—')return null;
const m=t.replace(/[,≈]/g,'').match(/^([0-9]+([.][0-9]+)?)(V|K|W)?$/);return m?parseFloat(m[1]):t.toLowerCase();}
document.querySelectorAll('table.sv thead th').forEach(th=>th.addEventListener('click',()=>{
const tr=th.parentElement,i=th.cellIndex,tb=th.closest('table').tBodies[0],dir=th.dataset.dir==='asc'?'desc':'asc';
tr.querySelectorAll('th').forEach(x=>delete x.dataset.dir);th.dataset.dir=dir;
const rows=[...tb.rows].map((r,n)=>({r,n,k:sortKey(r.cells[i])}));
rows.sort((a,b)=>{if(a.k===null||b.k===null)return a.k===b.k?a.n-b.n:(a.k===null?1:-1);
if(typeof a.k!==typeof b.k)return typeof a.k==='number'?-1:1;
let c=typeof a.k==='number'?a.k-b.k:String(a.k).localeCompare(String(b.k),undefined,{numeric:true});
return (dir==='asc'?c:-c)||a.n-b.n;});rows.forEach(x=>tb.appendChild(x.r));}));
function fit(){const w=window.innerWidth,h=window.innerHeight,c=w<1000||h<=560;document.body.classList.toggle('compact',c);
const sizes=c?[11,10.5,10]:[12.5,12,11.5,11];const wraps=[...document.querySelectorAll('table.sv')].map(t=>t.parentElement);
for(const fs of sizes){document.body.style.setProperty('--fx',fs+'px');if(wraps.every(x=>x.scrollWidth<=x.clientWidth+1))break;}}
let ft;window.addEventListener('resize',()=>{clearTimeout(ft);ft=setTimeout(fit,120);});fit();
"""


def vtd(content, view="", cls="", full=None):
    """Cell of a three-view table. view is "" (always shown) or "1"/"2"/"3" (shown only in that slider position)."""
    title = f' title="{e(full)}"' if full else ""
    v = f"v{view} " if view else ""
    return f'<td class="{v}{cls}"{title}><div class="cl">{content}</div></td>'


def view_table(headers, body, empty_msg):
    """headers: list of (label, view) with view "" or "1"/"2"/"3"."""
    head = "".join(f'<th class="{"v" + v if v else ""}">{e(h)}</th>' for h, v in headers)
    if not body:
        body = f'<tr><td colspan="{len(headers)}" class="empty">{e(empty_msg)}</td></tr>'
    return f'<div class="table-wrap"><table class="sv"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def view_slider(labels):
    spans = "".join(f'<span data-v="{n + 1}"{" class=\"on\"" if n == 0 else ""}>{e(l)}</span>' for n, l in enumerate(labels))
    # A page may carry several sliders (one per table); the script keeps them all in step.
    return (f'<div class="views"><div class="vlabels">{spans}</div>'
            f'<input class="view" type="range" min="1" max="3" step="1" value="1" aria-label="Table view: {e(", ".join(labels))}"></div>')


# One navigation bar for every page, so no page links to an out-of-date set of pages.
NAV_PAGES = [("index.html", "Start"), ("fixtures-480v.html", "480V fixtures"), ("fixtures-120-277v.html", "120–277V fixtures"),
             ("fixtures-3k.html", "480V 3000K only"), ("fixtures-4k.html", "480V 4000K only"),
             ("fiber.html", "Fiber products"), ("conduit.html", "Conduit"), ("leads.html", "Leads to verify"), ("compliance.html", "Rules & state lists")]


def site_nav(current):
    pages = [(f, t) for f, t in NAV_PAGES if (f != "leads.html" or (DATA / "leads.json").exists())
             and (f != "conduit.html" or (DATA / "conduit.json").exists())]
    return " · ".join(f"<strong>{e(t)}</strong>" if f == current else f'<a href="{f}">{e(t)}</a>' for f, t in pages)


def table(headers, body, empty_msg):
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    if not body:
        body = f'<tr><td colspan="{len(headers)}" class="empty">{e(empty_msg)}</td></tr>'
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render(build_date):
    rule = load("rule.json", {})
    sources = load("sources.json", [])
    luminaires = load("luminaires.json", [])
    status = load("source_status.json", {})

    show_queue = bool(load("site.json", {}).get("show_unlisted"))
    compliant = [i for i in luminaires if is_compliant(i)]
    pending = [i for i in luminaires if not is_compliant(i)]
    key = lambda i: (i.get("manufacturer", "").lower(), i.get("model", "").lower())
    compliant.sort(key=key)
    pending.sort(key=key)

    states_covered = sorted({s.get("state") for s in sources})
    flagged = sum(1 for s in sources if s.get("baba_flag") == "yes")
    changed = sum(1 for s in status.values() if s.get("state") == "changed")
    state_opts = "".join(
        f'<option value="{e(c)}">{e(c)} – {e(STATE_NAMES.get(c, c))}</option>' for c in states_covered
    )

    prod_headers = [("Manufacturer", ""), ("Model / family", ""), ("DOT listing", "1"), ("US manufacture", "1"),
                    (">55% domestic", "1"), ("Type", "2"), ("Evidence", "2"), ("Sources", "2"), ("Verified", "2"), ("Notes", "3")]
    src_headers = [("State", ""), ("Approved product list", ""), ("Flags Buy America", "1"), ("Weekly check", "1"),
                   ("Luminaire category", "2"), ("Guidance", "2"), ("Notes", "3")]

    dates = "".join(
        f"<li><strong>{e(d.get('date'))}</strong> – {e(d.get('requirement'))}</li>"
        for d in rule.get("key_dates", [])
    )
    rule_sources = " · ".join(link(u, f"[{n + 1}]") for n, u in enumerate(rule.get("sources", [])))
    cfr_rows = "".join(
        f"<tr><td>{e(c.get('topic'))}</td><td class='nowrap'>{link(rule.get('cfr_url'), c.get('cite'))}</td><td>{e(c.get('text'))}</td></tr>"
        for c in rule.get("cfr", []))
    cfr_html = "" if not cfr_rows else (
        '<h2 id="cfr">CFR references for Phase 2 (projects obligated on or after Oct 1, 2026)</h2>'
        f'<p class="small muted">Quoted from {link(rule.get("cfr_url"), "23 CFR 635.410")} ({e(rule.get("cfr_checked", ""))}). '
        'Confirm the current text before relying on it.</p>'
        '<div class="table-wrap"><table class="cfr"><thead><tr><th>Requirement</th><th>Citation</th><th>Rule text</th></tr></thead>'
        f'<tbody>{cfr_rows}</tbody></table></div>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Luminaire Index</title>
<meta name="description" content="Weekly list of roadway luminaires accepted on state DOT approved product lists with documented FHWA Buy America (BABA) compliance: US final assembly and more than 55% domestic component cost.">
<style>{CSS}{SV_CSS}</style>
</head>
<body class="view1">
<main>
<h1>BABA Luminaire Index</h1>
<div class="muted">Roadway &amp; area luminaires on state DOT approved product lists with documented FHWA Buy America compliance · Updated {e(build_date)}</div>
<div class="small">{site_nav("compliance.html")}</div>

<div class="stats">
  <span><b>{len(compliant)}</b>compliant</span>
  {f"<span><b>{len(pending)}</b>awaiting verification</span>" if show_queue else ""}
  <span><b>{len(states_covered)}</b>state DOT lists</span>
  <span><b>{flagged}</b>lists flag Buy America</span>
  <span><b>{changed}</b>changed since last check</span>
</div>

<div class="card">
<strong>What counts as compliant here.</strong> Under FHWA's manufactured-products rule (23 CFR 635.410), a luminaire
must be <strong>manufactured in the United States</strong> (state lists often call this final assembly) and, for projects obligated on or after Oct 1, 2026,
<strong>domestic components costing more than 55%</strong> of all component cost. An entry appears in the main table
only when it is on at least one state DOT approved list <em>and</em> both tests are documented by the DOT or by the
manufacturer for that product family. This index is a research aid, not a certification: always obtain the
manufacturer's project-specific Buy America certification and confirm with the DOT.
<ul>{dates}</ul>
<div class="muted">{e(rule.get("changes_since", ""))} {rule_sources}</div>
<div class="muted">Use the slider above the tables to switch between compliance, evidence and notes. Rows are two lines each; tap a row to open it and a column header to sort.</div>
</div>

{cfr_html}

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, model, or state" aria-label="Search">
  <select id="state" aria-label="Filter by state"><option value="">State</option>{state_opts}</select>
  {view_slider(["Compliance", "Evidence & sources", "Notes"])}
</div>

<h2>Compliant luminaires</h2>
{view_table(prod_headers, product_rows(compliant), "No entries yet meet both documented tests.")}

{('<h2>Verification queue</h2><p class="small muted">On a DOT list, but only one test (or neither) is documented so far, or the claim is not specific to FHWA rules.</p>' + view_table(prod_headers, product_rows(pending), "Nothing in the queue.")) if show_queue else ""}

<h2>State DOT product lists</h2>
<p class="small muted">"Flags Buy America" means the list itself marks compliance. Weekly check shows whether the list page changed since the previous run.</p>
{view_table(src_headers, source_rows(sources, status), "No sources yet.")}

<footer>
Generated by <code>scripts/build_site.py</code> from <code>data/*.json</code>. Past weekly snapshots: <a href="archive/index.html">archive</a>.
Corrections welcome via GitHub issues.
</footer>
</main>
<script>{JS}{SV_JS}</script>
</body>
</html>
"""


HOME_CSS = """
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin:14px 0}
a.tile{display:block;text-decoration:none;color:inherit;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
a.tile:hover{background:var(--hover)}
a.tile .t{font-size:1.15rem;font-weight:700;color:var(--accent)}
a.tile .s{color:var(--muted);font-size:.9rem}
a.tile .n{font-size:.85rem;margin-top:4px;font-weight:600}
"""


def render_home(build_date):
    """index.html (and fixtures.html, so old links keep working): one tap target per list."""
    fx = load("fixtures.json", {})
    listed = [f for f in fx.get("fixtures", []) if f.get("basis") == "as-listed" and not f.get("voltage_inferred")]

    def count(v):
        rows = [f for f in listed if f.get("voltage") == v]
        ies = sum(1 for f in rows for i in f.get("ies", []) if i.get("file") and (ROOT / i["file"]).exists())
        return f"{len(rows)} configurations · {ies} .ies files"

    fiber = load("fiber.json", {})
    leads = load("leads.json", {})
    n_leads = len(leads.get("luminaires", [])) + len(leads.get("fiber", [])) + len(leads.get("conduit", []))
    tiles = [
        ("fixtures-480v.html", "480V luminaires", "Roadway, high mast and underpass", count(480)),
        ("fixtures-120-277v.html", "120–277V luminaires", "Roadway, high mast and underpass", count("120-277")),
        ("fiber.html", "Fiber products", "Multimode 62.5 µm, single-mode and cabinet hardware", f'{len(fiber.get("products", []))} products'),
    ]
    conduit = load("conduit.json", {})
    if conduit:
        tiles.append(("conduit.html", "Conduit", "2-inch HDPE and rigid metal conduit, with the rule for each material",
                      f'{len(conduit.get("rows", []))} listings'))
    if leads:
        tiles.append(("leads.html", "Leads to verify", "Flagged by a DOT or maker, but not yet a Phase 2 statement",
                      f"{n_leads} leads, kept separate from the lists above"))
    tiles.append(("compliance.html", "Rules and state lists", "23 CFR 635.410 references and the state DOT lists reviewed",
                  f'{len(load("sources.json", []))} state DOT lists'))
    cards = "".join(f'<a class="tile" href="{f}"><div class="t">{e(t)}</div><div class="s">{e(s)}</div><div class="n">{e(n)}</div></a>'
                    for f, t, s, n in tiles)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Highway Products</title>
<meta name="description" content="Highway lighting and fiber products that state DOT lists state are Buy America (BABA) compliant for projects obligated on or after Oct 1, 2026.">
<style>{CSS}{HOME_CSS}</style>
<script>if(location.hash==='#cfr')location.replace('compliance.html#cfr');</script>
</head>
<body>
<main>
<h1>BABA highway products</h1>
<div class="muted">State DOT-listed products compliant for projects obligated on or after Oct 1, 2026 · Updated {e(build_date)}</div>
<div class="cards">{cards}</div>
<div class="small muted">480V filters: <a href="fixtures-3k.html">3000K only</a> · <a href="fixtures-4k.html">4000K only</a>.
Only rows a state DOT prints as compliant, with the exact model number, are on the luminaire lists. This site is a research aid, not a certification.</div>
</main>
</body>
</html>
"""


def write_archive_index():
    snaps = sorted((p.stem for p in ARCHIVE.glob("????-??-??.html")), reverse=True)
    items = "".join(f'<li><a href="{s}.html">{s}</a></li>' for s in snaps)
    ARCHIVE.joinpath("index.html").write_text(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>BABA Index Archive</title>
<style>{CSS}</style></head><body><main><h1>Weekly snapshots</h1>
<p><a href="../compliance.html">Current list</a> · <a href="../index.html">Start page</a></p><ul>{items}</ul></main></body></html>
""",
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    page = render(args.date)
    ROOT.joinpath("compliance.html").write_text(page, encoding="utf-8")
    home = render_home(args.date)
    ROOT.joinpath("index.html").write_text(home, encoding="utf-8")
    ROOT.joinpath("fixtures.html").write_text(home, encoding="utf-8")
    if not args.no_archive:
        ARCHIVE.mkdir(exist_ok=True)
        # Archive pages live one folder down, so point the archive link back up.
        ARCHIVE.joinpath(f"{args.date}.html").write_text(
            re.sub(r'href="([a-z0-9-]+\.html)(#[^"]*)?"', r'href="../\1\2"', page).replace('href="archive/index.html"', 'href="index.html"'), encoding="utf-8"
        )
        write_archive_index()
    print(f"Built index.html, fixtures.html and compliance.html for {args.date}")


if __name__ == "__main__":
    main()
