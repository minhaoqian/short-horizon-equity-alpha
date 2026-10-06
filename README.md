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

**Stage 2B — Baseline Signal Evaluation: development CLOSED (RL-055)**

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
