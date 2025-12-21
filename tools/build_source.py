# tools/build_source.py
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS_DIR = ROOT / "dossier" / "parts"
OUT_FILE = ROOT / "dossier" / "source.md"

def main() -> None:
    PARTS_DIR.mkdir(parents=True, exist_ok=True)

    part_files = sorted([p for p in PARTS_DIR.glob("*.md") if p.is_file()])
    if not part_files:
        raise SystemExit(f"No parts found in {PARTS_DIR}. Add at least one .md file.")

    chunks: list[str] = []
    for p in part_files:
        text = p.read_text(encoding="utf-8").strip()
        if not text:
            continue
        header = f"\n\n<!-- BEGIN {p.name} -->\n\n"
        footer = f"\n\n<!-- END {p.name} -->\n\n"
        chunks.append(header + text + footer)

    OUT_FILE.write_text("\n".join(chunks).strip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FILE} from {len(part_files)} part(s).")

if __name__ == "__main__":
    main()
