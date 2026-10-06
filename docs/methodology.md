# Methodology Gate

This document is the pre-analysis research contract. Specifications may be changed only for documented data-quality or methodological reasons, not because a backtest result is unattractive.

## Locked specifications

| Component | Specification |
|---|---|
| Market | US equities |
| Frequency | Daily |
| Primary data source | CRSP CIZ daily stock data |
| Research task | Cross-sectional return forecasting / ranking |
| Primary horizon | 5 trading days |
| Validation | Strict walk-forward |
| Primary forecast metric | Spearman Rank IC |
| Portfolio family | Long-short market-neutral |
| Headline performance | Net of transaction costs |
| Timing discipline | Point-in-time information only |
| Final holdout | Must not be used for iterative tuning |

## Conditional specifications

### Execution convention
Locked baseline:
- observe features using information available through close of day t
- form the signal after close t
- execute at open t+1

This rule was locked after empirical coverage testing in the candidate liquid universe using true trailing ADV20. Annual opening-price coverage is at least 99.294% over 1993–2025 and is effectively complete in recent years.

The baseline 5-day forward target therefore begins at the t+1 open. Any robustness specification using a different execution convention must be labelled explicitly and may not replace the baseline because of superior realised performance.

### Universe thresholds
Locked baseline filters:
- ordinary US common equities under the locked point-in-time security-classification rules
- price > $5
- market capitalisation > $1bn
- trailing 20-day ADV > $20m
- at least 15 valid observations in the 20-day ADV window

These thresholds were locked after a pre-specified sensitivity analysis using only sample breadth, time-series stability, opening-price coverage, and implementability proxies. No return-performance statistic was used.

### Sample period
Candidate extraction period:
- 1993-01-01 through 2025-12-31

The final modelling period will be chosen after data QA. Earlier observations may be used solely for feature warm-up and training history.

## Forecast target

**Stage 1G CLOSED — target specification frozen (RL-042).**

For every locked eligible signal formed after close t, entry date a is global
market date t+1 and planned exit date b is t+6. Do not shift these dates to
available security rows or re-filter holdings using future eligibility.
Buy one post-event share at the observed positive finite regular-session open a.

The five-day total-return label is:

```
y_i,t = (sum_j quantity_j(b) * observed_open_j(b)
         + cash(b) + established_measurable_receivables(b)) / observed_open_i(a) - 1
```

Positions include retained parent and verified successor assets. With no event,
this reduces to exit_open/entry_open - 1. Cash earns zero interest and is not
reinvested; established fixed cash receivables are carried at face value.
Entitlement is entry_date < DisExDt <= exit_date: entry-day rights are excluded,
exit-day rights included. Use actual ex-dates, never payment/storage dates to
assign rights. Apply verified splits before the relevant opening, including
exit-day splits. Cash amounts use the actual owned-share basis; documented
single-period daily amounts use the previous-price/share basis. Same-date cash
and split accounting must preserve that basis rather than arbitrarily order
individual distribution records. Pure split multipliers are 1+DisFacShr;
DlyCumFacShr is a consistency check, not DlyCumFacPr as a share multiplier.

Cash-only delistings receive numeric labels only when exit-boundary cash wealth
is independently measurable from matched event terms. Preserve the asset or
claim resulting from delisting; DelRet/storage dates do not themselves establish
exit-opening wealth, and payments/returns must not be counted twice. Later
settlement amounts are not substituted for values unavailable at the boundary.
Received securities, rights, property and compound assets require verified
quantities and exit-boundary values; otherwise the entire label is missing.

Every original eligible key is retained with one mutually exclusive status:

| Label status | Frozen construction count |
|---|---:|
| measurable_ordinary_event_adjusted | 6,673,134 |
| missing_entry_measurement | 7,596 |
| measurable_cash_only_delisting | 3,616 |
| valid_entry_unresolved_exit_wealth | 4,087 |
| administrative_right_censoring | 8,686 |
| other_unresolved_corporate_action | 1,982 |

