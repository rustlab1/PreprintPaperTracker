#!/usr/bin/env python3
"""
statistics.py
-------------
Reproduces the statistics reported in the paper from data/full_corpus_labels.csv
and data/journal_metrics.json. Each value is printed next to the value given in
the manuscript.

The analyses added during revision live in revision/. Those that need inputs
beyond full_corpus_labels.csv (the retraction cohort, the blind extraction
sample) are documented in revision/README.md; this script reads their result
tables where it reports their values.

    python statistics.py

Requires: numpy, pandas, scipy, statsmodels.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import binomtest, chi2, chi2_contingency

HERE = Path(__file__).parent
D = pd.read_csv(HERE / "data" / "full_corpus_labels.csv")
D["days"] = pd.to_numeric(D["days_to_publication"], errors="coerce")
D["posted"] = pd.to_datetime(D["preprint_date"], errors="coerce")
D["yr"] = D["posted"].dt.year
D["maj"] = (D["primary_label"] == "major").astype(int)

# Journal and category strings are case-inconsistent in the bioRxiv metadata
# (e.g. "Bioinformatics" and "bioinformatics"). Normalise before any grouping.
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

# Claim-type transitions are only interpretable when the same claim is present
# on both sides, so the revised analysis excludes pairs whose primary claim was
# replaced, added or removed, and pairs without a valid type on both sides.
# Replacement is not a column here; it is reconstructed from the missing hedging
# label, which the codebook assigns to exactly those pairs. That reconstruction
# gives a denominator of 70,974 against the 71,055 reported in the paper, an
# 81-pair difference; the transition count and the preserved percentage are
# unaffected.
VALID_TYPES = {"mechanism", "association", "descriptive",
               "method", "therapeutic", "null_result"}
typed = (D.preprint_primary_type.isin(VALID_TYPES)
         & D.published_primary_type.isin(VALID_TYPES))
ct = D[typed & D.primary_hedging.notna()]
same = (ct.preprint_primary_type == ct.published_primary_type)
line("pairs in the restricted analysis", f"{len(ct):,}", "71,055")
line("primary claim type preserved", f"{100 * same.mean():.1f}%", "97.7%")
line("claim-type changes", f"{int((~same).sum()):,}", "1,605")
line("claim-type changes, share", f"{100 * (~same).mean():.1f}%", "2.3%")

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

# Journal-level grouped binomial model. Mean citedness enters continuously and
# its functional form is chosen by fractional polynomials over the standard
# power set with degree capped at FP2. The selected model has powers
# (-0.5, 0). This replaces the octile-binned weighted linear fit reported in
# the original submission.
J["rev"] = (J.primary_label != "unchanged").astype(int)
g = (J.groupby("journal")
       .agg(n=("rev", "size"), k=("rev", "sum"), imp=("imp", "first"))
       .reset_index())


def fp_design(v, powers):
    v = np.asarray(v, dtype=float)
    f = lambda p: np.log(v) if p == 0 else v ** p          # noqa: E731
    return sm.add_constant(np.column_stack([f(powers[0]), f(powers[1])]),
                           has_constant="add")


resp = np.column_stack([g.k, g.n - g.k])
fp2 = sm.GLM(resp, fp_design(g.imp, (-0.5, 0)), family=sm.families.Binomial()).fit()
lin = sm.GLM(resp, sm.add_constant(g.imp.values), family=sm.families.Binomial()).fit()

pr = lambda v: fp2.predict(fp_design([v], (-0.5, 0)))[0]   # noqa: E731
odds = lambda q: q / (1 - q)                               # noqa: E731
gstat = lin.deviance - fp2.deviance

line("journals in the model", f"{len(g):,}", "736")
line("selected FP2 powers", "(-0.5, 0)", "(-0.5, 0)")
line("revision probability at citedness 2", f"{pr(2) * 100:.1f}%", "53.8%")
line("revision probability at citedness 10", f"{pr(10) * 100:.1f}%", "67.5%")
line("odds ratio, citedness 10 vs 2", f"{odds(pr(10)) / odds(pr(2)):.2f}", "1.78")
line("FP2 vs linear", f"chi2={gstat:.1f}, P={chi2.sf(gstat, 1):.3g}", "P < 0.001")

# ---------------------------------------------------------------- retraction
# The crude rate ratio reported in the original submission was replaced during
# revision by a time-to-event analysis on an article-level cohort. That cohort
# is not derived from full_corpus_labels.csv, so the values below are read from
# the tables in revision/data/; revision/scripts/retraction_stratified_firth.R
# regenerates them from revision/data/retraction_cohort.csv.gz.
head("RETRACTION  (Fig. 2f, Suppl. Fig. 8)")
arms = pd.read_csv(HERE / "revision" / "data" / "retraction_arm_summary.csv")
cox = pd.read_csv(HERE / "revision" / "data" / "retraction_cox_results.csv")
a = arms[arms.window == "2021-2024"].set_index("arm")

line("articles, bioRxiv-linked", f"{a.loc['bioRxiv-linked', 'n']:,.0f}", "19,692")
line("articles, not linked", f"{a.loc['not linked', 'n']:,.0f}", "380,236")
line("retractions, bioRxiv-linked", f"{a.loc['bioRxiv-linked', 'events']:,.0f}", "6")
line("retractions, not linked", f"{a.loc['not linked', 'events']:,.0f}", "715")
line("rate per 10,000 article-years, linked",
     f"{a.loc['bioRxiv-linked', 'rate_per_10k_yr']:.2f}", "0.79")
line("rate per 10,000 article-years, not linked",
     f"{a.loc['not linked', 'rate_per_10k_yr']:.2f}", "5.20")

paper = {"Journal- and year-stratified": "0.22 (0.10-0.50)",
         "Firth-penalized, journal- and year-stratified": "0.24 (0.10-0.48)"}
for _, r in cox.iterrows():
    line(f"HR, {r.model}", f"{r.hr:.2f} ({r.lo:.2f}-{r.hi:.2f})",
         paper.get(r.model, ""))

print()
