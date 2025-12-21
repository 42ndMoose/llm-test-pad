import os, re, sys
from pathlib import Path
from html import escape

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
</head>
<body>
  <nav><a href="./index.html">Index</a></nav>
  <main>
    <h1>{title}</h1>
    <pre style="white-space:pre-wrap;line-height:1.35">{body}</pre>
  </main>
  <hr/>
  <footer>© 2025</footer>
</body>
</html>
"""

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"

def main(src, outdir):
    text = Path(src).read_text(encoding="utf-8")
    # split on H1 headings only
    parts = re.split(r"(?m)^(# .+)\n", text)
    # parts looks like: [preamble, "# title", body, "# title2", body2, ...]
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    pages = []
    i = 1
    while i < len(parts):
        title_line = parts[i].strip()
        title = title_line[2:].strip()
        body = parts[i+1]
        filename = f"{slugify(title)}.html"
        (out / filename).write_text(
            TEMPLATE.format(title=escape(title), body=escape(body)),
            encoding="utf-8"
        )
        pages.append((title, filename))
        i += 2

    # index
    links = "\n".join([f'<li><a href="./{fn}">{escape(t)}</a></li>' for t, fn in pages])
    index_html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Dossier Index</title></head>
<body>
<main>
<h1>Dossier Index</h1>
<p><strong>Start here:</strong> read sections as needed. Use the Claims Ledger for fast verification.</p>
<ol>{links}</ol>
</main>
</body></html>"""
    (out / "index.html").write_text(index_html, encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python split_dossier.py <source.md> <output_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
