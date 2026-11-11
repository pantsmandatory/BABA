#!/usr/bin/env python3
"""Check each state DOT product list in data/sources.json for changes.

Downloads every list URL, hashes the content, and compares it with the hash
saved last week in data/source_status.json. Lists that changed are marked
"changed" so a person knows which DOT lists to re-review for new or removed
luminaires. Also writes data/changed_sources.md, which the weekly workflow
uses as the body of a review issue.

Standard library only.
"""

import datetime as dt
import hashlib
import json
import pathlib
import re
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = "BABA-luminaire-index/1.0 (+https://github.com/pantsmandatory/BABA)"


def normalize(body: bytes, content_type: str) -> bytes:
    """Strip parts of HTML pages that change on every load (scripts, tokens, timestamps)."""
    if "html" not in content_type:
        return body
    text = body.decode("utf-8", "replace")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->", "", text)
    text = re.sub(r"(?i)<input[^>]+(__VIEWSTATE|__EVENTVALIDATION|csrf|token)[^>]*>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.encode("utf-8")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def main():
    today = dt.date.today().isoformat()
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    status_path = DATA / "source_status.json"
    old = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    new = {}
    changed, errors = [], []

    for s in sources:
        url = s.get("url")
        if not url or url in new:
            continue
        prev = old.get(url, {})
        entry = {"state": "new", "checked": today, "hash": prev.get("hash"),
                 "last_changed": prev.get("last_changed")}
        try:
            body, ctype = fetch(url)
            digest = hashlib.sha256(normalize(body, ctype)).hexdigest()
            if prev.get("hash") is None:
                entry["state"] = "new"
                entry["last_changed"] = today
            elif digest != prev["hash"]:
                entry["state"] = "changed"
                entry["last_changed"] = today
                changed.append(s)
            else:
                entry["state"] = "unchanged"
            entry["hash"] = digest
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            entry["state"] = "error"
            entry["error"] = str(exc)[:200]
            errors.append((s, entry["error"]))
        new[url] = entry
        print(f'{s.get("state")}: {entry["state"]}')

    status_path.write_text(json.dumps(new, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [f"Weekly check of state DOT product lists, {today}.", ""]
    if changed:
        lines += ["## Lists that changed (re-review luminaire entries)", ""]
        lines += [f'- [ ] **{s["state"]}** – [{s.get("list_name") or s["url"]}]({s["url"]})' for s in changed]
        lines.append("")
    if errors:
        lines += ["## Lists that could not be reached", ""]
        lines += [f'- **{s["state"]}** – {s["url"]} ({err})' for s, err in errors]
        lines.append("")
    if not changed and not errors:
        lines.append("No list changes detected.")
    (DATA / "changed_sources.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(changed)} changed, {len(errors)} unreachable")


if __name__ == "__main__":
    main()
