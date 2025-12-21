import re
import sys
import json
from dataclasses import dataclass
from pathlib import Path
from html import escape


# -----------------------------
# Old mode: heading splitting
# -----------------------------
NUM_HEADING_RE = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")
MD_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
DIVIDER_RE = re.compile(r"^\s*(?:⸻+|[-_]{3,}|={3,})\s*$")


@dataclass
class Heading:
    kind: str
    number: str
    level: int
    title: str
    line_index: int


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def file_name_from_heading(h: Heading) -> str:
    if h.kind == "num":
        parts = h.number.split(".")
        num = "-".join(p.zfill(2) for p in parts)
        return f"{num}-{slugify(h.title)}.html"
    return f"{slugify(h.title)}.html"


def prev_nonempty_line(lines: list[str], i: int) -> str:
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
            level = 1  # only top-level in your patched logic
            prev = prev_nonempty_line(lines, i)
            if not DIVIDER_RE.match(prev):
                continue
            heads.append(Heading(kind="num", number=number, level=level, title=title, line_index=i))
            continue

        m = MD_HEADING_RE.match(line)
        if m:
            hashes, title = m.group(1), m.group(2)
            level = len(hashes)
            if level == 1:
                heads.append(Heading(kind="md", number="", level=level, title=title, line_index=i))
            continue
    return heads


def section_end_index(heads: list[Heading], idx: int, total_lines: int) -> int:
    cur = heads[idx]
    for j in range(idx + 1, len(heads)):
        nxt = heads[j]
        if nxt.level <= cur.level:
            return nxt.line_index
    return total_lines


