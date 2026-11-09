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

from build_site import CSS, ROW_JS, e, link, table, td

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

STATUS_BADGE = {
    "Compliant v5": ("v5 · Phase 2", "ok"),
    "Compliant v4": ("v4 · Phase 1", "warn"),
}

EXTRA_CSS = """
.chips{display:inline-flex;flex-wrap:wrap;gap:4px;vertical-align:middle}
.chip{background:var(--info-bg);color:var(--info);border-radius:999px;padding:0 8px;font-size:11px;font-weight:600}
"""

JS = """
const q=document.getElementById('q'),ty=document.getElementById('type');
function apply(){const t=q.value.trim().toLowerCase(),y=ty.value;let n=0;
document.querySelectorAll('tbody tr[data-search]').forEach(r=>{
const ok=(!t||r.dataset.search.includes(t))&&(!y||r.dataset.type===y);r.hidden=!ok;if(ok)n++;});
document.getElementById('count').textContent=n;}
q.addEventListener('input',apply);ty.addEventListener('change',apply);
""" + ROW_JS


def matches(fx, flt):
    return all(fx.get(k) == v for k, v in flt.items())


def has_file(path):
    return bool(path) and (ROOT / path).exists()


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


def ies_title(fx, cct_label):
    return " | ".join(
        " · ".join(str(x) for x in [pathlib.Path(f.get("file", "")).name, f.get("lumcat"), f.get("note")] if x)
        for f in fx.get("ies", [])
    ) or f"No {cct_label} .ies published; request from manufacturer."


def row(fx, sources, view):
    d = fx["dot"]
    src = sources.get(d["source"], {})
    label, tone = STATUS_BADGE.get(d.get("status"), (d.get("status"), "muted"))
    sheet = fx.get("cut_sheet") or {}
    kind = "High mast" if "high mast" in fx.get("product_type", "") else "Roadway"
    if d.get("application"):
        kind += f' {d["application"]}'
    dot = f'<strong>{e(src.get("state"))}</strong> ' + link(src.get("url"), d.get("table") or src.get("short_name"))
    lumens = fx.get("lumens")
    lm = (("≈" if fx.get("lumens_estimated") else "") + f"{lumens:,}") if lumens else "—"
    notes = " · ".join(fx.get("caveats", []))
    search = " ".join([fx.get("manufacturer", ""), fx.get("brand", ""), fx.get("family", ""),
                       fx.get("catalog", ""), d.get("listed_catalog", ""), kind, src.get("state", "")]).lower()
    who = fx.get("manufacturer", "") + (f' · {fx["brand"]}' if fx.get("brand") else "")
    return (
        f'<tr data-search="{e(search)}" data-type="{e(fx.get("product_type"))}">'
        + td(f"<strong>{e(fx.get('manufacturer'))}</strong>", "c-m", who)
        + td(e(fx.get("family")), "c-l", fx.get("family"))
        + td(e(kind), "c-d")
        + td(dot, "c-d", src.get("name"))
        + td(f'<span class="badge {tone}">{e(label)}</span>', "c-b", d.get("status"))
        + td(e(fx.get("catalog")), "c-cat mono", fx.get("catalog"))
        + td(e(fx.get("distribution")), "c-s", fx.get("distribution"))
        + td(e(fx.get("watts") if fx.get("watts") is not None else "—"), "num")
        + td(e(lm), "num", "Estimated" if fx.get("lumens_estimated") else None)
        + td(sheet_cell(sheet), "c-d", sheet.get("title"))
        + td(ies_cell(fx), "c-d", ies_title(fx, view["cct_label"]))
        + td(e(notes), "c-x muted", notes)
        + (td(e(d.get("listed_catalog")), "c-l mono muted", f'{d.get("listed_cct", "")}: {d.get("listed_catalog", "")}')
           if view.get("show_listed") else "")
        + "</tr>"
    )


