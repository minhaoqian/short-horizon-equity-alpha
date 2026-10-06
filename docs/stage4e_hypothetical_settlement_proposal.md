# Stage 4E — hypothetical settlement scenarios: proposal only

Date: 2026-10-06. Research Log: RL-072. NOT APPROVED FOR EXECUTION.

## Purpose and evidence gate

Conditional simulation of the blocking Household-to-HSBC event, not historically identified execution. Historical D and M remain null/unidentified. Preserve all Stage1–3 specifications, Stage4A strict result, Stage4B original failed audit and Stage4C accepted ratio. No performance has informed these assumptions. This proposal requests review before any implementation or feasibility computation.

## Fixed scenario grid

Use three equally reported hypothetical pre-open credit scenarios, indexed from the first global trading date following the merger: D0=2003-03-31, D2=2003-04-02, D5=2003-04-07. Indices mean global trading positions from March31, not generic settlement conventions. These dates are availability stress assumptions, not inferred delivery dates. Do not select the scenario producing better outcomes; no historically preferred or empirically selected scenario is designated.

For all three, hypothetical M is the legally permitted effective-date ADS closing-quotation method. This is explicitly NOT evidence of HSBC's actual selection. Fractional amount equals signed fractional ADS entitlement times the verified specified ADS closing quotation for 2003-03-28, the legal effective date. Before any implementation, verify that the existing quote and its flags certify the required closing quotation; an unverified daily value is insufficient. If the prescribed quotation cannot be certified, stop for review; no substitute quotation or later price. The historical agent-sales method is not simulated because actual pool sales, expenses and allocation are unidentified.

Assume valid account exchange instructions and successful processing before each scenario's pre-open credit. This is an additional hypothetical account-processing assumption, not a historical mailing or instruction date. Assume cash-in-lieu credit on that same D; cash-credit timing is separately flagged as hypothetical. Fractional cash remains a signed receivable/obligation until D and then converts to cash exactly once. Before credit, it is a scenario-established measurable claim, not spendable cash. Zero interest/no reinvestment; no invented fees beyond the separately frozen portfolio cost rules.

## Inventory and execution

For each cohort separately: e=0.535*q; W=sign(e)*floor(abs(e)); F=e-W. Signed whole ADS inventory/delivery obligation and fractional cash claim remain distinct. No fractional ADS trade, cross-cohort netting or sign asymmetry. Existing parent cash rights survive independently with their original timing; this proposal does not assign them the merger cash-credit date.

Whole ADSs become executable no earlier than scenario D. Apply the first positive observed regular-session open at or after scheduled exit and delivery, within the existing scheduled-exit-plus-five-global-date cap. The original cohort cap dates remain April7/8/11; credit does not restart the clock. Reject unobserved opens, later-best-price selection and horizon rewriting. Preserve action/share transformations during delay. Record realized duration separately from frozen five-day targets. Unknown residual assets, obligations or unsupported execution trigger the unchanged strict halt policy; no capital reuse. The assumption is specific to this event and cannot resolve unrelated events by default.

## Proposed authorized sequence after review

1. Implement only this event-specific scenario adapter and focused signed-accounting tests.
2. Recheck the six affected candidate/cohort obligations, including short delivery and prior cash rights; report deliverability, fractions, cash credit, actual execution/delay and unresolved reasons.
3. If focused accounting is sound, rerun development-wide Stage4B feasibility separately for each scenario. Preserve original artifacts; use new scenario output directories and label every result conditional.
4. Stop with feasibility results. Even passing scenarios do not authorize PnL, Sharpe, candidate selection or holdout evaluation. Any later performance stage requires review and the primary measurement gate.

QA: W+F=e; abs(F)<1; sign symmetry; no pre-D execution; no double-counting receivable/cash; immutable caps; first admissible open; canceled entries stay cash; unresolved holdings/borrow remain outstanding; original artifacts and targets unchanged. No performance-derived scenario selection.

Proposed outputs: private data/interim/stage4e_scenarios/<scenario>/ inventory/feasibility/manifest files, safe results/tables/stage4e/ scenario assumptions, cohort status and operational coverage. Event-specific history remains licensed/local. Current deliverable is only proposed_settlement_scenarios.csv; no numerical ledger, new figure or simulation generated. A table is appropriate for a discrete assumption grid.

Review requested: approve or revise the three delivery stress points, hypothetical fixed-quotation M, hypothetical same-D fractional cash credit and processing assumption. None is represented as recovered history.
