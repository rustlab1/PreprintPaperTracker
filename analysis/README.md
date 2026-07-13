# Analysis

Materials to reproduce the published analysis.

## Contents

    make_figures.py               Reproduces Figure 1 and Figure 2
    statistics.py                 Reproduces every statistic reported in the paper
    data/full_corpus_labels.csv   72,644 preprint-publication pairs with labels
    data/journal_metrics.json     Journal to OpenAlex 2-year mean citedness
    codebook/prompt_v7.1.md       Locked extraction and comparison prompt
    codebook/claim_definitions.md Operational claim definitions
    validation/                   Aggregate reliability tables for the 550-pair subsample
    DATA_DICTIONARY.md            Column definitions for full_corpus_labels.csv
    requirements.txt              Python dependencies

## Run

    pip install -r requirements.txt

    python3 make_figures.py                        # Figure 1 and Figure 2
    python3 statistics.py                          # all reported statistics
    python3 validation/reliability_from_tables.py  # reliability values

`make_figures.py` writes to `figures/`: Figure1_headline (pdf and png),
Figure2_drivers (pdf and png), and `figure_stats.txt` with the values behind each
panel. Figures are vector PDFs with embedded fonts.

`statistics.py` and `reliability_from_tables.py` print each value next to the
corresponding value in the manuscript.
