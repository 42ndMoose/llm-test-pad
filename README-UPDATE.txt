Update your GitHub Pages site with About + persistent Notes
=============================================================

Files in this update:
- index.html      (updated with nav)
- about.html      (static page, easy to edit in GitHub)
- notes.html      (renders notes.txt via Jekyll include_relative)
- notes.txt       (the content you can edit; persists across refresh)
- README-UPDATE.txt

How to update on GitHub (no command line):
1) Open your repo (42ndmoose/llm-test-pad).
2) Click "Add file" → "Upload files".
3) Drag these files in. If asked to replace index.html, agree.
4) Commit changes.
5) Wait ~30–90 seconds and reload your site:
   - /about.html
   - /notes.html (pulls the content of notes.txt)
6) To change the notes later: open notes.txt in GitHub → Edit → Commit.
