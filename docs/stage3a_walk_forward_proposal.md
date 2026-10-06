# Stage 3A — Walk-forward baseline signal combination proposal

2026-10-06, RL-056. **REVIEW REQUIRED; no model fitting authorized yet.**
Stage 1G targets, Stage 2A features and Stage 2B temporal split remain frozen.

## Methodology gate and scope

Permitted now: read the frozen contracts, prior development diagnostics and
cached market-calendar dates; define a protocol and document alternatives.
No new predictive computation, fitting, model/hyperparameter selection or
holdout inspection in this proposal step. Stage 2B results do not determine
feature membership, input signs, penalty strength or the evaluation start.
No new targets, neutralization, data sources, portfolios, costs or Sharpe.

If approved, Stage 3A would fit regularized linear combinations and evaluate
forward development forecasts only. It is the first supervised model-fitting
sub-stage, not permission for Elastic Net, trees, portfolio optimization or the
2020–2025 holdout. All 1993–2019 has already been examined in Stage 2B; forward
predictions in this stage are temporally out of training sample, not a pristine
research holdout or evidence immune to earlier development inspection.

## Dated protocol

- Initial history: development signal dates 1993-01-04–2002-12-31, restricted
  to labels matured by the initial fit-information cutoff, 2002-12-31 close.
  Actual original eligible history starts 1993-01-22. The latest signal whose
  t+6 exit is calendar-mature at that first cutoff is **2002-12-20**.
- First forward signal: **2003-01-02** after close, execution still open t+1.
- Evaluation ends at signal **2019-12-31**. Its frozen holding window may extend
  into 2020; retain the label as development. No 2020–2025 signal is admitted.
- Expanding history from the same 1993 start; no rolling-window variant in this
  first baseline. Avoid choosing a forgetting length after performance.
- Refit quarterly with information through the last market close preceding the
  quarter's first market signal date. Freeze coefficients for all signal dates
  of that quarter; new close-t features/preprocessing remain date-local.
- **68 sequential quarters**, 2003Q1–2019Q4. The proposed schedule CSV lists
  each fit cutoff, latest calendar-mature signal and evaluation interval.

| Forward validation block | Fit information cutoff | Calendar-mature training signals through | Evaluation signal dates |
|---|---|---|---|
| 2003Q1 | 2002-12-31 close | 2002-12-20 | 2003-01-02–2003-03-31 |
| 2003Q2 | 2003-03-31 close | 2003-03-21 | 2003-04-01–2003-06-30 |
| 2003Q3 | 2003-06-30 close | 2003-06-20 | 2003-07-01–2003-09-30 |
| 2003Q4 | 2003-09-30 close | 2003-09-22 | 2003-10-01–2003-12-31 |
| Remaining quarters | Previous quarter's final market close | Cutoff minus six global market positions | Through 2019-12-31 |

Every quarter is forward validation. There is **no inner hyperparameter search
or distinct tuning-validation period** in this fixed-penalty baseline. Previous
validation observations may enter later training only when their labels have
matured. Report the concatenated forward stream, every quarter and every year;
never choose favorable blocks. No random split. Later tuning requires a new
nested temporal-validation proposal before execution.

The schedule is generated from DISTINCT cached dlycaldt dates in development,
ordered with zero-based market positions. For each year/quarter beginning
2003, cutoff position = first evaluation position −1; latest calendar-mature
training signal position = cutoff position −6. The full date table, rather
than a security's available rows, determines every boundary.

## Label maturity and overlap purge

At fit cutoff C, require numeric frozen label, signal date <= C, planned
exit date <= C, and economic availability of every ledger valuation/claim
input by C. A populated final label is not alone a maturity certificate.
Audit this against the existing frozen ledger/event-cache timing before fitting;
if an input's required availability cannot be established, stop for review.
Static CRSP snapshot/revision-vintage limitations remain disclosed; effective
ledger dates do not prove historical database publication vintages.

For ordinary five-day labels, the exit condition excludes the final six signal
dates through C: their exits lie after C. This is a training-availability mask,
not censorship, reassignment or mutation of any frozen label/key. Do not use
later payments, successor prices or later eligibility to mature a label.
Training targets therefore do not overlap the upcoming validation holdings.
No additional arbitrary embargo or feature-lookback purge: past inputs may
legitimately be shared. There is no use of training observations after an
evaluation block, unlike symmetric cross-validation.

Labels within training and validation still overlap across adjacent signals.
Do not claim independent rows/daily ICs or report IID coefficient significance.
Retain approved evaluation inference: Bartlett/Newey–West lag4 primary,
fixed lag20 sensitivity, calendar gaps preserved, all five non-overlap phases
anchored 1993-01-04 and sampled HAC4. Apply the same inference to dated paired
IC differences between combination and benchmarks. No winning lag/phase choice.

## Primary model and regularization

Inputs: all eight stored Stage 2A z features, unchanged:
reversal_5, momentum_60_skip5, volatility_20, turnover_20,
dollar_liquidity_20, volume_shock_20, gap_1, intraday_1.
Target: original decimal frozen five-day total return, no clipping,
transformation, cross-sectional demeaning or replacement.

