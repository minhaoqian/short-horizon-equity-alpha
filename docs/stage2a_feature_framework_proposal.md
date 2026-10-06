# Stage 2A — Approved feature framework

Date: 2026-10-06. Implemented/validated under RL-044 and RL-048–RL-050; see docs/stage2a_completion.md. Stage 1G contract remains unchanged. This proposal uses
interpretability, point-in-time timing and data integrity; no predictive evidence.

## Timing and admissible observations

Every feature has as-of date t and availability close t. Use a global market
calendar, never the next/previous available security row as a trading-day shift.
Historical input rows need not have been eligible: eligibility selects signal
keys at t, not the constituent historical observations. Retain all 6,699,101
keys, including observations without labels or with missing features.

Use an explicit allowlist of daily inputs. The target table supplies only
(permno,signal_date) to feature construction. Join label/status/outcome metadata
only after computing features; these fields cannot affect rolling windows,
cross-sectional samples, clipping or normalization. No label-availability mask.
No after-t event, security classification, price, settlement or successor value.
No full-history cumulative-factor level or backward-adjusted price is required.
A historical CRSP snapshot is not proof of revision-free historical vintages;
record that limitation and test economic date/interval availability explicitly.

Proposed admitted daily return r_s is CRSP DlyRet, checked against the validated
source identity (DlyPrc*DlyFacPrc + DlyNonOrdDivAmt + DlyOrdDivAmt)/DlyPrevPrc - 1.
Require finite return >= -1, positive actual current/previous close prices,
a single-market-period source interval, and the preceding global trading-date
price anchor. Do not divide a multi-period return across days. Exclude stored
delisting-return rows and nonordinary/received-asset or ambiguous event amounts
whose measurement by close s cannot be established. Ordinary fixed cash and
verified pure same-security splits are allowed; unresolved factor changes are
not. Event verification uses only dates/terms through s, never later settlement
values. Missing input days invalidate a strict return window; no bridging.
The admitted-return mask needs a small local field/event QA before implementation.

## Baseline definitions

Let W_L(t)={t-L+1,...,t} in market-date indices. Let P_s be a positive actual
closing price, V_s nonnegative DlyVol in shares, M_s=1000*DlyCap in dollars,
D_s=P_s*V_s, T_s=D_s/M_s. Validate price/volume units and flags; quote-only or
unverified price measurements do not become actual transaction measurements.
Zero reported volume is valid; missing volume is not zero. A liquidity window
has its full calendar span and at least 15 valid days out of 20; record n_valid.
Return windows require every specified observation. No annualization of volatility.

| Feature | Exact raw definition / window | Required CRSP fields | Missing behavior | Intuition / overlap |
|---|---|---|---|---|
| reversal_5 | -[product_{s in W_5(t)}(1+r_s)-1] | DlyRet, DlyRetDurFlg, DlyPrc, DlyPrevPrc, DlyFacPrc, ordinary/nonordinary amounts, return/price/delisting flags and source-date checks | Any of 5 inadmissible returns => missing | Recent reversal; overlaps gap/intraday and momentum |
| momentum_60_skip5 | product_{s=t-59}^{t-5}(1+r_s)-1; 55 daily returns within 60-date span, latest 5 excluded | Same return inputs | All 55 required; insufficient history/gap => missing | Medium-term continuation separated from recent reversal |
| volatility_20 | sqrt[sum_{s in W_20}(r_s-mean(r))^2/19] | Same return inputs | All 20 required; no replacement of -100% by finite log return | Realized risk; overlaps shock and liquidity |
| turnover_20 | log(1+mean_valid_{W_20}(T_s)) | DlyPrc, DlyVol, DlyCap, price/volume/cap flags | >=15 valid days, positive cap; report valid count | Trading intensity relative to total cap; proxy, not free-float turnover |
| dollar_liquidity_20 | log(1+mean_valid_{W_20}(D_s)/1 USD) | DlyPrc, DlyVol, measurement flags | >=15 valid days | Trading capacity; overlaps locked ADV filter, size and turnover |
| volume_shock_20 | log[(1+D_t/1 USD)/(1+mean_valid_{s=t-20}^{t-1}(D_s)/1 USD)] | DlyPrc, DlyVol, measurement flags | Valid current day and >=15 of previous 20; full 21-date span | Dollar-volume activity shock; avoids artificial raw-share-volume split shocks, also reflects price changes |
| gap_1 | Open_t/P_{t-1}-1 | DlyOpen, DlyPrc/PrevPrc, source dates/flags, DlyFacPrc, ordinary/nonordinary amounts | Positive actual opens/closes, adjacent market dates; baseline missing on split/distribution/ambiguous-event days | Overnight repricing; overlaps reversal; event-day decomposition deferred |
| intraday_1 | P_t/Open_t-1 | DlyOpen, DlyPrc, price flags | Positive actual same-day measurements; no overnight entitlement included | Session price move; overlaps reversal and gap |

