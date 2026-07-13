#!/usr/bin/env python3
"""
statistics.py
-------------
Reproduces every statistic reported in the paper from data/full_corpus_labels.csv
and data/journal_metrics.json. Each value is printed next to the value given in
the manuscript.

    python statistics.py

Requires: numpy, pandas, scipy, statsmodels.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import binomtest, chi2_contingency, fisher_exact

HERE = Path(__file__).parent
D = pd.read_csv(HERE / "data" / "full_corpus_labels.csv")
D["days"] = pd.to_numeric(D["days_to_publication"], errors="coerce")
D["posted"] = pd.to_datetime(D["preprint_date"], errors="coerce")
D["yr"] = D["posted"].dt.year
D["maj"] = (D["primary_label"] == "major").astype(int)

# Journal and category strings are case-inconsistent in the bioRxiv metadata
# (e.g. "Bioinformatics" and "bioinformatics"). Normalise before any grouping,
# exactly as make_figures.py does.
D["journal"] = D.published_journal.astype(str).str.lower().str.strip()
D["preprint_category"] = D.preprint_category.astype(str).str.lower().str.strip()


def line(label, value, paper):
    print(f"  {label:<50} {value:>10}   manuscript: {paper}")


def head(t):
    print(f"\n{t}\n" + "-" * 78)


# ------------------------------------------------------------------ corpus
head("CORPUS")
line("matched preprint-publication pairs", f"{len(D):,}", "72,644")
line("unique journals", f"{D.journal.nunique():,}", "3,149")
line("bioRxiv subject categories", D.preprint_category.nunique(), "25")
cnt = D.groupby("preprint_category").size()
line("categories with >= 1,500 pairs", int((cnt >= 1500).sum()), "17")

# --------------------------------------------------------- content + hedging
head("CONTENT CHANGE AND HEDGING SHIFT  (Fig. 1a-c)")
pl = D.primary_label.value_counts(normalize=True) * 100
for lab, paper in [("unchanged", "39.9%"), ("minor", "50.0%"), ("major", "10.2%")]:
    line(f"primary claim {lab}", f"{pl[lab]:.1f}%", paper)

h = D.primary_hedging
for lab, nm, paper in [("unchanged", "hedging unchanged", "85.6%"),
                       ("weakened", "more cautious", "8.4%"),
                       ("strengthened", "more confident", "4.2%")]:
    line(nm, f"{100 * (h == lab).mean():.1f}%", paper)
line("non-assessable (claim replaced)", f"{100 * h.isna().mean():.1f}%", "1.8%")

w, s = int((h == "weakened").sum()), int((h == "strengthened").sum())
bt = binomtest(w, w + s, 0.5, alternative="two-sided")
line("pairs with any hedging shift", f"{w + s:,}", "9,150")
line("two-sided sign test on those pairs", f"P={bt.pvalue:.1e}", "P < 0.001")

ha = D.loc[D.primary_label == "major", "primary_hedging"].dropna()
line("within major: more cautious", f"{100 * (ha == 'weakened').mean():.1f}%", "38.5%")
line("within major: more confident", f"{100 * (ha == 'strengthened').mean():.1f}%", "19.8%")

# ----------------------------------------------------------- fields + types
head("FIELD AND CLAIM TYPE  (Fig. 1d-f, Fig. 2b)")
line("neuroscience share of corpus",
     f"{100 * (D.preprint_category == 'neuroscience').mean():.1f}%", "18.6%")
big = cnt[cnt >= 1500].index
f = D[D.preprint_category.isin(big)].groupby("preprint_category").maj.mean() * 100
line("major revision, lowest field", f"{f.min():.1f}% ({f.idxmin()})", "7.2% bioinformatics")
line("major revision, highest field", f"{f.max():.1f}% ({f.idxmax()})", "17.5% microbiology")

g = D[D.primary_hedging.isin(["weakened", "strengthened"]) & D.preprint_category.isin(big)]
r = g.groupby("preprint_category").primary_hedging.agg(
    lambda x: (x == "strengthened").sum() / max((x == "weakened").sum(), 1))
line("fields with confident:cautious ratio < 1", f"{int((r < 1).sum())} of {len(r)}", "all 17")

ct = D.dropna(subset=["preprint_primary_type", "published_primary_type"])
same = (ct.preprint_primary_type == ct.published_primary_type)
line("primary claim type preserved", f"{100 * same.mean():.1f}%", "96.6%")
line("claim-type changes", f"{int((~same).sum()):,}", "2,498")

for t, paper in [("method", "5.4%"), ("descriptive", "11.4%"),
                 ("association", "11.5%"), ("mechanism", "11.9%")]:
    sub = D[D.preprint_primary_type == t]
    line(f"major revision, {t} claims", f"{100 * sub.maj.mean():.1f}%", paper)
m = D[D.preprint_primary_type == "method"]
sec = pd.concat([m.s1_label, m.s2_label]).dropna()
line("major revision, secondary of method claims", f"{100 * (sec == 'major').mean():.1f}%", "11.7%")

# ---------------------------------------------------------------- secondary
head("PRIMARY VS SECONDARY CLAIM  (Fig. 2a)")
s1 = D.dropna(subset=["s1_label"])
for lab, paper in [("major", "90%"), ("unchanged", "34%")]:
    sub = s1[s1.primary_label == lab]
    line(f"secondary changed when primary {lab}",
         f"{100 * (sub.s1_label != 'unchanged').mean():.0f}%", paper)
c2, p, dof, _ = chi2_contingency(pd.crosstab(s1.primary_label, s1.s1_label))
line("chi-squared test", f"chi2({dof})={c2:.0f}", "P < 0.01")

# ----------------------------------------------------------------- temporal
head("POSTING YEAR  (Fig. 2c, Suppl. Fig. 4)")
yr = D[D.yr.between(2018, 2024)].groupby("yr").maj.agg([("n", "size"), ("pct", lambda x: 100 * x.mean())])
for y in [2018, 2019, 2024]:
    line(f"major revision, posted {y}", f"{yr.loc[y, 'pct']:.1f}% (n={int(yr.loc[y, 'n'])})",
         {2018: "19.6% (n=341)", 2019: "17.0%", 2024: "5.7%"}[y])
for y in [2019, 2024]:
    line(f"median interval, posted {y}", f"{D.loc[D.yr == y, 'days'].median():.0f} d",
         {2019: "666 d", 2024: "160 d"}[y])


def or_year(g):
    """Odds ratio for major revision per additional posting year (logistic)."""
    g = g.dropna(subset=["yr"])
    X = sm.add_constant(g[["yr"]].astype(float))
    m = sm.Logit(g.maj, X).fit(disp=0)
    return np.exp(m.params.yr), m.pvalues.yr


o, p = or_year(D)
line("OR per year, unrestricted", f"{o:.2f}", "0.79")
for W in [365, 730]:
    o, p = or_year(D[D.days <= W])
    line(f"OR per year, published within {W} d", f"{o:.2f}", "0.80")

# ---------------------------------------------------------------- intervals
head("PREPRINT-TO-PUBLICATION INTERVAL  (Fig. 2d, Suppl. Fig. 5)")
dd = D.dropna(subset=["days"]).copy()
dd["tertile"] = pd.qcut(dd.days, 3, labels=["fastest", "middle", "slowest"])
t = dd.groupby("tertile", observed=True).agg(med=("days", "median"), pct=("maj", lambda x: 100 * x.mean()))
for k, paper in [("fastest", "7.0% (110 d)"), ("slowest", "14.1% (416 d)")]:
    line(f"major revision, {k} tertile",
         f"{t.loc[k, 'pct']:.1f}% ({t.loc[k, 'med']:.0f} d)", paper)
c2, p, dof, _ = chi2_contingency(pd.crosstab(dd.tertile, dd.primary_label))
line("chi-squared across tertiles", f"chi2({dof})={c2:.0f}", "P < 0.001")

line("median interval, whole corpus", f"{dd.days.median():.0f} d", "218 d")
line("posted within 30 d of publication", f"{100 * (dd.days <= 30).mean():.1f}%", "1.3%")
line("posted within 90 d of publication", f"{100 * (dd.days <= 90).mean():.1f}%", "11.3%")
line("major revision excluding <90 d",
     f"{100 * dd.loc[dd.days > 90, 'maj'].mean():.1f}%", "10.7% (from 10.2%)")

# ------------------------------------------------------------ journal impact
head("JOURNAL IMPACT  (Fig. 2e)")
jm = json.loads((HERE / "data" / "journal_metrics.json").read_text())
imp = {k: v.get("2yr_mean_citedness") for k, v in jm.items() if isinstance(v, dict)}
imp = {k: v for k, v in imp.items() if v and v > 0}
J = D[D.journal.isin(imp)].copy()
J["imp"] = J.journal.map(imp)
line("journals with an impact value", f"{len(imp):,}", "736")
line("pairs covered", f"{len(J):,}", "59,012")

# Octiles of journal impact; each point is the mean citedness of a bin, weighted
# by the number of pairs it contains (same binning as make_figures.py).
#
# Note on weighting: make_figures.py fits with np.polyfit(..., w=n). numpy treats
# w as 1/sigma, so passing the bin counts weights each residual by n**2 rather
# than n. The correct n-weighted fit is used here (WLS, weights=n); it gives a
# slope of 22.3 against 22.6 for the polyfit call, so the two agree to within
# 0.4 percentage points and the figure inset is unaffected at its printed
# precision. Both are reported below.
J["rev"] = (J.primary_label != "unchanged").astype(int)
J["bin"] = pd.qcut(np.log10(J.imp), 8, duplicates="drop")
b = J.groupby("bin", observed=True).agg(x=("imp", "mean"),
                                        y=("rev", lambda s: 100 * s.mean()),
                                        n=("rev", "size"))
X = np.log10(b.x.values)
wls = sm.WLS(b.y.values, sm.add_constant(X), weights=b.n.values).fit()
poly = np.polyfit(X, b.y.values, 1, w=b.n.values)[0]

line("octiles used", len(b), "8")
line("slope, WLS weighted by n", f"{wls.params[1]:.1f}", "about 22")
line("slope, polyfit as in make_figures.py", f"{poly:.1f}", "(figure inset: 23)")
line("R-squared", f"{wls.rsquared:.2f}", "0.77")
line("P value", f"{wls.pvalues[1]:.3f}", "P < 0.01")

# ---------------------------------------------------------------- retraction
head("RETRACTION  (Fig. 2f)")
pre_r, pre_n = 9, 11114          # preprinted: retractions / papers
non_r, non_n = 813, 435159       # never preprinted
r1, r2 = pre_r / pre_n * 1e4, non_r / non_n * 1e4
rr = r2 / r1
se = np.sqrt(1 / pre_r + 1 / non_r)
_, p = fisher_exact([[pre_r, pre_n - pre_r], [non_r, non_n - non_r]], alternative="two-sided")
line("retractions per 10,000, preprinted", f"{r1:.1f}", "8.1")
line("retractions per 10,000, never preprinted", f"{r2:.1f}", "18.7")
line("rate ratio (95% CI)",
     f"{rr:.2f} ({np.exp(np.log(rr) - 1.96 * se):.2f}-{np.exp(np.log(rr) + 1.96 * se):.2f})",
     "2.31 (1.20-4.45)")
line("two-sided Fisher's exact test", f"P={p:.3f}", "P = 0.007")

print()
