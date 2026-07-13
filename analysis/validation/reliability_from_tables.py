#!/usr/bin/env python3
"""
reliability_from_tables.py
--------------------------
Reproduces every inter-rater reliability figure reported in the manuscript
using ONLY the aggregate tables in this directory. No row-level rater labels
are required: quadratic-weighted Cohen's kappa, Krippendorff's alpha and
Gwet's AC1 are all functions of the contingency / coincidence matrices.

    python reliability_from_tables.py

Requires: numpy, pandas.
"""
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CONTENT = ["unchanged", "minor", "major"]
HEDGE = ["weakened", "unchanged", "strengthened"]


def kappa_quadratic(O):
    """Quadratic-weighted Cohen's kappa from a square confusion matrix."""
    O = np.asarray(O, float)
    k = O.shape[0]
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], float)
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (W * O).sum() / (W * E).sum()


def alpha_ordinal(o):
    """Krippendorff's alpha, ordinal metric, from a coincidence matrix."""
    o = np.asarray(o, float)
    k = o.shape[0]
    nc = o.sum(1)
    n = nc.sum()
    d = np.zeros((k, k))
    for c in range(k):
        for j in range(k):
            lo, hi = min(c, j), max(c, j)
            d[c, j] = (nc[lo:hi + 1].sum() - (nc[c] + nc[j]) / 2.0) ** 2
    Do = (o * d).sum() / n
    De = (np.outer(nc, nc) * d).sum() / (n * (n - 1))
    return 1 - Do / De


def kappa_and_ac1_binary(O):
    """Unweighted Cohen's kappa and Gwet's AC1 from a 2x2 confusion matrix."""
    O = np.asarray(O, float)
    n = O.sum()
    pa = np.trace(O) / n
    p1 = (O.sum(0) + O.sum(1)) / (2 * n)           # marginal prevalence of each class
    pe_kappa = (O.sum(0) / n * O.sum(1) / n).sum()
    pe_ac1 = 2 * p1[0] * p1[1]                     # Gwet's chance-agreement term
    return (pa - pe_kappa) / (1 - pe_kappa), (pa - pe_ac1) / (1 - pe_ac1)


def collapse_major(O):
    """3x3 (unchanged, minor, major) -> 2x2 (non-major, major)."""
    O = np.asarray(O, float)
    return np.array([[O[:2, :2].sum(), O[:2, 2].sum()],
                     [O[2, :2].sum(), O[2, 2]]])


def line(label, value, paper):
    print(f"  {label:<44} {value:>7}   manuscript: {paper}")


# ------------------------------------------------------------------ content
cm = pd.read_csv(HERE / "content_model_vs_consensus.csv", index_col=0).values
coin = pd.read_csv(HERE / "content_rater_coincidence.csv", index_col=0).values
pk = pd.read_csv(HERE / "content_pairwise_kappa.csv")
cal = pd.read_csv(HERE / "content_calibration.csv")

n = int(cm.sum())
two_level = int(cm[0, 2] + cm[2, 0])
rr = pk.loc[pk.type == "rater-rater", "kappa_quadratic"]
mr = pk.loc[pk.type == "model-rater", "kappa_quadratic"]
k_bin, ac1_bin = kappa_and_ac1_binary(collapse_major(cm))

print(f"\nCONTENT CHANGE  (n = {n} pairs, 4 raters)")
line("rater-rater kappa (quadratic), mean", f"{rr.mean():.2f}", "0.76")
line("  range across the 6 rater pairs", f"{rr.min():.2f}-{rr.max():.2f}", "0.70-0.82")
line("Krippendorff's alpha (ordinal)", f"{alpha_ordinal(coin):.2f}", "0.77")
line("model vs consensus, kappa (quadratic)", f"{kappa_quadratic(cm):.2f}", "0.76")
line("model vs individual raters, mean kappa", f"{mr.mean():.2f}", "0.67")
line("all 10 comparisons >= 0.61", str(bool((pk.kappa_quadratic >= 0.61).all())), "True")
line("within one ordinal level of consensus", f"{100 * (n - two_level) / n:.1f}%", "98.9%")
line("two-level discordant (unchanged vs major)", f"{two_level} ({100 * two_level / n:.1f}%)", "6 (1.1%)")
line("major-vs-non-major: kappa / AC1", f"{k_bin:.2f}/{ac1_bin:.2f}", "0.70 / 0.76")
line("model called major, 0 of 4 raters did", f"{cal.pct_model_called_major.iloc[0]:.0f}%", "12%")
line("model called major, 4 of 4 raters did", f"{cal.pct_model_called_major.iloc[4]:.0f}%", "93%")

# ------------------------------------------------------------------ hedging
hm = pd.read_csv(HERE / "hedging_model_vs_consensus.csv", index_col=0).values
hd = pd.read_csv(HERE / "hedging_direction_by_rater.csv")

nh = int(hm.sum())
inv = int(hm[0, 2] + hm[2, 0])
pooled = hd.loc[hd.source == "raters_pooled", "ratio_cautious_to_confident"].iloc[0]
model = hd.loc[hd.source == "model", "ratio_cautious_to_confident"].iloc[0]
per_rater = hd[hd.source.str.match(r"R\d")]

print(f"\nHEDGING SHIFT  (n = {nh} pairs with a rater majority)")
line("direction inversions (opposite calls)", f"{inv} ({100 * inv / nh:.1f}%)", "4 (0.9%)")
line("cautious:confident, raters pooled", f"{pooled:.1f}x", "1.6x")
line("cautious:confident, model", f"{model:.1f}x", "2.0x")
line("every individual rater above parity", str(bool((per_rater.ratio_cautious_to_confident > 1).all())), "True")

print("\nAll values above were computed from the aggregate tables in this")
print("directory. Individual rater labels are not required and are not shared.\n")