Only the two measurable statuses have numeric labels. Missing entry means a
missing execution-price measurement, not necessarily a proven no-fill.
Unresolved exit holdings and corporate-action assets remain explicitly unvalued;
right-censoring is administrative. Every missing label has an explicit reason.
No forward-fill, interpolation, later-price substitution, horizon shifting,
or zero/-100% assumption without supporting evidence is permitted.

Label statuses and event flags are outcome metadata, never signal predictors
or future eligibility filters. Supervised training/evaluation use only numeric
labels after the relevant horizon/claim information has matured, under strict
walk-forward timing. Report coverage against the original eligible denominator.
Complete-case evaluation is conditional on measurability and is not asserted
to be unbiased for the full universe. Later robustness must retain the 6,069
valid-entry unresolved holdings in explicit sensitivity/bounds analyses, using
established components where possible; do not assume missing-at-random or
silently delete delistings. A nonnegative long-position wealth assumption alone
provides a -100% lower bound, not a finite upper bound. This is a robustness
assumption, not an imputed primary label. Overlapping labels require explicit
handling in subsequent validation design.

Reproduction: scripts/20_construct_stage1g_targets.py, using existing local
Stage 1G caches only. Licensed output: data/interim/stage1g_targets/targets_5d.parquet;
manifest.json records coverage, input fingerprints and accounting QA.

## Stage 2A baseline feature contract (RL-048–RL-050)

Stage 2A feature construction/descriptive QA is complete. Eight baseline definitions
in docs/stage2a_feature_framework_proposal.md and docs/stage2a_completion.md are
preserved: compounded reversal (t-4:t), compounded momentum (t-59:t-5, 55 returns),
sample volatility (latest 20), log mean turnover and dollar liquidity (20 with
15 valid), dollar-volume shock against the prior 20 (15 valid), event-free
adjacent-market-date observed overnight gap, and same-day observed intraday return.
Market-calendar positions are fixed; security-row gaps never shift a window.
DlyCap is converted from thousands of dollars using 1000*DlyCap.

Economic effective dates govern the through-close-t event layer. Complete global
StkDistributions/ StkDelists histories establish scope independently of outcomes.
An event enters only its through-t effective interval. DisDeclareDt is metadata QA,
not a standalone availability timestamp. Conflicting chronology must reconcile
with contemporaneous/earlier cached daily terms and the return identity; otherwise
the affected admitted-return/gap interval is timing_ambiguous and missing. Missing
metadata never implies no event. Unsupported received assets, nonordinary returns,
unverified factors and stored-delisting-return intervals remain inadmissible under
the approved conservative return definition. No later metadata/value repairs a feature.
Static snapshots do not establish revision-free historical publication vintages.

Preserve all 6,699,101 signal keys with explicit per-feature missingness/reasons.
Target/status/availability fields cannot construct or preprocess features. The
frozen target relation remains unchanged and separate; any label/status join occurs
after feature construction. No filling, future eligibility or future price input.

Preprocessing is per date/feature on finite close-t eligible values: at least 30,
linear/type-7 1st/99th percentile clipping, then mean/population-SD z-score.
Keep raw/clipped/z separately. Constant sections have observed z=0 and a flag;
insufficient/missing sections remain missing. No full-sample normalization or
performance-driven adjustment. Industry/sector neutralization remains deferred.
Stage 2A outputs are descriptive only; predictive evaluation requires separate
approval, strict walk-forward and explicit overlapping-label treatment.

## Stage 2B development evaluation contract (RL-053–RL-055)

Signal-date split: development/evaluation 1993-01-04 through 2019-12-31;
untouched final holdout 2020-01-02 through 2025-12-31. Development labels with
holdings crossing into 2020 remain development observations. Do not truncate,
censor or reassign them solely for crossing the boundary. Holdout signal
performance and use for feature/preprocessing/design/model/hyperparameter/cost
or portfolio choices are prohibited until the later research design/model/
portfolio freeze. Preserve every original key and frozen label status.

