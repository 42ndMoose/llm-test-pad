from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path


# Keep these regexes EXACTLY aligned with split_dossier.py
NUM_HEADING_RE = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")
MD_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
DIVIDER_RE = re.compile(r"^\s*(?:⸻+|[-_]{3,}|={3,})\s*$")

CLAIM_BLOCK_START_RE = re.compile(r"^\s*(?:[-*]\s*)?\[(?i:claim)\]\s*$")
CLAIM_BLOCK_END_RE = re.compile(r"^\s*\[/(?i:claim)\]\s*$")
CLAIM_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\[(?i:claim)\]\s*|(?i:claim)\s*:\s*).+?\s*$"
)

C_MARKER_RE = re.compile(r"\s*\[(?i:c)\]\s*")
EVIDENCE_HEADER_RE = re.compile(
    r"^\s*(?i:(evidence|links|sources|verification paths?|verify|citations))\s*:?\s*(?:\(.*\))?\s*$"
)


def pick_doc_title(lines: list[str]) -> str:
    for ln in lines:
        if ln.strip():
            return ln.strip().lstrip("#").strip() or "Dossier"
    return "Dossier"


def _looks_like_section_boundary(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return bool(NUM_HEADING_RE.match(s) or MD_HEADING_RE.match(s) or DIVIDER_RE.match(s))


def strip_claims(text: str) -> str:
    """
    Clean human-facing pages:
      - Removes [CLAIM]...[/CLAIM] blocks and single-line CLAIM markers
      - Removes inline [C] markers but keeps the claim sentence
      - If a line contains [C], hide subsequent lines until:
          * a blank line, OR
          * the next claim marker ([C], CLAIM:, [CLAIM] block), OR
          * a new section boundary (heading/divider)
      - Also strips standalone Evidence/Links/Sources blocks.
    """
    lines = text.splitlines()
    out: list[str] = []

    def is_boundary(s: str) -> bool:
        return bool(_looks_like_section_boundary(s))

    def is_claim_start(s: str) -> bool:
        return bool(
            CLAIM_BLOCK_START_RE.match(s)
            or CLAIM_LINE_RE.match(s)
            or C_MARKER_RE.search(s)
        )

    i = 0
    skip_after_c = False

    while i < len(lines):
        line = lines[i]

        # 1) Drop [CLAIM]...[/CLAIM] blocks entirely
        if CLAIM_BLOCK_START_RE.match(line):
            i += 1
            while i < len(lines) and not CLAIM_BLOCK_END_RE.match(lines[i]):
                i += 1
            if i < len(lines) and CLAIM_BLOCK_END_RE.match(lines[i]):
                i += 1
            skip_after_c = False
            continue

        # 2) Drop single-line CLAIM: / [CLAIM] lines
        if CLAIM_LINE_RE.match(line):
            i += 1
            skip_after_c = False
            continue

        # 3) If we're in "hide evidence after [C]" mode, skip until stop conditions
        if skip_after_c:
            s = line.strip()

            # stop on blank line
            if not s:
                if out and out[-1].strip():
                    out.append("")
                i += 1
                skip_after_c = False
                continue

            # stop BEFORE a new claim/boundary and reprocess that line normally
            if is_boundary(line) or is_claim_start(line):
                skip_after_c = False
                continue

            # otherwise hide this line
            i += 1
            continue

        # 4) Strip standalone Evidence/Links/Sources blocks even without [C]
        if EVIDENCE_HEADER_RE.match(line):
            i += 1
            while i < len(lines):
                if not lines[i].strip():
                    break
                # stop BEFORE next section/claim and reprocess it
                if is_boundary(lines[i]) or is_claim_start(lines[i]):
                    break
                i += 1

            if i < len(lines) and not lines[i].strip():
                if out and out[-1].strip():
                    out.append("")
                i += 1
            continue

        # 5) Normal line: remove [C] inline marker, keep content
        had_c = bool(C_MARKER_RE.search(line))
        cleaned = C_MARKER_RE.sub(" ", line)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).rstrip()

        out.append(cleaned)

        # If this line had [C], hide following evidence lines
        if had_c:
            skip_after_c = True

        i += 1

    return "\n".join(out).strip() + "\n"


def render_source_html(doc_title: str, body_text: str) -> str:
    nav = "\n".join(
        [
            "<nav>",
            '  <a href="./index.html">Index</a> |',
            '  <a href="./source.html">Source</a> |',
            '  <a href="./claims.html">Claims</a> |',
            '  <a href="./timeline.html">Timeline</a>',
            "</nav>",
        ]
    )

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8"/>',
            '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
            f"<title>{escape(doc_title)} - Source</title>",
            "</head>",
            "<body>",
            nav,
            "<main>",
            f"<h1>{escape(doc_title)} (Source)</h1>",
            "<p>Built from <code>dossier/source.md</code>. Claim evidence blocks are hidden for human reading.</p>",
            '<pre style="white-space:pre-wrap;line-height:1.35">',
            escape(body_text),
            "</pre>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def main(src_md: str, out_html: str) -> None:
    src_path = Path(src_md)
    out_path = Path(out_html)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    text = src_path.read_text(encoding="utf-8")
    doc_title = pick_doc_title(text.splitlines())

    clean = strip_claims(text)
    html = render_source_html(doc_title, clean)
    out_path.write_text(html, encoding="utf-8")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tools/build_source_html.py <source.md> <out.html>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
