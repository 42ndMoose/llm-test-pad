# tools/build_source_html.py
from __future__ import annotations

import json
import re
import sys
from html import escape
from pathlib import Path


# A "claim line" is any line that contains [C] anywhere
CLAIM_INLINE_RE = re.compile(r"\[C\]")


def pick_doc_title(lines: list[str]) -> str:
    for ln in lines:
        if ln.strip():
            # allow markdown title or plain first line
            return ln.strip().lstrip("#").strip() or "Dossier"
    return "Dossier"


def hide_claim_evidence_markdown(md_text: str) -> str:
    """
    Human-view transform:
    - If a line contains [C], treat it as a claim line.
    - Hide that line AND everything after it until:
        - a blank line, OR
        - another [C] claim line.
    Output keeps non-claim prose intact.

    This matches your current behavior in split_dossier.py for parts pages.
    """
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if CLAIM_INLINE_RE.search(line):
            # skip this claim line and its evidence block
            i += 1
            while i < len(lines):
                if CLAIM_INLINE_RE.search(lines[i]):
                    # next claim begins immediately
                    break
                if lines[i].strip() == "":
                    # blank line ends the hidden block (consume it too)
                    i += 1
                    break
                i += 1
            continue

        out.append(line)
        i += 1

    return "\n".join(out).strip() + "\n"


def render_source_html(doc_title: str, clean_text: str) -> str:
    # We keep it simple and consistent with your section pages:
    # pre-wrap text, no markdown rendering.
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
            '<nav><a href="./index.html">Index</a> | <a href="./claims.html">Claims</a></nav>',
            "<main>",
            f"<h1>{escape(doc_title)} (Source)</h1>",
            "<p>This is the built single-file source with claim/evidence blocks hidden for humans.</p>",
            '<pre style="white-space:pre-wrap;line-height:1.35">',
            escape(clean_text),
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

    md_text = src_path.read_text(encoding="utf-8")
    lines = md_text.splitlines()
    doc_title = pick_doc_title(lines)

    clean = hide_claim_evidence_markdown(md_text)
    html = render_source_html(doc_title, clean)
    out_path.write_text(html, encoding="utf-8")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tools/build_source_html.py <source.md> <out.html>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
