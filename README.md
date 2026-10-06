# Short-Horizon Equity Alpha

**Working title:** Short-Horizon Equity Alpha Forecasting and Cost-Aware Market-Neutral Portfolio Construction

This repository implements a research-grade systematic equity workflow:

```
point-in-time data
→ feature engineering
→ walk-forward forecasting
→ market-neutral portfolio construction
→ transaction costs
→ risk controls
→ PnL attribution
```

## Research question

Can short-horizon cross-sectional equity forecasts generate economically meaningful market-neutral alpha after realistic risk controls and transaction costs?

## Current stage

**Stage 4B — Execution-Assumption Feasibility: OPEN / gate failed (RL-066)**

[Approved protocol](docs/stage4b_execution_protocol.md) and
[feasibility result](docs/stage4b_execution_feasibility.md): first-open capped
fallback resolves ordinary gaps but both candidates halt close2003-03-31 on
unverified successor quantities.60/4279decisiondates operational;114tests pass.
No portfolio performance/selection or holdout access. Review required; no cap extension.

Stage4A strict-identification audit and permanent limitation remain unchanged.

**Stage 4A — Cost-Aware Market-Neutral Portfolio Protocol: OPEN / strict continuation infeasible (RL-064)**

[Proposed dated portfolio and cost protocol](docs/stage4a_portfolio_protocol.md)
retains reversal and Ridge candidates with identical five-sleeve rules.
[Development-wide feasibility audit](docs/stage4a_continuation_feasibility.md)
complete: both candidates halt close2003-01-13 with no identified resumption
through2019; only7/4279 decision dates permit new orders.103tests pass.
No portfolio returns/Sharpe computed. A separately prespecified execution-
assumption stage is required before full-period portfolio claims.
2020–2025 holdout remains untouched.

**Stage 3A — Walk-Forward Baseline Signal Combination: CLOSED (RL-059)**

[Completion report](docs/stage3a_completion.md): all 68 quarterly forward blocks
completed under the approved fixed protocol, with 3,829,908 eligible keys retained.
Ridge mean Rank IC .013399; no demonstrated gain over univariate reversal.
87 tests pass. Frozen Stage 1/2 inputs and protected 2020–2025 holdout unchanged.
Stop for research-lead review before another model or portfolio stage.

Stage 1G remains CLOSED (RL-042).

The five-day next-open wealth target and explicit missing-label policy are
frozen in docs/methodology.md. All 6,699,101 eligible signal keys are retained;
6,676,750 have numeric labels (99.666358%). Distributions are not reinvested,
cash earns zero interest, and entitlement is entry_date < DisExDt <= exit_date.
Missing openings and unvalued holdings remain explicitly unlabeled; no prices
or returns are invented. Complete-case selection risk requires later bounds
and sensitivity analysis.

Local licensed dataset: data/interim/stage1g_targets/targets_5d.parquet.
Reproduction: scripts/20_construct_stage1g_targets.py.
Eight approved baselines are constructed for all 6,699,101 eligible keys;
raw, clipped, standardized values and explicit missingness are preserved.
Global event timing QA and full preprocessing/integrity QA passed; 64 tests pass.
Declaration dates are QA metadata; effective events and contemporaneous daily
reconciliation govern admission. See [Stage 2A completion](docs/stage2a_completion.md).
Licensed features: data/interim/stage2a_features/parts/ (32 parquet partitions).
Descriptive coverage/distribution/dispersion/correlation tables and four figures
are under results/tables/stage2a/ and results/figures/stage2a/.
Stage 2A is CLOSED. Stage 2B development evaluation is complete for signal dates
1993-01-04–2019-12-31: 4,816,452 original keys / 4,804,070 numeric labels.
The 2020–2025 final holdout remains untouched for predictive analysis/tuning.
All development signals with holding windows crossing into 2020 remain assigned
by signal date. Daily tied Rank IC, fixed HAC4/HAC20, five nonoverlap phases,
quintiles, annual stability and redundancy diagnostics passed QA; 78 tests pass.
Reversal's mean IC is +0.029921; intraday's is −0.020688. Weak, mixed and negative
signals remain unchanged; these conditional development diagnostics are not
implemented portfolios or net-alpha claims. See [Stage 2B completion](docs/stage2b_completion.md)
for all eight results, coverage/selection limits and safe tables/six figures.
Reproduction: scripts/29_evaluate_stage2b_baselines.py. No feature selection, ML,
portfolios or IC decay begun. Next protocol needs research-lead approval.
Stage 1G target and Stage 2A features remain frozen.

## Core design

- Market: US equities
- Frequency: daily
- Primary data: CRSP CIZ
- Primary forecast horizon: 5 trading days
- Task: cross-sectional return forecasting / ranking
- Validation: strictly walk-forward
- Portfolio: long-short, market-neutral
- Reporting: net of transaction costs
- Research discipline: point-in-time only; no survivorship, normalization, target, or execution leakage

## Repository map

- `docs/` — research design, decisions, literature, data dictionary, experiment registry
- `data/` — local raw/interim/processed data; licensed raw data are not committed
- `notebooks/` — exploratory and diagnostic notebooks
- `src/` — reusable research code
- `tests/` — integrity and leakage tests
- `scripts/` — reproducible pipeline entry points
- `results/` — generated figures, tables, experiment outputs
- `paper/` — final research paper

## Research integrity

Headline conclusions must come from pre-specified out-of-sample tests. Failed hypotheses and rejected specifications are retained in the research log rather than silently discarded.
