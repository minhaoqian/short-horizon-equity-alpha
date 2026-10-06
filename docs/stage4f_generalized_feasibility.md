# Stage 4F generalized reservation audit — BLOCKED FOR REVIEW

Date: 2026-10-06. RL-080–082. No portfolio performance computed.

## Approved contract and completed QA

Uniform from-empty2003 quarantine; reserve absolute original **executed** entry notional; separate phase/side budgets, no netting or unsupported release; tighter-side new paired deployment; frozen ranks/caps/ADV/cost/borrow/five-day fallback; grandfather submitted orders. Reference deployment exhaustion is not insolvency or broker-margin failure. Stage4A–E findings remain intact. No Household-specific delivery/cash adapter is used.

Twenty-three focused synthetic tests cover allocation equivalence at zero reserve, signed claims, phase/side isolation, original-entry reference basis, independent-release timing, queued-order overcommitment and unknown propagation. The full relevant suite has160tests. Bounded Jan2–Apr30,2003 historical QA passes for both candidates:40,463 original eligible keys and82 decision dates each;4 unresolved positions each,3long/1short,2security events. All six Household cohorts are generically quarantined; unrelated orders continue afterApr16. End bounded reserves are $60,051.916868 long-origin and $20,961.591096 short-origin per candidate. No phase exhaustion or independent release within this bounded interval. These are budgeting proxies, not wealth.

Safe outputs: results/tables/stage4f/bounded_reservation_qa.csv, entry_basis_gate.csv and results/figures/stage4f/bounded_reservation_qa.png. Private inventories, obligations, claims, orders and date/phase accounting stay under data/interim/stage4f/.

## Material entry-boundary gate

A generic cached-data entry-boundary check found two reversal order keys, two securities, on2006-10-13 and2013-01-29, with `SP / OS / SECDO` events and nonzero `DisFacShr`. These fall outside the already verified pure-parent FRS/SS split transformation. The original queued quantities were fixed at the previous close; a positive post-event open does not independently establish that those pre-event quantities map to executable post-event quantities. Entry-day distribution rights remain excluded, but that does not establish the parent order's share basis.

The first implementation applied only verified pure splits and otherwise retained nominal order shares at entry. That was uncertified for these cases. Full development results generated before detection are explicitly provisional/invalid, not a passing feasibility audit. The audit was interrupted; Ridge's partial processing is not a zero-case finding. A regression guard now stops before assigning executed quantity/notional whenever a non-pure nonzero entry-day share transformation appears. No successor quantity or alternative factor mapping is inferred.

The approved reserve requires original **executed** entry notional. That basis cannot be certified until the queued order's executed quantity is known. Treating it as a missing-open cancellation, silently assuming unchanged quantities, applying every distribution factor as an order adjustment, or substituting planned notional for executed notional would introduce an unapproved convention. This is a generalized order-timing issue, not an individual historical recovery search. No event-specific source search was opened.

## Engineering corrections and reproducibility

The first full run also encountered a calendar IndexError: Stage3A's calendar ends2019, while late development orders have2020 exits/deadlines. Fixed by reading only cached global calendar dates throughJan17,2020. No2020price/event/feature/forecast/target/eligibility records used; pending development-origin holdings remain outstanding at the2019boundary. Yearly terminal journals preserve cross-year retirement states. Cached annual source files are fingerprinted/checksummed and reused; no raw scan, WRDS, authentication or new fits.

Entry point: scripts/36_stage4f_reservation_feasibility.py; reusable reservation, source, audit and report modules under src/portfolio. Full-panel report generation refuses incomplete manifests. Prior artifact hashes were verified unchanged before the approved Stage4F contract was appended to methodology; earlier contract text and Stage4A–E outputs remain unchanged. All licensed security-level outputs remain ignored. No PnL, Sharpe, drawdown, candidate selection or holdout results.

## Review required

Full2003–2019 reserve/exhaustion/release/measurement totals are **not certified**. The bounded accounting framework passes, but full measured-component feasibility remains undetermined at this gate. No synthetic full-book NAV is authorized.

One next action: review a generalized convention for already-submitted orders with unidentified entry-day share-basis transformations. If a separate unresolved-queued-execution state with a planned-notional budget proxy is desired, it must be explicitly approved as distinct from the executed-entry-notional reserve; it cannot certify execution, wealth, funding or termination. Otherwise the executed quantity requires verified evidence before this audit can complete. No convention has been adopted here.
