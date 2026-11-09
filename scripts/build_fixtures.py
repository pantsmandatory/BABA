#!/usr/bin/env python3
"""Build fixtures.html: BABA-compliant fixtures from state DOT lists, with .ies files and cut sheets.

Reads data/fixtures.json and shows only the fixtures that match its "filter" block
(for now 3000K, 480V, 70 CRI). Photometric files live in ies/<manufacturer>/.
Laid out like a spreadsheet: one line per fixture; click a row to see its full text.

Usage: python3 scripts/build_fixtures.py [--date YYYY-MM-DD]
Standard library only.
"""

import argparse
import datetime as dt
import json
import pathlib

from build_site import CSS, ROW_JS, STATE_NAMES, e, link, table, td

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

PHASE_BADGE = {
    "phase2": ("Phase 2 · 55%", "ok"),
    "phase1": ("Phase 1 only", "warn"),
    "eligible-unspecified": ("Eligible · no phase", "info"),
    "project-level": ("Project cert.", "muted"),
}
PHASE_RANK = {"phase2": 0, "phase1": 1, "eligible-unspecified": 2, "project-level": 3}
BASIS_BADGE = {"as-listed": ("As listed", "ok"), "cct-swapped": ("CCT swapped", "warn")}

EXTRA_CSS = """
.chips{display:inline-flex;flex-wrap:wrap;gap:4px;vertical-align:middle}
.chip{background:var(--info-bg);color:var(--info);border-radius:999px;padding:0 8px;font-size:11px;font-weight:600}
.phases{display:flex;flex-wrap:wrap;gap:4px 14px;margin:4px 0}
"""

JS = """
const q=document.getElementById('q'),ty=document.getElementById('type'),sf=document.getElementById('st'),ph=document.getElementById('ph');
function apply(){const t=q.value.trim().toLowerCase(),y=ty.value,s=sf.value,p=ph.value;let n=0;
document.querySelectorAll('tbody tr[data-search]').forEach(r=>{
const ok=(!t||r.dataset.search.includes(t))&&(!y||r.dataset.type===y)&&(!s||r.dataset.state===s)&&(!p||r.dataset.phase===p);
r.hidden=!ok;if(ok&&r.dataset.main)n++;});
document.getElementById('count').textContent=n;}
[q,ty,sf,ph].forEach(x=>x.addEventListener(x===q?'input':'change',apply));
""" + ROW_JS


def matches(fx, flt):
    return all(fx.get(k) == v for k, v in flt.items())


def has_file(path):
    return bool(path) and (ROOT / path).exists()


def badge_for(table, key):
    text, tone = table.get(key, (key or "—", "muted"))
    return f'<span class="badge {tone}">{e(text)}</span>'


def sheet_cell(sheet):
    if not sheet.get("url"):
        return "—"
    out = link(sheet["url"], "PDF")
    if has_file(sheet.get("file")):
        out += f' · <a href="{e(sheet["file"])}" download>copy</a>'
    return out


def ies_cell(fx):
    parts = []
    for f in fx.get("ies", []):
        if has_file(f.get("file")):
            parts.append(f'<a href="{e(f["file"])}" download>⬇ .ies</a>')
        if f.get("source_url"):
            parts.append(link(f["source_url"], "src"))
    return " · ".join(parts) if parts else '<span class="muted">request</span>'


def ies_title(fx):
    return " | ".join(
        " · ".join(str(x) for x in [pathlib.Path(f.get("file", "")).name, f.get("lumcat"), f.get("note")] if x)
        for f in fx.get("ies", [])
    ) or "No .ies published for this exact configuration; request from manufacturer."


def use_label(fx):
    pt = fx.get("product_type", "")
    kind = "High mast" if "high mast" in pt else "Underpass" if "underpass" in pt else "Roadway"
    app = fx["dot"].get("application")
    return kind + (f" {app}" if app else "")


