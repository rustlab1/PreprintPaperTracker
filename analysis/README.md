# Analysis

Materials to reproduce the published analysis.

## Contents

    statistics.py                 Reproduces the statistics reported in the paper
    data/full_corpus_labels.csv   72,644 preprint-publication pairs with labels
    data/journal_metrics.json     Journal to OpenAlex 2-year mean citedness
    codebook/prompt_v7.1.md       Locked extraction and comparison prompt
    codebook/claim_definitions.md Operational claim definitions
    validation/                   Aggregate reliability tables for the 550-pair subsample
    revision/                     Analyses added during peer review
    DATA_DICTIONARY.md            Column definitions for full_corpus_labels.csv
    requirements.txt              Python dependencies

## Run

    pip install -r requirements.txt

    python3 statistics.py                          # reported statistics
    python3 validation/reliability_from_tables.py  # reliability values
    python3 revision/fp_interval.py                # interval fractional polynomial

`statistics.py`, `reliability_from_tables.py` and `fp_interval.py` print each
value next to the corresponding value in the manuscript.

Analyses added during peer review are in `revision/`. Two of them supersede
results in the original submission: the retraction analysis is now a stratified
Cox model rather than a crude rate ratio, and journal impact is now a grouped
binomial fractional-polynomial model rather than a weighted linear fit on
octiles. See `revision/README.md`.
