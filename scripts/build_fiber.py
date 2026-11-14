#!/usr/bin/env python3
"""Build fiber.html: Corning products documented as BABA compliant, grouped by category.

Reads data/fiber.json. Same one-line-per-row spreadsheet layout as the other pages.

Usage: python3 scripts/build_fiber.py [--date YYYY-MM-DD]
Standard library only.
"""

import argparse
import datetime as dt
import json
import pathlib

from build_site import CSS, ROW_JS, SV_CSS, SV_JS, e, link, numbered_links, site_nav, view_slider, view_table, vtd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

BASIS_BADGE = {
    "stated": ("Stated", "ok"),
    "family": ("Family-level", "info"),
    "not stated": ("Not stated", "warn"),
}

JS = """
const q=document.getElementById('q'),cat=document.getElementById('cat');
function apply(){const t=q.value.trim().toLowerCase(),c=cat.value;let n=0;
document.querySelectorAll('tbody tr[data-search]').forEach(r=>{
const ok=(!t||r.dataset.search.includes(t))&&(!c||r.dataset.cat===c);r.hidden=!ok;if(ok)n++;});
document.querySelectorAll('section[data-cat]').forEach(s=>{s.hidden=!!c&&s.dataset.cat!==c;});
document.getElementById('count').textContent=n;}
q.addEventListener('input',apply);cat.addEventListener('change',apply);
""" + ROW_JS

# (label, slider view): "" = always shown; 1 = product details, 2 = spec sheet and DOT listing, 3 = BABA nuances
HEADERS = [("Product", ""), ("Part number / ordering", ""), ("Fiber", "1"), ("Jacket", "1"), ("Rating", "1"), ("Counts", "1"),
           ("Spec sheet", "2"), ("DOT listing", "2"), ("Sources", "2"), ("Maker BABA", "3"), ("BABA basis", "3"), ("Notes", "3")]


def label(key):
    text, tone = BASIS_BADGE.get(key, (key or "—", "muted"))
    return f'<span class="badge {tone}">{e(text)}</span>'


def row(p, cat_id):
    sheet = p.get("spec_sheet") or {}
    dots = p.get("dot_listings", [])
    dot_cell = "; ".join(f'<strong>{e(d.get("state"))}</strong> ' + link(d.get("url"), d.get("listing_id") or "list")
                         for d in dots) or "—"
    dot_full = "; ".join(f'{d.get("state")}: {d.get("list_name", "")} {d.get("listing_id", "")}' for d in dots)
    ev = p.get("evidence", [])
    notes = " · ".join(p.get("notes", []))
    search = " ".join(str(p.get(k, "")) for k in
                      ["name", "part_number", "fiber", "jacket", "rating", "basis"]).lower() + " " + notes.lower()
    return (
        f'<tr data-search="{e(search)}" data-cat="{e(cat_id)}">'
        + vtd(f"<strong>{e(p.get('name'))}</strong>", "", "", p.get("name"))
        + vtd(e(p.get("part_number")), "", "mono", p.get("part_number"))
        + vtd(e(p.get("fiber", "—")), "1", "", p.get("fiber"))
        + vtd(e(p.get("jacket", "—")), "1")
        + vtd(e(p.get("rating", "—")), "1", "", p.get("rating"))
        + vtd(e(p.get("counts", "—")), "1", "", p.get("counts"))
        + vtd(link(sheet.get("url"), "PDF") if sheet.get("url") else e(sheet.get("title") or "—"), "2", "", sheet.get("title"))
        + vtd(dot_cell, "2", "", dot_full)
        + vtd(numbered_links(ev), "2", "", " | ".join(x.get("summary", "") for x in ev))
        + vtd(label(p.get("corning_baba")), "3", "c-b", p.get("corning_quote"))
        + vtd(e(p.get("basis", "—").split(" (")[0]), "3", "", p.get("basis"))
        + vtd(e(notes), "3", "wide muted", notes)
        + "</tr>"
    )


def render(build_date):
    data = json.loads((DATA / "fiber.json").read_text(encoding="utf-8"))
    cats = data.get("categories", [])
    products = data.get("products", [])
    total = len(products)
    stated = sum(1 for p in products if p.get("corning_baba") == "stated")
    dot_listed = sum(1 for p in products if p.get("dot_listings"))
    cat_opts = "".join(f'<option value="{e(c["id"])}">{e(c["name"])}</option>' for c in cats)
    sections = []
    for c in cats:
        rows = "\n".join(row(p, c["id"]) for p in products if p.get("category") == c["id"])
        sections.append(
            f'<section data-cat="{e(c["id"])}"><h2>{e(c["name"])}</h2>'
            f'<p class="small muted">{e(c.get("description", ""))}</p>'
            f'{view_table(HEADERS, rows, "No products with BABA documentation found yet.")}</section>'
        )
    rules = "".join(f"<li>{r}</li>" for r in data.get("rule_notes_html", []))
    docs = "".join(f"<li>{link(d.get('url'), d.get('title'))} <span class='muted'>{e(d.get('note', ''))}</span></li>"
                   for d in data.get("corning_documents", []))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Fiber Products</title>
<meta name="description" content="Corning fiber products documented as Build America, Buy America (BABA) compliant: traffic cabinet splice housings, orange multimode cable, and G.652 single-mode cable.">
<style>{CSS}{SV_CSS}</style>
</head>
<body class="view1">
<main>
<h1>BABA Fiber Products · Corning</h1>
<div class="muted">Splice housings for traffic and ITS cabinets, orange multimode cable, and G.652 single-mode cable · Updated {e(build_date)}</div>
<div class="small">{site_nav("fiber.html")}</div>

<div class="stats">
  <span><b id="count">{total}</b>products</span>
  <span><b>{dot_listed}</b>on a DOT list as BABA eligible</span>
  <span><b>{stated}</b>with a part-specific Corning BABA statement</span>
  <span><b>{len(cats)}</b>categories</span>
</div>

<div class="card">
<strong>Which rule applies.</strong>
<ul>{rules}</ul>
<strong>Corning documents used</strong>
<ul>{docs}</ul>
<div class="muted">Research aid, not a certification: get Corning's project-specific Buy America certificate for the exact part numbers you order. Use the slider above the tables to switch between product details, spec sheet and DOT listing, and BABA nuances. Rows are two lines each; tap a row to open it and a column header to sort.</div>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search product, part number, or fiber type" aria-label="Search">
  <select id="cat" aria-label="Filter by category"><option value="">Category</option>{cat_opts}</select>
  {view_slider(["Product details", "Spec sheet & DOT listing", "BABA nuances"])}
</div>

{''.join(sections)}

<footer>
Generated by <code>scripts/build_fiber.py</code> from <code>data/fiber.json</code>. Corrections welcome via GitHub issues.
</footer>
</main>
<script>{JS}{SV_JS}</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    ROOT.joinpath("fiber.html").write_text(render(args.date), encoding="utf-8")
    print(f"Built fiber.html for {args.date}")


if __name__ == "__main__":
    main()