def row(fx, sources, show_listed, main):
    d = fx["dot"]
    src = sources.get(d["source"], {})
    st = src.get("state", "")
    label = PHASE_BADGE.get(d.get("phase"), (d.get("status"), "muted"))
    if d["source"] == "tx-mpl-2026-09":
        label = ("v5 · Phase 2", "ok")
    sheet = fx.get("cut_sheet") or {}
    kind = use_label(fx)
    where = d.get("table") or src.get("short_name")
    dot = f"<strong>{e(st)}</strong> " + link(d.get("list_url") or src.get("url"), where)
    lumens = fx.get("lumens")
    lm = (("≈" if fx.get("lumens_estimated") else "") + f"{lumens:,}") if isinstance(lumens, (int, float)) else "—"
    watts = fx.get("watts")
    notes = " · ".join(fx.get("caveats", []))
    volt = "not shown" if fx.get("voltage_inferred") else "480V"
    search = " ".join(str(x) for x in [fx.get("manufacturer"), fx.get("brand"), fx.get("family"), fx.get("catalog"),
                                       d.get("listed_catalog"), kind, st, STATE_NAMES.get(st, ""), notes] if x).lower()
    who = fx.get("manufacturer", "") + (f' · {fx["brand"]}' if fx.get("brand") else "")
    listed = d.get("listed_catalog") if fx.get("basis") == "cct-swapped" else "—"
    return (
        f'<tr data-search="{e(search)}" data-type="{e(fx.get("product_type"))}" data-state="{e(st)}" '
        f'data-phase="{e(d.get("phase", ""))}"{" data-main=1" if main else ""}>'
        + td(dot, "c-l", f'{src.get("name", "")} · {d.get("table", "")}')
        + td(f'<span class="badge {label[1]}">{e(label[0])}</span>', "c-b", d.get("status"))
        + td(f"<strong>{e(fx.get('manufacturer'))}</strong>", "c-m", who)
        + td(e(fx.get("family")), "c-s", fx.get("family"))
        + td(e(kind), "c-d")
        + td(e(fx.get("catalog")), "c-cat mono", fx.get("catalog"))
        + td(badge_for(BASIS_BADGE, fx.get("basis")), "c-b")
        + td(e(volt), "c-d", "Not shown on the DOT listing (placeholder voltage code); 480V is only an available option for the family" if fx.get("voltage_inferred") else None)
        + td(e(fx.get("distribution") or "—"), "c-s", fx.get("distribution"))
        + td(e(watts if watts not in (None, "") else "—"), "num")
        + td(e(lm), "num", "Estimated" if fx.get("lumens_estimated") else None)
        + td(sheet_cell(sheet), "c-d", sheet.get("title"))
        + td(ies_cell(fx), "c-d", ies_title(fx))
        + td(e(notes), "c-x muted", notes)
        + (td(e(listed), "c-l mono muted", listed) if show_listed else "")
        + "</tr>"
    )


def sort_key(f):
    return (f.get("basis") != "as-listed", PHASE_RANK.get(f["dot"].get("phase"), 9),
            f["dot"]["source"] != "tx-mpl-2026-09", f["dot"]["source"],
            f.get("product_type") != "LED roadway luminaire", f.get("manufacturer", "").lower(),
            f.get("family", "").split(" · ")[0], f.get("watts") if isinstance(f.get("watts"), (int, float)) else 0)


def nav(current):
    pages = [("fixtures-3k.html", "Fixtures 3000K"), ("fixtures-4k.html", "Fixtures 4000K"),
             ("index.html", "Compliance index"), ("fiber.html", "Fiber products")]
    return " · ".join(f"<strong>{e(t)}</strong>" if f == current else f'<a href="{f}">{e(t)}</a>' for f, t in pages)


def render(build_date, data, view):
    flt = view["filter"]
    sources = {s["id"]: s for s in data.get("sources", [])}
    shown = sorted((f for f in data["fixtures"] if matches(f, flt) and not f.get("voltage_inferred")), key=sort_key)
    family = sorted((f for f in data["fixtures"] if f.get("voltage") == 480 and
                     (f.get("cct") == "unspecified" or (f.get("cct") == flt["cct"] and f.get("voltage_inferred")))), key=sort_key)
    both = shown + family
    types = sorted({f.get("product_type") for f in both})
    type_opts = "".join(f'<option value="{e(t)}">{e(t)}</option>' for t in types)
    states = sorted({sources[f["dot"]["source"]]["state"] for f in both})
    state_opts = "".join(f'<option value="{e(s)}">{e(s)} – {e(STATE_NAMES.get(s, s))}</option>' for s in states)
    phase_opts = "".join(f'<option value="{k}">{e(v[0])}</option>' for k, v in PHASE_BADGE.items())
    n_ies = sum(1 for f in shown for i in f.get("ies", []) if has_file(i.get("file")))
    n_p2 = sum(1 for f in shown if f["dot"].get("phase") == "phase2")
    chips = "".join(f'<span class="chip">{e(c)}</span>' for c in view.get("labels", []))
    used = {f["dot"]["source"] for f in both}
    src_items = "".join(
        f"<li><strong>{e(s['state'])}</strong> – {link(s.get('url'), s.get('name'))} "
        f"<span class='muted'>({e(s.get('edition', ''))})</span>. {e(s.get('status_note', ''))}</li>"
        for s in sorted(sources.values(), key=lambda s: s["state"]) if s["id"] in used
    )
    show_listed = view.get("show_listed")
    headers = ["DOT list", "BABA status", "Manufacturer", "Family", "Use", view["order_label"], "Catalog basis",
               "Voltage", "Optic", "W", "Lumens", "Cut sheet", "Photometry", "Notes"]
    if show_listed:
        headers.append("TxDOT-listed catalog (4000K)")
    body = "\n".join(row(f, sources, show_listed, True) for f in shown)
    fam_headers = [h if h != view["order_label"] else "Listing as published" for h in headers[:14]]
    fam_body = "\n".join(row(f, sources, False, False) for f in family)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(view["title"])}</title>
