# Stage 4G — conditional measured-component reporting

2026-10-06. Implementation under the research-lead-approved protocol; final
synthesis review required before any further research action.

## Interpretation comes first

Stage4A strict identification failed; Stage4B's five-date fallback failed on
unverified successor inventory. Stage4C recovered legal entitlement only;
Stage4D could not identify historical delivery/cash-in-lieu settlement.
Stage4E's equally reported hypothetical cases resolved the first merger but
all halted at the second event on2003-04-16. These results remain unchanged.
Stage4F permits continued reference-budget deployment using quarantine and
separate executed-entry/planned-notional commitments. It does not establish
actual funding, neutrality, margin or solvency. Reserves are not wealth.

Every Stage4G numerical result is a **conditional simulation under a generalized
unresolved-position reservation convention**. Full-account wealth and its
market-value coverage denominator remain unidentified. Unknowns are not zero;
no synthetic NAV, full-book Sharpe, drawdown or candidate choice is produced.
The complete-ledger prerequisite of the old candidate-selection rule is unmet.
No defensible full-book finite wealth bound is established from reserve proxies,
particularly for unknown short quantities/obligations.

## Reproduction and economic partition

- `scripts/37_stage4g_measured_components.py --end 2003-04-30`: bounded accounting QA.
- `scripts/37_stage4g_measured_components.py`: full frozen-order development replay.
- `scripts/38_report_stage4g_components.py`: journal reconciliation, tables and figures.
- `python -m pytest -q`: repository tests, using the existing project environment.

Reusable logic is in `src/portfolio/measured_components.py`, `measured_replay.py`
and `measured_report.py`. Stage4F orders are replayed without refitting, reranking,
new sizing or availability filters. Durable terminal snapshots are QA expectations
only; execution/event/quantity decisions are computed first from contemporaneous
cached inputs. Previous-close gross planned security flow (no sleeve netting),
ADV and raw sigma determine impact inputs. Fixed6bp/.10impact/100bpACT365 borrow
remain unchanged. Verified entry and actual assumed exit fees post at their
opening; entry principal is not income. Previous-open-to-current-open signed
asset increments transport verified splits and exclude entry-day entitlements.
Established cash rights use prior owned shares and are recognized once.
Verified cash replacement separates the prior parent component from its signed
claims exactly once. Payment is a cash/claim transfer, never a second gain.

Quarantine produces neither a write-off nor a transfer at reserve value. Unknown
asset/claim residuals stay null permanently; known expenses/claims remain
identified. Missing adjacent marks are not bridged by later prices. Known original
short-entry borrow bases persist through unresolved states. The two unknown queued
executions retain null fees/borrow bases, never planned-proxy estimates. Exit-cost
obligations whose executions are unidentified are disclosed as unknown rather
than invented daily trades. Claim cash-state/payment histories remain in the
unchanged Stage4F journals; Stage4G posts economic entitlements, not cash receipts
as new income.

All4278 reporting dates2003-01-03–2019-12-31 per candidate are retained. The empty
Jan2 initialization is not an extra performance observation. All3,829,908 original
development decision keys/4279dates and forecasts/orders remain unchanged. Late2019
inventory and queued development orders remain outstanding, with no forced close,
new horizon or2020 outcome access. This is a calendar contribution report, not a
completed-lifetime report for all signal cohorts.

## Coverage and nominal statistics

Daily/annual tables report original calendar/order denominators, required asset
cohort intervals, identified/complete interval counts, verified-entry-basis coverage
and separately unknown planned proxies, signed fixed entitlements, expense counts,
unresolved asset/claim bundles and exit-cost obligations, unknown borrow bases,
raw/paired reserves and unmatched allowance. Asset/claim unknown counts use one
coupled cohort bundle per unresolved position; splitting identified cash pieces
does not inflate asset coverage. Annual coverage is a ratio of summed counts.
These count/original-entry-basis fractions are proxies, not market-value fractions.
Known-cost primitive coverage differs from complete wealth coverage and does not
certify complete modeled fees on an unverified book.

All ratios use fixedN=$10m. Mean and sample SD use numeric identified daily net
subtotals with n/T disclosed; no surviving-capital denominator, coverage rescaling,
favorable date selection, clipping or compounding. Dispersion scaling is labeled
**annualized SD of conditional measured-component daily contribution**. Bartlett
HAC20 (primary) and HAC4 (fixed sensitivity) use original-calendar positions,
including masked scores for null aggregate dates without zeroing ledger values.
Every summary is **nominal inference for the conditional measured-component mean**,
not full-strategy significance or full net alpha. Inference cannot correct
nonrandom missingness, changing component composition or nonstationarity.

## Outputs

