# Preprint to Publication

Data, code, and companion website for

> Yin H, Anh W, Forster PM, Rust R. Tracking claim changes from preprint to
> publication across 72,644 biomedical studies using large language models.

Every bioRxiv preprint published in a peer-reviewed journal between January 2021
and February 2025 that could be matched to its published version by DOI was
compared at the level of the scientific claim. A large language model (Claude
Sonnet 4.6) parsed each preprint and published abstract into one primary and two
secondary claims and labelled every pair for content change (unchanged, minor,
major), hedging shift (more cautious, more confident, unchanged), and claim type.
The final corpus contains 72,644 matched abstract pairs, posted between 2018 and
2025.

## Repository structure

    analysis/              Materials to reproduce the published analysis
      make_figures.py      Reproduces Figure 1 and Figure 2
      statistics.py        Reproduces every statistic reported in the paper
      data/                full_corpus_labels.csv, journal_metrics.json
      codebook/            Locked v7.1 prompt and claim definitions
      validation/          Aggregate reliability tables for the 550-pair subsample
      DATA_DICTIONARY.md   Column definitions for full_corpus_labels.csv
      requirements.txt     Python dependencies

    index.html             Companion website (entry point)
    browser.html           Searchable browser over all 72,644 pairs
    findings.html          Interactive versions of Figure 1 and Figure 2
    data/                  Website data (index.json, detail shards, stats.json)

    maintenance/           Ongoing updates to the website, separate from the paper
      update_pending.py

## Reproduce

    cd analysis
    pip install -r requirements.txt

    python3 make_figures.py           # Figure 1 and Figure 2 -> analysis/figures
    python3 statistics.py             # every statistic reported in the paper
    python3 validation/reliability_from_tables.py   # the reliability values

`make_figures.py` also writes `figure_stats.txt`, listing the values behind each
panel. `statistics.py` prints each result next to the corresponding value in the
manuscript.

## Companion website

The searchable site is served with GitHub Pages from the repository root:
https://rustlab1.github.io/PreprintPaperTracker/ . `index.html` is the entry
point, `findings.html` reproduces the figures interactively, and `browser.html`
searches all 72,644 pairs.

## Continuous updates

bioRxiv continues to link older preprints to their journal articles.
`maintenance/update_pending.py` harvests preprints published after the corpus
cut-off and adds them to the website with a "Not assessed yet" tag. This keeps
the browsable database current. It is separate from the analysis reported in the
paper: it assigns no labels and changes no published result.

## Method summary

Codebook v7.1, locked 25 April 2026. Claude Sonnet 4.6 (`claude-sonnet-4-6`) at
temperature 0 with a 1,200-token output limit, returning structured JSON. Content
change is labelled unchanged, minor, or major; hedging shift is labelled more
cautious, unchanged, or more confident; claim type is one of mechanistic,
associative, descriptive, methodological, therapeutic, or null result.
Validation on a stratified subsample of 550 pairs, labelled independently by four
raters, gave quadratic-weighted Cohen's kappa of 0.76 among the raters
(Krippendorff's alpha 0.77), 0.76 between the model and the rater consensus, and
0.67 between the model and individual raters. See `analysis/validation`. The full
prompt and codebook are in `analysis/codebook`.

## Citation

See `CITATION.cff`.

## License

Code is released under the MIT License (`LICENSE`). Data files are released under
CC BY 4.0.
