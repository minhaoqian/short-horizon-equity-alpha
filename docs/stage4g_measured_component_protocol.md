# Stage 4G — Conditional Measured-Component Performance Protocol

Date: 2026-10-06. **PROPOSAL FOR RESEARCH-LEAD REVIEW.** RL-086–087. No performance computation, implementation or new data access authorized by this document. Frozen Stage1–4F specifications remain unchanged.

## 1. Scope and evidence gate

Propose how to report the identified parts of the two frozen development candidate books: univariate reversal and eight-feature Ridge. Use the Stage4F orders, executed inventory, claims, unknown obligations, reserves and original calendars. Do not refit, rerank, alter allocation/execution/cost parameters, select a winner or use target-status inputs.

Permitted evidence at this step: approved accounting contracts, timing identities, existing measurement schemas and Stage4F descriptive QA. Prohibited: computing/inspecting new PnL, return distributions, significance, Sharpe, drawdown, target performance, cost calibration or holdout outcomes. No raw scan, WRDS, event recovery search or new source.

Every later numerical report must begin with the permanent Stage4A–E identification findings, followed by Stage4F reservation/coverage evidence, before conditional contributions. Strict account wealth remains unidentified. Reference deployment capacity does not establish actual funding, dollar/beta neutrality, margin or solvency. Original-executed-entry reserves and planned-notional proxies are commitments, never market values or loss bounds.

## 2. Calendar, accounting boundary and fixed denominator

Primary proposed reporting grid: every global trading date from the first scheduled entry **2003-01-03 through2019-12-31**, fixed before results. Keep the empty2003-01-02 initial decision state as initialization/QA, not an extra zero observation in performance means. Stage4F's4,279decision-date grid remains intact and accompanies the reporting grid. No candidate-specific start, fully measured prefix as the primary sample, or outcome-selected ending date.

A row dated d records the gross wealth increment from the preceding regular-session opening to opening d, plus fees for actual assumed executions at opening d and borrow accrued over the preceding opening-to-opening calendar interval. Positions entered at d first acquire market-price PnL in the following interval; their entry fee belongs to d. Positions liquidated at d receive their final preceding-interval price/entitlement contribution, then exit fees at d. On the first entry row there are no prior holdings: their gross increment is a documented structural zero, while any identified entry fees are still charged. Initial funding and trade principal are not income.

All ratios use fixed **N=$10,000,000 per candidate**, never measurable capital, remaining paired allowance, actual surviving assets, or proxy reserves:

`conditional_measured_component_contribution_d = identified_net_contribution_d / N`.

Mandatory display label: **conditional measured-component return**. It is not total portfolio return, a self-financing wealth process or expected full-book alpha. No compounding, NAV=N+cumulative partial PnL, equity curve, full-book drawdown, Sharpe ratio or mean/volatility ratio.

No2020–2025 source outcomes, signals, forecasts, eligibility or performance in the primary report. Late2019development positions/orders remain outstanding; no forced closing, truncation of original holding rules or completed-lifetime claim. This is a calendar-window contribution report, not complete signal-cohort lifetime performance. Development-origin2020runoff is deferred from this proposal; any later report needs separately reaffirmed narrow accounting scope, cannot include holdout signals or extend indefinite unresolved recovery.

## 3. Atomic economic increments and no fictitious quarantine transfer

Build a signed component journal keyed by candidate, cohort/phase, asset/claim/expense identifier and posting date. Each component has value or null, measurement reason, required inputs and timing provenance. Separate gross economic increments, fixed execution costs, impact costs, borrow expenses, structural zeros and unknown residuals. Do not change the existing strict `measured_sum` primitive into a null-skipping total-book aggregator.

For an ordinary held asset with verified quantity and both adjacent opening marks, gross increment is signed owned quantity times the opening-price difference. Verified splits transport quantity/share basis before valuation; same-date claims use the prior owned basis. Corporate-event asset bundles require verified retained/successor quantities, claims and both boundary values. Linked conversions cannot be broken into a measured parent write-off and an omitted successor gain: internal asset replacement is one coupled economic increment unless independently separable components are established.

