--- a/dossier/claims_format.md
+++ b/dossier/claims_format.md
@@
 # Claims format (repo standard)
 
-Goal: keep inference readable in the dossier, while hiding evidence/link clutter on human HTML pages and extracting it into claims.json.
+Goal: Keep the main dossier narrative clean and readable for humans while providing structured, extractable evidence/sources (e.g., for claims.json or verification). 
+The [C] marker and everything after it (until a blank line) is hidden in rendered HTML views, keeping the reading experience uncluttered.
 
 ## How to write a claim
-
-Write the claim sentence as normal prose, then put `[C]` at the end of the line.
-
-Immediately below it, put any evidence notes, links, citations, or verification paths.
-
-Stop the “evidence block” with a BLANK LINE.
-
-Example:
-
-Vanguard, BlackRock, and State Street frequently appear among the largest institutional holders across many S&P 500 companies due to broad index-fund ownership and related institutional positions. [C]
-Evidence:
-- SEC EDGAR 13F filings (Vanguard / BlackRock / State Street)
-- Nasdaq institutional holders pages for tickers
-Notes:
-- Prefer primary filings when possible.
-
-(Blank line ends the evidence block)
+Integrate the claim as a normal sentence/paragraph in the narrative flow, ending the claim sentence with ` [C]` (space before bracket recommended for readability).
+
+Immediately after the claim line, insert the structured metadata block:
+
+[C]
+DATE: YYYY-MM-DD  (date of the event, primary source publication, or verification; omit if structural, timeless, or inapplicable)
+TITLE: Concise descriptive title of the claim/event
+TAGS: lowercase, hyphenated, comma-separated keywords (no spaces after commas, e.g., tag1,tag2,tag3)
+NOTE: Optional free-text notes (multi-line OK; e.g., updates, caveats, or additional context)
+- https://primary-source-url.example
+- https://secondary-source-url.example
+
+End the block with a blank line (this terminates the hidden section).
+
+Multiple URLs are fully supported as bulleted lines.
+
+## Example (from 08-trump-vs-architecture.md, section 8.8.3)
+
+National Guardsman Sarah Beckstrom was killed and National Guardsman Andrew Wolfe was seriously injured in what prosecutors described as an ambush-style shooting in Washington, D.C.; the suspect, Rahmanullah Lakanwal, later faced a federal complaint adding firearm-related counts tied to transporting (including a stolen) firearm across state lines, moving the case into U.S. District Court where capital punishment can be considered. [C]
+DATE: 2025-11-26
+TITLE: Ambush-style shooting of National Guardsmen near Farragut West Metro (Washington, D.C.)
+TAGS: national-guard,washington-dc,firearms,immigration,doj
+NOTE: DOJ says Beckstrom died 2025-11-27; added charges announced 2025-12-24.
+- https://www.justice.gov/usao-dc/pr/afghan-national-charged-murder-national-guard-soldier-sarah-beckstrom
+- https://www.justice.gov/usao-dc/pr/new-federal-charges-killing-national-guardsman-sarah-beckstrom-and-shooting-guardsman
 
 ## Rules
-
-- `[C]` must be on the same line as the claim sentence.
-- Everything after that line is “evidence” until a blank line.
-- Evidence can be multi-line, bullets, indented, whatever. Only the blank line matters.
-- Human pages hide `[C]` and hide the evidence block after it.
-- claims.json keeps the claim + evidence block for verification.
-- claims.min.json is a skim list (no links browsing required).
+- The `[C]` marker **must** appear at the end of the claim sentence/line.
+- The structured metadata block **must** start on the very next line.
+- Use the exact field order and labels (DATE:, TITLE:, TAGS:, NOTE:).
+- TAGS must be relevant, consistent across the repo, and comma-separated without spaces.
+- URLs must be bulleted (`- `) and be direct primary sources when possible.
+- The block ends **only** with a blank line (headings, new [C] blocks, or other content will also terminate it implicitly).
+- Do not mix old loose "Evidence:/Notes:" style — always use the structured format for consistency and easier extraction.
 
 ## What counts as a new block boundary
-
-A blank line always ends the evidence block.
-Also, a new claim line (contains `[C]`) ends the previous block.
-Also, section boundaries (headings/dividers) end the block.
+A blank line always ends the hidden metadata block.  
+A new `[C]` line or major section heading will also terminate the previous block.
+
+## Placement Guidelines
+- Attach claims to the most specific relevant paragraph or subsection.
+- Prefer integrating as inline prose sentences rather than isolated bullets (keeps narrative flow).
+- Hierarchy choices for new claims:
+  - Major standalone claim → new numbered subsection (e.g., 8.8.7) with supporting text.
+  - Supporting detail → new sentence/paragraph under existing subsection.
+  - Minor evidentiary point → bullet or sub-bullet under an existing statement.
+- For updates to existing claims → add/revise URLs, update NOTE, or adjust DATE/TITLE as needed.
+
+## Guidelines for AI/LLM Usage
+When an LLM is asked to verify, source, or add claims:
+- Existing claim: Add new URLs to the bullet list or update NOTE/DATE.
+- New claim: Identify the most relevant dossier file and section, then output a **unified diff patch** showing exact insertion point.
+- Patch should insert the full claim sentence + [C] block at the appropriate location (e.g., end of a paragraph or new subsection).
+- Suggest precise context lines (e.g., insert after a specific existing sentence).
+- This enables easy application via copy-paste or `git apply`.
+
+Example patch snippet for a new claim:
+
+```diff
+@@
+ Some existing paragraph text that the new claim supports or extends.
+ 
+-Existing sentence.
++Existing sentence.
++
++New factual claim sentence here describing the event or fact. [C]
++DATE: 2026-01-01
++TITLE: Short title
++TAGS: tag1,tag2
++NOTE: Optional note about updates or caveats.
++- https://source1.example
++- https://source2.example
+```
