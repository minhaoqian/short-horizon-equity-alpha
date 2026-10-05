# Methodology Gate

This document is the pre-analysis research contract. Specifications may be changed only for documented data-quality or methodological reasons, not because a backtest result is unattractive.

## Locked specifications

| Component | Specification |
|---|---|
| Market | US equities |
| Frequency | Daily |
| Primary data source | CRSP CIZ daily stock data |
| Research task | Cross-sectional return forecasting / ranking |
| Primary horizon | 5 trading days |
| Validation | Strict walk-forward |
| Primary forecast metric | Spearman Rank IC |
| Portfolio family | Long-short market-neutral |
| Headline performance | Net of transaction costs |
| Timing discipline | Point-in-time information only |
| Final holdout | Must not be used for iterative tuning |

## Conditional specifications

### Execution convention
Locked baseline:
- observe features using information available through close of day t
- form the signal after close t
- execute at open t+1

This rule was locked after empirical coverage testing in the candidate liquid universe using true trailing ADV20. Annual opening-price coverage is at least 99.294% over 1993–2025 and is effectively complete in recent years.

The baseline 5-day forward target therefore begins at the t+1 open. Any robustness specification using a different execution convention must be labelled explicitly and may not replace the baseline because of superior realised performance.

### Universe thresholds
Locked baseline filters:
- ordinary US common equities under the locked point-in-time security-classification rules
- price > $5
- market capitalisation > $1bn
- trailing 20-day ADV > $20m
- at least 15 valid observations in the 20-day ADV window

These thresholds were locked after a pre-specified sensitivity analysis using only sample breadth, time-series stability, opening-price coverage, and implementability proxies. No return-performance statistic was used.

### Sample period
Candidate extraction period:
- 1993-01-01 through 2025-12-31

The final modelling period will be chosen after data QA. Earlier observations may be used solely for feature warm-up and training history.

## Forecast target

**Stage 1G CLOSED — target specification frozen (RL-042).**

For every locked eligible signal formed after close t, entry date a is global
market date t+1 and planned exit date b is t+6. Do not shift these dates to
available security rows or re-filter holdings using future eligibility.
Buy one post-event share at the observed positive finite regular-session open a.

The five-day total-return label is:

```
y_i,t = (sum_j quantity_j(b) * observed_open_j(b)
         + cash(b) + established_measurable_receivables(b)) / observed_open_i(a) - 1
```

Positions include retained parent and verified successor assets. With no event,
this reduces to exit_open/entry_open - 1. Cash earns zero interest and is not
reinvested; established fixed cash receivables are carried at face value.
Entitlement is entry_date < DisExDt <= exit_date: entry-day rights are excluded,
exit-day rights included. Use actual ex-dates, never payment/storage dates to
assign rights. Apply verified splits before the relevant opening, including
exit-day splits. Cash amounts use the actual owned-share basis; documented
single-period daily amounts use the previous-price/share basis. Same-date cash
and split accounting must preserve that basis rather than arbitrarily order
individual distribution records. Pure split multipliers are 1+DisFacShr;
DlyCumFacShr is a consistency check, not DlyCumFacPr as a share multiplier.

Cash-only delistings receive numeric labels only when exit-boundary cash wealth
is independently measurable from matched event terms. Preserve the asset or
claim resulting from delisting; DelRet/storage dates do not themselves establish
exit-opening wealth, and payments/returns must not be counted twice. Later
settlement amounts are not substituted for values unavailable at the boundary.
Received securities, rights, property and compound assets require verified
quantities and exit-boundary values; otherwise the entire label is missing.

Every original eligible key is retained with one mutually exclusive status:

| Label status | Frozen construction count |
|---|---:|
| measurable_ordinary_event_adjusted | 6,673,134 |
| missing_entry_measurement | 7,596 |
| measurable_cash_only_delisting | 3,616 |
| valid_entry_unresolved_exit_wealth | 4,087 |
| administrative_right_censoring | 8,686 |
| other_unresolved_corporate_action | 1,982 |

Only the two measurable statuses have numeric labels. Missing entry means a
missing execution-price measurement, not necessarily a proven no-fill.
Unresolved exit holdings and corporate-action assets remain explicitly unvalued;
right-censoring is administrative. Every missing label has an explicit reason.
No forward-fill, interpolation, later-price substitution, horizon shifting,
or zero/-100% assumption without supporting evidence is permitted.

Label statuses and event flags are outcome metadata, never signal predictors
or future eligibility filters. Supervised training/evaluation use only numeric
labels after the relevant horizon/claim information has matured, under strict
walk-forward timing. Report coverage against the original eligible denominator.
Complete-case evaluation is conditional on measurability and is not asserted
to be unbiased for the full universe. Later robustness must retain the 6,069
valid-entry unresolved holdings in explicit sensitivity/bounds analyses, using
established components where possible; do not assume missing-at-random or
silently delete delistings. A nonnegative long-position wealth assumption alone
provides a -100% lower bound, not a finite upper bound. This is a robustness
assumption, not an imputed primary label. Overlapping labels require explicit
handling in subsequent validation design.

Reproduction: scripts/20_construct_stage1g_targets.py, using existing local
Stage 1G caches only. Licensed output: data/interim/stage1g_targets/targets_5d.parquet;
manifest.json records coverage, input fingerprints and accounting QA.

## Model ladder

Complexity must earn its place out of sample.

1. naive / simple signal benchmarks
2. OLS or Ridge
3. Elastic Net
4. gradient-boosted trees such as LightGBM
5. optional nonlinear extension only if incremental value is demonstrated

## Portfolio layer

Forecasts and portfolio construction are separate research modules.

Baseline portfolio:
- rank signals cross-sectionally
- long high-forecast names
- short low-forecast names
- dollar neutral

Later constrained implementation may include:
- beta neutrality
- industry neutrality
- gross exposure target
- single-name caps
- liquidity / ADV constraints
- turnover penalty
- explicit transaction-cost penalty

## Research integrity rules

1. Every feature must have a documented availability timestamp.
2. Universe formation must be point-in-time.
3. Delisted securities must not disappear retrospectively.
4. No global full-sample normalisation.
5. No random train/test split.
6. Execution must occur strictly after signal formation.
7. Overlapping labels must be accounted for in inference and validation.
8. Hyperparameters cannot be tuned on the final holdout.
9. Headline portfolio results must be net of costs.
10. Failed hypotheses and rejected specifications remain in the research record.


## Locked security-classification universe

Historical security metadata are joined point-in-time using `SecInfoStartDt <= date <= SecInfoEndDt`.

Baseline security eligibility:
- SecurityType = EQTY
- SecuritySubType = COM
- ShareType = NS
- USIncFlg = Y
- IssuerType in (ACOR, CORP)
- PrimaryExch in (N, A, Q)
- TradingStatusFlg = A

This definition was locked after metadata-integrity and exchange/status breadth diagnostics.
