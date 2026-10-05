# Stage 2A synthetic feature QA

2026-10-06, RL-044. Approved scope: synthetic/local-fixture QA only.
No historical CRSP rows were read. Stage 1G methodology and targets unchanged.

Reproduce:
- python3 -m pytest tests/test_stage2a_features.py -q
- python3 scripts/21_qa_stage2a_fixture.py

24 tests pass. The output results/tables/stage2a/synthetic_feature_qa.csv has
16 scenario/feature rows for complete and missing-security-row fixtures.
The small table is sufficient for this step; an additional figure would not
improve assessment of fixed positions and missingness. Future material research
sub-stages must separately assess useful descriptive figures/tables.

Overnight gap denominator is the positive observed DlyPrc on the immediately
preceding global calendar date, from that actual security row. It is not an
older available close, source DlyPrevPrc fallback, adjusted close, or future
price. A missing/unverified prior row makes the gap missing. The source anchor
must identify that adjacent date; event-free checks require F=1, O=N=0, no
stored delisting return and verified contemporaneous event status. Intraday
uses current DlyOpen as denominator and positive observed current DlyPrc.

Return admission additionally checks DlyPrevPrc against the observed preceding
close, single-period duration, source reconstruction, and event verification
known by the source close. Synthetic verification fields are explicit evidence
inputs (event_verified, event_known_date, event_type, volume_verified,
cap_verified), not defaults inferred from volume or future target flags.
Nonordinary/received-asset amounts remain conservatively inadmissible; verified
ordinary cash/pure splits are tested. TR is the fixture's actual-price flag;
live CRSP provider-code/event-evidence mapping still requires a bounded local
historical QA and is not claimed to be complete from these fixtures.

Global calendar windows retain missing positions; strict return windows become
missing, liquidity means use >=15/20 observations without shifting boundaries.
Both the dollar-volume shock's prior denominator and the momentum skip exclude
the specified current/recent observations. Warm-up is based on calendar span.
Every feature retains raw value, missing flag, reason, valid count and positions.
Preprocessing preserves raw/clipped/z separately, reasons, finite counts,
cutoffs and constant-section flags. Nonfinite values have explicit invalid
reasons; no filling or model-matrix encoding is performed.

After-t perturbation and label/status independence tests pass. No target mask
changes feature inputs or same-date finite-value samples. Synthetic dates are a
weekday calendar example, not an authoritative exchange holiday calendar.
The real calendar must be supplied independently of security observations.

Ready for a small explicitly bounded historical sample to validate live field
adapters and availability masks. Not approved for full-panel computation;
revision-free historical vintages remain unestablished. No performance metric,
model, portfolio, WRDS query or new source used.
