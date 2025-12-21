name: Build dossier pages

on:
  push:
    paths:
      - "dossier/source.md"
      - "tools/**"
      - ".github/workflows/build-dossier.yml"

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Build
        run: |
          python tools/split_dossier.py dossier/source.md dossier/site
      - name: Commit built site
        run: |
          git config user.name "dossier-bot"
          git config user.email "dossier-bot@users.noreply.github.com"
          git add dossier/site
          git commit -m "Auto-build dossier site" || exit 0
          git push
