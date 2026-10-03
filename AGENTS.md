# AGENTS.md

## Purpose

This repository is a research-grade systematic-equity project. Agents working here should behave like disciplined research assistants, not code generators.

The project question is:

> Can short-horizon cross-sectional equity forecasts generate economically meaningful market-neutral alpha after realistic risk controls and transaction costs?

## Mandatory workflow

For every material new research step:

1. **Inspect current state**
   - Read `docs/methodology.md`.
   - Read the most recent entries in `docs/research_log.md`.
   - Inspect the relevant scripts, tests, and prior outputs.

2. **Run a methodology gate**
   - State what evidence is permitted for the step.
   - State what evidence is prohibited.
   - Do not change locked specifications because later results look better or worse.
   - If a methodological change is genuinely required, document the reason before using it.

3. **Plan the smallest next action**
   - Prefer one auditable step over a large multi-stage jump.
   - Do not train models before the data/target gates are closed.
   - Do not introduce new data sources unless the current stage requires them.

4. **Execute reproducibly**
   - Reusable logic belongs in `src/`.
   - Pipeline entry points belong in `scripts/`.
   - Exploratory work belongs in `notebooks/`.
   - Tests for leakage, keys, timing, and data integrity belong in `tests/`.

5. **QA before interpretation**
   - Verify schema, keys, dates, missingness, point-in-time timing, and sample attrition.
   - Separate data-quality failures from economically meaningful observations.
   - Never silently drop problematic observations.

6. **Record the decision**
   - Append a numbered entry to `docs/research_log.md` for every material methodological choice, failed diagnostic, rejected specification, or gate closure.
   - Preserve failed hypotheses and rejected alternatives.

7. **Commit with a descriptive message**
   - One logical research change per commit when practical.
   - Do not commit licensed raw CRSP data or secrets.

8. **Report compactly**
   - Tell the user what was checked, what changed, what remains unresolved, and exactly one next action when possible.

## Locked research specifications

Treat `docs/methodology.md` as the source of truth.

Currently locked:
- Market: US equities
- Frequency: daily
- Primary market data: CRSP CIZ
- Research task: cross-sectional return forecasting/ranking
- Primary horizon: 5 trading days
- Validation: strict walk-forward
- Primary forecast metric: Spearman Rank IC
- Portfolio family: long-short market-neutral
- Headline results: net of transaction costs
- Timing: information through close t; signal after close t; execution at open t+1
- Security universe: point-in-time ordinary US common equity under the locked CRSP CIZ classification
- Liquidity filters: price > $5, market cap > $1bn, ADV20 > $20m, with at least 15 valid observations in the 20-day ADV window

The primary forecast target is **not yet frozen**. Cumulative-factor verification and close-to-close return reconstruction have passed. Do not treat the candidate open-to-open formula as final until holding-boundary dividend treatment and endpoint/delisting rules are verified.

## Research integrity rules

- Point-in-time information only.
- No survivorship bias.
- No random train/test split.
- No global full-sample normalization.
- No execution before the assumed fill.
- Delisted securities must not disappear retrospectively.
- Overlapping labels must be handled explicitly.
- Hyperparameters must not be tuned on the final holdout.
- Universe thresholds cannot be chosen using Sharpe, PnL, IC, or future returns.
- Failed or unattractive results must not be hidden.

## Data handling

Licensed CRSP raw data stay local.

Do not commit:
- `data/raw/`
- large licensed extracts
- credentials
- WRDS passwords
- local environment secrets

Derived compact QA tables may be committed only when licensing and repository policy permit.

## Repository structure

- `docs/` — methodology, research log, analysis plan, data dictionary, sample construction, experiment registry
- `data/raw/` — local licensed source data, gitignored
- `data/interim/` — local intermediate datasets
- `data/processed/` — model-ready datasets
- `scripts/` — reproducible pipeline entry points
- `src/` — reusable research code
- `tests/` — integrity/leakage/unit tests
- `results/tables/` — generated QA/result tables
- `results/figures/` — generated figures
- `results/experiments/` — experiment outputs
- `notebooks/` — exploratory diagnostics
- `paper/` — final research paper

## Current handoff state

Latest completed methodology log entry: **RL-033**.

Current stage: **Stage 1G — Target Formula Freeze**.

Completed sub-gate: **close-to-close distribution-aware reconstruction PASSED**.
Validated source-interval returns are `(P*F+N)/P0-1` (price) and
`(P*F+N+O)/P0-1` (total), using CRSP previous price and period factor.
Cumulative-basis reconstruction must retain the factor transport documented in
`docs/stage1g_return_reconstruction.md`; cumulative factors cannot replace the
period return factor.

Reproduction script (completed diagnostic):
`scripts/14_validate_distribution_reconstruction.py`

Local inputs and outputs:
- fingerprinted daily and cumulative-factor caches in `data/interim/`
- `data/raw/crsp_names_history.csv`
- local QA outputs in `results/tables/stage1g/`

The 45 missing-lag eligible observations remain in the sample with explicit
multi-period flags. DlyPrevPrc recovers source two/three-period returns only;
missing daily prices must not be interpolated or forward-filled.

Next action: plan Stage 1G holding-boundary dividend treatment and
endpoint/delisting rules. This sub-gate has not been executed.

The primary five-day next-open target is **not frozen**. Do not train models.
