# Preprint Tracker

A meta-science study of how scientific claims change between bioRxiv preprints and their peer-reviewed journal versions.

## Site structure

This is a static three-page website. Open `index.html` to start.

- **`index.html`** — landing page with navigation
- **`findings.html`** — key findings with embedded figures and short explanations
- **`browser.html`** — searchable database of all 3,010 preprint–publication pairs
- **`papers.json`** — the dataset (6.4 MB, 3,010 records with v7.1 labels and metadata)

## To preview locally

Browsers refuse `fetch()` from `file://`, so you need a quick local server:

```bash
cd PreprintPaperTracker
python3 -m http.server 8000
# open http://localhost:8000 in your browser
```

## Deployment

Push to GitHub and enable **Settings → Pages → Deploy from branch (main, root)**. Your site goes live at `https://USERNAME.github.io/REPO/` within a minute.

Total repo size: ~6.4 MB. Well under GitHub's 100 MB per-file and 1 GB repo soft limits.

## Features

**Browser page (`browser.html`):**
- Live search across title, author, corresponding author, institution, journal, category, ID
- Filter chips: change label, hedging direction, type-changed, retracted-only
- Dropdowns: bioRxiv category, year
- Click any card → modal with full bibliographic metadata, DOI links, side-by-side primary and secondary claims, Sonnet's reasoning
- Pagination with first/prev/next/last + jump-to-page

**Findings page (`findings.html`):**
- Seven curated highlight figures with brief explanations
- Self-contained: figures embedded as base64, no external image hosting needed
- ~1.4 MB total page size

**Landing page (`index.html`):**
- Three primary navigation cards (browse / findings / methodology)
- Stats strip with headline numbers

## Visual style

Inter typography, navy primary (`#1E3A8A`), warm coral accent (`#FF6B6B`), generous whitespace, rounded cards, subtle shadows. Inspired by Airbnb's minimalist product surfaces.

## Methodology

Codebook v7.1 (locked April 2026). Sonnet 4.6 at temperature 0. Reliability:

- Sonnet vs Opus on n=425: κ = 0.66 (binary modified/preserved), 95% CI [0.55, 0.77]
- Sonnet vs Opus claim type (6-level): κ = 0.78–0.81
- Intra-Sonnet (3 runs): κ = 0.89, 95% CI [0.83, 0.94]

Retraction analysis: matched cohort of 11,114 preprint-published vs 435,159 non-preprint papers in 47 journals, 2018–2022. Rate ratio 2.31× (95% CI 1.20–4.45, Fisher one-sided p = 0.003).

## To regenerate `papers.json`

Re-run the build script in the parent project after each new extraction round.
