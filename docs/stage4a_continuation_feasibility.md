# Stage 4A strict continuation-feasibility audit

2026-10-06; RL-063–064. Feasibility audit COMPLETE. Stage 4A full-period portfolio evaluation remains OPEN / not identified under the strict execution policy.

## Approved rule and evidence gate

Halt new orders from the decision close when a scheduled exit's execution/remaining quantity is unresolved. Retain all holdings, claims, liabilities and borrowing; no capital reuse, residual-reservation approximation, order cancellation after submission, price substitution, filling or horizon shift. Only independent termination of the account position/obligations permits resume. This audit projects no candidate returns or target return values and calculates no PnL, Sharpe, cost performance or selection differences. Frozen Stage1–3 contracts unchanged.

## Development-wide result

| Measure | Reversal | Ridge |
| --- | ---: | ---: |
| First unresolved scheduled exit | 2003-01-13 | 2003-01-13 |
| Halt decision close | 2003-01-13 | 2003-01-13 |
| First blocked new entry open | 2003-01-14 | 2003-01-14 |
| First affected position | Long | Long |
| Observed entry notional | $22,149.00 | $22,149.00 |
| Valid-entry unresolved exit cases actually submitted | 1 | 1 |
| Additional pre-submitted unknown entry/quantity cases | 0 | 1 (short) |
| Total unresolved scheduled-exit or quantity states | 1 | 2 |
| Distinct affected PERMNOs | 1 | 1 |
| Decision dates permitting new primary orders | 7 / 4,279 | 7 / 4,279 |
| Tradable decision-date fraction | 0.163590% | 0.163590% |
| Independent resumption established through 2019-12-31 | No | No |

Initial long: signal2003-01-03, entry2003-01-06, plannedexit2003-01-13. Both exit open and close missing; missing measurement does not prove an unfilled order. First seven permitted decision dates are2003-01-02/03/06/07/08/09/10. Orders submitted closeJan10 for openJan13 remain; they are not retrospectively canceled. Ridge's already-submitted Jan10 short in the same PERMNO has an unmeasured Jan13 entry and plannedJan21 exit; neither its entry notional nor remaining quantity is invented. Conservative gross accounting does not net this uncertain short against the long. The valid-entry exit count and the unknown-entry quantity count are deliberately separate.

Each unresolved state persists for 6,196 elapsed calendar days and affects 4,272 development decision dates, right-censored at2019-12-31. “Permanent halt” here means no independently recoverable resumption during the observed development period, beginning2003-01-13, not proof of perpetual nontermination after2019. Existing holdings/claims remain accounted as unresolved; no zero wealth or zero borrowing assumption.

## Later independent event evidence

The complete cached event histories contain one later delisting record and two distribution records for this security during the remaining development period. Actual delisting date2011-04-08, stored/amount dates2011-04-11; payment formCSHN, completionFPAY. This establishes a later cash-and-stock security event, not this account's2003 exit fill, remaining ownership, successor inventory, cash receipts or termination of all liabilities. A security-level final-payment flag is not a certificate for an account whose quantity is unknown. Therefore it does not lift either halt. Later quoted prices/trading are not used as replacement execution prices or proof of liquidation. No missing/new event extraction needed to reach this identification conclusion.

## Audit construction and scope

All68 frozen forecast hashes and existing frozen input fingerprints verified. 3,829,908 original2003–2019 eligible keys /4,279 decision dates reconcile without duplicates. Score-only projection excludes label returns, holdout signals and other models. Outcome metadata enter only after order construction for execution-state audit.

Primary pre-halt decisions retain all keys/reasons. Capped ranks/close-t share sizing use the first seven decision dates. Scheduled gross parent flow is conservatively reserved before known cash conversion; capacity is demonstrably nonbinding for these selected entries, with every allocation agreeing with the independent zero-flow bound. Supported through-close pure splits preserve share basis; cash/ordinary event records are not mistaken for proof of a future trade. This is an identification audit, not a completed wealth ledger.

Full-development counterfactual rank-screen inventories are also published, expressly **not submitted orders or a full virtual portfolio**. Potential valid-entry unresolved exits: reversal718, Ridge744; other corporate paths433/426; missing entries420/523 respectively. They do not enter strict-primary counts because the primary books have already halted. These screen counts are not screened on future numeric-label availability, not performance evidence, and do not certify allocations, quantities or executed capacity after the halt.

No new full virtual scheduled-book study was needed after identifying the early persistent halt. No WRDS login/query, raw-file scan, new forecast fit or2020 record access. Existing development-label endpoint metadata may describe planned exits in2020; no2020 signal/source rows were opened. No runoff extraction is necessary for the halted primary book.

## QA, artifacts and stopping decision

103 repository tests pass, including four new strict-state tests for decision-close timing, certificate-only resumption, multiple unresolved obligations and chronology/calendar integrity. Non-performance figure visually verified.

Reproduce: scripts/32_stage4a_continuation_feasibility.py; reusable src/portfolio/continuation.py and continuation_report.py. Private licensed decisions/endpoint-state inventories/later events/manifest: data/interim/stage4a_continuation/. Public aggregate tables under results/tables/stage4a/: continuation_feasibility_summary, unresolved_durations, decision_states, later_event_evidence, pre_halt_capacity_qa, submitted_order_inventory and virtual_rank_screen. Figure: results/figures/stage4a/continuation_feasibility.png (permission timeline, not returns).

**Stop:** full-period primary portfolio performance is not identified under this strict policy. Headline PnL/Sharpe/drawdown and candidate selection are unavailable and were not computed. The approved feasibility audit is complete; Stage4A overall remains open. Exactly next action: research-lead prespecification/review of a separate execution-assumption stage before any full-period portfolio performance claim. No execution assumption is invented in this audit.
