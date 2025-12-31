# tools/build_timeline.py
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from html import escape
from pathlib import Path


CLAIM_SHORT_RE = re.compile(r"^(C-\d+)", re.IGNORECASE)          # C-08 from C-08-...
SECTION_NUM_RE = re.compile(r"^\s*(\d+)\s*(?:[.)]|$)")           # 8 from "8. Title" or "8) Title"


def load_claims(claims_json: Path) -> list[dict]:
    return json.loads(claims_json.read_text(encoding="utf-8"))


def _short_claim_id(claim_id: str) -> str:
    m = CLAIM_SHORT_RE.match((claim_id or "").strip())
    return m.group(1).upper() if m else (claim_id or "").strip()


def _section_number(section_label: str) -> str:
    s = (section_label or "").strip()
    m = SECTION_NUM_RE.match(s)
    return m.group(1) if m else ""


def build_events(claims: list[dict]) -> list[dict]:
    events: list[dict] = []
    for c in claims:
        date = (c.get("date") or "").strip()
        title = (c.get("title") or "").strip()
        if not date:
            continue  # only timeline claims

        if not title:
            txt = " ".join((c.get("text") or "").split())
            title = txt[:120] + ("…" if len(txt) > 120 else "")

        sec_label = (c.get("section_label") or "").strip()

        events.append(
            {
                "date": date,
                "title": title,
                "id": c["id"],
                "claim": c.get("text", ""),
                "tags": c.get("tags", []),
                "note": c.get("note", ""),
                "section_url": c.get("url", ""),
                "section_label": sec_label,
                "section_num": _section_number(sec_label),
                "claim_url": f"claims.html#{c['id']}",
                "claim_short": _short_claim_id(c["id"]),
                "links": c.get("links", []),
            }
        )

    events.sort(key=lambda e: (e["date"], e["id"]))
    return events


def render_html(events: list[dict]) -> str:
    by_day: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        by_day[e["date"]].append(e)

    days = sorted(by_day.keys())

    out: list[str] = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
        "<title>Timeline</title>",
        "</head>",
        "<body>",
        "<nav>"
        '  <a href="./index.html">Index</a> | '
        '  <a href="./claims.html">Claims</a> | '
        '  <a href="./timeline.html">Timeline</a>'
        "</nav>",
        "<main>",
        "<h1>Timeline</h1>",
        "<p>Timeline is generated from claims that include <code>DATE: YYYY-MM-DD</code>.</p>",
        '<p><a href="./timeline.json">timeline.json</a></p>',
        "<hr/>",
    ]

    for d in days:
        out.append(f"<h2>{escape(d)}</h2>")
        out.append("<ul>")
        for e in by_day[d]:
            tags = ", ".join(e.get("tags") or [])
            tags_html = f" <span style='opacity:.7'>[{escape(tags)}]</span>" if tags else ""

            note = e.get("note") or ""
            note_html = f"<div style='opacity:.8;margin-top:4px'>{escape(note)}</div>" if note else ""

            links = e.get("links") or []
            links_html = ""
            if links:
                links_html = "<div style='margin-top:4px'>" + " ".join(
                    [f'<a href="{escape(u)}" rel="noreferrer noopener">{escape(u)}</a>' for u in links]
                ) + "</div>"

            claim_text = f"Claim {e.get('claim_short') or e['id']}"
            claim_link = f"<a href='./{escape(e['claim_url'])}'>{escape(claim_text)}</a>"

            section_link = ""
            sec_url = e.get("section_url") or ""
            sec_num = (e.get("section_num") or "").strip()
            if sec_url:
                section_text = f"Section {sec_num}" if sec_num else "Section"
                section_link = f" | <a href='./{escape(sec_url)}'>{escape(section_text)}</a>"

            out.append(
                "<li>"
                f"<strong>{escape(e['title'])}</strong>{tags_html}"
                f"<div>{claim_link}{section_link}</div>"
                f"{note_html}"
                f"{links_html}"
                "</li>"
            )
        out.append("</ul>")
        out.append("<hr/>")

    out += ["</main>", "</body>", "</html>"]
    return "\n".join(out)


def main(site_dir: str) -> None:
    site = Path(site_dir)
    claims_json = site / "claims.json"
    claims = load_claims(claims_json)
    events = build_events(claims)

    (site / "timeline.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    (site / "timeline.html").write_text(render_html(events), encoding="utf-8")

    print(f"Wrote {site / 'timeline.json'} ({len(events)} events)")
    print(f"Wrote {site / 'timeline.html'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tools/build_timeline.py <site_dir>")
        sys.exit(1)
    main(sys.argv[1])
