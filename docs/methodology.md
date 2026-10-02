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
Preferred:
- observe features using information available through close of day t
- form signal after close t
- execute at open t+1

This specification is **not yet locked**. It requires empirical verification of CRSP opening-price coverage in the chosen liquid universe.

Fallback:
- signal after close t
- execute at close t+1
- measure the forward holding-period return strictly after execution

The execution convention will be selected based on data quality and implementability, never on which convention produces the higher Sharpe ratio.

### Universe thresholds
Candidate baseline filters:
- ordinary US common equities
- price > $5
- market capitalisation > $1bn
- trailing 20-day ADV > $20m
- adequate history for required features

Exact thresholds remain conditional on cross-sectional distribution and coverage diagnostics.

### Sample period
Candidate extraction period:
- 1993-01-01 through 2025-12-31

The final modelling period will be chosen after data QA. Earlier observations may be used solely for feature warm-up and training history.

## Forecast target

Primary target is a five-trading-day forward return beginning strictly after the chosen execution time.

For next-open execution, candidate definition:

```
y_i,t = Open_i,t+6 / Open_i,t+1 - 1
```

If close-based execution is selected, the target will be redefined so that no return used in the label predates the assumed fill.

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
