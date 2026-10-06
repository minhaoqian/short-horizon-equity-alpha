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

**Stage 2A — Feature Framework / Baseline Signals: global event timing requires review (RL-047)**

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
Feature definitions, timing, preprocessing and descriptive-output plans are
documented in docs/stage2a_feature_framework_proposal.md. The small synthetic
global event layer now covers all securities for 1993–2025; both rights cases
are detected and all 59 repository tests pass. Declaration/ex-date conflicts
require point-in-time review; see docs/stage2a_global_event_layer.md.
No full-panel features or models computed.

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
