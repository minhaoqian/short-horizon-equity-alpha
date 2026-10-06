# Stage 5 — Predictive holdout completion

Status: **CLOSED; final project synthesis review only**. Signal dates2020-01-02–2025-12-31. Development specifications were frozen before the single authorized opening. No portfolio performance or accounting changes were made.

## Protocol and timing

Three candidates only: unfitted original signed reversal after frozen same-date Stage2A preprocessing (`reversal_5_z`), Stage3A univariate reversal Ridge, and all-eight-feature Ridge. “Raw reversal” means unmodeled, not a new unprocessed-feature specification. No learned sign applied to the unfitted feature. Both learned candidates retain complete-eight/no-imputation coverage; raw reversal also has a separately disclosed broader sample. Same-key paired differences use the complete-eight intersection.

24 quarterly expanding refits continue history from1993. Prior-quarter close is the information cutoff; exit and frozen ledger maturity must precede or equal it. Normalized lambda1, equal-date raw-target squared-error loss, unpenalized intercept and all eight unchanged standardized features remain fixed. Earlier holdout outcomes enter later quarterly training only when mature. This is a prequential holdout of a frozen updating rule, not a2019fixed-coefficient evaluation. Objective/Rank-IC metric difference remains intentional.

Input-only predictions are durably saved and checksummed before future target/status joins. No target availability selects forecasts. Static CRSP publication/revision vintage is not independently established; existing effective-date/economic maturity caveats remain. All Stage2B tied-rank/min30/quintile rules retained; Bartlett HAC4 primary, fixedHAC20, all five global1993-calendar phases with sampledHAC4. Right-censored dates stay present and inference preserves calendar gaps.

## Sample and coverage

1,882,649 unique original eligible keys,1,872,680 numeric labels,9,969 explicit missing labels;1,508 original signal dates,1,502 dates with defined IC. Last six dates have no numeric target due to frozen endpoint censoring, not retrospective sample selection. Missing statuses:8,686administrative right-censoring,364missing entry,553unresolved exit,366other corporate action. Numeric labels include1,067cash-only delistings and1,871,613ordinary/event-adjusted paths. Nothing interpolated, filled or re-filtered.

| model | original_eligible | numeric_labels | predictions | evaluated_pairs | prediction_eligible_pct | evaluation_eligible_pct |
| --- | --- | --- | --- | --- | --- | --- |
| raw_reversal | 1882649 | 1872680 | 1882212 | 1872246 | 99.976788 | 99.447428 |
| univariate_reversal_ridge | 1882649 | 1872680 | 1852816 | 1842977 | 98.415371 | 97.892756 |
| ridge | 1882649 | 1872680 | 1852816 | 1842977 | 98.415371 | 97.892756 |

Learned forecasts lose29,833keys because one or more frozen inputs are missing. Broader reversal loses437feature keys. Conditional evaluation is not missing-at-random. Reason/date/year/status coverage is supplied, including retained timing-ambiguous feature intervals.2025evaluated coverage drops principally because final endpoint labels are censored.

## Frozen predictive results

Primary available-sample summaries; SD is daily IC sample SD, positive frequency is by defined date. HAC4 intervals below; HAC20 statistics in the accompanying table.

| model | mean | median | std | t_stat | ci_lower | ci_upper | positive_frequency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| raw_reversal | 0.015817 | 0.004423 | 0.166844 | 2.287246 | 0.002263 | 0.029371 | 0.513316 |
| univariate_reversal_ridge | 0.016043 | 0.005636 | 0.167257 | 2.317759 | 0.002477 | 0.029609 | 0.513981 |
| ridge | 0.015672 | 0.012317 | 0.157175 | 2.615266 | 0.003927 | 0.027417 | 0.529294 |

HAC20 t-statistics:2.157305unfitted reversal,2.183434univariate reversal Ridge,2.495336eight-feature Ridge. All primary means and95%intervals positive, but nominal inference and nonrandom measurability limitations must be retained. No multiplicity-adjusted discovery or economically executable alpha claim.

Annual means (all six years retained):

| year | raw_reversal | ridge | univariate_reversal_ridge |
| --- | --- | --- | --- |
| 2020 | 0.030681 | 0.029858 | 0.030666 |
| 2021 | 0.009042 | 0.009676 | 0.009034 |
| 2022 | 0.025195 | 0.025882 | 0.025954 |
| 2023 | 0.002512 | 0.004182 | 0.002946 |
| 2024 | 0.016488 | 0.018791 | 0.01663 |
| 2025 | 0.010695 | 0.005204 | 0.010737 |

All six annual means and all five phase means are positive for every candidate, with materially varying strength. Phase mean ranges: reversal0.010010–0.023624; univariate0.010327–0.023820; Ridge0.008117–0.024555. Individual annual/phase confidence intervals often include zero. No favorable phase/year selected.

All three aggregate quintile curves strictly increase. Q5−Q1 frozen-target contrasts:0.002522/0.002577/0.002076 (25.22/25.77/20.76bp) for reversal/univariate/Ridge. These equal-date predictive contrasts are not portfolio returns and include no execution/cost assumptions.

On identical complete-eight keys, Ridge-minus-reversal and Ridge-minus-univariate mean daily IC difference is−0.000370817; HAC4 t−0.117948,95%CI[−0.006534,0.005792];HAC20 t−0.114774. Univariate slope remains positive, so its ranks equal unfitted reversal on the same keys. There is **no demonstrated incremental Rank-IC advantage** from the combination; no candidate winner selected.

Frozen forward development2003–2019 primary means0.015021/0.014787/0.013399 compare with holdout0.015817/0.016043/0.015672. Positive average prediction and aggregate monotonicity survive descriptively; year/phase magnitudes vary. Development Ridge-minus-reversal difference−0.001388 also failed to establish incremental value. Original1993–2019 Stage2B reversal reference remains separately labeled. No result triggered specification changes.

## QA and reproducibility

195repository tests pass, including8focused tests for weighted reference fits, future-input perturbation invariance, maturity, schedule, input-only/no-imputation API, identical-key tied ranks/quintiles, undefined constant ranks and join-order mapping. Bounded2019fixture matches independent sklearn fits.144quarter files checksum-verified;2,400forecast rows independently reconstructed with zero score error;24maturity audits have zero violations.24quarters/48reported learned model fits; all original keys retained, no duplicates, numeric-status reconciliation exact. Protected development/Stage4 files byte-identical.

Two engineering failures were corrected without changing rules or inspecting predictive results: calendar SQL parentheses before any fit, and outer-join ordering after the first saved forecast but before any IC calculation. Same holdout-opening fingerprint migrations and original forecast checksum are recorded privately; no second opening or score overwrite.

Reproduce saved-report QA using `scripts/40_report_stage5_holdout.py`. `scripts/39_stage5_predictive_holdout.py` verifies/resumes the existing single-opening manifest; completed runs return without refitting. Private predictions, outcomes, training moments and manifest are under `data/interim/stage5/`; no licensed security rows committed.31safe aggregate CSV/JSON outputs under `results/tables/stage5/`,8figures under `results/figures/stage5/`: IC time series/distribution, annual stability, all phases, quintile monotonicity, same-key paired differences, coverage and development comparison. Daily evidence is also saved, not just monthly figure smoothing.

RL-092–RL-097 record approval, QA repairs, results and closure. Stage4A–G strict failures/conditional limitations remain permanent; predictive holdout cannot establish complete executable wealth or justify a cost/accounting change. **Next action: final research-lead project synthesis. No automatic new research stage.**
