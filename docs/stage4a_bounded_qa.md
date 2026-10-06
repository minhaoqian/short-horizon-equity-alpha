# Stage 4A bounded accounting QA — continuation review gate

2026-10-06; RL-061–062. Stage 4A OPEN. No portfolio performance computed.

## Implemented and verified

Reusable capped rank allocation and strict signed-wealth/cost primitives under src/portfolio/; executable bounded diagnostic scripts/31_stage4a_bounded_qa.py. Full repository suite: **99 tests passed**, including twelve focused synthetic tests: capped redistribution/order invariance, dollar-neutral plans versus opening-gap drift, ties, gross flow budgeting, replacing linear-cost scenarios, ACT365 borrow, five-calendar-position phases, entitlement boundaries, signed split/cash accounting, unknown propagation and receivable settlement.

Cached first two signal dates2003-01-02/03: 923 original keys per candidate,360 planned orders per candidate; all keys/reasons retained. No prior sleeve exits due, so initial gross-capacity inputs are exactly zero, not guessed. Decisions depend only on stored forecast/close/ADV fields; endpoint outcome join follows decisions solely for accounting QA. No new fit, raw scan, WRDS or 2020 record accessed.

## New continuation-policy ambiguity

Both candidates choose the same security on2003-01-03. Positive observed entry at2003-01-06; planned exit2003-01-13 has neither open nor close. No distribution/delisting records during the bounded interval establish replacement cash or a share change. Planned notional $22,222.22 and observed entry notional $22,149.00 per candidate. Existing frozen label reason missing_exit_open_no_flag. These are measurement diagnostics, not returns. A missing mark does not establish that the exit failed; the residual inventory/exit fill is unknown.

This expected missing-label case alone would merely fail the headline measurement gate. The additional issue is how to execute subsequent deterministic sleeve replacement: five scheduled sleeves do not guarantee only five actual exposure vintages when exit execution is uncertain. Future borrowing termination, residual risk/capital commitments and ability to reuse that sleeve cannot be proven from the unavailable exit observation. The current approved rules retain unknown assets and forbid horizon-shifting/substitution, but do not specify whether to reserve bounded residual commitment, halt new primary trades, or continue a separate virtual schedule under an explicit continuation assumption. No option has been silently implemented. No automatic exit retry or later-price substitution.

## Review options

Recommended conservative primary policy: halt new primary orders for the affected candidate from the first decision close when the unresolved execution/quantity state is known (not retrospectively canceling orders already submitted for that opening), retaining all existing assets/obligations and unknown accounting; do not assume liquidation or zero return. A later independent scheduled-sleeve diagnostic may continue only as an explicitly conditional virtual-book study, not the live-book/headline strategy. This halt rule is a proposed material extension, not approved or executed retrospectively.

Alternative: approve a deterministic conservative residual-reservation rule (with quantity bounds, participation/position-cap treatment, capital allocation and borrowing implications) before continuation. It can reduce deployable gross and thus requires research-lead approval. Ordinary missing impact inputs can propagate unknown cost without changing inventory; distinguish them from unknown execution.

Public evidence: results/tables/stage4a/bounded_accounting_gate.csv. Private full keys/orders/witnesses/manifest: data/interim/stage4a/. Aggregate notional table is sufficient at this review gate; no misleading performance figure. Full-panel implementation and runoff remain pending; no selection/Sharpe/PnL, frozen contracts unchanged.
