#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class QueueItem:
    claim: str
    part: Path
    insert_after: str | None
    date: str
    title: str
    tags: str
    note: str
    sources: list[str]


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _parse_kv(text: str) -> tuple[str, str | None]:
    if ":" not in text:
        return text.strip(), None
    key, raw = text.split(":", 1)
    key = key.strip()
    value = raw.strip()
    if value == "":
        return key, None
    return key, _strip_quotes(value)


def load_queue(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Queue file not found: {path}")

    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_list_key: str | None = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if indent == 0 and stripped.startswith("- "):
            current = {}
            items.append(current)
            current_list_key = None
            remainder = stripped[2:].strip()
            if remainder:
                key, value = _parse_kv(remainder)
                if value is None:
                    current[key] = []
                    current_list_key = key
                else:
                    current[key] = value
            continue

        if current is None:
            continue

        if stripped.startswith("- ") and current_list_key:
            current[current_list_key].append(_strip_quotes(stripped[2:]))
            continue

        key, value = _parse_kv(stripped)
        if value is None:
            current[key] = []
            current_list_key = key
        else:
            current[key] = value
            current_list_key = None

    return items


def _ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [text]


def normalize_item(raw: dict[str, Any]) -> QueueItem:
    claim = str(raw.get("claim", "")).strip()
    part = Path(str(raw.get("part", "")).strip())
    insert_after = str(raw.get("insert_after", "")).strip() or None
    date = str(raw.get("date", "")).strip()
    title = str(raw.get("title", "")).strip()
    tags_raw = raw.get("tags", "")
    note = str(raw.get("note", "")).strip()
    sources = _ensure_list(raw.get("sources"))

    if isinstance(tags_raw, list):
        tags = ",".join([str(t).strip().lower().replace(" ", "-") for t in tags_raw if str(t).strip()])
    else:
        tags = str(tags_raw).strip()

    if not claim:
        raise ValueError("Queue item is missing required field: claim")
    if not part.as_posix():
        raise ValueError("Queue item is missing required field: part")

    return QueueItem(
        claim=claim,
        part=part,
        insert_after=insert_after,
        date=date,
        title=title,
        tags=tags,
        note=note,
        sources=sources,
    )


def build_claim_block(item: QueueItem) -> list[str]:
    claim_line = item.claim.rstrip()
    if not claim_line.endswith("[C]"):
        claim_line = f"{claim_line} [C]"

    lines = [claim_line]
    lines.append(f"DATE: {item.date}")
    lines.append(f"TITLE: {item.title}")
    lines.append(f"TAGS: {item.tags}")

    if item.note:
        for idx, note_line in enumerate(item.note.splitlines()):
            note_prefix = "NOTE: " if idx == 0 else "NOTE: "
            lines.append(f"{note_prefix}{note_line.strip()}")
    else:
        lines.append("NOTE: ")

    for src in item.sources:
        lines.append(f"- {src}")

    lines.append("")
    return lines


def insert_block(text: str, block_lines: list[str], insert_after: str | None) -> str:
    lines = text.splitlines()
    insert_idx = len(lines)
    if insert_after:
        for idx, line in enumerate(lines):
            if insert_after in line:
                insert_idx = idx + 1
                break

    if insert_idx > 0 and lines[insert_idx - 1].strip():
        block_lines = [""] + block_lines

    new_lines = lines[:insert_idx] + block_lines + lines[insert_idx:]
    return "\n".join(new_lines).rstrip() + "\n"


def apply_queue(queue_path: Path, root: Path, dry_run: bool) -> list[Path]:
    items = [normalize_item(raw) for raw in load_queue(queue_path)]
    touched: list[Path] = []

    for item in items:
        part_path = (root / item.part).resolve()
        if not part_path.exists():
            raise FileNotFoundError(f"Part not found: {part_path}")

        original = part_path.read_text(encoding="utf-8")
        updated = insert_block(original, build_claim_block(item), item.insert_after)

        if updated != original:
            touched.append(part_path)
            if not dry_run:
                part_path.write_text(updated, encoding="utf-8")

    return touched


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply claim queue YAML into dossier parts.")
    parser.add_argument(
        "queue",
        type=Path,
        nargs="?",
        default=Path("dossier/claim_queue.yaml"),
        help="Path to the queue YAML file (default: dossier/claim_queue.yaml)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repository root (default: .)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing files.")
    args = parser.parse_args()

    touched = apply_queue(args.queue, args.root, args.dry_run)
    if args.dry_run:
        if touched:
            print("Would update:")
            for path in touched:
                print(f"- {path}")
        else:
            print("No changes.")
    else:
        if touched:
            print("Updated:")
            for path in touched:
                print(f"- {path}")
        else:
            print("No changes.")


if __name__ == "__main__":
    main()
