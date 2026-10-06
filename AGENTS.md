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

The primary forecast target and explicit missing-label policy are **frozen** in docs/methodology.md (RL-042). Stage 1G is CLOSED. Preserve all eligible keys and never treat outcome-derived label availability as signal-time eligibility or a predictor.

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

Latest completed methodology log entry: **RL-050**.

Current work: **Stage 2A — Feature Framework / Baseline Signals: CLOSED**.
See docs/stage2a_completion.md. 6,699,101 unique eligible feature keys retained;
eight approved raw/clipped/z baselines, explicit missingness, global outcome-
independent effective-date events. All 109 chronology conflicts checked: 92
reconciled / 17 explicitly ambiguous. Both rights regressions pass; 64 tests pass.
Full integrity/preprocessing QA passes. No target/performance evidence used.
Licensed outputs are local data/interim/stage2a_features/parts/ (32 partitions)
plus manifest.json. Static snapshot-vintage limitation remains documented.
Stop before predictive evaluation, feature selection, ML or portfolios.

Completed stage: **Stage 1G — Target Formula Freeze: CLOSED**.
Cumulative-factor verification and distribution-aware close-to-close
reconstruction passed; source-interval price/total returns remain
(P*F+N)/P0-1 and (P*F+N+O)/P0-1. Period factor transport remains required.

The approved next-open wealth ledger and missing-label contract are frozen in
`docs/methodology.md`. Signal after close t; observed entry open t+1; planned
exit open t+6. Entitlement: entry_date < DisExDt <= exit_date. No reinvestment,
zero interest on cash. Received assets require verified quantities/boundary
values; cash delistings require independently measurable wealth. No fabricated
prices, shifted horizons or unsupported zero/-100% labels.

Reproduction: `scripts/20_construct_stage1g_targets.py`.
Output: `data/interim/stage1g_targets/targets_5d.parquet`, with manifest and
32 reproducible partitions. All licensed outputs remain local/uncommitted.
6,699,101 unique eligible keys; 6,676,750 numeric labels (99.666358%).
Statuses: ordinary/event-adjusted 6,673,134; missing entry 7,596;
measurable cash delisting 3,616; unresolved exit 4,087;
right-censored 8,686; other unresolved corporate action 1,982.

All missing labels retain reasons and holdings/event flags. These are outcome
metadata, not predictors. The 6,069 valid-entry unresolved paths require later
bounds/sensitivity analysis; complete-case evaluation remains conditional on
measurability. The 45 missing-lag source observations remain preserved; never
interpolate/forward-fill them. No model has been trained.

Next action: research-lead authorization/specification for baseline predictive
signal evaluation, including strict walk-forward and overlapping-label controls.
Do not begin it automatically. Preserve the frozen Stage 1G contract.

## Autonomous execution policy

Within an approved sub-stage, proceed through methodology check, implementation,
processing, QA, descriptive outputs, log/docs/handoff and commit without routine
engineering approval. Use caches; report unexpectedly expensive work before running.
Stop for material specification changes, ambiguous economic/source evidence or
uncertain point-in-time validity, performance-driven specification risk, material
integrity problems, external authentication/permission, and major stage boundaries.
Never retry failed authentication automatically. Preserve all keys, forbid future
inputs/outcome metadata as predictors and unauthorized filling, and log material
findings/failures sequentially. Assess useful safe tables and figures at each
material sub-stage; no performance charts before authorization. Commit tested safe
code/docs/aggregate outputs only; push only when policy/credentials permit.
Do not cross into predictive evaluation, ML or portfolios without authorization.
