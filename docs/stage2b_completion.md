# Stage 2B development evaluation — completed (RL-055)

Stage 2B development evaluation is CLOSED. The 2020–2025 final holdout remains
untouched for predictive evaluation. No feature selection, model fitting,
portfolio construction, costs, Sharpe or new target horizon has begun.

## Frozen scope and methodology

Signal-date development interval: 1993-01-04–2019-12-31; actual eligible dates
start 1993-01-22. Holdout signal dates: 2020-01-02–2025-12-31. Both inputs are
filtered before evaluation materialization; no holdout signal statistic is
computed or used. Retain all 6,488 development signals with exit dates in 2020,
including 6,482 numeric labels, without changing their frozen holding windows.

Primary metric: average-tie Spearman of stored Stage 2A z features and frozen
five-day next-open targets, by date, at least 30 finite pairs, equal date weight.
Stored clipping/standardization is unchanged and never repeated on a label-
available subset. Fixed feature signs are unchanged; negative results remain
negative. Undefined cross-sections remain missing with reasons.

Primary mean inference: Bartlett/Newey–West lag4, M/(M−1) correction, nominal
normal 95% intervals. Fixed lag20 sensitivity shown for all features, without
choosing significance. Missing IC dates retain original market positions.
Non-overlapping diagnostics show all five phases anchored to 1993-01-04, with
sampled lag4 (20 trading days) inference; no best phase selection. These nominal
exploratory intervals do not establish stationarity, eliminate long-memory
uncertainty or adjust for eight simultaneous signal hypotheses. No fitted model
or random split; later fitting requires a separate walk-forward protocol.
IC decay is deferred.

## Coverage and selection

4,816,452 unique original development keys; 4,804,070 numeric labels
(99.742923%); 12,382 missing labels remain explicit. Numeric labels include
2,549 cash-only delistings and 4,801,521 ordinary/event-adjusted observations.
Missing labels: 7,232 missing entry; 3,534 unresolved exit wealth; 1,616 other
unresolved corporate action. No administrative right-censoring in development.
The 5,150 valid-entry unresolved paths remain for later sensitivity/bounds
analysis; no zero, −100%, interpolation or guessed label is used.

Evaluated finite feature/label pair counts range 4,753,755 (momentum) to
4,803,412 (intraday). They equal the sums of dated IC/quantile membership:
no finite pair is lost to a minimum-size/constant gate in this dataset.
Coverage against original eligible keys ranges 98.698%–99.729%; coverage among
numeric labels ranges 98.953%–99.986%. Dates without valid ICs are explicit, never observed zero ICs. Two development
signal dates have no numeric labels: 1994-10-28 (166 missing-exit labels) and
1994-11-04 (163 missing-entry labels). Both depend on the already unavailable
1994-11-07 open. Cached daily data show 0/167 eligible positive opens that day,
with 167/167 positive closes. Gap/intraday features on 1994-11-07 are also
missing by their locked input rules. No physical cause or substitute opening
fill is inferred. These 329 missing labels are already in the frozen status
counts; explicit dated attribution supplements early-history/calendar gaps.
Original calendar positions remain intact for HAC and sampling phases.

Missingness is structured: intraday is available for 1,815/7,232 (25.097%)
missing-entry signals, versus 99.986% of numeric-label signals. Momentum's 1993
numeric-label coverage is 80.468%, from required history and input integrity;
2019 coverage is 99.221%. Gap labeled coverage is 99.028%; its event-admissibility
restrictions remain unchanged. No newly unexplained attrition/key/PIT pattern
was discovered. ICs and quantile means describe measurable feature/label pairs,
not guaranteed unbiased estimates for all eligible signals. Missing outcomes
are not assumed random; this known limitation is preserved rather than repaired
using outcomes or future eligibility.

## Primary results, including weak and negative signals

| Fixed feature | Mean IC | HAC4 t | Nominal HAC4 95% CI | HAC20 t | Labeled feature coverage |
|---|---:|---:|---|---:|---:|
| reversal_5 | 0.029921 | 10.632 | [0.024405, 0.035436] | 9.665 | 99.954% |
| momentum_60_skip5 | 0.004770 | 1.282 | [-0.002522, 0.012062] | 1.152 | 98.953% |
| volatility_20 | -0.014487 | -2.798 | [-0.024633, -0.004340] | -2.605 | 99.701% |
| turnover_20 | -0.009754 | -2.157 | [-0.018619, -0.000890] | -1.959 | 99.986% |
| dollar_liquidity_20 | 0.000629 | 0.315 | [-0.003286, 0.004544] | 0.270 | 99.986% |
| volume_shock_20 | 0.000337 | 0.258 | [-0.002217, 0.002891] | 0.233 | 99.965% |
| gap_1 | -0.005651 | -3.656 | [-0.008680, -0.002622] | -3.722 | 99.028% |
| intraday_1 | -0.020688 | -12.147 | [-0.024026, -0.017350] | -11.413 | 99.986% |

