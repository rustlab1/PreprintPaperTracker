# Maintenance

Scripts that keep the companion website current. These are separate from the
analysis reported in the paper.

## update_pending.py

bioRxiv continues to link older preprints to their journal articles. This script
harvests preprints published after the corpus cut-off, keeps those not already in
the corpus, and writes `data/pending.json` and `data/pending_authors.json`. These
appear on the website with a "Not assessed yet" tag.

The script assigns no content-change, hedging, or claim-type labels. Assessment
is a separate step and does not affect any published result.

Usage:

    python3 maintenance/update_pending.py --from 2025-03-01 --to 2026-12-31

Only the Python standard library is required. The machine must be able to reach
api.biorxiv.org.
