# Prompt v7.1 - locked codebook (audit fixes applied)

Builds on v7. Fixes the codebook self-audit issues:
1. `minor` definition loosened to match observed model behaviour (and reviewer intuition).
2. Decision rule made internally consistent (no more "unchanged + hedging shift" loophole).
3. Magnitude rule given an explicit baseline.
4. Effect-type lexicon extended.
5. Trivial-paraphrase threshold operationalised.

**Backward compatibility note.** Existing v7 Sonnet labels remain valid under v7.1. The rule changes mostly clarify intent rather than relabel categories. The single inconsistent v7 pair (X0770) will be corrected manually.

---

## System prompt

You are a scientific abstract annotator. You follow a strict codebook. You never speculate beyond what the abstracts say. You output only valid JSON matching the requested schema.

## User prompt template

You will classify how the PRIMARY claim and the top TWO SECONDARY claims of a scientific paper changed from its bioRxiv preprint abstract to its final published journal abstract.

---

## Part 1. Claim extraction

**Primary claim.** The single statement most directly answering the paper's central question, foregrounded as the take-home message. Assertive, declarative, study-own, study-level. Not background, methods, aims, or tool announcements. When multiple candidates remain, prefer final 1-3 sentences, cue-phrase openers (*we show, we demonstrate, we find, we conclude, these results establish, collectively*), title alignment, broadest scope. Exactly one primary claim per abstract. **Tie-breaker:** if two candidates remain after the heuristics, pick the statement with the highest noun-phrase overlap with the title.

**Secondary claims.** Additional distinct study-own declarative findings. Extract top 2 ranked by: (1) mechanism > non-mechanism, (2) moderator/scope > applied implication, (3) order of appearance otherwise. **Final tie-breaker for equal-weight candidates:** sentence-length proximity to the primary claim's length.

---

## Part 2. Claim type (decision tree, apply in order)

Classify `preprint_primary_type` and `published_primary_type` independently. First matching rule wins:

1. Primary claim foregrounded as a null/absence/non-significant finding -> `null_result`
2. Primary claim is a specific treatment effect, clinical intervention outcome, or drug-target validation in patients/disease model -> `therapeutic`
3. Primary contribution is a new method, tool, algorithm, pipeline, or benchmark (headline would remain substantive without the biological content) -> `method`
4. Primary claim asserts causation/regulation/necessity/sufficiency with mechanistic "how" -> `mechanism`
5. Primary claim reports a statistical/empirical linkage without asserting causality -> `association`
6. Otherwise (characterises, catalogues, measures) -> `descriptive`

**Stability rule.** Apply the tree independently to each version. Flag a type transition ONLY when the decision tree crosses a boundary, NOT when wording merely shifts within a type's verb family.

---

## Part 3. Secondary claim type

Choose exactly one per secondary, first-fit order: `negative_result`, `quantitative_detail`, `moderator`, `mechanism`, `secondary_outcome`, `applied_implication`. Generic "these findings have broad implications" does NOT qualify. If both `mechanism` and `moderator` fit, prefer `mechanism`.

---

## Part 4. Change label (primary, S1, S2)

Three levels, applied to each claim independently:

- `unchanged` - same assertion, **identical wording or trivial paraphrase only**. Trivial paraphrase = whole-claim Jaccard similarity ≥ 0.90 with no change in entity, direction, scope, magnitude, effect-type class, OR hedging tier.
- `minor` - **any non-substantive revision**. Includes (a) wording changes that do not change entity/direction/scope/magnitude/effect-type, with or without a hedging shift; (b) hedging tier shift on otherwise identical content. NOT major.
- `major` - at least one of: direction flipped, scope changed, magnitude changed, effect-type class changed, primary claim replaced.

**Decision rule (this is the only authority - apply in this order):**
1. If any `major` condition holds -> `major`.
2. Else if the claim is an exact match or a trivial paraphrase (Jaccard ≥ 0.90, no hedging tier shift) -> `unchanged`.
3. Else -> `minor`.

**Internally consistent corollary:** if hedging tier shifts at all, the claim CANNOT be `unchanged`. It is at minimum `minor`.

### Scope rule
Scope change (= major) requires a change in entity, population, species, cell type, tissue, system, or experimental setting. Rhetorical trims (priority phrases *first, novel*, implication phrases, elaboration phrases, GitHub/data-availability notes, Author Summary blocks not present in the published version) are NOT scope changes.

### Direction flip rule
Direction = sign of the primary relationship reversed between versions.
- Correlation positive ↔ negative -> flip.
- Rank A > B ↔ B > A -> flip.
- Effect *increases* X ↔ *decreases* X -> flip.
- Effect present ↔ absent -> NOT a flip (this is a null-result transition; still `major`).
- Scope narrowing with unchanged direction -> NOT a flip.

### Magnitude change rule

Compare point estimates of the primary quantitative finding. Apply in order:

1. If the same effect is not quantified in both versions, magnitude change does not apply.
2. **Relative change rule:** `|published - preprint| / max(|published|, |preprint|) >= 0.20` -> major. Example: 10 -> 13 yields 3/13 ≈ 0.23 -> major. 10 -> 11 yields 1/11 ≈ 0.09 -> not major.
3. For log-scale quantities, ≥1 order of magnitude OR ≥2x fold-change difference = major.
4. p-values are NOT magnitudes. p<0.001 -> p<0.05 is at most a hedging shift.

### Effect-type classes (extended lexicon)

Ordered weak -> strong:

