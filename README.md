# BABA Luminaire Index

A weekly list of roadway and area luminaires that are on state DOT approved product lists **and** have documented
FHWA Buy America (BABA) compliance for manufactured products (23 CFR 635.410):

1. Final assembly in the United States (projects obligated on/after Oct 1, 2025), and
2. Domestic components costing more than 55% of total component cost (projects obligated on/after Oct 1, 2026).

Open `index.html` for the current list. Weekly snapshots are in `archive/`.

Fixture pages list the DOT-certified fixtures at 480V with downloadable `.ies` files and manufacturer cut sheets:
`fixtures-4k.html` shows the 4000K catalog numbers exactly as TxDOT lists them; `fixtures-3k.html` shows the same
configurations with the 3000K / 70 CRI option swapped in. `fixtures.html` links to both. Pages are set by `views` in
`data/fixtures.json`.
`fiber.html` lists Corning fiber products with BABA evidence: traffic/ITS cabinet splice housings, orange OM1/OM2
multimode cable, and G.652 single-mode cable (data in `data/fiber.json`, built by `scripts/build_fiber.py`).

**Strict design (default).** `data/site.json` has `"show_unlisted": false`: every page shows only rows that a state DOT list
prints, with that exact model number, as Buy America compliant for projects obligated on or after Oct 1, 2026. Setting it to
`true` and re-running the build scripts restores the earlier design (commit `817d028`), which also showed TxDOT rows with the
3000K option swapped in, the Current Lighting / Cree Lighting 480V 3000K section, and the index verification queue. That data
and the `.ies` files in `ies/current/` and `ies/cree/` stay in the repo; only the rendering changes.

Fixture pages show **Phase 2 listings only** (a state DOT states US final assembly and more than 55% domestic component
cost, for projects obligated on or after Oct 1, 2026). Rows a DOT flags only for Phase 1, as "eligible"/"BAA" with no phase,
or for project-level certification were removed on 2026-11-09 and are kept, unrendered, in `data/fixtures_removed.json`.

`fixtures-3k.html` also has a **Current Lighting and Cree Lighting** section (`focus` in `data/fixtures.json`): 480V 3000K
roadway (about 20,000 lm, Type II/III) and high mast (about 250–500W) configurations with `.ies` files in `ies/current/` and
`ies/cree/`, each with what the state DOT lists actually say. None of those exact configurations has a DOT Phase 2 statement. Gen 7 ERL2 rows carry Current's
"D1 = BABA Compliant" ordering suffix (manufacturer option, no DOT listing).

Fixture page first source: TxDOT's Roadway Illumination MPL, "Compliant v5" entries (projects obligated on/after Oct 1, 2026).

## How it works

| File | Purpose |
| --- | --- |
| `data/sources.json` | One entry per state DOT approved/qualified product list (URL, luminaire category, whether it flags Buy America). |
| `data/luminaires.json` | Luminaire entries with DOT listing(s) and evidence. Edited by hand. |
| `data/rule.json` | Summary of the federal rule shown at the top of the page. |
| `data/source_status.json` | Written by the weekly check: content hash and changed/unchanged per list. |
| `scripts/build_site.py` | Builds `index.html` and `archive/YYYY-MM-DD.html`. |
| `data/fixtures.json` | Fixture configurations (catalog number, DOT listing, cut sheet, .ies) and the page filter. |
| `ies/<manufacturer>/` | Copies of manufacturer .ies files; each entry links to its source. |
| `cutsheets/<manufacturer>/` | Copies of cut sheets whose official site blocks automated downloads. |
| `scripts/build_fixtures.py` | Builds `fixtures.html` from `data/fixtures.json`. |
| `scripts/check_sources.py` | Downloads each DOT list and flags lists that changed since last week. |
| `.github/workflows/weekly-update.yml` | Runs both scripts every Monday, commits the pages, and opens an issue listing changed DOT lists. |

An entry appears in the **Compliant luminaires** table only when `final_assembly_us` and `domestic_content_55` are
both `"stated"`. Everything else is shown in the **Verification queue**.

## Weekly routine

1. The workflow runs Monday and opens a "Weekly review" issue if any DOT list changed.
2. Review those lists, then add, update, or remove entries in `data/luminaires.json`.
3. Run `python3 scripts/build_site.py` (or re-run the workflow) and commit.

## Adding a luminaire

```json
{
  "id": "ks-acme-roadway-x",
  "manufacturer": "Acme Lighting",
  "model": "Roadway X (order with BABA option)",
  "product_type": "LED roadway luminaire",
  "states": [{"state": "KS", "list_name": "PQL-24.2", "listing_id": "LED-A", "dot_list_url": "https://..."}],
  "final_assembly_us": "stated",
  "domestic_content_55": "stated",
  "evidence_level": "manufacturer-declared",
  "evidence": [{"summary": "Manufacturer BABA certificate", "url": "https://..."}],
  "notes": "",
  "last_verified": "2026-11-06"
}
```

`evidence_level` is `dot-flagged` when the DOT list itself marks the product compliant, otherwise `manufacturer-declared`.

This index is a research aid, not a certification. Always get the manufacturer's project-specific Buy America
certification and confirm acceptance with the DOT.
