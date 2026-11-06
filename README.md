# BABA Luminaire Index

A weekly list of roadway and area luminaires that are on state DOT approved product lists **and** have documented
FHWA Buy America (BABA) compliance for manufactured products (23 CFR 635.410):

1. Final assembly in the United States (projects obligated on/after Oct 1, 2025), and
2. Domestic components costing more than 55% of total component cost (projects obligated on/after Oct 1, 2026).

Open `index.html` for the current list. Weekly snapshots are in `archive/`.

`fixtures.html` lists the DOT-certified fixtures with downloadable `.ies` files and manufacturer cut sheets.
It currently shows only **3000K, 480V, 70 CRI** variants (set by `filter` in `data/fixtures.json`).
First source: TxDOT's Roadway Illumination MPL, "Compliant v5" entries (projects obligated on/after Oct 1, 2026).

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
