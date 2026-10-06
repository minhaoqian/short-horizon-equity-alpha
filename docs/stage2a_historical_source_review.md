# Stage 2A historical verification review gate

RL-045, 2026-10-06. No full-panel features constructed. Stage 1G unchanged.

Reproduce bounded audit:
`python3 scripts/22_audit_stage2a_historical_sources.py`

The cache-only sample has 32,010 rows / 275 securities / 124 global market
dates, Nov 2020–Apr 2021. Keys/units and the tested numerical price anchors
pass. However, eight prespecified zero/null-value event records from existing
histories expose two eligible trade/open observations that pass F=1,O=N=0,
non-delisting daily fields while actual events are unknown rights/rights.
Therefore those fields alone cannot supply the fixture's verified-none flag.

The event histories cover only the outcome-selected Stage 1G extraction set.
974 of 4,971 eligible sample keys lie outside that set. This is a coverage
limitation, not permission to omit features. Outcome-derived event-history
coverage must not become a missingness predictor or sample-selection rule.

Review needed: establish globally consistent through-t event evidence and
an admissibility adapter under the approved definitions. If instead adopting
an explicitly daily-impact-only definition, its event treatment and missingness
policy must be approved as a methodological change. Official DlyDistRetFlg is
a potential supporting field, not assumed sufficient; its semantics do not
necessarily certify absence of zero-valued legal rights events. No new WRDS
or source access is authorized/executed in this audit.

Aggregate evidence: results/tables/stage2a/historical_source_verification_qa.csv;
source-coverage visual: results/figures/stage2a/historical_event_history_coverage.svg.
Exact licensed cases and manifest remain local in data/interim/stage2a_historical_qa/.
All 25 synthetic/source regression tests pass. The historical verification gate
does not pass, so full construction remains stopped pending review.
