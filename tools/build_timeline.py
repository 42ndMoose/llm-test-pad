# tools/build_timeline.py
from __future__ import annotations

import json
import sys
from collections import defaultdict
from html import escape
from pathlib import Path


def load_claims(claims_json: Path) -> list[dict]:
    return json.loads(claims_json.read_text(encoding="utf-8"))


def build_events(claims: list[dict]) -> list[dict]:
    events: list[dict] = []
    for c in claims:
        date = (c.get("date") or "").strip()
        title = (c.get("title") or "").strip()
        if not date:
            continue  # only timeline claims

        if not title:
            # fallback: use shortened claim text
            txt = " ".join((c.get("text") or "").split())
            title = txt[:120] + ("…" if len(txt) > 120 else "")

        events.append(
            {
                "date": date,
                "title": title,
                "id": c["id"],
                "claim": c.get("text", ""),
                "tags": c.get("tags", []),
                "note": c.get("note", ""),
                "section_url": c.get("url", ""),
                "section_label": c.get("section_label", ""),
                "claim_url": f"claims.html#{c['id']}",
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

            sec_url = e.get("section_url") or ""
            sec_label = (e.get("section_label") or "").strip()
            sec_label_html = f" <span style='opacity:.7'>({escape(sec_label)})</span>" if sec_label else ""

            section_link_html = ""
            if sec_url:
                section_link_html = f" | <a href='./{escape(sec_url)}'>Section</a>{sec_label_html}"

            out.append(
                "<li>"
                f"<strong>{escape(e['title'])}</strong>{tags_html}"
                f"<div><a href='./{escape(e['claim_url'])}'>Claim {escape(e['id'])}</a>"
                f"{section_link_html}"
                "</div>"
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
