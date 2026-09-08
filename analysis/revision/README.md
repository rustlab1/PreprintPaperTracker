# Revision analyses

Analyses added during peer review at Nature Human Behaviour. They supersede two
analyses in the original submission: the crude retraction rate ratio and the
weighted linear fit of revision against journal impact.

## Manuscript mapping

| Analysis | Figure | Files |
|---|---|---|
| Retraction cohort, Cox and stratified Firth | Fig. 2f, Suppl. Fig. 8 | `scripts/retraction_stratified_firth.R`, `data/retraction_*` |
| Calendar-time fixed-window sensitivity | Suppl. Fig. 5 | `scripts/calendar_fixed_window.R`, `data/fixed_window_*` |
| Interval, fractional polynomial | Suppl. Fig. 6 | `fp_interval.py` |
| Journal impact, fractional polynomial | Fig. 2e | `scripts/journal_impact_fp.R`, `data/journal_impact_*` |

`fp_interval.py` runs end to end from `../data/full_corpus_labels.csv` and
prints each value next to the number reported in the paper. The R scripts are
provenance copies of the scripts used to produce the published results and
retain their original absolute paths; the tables they generated are included in
`data/` so every reported value can be checked without re-running them.

## Retraction

An article-level cohort of Europe PMC records from the 47 journals with
unambiguous ISSN matches, published 2018 to 2024. Follow-up runs from journal
publication to retraction or the administrative censoring date of 19 August 2026,
the Retraction Watch snapshot. The primary analysis covers 2021 to 2024, when
both groups are represented (n = 399,928; 721 retractions).

    retraction_cohort.csv.gz      one row per article: journal, DOI, date, exposure,
                                  outcome, follow-up days, publication type
    retraction_cox_results.csv    hazard ratios for every specification in Suppl. Fig. 8a
    retraction_arm_summary.csv    events, person-time and rates by arm and window
    retraction_events.csv         the retracted articles
    retraction_km_curve.csv       cumulative incidence underlying Fig. 2f

Note on `retraction_cox_results.csv`: the `p_type` column records which test each
P value comes from. The Firth row is a penalised likelihood-ratio P value and the
others are Wald P values, so the column is not directly comparable across rows.

The Firth model is stratified by journal and publication year. Because the
`coxphf` package does not support `strata()`, `retraction_stratified_firth.R`
implements a one-parameter stratified penalised partial likelihood, validated
against `coxphf` without strata and against ordinary stratified Cox with Breslow
ties (agreement to within 1e-7 on the log hazard ratio). The stratified fit uses
187 journal-by-year strata, of which 50 contain both a retraction and a
bioRxiv-linked article; all 721 events are retained.

## Calendar time

Major-revision rate by posting year, restricted to pairs published within 365 or
730 days and to posting dates whose full publication window falls inside the
dataset's coverage (1 January 2021 to 28 February 2025).

    fixed_window_models.csv   odds ratio per posting year for each window
    fixed_window_rates.csv    yearly rates for each series in Suppl. Fig. 5b
    interval_summary.csv      median and IQR of the interval by posting year

## Fractional polynomials

Both analyses use the standard power set {-2, -1, -0.5, 0, 0.5, 1, 2, 3} with
degree capped at FP2. The interval model selects powers (1, 1); the journal
impact model selects powers (-0.5, 0).

    journal_impact_model_comparison.csv           deviance and AIC by candidate model
    journal_impact_predicted_probabilities.csv    fitted curve with confidence interval
    journal_impact_sensitivity.csv                sensitivity analyses
    journal_impact_journal_level_data.csv         revised and unchanged counts per journal

## Not included

Two analyses that validate the extraction step itself are not distributed here:
the blind independent extraction in a 500-pair sample (Supplementary Fig. 3a-b)
and the human claim-extraction comparison in 100 pairs (Supplementary Fig. 3c).
Both are reported in full in the paper. This follows the same line as
`../validation/`, which ships aggregate reliability tables for the labelling
scheme but no per-abstract model outputs or individual rater judgements.
