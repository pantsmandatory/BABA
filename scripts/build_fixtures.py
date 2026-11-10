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
FOCUS_BADGE = {
    "twin": ("Phase 2 listed at 120–277V · 480V not printed", "warn"),
    "family": ("Family flagged · this optic/voltage not listed", "warn"),
    "mfr-option": ("Mfr. BABA option (D1) · no DOT listing", "info"),
    "none": ("No DOT Phase 2 statement", "bad"),
}

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


def row(fx, sources, show_listed, main, show_cct=False):
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
    volt = "not shown" if fx.get("voltage_inferred") else volt_label(fx.get("voltage"))
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
        + (td(e(cct_label(fx)), "c-d", "Color temperature printed on the DOT listing") if show_cct else "")
        + (td(e(listed), "c-l mono muted", listed) if show_listed else "")
        + "</tr>"
    )


def focus_row(fx):
    """One Current/Cree row: 480V 3000K photometry plus what the state DOT lists actually say."""
    sheet = fx.get("cut_sheet") or {}
    search = " ".join(str(x) for x in [fx.get("manufacturer"), fx.get("brand"), fx.get("family"), fx.get("catalog"),
                                       fx.get("use"), fx.get("optic"), fx.get("evidence")] if x).lower()
    kind = "LED high mast luminaire" if fx.get("use") == "High mast" else "LED roadway luminaire"
    return (
        f'<tr data-search="{e(search)}" data-type="{kind}" data-state="" data-phase="">'
        + td(badge_for(FOCUS_BADGE, fx.get("status")), "c-b", FOCUS_BADGE.get(fx.get("status"), ("",))[0])
        + td(f"<strong>{e(fx.get('manufacturer'))}</strong>", "c-m", fx.get("manufacturer"))
        + td(e(fx.get("family")), "c-s", fx.get("family"))
        + td(e(fx.get("use")), "c-d")
        + td(e(fx.get("catalog")), "c-cat mono", fx.get("catalog"))
        + td(e(fx.get("voltage")), "c-d", fx.get("voltage"))
        + td(e(fx.get("optic") or "—"), "c-s", fx.get("optic"))
        + td(e(fx.get("watts")), "num")
        + td(f'{fx["lumens"]:,}', "num")
        + td(sheet_cell(sheet), "c-d", sheet.get("title"))
        + td(ies_cell(fx), "c-d", ies_title(fx))
        + td(e(fx.get("evidence")), "c-x muted", fx.get("evidence"))
        + td(e(fx.get("notes")), "c-x muted", fx.get("notes"))
        + "</tr>"
    )


def focus_section(data):
    rows = data.get("focus", [])
    if not rows:
        return ""
    headers = ["Status", "Manufacturer", "Family", "Use", "Catalog number (480V, 3000K)", "Voltage", "Optic", "W",
               "Lumens", "Cut sheet", "Photometry", "What the state DOT lists say", "Notes"]
    out = """<h2 id="current-cree">Current Lighting and Cree Lighting: 480V 3000K photometry and DOT status</h2>
<p class="small muted">Requested search: 480V, 3000K, about 20,000 lumens in Type II and Type III, and high mast at about 250–500W.
<strong>None of these exact 480V configurations is printed on a state DOT list with a Phase 2 statement</strong>, so they are kept out of
the table above. The Status column says how close each one is, and the DOT column quotes what each list says. The only Current
row a DOT prints at 480V with a Phase 2 statement is Caltrans ERL2H12D530DGRAYBL251, in the table above. The Gen 7 ERL2 rows use
Current's own "D1 = BABA Compliant" ordering suffix, which is a manufacturer option to verify with the factory, not a DOT statement. No state DOT states
Phase 2 for any Cree Lighting luminaire. Get the manufacturer's Buy America certification for the exact catalog number.</p>
"""
    for group in dict.fromkeys(f["group"] for f in rows):
        body = "\n".join(focus_row(f) for f in rows if f["group"] == group)
        out += f"<h3>{e(group)}</h3>\n" + table(headers, body, "None.") + "\n"
    return out


def sort_key(f):
    return (f.get("basis") != "as-listed", PHASE_RANK.get(f["dot"].get("phase"), 9),
            f["dot"]["source"] != "tx-mpl-2026-09", f["dot"]["source"],
            f.get("product_type") != "LED roadway luminaire", f.get("manufacturer", "").lower(),
            f.get("family", "").split(" · ")[0], f.get("watts") if isinstance(f.get("watts"), (int, float)) else 0)


def volt_label(v):
    return "120–277V" if v == "120-277" else f"{v}V"


def volt_view(voltage, slug):
    """Strict design: the full list for one voltage, at any color temperature."""
    lab = volt_label(voltage)
    return {
        "file": f"fixtures-{slug}.html", "title": f"BABA Fixture Downloads · {lab}", "filter": {"voltage": voltage},
        "show_cct": True, "volt_label": lab,
        "labels": [lab, "Any color temperature", "Phase 2 only (Oct 1, 2026)"], "order_label": "Catalog number (as listed)",
        "intro": f"Every {lab} configuration that a state DOT list prints, with this exact model number, as Phase 2 compliant "
                 "(US final assembly and more than 55% domestic component cost, for projects obligated on or after Oct 1, 2026), "
                 "at any color temperature. TxDOT's Compliant v5, Alabama's Y2 code and Caltrans's \"55% or higher cost and final "
                 "assembly both in US\" all mean Phase 2. The CCT column shows the color temperature the listing prints.",
    }


