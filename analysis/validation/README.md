# Validation

The label scheme was validated on a stratified subsample of 550 preprint-publication
pairs. Each pair was labelled independently by four raters (H.Y., W.A., P.M.F. and
R.R.) using the v7.1 codebook, blind to the model output, and by Claude Sonnet 4.6.

For content change, the rater consensus is the mean ordinal rating of the four raters
(unchanged = 0, minor = 1, major = 2), binned at 0.5 and 1.5, with exact ties assigned
to the more severe category. For hedging shift, the consensus is the majority vote;
pairs whose primary claim was replaced outright are excluded, leaving 514 assessable
pairs, of which 470 have a rater majority.

This directory contains the aggregate contingency tables. Quadratic-weighted Cohen's
kappa, Krippendorff's alpha and Gwet's AC1 are functions of these tables, so every
reliability value reported in the paper is recomputed from them directly. Individual
rater labels are not included.

## Files

    content_model_vs_consensus.csv   3x3 counts, model label vs rater consensus (n = 550)
    content_rater_coincidence.csv    Krippendorff coincidence matrix across the 4 raters
    content_pairwise_kappa.csv       quadratic-weighted kappa for all 10 comparisons
                                     (6 rater-rater, 4 model-rater)
    content_calibration.csv          model major-revision rate by the number of raters
                                     (0 to 4) who called the pair major
    hedging_model_vs_consensus.csv   3x3 counts, model vs rater consensus (n = 470)
    hedging_direction_by_rater.csv   more-cautious and more-confident counts for each
                                     rater, the four raters pooled, and the model
    reliability_from_tables.py       recomputes all reported values from the tables above

## Reproduce

    pip install -r ../requirements.txt
    python reliability_from_tables.py

The script prints each value next to the corresponding value in the manuscript.
