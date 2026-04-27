# Preprint Browser

Self-contained static website for browsing the v7.1-labeled preprint-to-publication dataset.

## Files

- `index.html` — the app (HTML + CSS + JS, ~30 KB)
- `papers.json` — the data (~6 MB, 3,010 records with v7.1 labels and metadata)

## To open locally

Most browsers won't `fetch()` a local JSON file via `file://` for security reasons. Use one of these:

**Python one-liner (works anywhere with Python):**
```bash
cd paper_browser/site
python3 -m http.server 8000
# open http://localhost:8000 in your browser
```

**VS Code Live Server:** install the extension, right-click `index.html` → Open with Live Server.

**Any other static server:** `npx serve`, `caddy`, etc.

## To deploy publicly (recommended for sharing with collaborators)

The site is two files. Drop them on:

- **GitHub Pages:** push to a branch, enable Pages. Free, instant.
- **Netlify Drop:** drag the `site/` folder onto netlify.com/drop. Free, no account needed.
- **Cloudflare Pages, Vercel, AWS S3 + CloudFront** — any static host works.

Total size: ~6 MB. No server-side code, no build step, no dependencies beyond a browser.

## Features

- Search by title, author, journal, institution, ID, category (live, instant filtering)
- Filter chips: change label, hedging direction, type changed, retracted-only
- Dropdown filters: category, year
- Card grid with badges showing label, hedging, type-changed flag, retraction
- Click any card → modal with:
  - Full bibliographic metadata
  - DOI links to bioRxiv and to journal version
  - Side-by-side preprint vs published primary claim with type tags
  - Side-by-side secondary claims 1 and 2
  - Sonnet's one-sentence reasoning for the labels
- Pagination (60 per page) with first/prev/next/last + jump-to-page
- Keyboard: Esc closes modal

## Visual style

Matches the v7.1 report (Inter font, navy primary, amber/red accents).

## Updating the data

To regenerate `papers.json` after a new run:

```bash
python3 sessions/2026-04-22_kappa_pilot/scripts/build_paper_browser_json.py
```

(Script recreated each time the dataset is refreshed.)
