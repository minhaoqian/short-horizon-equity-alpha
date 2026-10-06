# Stage 4F generalized reservation feasibility — COMPLETE / measurement review required

Date: 2026-10-06. Research Log RL-083–085. Conditional simulation under a generalized unresolved-position reservation convention. No PnL, Sharpe, drawdown, candidate selection or holdout results computed.

## Methodology and implementation

Uniform policy applied from the empty 2003 book to both frozen development signals. No Household/Stage4E settlement exception; Stage4A–E findings and the RL-082 queued-entry gate remain permanent historical records. Missing scheduled opens, verified splits, normal cash claims/terminations, first-positive-open exit fallback, five-global-date cap, ranks, absolute name caps, ADV flow and cost/borrow conventions are unchanged.

Verified executed entries later becoming unresolved reserve absolute original executed entry notional. Already-submitted entries with unidentified post-event share quantity instead become `queued_execution_quantity_unresolved`: original queued order, identifiers and event reasons retained; executed quantity/notional, execution state, wealth, claims/obligations and required borrow/cost bases remain unknown. Their original decision-close dollars form a separate `planned_notional_reserve_proxy`. Neither reserve is wealth, exposure, collateral, NAV, PnL, a loss bound or a termination value.

Separate phase/side arrays track both reserve bases; total commitments reduce reference deployment without netting or recycling. Tighter-side remaining allowance governs equal new long/short allocation within the frozen selected pools. Known retained positions and queued commitments stay separate. Already-submitted orders are honored; opening overcommitments are recorded, not erased. Unrelated positions continue. Independent complete account evidence is required for a reserve release; later prices/security flags/payment metadata do not suffice. No individual event recovery search.

## Full development audit

Both candidates preserve **3,829,908 unique original keys** on **4,279 decision dates**, 2003-01-02 through2019-12-31. Every submitted order reconciles to one terminal, unresolved, live or pending state; no duplicated order terminal keys. Forecast checksums68/68 and cached-source fingerprints verified. Quarantine budget identities, separate reserve bases and tighter-side allocation checks pass.

| Measure | Reversal | Ridge |
|---|---:|---:|
| Unresolved positions | 828 | 840 |
| Distinct securities | 319 | 362 |
| Distinct security/recognition dates | 328 | 370 |
| Corporate-action positions, verified original entry | 814 | 828 |
| Ordinary capped-exit failures | 12 | 12 |
| Unresolved queued executions | 2 | 0 |
| Unresolved long / short cohorts | 344 / 484 | 461 / 379 |
| Ending executed-basis reserve | $7,714,314.10 | $8,015,526.44 |
| Ending planned-notional proxy | $20,724.42 | $0.00 |
| Total long-origin reference commitments | $3,246,984.61 | $4,432,835.36 |
| Total short-origin reference commitments | $4,488,053.91 | $3,582,691.08 |
| Raw combined commitment / N | 77.3504% | 80.1553% |
| Paired-budget reserve / N | 44.8805% | 44.3284% |
| Remaining paired reference allowance, before retained commitments | $5,511,946.09 | $5,567,164.64 |
| Unmatched undeployed side allowance, before retained commitments | $1,241,069.30 | $850,144.28 |
| Supported reserve releases | 0 | 0 |
| Dates permitting new paired deployment | 4,279 / 4,279 | 4,279 / 4,279 |
| Phase or candidate reserve-budget exhaustion | None | None |

Reversal's queued proxies are $9,690.67 long-origin in phase4 and $11,033.74 short-origin in phase2; neither has numeric executed quantity/notional. These are not verified fills. Ridge's zero queued category is a complete audit finding, unlike the earlier partial scan. Reserve-backed deployments are budgeting assumptions and cannot certify total-book neutrality, solvency or margin. No reference deployment exhausted; even if it had, that would not establish economic insolvency or broker-margin failure.