Stage 2B uses fixed signed stored-z features and numeric frozen 5D labels,
including measurable cash delistings: date-local average-tied-rank Spearman IC,
minimum 30 finite pairs, explicit undefined constants, equal-date summaries.
No preprocessing on the labeled subset. Approved primary mean-IC inference is
Bartlett/Newey–West HAC lag4 with fixed lag20 sensitivity, original calendar
gaps and intercept correction. Every-fifth-market-date robustness reports all
five phases anchored at 1993-01-04, with sampled lag4 HAC (20 market days).
No best-phase/lag/sign/feature selection. Five tie-preserving quantiles and
Q5-Q1 target contrasts are descriptive signal diagnostics, not portfolio returns.
Annual summaries and feature/IC correlations are development-only. Fixed-feature
chronological evaluation fits no model; later model fitting requires strict
walk-forward, no random splits, and explicit label-maturity/overlap controls.
IC decay is deferred; no new target horizon is authorized in Stage 2B.

Development evaluation completed in RL-055; see docs/stage2b_completion.md.
All fixed features remain unchanged. Reported statistics are conditional on
feature/target measurability, with nonrandom missing outcomes left explicit for
later sensitivity/bounds. Completion does not authorize feature selection,
model fitting, portfolio rules or opening the protected final holdout.

## Stage 3A approved walk-forward baseline contract (RL-057)

Protocol/schedule: docs/stage3a_walk_forward_proposal.md and its 68-quarter table.
Expanding1993 history, quarterly previous-market-close fit cutoffs, forward
signals2003-01-02–2019-12-31. Exit and ledger information must mature by cutoff.
All eight frozen z features, complete-eight/no-imputation model inputs; preserve
all prediction keys and report selection by date/year/status against eligible
denominators. Score availability cannot depend on future label status.
Normalized equal-date raw-return squared loss plus fixed lambda1 L2 penalty,
unpenalized intercept and unconstrained training-only coefficients. No tuning,
feature selection, pooled scaling, target clipping/transformation or input flips.
Benchmarks: fixed equal-weight and eight matched-sample univariate Ridge models.
Stage2B Rank IC/HAC4/HAC20/all phases/quantiles and paired difference inference
apply; no holdout signal access, portfolios/costs or other model families.

The squared-error training objective versus Rank-IC evaluation distinction is
intentional. Never alter it after Stage3A results; alternative transformed targets
or rank-oriented models need a separately prespecified stage. Complete-case
missingness is not assumed random. Static snapshot-vintage limitations persist.

## Model ladder

Complexity must earn its place out of sample.

1. naive / simple signal benchmarks
2. OLS or Ridge
3. Elastic Net
4. gradient-boosted trees such as LightGBM
5. optional nonlinear extension only if incremental value is demonstrated

## Portfolio layer

Forecasts and portfolio construction are separate research modules.

Baseline portfolio:
- rank signals cross-sectionally
- long high-forecast names
- short low-forecast names
- dollar neutral

Later constrained implementation may include:
- beta neutrality
- industry neutrality
- gross exposure target
- single-name caps
- liquidity / ADV constraints
- turnover penalty
- explicit transaction-cost penalty

## Research integrity rules

1. Every feature must have a documented availability timestamp.
2. Universe formation must be point-in-time.
3. Delisted securities must not disappear retrospectively.
4. No global full-sample normalisation.
5. No random train/test split.
6. Execution must occur strictly after signal formation.
7. Overlapping labels must be accounted for in inference and validation.
8. Hyperparameters cannot be tuned on the final holdout.
9. Headline portfolio results must be net of costs.
10. Failed hypotheses and rejected specifications remain in the research record.


## Locked security-classification universe

Historical security metadata are joined point-in-time using `SecInfoStartDt <= date <= SecInfoEndDt`.

Baseline security eligibility:
- SecurityType = EQTY
- SecuritySubType = COM
- ShareType = NS
- USIncFlg = Y
- IssuerType in (ACOR, CORP)
- PrimaryExch in (N, A, Q)
- TradingStatusFlg = A