All windows end by close t. Gap baseline requires an event-free interval
(F=1, ordinary/nonordinary amounts zero, no flagged ambiguous event). Do not
silently apply the event-free ratio on an ex-date. Intraday is a same-share-basis
price return, not a cash-inclusive close-to-close total return. On clean days,
(1+gap)*(1+intraday)=P_t/P_{t-1}; test this accounting identity. No forecast-sign
claim is implied by an economic interpretation.

## Cross-sectional preprocessing

For each feature independently, on each date t, use finite raw values from
all close-t eligible keys, including keys with subsequently missing targets.
No pooled full-sample moments or train/holdout-dependent transformation.

1. Keep raw units and data-quality/missingness reasons. Invalid values become
   missing before statistical clipping; do not disguise invalid fields as outliers.
2. Require at least 30 finite eligible observations for the date/feature.
3. Clip to same-date empirical 1st/99th percentiles, using linear/type-7 quantiles.
   Keep lower/upper cutoffs and fraction clipped. These thresholds are proposed
   for robustness to tails, not selected using outcomes.
4. Standardize clipped values: z=(x_clipped-mean_t)/sd_t, population sd (ddof=0).
   For an exactly constant observed cross-section, z=0 and flag degeneracy;
   for fewer than 30 observations, processed values are missing with a reason.
5. Preserve missing raw/processed values and distinct missingness reasons/masks.
   Do not forward-fill or back-fill. A later numeric model matrix may encode
   missing standardized values as zero with a separate feature-missing indicator;
   that zero is an encoding of missingness, not a measured neutral signal.
   No model matrix or imputation is built in Stage 2A proposal work.

Do not add pooled normalization, learned imputation, extra final z-clipping or
performance-based threshold/window selection. Maintain stable sign conventions.
Industry/sector neutralization is deferred: it requires verified historical
classification and changes the economic interpretation. Baseline retains market,
sector and size exposures explicitly; later neutralization is a separately logged
specification, never adopted because of superior performance.

## Architecture and QA plan

Proposed reusable modules: src/features/returns.py (admitted intervals),
src/features/baseline.py (pure window functions), src/features/preprocessing.py
(date-local clipping/standardization), src/features/qa.py (keys/timing/coverage).
Entry point: scripts/21_build_stage2a_baselines.py. Not created in proposal step.
Feature output is separate from labels, keyed by (permno,signal_date), with raw/z
values, feature-missing masks/reasons, valid counts and max_input_date. A later
left join preserves target/status exactly. Predictor allowlist excludes every
Stage 1G outcome column. Labels/status remain a separate auditable relation.

Tests before scaling: append/change all after-t prices/events/eligibility and
confirm unchanged features at t; source-anchor/global-calendar adjacency;
nonordinary/delisting availability masks; split-safe return/volume behavior;
strict warm-up and gaps; excluded-current shock denominator; quantile/constant
cross-section behavior; missing-target independence; unchanged eligible keys,
label counts and target values. Cross-sectional availability flags must derive
only from through-t feature inputs.

## Descriptive output plan

Tables under results/tables/stage2a/: feature_definitions.csv,
coverage_by_year.csv, missingness_reasons.csv, distribution_summary.csv,
cross_sectional_dispersion.csv, preprocessing_diagnostics.csv,
correlation_after_preprocessing.csv. Include denominators, valid counts,
raw/clipped summaries and daily cutoff/dispersion diagnostics. Correlations
are same-date pairwise Pearson correlations of standardized features, summarized
with equal date weighting and valid-date/pair counts; never correlations to targets.

Figures under results/figures/stage2a/: annual coverage heatmap, feature-correlation
heatmap, raw cross-sectional dispersion series and representative distributions
for the first market date in June of 2000/2010/2020/2025 where available. Plot
selection is calendar-based and independent of targets/performance. Tables and
figures should be reproducible from cached features and a recorded specification.
No IC, Sharpe, PnL, portfolio or model-performance output. No empirical coverage
or distribution claim is made before computation; no fabricated charts now.

## Remaining preimplementation questions

Confirm the conservative daily-return/event availability mask and unit/status
handling from existing local caches/reference definitions on a small fixture.
Measure historical warm-up coverage without choosing a window from predictive
results. Reconfirm any proposed minimum-period/clip conventions on data integrity
and numerical stability only, with a new log entry if altered. The snapshot's
historical-revision limitation is not cured by close-t filtering. Proposed
preprocessing and feature definitions are not yet frozen; target remains frozen.

The original proposal text is retained as the specification record. Current implementation and QA results are in docs/stage2a_completion.md; predictive evaluation requires separate authorization.
