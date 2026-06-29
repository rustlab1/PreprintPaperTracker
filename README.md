# Preprint → Publication Tracker

A searchable companion site for **Yin & Rust, _Tracking claim changes from preprint to publication across 72,644 biomedical studies using large language models._**

Every bioRxiv preprint posted 2018–2025 that could be matched by DOI to its peer-reviewed publication, labelled at the level of the scientific claim by Claude Sonnet 4.6. The site lets anyone search the full dataset and explore interactive versions of every figure in the paper.

## Site structure

A static three-page site. Open `index.html` to start.

- **`index.html`** — overview: headline numbers, abstract, unified search box.
- **`findings.html`** — interactive reproductions of Figure 1 (a–f) and Figure 2 (a–f) plus the validation panel, computed live from `data/stats.json`.
- **`browser.html`** — searchable browser over all **72,644** pairs, with claim-text search, filters, and a per-pair modal showing the preprint vs published claims and the model's reasoning.

## Data files (`data/`)

The dataset is split into a lightweight search index plus on-demand detail shards, so the browser loads fast and only fetches full claim text when a pair is opened.

- **`data/index.json`** (~43 MB) — one row per pair: title, first author, corresponding author, institution, journal, field, year, days-to-publication, journal impact, all content/hedging/type labels, and the **published primary claim** (searchable). Served gzipped (~15 MB over the wire) by GitHub Pages.
- **`data/d/0.json` … `data/d/60.json`** — detail shards (1,200 pairs each): preprint primary claim, both versions of secondary claims 1 & 2, model reasoning, full author list, dates, PubMed ID, abstract similarity. Loaded only when a card is opened.
- **`data/stats.json`** (~9 KB) — pre-computed panel data for every figure on the findings page.

All numbers are computed directly from the corpus and match the manuscript (e.g. content change 39.9 / 50.0 / 10.2%; hedging 85.6 / 8.4 / 4.2%; year trend 17.0% → 5.7%; review tertiles 7.0 / 9.5 / 14.1%; retraction RR 2.31).

## Preview locally

Browsers block `fetch()` from `file://`, so run a quick local server:

```bash
cd PreprintPaperTracker
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy on GitHub Pages

```bash
git add -A
git commit -m "Full 72,644-pair searchable site"
git push
```

Then enable **Settings → Pages → Deploy from branch → `main` / root**. The site goes live at `https://<username>.github.io/PreprintPaperTracker/` within a minute. Nothing is tracked via Git LFS, so all data files are served as normal blobs.

Repo size is ~170 MB (index + shards), under GitHub's 1 GB soft limit and 100 MB per-file hard limit.

## Methodology (summary)

Codebook v7.1, locked 25 April 2026. Claude Sonnet 4.6 (`claude-sonnet-4-6`) at temperature 0, 1,200-token output, structured JSON. Each abstract pair is parsed into one primary and two secondary claims; each claim is assigned a type (mechanism, association, descriptive, method, therapeutic, null result), a content-change label (unchanged, minor, major) and a hedging shift (more cautious, unchanged, more confident).

Validation on 120 stratified pairs: model–expert agreement Cohen's κ 0.63–0.66 vs expert–expert 0.60; three replicate Sonnet runs κ = 0.75. Journal impact is the OpenAlex 2-year mean citedness (908 journals, 59,012 pairs), not the Journal Impact Factor. Retraction analysis uses the Crossref-hosted Retraction Watch database (47 journals with unambiguous ISSNs): preprinted 9 / 11,114 vs non-preprinted 813 / 435,159; rate ratio 2.31 (95% CI 1.20–4.45, Fisher one-sided P = 0.003).

## Rebuilding the data

The `data/` files are generated from the parent project's `sessions/full_extraction/analysis/full_corpus_labels.csv` (authoritative labels), `data/processed/full_analysis_data_v2.csv` (bibliographic metadata), `sessions/full_extraction/results/sonnet_full_labels.csv` (claim text + reasoning), and `data/processed/journal_metrics.json` (impact). Re-run the build after each new extraction round.
