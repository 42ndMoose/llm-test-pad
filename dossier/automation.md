# Dossier automation workflow

This workflow turns a small YAML queue into correctly formatted `[C]` claim blocks
inside the relevant dossier part files. It avoids hand-formatting, keeps evidence
metadata consistent, and lets you batch updates.

## Why this helps
- **Single source of truth:** You add items once in a queue file.
- **Consistent formatting:** The script enforces the `[C]` block shape.
- **Scalable updates:** Batch multiple claims across multiple sections.

## Queue format (minimal YAML)
Edit `dossier/claim_queue.yaml` and add items like:

```yaml
- claim: "Claim sentence goes here."
  part: "dossier/parts/05-censorship-compliance-network.md"
  insert_after: "## 5.1"
  date: "2025-07-11"
  title: "Short claim title"
  tags:
    - "tag-one"
    - "tag-two"
  note: "Optional note; keep it short."
  sources:
    - "https://primary-source.example"
    - "/dossier/site/assets/mirrors/local-copy.html"
```

### Field guide
- `claim` (**required**): Sentence or paragraph you want inserted. `[C]` is added if missing.
- `part` (**required**): Target file path under the repo.
- `insert_after` (optional): Substring match for insertion line. If missing, appends to end.
- `date`, `title`, `tags`, `note` (optional): Structured metadata fields.
- `sources` (optional list): URLs or local mirror paths, added as bullet lines.

## Run the queue script
From repo root:

```bash
python tools/claim_queue.py --dry-run
python tools/claim_queue.py
```

The script inserts `[C]` blocks using the order required by `dossier/claims_format.md`.

## Suggested end-to-end flow
1. Add queue items for new claims.
2. Run `python tools/claim_queue.py`.
3. Rebuild the public artifacts:
   - `python tools/build_source.py`
   - `python tools/split_dossier.py dossier/source.md dossier/site`
   - `python tools/build_claims.py dossier/source.md`

## Notes
- The queue parser accepts a minimal YAML subset (list of objects with scalar fields
  and simple lists). Keep it simple; no nested objects.
- If `insert_after` does not match, the claim is appended at the end of the file.
