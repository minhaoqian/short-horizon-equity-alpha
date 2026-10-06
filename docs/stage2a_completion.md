# Stage 2A completion — approved baseline feature framework

2026-10-06. RL-048–RL-050. Stage 2A is CLOSED after descriptive QA; no predictive evaluation authorized or performed. Stage 1G stays unchanged/frozen.

## Timing gate

All 109 declaration-after-exdate events checked against same-date complete distribution groups and cached daily amounts/factors/return identities: **92 reconciled, 17 ambiguous**. DisOrdinaryFlg, not frequency/type, determines the ordinary cash bucket (official CIZ User Guide p12). DisDeclareDt is QA metadata, not an availability timestamp. Three ambiguous event-date records enter the eligible sample; a conservative 60-date exposure bound has 180 unique keys. Failed reconciliation yields explicit timing_ambiguous affected feature intervals. No later metadata repairs a value. These counts concern events/exposure, not mutually exclusive feature missingness.

Effective interval is (previous global trading date,current date]; events must be effective by close t. The globally complete index retains all event types and zero-valued rights. Nonmarket-date events belong only to the subsequent containing market interval. Distributions use all 670,977 records; delistings use complete 29,833 records. Neither source scope nor admission uses target outcomes or exception membership. Actual last-price delisting dates are not treated as announcement times; stored-return rows are excluded.

## Implemented definitions

- Reversal: 1 minus compounded gross returns t-4:t, all five admitted.
- Momentum: compounded gross returns minus one, t-59:t-5, exactly 55 admitted.
- Volatility: sample standard deviation, latest 20 admitted returns.
- Turnover: log1p(mean(P*V/(1000*DlyCap))), latest 20, at least 15 valid.
- Dollar liquidity: log1p(mean(P*V)), latest 20, at least 15 valid.
- Volume shock: log1p(current dollar volume) minus log1p(mean prior 20), at least 15 prior valid plus current.
- Gap: observed open divided by observed immediately preceding market close minus one; positive actual prices and globally verified event-free interval.
- Intraday: observed close divided by observed same-day open minus one.

Strict return windows retain absent calendar positions. Returns require positive trade-price anchors, adjacent market dates, single-period source flags and reconstruction consistency. Nonordinary/received-asset or unverified factor paths are inadmissible. The simple-split factor definition is documented in official CIZ Calculations p7; simultaneous factor combinations not verified by daily terms are excluded rather than guessed. Dollar-volume/cap fields use documented native units. No cumulative-factor level, future eligibility or filling is used.

## Dataset, coverage and preprocessing

**6,699,101 rows and unique eligible keys**, exactly matching frozen target identifiers in both directions. The target relation remains separate/unchanged; construction projects only its identifiers for reconciliation. No label/status/value enters features, selection or preprocessing. Output keeps raw, clipped and z values, valid counts, raw/processed missingness reasons and through-t event flags. Source masks are not outcome availability flags.

| Feature | Raw / standardized observed | Missing | Coverage | Timing-ambiguous keys |
|---|---:|---:|---:|---:|
| reversal_5 | 6,696,422 | 2,679 | 99.960010% | 15 |
| momentum_60_skip5 | 6,635,431 | 63,670 | 99.049574% | 165 |
| volatility_20 | 6,681,241 | 17,860 | 99.733397% | 60 |
| turnover_20 | 6,698,418 | 683 | 99.989805% | 0 |
| dollar_liquidity_20 | 6,698,418 | 683 | 99.989805% | 0 |
| volume_shock_20 | 6,697,073 | 2,028 | 99.969727% | 0 |
| gap_1 | 6,630,530 | 68,571 | 98.976415% | 3 |
| intraday_1 | 6,693,015 | 6,086 | 99.909152% | 0 |

Timing-ambiguous feature counts overlap. Gap has the lowest overall coverage (98.976415%); momentum coverage is 99.049574%, with strict history/warm-up requirements. Liquidity coverage is 99.989805%.

Same-date finite eligible cross-sections only: type-7 1st/99th percentile clipping, population-SD z-scores, minimum 30 observations, constant sections zero with explicit flag. Raw/clipped/z stored separately. No additional finite raw keys are lost to preprocessing in this panel. Maximum absolute daily z-mean error is <7e-14; maximum nonconstant z-SD error <4e-15; zero clipping/count/nonfinite/reason/key/future-input violations. Sector/industry neutralization remains deferred. No imputation/model matrix.

## QA and descriptive findings

Bounded sample retained 4,971 eligible keys from 32,010 source rows/275 securities/124 market dates; 24 deterministic production-vs-pure raw-value/count comparisons pass. Both zero-impact rights corner cases have missing gap/reversal/volatility in the final dataset, while their original keys remain. Full relevant suite: 64 tests passed, covering timing, calendar gaps, compounding, units, missingness, preprocessing and after-t invariance.

Full factor QA finds no factor changes without global event records among comparable source intervals. Twelve preliminary comparisons exceeded nominal absolute 1e-6 due rounding edges or simultaneous splits; unresolved combinations are conservatively excluded under the existing verified-factor rule. This adds no missing eligible feature observations. Nonconflicting metadata cash amounts are not substituted for contemporaneous daily amounts.

Feature-to-feature correlations are descriptive, equal-date pairwise means, with pair/date counts. Largest observed overlap is volatility/turnover (~0.672); no feature is selected or rejected on that basis. Missingness and warm-up remain visible against the full eligible denominator. No target correlation, IC, Sharpe, PnL, portfolio return or model-fit statistic was computed.

## Reproduction and outputs

- `python3 scripts/25_qa_stage2a_timing.py`: offline census, safe aggregate table; exact cases remain local.
- `python3 scripts/26_construct_stage2a_features.py`: bounded QA only; `--full` builds 32 fingerprinted/checksummed cached batches plus date-local preprocessing.
- `python3 scripts/27_report_stage2a_features.py`: final integrity/preprocessing QA and descriptive tables/figures.
- Licensed dataset: `data/interim/stage2a_features/parts/part_*.parquet` (32 partitions), raw_parts, cross_section_stats.parquet, manifest.json; all ignored.
- Safe tables: timing_conflict_reconciliation, bounded_feature_qa, feature_definitions, coverage_by_year, missingness_reasons, distribution_summary, cross_sectional_dispersion, preprocessing_diagnostics, correlation_after_preprocessing under results/tables/stage2a/.
- Figures: annual_feature_coverage, feature_correlation, raw_dispersion (monthly median of daily dispersion), representative_distributions under results/figures/stage2a/. Distribution dates are first June market dates in 2000/2010/2020/2025, fixed independently of outcomes.

## Limits and boundary

Static CRSP caches do not prove revision-free historical publication vintages. Missing/unsupported events remain explicit, not evidence of zero effects or absence. No new network/authentication/data extraction or raw scan was performed in this step. No remaining construction gate is open under the approved economic-date/missingness policy. Stop before baseline predictive/signal evaluation; that next research step needs explicit authorization and walk-forward/overlap controls.
