# tools/build_claims.py
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Optional

# Numeric headings like:
#   0. Title
#   0.1 Subtitle
#   8.8.6 Deeper subtitle
NUM_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\.\s+(.+?)\s*$")

# Markdown headings like:
#   # Title
#   ## Title
#   ### Title
MD_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")

# Claims markers:
#   - [CLAIM] text...
#   [CLAIM] text...
#   CLAIM: text...
CLAIM_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:\[(?i:claim)\]\s*|(?i:claim)\s*:\s*)(.+?)\s*$")

URL_RE = re.compile(r"https?://[^\s)>\]]+")


@dataclass
class Heading:
    kind: str         # "num" or "md"
    number: str       # e.g. "8.8.6" (empty for md)
    level: int        # 1 for "0.", 2 for "0.1", etc. (or # count for md)
    title: str        # heading title
    line_index: int   # where it starts in the file


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def file_name(h: Heading) -> str:
    """
    Must match tools/split_dossier.py naming so links are correct.
    Current scheme:
      - numeric: 8.8.6 -> 8-8-6-title.html
      - md: title.html
    """
    if h.kind == "num":
        num = h.number.replace(".", "-")
        return f"{num}-{slugify(h.title)}.html"
    return f"{slugify(h.title)}.html"


def detect_headings(lines: list[str]) -> list[Heading]:
    heads: list[Heading] = []
    for i, line in enumerate(lines):
        m = NUM_HEADING_RE.match(line)
        if m:
            number, title = m.group(1), m.group(2)
            level = number.count(".") + 1
            heads.append(Heading(kind="num", number=number, level=level, title=title, line_index=i))
            continue

        m = MD_HEADING_RE.match(line)
        if m:
            hashes, title = m.group(1), m.group(2)
            level = len(hashes)
            heads.append(Heading(kind="md", number="", level=level, title=title, line_index=i))
            continue

    return heads


def pick_doc_title(lines: list[str]) -> str:
    for ln in lines:
        if ln.strip():
            return ln.strip().lstrip("#").strip() or "Dossier"
    return "Dossier"


def find_current_heading(heads: list[Heading], line_index: int) -> Optional[Heading]:
    # heads are in ascending line_index
    cur: Optional[Heading] = None
    for h in heads:
        if h.line_index <= line_index:
            cur = h
        else:
            break
    return cur


def claim_id(section_key: str, idx: int) -> str:
    # section_key already sanitized, idx 1-based
    return f"C-{section_key}-{idx:03d}"


def render_claims_html(doc_title: str, claims: list[dict]) -> str:
    rows = []
    for c in claims:
        cid = escape(c["id"])
        txt = escape(c["text"])
        sec_label = escape(c.get("section_label", ""))
        url = escape(c.get("url", ""))
        line = c.get("line", None)

        where = sec_label
        if url:
            where = f'<a href="./{url}">{where}</a>'
        if line is not None:
            where += f" <span style='opacity:.7'>(line {int(line)})</span>"

        links_html = ""
        links = c.get("links", [])
        if links:
            links_html = " ".join(
                [f'<a href="{escape(u)}" rel="noreferrer noopener">{escape(u)}</a>' for u in links]
            )

        rows.append(
            "<tr>"
            f"<td style='white-space:nowrap'>{cid}</td>"
            f"<td>{txt}</td>"
            f"<td style='white-space:nowrap'>{where}</td>"
            f"<td>{links_html}</td>"
            "</tr>"
        )

    if rows:
        body = (
            "<table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;width:100%'>"
            "<thead><tr>"
            "<th>ID</th><th>Claim</th><th>Section</th><th>Links</th>"
            "</tr></thead>"
            "<tbody>"
            + "\n".join(rows) +
            "</tbody></table>"
        )
    else:
        body = (
            "<p>No claims found yet. Add lines like <code>[CLAIM] ...</code> or "
            "<code>CLAIM: ...</code> to your dossier.</p>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{escape(doc_title)} - Claims Ledger</title>
</head>
<body>
  <nav><a href="./index.html">Index</a></nav>
  <main>
    <h1>Claims Ledger</h1>
    <p>This page lists atomic claims marked in the source with <code>[CLAIM]</code> or <code>CLAIM:</code>.</p>
    <ul>
      <li><a href="./claims.json">claims.json</a> (full)</li>
      <li><a href="./claims.min.json">claims.min.json</a> (lightweight)</li>
    </ul>
    {body}
  </main>
</body>
</html>
"""


def main(src: str, outdir: str) -> None:
    src_path = Path(src)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    doc_title = pick_doc_title(lines)
    heads = detect_headings(lines)

    claims: list[dict] = []
    section_counts: dict[str, int] = {}

    for i, line in enumerate(lines):
        m = CLAIM_RE.match(line)
        if not m:
            continue

        claim_text = m.group(1).strip()
        if not claim_text:
            continue

        h = find_current_heading(heads, i)
        if h is None:
            section_key = "no-heading"
            section_label = "No heading"
            url = ""
        else:
            url = file_name(h)
            if h.kind == "num":
                section_key = h.number.replace(".", "-")
                section_label = f"{h.number}. {h.title}"
            else:
                section_key = "md-" + slugify(h.title)
                section_label = h.title

        section_counts.setdefault(section_key, 0)
        section_counts[section_key] += 1
        cid = claim_id(section_key, section_counts[section_key])

        links = URL_RE.findall(claim_text)

        claims.append({
            "id": cid,
            "text": claim_text,
            "section_label": section_label,
            "url": url,
            "line": i + 1,
            "links": links,
        })

    claims_min = [
        {
            "id": c["id"],
            "section_label": c.get("section_label", ""),
            "url": c.get("url", ""),
            "line": c.get("line", None),
        }
        for c in claims
    ]

    # Write JSON + HTML
    (out / "claims.json").write_text(json.dumps(claims, indent=2), encoding="utf-8")
    (out / "claims.min.json").write_text(json.dumps(claims_min, separators=(",", ":")), encoding="utf-8")
    (out / "claims.html").write_text(render_claims_html(doc_title, claims), encoding="utf-8")

    print(f"Wrote {out / 'claims.json'} ({len(claims)} claims)")
    print(f"Wrote {out / 'claims.min.json'} ({len(claims_min)} claims)")
    print(f"Wrote {out / 'claims.html'}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tools/build_claims.py <source.md> <output_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