Primary model is Ridge with one unpenalized intercept and eight unconstrained
coefficients. Proposed fixed dimensionless **lambda = 1.0**, chosen before any
combination fit; no penalty grid or selection in Stage 3A.

For D training dates with n_d usable rows per date, minimize:

```
(1/D) * sum_d [(1/n_d) * sum_i (y_i,d - b - x_i,d' beta)^2]
+ lambda * sum_j beta_j^2
```

All mature numeric, complete-feature rows enter; no outcome outlier trimming.
Dates with zero usable rows contribute no loss. Report thin training sections;
minimum30 applies to evaluated ICs, not a silent extra training-row exclusion.
Each date has equal total weight, preventing later larger cross-sections from
determining the training objective by row count alone. Normalize row weights
to 1/(D*n_d) so fixed regularization does not weaken merely as history grows.
Use float64 and a deterministic numerically stable solve. No further pooled
feature scaling; frozen same-date preprocessing is already applied.

L2 regularization handles collinearity while retaining every feature; no PCA,
Lasso, correlation pruning or industry neutralization. Ridge coefficients may
be negative when learned **only from each past training window**. This is model
estimation, not pre-flipping an input using full-period Stage 2B ICs. Do not
choose constraints or orientations after results. Unconstrained signed learning
is explicitly part of the proposal requiring approval.

## Missingness and prediction ledger

No imputation, zero/mean fill, forward/back-fill, missingness predictors or
outcome-derived features. Primary combination requires all eight finite z
values. If any is missing, keep the original key with missing score and the
specific feature/reason flags. No fallback model or feature-specific changing
weights in this first baseline. This preserves frozen feature definitions but
adds an explicit complete-feature **model-input policy**, subject to review.

Produce scores for every complete-feature eligible validation signal even when
its eventual target is missing. Label status/availability never determines
whether to predict. Training needs matured numeric labels; evaluation needs
numeric labels, but prediction and coverage ledgers retain all eligible keys.
Report original eligible, complete-feature, prediction, numeric-label and
evaluable-pair denominators by date/year and label status after prediction.
Missing labels remain as frozen, including cash delistings and unresolved assets.
Do not assume missingness random; retain later bounds-analysis obligations.

## Benchmarks and incremental information

Prespecify all benchmarks; select none from Stage 2B rankings:

1. Fixed equal-weight average of all eight unchanged z inputs, no learned signs.
2. Eight separate univariate Ridge models, each with intercept, lambda1,
   identical dated training cutoffs/date weights and the **same all-eight-
   complete training/evaluation keys** as the combination. Learned coefficients
   can be signed using past training only, as above. These assess incremental
   combination value beyond historically calibrated single signals, rather
   than an apparent gain from reversing a raw negative feature.
3. All eight original feature scores on the same evaluation keys, plus their
   broader pairwise availability as a separately labeled coverage reference.

No best-single-feature winner chosen after evaluation, coefficient sign flip,
feature selection, learned ensemble of models or Elastic Net/OLS/tree search.
Primary Ridge plus eight univariate Ridge fits implies **612 fixed fits**
(68*9), not 612 independent experiments or a model-selection tournament.
Use paired daily IC differences on identical securities and common valid dates;
never compare an all-feature score's restricted sample directly with Stage 2B's
1993–2019 wider feature-specific means as proof of combination improvement.

## Predictive metrics, tables, figures and QA

Primary: daily tied-rank Spearman, >=30 numeric score/target pairs, explicit
undefined constants; equal-date mean, median, SD, positive frequency and
HAC4/HAC20 nominal confidence intervals. Report quarterly/annual stability,
all five fixed phases, paired mean-IC differences against every benchmark,
tie-preserving quintile monotonicity/Q5−Q1 target contrasts and IC correlations.
No single post-result superiority threshold, familywise-confirmatory claim,
forecast-driven specification change or portfolio-return interpretation.

Secondary stability: quarterly coefficient/intercept paths, coefficient norm,
training conditioning/penalty checks and forecast coverage. No coefficient
p-value claims, target-based preprocessing, new target horizons or IC decay.
Preserve failed combinations, weak benchmarks and every fixed comparison.

After approval, reusable logic under src/, entry points under scripts/;
private predictions/fit manifests under data/interim/stage3a. Safe tables under
results/tables/stage3a and figures under results/figures/stage3a: schedule and
maturity/coverage QA, OOS IC summaries/series, annual/phase/paired comparisons,
quintiles and coefficient paths. At this proposal gate the dated table is useful;
no performance chart or placeholder model result is produced.

Before execution, synthetic tests must show: unchanged predictions when future
labels/features are perturbed; quarterly coefficient freeze; exit/ledger maturity
purge; global calendar boundaries; no holdout signals; preserved missing keys;
no label-status input; matched benchmark sample; no imputation; penalty scaling
consistent across growing sample sizes. Bounded historical integrity QA precedes
full fitting. Stop at material timing/selection/integrity ambiguity or completion.

## Review requested

Approve or revise this dated quarterly expanding protocol, fixed normalized
lambda1/date-balanced Ridge objective, complete-feature/no-imputation policy,
and training-only signed combination/univariate benchmark coefficients.
No frozen methodology is modified until approval. No fitting has occurred.
