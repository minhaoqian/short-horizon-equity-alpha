# Stage 3A completion — fixed walk-forward baseline combination

Stage 3A CLOSED, 2026-10-06; RL-057–RL-059. No holdout signals accessed.

## Frozen implementation

Expanding 1993 history, 68 quarterly fits, forward signal dates 2003-01-02–2019-12-31. Training requires signal, exit and economic ledger maturity by the prior-quarter cutoff. Normalized equal-date squared loss, fixed Ridge lambda=1, unpenalized intercept; all eight unchanged stored standardized features, complete-eight inputs, no imputation. Coefficients learned from past mature labels and held fixed within each quarter. Equal-weight and all eight univariate Ridge benchmarks use matched keys; original standardized feature scores also retained. Table prefixes `raw_` denote unchanged stored z scores, not original unprocessed feature measurements.

Ridge minimizes squared error on raw frozen five-day returns while evaluation uses cross-sectional Rank IC. This intentional objective/metric difference is frozen; a rank-oriented model or target transformation requires a separately prespecified stage. No feature/sign/penalty selection, portfolio analysis, new horizon or Stage 1/2 change.

## Sample and integrity

3,829,908 original forward eligible keys retained, zero duplicates or key-set differences; 3,824,632 numeric labels. Complete-feature predictions: 3,764,003 (98.2792% of eligible). Evaluation pairs: 3,759,878 (98.1715%). All 65,905 incomplete-feature keys retain missing reasons. 4,125 unlabeled signals still receive forecasts: future label availability never determines prediction.

Coverage tables by date, year, label status and year/status retain original denominators. Annual score coverage ranges 97.8133%–98.7295%. Missing-entry score coverage is 50.4977%, ordinary 98.3063%, cash delisting 99.3628%; complete-case missingness is not assumed random. The 3,066 valid-entry unresolved outcome paths remain recorded for later sensitivity/bounds analysis.

612 fixed Ridge fits completed. First fit: 943,294 mature complete rows / 2,451 dates; final fit: 4,633,164 / 6,666. All cutoff/maturity checks pass. Synthetic and bounded 1998 numerical QA matches independent SVD Ridge (maximum coefficient error 3.36e-18). All 204 fold-file checksums verified; 300 stored forecasts independently recomputed, maximum error 8.67e-19; 34 paired inference rows independently checked. Maximum normal-equation residual 4.34e-19.

## Predictive findings

| Model | Mean Rank IC | HAC4 t |
| --- | ---: | ---: |
| Ridge combination | .013399 | 4.805 |
| Equal weight | -.003838 | -1.223 |
| Univariate reversal | .014787 | 4.512 |
| Univariate momentum | .002249 | .528 |
| Univariate volatility | .006039 | 1.030 |
| Univariate turnover | .006073 | 1.320 |
| Univariate dollar liquidity | -.001058 | -.490 |
| Univariate volume shock | -.000212 | -.159 |
| Univariate gap | .006441 | 3.567 |
| Univariate intraday | .008127 | 4.192 |

4,279 IC dates per model. Ridge HAC4 nominal 95% interval [.007934,.018864]; fixed HAC20 t=4.520, interval [.007589,.019209]. All five anchored nonoverlap phase means positive (.008469–.017209), all phase nominal intervals above zero. Positive annual IC in 13/17 years and 48/68 quarters; negative years preserved.

Paired Ridge minus equal-weight mean IC .017237, HAC4 t=4.170. Paired Ridge minus univariate reversal -.001388, HAC4 interval [-.005221,.002446], HAC20 interval [-.005514,.002738]. **No demonstrated incremental predictive gain over reversal.** All benchmarks and weak/negative findings retained; no redefinition after results. Nominal exploratory intervals do not provide familywise-confirmatory claims.

Ridge quintile means increase monotonically; Q5 minus Q1 target contrast .001518 (15.18 basis points), versus .001926 for univariate reversal. These conditional five-day target contrasts are not portfolio returns. Equal-weight curve mixed; no feature removal or reweighting. Correlation tables/heatmap preserve descriptive score redundancy.

## Reproduction and outputs

Entry point: scripts/30_walk_forward_stage3a.py; reusable modules src/models/. Existing local research Python must provide requirements.txt dependencies. Project WRDS-only .venv does not contain the research dependencies; use the established system research interpreter for tests/processing. No installation or authentication required for this cached stage.

Private licensed outputs: data/interim/stage3a/manifest.json, source_manifest.json, predictions/fold_01.parquet through fold_68.parquet, daily_ic.parquet and daily_quantiles.parquet. All remain ignored and uncommitted; checksum/fingerprint resume prevents silent stale reuse.

Public reproducible aggregate tables: results/tables/stage3a/ (IC, annual/quarterly, five phases, paired differences, coverage/status/reasons, coefficients, maturity/numerical/integrity QA). Seven figures under results/figures/stage3a/: forward_ic_time_series, quintile_monotonicity, coefficient_paths, paired_ic_differences, nonoverlapping_phases, prediction_coverage and ic_correlations.

Full repository suite: 87 tests passed. Static CRSP revision-vintage limitations and conditional outcome/feature measurability remain explicit; economic maturity proof does not certify historical publication vintages. No new unresolved implementation gate. Development has previously been inspected and is not a pristine research holdout. 2020–2025 holdout remains untouched.

Next action: research-lead review of these fixed results and authorization of a separately prespecified next stage. Do not automatically begin another model, tuning, portfolio construction or holdout evaluation.
