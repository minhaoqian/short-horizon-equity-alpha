# Stage 4F — Generalized Conditional Portfolio Simulation Protocol

Date: 2026-10-06. Status: PROPOSAL FOR REVIEW; no implementation or performance authorized. Research Log RL-078–079.

## Scope, evidence gate and preservation

Close the event-by-event historical execution-recovery branch after Stage4E. Do not investigate the next merger individually. Stage4A strict identification failure, Stage4B failed fallback feasibility, Stage4C verified0.535 economic entitlement, Stage4D historical settlement identification CLOSED UNRESOLVED, and Stage4E three conditional failures remain permanent separate findings. New reservation rules cannot overwrite their artifacts or retroactively convert their results into passes.

Use unchanged development signals2003-01-02–2019-12-31, frozen Stage1 target and Stage2/3 features/forecasts, both candidates on identical rules, fixed reference capital N=$10m and five phase sleeves with S=N/5=$2m per side. No new fits, target horizon, feature selection, holdout access or performance. Permitted now: existing contracts, accounting identities, through-t state transitions and implementation feasibility reasoning. No new corporate-action search, data processing or extraction. The proposal is separate from the frozen methodology until approved.

## One generalized rule, applied from the start

Rebuild the future Stage4F simulation from the empty2003book under one rule for every security/cohort, including the original Household event. Do not inherit a preferred D0/D2/D5 settlement scenario or introduce a merger whitelist. Verified economic entitlement may be recorded as a claim, but does not certify deliverable/tradable inventory. Stage4E scenarios remain separate artifacts rather than primary exceptions.

At the first through-t recognition of an effective corporate action with unverifiable asset quantities, rights, cash terms, delivery or remaining obligations, set that position `corporate_action_unresolved`. Preserve parent/cohort identifiers, entry/exit/deadline, last verified signed quantity and share basis, any verified asset components, claims, liabilities and borrowing basis. The last verified quantity is a record of entitlement/obligation, not a claim that an extinguished parent stock remains tradable. Unverified components have null quantity/value; no artificial successor, zero wealth or assumed termination.

Verified components can follow the existing first-admissible execution rule only when their identity, quantity, deliverability and all effects of the action on that component are independently separable. Unverified successor inventory is never traded. If the original scheduled-exit-plus-five-global-date cap passes, retain `unresolved_execution` as an additional reason; reservation persists, without restarting or extending the cap. No outside-window discretionary liquidation is introduced.

Use the same quarantine/reservation treatment for an ordinary position still unresolved after the frozen five-date fallback, with reason `exit_execution_unresolved`. Temporary delayed positions with known inventory remain outstanding under the original fallback and occupy their sleeve capacity; they do not trigger a corporate-action reservation or vanish. Missing scheduled entry open still means canceled entry/cash/no chase: no executed position and no unresolved-position reserve.

The affected position alone stops consuming tradable-inventory assumptions. Other positions continue their frozen holds, exits, costs and borrow accounting. No candidate-wide halt solely for quarantine. If deployment allowance eventually reaches zero, record capital exhaustion and no new orders, not an inferred termination or a methodological whole-book halt.

## Separate ledgers and reservation basis

Keep independent records for:

| Ledger | Contents | Interpretation |
| --- | --- | --- |
| Verified inventory | Signed quantities, asset identifiers, deliverability and observed marks | Tradable only with verified execution inputs |
| Unresolved obligations | Last verified quantities/basis, unknown received assets, rights and signed liabilities | Never silently removed or valued at a reserve |
| Measured cash/claims | Established amounts, entitlement/payment dates, cash transfers | No double counting; receivable is not spendable cash |
| Deployment commitments | Phase/side budgets, pending orders, known retained commitments, reserves | Reference-capital allocation accounting, not NAV or broker margin |
| Unknown measurement | Component/date/reason, missing marks/costs/quantity, duration | Full wealth/risk metrics remain unidentified |

For position j, reserve R_j=absolute executed entry notional, using its verified entered quantity and observed entry open. Use the remaining original entry-notional basis only after an independently verified partial termination with a documented proportional allocation. Otherwise reserve the entire original amount. Signed short entry proceeds are not new deployment capital. No long/short or cross-cohort reserve netting.

R_j is fixed until verified release; it is NOT a stale market mark, estimated successor value, maximum loss, haircut, collateral requirement or historical settlement amount. No later prices update it. This reference-basis convention is proposed for approval because no certified market-value reserve exists for unknown assets, especially shorts. Unknown mark-to-market loss can exceed R_j; the simulation cannot certify solvency, gross/net exposure, concentration or actual funding from this reserve.