| Item | Reporting treatment |
|---|---|
| Verified adjacent asset wealth increment | Identified signed gross contribution |
| Independently established fixed entitlement | Recognize once on effective entitlement date/boundary; signed debit for shorts |
| Payment of an already recognized receivable | Cash/claim transfer, no second income |
| Market entry/exit principal | Cash and inventory change together; not a standalone profit or loss |
| Verified cash-only termination | Cash/claim replacement less prior asset wealth once; no duplicated sale/dividend/DelRet |
| Quarantine or reference reserve creation | State/budget change only; no asset sale, reserve-value mark, write-off or transfer PnL |
| Unverified quantity/value/entitlement | Null economic increment with reason; retained obligation |
| Ordinary missing opening mark | Null adjacent increment; no carry-forward or gap bridging |

Entitlement remains `entry_date < DisExDt <= actual_assumed_exit_date` for the simulated held inventory; the frozen Stage1 target keeps its original planned exit. Entry-day rights are excluded and exit-day rights included. Delayed holdings retain legally established intervening claims under the unchanged five-date cap; no reinvestment, zero cash interest. Later payment amounts or successor prices cannot retrospectively repair boundary measurements.

A known cash entitlement can be reported separately while an associated stock/rights increment is unknown, only with a disjoint ledger partition: it is excluded from that unknown bundle's residual and cannot also be counted in a measured event-bundle increment. Unknown claims do not become zero claims. Short obligations preserve their sign; no long/short or cross-cohort netting of unknown wealth.

A missing adjacent mark remains missing even if a later mark returns. Resume identified daily increments only between two newly valid adjacent marks with verified inventory/event terms. Do not allocate an unmeasured multi-day change to a later daily row or reconstruct it with a later-price substitute.

## 4. Costs and borrow: identified under frozen assumptions

“Measured” means required quantity/value inputs are identified **under the frozen simulation assumptions**, not that historical auction fills, broker invoices, loans or settlement were observed.

Keep the baseline6bp fixed allowance, impact coefficient0.10, borrow100bp/year ACT/365 and zero financing drag. No cross-sleeve trade netting. Apply frozen sensitivities only if later authorized for reporting, all symmetrically and without choosing a preferred case;3/6/12bp replaces the fixed6bp component. Reporting does not alter orders or reserve budgets.

For a verified execution leg k:

```
V_k = abs(verified executed quantity) * positive observed execution open
fixed_cost_k  = V_k * 6/10000
impact_cost_k = V_k * 0.10 * sigma20_previous_close * sqrt(participation_k)
```

Participation uses the frozen gross-flow/ADV convention and decision-time inputs, never same-day future volume. Identify fixed and impact charges separately. If V is known but sigma/participation is unknown, the fixed charge remains an identified expense while impact stays null. Unknown V/execution makes both charges unknown; never charge a planned-notional proxy as if it were executed flow. Known actual simulated legs remain in turnover even if their modeled impact cannot be measured. Missing cost inputs cannot erase a known charge or become a zero charge.

Borrow accrues with the frozen original verified short-entry basis over actual calendar days, including weekends, from entry through before independently verified termination/cover. Existing unresolved shorts retain their known basis and conditional fee accrual; associated unknown asset wealth does not erase this expense. For `queued_execution_quantity_unresolved`, executed entry date/basis remain unknown: borrow is null, not planned-proxy times a rate. Known short dividend/claim obligations belong to signed gross economic components, not a second borrow fee.

## 5. Identified subtotals, unknown residuals and empty cases

Define a mutually exclusive journal of economic increments. The daily identified gross subtotal sums only identified gross increments; transaction/borrow subtotals sum only identified charges. Each displays identified and unknown component counts/status alongside its value. Unknown components remain stored as null throughout; unknown residual dollars are **unavailable**, not equal to the reserve and not assumed to cancel.

Daily identified net contribution is a sum of identified **signed primitives**: gross increments and negative known expenses. Retain known fees even when associated gross wealth is unknown, and known cash entitlements even when other components are unknown. Do not apply an intersection mask that discards all expenses from a quarantined cohort. Conversely, do not evaluate `gross.fillna(0)-cost.fillna(0)-borrow.fillna(0)` or label a null-skipping sum total PnL.

