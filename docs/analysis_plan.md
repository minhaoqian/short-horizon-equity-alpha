# Analysis Plan

## Stage 0 — Methodology gate
Status: substantially complete.

Deliverables:
- research question
- timing discipline
- primary horizon
- validation architecture
- research integrity rules

## Stage 1 — Data and target design

### 1A. CRSP extraction and QA
- confirm exact CIZ WRDS schema
- extract candidate daily fields
- test duplicates and identifier integrity
- audit missingness
- audit opening-price coverage
- audit delistings
- inspect size and liquidity distributions

### 1B. Universe construction
- define point-in-time common-stock universe
- set price / size / ADV thresholds
- document exclusion reasons
- test universe stability through time

### 1C. Target construction
- lock execution convention
- construct 5D target strictly after execution
- quantify overlapping-label dependence
- specify purging / inference treatment

## Stage 2 — Feature engineering
- returns / reversal
- momentum
- volatility
- liquidity
- market-relative / beta
- optional industry-relative features

Each feature requires timestamp, formula, missing-data rule, and economic rationale.

## Stage 3 — Forecasting
Model ladder:
1. simple signal benchmarks
2. Ridge
3. Elastic Net
4. LightGBM / boosted trees

Evaluation:
- OOS Rank IC
- IC distribution
- IC decay
- quantile monotonicity
- stability by regime / sector / size

## Stage 4 — Portfolio construction
- rank long-short baseline
- dollar neutrality
- beta neutrality
- industry neutrality
- position limits
- gross exposure
- liquidity constraints

## Stage 5 — Transaction costs
- turnover accounting
- baseline linear cost
- spread-aware sensitivity
- market-impact sensitivity
- optional short-cost sensitivity

## Stage 6 — Net backtest
- daily PnL
- net Sharpe
- drawdown
- hit rate
- turnover
- cost drag
- exposure diagnostics

## Stage 7 — Attribution
Separate realised PnL into:
- broad market exposure
- industry exposure
- style / risk-factor exposure where feasible
- stock-specific residual
- transaction costs

## Stage 8 — Robustness
- 1D / 5D / 10D horizons
- universe thresholds
- feature subsets
- model complexity
- cost assumptions
- execution convention where data permit

## Stage 9 — Final paper
Research-paper structure:
1. Abstract
2. Introduction
3. Related literature
4. Data and sample construction
5. Methodology
6. Forecasting results
7. Portfolio construction
8. Costs and implementation
9. Portfolio results
10. Attribution and robustness
11. Conclusion