Measured distributions, sale of a verified component and partial cash receipts remain separately recorded. They do not release the entire reserve or remove unknown rights. Release requires independent evidence of termination of all remaining assets/claims/obligations, or independently documented proportional termination of a separable component. Do not actively pursue individual recovery events; a reusable adapter may recognize sufficient evidence in already available histories, through its effective/known date. No retrospective release or security-level delisting flag alone.

## Deployment and asymmetric long/short reserves

Reserve stays in the original phase's allocation budget across subsequent sleeve generations; no transfer to other phases or capital recycling. For phase p at decision close t, let U_Lp and U_Sp be sums of long-origin and short-origin unresolved reserves. Let K_Lp and K_Sp be known retained/overdue and already committed reference-basis amounts occupying that phase at the replacement boundary under the existing order lifecycle. Count a position once, as K or U, never both. Pending orders already charged to a budget are not charged again at fill.

```
A_Lp = max(0, S - U_Lp - K_Lp)
A_Sp = max(0, S - U_Sp - K_Sp)
A_p  = min(A_Lp, A_Sp)
new_long_dollars = new_short_dollars
                = min(A_p, original_selected_long_capacity,
                           original_selected_short_capacity)
```

This applies only to the phase scheduled for replacement, not five fresh sleeves per day. Preserve original top/bottom tied-quintile pools and deterministic equal-dollar water-filling, original absolute sleeve-name cap2%*S=$40k, gross1%ADV flow reservation, no cross-sleeve execution netting, fixed-share sizing at close and observed-open execution. A lower budget does not rerank names, relax caps, refill canceled entries using future opens or increase another phase's allocation. The proposed reserve changes only deployment allowance, not forecasts, target labels or frozen costs.

For example, one $40k unresolved long in a phase with no other commitments leaves $1.96m on BOTH new sides; the matching $40k short-side allowance stays undeployed. Do not short an extra $40k to offset an unknown long exposure. Equal new dollar deployment does not imply the unresolved total book is neutral.

With no K, aggregate remaining paired capital is sum_p max(0,S-max(U_Lp,U_Sp)); gross planned verified deployment is at most twice that amount. This phase-specific rule is stricter than pooling all reserves: no cross-phase balancing can conceal a constrained phase. Report both raw unresolved-notional fraction (sum_j R_j)/N and reserved paired-budget fraction sum_p max(U_Lp,U_Sp)/N. They are different quantities; neither is a measured loss or market exposure. Reconcile effective budgets including K and undeployed matched-side allowance separately.

### Order timing and budget exceptions

All new commitments are based on close-t knowledge. Reserve from the first decision close when unresolved state becomes known. Honor previously submitted orders; do not cancel retrospectively. Normal due-sleeve retirement/replacement remains the frozen opening lifecycle. Known overdue inventory and earlier commitments reduce later deployment; no assumed release of an ALREADY unresolved reserve at a scheduled exit.

An opening event, missed exit or price gap can make previously committed orders exceed a newly reduced reference allowance. Grandfather those orders, record explicit phase/side budget overcommitment, and make subsequent allowance zero on the affected constrained phase/side until reference capacity becomes available. Do not borrow from another phase, reset a reserve, rescale already submitted orders using the opening, or claim hard realized caps. This inherited timing exception must be reviewed explicitly; the rule certifies no NEW use of a known reserve, not future-proof account funding. Unknown obligations cannot certify broker margin. Independent actual-account funding/capital failure would be a review gate, not proof obtained from this proxy.

Where unresolved identity/quantity makes same-security flow or name-cap commitments unknown, block NEW orders in the affected parent/linked identifiers known through t. Keep the original eligible/forecast keys and quintile assignment, use zero execution capacity and an explicit reason, and redistribute only within the original selected pool under existing caps. Do not infer a future corporate group or change the universe. Unrelated names continue. Existing verified positions in the same name still follow their exit rules; uncertain affected executions remain quarantined.

## Costs, borrowing and incomplete marks

Keep frozen6bp linear +0.10*sigma20*sqrt(participation), original3/6/12bp replacement sensitivities, fixed100bp/year ACT/365 short-entry-notional borrow basis, existing borrow/impact sensitivities and zero baseline financing. No cost calibration. Verified partial termination adjusts borrow basis only with evidence; unresolved shorts continue their original fixed-basis fee accrual, without invented successor borrowing rates or assumed cover. Those calculable hypothetical fees are included in the known expense ledger even when associated wealth is unknown.