VOLT_VIEWS = [volt_view(480, "480v"), volt_view("120-277", "120-277v")]


def cct_label(fx):
    return f'{fx["cct"]}K' if isinstance(fx.get("cct"), int) else "not printed"


def nav(current, strict=False):
    pages = ([("fixtures-480v.html", "480V fixtures"), ("fixtures-120-277v.html", "120–277V fixtures")] if strict else []) + [
        ("fixtures-3k.html", "480V 3000K only" if strict else "Fixtures 3000K"),
        ("fixtures-4k.html", "480V 4000K only" if strict else "Fixtures 4000K"),
        ("index.html", "Compliance index"), ("fiber.html", "Fiber products")]
    return " · ".join(f"<strong>{e(t)}</strong>" if f == current else f'<a href="{f}">{e(t)}</a>' for f, t in pages)


def render(build_date, data, view):
    flt = view["filter"]
    unlisted = data.get("show_unlisted", False)
    if not unlisted:
        # Strict design: only rows whose catalog number is copied from a state DOT list.
        data = dict(data, fixtures=[f for f in data["fixtures"] if f.get("basis") == "as-listed"], focus=[])
        view = dict(view, show_listed=False, show_focus=False, intro=view.get("intro_strict") or view.get("intro", ""))
    sources = {s["id"]: s for s in data.get("sources", [])}
    shown = sorted((f for f in data["fixtures"] if matches(f, flt) and not f.get("voltage_inferred")), key=sort_key)
    family = sorted((f for f in data["fixtures"] if f.get("voltage") == 480 and
                     (f.get("cct") == "unspecified" or (f.get("cct") == flt.get("cct") and f.get("voltage_inferred")))), key=sort_key)
    if not unlisted:
        family = []  # strict design: no listings with a placeholder voltage
    both = shown + family
    types = sorted({f.get("product_type") for f in both})
    type_opts = "".join(f'<option value="{e(t)}">{e(t)}</option>' for t in types)
    states = sorted({sources[f["dot"]["source"]]["state"] for f in both})
    state_opts = "".join(f'<option value="{e(s)}">{e(s)} – {e(STATE_NAMES.get(s, s))}</option>' for s in states)
    phase_opts = "".join(f'<option value="{k}">{e(v[0])}</option>' for k, v in PHASE_BADGE.items()
                         if any(f["dot"].get("phase") == k for f in both))
    focus = data.get("focus", []) if view.get("show_focus") else []
    n_ies = sum(1 for f in shown + focus for i in f.get("ies", []) if has_file(i.get("file")))
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
    if view.get("show_cct"):
        headers.append("CCT")
    if show_listed:
        headers.append("TxDOT-listed catalog (4000K)")
    body = "\n".join(row(f, sources, show_listed, True, view.get("show_cct")) for f in shown)
    family_html = "" if not unlisted else f"""<h2>Flagged listings that don't show 480V or a color temperature</h2>
<p class="small muted">These DOT entries are flagged for Buy America, but the listing itself does not print a 480V voltage code
(it shows a placeholder such as xx*, x or X, or no catalog number at all) or a color temperature. The product family offers a 480V
option, but that is not evidence the listed configuration is 480V; for example, Caltrans spells out its 480V variants separately as
"(480 VAC)". Confirm the exact configuration with the manufacturer and the DOT.</p>
{table([h if h != view["order_label"] else "Listing as published" for h in headers[:14]], chr(10).join(row(f, sources, False, False) for f in family), "None.")}"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(view["title"])}</title>
<meta name="description" content="Roadway, high mast and underpass luminaires that state DOT lists flag for Buy America (BABA), at {e(view.get("volt_label", "480V"))}, with .ies files and cut sheets. {e(", ".join(view.get("labels", [])[:2]))}.">
<style>{CSS}{EXTRA_CSS}</style>
</head>
<body>
<main>
<h1>{e(view["title"])}</h1>
<div class="muted">{e(view.get("volt_label", "480V"))} luminaires that state DOT product lists state are Phase 2 Buy America (BABA) compliant · Updated {e(build_date)}</div>
<div class="small">{nav(view["file"], not unlisted)}</div>

<div class="stats">
  <span class="chips">{chips}</span>
  <span><b id="count">{len(shown)}</b>configurations</span>
  <span><b>{n_p2}</b>flagged Phase 2 (55%)</span>
  <span><b>{n_ies}</b>.ies files</span>
  <span><b>{len(states)}</b>states</span>
</div>

<div class="card">
<strong>How to read this.</strong> {e(view.get("intro", ""))}
<div class="phases"><span>{badge_for(PHASE_BADGE, "phase2")} DOT says US final assembly and more than 55% domestic cost (projects obligated on/after Oct 1, 2026). Only these listings are shown.</span></div>
<span class="muted">Removed 2026-11-09: {data.get("removed_count", 0)} listings that are not Phase 2 (final assembly only, "eligible" or "BAA" with no phase, TxDOT Compliant v4, or project-level certification). They are kept in <code>data/fixtures_removed.json</code>.</span><br>
<span class="muted">{'"As listed" = catalog number copied from the DOT list. "CCT swapped" = TxDOT-listed number with the 3000K option substituted.' if unlisted else 'Every catalog number is copied from the state DOT list as printed; nothing is substituted or inferred.'}
{'The main table only includes listings that print a 480V code (480, 8 for Cooper, HVOLT/HV); flagged listings with a placeholder voltage are in the second table.' if unlisted else ('Only listings that print a 120–277V code (MVOLT, MV, UNV, U, 0, or "120-277 VAC") are included. TxDOT labels its rows 120/240V. Listings with a placeholder voltage, or a voltage code that could not be confirmed as 120–277V, are left out.' if view.get("volt_label") == "120–277V" else 'Only listings that print a 480V code (480, 480 VAC, 8 for Cooper, HVOLT/HV) are included; listings with a placeholder voltage are left out.')} Rows are one line each; tap or click a row to show its full text.</span>
<ul>{src_items}</ul>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, family, catalog number, or state" aria-label="Search">
  <select id="st" aria-label="Filter by state"><option value="">All states</option>{state_opts}</select>
  <select id="ph" aria-label="Filter by BABA status"><option value="">All BABA statuses</option>{phase_opts}</select>
  <select id="type" aria-label="Filter by type"><option value="">All types</option>{type_opts}</select>
</div>

{table(headers, body, "No fixtures match the filter.")}

{family_html}

{focus_section(data) if view.get("show_focus") else ""}

<footer>
Generated by <code>scripts/build_fixtures.py</code> from <code>data/fixtures.json</code>. Photometric files and cut sheet
copies are the manufacturers' published files, kept here for convenience; each links to its source. States researched with no
Buy America-flagged luminaires are summarized on the <a href="index.html">compliance index</a>. This page is a research
aid, not a certification: get the manufacturer's project-specific Buy America certification for the exact catalog number you order.
</footer>
</main>
<script>{JS}</script>
</body>
</html>
"""


