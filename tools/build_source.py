# tools/build_source.py
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS_DIR = ROOT / "dossier" / "parts"
OUT_FILE = ROOT / "dossier" / "source.md"

DOC_TITLE = "Trump’s Second Term, Elite Factions, Legacy Media, and the Compliance Stack"


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
    body = "\n".join(lines[end_idx + 1:]).lstrip("\n")

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
                meta[cur_key].append(m_item.group(1))
            continue

        m_kv = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", line)
        if m_kv:
            key = m_kv.group(1)
            val = m_kv.group(2)
            cur_key = key

            if val == "":
                meta[key] = []  # expect list items
            else:
                meta[key] = val.strip().strip('"').strip("'")
            continue

        # ignore anything else (safe)

    return meta, body


def norm_ws(s: str) -> str:
    # Trim trailing spaces on each line, keep internal formatting
    return "\n".join(line.rstrip() for line in s.splitlines()).strip() + "\n"


def main() -> None:
    PARTS_DIR.mkdir(parents=True, exist_ok=True)

    part_files = sorted([p for p in PARTS_DIR.glob("*.md") if p.is_file()])
    if not part_files:
        raise SystemExit(f"No parts found in {PARTS_DIR}. Add at least one .md file.")

    parts: list[dict] = []

    for p in part_files:
        raw = p.read_text(encoding="utf-8")

        meta, body = parse_front_matter(raw)
        order = meta.get("order", "999999")
        title = meta.get("title", p.stem)

        # strip YAML (done) + normalize body
        body = norm_ws(body)

        # skip empty bodies
        if not body.strip():
            continue

        parts.append(
            {
                "path": p,
                "order": str(order),
                "title": str(title),
                "body": body,
            }
        )

    # Sort by YAML order, then filename as stable fallback
    parts.sort(key=lambda x: (x["order"], x["path"].name))

    chunks: list[str] = []
    # Optional: ensure a single consistent title at the top
    chunks.append(DOC_TITLE.strip() + "\n")

    for item in parts:
        p = item["path"]
        body = item["body"]

        header = f"\n\n<!-- BEGIN {p.name} -->\n\n"
        footer = f"\n\n<!-- END {p.name} -->\n\n"

        chunks.append(header + body + footer)

    OUT_FILE.write_text("".join(chunks).strip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FILE} from {len(parts)} part(s).")


if __name__ == "__main__":
    main()