1. **Associative:** correlates with, is associated with, is linked to, is influenced by, tracks, co-varies with, is correlated with.
2. **Predictive:** predicts, forecasts, is expected to, suggesting X will.
3. **Explanatory:** explains, accounts for, underlies, is the basis for, mediates the link between.
4. **Causal-regulation:** regulates, controls, promotes, inhibits, induces, activates, modulates, governs, coordinates, orchestrates, perturbs, reshapes, rewires, couples to, mediates.
5. **Causal-necessity:** causes, requires, is required for, is necessary for, is sufficient for, drives, is needed for.

Shift BETWEEN classes -> major (effect-type change). Shift within a class is not. **Default rule for verbs not listed:** classify by the most similar listed verb; if uncertain, default to causal-regulation.

---

## Part 5. Hedging dimension (4-level, INDEPENDENT of change label)

Hedging captures certainty shifts and is assessed on TWO axes:

**Axis A - modal/verb tier:**
- High: demonstrates, shows, establishes, proves, reveals, causes, is required for, is necessary for, is sufficient for.
- Moderate: suggests, indicates, supports, is consistent with, provides evidence that, implies.
- Low: may, might, could, can, potentially, possibly, appears to, seems to, we speculate, we hypothesize.

**Axis B - effect-type class rank** (1-5 from the weak->strong order above).

**Primary verb selection rule.** When a claim has multiple verbs:

1. In the form *"[cue-phrase] that X [verb] Y"* (e.g., *"we demonstrate that X regulates Y"*), the primary verb is the INNER verb (*regulates*), not the cue-phrase verb.
2. If two parallel clauses are joined by "and", pick the verb attached to the broader/more-foregrounded assertion. When unsure, pick the verb with LOWER certainty.
3. Nominalisations and passive constructions count as the active verb (*"was found to regulate"* = *regulates*).

**Decision tree for hedging label:**
1. No comparable primary claim (claim replaced/added/removed entirely) -> `NA`.
2. Else compute Axis A tier shift AND Axis B rank shift.
3. Either axis moved UP and the other did not move DOWN -> `strengthened`.
4. Either axis moved DOWN and the other did not move UP -> `weakened`.
5. Both axes unchanged -> `unchanged`.
6. Axes in conflict: larger move wins; tie -> `unchanged`.

Within-tier swaps (*may* ↔ *might*, *shows* ↔ *demonstrates*) and within-class swaps (*regulates* ↔ *controls*) do NOT count as movement.

**Apply to every claim regardless of change label, but with the corollary from Part 4:**
- `unchanged` claim: hedging MUST be `unchanged` or `NA`. It cannot be `strengthened` or `weakened` (if hedging shifted, the claim is at minimum `minor`).
- `minor` claim: hedging may be `strengthened`, `weakened`, OR `unchanged` (since `minor` now also covers wording-only changes without hedging shift).
- `major` claim: hedging is independently assessed. Usually `unchanged`, `strengthened`, or `weakened`. Only `NA` if the primary claim was entirely replaced/added/removed.

---

## Part 6. Missing secondary claims

If a version has no secondary claim for a slot, set that slot's verbatim field to `"NA"` and all other slot fields to `"NA"`. If one version has a secondary that the other does not, slot label = `major` and slot hedging = `NA`.

---

## Input

PREPRINT ABSTRACT:
{{preprint_abstract}}

PUBLISHED ABSTRACT:
{{published_abstract}}

---

## Output schema (exact - return only valid JSON, no markdown fences, no commentary)

```json
{
  "pair_id": "{{pair_id}}",
  "preprint_primary": "<verbatim from preprint>",
  "preprint_primary_type": "mechanism|association|method|descriptive|therapeutic|null_result",
  "published_primary": "<verbatim from published>",
  "published_primary_type": "mechanism|association|method|descriptive|therapeutic|null_result",
  "primary_label": "unchanged|minor|major",
  "primary_hedging": "strengthened|weakened|unchanged|NA",

  "preprint_secondary_1": "<verbatim or NA>",
  "published_secondary_1": "<verbatim or NA>",
  "s1_type": "mechanism|moderator|secondary_outcome|quantitative_detail|applied_implication|negative_result|NA",
  "s1_label": "unchanged|minor|major|NA",
  "s1_hedging": "strengthened|weakened|unchanged|NA",

  "preprint_secondary_2": "<verbatim or NA>",
  "published_secondary_2": "<verbatim or NA>",
  "s2_type": "mechanism|moderator|secondary_outcome|quantitative_detail|applied_implication|negative_result|NA",
  "s2_label": "unchanged|minor|major|NA",
  "s2_hedging": "strengthened|weakened|unchanged|NA",

  "reasoning": "<one sentence per change label>",
  "model": "<claude-sonnet-4-6 | claude-opus-4-6 | claude-haiku-4-5 | other model id>"
}
```

---

## Changelog

- **v7.1** (2026-04-24): Loosened `minor` to include wording-only changes without hedging shift. Made `unchanged + hedging shift` formally impossible. Added Jaccard ≥ 0.90 trivial-paraphrase threshold. Added magnitude relative-change baseline. Extended effect-type lexicon to cover modulates/governs/coordinates/orchestrates/perturbs/reshapes/rewires/couples/mediates. Added title-overlap and sentence-length tie-breakers.
- **v7** (2026-04-23): Bundled v6 + claim type definitions + direction/magnitude/verb rules.
- **v6** (2026-04-23): Added 4-level hedging (strengthened/weakened/unchanged/NA), effect-type causal hierarchy as Axis B.
- **v5** (2026-04-23): Sharpening rule for verb-tier-only hedging lookup.
- **v4-v3-v2-v1**: Earlier drafts (see archive).
