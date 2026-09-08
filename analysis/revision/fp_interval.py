"""
Fractional-polynomial model of substantial/major revision against the
preprint-to-publication interval.  Reproduces Supplementary Fig. 6 and the
interval figures quoted in the Results.

The procedure follows Royston and Altman: candidate powers are drawn from the
standard set {-2, -1, -0.5, 0, 0.5, 1, 2, 3}, degree is capped at FP2, and a
repeated power (p, p) is fitted as x**p and x**p * log(x).  Deviance
differences are compared on a chi-squared scale.

Run from the analysis/ directory:

    python3 revision/fp_interval.py
"""

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2

POWERS = [-2, -1, -0.5, 0, 0.5, 1, 2, 3]
DATA = Path(__file__).resolve().parent.parent / "data" / "full_corpus_labels.csv"


def transform(x, p):
    """Box-Tidwell power transform; p = 0 is the log."""
    return np.log(x) if p == 0 else x ** p


def design(x, powers):
    """Design matrix (with intercept) for an FP1 or FP2 term set."""
    x = np.asarray(x, dtype=float)
    if len(powers) == 1:
        cols = [transform(x, powers[0])]
    else:
        p1, p2 = powers
        # A repeated power gives x**p and x**p * log(x).
        cols = ([transform(x, p1), transform(x, p1) * np.log(x)]
                if p1 == p2 else
                [transform(x, p1), transform(x, p2)])
    return sm.add_constant(np.column_stack(cols), has_constant="add")


def deviance(y, x, powers):
    return sm.GLM(y, design(x, powers), family=sm.families.Binomial()).fit().deviance


def main():
    d = pd.read_csv(DATA, usecols=["days_to_publication", "primary_label"]).dropna()
    # The log transform requires a strictly positive interval.
    d = d[d.days_to_publication > 0]
    y = (d.primary_label.str.lower() == "major").astype(int).values
    # Scale to hundreds of days purely for numerical stability; predictions
    # on the original scale are unaffected.
    x = d.days_to_publication.astype(float).values / 100.0

    print(f"pairs with a positive interval : {len(d):,}")
    print(f"substantial/major revisions    : {y.sum():,} ({y.mean() * 100:.2f}%)\n")

    dev_linear = deviance(y, x, [1])
    fp1 = min((deviance(y, x, [p]), [p]) for p in POWERS)
    fp2 = min((deviance(y, x, list(ps)), list(ps))
              for ps in itertools.combinations_with_replacement(POWERS, 2))

    print(f"linear (power 1)      deviance {dev_linear:10.1f}")
    print(f"best FP1  powers {str(fp1[1]):>9}  deviance {fp1[0]:10.1f}")
    print(f"best FP2  powers {str(fp2[1]):>9}  deviance {fp2[0]:10.1f}   <- selected\n")

    g_lin = dev_linear - fp2[0]
    g_fp1 = fp1[0] - fp2[0]
    print(f"FP2 vs linear   chi2 = {g_lin:6.1f}, df = 2, P = {chi2.sf(g_lin, 2):.3g}")
    print(f"FP2 vs best FP1 chi2 = {g_fp1:6.1f}, df = 1, P = {chi2.sf(g_fp1, 1):.3g}\n")

    fit = sm.GLM(y, design(x, fp2[1]), family=sm.families.Binomial()).fit()
    print("predicted probability of substantial/major revision")
    for days, paper in ((90, 6.8), (365, 12.3), (730, 17.5)):
        p = fit.predict(design([days / 100.0], fp2[1]))[0] * 100
        print(f"  {days:4d} days : {p:5.1f}%   (paper: {paper}%)")


if __name__ == "__main__":
    main()
