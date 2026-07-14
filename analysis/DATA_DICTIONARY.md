# Data dictionary

`data/full_corpus_labels.csv` has one row per matched preprint-publication pair
(72,644 rows). Labels follow codebook v7.1 (`codebook/prompt_v7.1.md`).

| Column | Description |
|---|---|
| biorxiv_doi | DOI of the bioRxiv preprint (first posted version). |
| preprint_category | bioRxiv subject category. |
| preprint_date | Date the preprint was first posted (YYYY-MM-DD). |
| published_date | Date of the peer-reviewed publication (YYYY-MM-DD). |
| days_to_publication | Days from preprint posting to publication. |
| published_journal | Journal of the peer-reviewed publication. |
| jaccard_similarity | Word-level Jaccard similarity between the preprint and published abstract (0 to 1). |
| preprint_word_count | Word count of the preprint abstract. |
| published_word_count | Word count of the published abstract. |
| year | Year of preprint posting. |
| primary_label | Content change of the primary claim: unchanged, minor, major. |
| primary_hedging | Hedging shift of the primary claim: unchanged, weakened (more cautious), strengthened (more confident), or NA. |
| preprint_primary_type | Claim type of the primary claim in the preprint. Six main types: mechanism, association, descriptive, method, therapeutic, null_result. A small residual (0.5% of pairs) carries other codebook categories: applied_implication, predictive, moderator, causal-necessity. |
| published_primary_type | Claim type of the primary claim in the publication. |
| s1_label | Content change of the first secondary claim. |
| s1_hedging | Hedging shift of the first secondary claim. |
| s2_label | Content change of the second secondary claim. |
| s2_hedging | Hedging shift of the second secondary claim. |
| source | Extraction batch identifier. |

Journal impact used in Figure 2e is the OpenAlex 2-year mean citedness, mapped
from `published_journal` through `data/journal_metrics.json`.