Local licensed journal and manifests: `data/interim/stage4g/{bounded,development}/`.
Security/cohort primitive rows remain ignored and uncommitted. Public compact
aggregate tables: `results/tables/stage4g/`; four reproducible descriptive figures:
`results/figures/stage4g/`. The large aggregate daily calendar CSV is local/ignored.
Strict findings are first-class; contribution figures contain aligned coverage
and reference-commitment panels. No cumulative wealth or strategy equity figure.

Final audit counts and conditional statistics are appended after completion.

CRSP inputs are static extracts, not complete historical revision-vintage records.
Identified component amounts remain conditional on the frozen opening-price,
borrow-access, event-term and cost assumptions; they are not broker fills,
settlement confirmations or actual invoices. The original source-vintage and
measurement-selection limitations therefore remain, even where arithmetic passes.

## Final accounting and conditional summaries

Stage4G implementation COMPLETE; stop for final research-lead synthesis. RL-088–091.

Each candidate retains4278/4278 reporting rows and numeric identified subtotals; this does not imply fully measured wealth. Stage4F original3829908keys/4279decisiondates, all68forecast hashes, every execution key/notional, signed claim, unresolved count and daily reserve reconcile. Earlier artifact hashes are unchanged.

| Diagnostic | Reversal | Ridge |
|---|---:|---:|
| Identified gross dollars | 13,069,785.39 | 10,823,675.59 |
| Identified fixed-cost dollars | -15,578,773.79 | -15,558,226.54 |
| Identified impact-cost dollars | -1,012,811.50 | -1,002,009.36 |
| Identified borrow dollars | -1,695,878.21 | -1,613,179.23 |
| Identified net subtotal dollars | -5,217,678.11 | -7,349,739.54 |
| Conditional daily mean / N (bp) | -1.2197 | -1.7180 |
| Conditional daily sample SD / N (bp) | 58.1288 | 48.5547 |
| Annualized SD of conditional measured-component daily contribution (%) | 9.2277 | 7.7078 |
| Identified asset-interval count coverage (%) | 80.5789 | 79.9866 |
| Complete wealth-and-expense interval coverage (%) | 80.1159 | 79.5005 |
| Identified verified-entry-basis fraction (%) | 78.5504 | 77.7083 |
| End-date asset-interval coverage (%) | 69.1160 | 68.4329 |
| End raw reserve proxy / N (%) | 77.3504 | 80.1553 |
| End paired-budget proxy / N (%) | 44.8805 | 44.3284 |

Known fixed charges alone exceed identified gross subtotals for both candidates. This is a statement about the measured primitives under the fixed cost assumption, not about total account losses, full strategy alpha or relative superiority. Annual asset-count coverage falls from99.1% in2003 to68.9%/68.3% in2019; annual count ratios and end-date fractions are distinguished in the tables. No specification is changed because of these results.

**Nominal inference for the conditional measured-component mean**, with the same coverage/reserve states above:

| Candidate | Fixed lag | Nominal t | 95% conditional mean CI (bp/day) | Numeric / original dates |
|---|---:|---:|---:|---:|
| uni_reversal_5 | 20 | -1.7430 | [-2.5912, 0.1519] | 4278/4278 |
| uni_reversal_5 | 4 | -1.4570 | [-2.8604, 0.4211] | 4278/4278 |
| ridge | 20 | -2.7014 | [-2.9645, -0.4715] | 4278/4278 |
| ridge | 4 | -2.4660 | [-3.0836, -0.3525] | 4278/4278 |

HAC20 is primary; HAC4 is fixed sensitivity. These are not tests of full-strategy significance or full net alpha. No winner is selected.

Journal QA:18,077,042/17,852,036 unique primitive rows. Fully identified closed-lifecycle accounting identities pass for1,341,514/1,335,859 cohorts; maximum absolute discrepancy5.00e-12/7.28e-12 dollars. These lifecycle checks are integrity identities, not a favorable completed-cohort performance report. Ending828/840 unresolved positions, including reversal2queued unknown executions,1839/1823 verified inventory and378/366 pending development orders remain explicit. No supported releases or reserved-capital reuse.

The reporting assembly initially raised duplicate calendar-count keyword errors; corrected by checking HAC and coverage denominators agree, then merging without duplication. A regression test rejects any denominator mismatch. Day-level residual annotations are derived from unknown primitive/reserve counts; an overall unidentified-book annotation cannot replace those counts. This changes no economic values. Figures were inspected, and time axes are restricted to the development reporting dates.

QA:22focused tests and187repository tests pass. Eight compact aggregate CSV tables, one local large daily CSV, one report manifest and four coverage-qualified figures are produced. Licensed security/cohort journals and quotations stay local; no data extract/secrets are committed. No WRDS/raw scan/new model/2020outcome read.

**Next action: final research-lead synthesis of the preserved identification limits, reservation/coverage evidence and conditional component results. No automatic new methodology stage or holdout access.**