This definition was locked after metadata-integrity and exchange/status breadth diagnostics.

Stage 3A execution completed under this approved contract (RL-059); see docs/stage3a_completion.md. No subsequent model, portfolio or holdout evaluation is authorized by closure.


## Stage 4A approved continuation contract and identification stop (RL-061–RL-064)

Preserve the approved five-sleeve fixedcapital/rank/cap/ADV/cost protocol in
docs/stage4a_portfolio_protocol.md. Linear3/6/12bp scenarios replace baseline
fixed6bp; narrow2020runoff permitted only for pre-existing development holdings,
never holdout signals/eligibility/forecasts/design choices. Strict unknown
propagation precludes full headlineperformance without a complete measured ledger.
Halt new primary orders from the first decision close when a scheduled exit's
execution/remaining quantity is unresolved; retain holdings, claims, liabilities
and borrowing, no capitalreuse/reservation approximation. Already-submitted
orders cannot be canceled retrospectively. Resume needs independent termination
evidence; later prices or security-level payment flags alone do not certify
account quantities/obligations. No filling, price substitution or horizon shift.
A virtual schedule is conditional mechanics only, not headline/live-book returns.

RL-064 feasibility audit finds both candidates persistently halted from close
2003-01-13 through2019; no fullperiod primaryperformance identified. Stop for a
separately prespecified execution-assumption stage. No such assumption or PnL
is authorized/implemented by this conclusion; frozen Stage1–3 unchanged.


## Stage 4B prespecified simulation execution contract (RL-065–RL-066)

Separate benchmark simulation, not observed historical execution; preserve the
Stage4A identification result permanently. Positive observed scheduled entryopen
t+1 else assume nofill/cancel/cash, no chase/future reallocation. Exitopen t+6
else first admissible positiveopen on next1–5 GLOBALdates; preserve all owned
assets/claims/quantities and short obligations until actual assumed liquidation.
No sixth-date extension, imputed open or bestprice choice. Aftercap failure use
unresolvedexecution/strictknown-close halt; earlier unknown corporate quantities
are integrity gates. Record assumeddates/reasons/globaldelay/realizedholding;
this does not alter frozen Stage1 five-day targets or Stage2/3specifications.

RL-066 audit fails on unverified successor quantities, halting both candidates
close2003-03-31 throughdevelopmentend; no performance/selection authorized or
computed. See docs/stage4b_execution_protocol.md and execution_feasibility.md.
Do not expand fallback cap or invent received inventory to pass this gate.

## Stage 4F approved generalized reservation contract (RL-080–082)

Separate conditional simulation; preserve Stage4A–E strict/conditional findings.
From empty2003book apply one generic quarantine policy, including Household,
without Stage4E-specific settlement exceptions. Reserve absolute original verified
executed entry notional, never asset value/NAV/collateral/loss/termination value.
No phase/cohort/side netting or unsupported release. Deduct long/short reserves
and retained/pending commitments separately; new equal paired deployment uses
minimum remaining side allowance in the current phase, under frozen ranks/caps/
ADV/fixed-share execution/cost/borrow/five-date cap. Honor submitted orders;
record opening overcommitments, block new affected-identity orders through known
information, and continue unrelated verified positions. Ordinary cap failures
also quarantine; canceled missing-open entries create no executed reserve.
Unknown obligations/wealth remain separate from verified inventory, measured
claims/cash and deployment accounting. Reference deployment exhaustion means no
new paired reference allowance, NOT insolvency or broker-margin failure.

Only feasibility/reservation/measurement-coverage evidence authorized. Full NAV,
Sharpe/drawdown and candidate selection cannot be reconstructed from measured
components. Conditional measured-component performance requires separate review.
RL-082 stops full feasibility at unidentified queued-entry share transformations:
no approved rule substitutes planned notional for an uncertified executed-entry
basis or silently changes share quantities. Synthetic/bounded QA passes; full
2003–2019 counts and measured-book feasibility remain uncertified pending review.
Frozen Stage1–3 and Stage4A–E contracts remain unchanged.
