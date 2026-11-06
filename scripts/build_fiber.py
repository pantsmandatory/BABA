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

from build_site import CSS, ROW_JS, e, link, numbered_links, table, td

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

HEADERS = ["Product", "Part number / ordering", "Fiber", "Jacket", "Rating", "Counts", "BABA basis",
           "Corning BABA", "DOT listing", "Spec sheet", "Sources", "Notes"]


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
        + td(f"<strong>{e(p.get('name'))}</strong>", "c-l", p.get("name"))
        + td(e(p.get("part_number")), "c-cat mono", p.get("part_number"))
        + td(e(p.get("fiber", "—")), "c-s", p.get("fiber"))
        + td(e(p.get("jacket", "—")), "c-d")
        + td(e(p.get("rating", "—")), "c-s", p.get("rating"))
        + td(e(p.get("counts", "—")), "c-s", p.get("counts"))
        + td(e(p.get("basis", "—")), "c-s", p.get("basis"))
        + td(label(p.get("corning_baba")), "c-b", p.get("corning_quote"))
        + td(dot_cell, "c-l", dot_full)
        + td(link(sheet.get("url"), "PDF") if sheet.get("url") else "—", "c-d", sheet.get("title"))
        + td(numbered_links(ev), "c-n", " | ".join(x.get("summary", "") for x in ev))
        + td(e(notes), "c-x muted", notes)
        + "</tr>"
    )


def render(build_date):
    data = json.loads((DATA / "fiber.json").read_text(encoding="utf-8"))
    cats = data.get("categories", [])
    products = data.get("products", [])
    total = len(products)
    stated = sum(1 for p in products if p.get("corning_baba") == "stated")
    cat_opts = "".join(f'<option value="{e(c["id"])}">{e(c["name"])}</option>' for c in cats)
    sections = []
    for c in cats:
        rows = "\n".join(row(p, c["id"]) for p in products if p.get("category") == c["id"])
        sections.append(
            f'<section data-cat="{e(c["id"])}"><h2>{e(c["name"])}</h2>'
            f'<p class="small muted">{e(c.get("description", ""))}</p>'
            f'{table(HEADERS, rows, "No Corning products with BABA documentation found yet.")}</section>'
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
<style>{CSS}</style>
</head>
<body>
<main>
<h1>BABA Fiber Products · Corning</h1>
<div class="muted">Splice housings for traffic and ITS cabinets, orange multimode cable, and G.652 single-mode cable · Updated {e(build_date)} · <a href="index.html">Luminaire index</a> · <a href="fixtures.html">Fixture downloads</a></div>

<div class="stats">
  <span><b id="count">{total}</b>products</span>
  <span><b>{stated}</b>with a product-specific Corning BABA statement</span>
  <span><b>{len(cats)}</b>categories</span>
</div>

<div class="card">
<strong>Which rule applies.</strong>
<ul>{rules}</ul>
<strong>Corning documents used</strong>
<ul>{docs}</ul>
<div class="muted">Research aid, not a certification: get Corning's project-specific Buy America certificate for the exact part numbers you order. Rows are one line each; tap or click a row to show its full text.</div>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search product, part number, or fiber type" aria-label="Search">
  <select id="cat" aria-label="Filter by category"><option value="">All categories</option>{cat_opts}</select>
</div>

{''.join(sections)}

<footer>
Generated by <code>scripts/build_fiber.py</code> from <code>data/fiber.json</code>. Corrections welcome via GitHub issues.
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
    ROOT.joinpath("fiber.html").write_text(render(args.date), encoding="utf-8")
    print(f"Built fiber.html for {args.date}")


if __name__ == "__main__":
    main()
