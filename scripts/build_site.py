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


def product_rows(items):
    rows = []
    for it in items:
        states = it.get("states", [])
        state_codes = sorted({s.get("state", "") for s in states})
        state_cells = "<br>".join(
            f'<strong>{e(s.get("state"))}</strong> '
            + link(s.get("dot_list_url"), s.get("list_name") or "list")
            + (f' <span class="muted">#{e(s["listing_id"])}</span>' if s.get("listing_id") else "")
            for s in states
        )
        evidence = "<br>".join(
            link(ev.get("url"), ev.get("summary") or ev.get("url")) for ev in it.get("evidence", [])
        )
        search_blob = " ".join(
            [it.get("manufacturer", ""), it.get("model", ""), it.get("product_type", "")]
            + state_codes
            + [STATE_NAMES.get(c, "") for c in state_codes]
        ).lower()
        rows.append(
            f'<tr data-search="{e(search_blob)}" data-states="{e(" ".join(state_codes))}">'
            f'<td><strong>{e(it.get("manufacturer"))}</strong></td>'
            f'<td>{e(it.get("model"))}<div class="muted small">{e(it.get("product_type"))}</div></td>'
            f"<td>{state_cells}</td>"
            f'<td>{badge(it.get("final_assembly_us"))}</td>'
            f'<td>{badge(it.get("domestic_content_55"))}</td>'
            f'<td>{badge(it.get("evidence_level"))}</td>'
            f'<td class="small">{evidence}<div class="muted">{e(it.get("notes", ""))}</div></td>'
            f'<td class="nowrap small">{e(it.get("last_verified"))}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def source_rows(sources, status):
    rows = []
    for s in sorted(sources, key=lambda x: (STATE_NAMES.get(x.get("state"), x.get("state", "")))):
        st = status.get(s.get("url"), {})
        state = s.get("state", "")
        rows.append(
            f'<tr data-search="{e((state + " " + STATE_NAMES.get(state, "") + " " + s.get("agency", "")).lower())}" data-states="{e(state)}">'
            f'<td class="nowrap"><strong>{e(state)}</strong> <span class="muted small">{e(STATE_NAMES.get(state, ""))}</span></td>'
            f'<td>{link(s.get("url"), s.get("list_name") or "Product list")}'
            f'<div class="muted small">{e(s.get("luminaire_category"))}</div></td>'
            f'<td>{badge(s.get("baba_flag"))}<div class="small">{e(s.get("baba_notes"))}</div></td>'
            f'<td class="small">{link(s.get("buy_america_guidance_url"), "Guidance") if s.get("buy_america_guidance_url") else "—"}</td>'
            f'<td class="small">{badge(st.get("state")) if st else "—"}'
            f'<div class="muted">{e(st.get("checked", ""))}</div></td>'
            "</tr>"
        )
    return "\n".join(rows)


CSS = """
:root{--bg:#f7f8fa;--surface:#fff;--text:#1a1d23;--muted:#5d6573;--border:#dde1e7;--accent:#1f5fbf;
--ok-bg:#e3f4e8;--ok:#1d6b35;--warn-bg:#fdf1dc;--warn:#8a5300;--bad-bg:#fde4e4;--bad:#a32020;--info-bg:#e4edfb;--info:#1f4f9a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121418;--surface:#1b1e24;--text:#e7e9ee;--muted:#9aa3b2;
--border:#2e333c;--accent:#7fb0ff;--ok-bg:#16351f;--ok:#8fdca6;--warn-bg:#3a2c12;--warn:#f2c374;--bad-bg:#3d1818;--bad:#ff9d9d;--info-bg:#172a48;--info:#9cc2ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1280px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.2rem;margin:36px 0 8px}
a{color:var(--accent)}
.muted{color:var(--muted)}.small{font-size:.85rem}.nowrap{white-space:nowrap}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;margin:12px 0}
.stats{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 14px;min-width:150px}
.stat b{display:block;font-size:1.5rem}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
input,select{font:inherit;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text)}
input{flex:1;min-width:200px}
.table-wrap{overflow-x:auto;background:var(--surface);border:1px solid var(--border);border-radius:10px}
table{border-collapse:collapse;width:100%;min-width:760px}
th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid var(--border)}
th{font-size:.8rem;text-transform:uppercase;letter-spacing:.03em;color:var(--muted);background:var(--surface);position:sticky;top:0}
tr:last-child td{border-bottom:0}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:.78rem;font-weight:600;white-space:nowrap}
.ok{background:var(--ok-bg);color:var(--ok)}.warn{background:var(--warn-bg);color:var(--warn)}
.bad{background:var(--bad-bg);color:var(--bad)}.info{background:var(--info-bg);color:var(--info)}
.muted.badge{background:var(--border);color:var(--muted)}
.empty{padding:16px;color:var(--muted)}
footer{margin-top:40px;color:var(--muted);font-size:.85rem}
"""

JS = """
const q=document.getElementById('q'),st=document.getElementById('state');
function apply(){const t=q.value.trim().toLowerCase(),s=st.value;
document.querySelectorAll('tbody tr[data-search]').forEach(r=>{
const ok=(!t||r.dataset.search.includes(t))&&(!s||r.dataset.states.split(' ').includes(s));r.hidden=!ok;});}
q.addEventListener('input',apply);st.addEventListener('change',apply);
"""


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

    prod_headers = ["Manufacturer", "Model / family", "State DOT listing", "US final assembly",
                    ">55% domestic", "Evidence", "Sources", "Verified"]

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
<div class="muted">Roadway &amp; area luminaires on state DOT approved product lists with documented FHWA Buy America compliance · Updated {e(build_date)} · <a href="fixtures.html">Fixture downloads (.ies + cut sheets)</a></div>

<div class="stats">
  <div class="stat"><b>{len(compliant)}</b>Compliant luminaire entries</div>
  <div class="stat"><b>{len(pending)}</b>Awaiting verification</div>
  <div class="stat"><b>{len(states_covered)}</b>State DOT lists indexed</div>
  <div class="stat"><b>{flagged}</b>Lists that flag Buy America</div>
  <div class="stat"><b>{changed}</b>Lists changed since last check</div>
</div>

<div class="card">
<strong>What counts as compliant here.</strong> Under FHWA's manufactured-products rule (23 CFR 635.410), a luminaire
must have <strong>final assembly in the United States</strong> and, for projects obligated on or after Oct 1, 2026,
<strong>domestic components costing more than 55%</strong> of all component cost. An entry appears in the main table
only when it is on at least one state DOT approved list <em>and</em> both tests are documented by the DOT or by the
manufacturer for that product family. This index is a research aid, not a certification: always obtain the
manufacturer's project-specific Buy America certification and confirm with the DOT.
<ul class="small">{dates}</ul>
<div class="small muted">{e(rule.get("changes_since", ""))} {rule_sources}</div>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, model, or state" aria-label="Search">
  <select id="state" aria-label="Filter by state"><option value="">All states</option>{state_opts}</select>
</div>

<h2>Compliant luminaires</h2>
{table(prod_headers, product_rows(compliant), "No entries yet meet both documented tests. See the verification queue below.")}

<h2>Verification queue</h2>
<p class="small muted">On a DOT list, but only one test (or neither) is documented so far, or the claim is not specific to FHWA rules.</p>
{table(prod_headers, product_rows(pending), "Nothing in the queue.")}

<h2>State DOT product lists</h2>
<p class="small muted">"Flags Buy America" means the list itself marks compliance. Weekly check shows whether the list page changed since the previous run.</p>
{table(["State", "Approved product list", "Flags Buy America", "DOT guidance", "Weekly check"], source_rows(sources, status), "No sources yet.")}

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
            page.replace('href="archive/index.html"', 'href="index.html"').replace('href="fixtures.html"', 'href="../fixtures.html"'), encoding="utf-8"
        )
        write_archive_index()
    print(f"Built index.html for {args.date}")


if __name__ == "__main__":
    main()
