# Analysis

Materials to reproduce the main-text figures.

## Contents

    make_figures.py               Reproduces Figure 1 and Figure 2
    data/full_corpus_labels.csv   72,644 preprint-publication pairs with labels
    data/journal_metrics.json     Journal to OpenAlex 2-year mean citedness
    codebook/prompt_v7.1.md       Locked extraction and comparison prompt
    codebook/claim_definitions.md Operational claim definitions
    validation/                   120-pair validation set
    DATA_DICTIONARY.md            Column definitions for full_corpus_labels.csv
    requirements.txt              Python dependencies

## Run

    pip install -r requirements.txt
    python3 make_figures.py

Outputs are written to `figures/`: Figure1_headline (pdf and png),
Figure2_drivers (pdf and png), and `figure_stats.txt` with the values behind
each panel. Figures are vector PDFs with embedded fonts.
