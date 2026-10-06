# Stage 2B — Baseline signal evaluation: approved development specification

2026-10-06, RL-052–RL-053. Stage 2A and the frozen Stage 1 target remain unchanged.
The scope/inference proposal was approved before results (RL-053). Development
evaluation is now complete (RL-055); see docs/stage2b_completion.md.

## Approved temporal scope (RL-053)

Development/evaluation signal dates: 1993-01-04 through 2019-12-31.
Untouched final holdout signal dates: 2020-01-02 through 2025-12-31.
Assignment is signal-date only. Cross-boundary development holdings remain
unaltered development observations. No holdout signal performance is read,
computed or reported; no holdout-driven design/tuning/selection.
IC decay is explicitly deferred; only frozen five-day targets are authorized.

## Primary metric and sample

For each approved signal date and each of the eight fixed feature orientations,
compute Pearson correlation of average tied ranks of the Stage 2A standardized
feature and frozen numeric target: Spearman Rank IC. Primary input is the stored
z-score, including the existing clipping ties; do not rerun preprocessing on the
labeled subset. Raw-feature Rank IC may be a prespecified sensitivity only, never
a reason to replace the primary input after seeing significance.

Every finite numeric label permitted by the frozen policy is eligible for the
pairwise evaluation, including measurable cash-only delistings. Require finite
feature/target pairs and at least 30 pairs for a dated IC. A constant rank vector
has undefined IC with an explicit reason, not IC=0. Keep original keys and all
statuses in an evaluation-coverage ledger; record missing feature, missing label,
insufficient cross-section and boundary exclusions separately. No additional
future eligibility, event/outcome filtering, imputation or sign flipping.

Date ICs receive equal weight. Report mean, median, sample SD, positive frequency
(IC>0 / valid IC dates), date counts and pair counts. No portfolio construction,
Sharpe, costs, learned weights, feature pruning or model fitting.

## Overlap inference specified before results

Five-day holding windows overlap for signal separations 1–4 trading days. Approved
primary inference: intercept-only mean IC with Newey–West/Bartlett HAC, lag L=4,
95% normal-approximation confidence interval. Fix lag from the horizon, never
from significance. Also report a fixed L=20 sensitivity to broader monthly serial
dependence; the shorter lag addresses mechanical overlap, not every possible
source of persistence. Do not select the stronger t-statistic or claim fixed-lag
HAC proves stationarity or eliminates arbitrary long-memory uncertainty.

Let M be valid date ICs, mu their mean, and u_t=IC_t-mu on the original market-date
index. Calendar gaps remain gaps; never compress missing IC dates into adjacent
observations. With S_h the sum of u_t*u_(t-h) over valid calendar pairs, use

```
variance(mu) = [S_0 + 2*sum_(h=1..L)(1-h/(L+1))*S_h] / M^2
```

Use the stated intercept finite-sample factor M/(M-1) when M>1. Missing dates
contribute no score/covariance term, not an observed zero IC. For complete regular
series, validate against installed statsmodels cov_hac_simple with explicit
Bartlett weights/use_correction; local source documents the kernel and assumes
consecutive equally spaced periods. Nonpositive/degenerate variance is flagged.

Non-overlapping robustness uses every fifth global market date. Anchor phase zero
to the first authorized evaluation date, before results; retain the other four
phases as separately reported fixed sensitivities. No best-phase selection.
Adjacent sampled holding windows abut at an open but do not share a holding
interval. Residual signal persistence may remain: use fixed lag 4 sampled periods
(20 trading days) for those mean-IC intervals, not an IID t-test. Record phases,
calendar positions and undefined/missing observations explicitly.

## Temporal discipline

Fixed features have no fitted parameters or training step in Stage 2B. Evaluate
chronologically only on the authorized period; retain annual/block diagnostics.
That is not a substitute for a later dated walk-forward model-selection protocol.
Preserve the untouched holdout; development horizon-straddling labels remain development by approved signal-date assignment. No random split, pooled normalization, future-dependent
preprocessing, orientation/window tuning or retrospective period selection.

## Quantiles, stability and redundancy

Use five same-date buckets from average feature ranks on numeric-label/finite-
feature pairs; percentile=(average_rank-0.5)/n. Assign floor(5*percentile)+1,
keeping ties together. Unequal/empty buckets are explicit; never break feature
ties with target values. Report dated bucket counts and mean/median targets,
equal-date bucket summaries, annual summaries and Q5-minus-Q1 target spread.
This is a conditional cross-sectional target contrast, not a tradable portfolio
return. Use the same prespecified horizon HAC for spread inference if reported.
Assess ordered bucket curves without changing sign or choosing buckets/results.

Recompute feature-correlation evidence on development eligible keys only, and
same-scope feature-pair/IC-pair correlations with date/pair counts. IC correlations
use common valid dates and are descriptive; preserve weak, negative and redundant
signals without deleting/reweighting any feature. Confidence intervals are nominal
exploratory summaries across eight fixed signals, not familywise confirmatory
claims or a feature-selection rule.

## Coverage and selection evidence

Preflight verifies 6,699,101 original keys and 6,676,750 numeric labels; 22,351
missing labels remain explicit. Potential finite-z/numeric-label pair counts
range 6,613,358 (momentum) to 6,676,084 (intraday), before any temporal scope or
minimum-cross-section exclusions. These are source-coverage counts, not evaluated
sample sizes. Report both original-eligible and numeric-label denominators.

Missingness is structured: intraday availability is 99.990% in numeric-label
observations but 28.660% in missing-entry observations; gap availability in the
latter group is 28.489%. Momentum labeled coverage in 1993 is 80.468% due to
warm-up/history. These associations do not estimate missing returns or prove a
particular IC bias; they preclude a missing-at-random claim. Primary eventual
results are conditional on measurability/feature availability. Keep the frozen
6,069 unresolved valid-entry paths for later bounds/sensitivity work; no invented
returns, zero/-100% assumption or retrospective universe repair.

## Planned outputs and stopping point

Reusable evaluation/inference/quantile logic under src/evaluation; entry scripts
under scripts; private joined/daily caches under data/interim/stage2b. Tests for
average ties, undefined constant IC, numeric cash delistings, duplicates, calendar
HAC gaps, fixed phases, label maturity/boundaries and frozen input isolation.

Tables under results/tables/stage2b: daily_ic, ic_summary, annual_ic,
nonoverlapping_comparison, coverage_by_year/status, quantile_daily/summary,
feature_correlation, ic_correlation, inference_QA. Figures under
results/figures/stage2b: IC series/distributions, phase comparison, feature and IC
correlation heatmaps, quantile curves. Do not synthesize figures before authorized
performance computation. The three current preflight tables are reproducible via
scripts/28_qa_stage2b_sources.py and contain no target-return statistic.

Temporal-scope and horizon gates resolved in RL-053. Execute development-only five-day evaluation; stop at a material gate or completion before ML/portfolios. No source download needed.