Phase/side paths include executed reserves, planned proxies, retained commitments, tighter-side allowances, new paired orders and post-decision reference usage. Annual tables preserve full development calendar denominators. Same-security parent/linked locks change execution capacity only; no reranking, future eligibility selection or label-status filtering.

## Measurement and continuation limits

| Availability measure | Reversal | Ridge |
|---|---:|---:|
| Asset-component interval count | 8,331,282 | 8,356,712 |
| Wealth-measurable interval fraction | 80.5789% | 79.9866% |
| Complete wealth + expense-input interval fraction | 80.1143% | 79.4989% |
| Expense-input-measurable interval fraction | 99.4740% | 99.5116% |
| Identified verified-entry-basis fraction | 78.5504% | 77.7083% |
| Opening overcommitment phase/side/date rows | 12,491 | 11,613 |
| Queued-increment overcommitment rows | 2,549 | 2,446 |
| Maximum opening side overcommitment | $107,553.29 | $111,017.79 |

Interval counts include persistently unresolved obligations; unknown wealth does not become zero. Verified-entry-basis coverage excludes unmeasured executed notionals; planned proxies are separately reported and never inserted into that denominator. These fractions are neither market-value coverage nor evidence of random missingness. Expense availability records known fixed-basis inputs separately from unmeasured execution/wealth; an unknown queued short has an unknown executed borrow basis rather than a fee computed from its proxy.

All unresolved durations are right-censored at2019-12-31: minimum22, maximum6,119 calendar days; medians2,405 reversal and2,737 Ridge. No termination is inferred from persistence. Descriptive coverage declines as unresolved commitments accumulate; that is not a strategy return or drawdown.

At the audit boundary, reversal retains1,839 verified positions and378 pending development orders; Ridge1,823 and366. They are not forcibly liquidated or reassigned. Only global calendar dates were extended into2020 to index development deadlines; no2020price/event/feature/forecast/target/eligibility outcomes were read. Any later runoff measurement must retain the separately authorized narrow development-origin scope.

Conditional measured-component analysis is technically feasible, subject to a separate reporting/measurement review. Full-account wealth remains unidentified for both candidates. No synthetic full-book NAV, headline historically observed executable Sharpe, full-book drawdown or candidate-selection claim can follow from measured pieces.

## QA, reproducibility and outputs

28focused reservation tests and **165full-suite tests pass**. Synthetic tests cover unknown queued state, no inferred fills/fees, mixed reserve bases, independent release requirements, no side/phase/cohort netting, frozen zero-reserve allocation equivalence and grandfathered orders. Bounded Jan–Apr2003 QA also passes. An additional validator initially attempted to access optional queued-state fields in Ridge's empty queued category; corrected the empty-category check, then reran full aggregate/key/budget/state QA. No source inconsistency or policy change.

Entry point: `scripts/36_stage4f_reservation_feasibility.py`; reusable modules under `src/portfolio/`. Annual caches reused; no raw scan, WRDS, login, new model or performance. Prior Stage4A–E artifacts unchanged. The failed prior full audit remains privately archived as `data/interim/stage4f/development_entry_gate_provisional/`; approved rerun outputs under `data/interim/stage4f/development/`. Licensed orders, inventories, obligations, claims, interval records and manifests remain local/ignored.

Safe reproducible tables under `results/tables/stage4f/`: feasibility_summary, annual_reservation_coverage, phase_end_state, queued_execution_summary, quarantine_categories, opening_overcommitments_annual, execution_input_coverage, unresolved_duration_summary, report_manifest. Large aggregate daily_reservation_coverage and phase_reservation_path stay local/ignored but reproducible. Figure: `results/figures/stage4f/reservation_measurement_paths.png`, visually checked; contains reference commitments/allowances and measurement coverage only. Earlier bounded QA and entry-gate artifacts remain separate historical evidence.

Next action: research-lead review of the full reservation/measurement results and the permissible conditional measured-component reporting protocol. **Stop before performance computation.**
