# Stage 4B execution-feasibility result — gate failed

2026-10-06; RL-065–066. A portfolio simulation under prespecified execution assumptions, not observed historical execution. Execution-feasibility audit COMPLETE; Stage4B OPEN / corporate-action quantity gate. No PnL, Sharpe, candidate returns or selection calculated.

## Actual simulation orders before persistent halt

| Measure | Reversal | Ridge |
| --- | ---: | ---: |
| Submitted name orders | 11,368 | 11,368 |
| Missing scheduled entries, assumed canceled | 2 short | 1 short |
| Canceled planned entry notional (close-t basis) | $40,816.33 | $21,505.38 |
| Missing scheduled parent exit opens | 8 | 10 |
| First admissible exit at delay1 | 3 (2 long,1 short) | 1 long |
| Exits resolved at delay2/3/4/5 | 0/0/0/0 | 0/0/0/0 |
| Independently measurable cash replacements among missing parent opens | 2 long | 6 long |
| Unresolved execution/received-quantity positions | 3 (2 long,1 short) | 3 (2 long,1 short) |
| Unresolved positions with no parent open through all0–5 attempt dates | 3 | 3 |
| Distinct affected parent PERMNOs, all execution exceptions | 6 | 5 |
| Distinct unresolved parent PERMNOs | 1 | 1 |
| First halt decision close | 2003-03-31 | 2003-03-31 |
| First blocked new-entry open | 2003-04-01 | 2003-04-01 |
| Operational development decision dates | 60 /4,279 (1.402197%) | 60 /4,279 (1.402197%) |
| Independently proven resumption through2019 | None | None |

Canceled entry notional is the planned decision-close allocation, not an unavailable actual opening value or a loss. Cancelations do not chase/reallocate the amount; no change to Stage4A's distinct unknown-fill interpretation. All queued orders submitted before the halt remain; canceled orders here use only the approved Stage4B no-fill assumption. Counts refer to actual submitted simulation orders; no hypothetical post-halt orders or full-period counterfactual strategy results. The entire development calendar is classified operational/nonoperational after this persistent gate.

## Remaining limitation and five-day cap

The same parent is converted to a successor stock under a March31 distribution event (paymentOS/typeSP/detailSECMRG). Three pre-existing cohorts per candidate are affected. The cached record links the successor but does not establish a verified received-share quantity under the frozen ledger. Parent DisFacShr=-1 is not interpreted as zero successor assets or a verified received ratio. Preserve last verified parent quantities, owned prior-share entitlement records, successor identifier, unknown received inventory and short delivery obligations. No cross-netting, amount/price inversion or later-price repair.

Scheduled exits2003-03-31,04-01 and04-04 have fixed cap deadlines04-07,04-08 and04-11 respectively. No positive parent open appears on their scheduled dates or next five global dates. That is not proof the successor lacks prices: **quantity and asset identity must be verified before a successor opening can liquidate the position.** These three positions remain unresolved through their caps. Strict remaining-quantity propagation already halts at closeMarch31, when the unverified exchange takes effect; this is an earlier corporate-action integrity gate rather than a discretionary change to the five-day fallback. Existing positions and obligations remain unresolved. Later cached parent/successor security event histories do not establish the missing original inventory or an independent account termination certificate; no certified resumption through2019.

The January13 missing opening which halted the strict Stage4A book instead assumes exit at the first subsequent global open,January14, under Stage4B. That resolves this execution scenario, not Stage4A identification. Their artifacts, source assertions and limitation remain untouched and protected by checksum checks.

## Realized holding durations and accounting distinction

Market-liquidated reversal positions: 11,358 at5 global days,3 at6. Ridge:11,357 at5,1 at6. None at7–10 in actual pre-halt orders. Canceled entries and unresolved positions receive no realized liquidation duration.

Cash replacement dates are separate security-event states: reversal1 at3days/1 at5; Ridge1 at2/3 at3/2 at5. These are durations to parent cash conversion, not claimed observed market executions or the final settlement of every retained fixed receivable. Established claim/payment terms are retained independently; no reinvestment or second recognition of cash on payment. Gross/net wealth and cash-income performance are not computed by this audit.

## QA and reproducibility

114 repository tests pass, including11 new fallback tests: first rather than best opening; delay1–5 on fixed global positions; no sixth-date extension; missing entry cancel; administrative calendar censoring; verified pure split versus received asset; and a positive successor quote not establishing unknown quantity. Historical QA independently verifies every assumed market exit is the first positive opening within its allowed window; duration=5+delay, no canceled actual entries, unique keys, complete order/state reconciliation and4,279 operational rows per candidate. Grouped cash replacement terms reconcile contemporaneous daily dividend sums and matched final-cash event amounts. Through-date share/event records and signed obligations retained locally, not treated as forecasts.

All68 forecast checksums and existing frozen source fingerprints checked;3,829,908 original development keys unchanged. Orders built from close-t forecast/price/ADV only; no target values/status used in allocation. First-quarter source projection supplies all actual pre-halt entries, delays and queued exits throughApril11. No new source scan/download/WRDS or2020record access necessary. Rejected post-halt new orders are represented by the full decision-calendar mask and unchanged original signal source, not silently disappearing eligibility. Stage1 labels and Stage4A strict report/table/figure/manifest protected read-only.

Reproduce scripts/33_stage4b_execution_feasibility.py. Licensed orders/decisions/event-ledger terms/source histories/manifest under data/interim/stage4b/ remain ignored. Safe aggregate tables under results/tables/stage4b/: summary, operational states, states/affected states by side, exit delays, holding durations, unresolved event summary and cap deadlines. Non-performance figure under results/figures/stage4b/execution_feasibility.png.

**Stop for review:** execution-feasibility did not pass. Do not compute portfolio performance/selection, expand the five-day cap, substitute prices or assume successor quantities. Exactly next action: research-lead review of verified successor-quantity recovery for the blocking corporate event. The prescribed fallback and permanent Stage4A limitation remain unchanged.
