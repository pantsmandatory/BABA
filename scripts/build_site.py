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
            + td(f'<strong>{e(it.get("manufacturer"))}</strong>', "c-m", it.get("manufacturer"))
            + td(e(it.get("model")), "c-l", it.get("model"))
            + td(e(it.get("product_type")), "c-s", it.get("product_type"))
            + td(state_cell, "c-l", state_full)
            + td(badge(it.get("final_assembly_us")), "c-b")
            + td(badge(it.get("domestic_content_55")), "c-b")
            + td(badge(it.get("evidence_level")), "c-b")
            + td(numbered_links(ev), "c-n", " | ".join(x.get("summary", "") for x in ev))
            + td(e(it.get("notes", "")), "c-x muted", it.get("notes"))
            + td(e(it.get("last_verified")), "c-d muted")
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
            + td(f'<strong>{e(state)}</strong> <span class="muted">{e(STATE_NAMES.get(state, ""))}</span>', "c-m")
            + td(link(s.get("url"), s.get("list_name") or "Product list"), "c-l", s.get("list_name"))
            + td(e(s.get("luminaire_category")), "c-l muted", s.get("luminaire_category"))
            + td(badge(s.get("baba_flag")), "c-b")
            + td(e(s.get("baba_notes")), "c-x muted", s.get("baba_notes"))
            + td(guide, "c-d")
            + td(check, "c-d")
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

    prod_headers = ["Manufacturer", "Model / family", "Type", "DOT listing", "US assembly",
                    ">55% domestic", "Evidence", "Sources", "Notes", "Verified"]

    dates = "".join(
        f"<li><strong>{e(d.get('date'))}</strong> – {e(d.get('requirement'))}</li>"
        for d in rule.get("key_dates", [])
    )
    rule_sources = " · ".join(link(u, f"[{n + 1}]") for n, u in enumerate(rule.get("sources", [])))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Luminaire Index</title>
<meta name="description" content="Weekly list of roadway luminaires accepted on state DOT approved product lists with documented FHWA Buy America (BABA) compliance: US final assembly and more than 55% domestic component cost.">
<style>{CSS}</style>
</head>
<body>
<main>
<h1>BABA Luminaire Index</h1>
<div class="muted">Roadway &amp; area luminaires on state DOT approved product lists with documented FHWA Buy America compliance · Updated {e(build_date)} · Fixture downloads: <a href="fixtures-480v.html">480V</a> · <a href="fixtures-120-277v.html">120–277V</a> · <a href="fixtures-3k.html">3000K</a> · <a href="fixtures-4k.html">4000K</a> · <a href="fiber.html">Fiber products</a></div>

<div class="stats">
  <span><b>{len(compliant)}</b>compliant</span>
  {f"<span><b>{len(pending)}</b>awaiting verification</span>" if show_queue else ""}
  <span><b>{len(states_covered)}</b>state DOT lists</span>
  <span><b>{flagged}</b>lists flag Buy America</span>
  <span><b>{changed}</b>changed since last check</span>
</div>

<div class="card">
<strong>What counts as compliant here.</strong> Under FHWA's manufactured-products rule (23 CFR 635.410), a luminaire
must have <strong>final assembly in the United States</strong> and, for projects obligated on or after Oct 1, 2026,
<strong>domestic components costing more than 55%</strong> of all component cost. An entry appears in the main table
only when it is on at least one state DOT approved list <em>and</em> both tests are documented by the DOT or by the
manufacturer for that product family. This index is a research aid, not a certification: always obtain the
manufacturer's project-specific Buy America certification and confirm with the DOT.
<ul>{dates}</ul>
<div class="muted">{e(rule.get("changes_since", ""))} {rule_sources}</div>
<div class="muted">Rows are one line each; tap or click a row to show its full text.</div>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, model, or state" aria-label="Search">
  <select id="state" aria-label="Filter by state"><option value="">All states</option>{state_opts}</select>
</div>

<h2>Compliant luminaires</h2>
{table(prod_headers, product_rows(compliant), "No entries yet meet both documented tests.")}

{('<h2>Verification queue</h2><p class="small muted">On a DOT list, but only one test (or neither) is documented so far, or the claim is not specific to FHWA rules.</p>' + table(prod_headers, product_rows(pending), "Nothing in the queue.")) if show_queue else ""}

<h2>State DOT product lists</h2>
<p class="small muted">"Flags Buy America" means the list itself marks compliance. Weekly check shows whether the list page changed since the previous run.</p>
{table(["State", "Approved product list", "Luminaire category", "Flags BA", "Notes", "Guidance", "Weekly check"], source_rows(sources, status), "No sources yet.")}

<footer>
Generated by <code>scripts/build_site.py</code> from <code>data/*.json</code>. Past weekly snapshots: <a href="archive/index.html">archive</a>.
Corrections welcome via GitHub issues.
</footer>
</main>
<script>{JS}</script>
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
<p><a href="../index.html">Current list</a></p><ul>{items}</ul></main></body></html>
""",
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    page = render(args.date)
    ROOT.joinpath("index.html").write_text(page, encoding="utf-8")
    if not args.no_archive:
        ARCHIVE.mkdir(exist_ok=True)
        # Archive pages live one folder down, so point the archive link back up.
        ARCHIVE.joinpath(f"{args.date}.html").write_text(
            page.replace('href="archive/index.html"', 'href="index.html"').replace('href="fixtures-3k.html"', 'href="../fixtures-3k.html"').replace('href="fixtures-480v.html"', 'href="../fixtures-480v.html"').replace('href="fixtures-120-277v.html"', 'href="../fixtures-120-277v.html"').replace('href="fixtures-4k.html"', 'href="../fixtures-4k.html"').replace('href="fiber.html"', 'href="../fiber.html"'), encoding="utf-8"
        )
        write_archive_index()
    print(f"Built index.html for {args.date}")


if __name__ == "__main__":
    main()