# -----------------------------
# New mode: parts + front matter
# -----------------------------
def parse_front_matter(text: str) -> tuple[dict, str]:
    """
    Very small YAML front matter parser for:
      key: value
      key:
        - item
        - item
    Scalars are kept as strings.
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
    body = "\n".join(lines[end_idx + 1:]).lstrip("\n")

    meta: dict = {}
    cur_key = None

    for raw in fm_lines:
        line = raw.rstrip()
        if not line.strip():
            continue

        # list item
        m_item = re.match(r"^\s*-\s*(.+?)\s*$", line)
        if m_item and cur_key:
            meta.setdefault(cur_key, [])
            if isinstance(meta[cur_key], list):
                meta[cur_key].append(m_item.group(1))
            continue

        # key: value
        m_kv = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", line)
        if m_kv:
            key = m_kv.group(1)
            val = m_kv.group(2)
            cur_key = key
            if val == "":
                # expect list or block to follow
                meta[key] = []
            else:
                # scalar
                meta[key] = val.strip().strip('"').strip("'")
            continue

        # ignore anything else (keeps parser safe)

    return meta, body


def wipe_output_dir(out: Path) -> None:
    if not out.exists():
        return
    for p in out.glob("*"):
        if p.is_file() and p.suffix in {".html", ".json"}:
            p.unlink()


def render_index(doc_title: str, toc_entries: list[dict]) -> str:
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
        lvl = int(e.get("level", 1))
        title = escape(e.get("title", "Untitled"))
        number = escape(e.get("number", "") or "")
        url = escape(e["url"])

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


def render_page(doc_title: str, page_title: str, body_text: str, meta: dict, prev_url: str | None, next_url: str | None) -> str:
    nav_bits = ['<a href="./index.html">Index</a>']
    if prev_url:
        nav_bits.append(f'<a href="./{escape(prev_url)}">Prev</a>')
    if next_url:
        nav_bits.append(f'<a href="./{escape(next_url)}">Next</a>')
    nav = " | ".join(nav_bits)

    # embed metadata for machines (does not clutter the page)
    meta_json = escape(json.dumps(meta, ensure_ascii=False, indent=2))

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
        f'<script type="application/json" id="section-meta">{meta_json}</script>',
        '<pre style="white-space:pre-wrap;line-height:1.35">',
        escape(body_text),
        "</pre>",
        "</main>",
        "</body>",
        "</html>",
    ])


def build_from_parts(parts_dir: Path, outdir: Path, doc_title: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    wipe_output_dir(outdir)

    part_files = sorted([p for p in parts_dir.glob("*.md") if p.is_file()])
    if not part_files:
        raise SystemExit(f"No parts found in {parts_dir}")

    items: list[dict] = []
    for p in part_files:
        raw = p.read_text(encoding="utf-8")
        meta, body = parse_front_matter(raw)

        # required fields (with safe defaults)
        sec_id = meta.get("id") or slugify(p.stem)
        order = meta.get("order") or "999999"
        title = meta.get("title") or p.stem
        number = meta.get("number") or ""
        level = int(meta.get("level") or 1)

        url = f"{sec_id}.html"

        # keep meta clean + consistent in toc.json
        meta_norm = {
            "id": sec_id,
            "order": order,
            "number": number,
            "level": level,
            "title": title,
            "keywords": meta.get("keywords", []),
            "summary": meta.get("summary", []),
            "related": meta.get("related", []),
            "url": url,
        }

        items.append({
            "order": order,
            "id": sec_id,
            "meta": meta_norm,
            "body": body,
        })

    # stable sort by order then id
    items.sort(key=lambda x: (x["order"], x["id"]))

    # write pages
    for i, it in enumerate(items):
        prev_url = items[i - 1]["meta"]["url"] if i > 0 else None
        next_url = items[i + 1]["meta"]["url"] if i + 1 < len(items) else None

        m = it["meta"]
        page_title = f'{m["number"]}. {m["title"]}'.strip(". ").strip() if m["number"] else m["title"]
        html = render_page(doc_title, page_title, it["body"], m, prev_url, next_url)
        (outdir / m["url"]).write_text(html, encoding="utf-8")

    toc_entries = [it["meta"] for it in items]

    (outdir / "index.html").write_text(render_index(doc_title, toc_entries), encoding="utf-8")
    (outdir / "toc.json").write_text(json.dumps(toc_entries, ensure_ascii=False, indent=2), encoding="utf-8")


def build_from_single_file(src_path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    wipe_output_dir(outdir)

    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    doc_title = "Dossier"
    for ln in lines:
        if ln.strip():
            doc_title = ln.strip().lstrip("#").strip()
            break

    heads = detect_headings(lines)

    if not heads:
        page = render_page(doc_title, "Full Document", text, {}, None, None)
        (outdir / "full.html").write_text(page, encoding="utf-8")
        idx = render_index(doc_title, [{"level": 1, "title": "Full Document", "number": "", "url": "full.html"}])
        (outdir / "index.html").write_text(idx, encoding="utf-8")
        (outdir / "toc.json").write_text(
            json.dumps([{"level": 1, "title": "Full Document", "number": "", "url": "full.html"}], indent=2),
            encoding="utf-8",
        )
        return

    entries: list[dict] = []
    pages: list[tuple[Heading, str]] = []

    for h in heads:
        fn = file_name_from_heading(h)
        pages.append((h, fn))
        entries.append({
            "kind": h.kind,
            "number": h.number,
            "level": h.level,
            "title": h.title,
            "url": fn,
        })

    for i, (h, fn) in enumerate(pages):
        prev_url = pages[i - 1][1] if i > 0 else None
        next_url = pages[i + 1][1] if i + 1 < len(pages) else None

        end = section_end_index(heads, i, len(lines))
        body = "\n".join(lines[h.line_index:end]).strip() + "\n"

        title_bits = []
        if h.kind == "num":
            title_bits.append(h.number + ".")
        title_bits.append(h.title)
        page_title = " ".join(title_bits).strip()

        html = render_page(doc_title, page_title, body, {}, prev_url, next_url)
        (outdir / fn).write_text(html, encoding="utf-8")

    (outdir / "index.html").write_text(render_index(doc_title, entries), encoding="utf-8")
    (outdir / "toc.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")


def main(src: str, outdir: str):
    src_path = Path(src)
    out_path = Path(outdir)

    # set your actual dossier title here
    doc_title = "Trump’s Second Term, Elite Factions, Legacy Media, and the Compliance Stack"

    if src_path.is_dir():
        build_from_parts(src_path, out_path, doc_title)
    else:
        build_from_single_file(src_path, out_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage:")
        print("  python split_dossier.py <parts_dir> <output_dir>")
        print("  python split_dossier.py <source.md> <output_dir>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
