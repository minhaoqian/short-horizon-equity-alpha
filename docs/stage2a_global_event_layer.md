> Superseded timing decision: RL-048–RL-050 approve effective-date admission
> with contemporaneous daily reconciliation. DisDeclareDt is QA metadata, not
> a hard availability timestamp. The historical review below preserves RL-047;
> current rules/results are in docs/stage2a_completion.md.

# Stage 2A global event evidence and timing review

2026-10-06, RL-046–RL-047. Existing feature and frozen Stage 1G definitions
remain unchanged. Global source coverage is established; temporal verification
is not yet sufficient to authorize full feature construction.

## Reproduction and local source files

- scripts/23_extract_stage2a_events.py: default plan only; --execute requires
  an explicitly authorized username, exactly one login and Duo. Complete cache
  skips authentication; prior authentication failure forbids automatic retry.
- scripts/24_qa_stage2a_global_events.py: offline global-scope/bounded adapter QA.
- src/features/events.py: per-security (start,end] effective-date index, requires
  end <= as_of; explicit true/false/REVIEW decisions, not automatic imputation.

Ignored directory data/interim/stage2a_events contains complete stkdelists.parquet
(29,833 rows, reused checksum-verified full source) and stkdistributions.parquet
(670,977 rows, all securities, DisExDt 1993–2025). Four disjoint extraction batches
retain all event types and zero/null amounts, independent of labels/eligibility.
Four observation queries completed on one WRDS login/session, which closed cleanly.
No raw daily scan or daily-data download. DisDeclareDt was added from the already
confirmed provider schema as supporting timing evidence, not an assumed perfect
point-in-time publication timestamp.

## Adapter boundaries

Only effective ex-dates within (start,end] and <= as_of are indexed. Later
payments, eventual settlement amounts/returns/statuses and outcome fields are
not admission inputs. Source coverage is global, never Stage 1G subset membership.
Rights, unknown-rights, property and received securities are retained as actual
events even when daily factors/dividend amounts show zero impact. Absence of event records
within a fully covered interval establishes dated absence; incomplete coverage
returns REVIEW. Verified ordinary cash and same-security splits have separate
admission checks; legal events still exclude the event-free gap. Split price/share
factors must agree before certification; cash publication timestamps may be unknown.

DelistingDt is a last-followed-exchange-price boundary, not a public announcement
timestamp. The adapter does not retrospectively mask that earlier day using the
future last-price designation. Stored-return intervals use DelDlyDt alongside
the existing daily flag checks; later DelAmtDt/DelRet cannot change earlier
admissibility. No claim of historical publication-vintage completeness is made.
These rules are evidence-layer checks; no population feature/missingness matrix
has been constructed from the adapter.

## Verified scope and unresolved timing

The bounded 32,010-row / 275-security / 124-market-date source sample remains
intact (4,971 close-date eligible keys). Both original eligible rights/unknown-
rights counterexamples are found by the global event index. The 974 previously
uncovered eligible sample keys no longer inherit missingness from a target-
selected extraction scope. No target value or label-status filter is read.

The local official CRSP CIZ User Guide (July 2026), pp. 12–13, defines
DisExDt as the first trading date without distribution rights and DisDeclareDt
as the board declaration date; neither is documented as a database publication
or revision timestamp.

However, global data have 109 records with DisDeclareDt > DisExDt, including
81 ordinary cash CDIV and 10 special cash SDIV records. A bounded first-20
cash-event chronology probe finds the corresponding amount already in daily
fields on the earlier ex-date in all 20 cases; one is an eligible observation.
This does not prove that investors lacked earlier information: metadata errors,
later restatements or retrospective dating are not distinguishable from these
fields. It does prevent assuming a verified through-close amount/admission time.
Another 61,542 records lack declaration dates; this count includes all event
kinds, not only ordinary cash, and does not itself prove a look-ahead issue.

Conflicts return REVIEW instead of silently choosing an effective-only rule,
forcing a blackout, or inventing historical cash information. Required review:
clarify the authoritative information-time interpretation and treatment of
conflicting/missing declaration dates while preserving the approved feature
families. Do not reintroduce the rejected daily-impact-only alternative or
use a future-derived exception mask as a predictor.

## Evidence outputs/tests

Safe aggregate tables: results/tables/stage2a/global_event_verification_qa.csv
and bounded_global_event_adapter_reasons.csv. Reproducible visual:
results/figures/stage2a/global_event_declaration_chronology.svg (log count widths,
explicit record-count labels; no predictive metric). Exact cases and QA manifest
stay licensed/local in data/interim/stage2a_events/adapter_qa_manifest.json.

All 59 repository tests pass. The broader first run exposed two stale uppercase
fixture/default-lowercase schema mismatches; fixtures now explicitly map CIZ
columns and separately test WRDS lowercase defaults, without production changes.
No full-panel features, preprocessing or predictive evaluation executed.