Three statuses are required for each subtotal: `complete_within_declared_component_scope`, `partial_identified_subtotal`, `no_identified_active_component`. A zero is allowed for a fully verified absence of an economic item or an identified flat increment. If active components are all unmeasured, the relevant subtotal is null. Empty idle phases or the baseline zero-financing assumption alone cannot manufacture a numeric zero net contribution for an otherwise wholly unmeasured active book. If only a nonzero known borrow charge is identified, the signed identified net subtotal can be negative while gross stays null and the full-account residual remains unknown.

Every calendar row remains present, including wholly unmeasured rows. No date is removed merely because one position is unresolved. Annual totals are sums of identified primitive dollars posted in that calendar year, with missing residuals and coverage displayed; they are not full-year account PnL or completed-cohort returns. An all-unmeasured category is null, not an empty-sum zero. No fiscal-year relocation, late-information recovery or artificial return at quarantine/release.

## 6. Coverage must accompany every result

Recompute amount/interval measurement validity before contribution calculation; Stage4F input-availability masks are useful QA, not proof that every economic increment/cost amount is measurable. Keep all original keys, cohort identities and dates; no future eligibility/target-availability filter.

Required daily/annual fields:

- Original eligible/decision/order denominators and reporting-calendar counts.
- Asset-cohort intervals: identified wealth increments / all required intervals, including persistently unresolved cohorts and queued executions. Declare the cohort/event-bundle counting unit; do not inflate coverage by splitting known pieces into extra counted assets.
- Complete wealth-and-expense component fraction; separate known fixed-cost/impact/borrow counts and unknown expense obligations. Conditional amount coverage is not necessarily identical to Stage4F screening coverage.
- Identified fixed cash/receivable components, unknown claim/obligation counts and reasons, separately from asset coverage.
- Verified-executed-entry-basis coverage with its explicit denominator; unmeasured executed notionals excluded and their counts disclosed. Planned proxies reported separately, never inserted as executed capital.
- Unresolved long/short/cohort counts and durations; executed-basis reserves, planned proxies, raw combined commitments/N, phase paired-budget reserve/N, matched undeployed allowance, phase/side commitments and queued overcommitments.
- Numeric-subtotal observation count / original calendar count; annual mean/minimum/end coverage and reserve states. Use ratio-of-count totals for annual interval coverage, not an unweighted mean of daily percentages.

The **market-value fraction of the full account identified is unavailable** when missing quantities/values prevent its denominator. Count and verified-entry-basis fractions are transparent proxies, not substitutes for that fraction. Changing measured composition and declining coverage are not missing-at-random. No post-result coverage cutoff, favorable fully measured date selection or inverse-coverage scaling of contributions.

## 7. Permissible diagnostics and inference proposed

| Diagnostic | Definition and limitation |
|---|---|
| Identified gross PnL subtotal | Sum of measured signed gross increments, unknown residual shown |
| Transaction-cost drag | Identified fixed and impact expense subtotals separately; full modeled drag unknown if any required part missing |
| Borrow drag | Identified conditional fixed-basis fees, including unresolved verified-entry shorts; unknown bases separately null |
| Conditional measured-component net PnL | Identified signed gross/cost primitives only; not total net PnL |
| Verified executed turnover | Sum abs verified traded notionals / N, both legs without netting; conventional one-way figure equals half this diagnostic |
| Daily contribution mean/volatility | Mean and sample SD of numeric identified net contribution/N; not full-account expected return or risk |
| Annual presentation | Identified calendar-dollar totals/N and observed-day mean/SD, with complete original calendar coverage |
| HAC mean inference | Nominal dependence-adjusted SE/t/95%CI for the conditional daily mean, not a test of full-book alpha |