Reversal mean IC is positive in all five fixed phases (0.027223–0.034243),
with each sampled CI above zero; annual means are positive in 23/27 years.
Intraday mean IC is negative in all phases (−0.024225 to −0.016464), each
sampled CI below zero, and negative in 26/27 annual blocks. Do not flip its sign
or select features in this stage. Momentum is weak under both lag specifications,
with phase intervals crossing zero; dollar liquidity and volume shock are weak
and phase signs vary. Gap phase means are all negative but some intervals cross
zero. Volatility and turnover phase means are negative, with substantial
annual variation. Turnover's lag20 interval narrowly includes zero: both lags
are retained. These are development observations, not final-holdout findings.

## Quantiles and redundancy

Average-rank buckets preserve ties without target-based tie breaking. No empty
bucket/date occurred; counts reconcile to all valid IC pairs. Reversal's five
bucket means strictly increase; Q5−Q1 mean target contrast is +0.004031
(+40.31 basis points over five days). Intraday's means strictly decrease;
contrast is −0.003037 (−30.37 basis points). These are equal-date conditional
target contrasts, not implemented portfolio returns or net alpha.
Momentum has one adjacent reversal; volatility, turnover, gap and volume shock
have non-monotone curves. Dollar liquidity mostly declines despite its weak
positive mean IC, illustrating that the diagnostics are distinct; no rule
changes or result suppression follow.

Development-only mean daily eligible feature correlation is 0.6747 for
volatility/turnover; their daily IC correlation is 0.9482. Reversal/intraday
feature correlation is −0.3693 and IC correlation −0.3899. All features remain,
with no learned combination, pruning or reweighting. Feature correlations use
all eligible development features without conditioning on labels; IC
correlations use common valid development dates.

## Reproduction and QA

Entry point: `scripts/29_evaluate_stage2b_baselines.py`.
Reusable logic: `src/evaluation/{baseline,statistics,audit}.py`.
Private fingerprinted/checksummed IC and quintile cache plus manifest:
`data/interim/stage2b/`. All eight aggregate batches were checksum-verified
and reused in the final run. Input feature hashes verified across 32 partitions.

QA: exact source keys/status/numeric reconciliation; no duplicates, key-set
mismatch or future maximum input dates; full 6,799-date development market
calendar verified against the independent Stage 1 audit (one-based versus
zero-based convention corrected); every pair/quintile count reconciles;
24 fixed-date independent SciPy IC checks maximum error 2.50e−16; synthetic
HAC agrees with statsmodels and preserves calendar gaps; tie, constants,
missing pairs, cash delistings and cross-split/holdout isolation tests pass.
Full repository suite: 78 tests passed. A fragile exact-floating-point equality
test was corrected to 1e−12 tolerance after 1.0000000000000002 versus 1.0;
no sample or definition changed. Exact constant mean-inference series now
explicitly return degenerate variance rather than round-off significance.

Tables: `results/tables/stage2b/` includes daily Rank IC, IC/annual summaries,
coverage by year/status/reason, overlap comparisons/all phases, annual quintiles,
monotonicity, bucket and independent QA, feature/IC correlations and spreads.
Large reproducible daily quintile and spread CSVs remain local and gitignored;
compact aggregate tables, dated IC series and figures contain no security-level
licensed extracts. Existing full-period RL-052 preflight tables remain historic
availability QA only; they were not rerun or used as development performance.

Six figures under `results/figures/stage2b/`: Rank IC monthly-display series,
daily IC distributions, fixed-phase comparison, quintile monotonicity and two
correlation heatmaps. Figures were visually checked; every baseline is shown.
No raw scan, WRDS login/extraction or new data source.

## Remaining limitations and next review

Known conditional-label/feature selection and snapshot-vintage limitations
remain. No claim of missing-at-random outcomes or guaranteed deployable/net
alpha. Frozen target and feature contracts unchanged. Research lead should
review these development results and authorize the next dated walk-forward
model/evaluation protocol. Do not start feature selection, ML, portfolios,
IC decay or final-holdout evaluation automatically.
