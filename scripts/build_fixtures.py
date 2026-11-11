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
import re

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
button{font:inherit;font-weight:600;padding:5px 12px;border:1px solid var(--accent);border-radius:6px;background:var(--surface);color:var(--accent);cursor:pointer}
button[aria-pressed="true"]{background:var(--accent);color:var(--surface)}
table.fx .r,table.fx .o3{display:none}
body.ref table.fx .m{display:none}
body.ref table.fx .r{display:table-cell}
body.ref table.fx td.r{white-space:normal;overflow:visible}
body.ref table.fx td.c-cat{white-space:normal;word-break:break-all}
body.ref table.fx td.c-l{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px}
body.ref table.fx tr.open td.c-l{white-space:normal;overflow:visible}
/* View 3: one line per row. Order code plus DOT list, BABA status and notes; notes are cut with an ellipsis.
   If the full order code leaves no room, the script adds body.short and the 4-character model code shows instead. */
body.one table.fx .m{display:none}
body.one table.fx .r.o,body.one table.fx .o3{display:table-cell}
body.one table.fx th,body.one table.fx td{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
body.one table.fx td.c-cat{min-width:0;overflow:visible;word-break:normal;overflow-wrap:normal}
body.one table.fx td.c-l{max-width:190px}
body.one table.fx td.c-x{max-width:0;width:100%;min-width:0}
body.one table.fx tr.open td{white-space:normal;overflow:visible}
.cs{display:none;font-weight:700}
body.one.short .cf{display:none}
body.one.short .cs{display:inline}
.views{flex:1 1 100%;max-width:560px;margin-top:2px}
.vlabels{display:flex;justify-content:space-between;gap:8px;font-size:12px;font-weight:600;color:var(--muted)}
.vlabels span{flex:1;cursor:pointer;line-height:1.2}
.vlabels span:nth-child(2){text-align:center}.vlabels span:nth-child(3){text-align:right}
.vlabels span.on{color:var(--accent)}
#view{display:block;width:100%;min-width:0;padding:0;margin:4px 0 0;border:0;background:transparent;accent-color:var(--accent);height:26px}
/* Every screen: cells wrap so a whole row shows with no sideways scrolling. The script below logs the screen
   size and steps the table text size down (--fx) until the table fits the window. */
table.fx{font-size:var(--fx,12.5px)}
table.fx th,table.fx td{white-space:normal;overflow:visible;max-width:none;min-width:0}
table.fx td.c-cat,table.fx td.mono{overflow-wrap:anywhere;font-size:.92em}
table.fx td.c-cat{min-width:150px}
table.fx td.c-b,table.fx td.num{white-space:nowrap}
body.compact main{padding:8px 8px 32px}
body.compact table.fx th,body.compact table.fx td{padding:2px 4px}
body.compact table.fx th{font-size:9.5px;letter-spacing:0}
body.compact.ref table.fx td.c-x{min-width:80px}
body.compact.ref table.fx td.c-cat{min-width:110px}
body.compact table.fx td.c-cat,body.compact table.fx td.mono{word-break:break-all}
#screeninfo{font-variant-numeric:tabular-nums}
/* Phone held upright: a rotate-your-phone picture. First tap makes it half transparent, second tap removes it. */
#turn{display:none;position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:20;width:112px;height:112px;border-radius:50%;
background:var(--accent);color:var(--surface);border:0;padding:14px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.3);transition:opacity .2s}
#turn svg{width:100%;height:100%;display:block}
body.turn #turn{display:block}
#turn.dim{opacity:.5}
#turn .ph{transform-origin:32px 32px;animation:turnrot 2.6s ease-in-out infinite}
@keyframes turnrot{0%,25%{transform:rotate(0)}60%,100%{transform:rotate(-90deg)}}
@media (prefers-reduced-motion:reduce){#turn .ph{animation:none}}
"""

JS = """
const q=document.getElementById('q'),ty=document.getElementById('type'),sf=document.getElementById('st'),ph=document.getElementById('ph');
function apply(){const t=q.value.trim().toLowerCase(),y=ty.value,s=sf.value,p=ph.value;let n=0;
document.querySelectorAll('tbody tr[data-search]').forEach(r=>{
const ok=(!t||r.dataset.search.includes(t))&&(!y||r.dataset.type===y)&&(!s||r.dataset.state===s)&&(!p||r.dataset.phase===p);
r.hidden=!ok;if(ok&&r.dataset.main)n++;});
document.getElementById('count').textContent=n;}
[q,ty,sf,ph].forEach(x=>x.addEventListener(x===q?'input':'change',apply));
const vw=document.getElementById('view'),vl=[...document.querySelectorAll('#vlabels span')];
function setView(v){vw.value=v;document.body.classList.toggle('ref',v==2);document.body.classList.toggle('one',v==3);
vl.forEach(x=>x.classList.toggle('on',x.dataset.v==v));fit();}
vw.addEventListener('input',()=>setView(+vw.value));
vl.forEach(x=>x.addEventListener('click',()=>setView(+x.dataset.v)));
// Phone check: the browser's own mobile flag when it has one, else a phone user agent on a small touch screen.
function isPhone(){const sc=window.screen||{},small=Math.min(sc.width||9999,sc.height||9999)<=600;if(!small)return false;
const ud=navigator.userAgentData;if(ud&&typeof ud.mobile==='boolean')return ud.mobile;
return /Android.*Mobile|iPhone|iPod|Windows Phone/i.test(navigator.userAgent)&&navigator.maxTouchPoints>0;}
let turnOff=false;
const tb=document.getElementById('turn');
tb.addEventListener('click',()=>{if(tb.classList.contains('dim')){turnOff=true;document.body.classList.remove('turn');}else tb.classList.add('dim');});
// Log the monitor / window size and fit the table to it, so desktop behaves like a phone held sideways.
function fit(){const w=window.innerWidth,h=window.innerHeight,sc=window.screen||{},dpr=window.devicePixelRatio||1;
document.body.classList.toggle('compact',w<1000);
const sizes=w<1000?[11,10.5,10]:[12.5,12,11.5,11,10.5,10];let used=sizes[0],ok=false;
const wraps=[...document.querySelectorAll('table.fx')].map(t=>t.parentElement),one=document.body.classList.contains('one');
// In the one-line view a row "fits" only if nothing overflows and the notes column keeps some room.
const room=()=>{const n=document.querySelector('table.fx td.o3');return !one||!n||n.offsetWidth>=110;};
const tryFit=()=>{for(const fs of sizes){used=fs;document.body.style.setProperty('--fx',fs+'px');
ok=wraps.every(x=>x.scrollWidth<=x.clientWidth+1)&&room();if(ok)break;}};
document.body.classList.remove('short');tryFit();
if(one&&!ok){document.body.classList.add('short');tryFit();}
const msg='Screen '+(sc.width||'?')+'×'+(sc.height||'?')+' · window '+w+'×'+h+' · pixel ratio '+(Math.round(dpr*100)/100)+
' · table text '+used+'px · '+(ok?'row fits the window':'row is wider than the window, scroll sideways')+
(document.body.classList.contains('short')?' · short model codes':'');
const phone=isPhone();document.body.classList.toggle('turn',phone&&h>w&&!turnOff);
const el=document.getElementById('screeninfo');if(el)el.textContent=msg+(phone?' · phone detected':'');
if(msg!==fit.last){fit.last=msg;console.log('[BABA fixtures] '+msg);}}
let ft;window.addEventListener('resize',()=>{clearTimeout(ft);ft=setTimeout(fit,120);});
window.addEventListener('orientationchange',()=>setTimeout(fit,200));fit();
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


# Column layout: voltage, watts, lumens, optic, CCT and the .ies link, then the order code. Everything else sits behind
# the toggle button: pressing it keeps the exact order code and swaps the other columns for the cut sheet, the maker
# and family, and the BABA reference (DOT list, status, basis, notes). Either view fits a phone held sideways.
MAIN_HEADERS = ["Voltage", "W", "Lumens", "Optic", "CCT", ".ies"]
REF_HEADERS = ["Cut sheet", "Manufacturer", "Family", "Use case", "DOT reference", "BABA status", "Order notes"]


ONE_LINE = {"DOT reference", "BABA status"}
# Notes about Buy America go in the last column of the third view ("BABA nuances"); everything else is an order note.
BABA_NOTE = re.compile(r"BABA|\bBAA\b|Buy America|DOT wording|Phase inferred|AML authorization|Y2 code|USPOM|Gold Star", re.I)


def short_code(fx):
    """Four-character model designator (ATB0, ARCH, GCJ2 ...) for the one-line view when the full order code will not fit."""
    cat = re.sub(r"^(Conventional Highway|Coventional Highway|Expressway)\s*[:\-–]\s*", "", fx.get("catalog") or "", flags=re.I)
    cat = re.sub(r"^(BABA|BAA)[-\s]+", "", cat)
    token = re.split(r"[-\s_/]", cat.strip(), maxsplit=1)[0]
    return re.sub(r"[^A-Za-z0-9]", "", token)[:4].upper() or "—"


def fixture_table(order_label, body, empty_msg, show_listed=False):
    ref = REF_HEADERS + (["Catalog basis", "TxDOT-listed catalog (4000K)"] if show_listed else [])
    head = ("".join(f'<th class="m">{e(h)}</th>' for h in MAIN_HEADERS) + f"<th>{e(order_label)}</th>"
            + "".join(f'<th class="r{" o" if h in ONE_LINE else ""}">{e(h)}</th>' for h in ref)
            + '<th class="o3">BABA nuances</th>')
    if not body:
        body = f'<tr><td colspan="{len(MAIN_HEADERS) + 2 + len(ref)}" class="empty">{e(empty_msg)}</td></tr>'
    return f'<div class="table-wrap"><table class="fx"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


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
    caveats = fx.get("caveats", [])
    notes = " · ".join(caveats)
    order_notes = " · ".join(c for c in caveats if not BABA_NOTE.search(c)) or "—"
    baba_notes = " · ".join(c for c in caveats if BABA_NOTE.search(c)) or "—"
    volt = "not shown" if fx.get("voltage_inferred") else volt_label(fx.get("voltage"))
    search = " ".join(str(x) for x in [fx.get("manufacturer"), fx.get("brand"), fx.get("family"), fx.get("catalog"),
                                       d.get("listed_catalog"), kind, st, STATE_NAMES.get(st, ""), notes] if x).lower()
    who = fx.get("manufacturer", "") + (f' · {fx["brand"]}' if fx.get("brand") else "")
    listed = d.get("listed_catalog") if fx.get("basis") == "cct-swapped" else "—"
    return (
        f'<tr data-search="{e(search)}" data-type="{e(fx.get("product_type"))}" data-state="{e(st)}" '
        f'data-phase="{e(d.get("phase", ""))}"{" data-main=1" if main else ""}>'
        + td(e(volt), "m c-d", "Not shown on the DOT listing (placeholder voltage code); 480V is only an available option for the family" if fx.get("voltage_inferred") else None)
        + td(e(watts if watts not in (None, "") else "—"), "m num")
        + td(e(lm), "m num", "Estimated" if fx.get("lumens_estimated") else None)
        + td(e(fx.get("distribution") or "—"), "m c-s", fx.get("distribution"))
        + td(e(cct_label(fx)), "m c-d", "Color temperature printed on the DOT listing")
        + td(ies_cell(fx), "m c-d", ies_title(fx))
        + td(f'<span class="cf">{e(fx.get("catalog"))}</span><span class="cs">{e(short_code(fx))}</span>', "c-cat mono", fx.get("catalog"))
        + td(sheet_cell(sheet), "r c-d", sheet.get("title"))
        + td(f"<strong>{e(fx.get('manufacturer'))}</strong>", "r c-m", who)
        + td(e(fx.get("family")), "r c-s", fx.get("family"))
        + td(e(kind), "r c-d")
        + td(dot, "r o c-l", f'{src.get("name", "")} · {d.get("table", "")}')
        + td(f'<span class="badge {label[1]}">{e(label[0])}</span>', "r o c-b", d.get("status"))
        + td(e(order_notes), "r c-x muted", order_notes)
        + (td(badge_for(BASIS_BADGE, fx.get("basis")), "r c-b") + td(e(listed), "r c-l mono muted", listed) if show_listed else "")
        + td(e(baba_notes), "o3 c-x muted", baba_notes)
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
    legacy_notes = "" if not unlisted else (
        f'<span class="muted">Removed 2026-11-09: {data.get("removed_count", 0)} listings that are not Phase 2. They are kept in '
        '<code>data/fixtures_removed.json</code>.</span><br><span class="muted">"As listed" = catalog number copied from the DOT list. '
        '"CCT swapped" = TxDOT-listed number with the 3000K option substituted. The main table only includes listings that print a 480V '
        'code; flagged listings with a placeholder voltage are in the second table.</span>')
    body = "\n".join(row(f, sources, show_listed, True, view.get("show_cct")) for f in shown)
    family_html = "" if not unlisted else f"""<h2>Flagged listings that don't show 480V or a color temperature</h2>
<p class="small muted">These DOT entries are flagged for Buy America, but the listing itself does not print a 480V voltage code
(it shows a placeholder such as xx*, x or X, or no catalog number at all) or a color temperature. The product family offers a 480V
option, but that is not evidence the listed configuration is 480V; for example, Caltrans spells out its 480V variants separately as
"(480 VAC)". Confirm the exact configuration with the manufacturer and the DOT.</p>
{fixture_table("Listing as published", chr(10).join(row(f, sources, False, False) for f in family), "None.")}"""

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
{legacy_notes}
<ul>{src_items}</ul>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search manufacturer, family, catalog number, or state" aria-label="Search">
  <select id="st" aria-label="Filter by state"><option value="">State</option>{state_opts}</select>
  <select id="ph" aria-label="Filter by BABA status"><option value="">BABA status</option>{phase_opts}</select>
  <select id="type" aria-label="Filter by use case"><option value="">Use case</option>{type_opts}</select>
  <div class="views">
    <div class="vlabels" id="vlabels"><span data-v="1" class="on">Fixture details</span><span data-v="2">Cut sheet &amp; BABA reference</span><span data-v="3">Order code &amp; BABA nuances</span></div>
    <input id="view" type="range" min="1" max="3" step="1" value="1" aria-label="Table view: 1 fixture details, 2 cut sheet and BABA reference, 3 order code and BABA nuances, one line per row">
  </div>
</div>

{fixture_table(view["order_label"], body, "No fixtures match the filter.", show_listed)}

{family_html}

{focus_section(data) if view.get("show_focus") else ""}

<footer>
Generated by <code>scripts/build_fixtures.py</code> from <code>data/fixtures.json</code>. Photometric files and cut sheet
copies are the manufacturers' published files, kept here for convenience; each links to its source. States researched with no
Buy America-flagged luminaires are summarized on the <a href="index.html">compliance index</a>. This page is a research
aid, not a certification: get the manufacturer's project-specific Buy America certification for the exact catalog number you order.
<div id="screeninfo" class="muted"></div>
</footer>
</main>
<button id="turn" type="button" aria-label="Turn your phone sideways to see each whole row. Tap once to fade this picture, twice to remove it." title="Turn your phone sideways"><svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g class="ph"><rect x="23" y="14" width="18" height="36" rx="4"/><path d="M29.5 44.5h5"/></g><path d="M6.6 22.8A27 27 0 0 1 41.2 6.6"/><path d="M45.2 8.1L37.1 9.9L40.1 1.4Z" fill="currentColor" stroke-width="1"/><path d="M57.4 41.2A27 27 0 0 1 22.8 57.4"/><path d="M18.8 55.9L26.9 54.1L23.9 62.6Z" fill="currentColor" stroke-width="1"/></svg></button>
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