Known trades incur their costs; internal asset conversions and cash transfers are not duplicate trades/PnL. Missing cost inputs stay unknown. Ordinary missing daily marks do not become a corporate-action termination or automatically disappear into cash: annotate the measurement gap and retain holdings. Do not forward-fill to certify a NAV/exposure. Quarantine does not license artificial liquidation costs, sale proceeds, zero returns or reservation-value wealth marks.

## Prespecified reporting hierarchy

1. **Strict identification:** Stage4A–E original stops and failed full-period identification remain first-class results. No full headline historically observed executable Sharpe.
2. **Conditional measured-book diagnostics:** only after separate implementation/measurement review, report additive PnL from intervals whose required inventory, boundary values, claims and expenses are measured. Denominator remains fixed N, never just surviving identified capital. Report gross known components and all measurable fees, including unresolved-short accruals, separately. Unknown wealth/cost contribution remains null, not zero. At transitions into/out of quarantine, do not book a fictitious transfer at R_j or disappearance gain/loss. An interval with an unknown component is excluded from that component's measured contribution, with its known cash flows separately retained and explicit coverage. No synthetic full NAV or total-book drawdown can be made by summing only observed pieces.
3. **Unresolved path:** long/short/cohort counts, reference reserves/N, pending claim types, unknown borrowing/delivery, durations, release evidence, budget depletion/overcommitment and no-new-order reasons on every original calendar date.
4. **Economic identification coverage:** date/year/phase/candidate counts and original-entry-basis fractions for identified live assets versus unresolved holdings. Use cash/claims separately, plus fraction of intervals whose complete wealth/cost increments are measurable. A notional proxy is NOT an exact market-value fraction or missing-at-random claim. Preserve all keys, outcome statuses and canceled/unallocated reasons. Candidate comparison, if later authorized, must show both full-calendar coverage and common measurable-date attrition; no favorable date selection.
5. **Bounds:** publish only claim-level bounds supported by explicit legal/quantity assumptions. Nonnegative asset wealth may bound a simple fully paid long's remaining gross asset value from below by0; it does not fix the missing return, account liability or fees. An unresolved short can have unbounded loss; a fixed R_j supplies no downside bound. Mixed rights/property/obligations may have no useful finite bounds. Portfolio bounds may be infinite/unavailable; report that rather than create haircuts or finite short-loss caps.

Any future metric must carry: **conditional simulation under a generalized unresolved-position reservation convention**. A known-component return series is not total strategy return or a self-financing portfolio NAV. A diagnostic mean/volatility/ratio, if subsequently approved, must identify its changing measured composition, coverage and unresolved expenses; never label it full-book Sharpe. Full conditional account NAV/Sharpe/drawdown still requires all components to be measured over the stated interval. Reference budgeting does not waive that measurement gate. The earlier candidate-selection rule cannot be applied to incomparable partial wealth as if its full-ledger prerequisites passed.

## Next implementation gates and outputs — not authorized now

After proposal approval: synthetic reservation/signed-claim/order-timing QA; bounded historical accounting QA using caches; generalized development feasibility/reservation audit; then STOP for research-lead measurement/reporting review before performance. No automatic transition to a performance run. Do not access holdout signals/outcomes; any later required development-origin runoff must remain separately scoped, not expanded by indefinite unresolved positions.

Tests should cover no successor invention, no zero-PnL marks, no duplicate reserves, same-entry reference basis, symmetric no-netting side budgets, phase isolation, known-overdue commitments, queued-order exceptions, no pre-known-date quarantine/release, conditional costs/borrow retention, no capital release from mere prices/delisting dates, key/denominator preservation and no target-status inputs.

Proposed safe outputs: reservation rule table, coverage by date/year/side/phase, unresolved duration and release reasons, capital-account reconciliations, execution/cost measurement flags. Descriptive figures: identified/reserved/undeployed reference-budget path, long/short unresolved fractions and identification coverage; no performance plots before authorization. Licensed histories/inventories remain private; code under src/portfolio and entrypoints under scripts. This proposal creates no executable logic, data outputs or new test claims. The accounting/state table above is useful now; a numerical figure would imply an unrun simulation.

## Review requested

Approve or revise fixed original-entry-notional reserves, phase-specific tighter-side equal deployment, grandfathered opening overcommitment handling, generalized treatment of capped ordinary exit failures, the uniform no-event-specific baseline (including Household), and the reporting/measurement hierarchy. These are proposed methodological choices, not frozen by this document. No event-level investigation, PnL, Sharpe, holdout or new model work has been performed.
