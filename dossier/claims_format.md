# Claims format (repo standard)

Goal: keep inference readable in the dossier, while hiding evidence/link clutter on human HTML pages and extracting it into claims.json.

## How to write a claim

Write the claim sentence as normal prose, then put `[C]` at the end of the line.

Immediately below it, put any evidence notes, links, citations, or verification paths.

Stop the “evidence block” with a BLANK LINE.

Example:

Vanguard, BlackRock, and State Street frequently appear among the largest institutional holders across many S&P 500 companies due to broad index-fund ownership and related institutional positions. [C]
Evidence:
- SEC EDGAR 13F filings (Vanguard / BlackRock / State Street)
- Nasdaq institutional holders pages for tickers
Notes:
- Prefer primary filings when possible.

(Blank line ends the evidence block)

## Rules

- `[C]` must be on the same line as the claim sentence.
- Everything after that line is “evidence” until a blank line.
- Evidence can be multi-line, bullets, indented, whatever. Only the blank line matters.
- Human pages hide `[C]` and hide the evidence block after it.
- claims.json keeps the claim + evidence block for verification.
- claims.min.json is a skim list (no links browsing required).

## What counts as a new block boundary

A blank line always ends the evidence block.
Also, a new claim line (contains `[C]`) ends the previous block.
Also, section boundaries (headings/dividers) end the block.