def nav(current):
    pages = [("fixtures-3k.html", "Fixtures 3000K"), ("fixtures-4k.html", "Fixtures 4000K (TxDOT as listed)"),
             ("index.html", "Compliance index"), ("fiber.html", "Fiber products")]
    return " · ".join(f"<strong>{e(t)}</strong>" if f == current else f'<a href="{f}">{e(t)}</a>' for f, t in pages)


def render(build_date, data, view):
    flt = view["filter"]
    sources = {s["id"]: s for s in data.get("sources", [])}
    shown = [f for f in data.get("fixtures", []) if matches(f, flt)]
    shown.sort(key=lambda f: (f.get("product_type") != "LED roadway luminaire",
                              f.get("manufacturer", "").lower(), f.get("family", "").split(" · ")[0], f.get("watts") or 0))
    types = sorted({f.get("product_type") for f in shown})
    type_opts = "".join(f'<option value="{e(t)}">{e(t)}</option>' for t in types)
    n_ies = sum(1 for f in shown for i in f.get("ies", []) if has_file(i.get("file")))
    chips = "".join(f'<span class="chip">{e(c)}</span>' for c in view.get("labels", []))
    src_items = "".join(
        f"<li><strong>{e(s['state'])}</strong> – {link(s.get('url'), s.get('name'))} "
        f"<span class='muted'>({e(s.get('edition', ''))})</span>. {e(s.get('status_note', ''))}</li>"
        for s in sources.values()
    )
    headers = ["Manufacturer", "Family", "Use", "DOT list", "Status", view["order_label"],
               "Optic", "W", "Lumens", "Cut sheet", "Photometry", "Notes"]
    if view.get("show_listed"):
        headers.append("DOT-listed catalog (4000K)")
    body = "\n".join(row(f, sources, view) for f in shown)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(view["title"])}</title>
<meta name="description" content="BABA-compliant roadway and high mast luminaires from state DOT approved lists, with .ies photometric files and manufacturer cut sheets. Showing {e(", ".join(view.get("labels", [])[:3]))} variants.">
<style>{CSS}{EXTRA_CSS}</style>
</head>
<body>
<main>
<h1>{e(view["title"])}</h1>
<div class="muted">Luminaires a state DOT lists as Buy America (BABA) compliant, with photometry and cut sheets · Updated {e(build_date)}</div>
<div class="small">{nav(view["file"])}</div>

<div class="stats">
  <span class="chips">{chips}</span>
  <span><b id="count">{len(shown)}</b>fixtures</span>
  <span><b>{n_ies}</b>.ies files</span>
  <span><b>{len(sources)}</b>DOT source list{'s' if len(sources) != 1 else ''}</span>
</div>

<div class="card">
<strong>How to read this.</strong> Each row is a configuration a state DOT lists as <strong>Compliant v5</strong>: the
manufacturer certified it for federal-aid projects obligated on or after Oct 1, 2026 (US final assembly and more than
55% domestic component cost). {e(view.get("intro", ""))} Rows are one line each; tap or click a row to show its full text.
<ul>{src_items}</ul>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, family, or catalog number" aria-label="Search">
  <select id="type" aria-label="Filter by type"><option value="">All types</option>{type_opts}</select>
</div>

{table(headers, body, "No fixtures match the filter.")}

<footer>
Generated by <code>scripts/build_fixtures.py</code> from <code>data/fixtures.json</code>. Photometric files and cut sheet
copies are the manufacturers' published files, kept here for convenience; each links to its source. This page is a
research aid, not a certification: get the manufacturer's project-specific Buy America certification for the exact
catalog number you order.
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
<div class="muted">TxDOT Compliant v5 luminaires at 480V with .ies files and cut sheets · Updated {e(build_date)}</div>
<div class="card"><ul>
<li><a href="fixtures-4k.html"><strong>4000K</strong></a> – catalog numbers exactly as TxDOT lists them (Compliant v5).</li>
<li><a href="fixtures-3k.html"><strong>3000K</strong></a> – the same configurations with the 3000K / 70 CRI option swapped in; confirm Buy America certification with the manufacturer.</li>
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
