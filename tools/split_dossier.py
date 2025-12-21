import re
import sys
import json
from dataclasses import dataclass
from pathlib import Path
from html import escape

# Recognize headings like:
#   0. Title
#   0.1 Subtitle
#   8.8.6 Deeper subtitle
#
# IMPORTANT:
# This regex will also match list items like "  1. Something"
# So we add a heuristic: single-number headings (level 1) must be "promoted"
# by having a divider line (⸻ or --- etc.) right above them.
NUM_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\.\s+(.+?)\s*$")

# Also support Markdown headings if you ever add them:
MD_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")

# Divider lines that "promote" the next single-number heading into a real section
DIVIDER_RE = re.compile(r"^\s*(?:⸻+|[-_]{3,}|={3,})\s*$")


@dataclass
class Heading:
    kind: str            # "num" or "md"
    number: str          # e.g. "8.8.6" (empty for md)
    level: int           # 1 for "0.", 2 for "0.1", etc. (or # count for md)
    title: str           # heading title
    line_index: int      # where it starts in the file


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def file_name(h: Heading) -> str:
    if h.kind == "num":
        # Stable names: 8.8.6 -> 08-08-06-delegitimization.html
        parts = h.number.split(".")
        num = "-".join(p.zfill(2) for p in parts)
        return f"{num}-{slugify(h.title)}.html"
    # For markdown headings
    return f"{slugify(h.title)}.html"


def prev_nonempty_line(lines: list[str], i: int) -> str:
    """Return the previous non-empty line (stripped), or empty string."""
    for j in range(i - 1, -1, -1):
        s = lines[j].strip()
        if s:
            return s
    return ""


def detect_headings(lines: list[str]) -> list[Heading]:
    heads: list[Heading] = []
    for i, line in enumerate(lines):
        m = NUM_HEADING_RE.match(line)
        if m:
            number, title = m.group(1), m.group(2)
            level = number.count(".") + 1

            # Heuristic:
            # - Level 1 "N. Title" headings are only real headings if
            #   the previous non-empty line is a divider.
            # - Dotted headings (0.1, 8.5.3, etc.) are allowed anywhere.
            if level == 1:
                prev = prev_nonempty_line(lines, i)
                if not DIVIDER_RE.match(prev):
                    continue

            heads.append(Heading(kind="num", number=number, level=level, title=title, line_index=i))
            continue

        m = MD_HEADING_RE.match(line)
        if m:
            hashes, title = m.group(1), m.group(2)
            level = len(hashes)
            heads.append(Heading(kind="md", number="", level=level, title=title, line_index=i))
            continue

    return heads


def section_end_index(heads: list[Heading], idx: int, total_lines: int) -> int:
    cur = heads[idx]
    for j in range(idx + 1, len(heads)):
        nxt = heads[j]
        # End when we reach a heading at the same or higher level
        if nxt.level <= cur.level:
            return nxt.line_index
    return total_lines


def render_index(doc_title: str, toc_entries: list[dict]) -> str:
    # Build nested lists using a level stack
    html_parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
        f"<title>{escape(doc_title)} - Index</title>",
        "</head>",
        "<body>",
        "<main>",
        f"<h1>{escape(doc_title)}</h1>",
        "<p>Open the smallest relevant section page instead of loading the whole dossier.</p>",
        '<p><a href="./toc.json">toc.json</a></p>',
        "<hr/>",
        "<h2>Table of contents</h2>",
    ]

    cur_level = 0
    for e in toc_entries:
        lvl = int(e["level"])
        title = escape(e["title"])
        number = escape(e.get("number", ""))
        url = escape(e["url"])

        # indent or dedent
        while cur_level < lvl:
            html_parts.append("<ul>")
            cur_level += 1
        while cur_level > lvl:
            html_parts.append("</ul>")
            cur_level -= 1

        label = f"{number}. {title}" if number else title
        html_parts.append(f'<li><a href="./{url}">{label}</a></li>')

    while cur_level > 0:
        html_parts.append("</ul>")
        cur_level -= 1

    html_parts += [
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html_parts)


def render_page(doc_title: str, h: Heading, body_text: str, prev_url: str | None, next_url: str | None) -> str:
    title_bits = []
    if h.kind == "num":
        title_bits.append(h.number + ".")
    title_bits.append(h.title)
    page_title = " ".join(title_bits).strip()

    nav_bits = ['<a href="./index.html">Index</a>']
    if prev_url:
        nav_bits.append(f'<a href="./{escape(prev_url)}">Prev</a>')
    if next_url:
        nav_bits.append(f'<a href="./{escape(next_url)}">Next</a>')
    nav = " | ".join(nav_bits)

    return "\n".join([
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
        f"<title>{escape(doc_title)} - {escape(page_title)}</title>",
        "</head>",
        "<body>",
        f"<nav>{nav}</nav>",
        "<main>",
        f"<h1>{escape(page_title)}</h1>",
        '<pre style="white-space:pre-wrap;line-height:1.35">',
        escape(body_text),
        "</pre>",
        "</main>",
        "</body>",
        "</html>",
    ])


def main(src: str, outdir: str):
    src_path = Path(src)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Title: use first non-empty line as doc title
    doc_title = "Dossier"
    for ln in lines:
        if ln.strip():
            doc_title = ln.strip().lstrip("#").strip()
            break

    heads = detect_headings(lines)

    # If we find no headings, just dump one page
    if not heads:
        page = render_page(doc_title, Heading("md", "", 1, "Full Document", 0), text, None, None)
        (out / "full.html").write_text(page, encoding="utf-8")
        idx = render_index(doc_title, [{"level": 1, "title": "Full Document", "number": "", "url": "full.html"}])
        (out / "index.html").write_text(idx, encoding="utf-8")
        (out / "toc.json").write_text(
            json.dumps([{"level": 1, "title": "Full Document", "number": "", "url": "full.html"}], indent=2),
            encoding="utf-8",
        )
        return

    # Build per-heading pages
    entries: list[dict] = []
    pages: list[tuple[Heading, str]] = []

    for i, h in enumerate(heads):
        fn = file_name(h)
        pages.append((h, fn))
        entries.append({
            "kind": h.kind,
            "number": h.number,
            "level": h.level,
            "title": h.title,
            "url": fn,
        })

    # Write pages with prev/next
    for i, (h, fn) in enumerate(pages):
        prev_url = pages[i - 1][1] if i > 0 else None
        next_url = pages[i + 1][1] if i + 1 < len(pages) else None

        end = section_end_index(heads, i, len(lines))
        body = "\n".join(lines[h.line_index:end]).strip() + "\n"

        html = render_page(doc_title, h, body, prev_url, next_url)
        (out / fn).write_text(html, encoding="utf-8")

    # Write index + toc.json
    (out / "index.html").write_text(render_index(doc_title, entries), encoding="utf-8")
    (out / "toc.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python split_dossier.py <source.md> <output_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