<meta name="description" content="Roadway, high mast and underpass luminaires that state DOT lists flag for Buy America (BABA), at 480V, with .ies files and cut sheets. {e(", ".join(view.get("labels", [])[:2]))}.">
<style>{CSS}{EXTRA_CSS}</style>
</head>
<body>
<main>
<h1>{e(view["title"])}</h1>
<div class="muted">480V luminaires that state DOT product lists flag for Buy America (BABA) · Updated {e(build_date)}</div>
<div class="small">{nav(view["file"])}</div>

<div class="stats">
  <span class="chips">{chips}</span>
  <span><b id="count">{len(shown)}</b>configurations</span>
  <span><b>{n_p2}</b>flagged Phase 2 (55%)</span>
  <span><b>{n_ies}</b>.ies files</span>
  <span><b>{len(states)}</b>states</span>
</div>

<div class="card">
<strong>How to read this.</strong> {e(view.get("intro", ""))}
<div class="phases">{''.join(f'<span>{badge_for(PHASE_BADGE, k)} {e(t)}</span>' for k, t in [
    ("phase2", "DOT says US final assembly and more than 55% domestic cost (projects obligated on/after Oct 1, 2026)"),
    ("phase1", "final assembly only; not enough after Oct 1, 2026"),
    ("eligible-unspecified", "DOT flags it BABA/BAA without saying which phase"),
    ("project-level", "DOT has not verified; certify per project")])}</div>
<span class="muted">"As listed" = catalog number copied from the DOT list. "CCT swapped" = TxDOT-listed number with the 3000K option substituted.
The main table only includes listings that print a 480V code (480, 8 for Cooper, HVOLT/HV); flagged listings with a placeholder voltage are in the second table. Rows are one line each; tap or click a row to show its full text.</span>
<ul>{src_items}</ul>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, family, catalog number, or state" aria-label="Search">
  <select id="st" aria-label="Filter by state"><option value="">All states</option>{state_opts}</select>
  <select id="ph" aria-label="Filter by BABA status"><option value="">All BABA statuses</option>{phase_opts}</select>
  <select id="type" aria-label="Filter by type"><option value="">All types</option>{type_opts}</select>
</div>

{table(headers, body, "No fixtures match the filter.")}

<h2>Flagged listings that don't show 480V or a color temperature</h2>
<p class="small muted">These DOT entries are flagged for Buy America, but the listing itself does not print a 480V voltage code
(it shows a placeholder such as xx*, x or X, or no catalog number at all) or a color temperature. The product family offers a 480V
option, but that is not evidence the listed configuration is 480V; for example, Caltrans spells out its 480V variants separately as
"(480 VAC)". Confirm the exact configuration with the manufacturer and the DOT.</p>
{table(fam_headers, fam_body, "None.")}

<footer>
Generated by <code>scripts/build_fixtures.py</code> from <code>data/fixtures.json</code>. Photometric files and cut sheet
copies are the manufacturers' published files, kept here for convenience; each links to its source. States researched with no
480V Buy America-flagged luminaires are summarized on the <a href="index.html">compliance index</a>. This page is a research
aid, not a certification: get the manufacturer's project-specific Buy America certification for the exact catalog number you order.
</footer>
</main>
<script>{JS}</script>
</body>
</html>
"""


def chooser(build_date):
    """fixtures.html: keeps the old link working and points to the 3000K and 4000K pages."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Fixture Downloads</title><style>{CSS}</style></head><body><main>
<h1>BABA Fixture Downloads</h1>
<div class="muted">480V luminaires flagged for Buy America on state DOT lists, with .ies files and cut sheets · Updated {e(build_date)}</div>
<div class="card"><ul>
<li><a href="fixtures-4k.html"><strong>4000K</strong></a> – TxDOT Compliant v5, Alabama Y2 and North Carolina listings at 480V.</li>
<li><a href="fixtures-3k.html"><strong>3000K</strong></a> – Caltrans, Washington and Missouri listings at 480V, plus TxDOT configurations with the 3000K option swapped in.</li>
</ul></div>
<div class="small"><a href="index.html">Compliance index</a> · <a href="fiber.html">Fiber products</a></div>
</main></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    data = json.loads((DATA / "fixtures.json").read_text(encoding="utf-8"))
    for view in data["views"]:
        ROOT.joinpath(view["file"]).write_text(render(args.date, data, view), encoding="utf-8")
        print(f"Built {view['file']} for {args.date}")
    ROOT.joinpath("fixtures.html").write_text(chooser(args.date), encoding="utf-8")


if __name__ == "__main__":
    main()
