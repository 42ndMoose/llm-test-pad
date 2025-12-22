# tools/build_claims.py
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Optional


BEGIN_PART_RE = re.compile(r"^\s*<!--\s*BEGIN\s+(.+?)\s*-->\s*$")

# Claims:
#   [CLAIM] text...
#   CLAIM: text...
#   - [CLAIM] text...
CLAIM_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\[(?i:claim)\]\s*|(?i:claim)\s*:\s*)(.+?)\s*$"
)

# Multi-line blocks:
#   [CLAIM]
#   ...
#   [/CLAIM]
CLAIM_BLOCK_START_RE = re.compile(r"^\s*(?:[-*]\s*)?\[(?i:claim)\]\s*$")
CLAIM_BLOCK_END_RE = re.compile(r"^\s*\[/(?i:claim)\]\s*$")

URL_RE = re.compile(r"https?://[^\s)>\]]+")


def _strip_wrapping_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1].strip()
    return s


def _ensure_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [_strip_wrapping_quotes(str(x)) for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        if s in ("", "[]"):
            return []
        return [_strip_wrapping_quotes(s)]
    # last-resort
    s = str(v).strip()
    return [s] if s else []


def parse_front_matter(text: str) -> tuple[dict, str]:
    """
    Minimal YAML front matter parser:
      ---
      key: value
      key:
        - item
        - item
      ---
    Returns (meta, body). If no front matter, meta is {} and body is original.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text  # no closing ---

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")

    meta: dict = {}
    cur_key: str | None = None

    for raw in fm_lines:
        line = raw.rstrip()
        if not line.strip():
            continue

        m_item = re.match(r"^\s*-\s*(.+?)\s*$", line)
        if m_item and cur_key:
            meta.setdefault(cur_key, [])
            if isinstance(meta[cur_key], list):
                meta[cur_key].append(_strip_wrapping_quotes(m_item.group(1)))
            continue

        m_kv = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", line)
        if m_kv:
            key = m_kv.group(1)
            val = m_kv.group(2)
            cur_key = key

            if val == "":
                meta[key] = []  # expect list items
            else:
                meta[key] = _strip_wrapping_quotes(val)
            continue

    return meta, body


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def load_parts_index(parts_dir: Path) -> dict[str, dict]:
    """
    Map "filename.md" -> normalized section meta used by split_dossier.py.
    """
    out: dict[str, dict] = {}
    if not parts_dir.exists():
        return out

    for p in parts_dir.glob("*.md"):
        if not p.is_file():
            continue

        raw = p.read_text(encoding="utf-8")
        meta, _body = parse_front_matter(raw)

        sec_id = meta.get("id") or slugify(p.stem)
        order = meta.get("order") or "999999"
        title = meta.get("title") or p.stem
        number = meta.get("number") or ""
        level = int(meta.get("level") or 1)

        out[p.name] = {
            "id": str(sec_id),
            "order": str(order),
            "number": str(number),
            "level": level,
            "title": str(title),
            "keywords": _ensure_list(meta.get("keywords")),
            "summary": _ensure_list(meta.get("summary")),
            "related": _ensure_list(meta.get("related")),
            "url": f"{sec_id}.html",
        }

    return out


def claim_id(section_id: str, idx: int) -> str:
    # stable, compact
    return f"C-{section_id}-{idx:03d}"


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
            "<p>No claims found yet. Add blocks like:</p>"
            "<pre>[CLAIM]\nYour claim text...\n[/CLAIM]</pre>"
            "<p>Or single lines like <code>CLAIM: ...</code></p>"
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
    <p>Claims are extracted from <code>[CLAIM]...[/CLAIM]</code> blocks and <code>CLAIM:</code> lines in the source.</p>
    <ul>
      <li><a href="./claims.json">claims.json</a></li>
      <li><a href="./claims.min.json">claims.min.json</a></li>
    </ul>
    {body}
  </main>
</body>
</html>
"""


def pick_doc_title(lines: list[str]) -> str:
    for ln in lines:
        if ln.strip():
            return ln.strip().lstrip("#").strip() or "Dossier"
    return "Dossier"


def main(src: str, outdir: str) -> None:
    src_path = Path(src)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    doc_title = pick_doc_title(lines)

    # Find parts dir next to source.md
    parts_dir = src_path.parent / "parts"
    parts_index = load_parts_index(parts_dir)

    claims: list[dict] = []
    claims_min: list[dict] = []

    # counts per section id
    section_counts: dict[str, int] = {}

    current_part_name: str | None = None
    current_part_meta: dict | None = None

    i = 0
    while i < len(lines):
        line = lines[i]

        m_begin = BEGIN_PART_RE.match(line)
        if m_begin:
            current_part_name = m_begin.group(1).strip()
            current_part_meta = parts_index.get(current_part_name)
            i += 1
            continue

        # Block claim
        if CLAIM_BLOCK_START_RE.match(line):
            block_lines: list[str] = []
            start_line_no = i + 1

            i += 1
            while i < len(lines) and not CLAIM_BLOCK_END_RE.match(lines[i]):
                block_lines.append(lines[i])
                i += 1

            # consume closing tag if present
            if i < len(lines) and CLAIM_BLOCK_END_RE.match(lines[i]):
                i += 1

            claim_text = "\n".join(block_lines).strip()
            if claim_text:
                # Map to section via current part
                if current_part_meta:
                    sec_id = current_part_meta["id"]
                    sec_label = (
                        f'{current_part_meta["number"]}. {current_part_meta["title"]}'.strip()
                        if current_part_meta.get("number")
                        else current_part_meta["title"]
                    )
                    url = current_part_meta["url"]
                else:
                    sec_id = "no-part"
                    sec_label = "No part"
                    url = ""

                section_counts.setdefault(sec_id, 0)
                section_counts[sec_id] += 1
                cid = claim_id(sec_id, section_counts[sec_id])

                links = URL_RE.findall(claim_text)

                claims.append(
                    {
                        "id": cid,
                        "text": claim_text,
                        "section_id": sec_id,
                        "section_label": sec_label,
                        "url": url,
                        "line": start_line_no,
                        "links": links,
                    }
                )
                claims_min.append(
                    {
                        "id": cid,
                        "u": url,
                        "t": " ".join(claim_text.split()),
                    }
                )
            continue

        # Single-line claim
        m_line = CLAIM_LINE_RE.match(line)
        if m_line:
            claim_text = m_line.group(1).strip()
            if claim_text:
                if current_part_meta:
                    sec_id = current_part_meta["id"]
                    sec_label = (
                        f'{current_part_meta["number"]}. {current_part_meta["title"]}'.strip()
                        if current_part_meta.get("number")
                        else current_part_meta["title"]
                    )
                    url = current_part_meta["url"]
                else:
                    sec_id = "no-part"
                    sec_label = "No part"
                    url = ""

                section_counts.setdefault(sec_id, 0)
                section_counts[sec_id] += 1
                cid = claim_id(sec_id, section_counts[sec_id])

                links = URL_RE.findall(claim_text)

                claims.append(
                    {
                        "id": cid,
                        "text": claim_text,
                        "section_id": sec_id,
                        "section_label": sec_label,
                        "url": url,
                        "line": i + 1,
                        "links": links,
                    }
                )
                claims_min.append(
                    {
                        "id": cid,
                        "u": url,
                        "t": claim_text,
                    }
                )

            i += 1
            continue

        i += 1

    # Write outputs
    (out / "claims.json").write_text(json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "claims.min.json").write_text(
        json.dumps(claims_min, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (out / "claims.html").write_text(render_claims_html(doc_title, claims), encoding="utf-8")

    print(f"Wrote {out / 'claims.json'} ({len(claims)} claims)")
    print(f"Wrote {out / 'claims.min.json'} ({len(claims_min)} claims)")
    print(f"Wrote {out / 'claims.html'}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tools/build_claims.py <source.md> <output_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