def chooser(build_date, unlisted=False):
    """fixtures.html: keeps the old link working and points to the per-voltage (or, in the earlier design, per-CCT) pages."""
    if unlisted:
        items = """<li><a href="fixtures-4k.html"><strong>4000K</strong></a> – TxDOT Compliant v5 and Alabama Y2 listings at 480V.</li>
<li><a href="fixtures-3k.html"><strong>3000K</strong></a> – Caltrans Phase 2 listings at 480V, TxDOT Compliant v5 configurations with the 3000K option swapped in, and <a href="fixtures-3k.html#current-cree">Current Lighting and Cree Lighting 480V 3000K photometry</a> with their DOT status.</li>"""
    else:
        items = """<li><a href="fixtures-480v.html"><strong>480V</strong></a> – TxDOT Compliant v5, Alabama Y2 and Caltrans Phase 2 listings that print a 480V code. Filters: <a href="fixtures-3k.html">3000K</a> · <a href="fixtures-4k.html">4000K</a>.</li>
<li><a href="fixtures-120-277v.html"><strong>120–277V</strong></a> – the same three lists, rows that print a 120–277V code (MVOLT, MV, UNV, U).</li>"""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Fixture Downloads</title><style>{CSS}</style></head><body><main>
<h1>BABA Fixture Downloads</h1>
<div class="muted">Luminaires that state DOT lists state are Buy America compliant for projects obligated on or after Oct 1, 2026, with .ies files and cut sheets · Updated {e(build_date)}</div>
<div class="card"><ul>
{items}
</ul><p class="small muted">Only Phase 2 listings are shown{'' if unlisted else ', with the exact model number the state DOT prints'}.</p></div>
<div class="small"><a href="index.html">Compliance index</a> · <a href="fiber.html">Fiber products</a></div>
</main></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    data = json.loads((DATA / "fixtures.json").read_text(encoding="utf-8"))
    site = json.loads((DATA / "site.json").read_text(encoding="utf-8")) if (DATA / "site.json").exists() else {}
    data["show_unlisted"] = bool(site.get("show_unlisted"))
    for view in data["views"]:
        ROOT.joinpath(view["file"]).write_text(render(args.date, data, view), encoding="utf-8")
        print(f"Built {view['file']} for {args.date}")
    ROOT.joinpath("fixtures.html").write_text(chooser(args.date, data["show_unlisted"]), encoding="utf-8")
    if not data["show_unlisted"]:  # strict design: one full list per voltage, with no color temperature requirement
        for view in VOLT_VIEWS:
            ROOT.joinpath(view["file"]).write_text(render(args.date, data, view), encoding="utf-8")
            print(f"Built {view['file']} for {args.date}")


if __name__ == "__main__":
    main()
