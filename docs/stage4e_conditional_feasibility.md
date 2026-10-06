# Stage 4E — conditional settlement feasibility complete; full-period gate FAILED

Date: 2026-10-06. Research Log RL-075–077. No portfolio performance computed.

## Frozen interpretation and methodology check

The approved same-date CRSP closing trade is the fixed hypothetical fractional-cash reference, not a certified WSJ quotation or evidence of HSBC's selected historical method. Historical D/M remain unidentified. All three delivery stress scenarios have equal reporting status. Frozen0.535 entitlement, signed whole/fraction decomposition, no netting, pre-open delivery/cash credit, original scheduled+5 cap and strict unknown propagation remain unchanged. Stage4A strictfailure, Stage4B original failure, Stage4C legalratio and Stage4D historical-unresolved records are preserved by hashes; frozen methodology unchanged.

Permitted evidence: signed account identities, effective events, observed positive opens, timing/keys and operational feasibility. Prohibited: PnL, Sharpe, drawdown, candidate selection, target/performance comparisons and holdout evaluation. No new source/authentication, raw scan or quotation search occurred.

## Six original Household obligations resolve under every scenario

The same three obligations occur separately for each candidate. No cohort or long/short offsetting. Whole inventories are381ADS,403ADS and−390ADS; fractional cash claims/obligations are approximately+$12.19142839,+$32.68431665 and−$24.40776389, respectively. Exact Decimal values and all18 scenario/candidate/cohort rows are preserved in the accounting table. Prior parent ordinary cash rights remain attached to the two longs; the later-entering short has no such pre-entry entitlement. Fractional cash is credited once on scenarioD, independently of whole inventory liquidation. No rounding cash to cents has been imposed in accounting.

| Scenario | Original scheduled exits Mar31 / Apr1 / Apr4: actual assumed exits | Delays | Original obligations resolved / unresolved |
| --- | --- | --- | --- |
| D0 | Mar31 / Apr1 / Apr4 | 0 / 0 / 0 | 6 / 0 |
| D2 | Apr2 / Apr2 / Apr4 | 2 / 1 / 0 | 6 / 0 |
| D5 | Apr7 / Apr7 / Apr7 | 5 / 4 / 1 | 6 / 0 |

Realized merger holding durations are5/5/5,7/6/5 and10/9/6globaltradingdays, respectively. The cap dates remain April7/8/11. No delayed holding is described as an exact five-day realization; Stage1 targets remain untouched.

## Development-wide continuation result

All68forecast checksums and frozeninputfingerprints verified; original3,829,908developmentkeys and4,279decisiondates retained as denominators. Each of six chronological runs processes35,328eligible pre-halt keys and submits13,770nameorders. Post-halt orders are not created. The failure witness makes later price scanning unnecessary: remaining development dates are explicitly halted under the existing no-certified-resumption policy. The audit does not claim those post-halt dates were traded, nor that a real historical account never settled.

Every scenario/candidate retains one unresolved long position in parentPERMNO18382, linked successor21936, from an April16OS/SP/SECMRG event. EntryApr14, scheduledexitApr22, originalcapApr29. Received quantity/terms are unsupported by the event-specific Household adapter. Last verified quantity, prior claims and unresolved state are retained; successor quotes cannot recover quantity. Do not apply0.535 to another merger or invent settlement. No independent account-resumption certificate is established by this adapter.

| Scenario | Candidate | Remaining unresolved | First halt close | Operational dates / development denominator | Full-period execution/accounting feasible |
| --- | --- | ---: | --- | --- | --- |
| D0 | Reversal | 1 long | 2003-04-16 | 72 / 4,279 (1.682636%) | No |
| D0 | Ridge | 1 long | 2003-04-16 | 72 / 4,279 (1.682636%) | No |
| D2 | Reversal | 1 long | 2003-04-16 | 72 / 4,279 (1.682636%) | No |
| D2 | Ridge | 1 long | 2003-04-16 | 72 / 4,279 (1.682636%) | No |
| D5 | Reversal | 1 long | 2003-04-16 | 72 / 4,279 (1.682636%) | No |
| D5 | Ridge | 1 long | 2003-04-16 | 72 / 4,279 (1.682636%) | No |

Already submitted entries onApr16remain honored. First blocked entry from a new decision isApr17. Unknown remaining inventory triggers the integrity halt before its scheduled exit/cap; this is not a shorter fallback window. Under the strict continuation policy the unresolved state persists through the development endpoint. No residual-reservation approximation or new termination assumption.

Reversal:13,765marketexits+2measurablecashterminations+2canceledentries+1unresolved=13,770. Ridge:13,761marketexits+6cashterminations+2canceledentries+1unresolved=13,770. Canceled plannedclose-sizedentrynotional is$40,816.33/$41,707.40, respectively, in every scenario. This is not realized PnL or an executed turnover amount.

| Scenario/candidate | Delay0 | Delay1 | Delay2 | Delay3 | Delay4 | Delay5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D0 Reversal | 13,762 | 3 | 0 | 0 | 0 | 0 |
| D0 Ridge | 13,760 | 1 | 0 | 0 | 0 | 0 |
| D2 Reversal | 13,760 | 4 | 1 | 0 | 0 | 0 |
| D2 Ridge | 13,758 | 2 | 1 | 0 | 0 | 0 |
| D5 Reversal | 13,759 | 4 | 0 | 0 | 1 | 1 |
| D5 Ridge | 13,757 | 2 | 0 | 0 | 1 | 1 |

These are market-exit counts; cash termination, canceled and unresolved paths are separately reported. No preferred scenario designated.

## Implementation, QA and outputs

Reusable adapter src/portfolio/settlement.py; audit settlement_audit.py; descriptive report settlement_report.py; entrypoint scripts/35_stage4e_settlement_feasibility.py. Yearly cached projections are shared across scenarios. No2020sourceprice/event rows needed because all books fail in2003; only globalcalendar dates needed for possible authorized runoff are read, never2020signals/outcomes.

137fulltests pass (18new focused tests). Historical QA verifies reference row uniqueness/date/TR/exactfixedvalue, signed identities, no fractional trade, separate claims, fixed credit once, exact focused-versus-chronological six-obligation agreement, unchanged pre-merger orders/quantities, first admissible opens, cap/duration identities, zeroremaininginventory after certified marketexit, unique keys,4,279datedstates each and exactorder reconciliation. Initial date-dtype merge and credited-claim metadata requeue bugs were corrected; credit-date assertion failed before final outputs, then passed after correction. No methodological change. Earlier artifacts/hash checks pass. Figure visually inspected; safe code/output diff reviewed; licensed histories/inventories remain ignored.

Safe reproducible outputs under results/tables/stage4e: conditional_merger_cohort_accounting.csv, conditional_feasibility_summary.csv, conditional_exit_delay_distribution.csv, conditional_holding_durations.csv and conditional_unresolved_summary.csv. Figure results/figures/stage4e/conditional_execution_feasibility.png is execution availability only. Private data/interim/stage4e_scenarios: focused obligations, per-scenario/candidate orders, claims, unresolved positions, operational states and feasibility manifests. No licensed source rows committed.

## Stop

The authorized feasibility substage is complete. All scenarios still fail full-period accounting; no PnL/Sharpe/drawdown/candidate selection authorized or computed. Stop for research-lead review of the newly blocking April16merger evidence gate. Do not expand the exit cap or invent a second settlement assumption.
