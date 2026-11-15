#!/usr/bin/env python3
"""Build conduit.html: conduit that a state DOT list flags for Buy America, starting with 2-inch HDPE and 2-inch RMC.

Reads data/conduit.json. Steel rigid metal conduit is an iron or steel product (23 CFR 635.410(b)); HDPE conduit is a
construction material (2 CFR 184.6(a)(2)). Neither has the 55% test that applies to manufactured products.
Each table has its own three-position slider; moving one moves all of them.

Usage: python3 scripts/build_conduit.py [--date YYYY-MM-DD]
Standard library only.
"""

import argparse
import datetime as dt
import json
import pathlib

from build_site import CSS, ROW_JS, STATE_NAMES, SV_CSS, SV_JS, e, link, site_nav, view_slider, view_table, vtd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SLIDER_LABELS = ["Product details", "DOT listing", "Buy America nuances"]
# (label, slider view): "" = always shown
HEADERS = [("Manufacturer", ""), ("Order code / listing as printed", ""),
           ("Type", "1"), ("Size", "1"), ("Plant or office printed", "1"),
           ("DOT list", "2"), ("Status", "2"), ("Edition", "2"),
           ("Rule that applies", "3"), ("Notes", "3")]

JS = """
const q=document.getElementById('q'),sf=document.getElementById('st');
function apply(){const t=q.value.trim().toLowerCase(),s=sf.value;let n=0;
document.querySelectorAll('tbody tr[data-search]').forEach(r=>{const ok=(!t||r.dataset.search.includes(t))&&(!s||r.dataset.state===s);r.hidden=!ok;if(ok)n++;});
document.getElementById('count').textContent=n;}
q.addEventListener('input',apply);sf.addEventListener('change',apply);
""" + ROW_JS


def row(r, rules):
    rule = rules.get(r.get("rule"), {})
    search = " ".join(str(r.get(k, "")) for k in ("manufacturer", "order_code", "type", "size", "location", "state", "status")).lower() \
        + " " + STATE_NAMES.get(r.get("state", ""), "").lower() + " " + " ".join(r.get("notes", [])).lower()
    notes = " · ".join(r.get("notes", [])) or "—"
    dot = f'<strong>{e(r.get("state"))}</strong> ' + link(r.get("list_url"), r.get("list_short") or "list")
    return (
        f'<tr data-search="{e(search)}" data-state="{e(r.get("state", ""))}">'
        + vtd(f"<strong>{e(r.get('manufacturer'))}</strong>", "", "", r.get("manufacturer"))
        + vtd(e(r.get("order_code")), "", "mono", r.get("order_code"))
        + vtd(e(r.get("type") or "—"), "1")
        + vtd(e(r.get("size") or "—"), "1")
        + vtd(e(r.get("location") or "—"), "1", "", r.get("location"))
        + vtd(dot, "2", "", r.get("list_name"))
        + vtd(f'<span class="badge {e(r.get("status_tone", "ok"))}">{e(r.get("status"))}</span>', "2", "c-b", r.get("status_means"))
        + vtd(e(r.get("edition") or "—"), "2")
        + vtd(link(rule.get("url"), rule.get("cite")) if rule else "—", "3", "", rule.get("short"))
        + vtd(e(notes), "3", "wide muted", notes)
        + "</tr>"
    )


def render(build_date):
    data = json.loads((DATA / "conduit.json").read_text(encoding="utf-8"))
    rules = {r["id"]: r for r in data.get("rules", [])}
    rows = data.get("rows", [])
    states = sorted({r.get("state") for r in rows if r.get("state")})
    state_opts = "".join(f'<option value="{e(s)}">{e(s)} – {e(STATE_NAMES.get(s, s))}</option>' for s in states)
    sections = []
    for sec in data.get("sections", []):
        body = "\n".join(row(r, rules) for r in rows if r.get("section") == sec["id"])
        sections.append(
            f'<section data-sec="{e(sec["id"])}"><h2 id="{e(sec["id"])}">{e(sec["name"])}</h2>'
            f'<p class="small muted">{e(sec.get("description", ""))}</p>'
            f'{view_slider(SLIDER_LABELS)}'
            f'{view_table(HEADERS, body, "No state DOT list found yet that flags this conduit for Buy America.")}</section>'
        )
    rule_rows = "".join(
        f"<tr><td>{e(r.get('applies_to'))}</td><td class='nowrap'>{link(r.get('url'), r.get('cite'))}</td><td>{e(r.get('text'))}</td></tr>"
        for r in data.get("rules", []))
    src_items = "".join(f"<li><strong>{e(s.get('state'))}</strong> – {link(s.get('url'), s.get('name'))} "
                        f"<span class='muted'>({e(s.get('edition', ''))})</span>. {e(s.get('note', ''))}</li>" for s in data.get("sources", []))
    n_makers = len({r.get("manufacturer") for r in rows})
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BABA Conduit</title>
<meta name="description" content="2-inch HDPE conduit and 2-inch rigid metal conduit that state DOT lists flag as Buy America compliant, with the CFR sections that apply to each material.">
<style>{CSS}{SV_CSS}</style>
</head>
<body class="view1">
<main>
<h1>BABA Conduit · 2-inch HDPE and RMC</h1>
<div class="muted">Conduit that state DOT lists flag for Buy America, with the rule that applies to each material · Updated {e(build_date)}</div>
<div class="small">{site_nav("conduit.html")}</div>

<div class="stats">
  <span><b id="count">{len(rows)}</b>listings</span>
  <span><b>{n_makers}</b>manufacturers</span>
  <span><b>{len(states)}</b>states</span>
  <span><a href="leads.html#conduit">Other makers and unconfirmed listings: leads page</a></span>
</div>

<details class="card" style="padding:6px 14px">
<summary style="cursor:pointer"><strong>Which rule applies</strong> · sources <span class="muted">(tap to open)</span></summary>
<p>{e(data.get("intro", ""))}</p>
<ul>{src_items}</ul>
<div class="muted">Each table has its own slider, and moving one moves all of them. Rows are two lines each; tap a row to open it and a column header to sort.
Research aid, not a certification: get the manufacturer's Buy America certificate for the exact product and plant.</div>
</details>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, order code, or state" aria-label="Search">
  <select id="st" aria-label="Filter by state"><option value="">State</option>{state_opts}</select>
</div>

{''.join(sections)}

<h2 id="cfr">CFR references for conduit</h2>
<p class="small muted">Quoted from eCFR ({e(data.get("cfr_checked", ""))}). Confirm the current text, and any waiver, with FHWA before relying on it.</p>
<div class="table-wrap"><table class="cfr"><thead><tr><th>Applies to</th><th>Citation</th><th>Rule text</th></tr></thead><tbody>{rule_rows}</tbody></table></div>

<footer>
Generated by <code>scripts/build_conduit.py</code> from <code>data/conduit.json</code>. This page is a research aid, not a certification.
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
    ROOT.joinpath("conduit.html").write_text(render(args.date), encoding="utf-8")
    print(f"Built conduit.html for {args.date}")


if __name__ == "__main__":
    main()