Primary inference retains the Stage4A prespecification: Bartlett/Newey–West **lag20**, fixed **lag4 sensitivity**, no result-dependent choice. Five overlapping sleeves, fallback holding extensions and persistent reservation states preclude IID inference. Lags do not certify stationarity or eliminate measurement selection/long memory; inference is descriptive for this observed component process. No Sharpe or mean/SD ratio, even under a “conditional” label. Annualized scaling, if shown, is explicitly252*observed daily mean and sqrt(252)*daily SD, never compounded annual portfolio return or annual account volatility.

For any wholly unmeasured aggregate dates, retain original calendar positions in inference; do not compress the remaining observations into adjacent trading days. Proposed explicit sandwich for mean mu over n numeric subtotals on original T-date grid:

```
s_d = x_d - mu for numeric x_d; masked score 0 for a missing aggregate
Var(mu) = [sum_d s_d^2
           + 2*sum_{l=1..L}(1-l/(L+1))*sum_{d=l+1..T} s_d*s_(d-l)] / n^2
```

A masked zero score is an inference bookkeeping device, **not** a zero return/value inserted into the ledger or statistics. This estimates the observed-subtotal mean conditional on the measurement process, not a missing-value-corrected full-calendar/full-book mean. Report n/T; no further finite-sample correction proposed. Require n>L+1 and positive finite SE; otherwise inference unavailable. Constant/insufficient sections stay explicitly labeled, never infinite significance. Use mu±1.96SE and mu/SE as nominal summaries. No extra horizons, lag optimization, coverage-conditioned model, outlier clipping, trimming or performance-driven specification changes.

## 8. Comparison and presentation hierarchy

Same calendar, fixed N, order policy, component partition, cost assumptions and coverage definitions for both candidates. Show side-by-side gross/expense/net identified subtotals and their coverage. Optional descriptive paired differences use only dates with numeric subtotals for both and disclose original-calendar attrition plus distinct component compositions; they are not complete-book relative returns. No selection test, superiority/winner claim or reuse of the old frozen selection thresholds: their complete-ledger prerequisite remains unmet.

Mandatory first panel/table in each later report:

1. Stage4A strict identification failure; Stage4B fallback failure.
2. Stage4C legal entitlement recovery only; Stage4D historical delivery/cash-method identification unresolved.
3. Stage4E equally reported hypothetical scenarios, then the second-event halt; no preferred scenario.
4. Stage4F accepted reference-budget continuation, unresolved commitments and deteriorating measurement coverage; no funding/solvency/exposure certification.
5. Conditional measured-component contributions and cost assumptions, always paired with the coverage/reserve panel.

Proposed later outputs under results/tables/stage4g/: strict_findings, daily_component_contributions, annual_component_summary, daily_annual_coverage, cost_borrow_decomposition, verified_turnover, conditional_mean_hac and descriptive_candidate_comparison. Security-level component journals stay licensed/local under data/interim/; reusable logic under src/portfolio/ and entry points under scripts/ only after approval.

Proposed figures under results/figures/stage4g/: daily contribution with aligned coverage/reserve panels; annual identified gross/cost/borrow/net decomposition with coverage; turnover and cost-availability panels; contribution distribution by fixed calendar year. No equity/NAV/cumulative-compounded-return, drawdown or Sharpe plots. This proposal's accounting/diagnostic tables are useful now; no numerical performance figure is appropriate before authorization.

## 9. Review and later implementation gates

Approve or revise the identified-subtotal/unknown-residual rules, opening-boundary posting and primary calendar, separate fixed/impact expense treatment, coverage denominators, nominal HAC20/4 sandwich and descriptive-only comparison. The proposal does not freeze these choices.

After approval: synthetic signed-ledger/no-double-count/null tests, bounded historical accounting validation and exact reconciliation of Stage4F orders/reserves before any development contribution run. Retain unknown fee/value/quantity masks, validate event/share bases and expense dates, and stop for any material timing/integrity ambiguity. No automatic recovery of event branches or use of later metadata/holdout. Numerical computation, new data access and performance publication require the subsequent authorization.

**Stop here for research-lead review.** Full-account wealth stays unidentified; no total-book NAV, historically executable Sharpe, drawdown, selection, funding, neutrality or solvency claim.
