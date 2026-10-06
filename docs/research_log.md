# Research Log

This log records design decisions, rejected alternatives, data issues, failed hypotheses, and material changes. Entries should be written before or at the time a research decision is made where possible.

---

## RL-001 — Project initiated
**Date:** 2026-10-02

**Decision:** Initiate Project 2 under the working title *Short-Horizon Equity Alpha Forecasting and Cost-Aware Market-Neutral Portfolio Construction*.

**Primary question:** Can short-horizon cross-sectional equity forecasts generate economically meaningful market-neutral alpha after realistic risk controls and transaction costs?

**Rationale:** The project is intended to simulate a research workflow closer to a systematic equity desk than a generic stock-prediction exercise.

---

## RL-002 — Research architecture
**Date:** 2026-10-02

**Decision:** Treat forecasting, portfolio construction, risk controls, transaction costs, and PnL attribution as separate research layers.

**Rejected framing:** single-stock price prediction.

**Reason:** The economic object of interest is cross-sectional implementable alpha, not directional prediction of one ticker.

---

## RL-003 — Primary market data
**Date:** 2026-10-02

**Decision:** Use CRSP CIZ daily US stock data as the core market-data backbone.

**Rationale:** Permanent identifiers, inactive securities, returns, prices, volume, market capitalisation, and corporate-action information make it appropriate for point-in-time historical research.

**Extension:** Compustat/CCM may be added only after the CRSP-only pipeline is stable.

---

## RL-004 — Primary horizon
**Date:** 2026-10-02

**Decision:** Set the primary forecast horizon to five trading days.

**Rationale:** This remains short-horizon while reducing some of the noise and extreme turnover pressure associated with a one-day target.

**Robustness horizons:** 1D and 10D may be examined later, but are secondary specifications.

---

## RL-005 — Execution convention not yet locked
**Date:** 2026-10-02

**Candidate:** signal after close t, execution at open t+1.

**Status:** conditional.

**Required evidence:** empirical CRSP opening-price coverage within the eventual liquid universe.

**Fallback:** execute no earlier than close t+1 with a correspondingly shifted label.

**Integrity rule:** execution convention must not be selected based on realised strategy performance.

---

## RL-006 — Universe thresholds not yet locked
**Date:** 2026-10-02

**Candidate filters:** price > $5, market cap > $1bn, 20-day ADV > $20m.

**Status:** conditional on distribution and coverage diagnostics.

**Integrity rule:** thresholds will be justified by implementability and sample quality, not Sharpe maximisation.

---

## RL-007 — Current stage
**Date:** 2026-10-02

**Stage:** 1A — CRSP extraction and data QA.

**Permitted work:** schema verification, extraction design, coverage diagnostics, eligibility logic, missingness checks, delisting checks.

**Not permitted yet:** model training or portfolio backtesting.

---

## RL-008 — CRSP CIZ market-cap unit verified
**Date:** 2026-10-02

**Finding:** Official CRSP CIZ documentation defines `DlyCap` as daily market capitalisation reported in thousands of dollars.

**Implication:** A $1bn threshold maps to `DlyCap > 1,000,000` in the native CRSP field, not `1,000,000,000`.

**Action:** Corrected the Stage 1A QA utility and documented the unit convention explicitly.

**Research-control lesson:** Source units must be verified before any universe filter or feature is operationalised.


---

## RL-009 — WRDS daily extraction schema confirmed
**Date:** 2026-10-02

**Finding:** The CIZ Daily Stock File web query exposes the core fields required for Stage 1A, including PERMNO/PERMCO, daily OHLC/price fields, total/price/income returns, volume, bid/ask, market capitalisation, delisting flag, price-adjustment factor, and ordinary/non-ordinary dividend amounts.

**Non-issue:** Several optional cumulative adjustment / return-quality variables considered during planning are not exposed in this query form. They are not necessary for Stage 1A data-quality testing and do not justify delaying the extraction.

**Implementation note:** WRDS web exports use lowercase variable names. Repository QA code was aligned to the actual export schema.

**Query decision:** Proceed with the full 1993–2025 entire-database daily extraction with no universe filters applied in WRDS.


---

## RL-010 — Large-file processing workflow
**Date:** 2026-10-02

**Finding:** The full 1993–2025 WRDS daily extract is multi-GB, as expected for an entire-database daily panel.

**Decision:** Raw licensed CRSP data remain local and are not uploaded to GitHub or external chat storage.

**Implementation:** Added a DuckDB-based Stage 1A QA script that queries compressed CSV directly and can spill to disk, avoiding a full pandas in-memory load.

**Research implication:** None. File size changes the engineering workflow, not the methodology or sample definition.


---

## RL-011 — Stage 1A first-pass CRSP QA completed
**Date:** 2026-10-02

**Sample:** 64,974,442 daily rows, 30,363 unique PERMNOs, 1993-01-04 through 2025-12-31.

**Finding 1 — opening-price coverage:** Raw all-security opening-price coverage rises from about 87.5% in 1993 to about 98.5% in 2025. In the preliminary liquid-security diagnostic, annual opening-price coverage is at least 99.27% and averages about 99.83%.

**Interpretation:** Missing opening prices are largely an illiquid-security problem, so next-open execution appears feasible for the intended liquid universe.

**Caveat:** The first liquid diagnostic used same-day dollar volume, not the pre-specified trailing ADV20. Execution timing remains formally unlocked until a lag-safe ADV20 test is completed.

**Finding 2 — duplicate keys:** 14,016 PERMNO-date groups contain duplicates, representing 14,881 excess rows, about 0.0229% of the extract. Maximum multiplicity is 12.

**Decision:** Do not deduplicate mechanically. Inspect representative full source rows to identify the cause before defining a deterministic resolution rule.

**Gate status:** schema passed; next-open execution provisionally supported; unique-key integrity remains under investigation.


---

## RL-012 — Representative duplicate rows inspected
**Date:** 2026-10-02

**Diagnostic:** Inspected 25 high-multiplicity duplicate PERMNO-date groups comprising 122 raw rows and all 29 extracted fields.

**Finding:** Within every inspected PERMNO-date group, all observed fields were exactly identical. No price, return, volume, capitalisation, identifier, flag, or corporate-action field differed within a sampled duplicate group.

**Interpretation:** The sampled duplicates appear to be mechanical exact-row duplication rather than economically distinct daily observations.

**Decision:** Do not yet collapse duplicates based only on the sample. Run a full-dataset row-hash integrity check across all 14,016 duplicate groups. If no conflicting group exists, define the deterministic cleaning rule as retaining one exact row per PERMNO-date key.


---

## RL-013 — Duplicate-key integrity gate passed
**Date:** 2026-10-02

**Full-dataset verification:** All 14,016 duplicated PERMNO-date groups were checked using full-row hashes across the complete extracted schema.

**Result:**
- duplicate groups: 14,016
- excess rows: 14,881
- exact duplicate groups: 14,016
- conflicting groups: 0
- maximum multiplicity: 12
- maximum distinct row versions within any duplicate group: 1

**Decision:** Exact duplicate rows may be deterministically collapsed to one observation per PERMNO-date key.

**Cleaning rule:** retain one row per unique full-row record and enforce uniqueness of PERMNO-date after removal of exact duplicates.

**Gate status:** PERMNO-date integrity PASSED.


---

## RL-014 — Next-open execution gate passed using true ADV20
**Date:** 2026-10-02

**Candidate liquid-universe rule tested:**
- |price| > $5
- market capitalisation > $1bn
- trailing 20-day ADV > $20m
- at least 15 valid observations in the 20-day ADV window

**Opening-price coverage result (1993–2025):**
- minimum annual coverage: 99.294% (2002)
- mean annual coverage: 99.844%
- median annual coverage: approximately 99.998%
- recent years are effectively 100% in most cases

**Universe breadth:**
- median daily eligible count: 1,178 securities
- mean daily eligible count: about 1,131
- maximum daily eligible count: 2,426
- 2025-12-31 eligible count: 2,381

**Decision:** Lock the baseline execution convention as:
signal formed after the close on day t -> execute at the open on day t+1.

**Implication for primary 5-day target:** the label must begin at the next-open execution price and exclude all return information prior to that fill.

**Gate status:** execution timing PASSED.


---

## RL-015 — Historical security metadata extraction initiated
**Date:** 2026-10-02

**Source:** CRSP CIZ Names / historical security information.

**Fields retained:** PERMNO, PERMCO, SecInfoStartDt, SecInfoEndDt, SecurityType, SecuritySubType, ShareType, IssuerType, USIncFlg, PrimaryExch, Ticker, CUSIP, SICCD, TradingStatusFlg.

**Point-in-time rule:** a metadata row is valid for a daily observation only when:
SecInfoStartDt <= date <= SecInfoEndDt.

**Candidate ordinary US common-equity definition:** SecurityType='EQTY', SecuritySubType='COM', ShareType='NS', USIncFlg='Y', IssuerType in ('ACOR','CORP').

**Rationale:** This reproduces the CIZ mapping corresponding to the legacy ordinary US common-stock share-code convention while explicitly excluding REIT issuer type from the core baseline.

**Status:** classification values and interval integrity must be empirically checked before the universe definition is locked.


---

## RL-016 — Historical metadata point-in-time gate passed
**Date:** 2026-10-02

**Metadata sample:**
- 191,048 historical security-information rows
- 40,518 unique PERMNOs
- history spanning 1925-12-31 through 2025-12-31
- zero missing interval start dates
- zero missing interval end dates
- zero invalid intervals
- zero overlapping intervals

**Point-in-time join result:** Candidate liquid daily observations matched historical security metadata at 100% in every calendar year from 1993 through 2025.

**Candidate ordinary-US-common classification:**
- SecurityType = 'EQTY'
- SecuritySubType = 'COM'
- ShareType = 'NS'
- USIncFlg = 'Y'
- IssuerType in ('ACOR','CORP')

This classification identifies 112,197 historical metadata intervals covering 26,914 unique PERMNOs.

**Interpretation:** Historical security classification data are sufficiently complete and internally consistent for point-in-time universe construction.

**Remaining universe decision:** determine the baseline PrimaryExch / TradingStatusFlg restrictions before locking the final ordinary common-equity universe.


---

## RL-017 — Baseline common-equity universe locked
**Date:** 2026-10-02

**Decision:** Lock the baseline point-in-time ordinary US common-equity classification as SecurityType='EQTY', SecuritySubType='COM', ShareType='NS', USIncFlg='Y', IssuerType in ('ACOR','CORP'), PrimaryExch in ('N','A','Q'), and TradingStatusFlg='A'.

**Exchange/status diagnostic:** N/A/Q retains approximately 99.98% of annual observations on average in the candidate liquid common-equity panel; the minimum annual retention is about 99.84%. Only 1,898 B-exchange observations and 227 I-exchange observations fall outside N/A/Q, involving three PERMNOs in total.

**Interpretation:** The N/A/Q restriction has economically immaterial breadth impact while producing a cleaner NYSE / NYSE American / NASDAQ baseline universe.

**Gate status:** security-classification universe PASSED.


---

## RL-018 — Stage 1C methodology check before liquidity-threshold analysis
**Date:** 2026-10-02

**Permitted evidence for threshold selection:** cross-sectional breadth, time-series stability, opening-price coverage, and implementability proxies only.

**Prohibited evidence:** future returns, IC, Sharpe ratio, PnL, or any strategy-performance statistic.

**Candidate baseline retained ex ante:** price > $5, market capitalisation > $1bn, trailing ADV20 > $20m, with at least 15 valid observations in the rolling ADV window.

**Sensitivity design:** compare nearby economically interpretable thresholds around the candidate baseline. The purpose is diagnostic, not optimisation.

**Gate condition:** final thresholds may be locked only after confirming that the baseline produces a sufficiently broad and historically stable ordinary-US-common-equity universe without compromising next-open data coverage.


---

## RL-019 — Liquidity thresholds locked after non-performance sensitivity analysis
**Date:** 2026-10-02

**Methodology constraint:** Threshold selection used only universe breadth, time-series stability, opening-price coverage, and implementability proxies. No returns, IC, Sharpe, or PnL were examined.

**Sensitivity grid:** Price floors $3/$5/$10; market-cap floors $0.5bn/$1bn/$2bn; ADV20 floors $10m/$20m/$50m.

**Baseline diagnostics for price > $5, market cap > $1bn, ADV20 > $20m:**
- mean annual securities: about 1,181
- minimum annual securities: 285
- maximum annual securities: 1,895
- mean annual open coverage: 99.836%
- minimum annual open coverage: 99.267%
- daily panel spans 8,293 trading dates
- median daily eligible securities: 858
- mean daily eligible securities: about 808
- maximum daily eligible securities: 1,475

**Neighbouring-threshold interpretation:** Lowering ADV20 to $10m materially broadens the universe; raising ADV20 to $50m materially narrows it. Moving the price floor from $5 to $3 or $10 has comparatively modest breadth impact once the size/liquidity filters are imposed. A $2bn cap floor narrows the sample materially; a $0.5bn floor broadens it.

**Decision:** Lock the baseline investability filters at price > $5, market capitalisation > $1bn, trailing 20-day ADV > $20m, with at least 15 valid observations in the ADV20 window.

**Rationale:** The baseline is a balanced, interpretable middle specification with strong open-price coverage and sufficient cross-sectional breadth across the full sample, without using any performance statistic.

**Gate status:** liquidity-threshold gate PASSED.


---

## RL-020 — Stage 1D methodology check before target construction
**Date:** 2026-10-02

**Objective:** Freeze the final signal-date eligibility panel and define a five-trading-day forward target consistent with the locked next-open execution convention.

**Locked timing:** information through close t -> signal after close t -> execution at open t+1.

**Candidate target:** open-to-open price return from t+1 through t+6, i.e. Open(t+6)/Open(t+1)-1.

**Integrity concern:** A security may lack a valid t+1 or t+6 opening price because of suspension, delisting, or other trading discontinuity. Blindly dropping such observations could create selection bias, particularly if failures are related to poor future returns.

**Permitted evidence in this gate:** label availability, endpoint-open coverage, five-day-horizon delisting incidence, trading-calendar integrity, and sample attrition only.

**Prohibited evidence:** IC, model fit, Sharpe, portfolio returns, PnL, or any performance statistic.

**Decision rule:** The primary target will be frozen only after quantifying endpoint failure and delisting within the forecast horizon. Any fallback treatment must preserve point-in-time logic and be documented before model training.


---

## RL-021 — Stage 1D first-pass target audit: target not yet locked
**Date:** 2026-10-02

**Observed first-pass coverage:** 6,699,101 eligible signal-date observations. Raw complete t+1/t+6 opening-price target coverage is 99.642% overall. Through 2024, annual complete-open-target coverage averages about 99.679%; the lowest pre-2025 annual rate is about 98.966% (1994).

**Important censoring issue:** 2025 endpoint coverage is artificially depressed because the CRSP extraction ends on 2025-12-31. Signals in the final six trading days cannot have a fully observed t+6 endpoint by construction. These are right-censored observations, not market-data failures.

**Failure-sample issue:** the initial endpoint-failure example export was ordered newest-first and therefore was dominated by 2025-12-31 right-censored rows. A revised diagnostic must separate right-censoring from genuine historical endpoint failure and sample failures across years.

**Corporate-action issue:** the candidate raw-open target Open(t+6)/Open(t+1)-1 must not be frozen until split/distribution treatment is verified. An unadjusted open-price ratio can be mechanically distorted by stock splits and does not automatically include distributions.

**Decision:** Do not lock the target yet. Next gate will audit corporate-action-adjusted open prices / return treatment and explicitly separate end-of-sample censoring from genuine endpoint failure.


---

## RL-022 — Stage 1E methodology check: corporate-action treatment
**Date:** 2026-10-02

CRSP documentation confirms that DlyFacPrc is the within-period factor used in CRSP's return calculation, while cumulative price adjustment is represented separately by DlyCumFacPr. The current Daily Stock File extract contains DlyFacPrc but not DlyCumFacPr.

Therefore DlyFacPrc must not be mechanically treated as a cumulative split-adjustment factor for open prices.

CRSP DlyRet already incorporates applicable price-adjustment factors and dividend amounts in the daily return calculation, but daily close-to-close returns cannot by themselves reproduce a next-open-to-next-open holding-period return because the overnight components at the entry and exit boundaries differ.

Stage 1E will therefore quantify the incidence of corporate actions and endpoint failures before deciding whether the current extract is sufficient or whether DlyCumFacPr / cumulative adjustment data must be downloaded.

No model-performance statistics may be used in this decision.


---

## RL-023 — Stage 1E audit bug identified and corrected
**Date:** 2026-10-02

The first corporate-action audit incorrectly flagged DlyFacPrc != 0 as a factor event. In CRSP CIZ, DlyFacPrc=1 is the dominant no-adjustment state, so this condition incorrectly classified nearly every holding window as containing a factor event.

Observed DlyFacPrc frequency confirms this: 64,941,709 rows have DlyFacPrc=1. Only about 15,382 non-unit factor rows are present among rows with observed DlyFacPrc, approximately 0.0237%.

The correct diagnostic is therefore DlyFacPrc != 1 (with numerical tolerance), not DlyFacPrc != 0.

Other Stage 1E findings remain valid: ordinary-dividend windows are material (~5.39% of eligible five-day windows), while genuine entry/exit-open failures and delisting windows are each around one-tenth of one percent overall.

The audit will be rerun with the corrected factor-event definition before the target is frozen.


---

## RL-024 — Stage 1E corporate-action audit passed; cumulative adjustment data required
**Date:** 2026-10-02

Corrected five-day-window audit across 6,699,101 eligible signal observations:
- right-censored windows: 8,686 (0.130%)
- genuine missing entry opens: 7,596 (0.113%)
- genuine missing exit opens: 7,703 (0.115%)
- ordinary-dividend windows: 360,788 (5.386%)
- non-ordinary-dividend windows: 8,446 (0.126%)
- non-unit DlyFacPrc windows: 12,617 (0.188%)
- delisting windows: 8,416 (0.126%)

**Interpretation:** corporate-action factor events are rare but non-negligible, while ordinary dividends occur in more than five percent of candidate holding windows. Therefore a raw opening-price ratio is not an adequate headline target.

**Decision:** obtain CRSP cumulative price-adjustment data (DlyCumFacPr or equivalent) before freezing the primary next-open-to-next-open target. Existing DlyFacPrc must not be used as a substitute cumulative factor.

**Target status:** still conditional pending cumulative-adjustment extraction and verification.


---

## RL-025 — Stage 1F methodology check: cumulative-factor verification
**Date:** 2026-10-03

The WRDS CIZ standalone daily cumulative-adjustment table was located and extracted from `crsp.stkdlycumulativeadjfactor`. The extract contains annual CSV files for 1993–2025 with PERMNO, DlyCalDt, DlyCumFacPr, and DlyCumFacShr.

Before the forecast target is frozen, the cumulative-factor data must pass three non-performance checks: (1) year/schema/key integrity, (2) join coverage against the CRSP daily panel, and (3) event-level verification that the documented price adjustment removes mechanical split-related discontinuities around changes in DlyCumFacPr.

No IC, model fit, Sharpe, PnL, or portfolio-return evidence may be used in this gate.

**Target status:** still conditional pending cumulative-factor verification.


---

## RL-026 — Stage 1F cumulative-factor integrity checks passed
**Date:** 2026-10-03

The 1993–2025 extract from `crsp.stkdlycumulativeadjfactor` was verified locally.

**Integrity results:**
- 33 annual files present, covering 1993 through 2025
- zero missing `DlyCumFacPr` values
- zero missing `DlyCumFacShr` values
- zero duplicate PERMNO-date rows
- annual join coverage against the CRSP daily panel is approximately 99.95%–99.98% throughout the sample
- 17,851 genuine cumulative-price-factor change events identified

**Interpretation:** the standalone cumulative-adjustment table is internally clean and matches the daily stock panel almost completely.

**Remaining Stage 1F gate:** verify event-level adjustment direction by comparing raw-open discontinuities with cumulative-factor-adjusted open discontinuities around factor changes. The primary forecast target remains conditional until this event-level check passes.


---

## RL-027 — Stage 1F event-level adjustment direction validated; zero-factor edge case remains
**Date:** 2026-10-03

The 500 largest raw-open discontinuities around cumulative-price-factor changes were inspected.

**Event-level result:** among 499 observations with both raw and adjusted jumps defined, the cumulative-factor adjustment reduced the open-price discontinuity in 499/499 cases. The median absolute raw open jump was about 39.7 (3,971%), compared with about 0.127 (12.7%) after adjustment. The 95th percentile fell from about 159.3 to about 0.478.

**Interpretation:** this strongly validates the documented adjustment direction using raw price divided by DlyCumFacPr for cross-date price comparability.

**Edge case:** one sampled event contains a zero cumulative price factor, making the adjusted price undefined; additional events contain extremely small factors. Before closing Stage 1F, quantify non-positive/tiny DlyCumFacPr values in the full factor panel and determine whether they intersect the locked eligible universe.

**Gate status:** event-level adjustment direction PASSED; numerical edge-case check remains OPEN.


---

## RL-028 — Stage 1F cumulative-factor gate passed
**Date:** 2026-10-03

Full-panel numerical edge-case QA found 5,241 zero cumulative-price-factor rows and additional extremely small positive factors in the broad CRSP factor table, but none of these problematic values enter the locked eligible universe.

Within the 6,699,101 locked eligible signal-date observations:
- missing DlyCumFacPr: 0
- zero DlyCumFacPr: 0
- negative DlyCumFacPr: 0
- DlyCumFacPr < 1e-6: 0
- minimum observed eligible DlyCumFacPr: 0.000002

Combined with the prior event-level evidence that cumulative-factor adjustment reduced mechanical open-price discontinuities in 499/499 comparable high-jump factor-change examples, this closes the cumulative-adjustment validation gate.

**Decision:** use DlyCumFacPr for cross-date price comparability in the target-construction layer.

**Gate status:** Stage 1F PASSED.

**Next stage:** target formula freeze, including explicit dividend treatment and endpoint/delisting rules.


---

## RL-029 — Stage 1G methodology check: total-return reconstruction before target freeze
**Date:** 2026-10-03

**Locked economic object:** return earned by buying at the open on t+1 and exiting at the open on t+6.

**Price component:** cross-date prices must be made comparable with `DlyCumFacPr`, using adjusted price = raw price / DlyCumFacPr.

**Dividend component:** a raw adjusted-price ratio alone is not a total return. Candidate dividend treatment will use the relationship between CRSP total return (`DlyRet`) and ex-distribution return (`DlyRetX`) to isolate the income/distribution multiplier.

Before constructing the open-to-open five-day target, the decomposition must reproduce CRSP's own close-to-close daily returns on observations where all required fields are valid.

**Permitted evidence:** reconstruction error, coverage, numerical edge cases, and field consistency only.

**Prohibited evidence:** forecast IC, model fit, Sharpe, PnL, or any strategy-performance statistic.

**Gate:** validate the CRSP-consistent total-return decomposition first. Endpoint/delisting treatment remains a separate unresolved sub-gate.


---

## RL-030 — Stage 1G methodology check: reconstruction coverage and outlier attribution
**Date:** 2026-10-03

**Scope:** Resolve the missingness and largest-discrepancy questions left open by the existing reconstruction outputs. No new research stage, target construction, or model training is authorized in this step.

**Permitted evidence:** coverage, reconstruction error, data integrity, numerical consistency, and locked point-in-time eligibility. IC, model fit, Sharpe, PnL, and portfolio-performance evidence are prohibited.

**Diagnostic plan:** Reuse the cumulative-factor parquet and saved 500 largest errors. Because no row-level daily reconstruction cache exists, scan only the required daily fields once into a local, uncommitted parquet cache. Reproduce the original reconstruction denominator and counts before interpreting any attribution. Report both overlapping missingness predicates and mutually exclusive primary reasons in a fixed order: missing current factor, missing current price, missing previous comparable price, zero current factor, zero previous comparable price, missing total return, missing ex-distribution return, near-zero return denominator, other. The partition order is a reporting convention, not a causal ranking.

**Numerical rules:** Retain the existing denominator tolerance of 1e-14. Use 1e-6 only as a diagnostic check of whether source previous-price reconstruction agrees with the exported return to its observed six-decimal precision; it does not establish a new target acceptance threshold. Price/factor events, unchanged prices, large calendar gaps, and extreme returns are diagnostic indicators, not proof of stale prices or causal explanations. Retain raw flag values rather than inventing undocumented flag meanings.

**Eligibility limitation:** Observation-date eligibility is not equivalent to eligibility at an earlier signal date. An observation outside the eligible universe may still affect a holding window initiated earlier; no exclusion rule may be inferred from current-date ineligibility.

**Gate status:** OPEN pending these diagnostics; the primary target remains conditional.


---

## RL-031 — Stage 1G coverage and outlier diagnostics completed; reconstruction gate remains OPEN
**Date:** 2026-10-03

**Reproducible diagnostic:** `scripts/13_diagnose_reconstruction_gate.py`, with reusable implementation in `src/data/reconstruction_diagnostics.py`. Local cached selected daily fields and 32 security-history partitions reuse the verified cumulative-factor parquet and original top-500 discrepancy export. No original Stage 1G reconstruction script was rerun. Cache input size/mtime fingerprints and schema version are checked on reuse; caches and row-level licensed diagnostic exports remain local and uncommitted.

**Engineering failures preserved:** Two full-panel window attempts exhausted the configured 4GB and 6GB memory budgets. Partitioning by PERMNO modulo 32 resolved this without splitting any security history or changing the research sample. Two export-query errors (reserved alias and ambiguous joined field names) were corrected before successful completion. These failures do not establish economic evidence.

**Integrity QA:** Exactly 64,959,561 unique PERMNO-date rows, 64,056,350 comparable reconstructions, 903,211 noncomparable observations, and 6,699,101 locked eligible observations reproduce the prior audits. All 500 saved discrepancy keys matched once; their recomputed errors agree with the saved values. Nonfinite observed returns and nonfinite non-null reconstructions each count zero. Primary-reason counts sum exactly to 903,211.

**Noncomparable coverage:** 98.6096% comparable. Mutually exclusive primary reasons, using the RL-030 ordering:
- missing current factor: 19,668 (2.1776% of noncomparable rows)
- missing current price after the factor-missing category: 844,241 (93.4711%)
- missing previous comparable price after the preceding categories: 39,302 (4.3514%)
- remaining primary categories, including missing returns, near-zero denominator, and other: zero, because their observations already belong to preceding missing-price/factor categories

Overlapping predicates must not be summed:
- missing current DlyCumFacPr: 19,668 (2.1776%)
- missing current raw price: 844,663 (93.5178%)
- missing previous comparable price: 879,828 (97.4111%)
- zero current factor: 5,241 (0.5803%)
- zero previous comparable price: zero
- missing DlyRet: 869,521 (96.2700%)
- missing DlyRetX: 869,521 (96.2700%)
- abs(1+DlyRetX) <= 1e-14: 22 (0.0024%)

The 879,828 missing previous comparable prices decompose into 30,363 first observations in the extraction, 844,225 missing previous raw prices, and 5,240 previous zero factors. No missing previous-factor or other cases remain in that decomposition. Forty-five noncomparable observations satisfy locked observation-date eligibility; all have missing previous raw prices, with observed source DlyPrevPrc and return-duration flags P1 (41) or P2 (4). Their source-previous-price accounting checks match DlyRetX within 1e-6, but substituting that field into the eventual holding-window target is not approved here.

**Largest-error attribution:** All 500 original largest-error examples fail locked observation-date eligibility. Overlapping liquidity failures include 490 below the market-cap threshold, 476 below the ADV20 threshold, and 88 below the price threshold; none fail the ADV observation-count minimum. None has a current delisting flag, missing current/source-previous raw price, or a calendar gap greater than four days. Source DlyPrevPrc equals the previous observed raw price in all 500, so replacing the lag with that field alone does not explain these discrepancies. One unchanged-price and one absolute-return-greater-than-one proxy occur. Raw price and return-duration flags are preserved in the local frequency table; these proxies are not proof of stale pricing or undocumented flag meanings.

Nonordinary distribution amounts are nonzero in 498/500 examples. Four have cumulative-factor changes and nonunit period factors. The diagnostic identity

`(abs(DlyPrc) * DlyFacPrc + DlyNonOrdDivAmt) / abs(DlyPrevPrc)`

matches `1 + DlyRetX` within 1e-6 in 499/500 examples. The remaining error is approximately 6.51e-6 in a factor-change example with a very small cumulative factor and a rounded period factor; rounding is a plausible explanation, not a verified cause. This accounting evidence indicates that the original adjusted-price-only reconstruction omits a nonordinary-distribution component present in the exported ex-distribution return. It is not evidence that a new open-to-open total-return target has been validated. No stale-price or delisting explanation is established for the leading errors.

**Locked eligible sample:** Of 6,699,056 comparable eligible observations, 6,699,046 have no nonordinary distribution. Their maximum absolute total-factor error is 7.6633e-7, with none above 1e-6. Ten have nonordinary distributions; four have original reconstruction errors above 0.001, with a maximum of 0.0367134. All ten match the source-previous-price/nonordinary-distribution diagnostic identity within 1e-6. Therefore the discrepancy is not confined to ineligible edge securities. Current-date ineligibility also cannot establish absence from holding windows formed on earlier eligible signal dates.

**Decision:** Reconstruction gate remains OPEN. Do not freeze the primary target. The original `(1+DlyRet)/(1+DlyRetX)` multiplier, combined with adjusted-price ratios alone, is insufficient to account for the observed nonordinary distributions. Retain all exceptions; do not silently exclude them or alter the locked universe.

**One next action:** Within Stage 1G, document and validate a distribution-aware close-to-close decomposition, including the treatment of the 45 missing-lag-price eligible observations, before reconsidering reconstruction closure. Endpoint/delisting target rules remain a separate unstarted sub-gate. No model or performance evidence was used.


---

## RL-032 — Stage 1G methodology check: definition-grounded distribution reconstruction and missing-price timing
**Date:** 2026-10-03

**Scope:** Resolve only the two RL-031 items. Re-read AGENTS.md, methodology.md, and latest research log. Use official CRSP CIZ field/calculation/flag definitions, reconstruction error, coverage, numerical consistency, data integrity, and locked eligibility only. IC, Sharpe, PnL, model fit, and performance-based specification selection are prohibited. No new research stage or predictive model is permitted.

**Plan:** Reuse the selected daily parquet and 32 diagnostic partitions without scanning raw daily data. Independently reconstruct price and total returns from prices, period factor, and nonordinary/ordinary distribution amounts; do not use observed returns to define the reconstructed value. Validate the original comparable population and the entire locked eligible population separately, and export every eligible nonordinary-distribution observation. Audit all 45 missing-lag cases against the global trading calendar, preceding rows and earlier valid prices, plus historical security metadata. Do not interpolate or forward-fill. Separate recovery of a CRSP multi-period return from recovery of a missing daily execution/valuation price.

**Numerical discipline:** Six-decimal exported returns/factors/distribution amounts may generate rounding errors. Check input-precision propagation using a stated fixed bound derived from rounding, rather than selecting an error threshold after inspecting returns. Do not treat cumulative-factor ratios as interchangeable with the period return factor without checking the CRSP definition and numerical relation; retain failed formulas. Keep the reconstruction gate OPEN until both numerical and timing questions are fully resolved.


---

## RL-033 — Stage 1G distribution-aware reconstruction passed; missing-lag timing resolved
**Date:** 2026-10-03

**Definition evidence and record:** See `docs/stage1g_return_reconstruction.md` for the official July 2026 CRSP calculation/user-guide URLs, inspected pages, derivation, rejected formulas, aggregate QA, and case disposition. DlyRetX excludes ordinary dividends only. Distribution amounts cover ex-dates in the source return interval on the previous-price basis. The validated independent equations are `R_X=(P*F+N)/P0-1` and `R_T=(P*F+N+O)/P0-1`, with P0 from DlyPrevPrc. They do not use observed return ratios. The cumulative-basis equivalent requires factor transport `K=F*C/C0`; substituting a cumulative-factor ratio for the period factor or simply adding all nonordinary cash to an adjusted-price ratio is rejected.

**Validation:** Original comparable count 64,056,350; locked eligible count 6,699,101, including all 45 formerly missing-lag reconstructions. Full-market price/total maximum error 1.3200e-4, P99 4.94382e-7, median 2.22222e-7. Eligible price/total maximum 4.78846e-6, P99 4.95050e-7, median 2.45902e-7. Raw and common-basis reconstructions agree within 1.78e-15 in the original comparable population. Complete formula coverage, no nonfinite output, and no sign/factor-integrity failure were found.

**All eligible nonordinary observations retained:** Ten rows. Price error maximum/P99/median: 4.66205e-7 / 4.62500e-7 / 2.22972e-7. Total error maximum/P99/median: 4.26343e-7 / 4.26226e-7 / 2.77597e-7. Per-row results are retained locally in `eligible_nonordinary_reconstruction.csv`.

**Precision gate:** Propagating six-decimal rounding of prices, factor, amounts, and observed return yields zero bound violations in every audited population; no undefined bounds are accepted. This is export-precision consistency, not an arbitrary uniform 1e-6 cutoff or proof of individual unrounded values. Seven eligible errors exceed 1e-6 but fall inside the derived bound. A provisional bound that omitted current/previous price rounding failed on nine broad-market penny-price rows and was rejected. The naive cumulative-price-plus-cash formula also failed (maximum eligible nonordinary price error 0.7284507); retained as a failed alternative.

**45-case cause/timing closure:** All 45 immediately previous trading-day rows exist and are flagged MP, with missing price/open and zero volume. There are no absent-row or listing-start cases, no recorded prior-day halt/suspension, and no current/prior-day factor/distribution event. Metadata records Active. Forty-one source returns span two trading periods (P1), four span three (P2); source previous prices exactly match the earlier valid prices, with no intervening valid price. Source-date cumulative factors also match the factors used by the basis check. Source-return errors maximum/P99/median: 5.00000e-7 / 4.86928e-7 / 2.09147e-7. The physical reason for an MP quote, including an unrecorded intraday halt, is not established; no speculative cause is asserted or needed for accounting/timing disposition.

**Disposition:** Preserve all 45 eligible signal dates and explicit multi-period/missing-price flags. DlyPrevPrc may reconstruct the actual source interval's return at the current close, not a missing day's price or a one-day return. No interpolation, forward-fill, daily spreading, or blanket signal-date exclusion. Missing execution endpoints and holding-interval compatibility must be resolved in the separate endpoint/delisting target sub-gate; this entry does not approve any target fallback.

**Execution and QA:** `scripts/14_validate_distribution_reconstruction.py` reused fingerprinted caches; no raw daily rescan. Six accounting/timing tests passed. Per-case context/source-date matching and aggregate consistency checks passed. Licensed row-level outputs and official-document copies remain local.

**Decision:** Close the Stage 1G close-to-close reconstruction sub-gate. The two RL-031 issues are resolved through definition-grounded distribution accounting and explicit multi-period treatment. Stage 1G and the primary five-day target remain unfinished. No model training or new stage was entered.

**One next action:** Plan the endpoint/delisting and holding-boundary treatment within Stage 1G before freezing the next-open target; do not execute it in this change.


---

## RL-034 — Stage 1G methodology check: next-open endpoints, delisting, and distribution boundaries
**Date:** 2026-10-03

**Scope:** Audit only the fixed signal-close t / entry-open t+1 / planned-exit-open t+6 economic object. No new stage or model training. Permitted evidence: official definitions, endpoint and event coverage, source interval timing, numerical consistency, and locked point-in-time eligibility. IC, Sharpe, PnL, model fit, and all strategy-performance evidence are prohibited.

**Plan:** Reuse the fingerprinted daily/cumulative-factor partitions and prior endpoint QA. Index future dates by the global market trading calendar, not the next observed security row. Separate extraction censoring from historical absence of rows or positive opening prices. Retain all signal-date eligible keys. Count ordinary/nonordinary distributions separately at entry, interior dates, and exit; a source multi-period amount is not automatically an ex-date-specific event. Inspect the actual CIZ daily delisting flag definition before interpreting prior flag-window counts as actual delisting counts. Do not manufacture missing execution prices or append legacy delisting returns to an already incorporated CIZ return. Record unresolved valuation, successor-security, entitlement, or event-date cases explicitly rather than dropping them.

**Decision discipline:** Freeze only if every proposed path has an identified economic interval and valid data treatment. Numeric reconstruction success alone does not prove next-open target availability or boundary correctness.


---

## RL-035 — Stage 1G next-open boundary audit completed; target gate remains OPEN
**Date:** 2026-10-03

**Record:** `docs/stage1g_target_boundary_proposal.md` documents the explicit asset/claims ledger proposal, sources, boundaries, missing-data disposition, full path table and missing fields. This is not a frozen target specification.

**Definition correction:** Official CIZ definitions identify DlyDelFlg as a stored delisting-return flag, while DelDlyDt is conventionally the trading day after the actual DelistingDt. Earlier 8,416-window "delisting" counts must be interpreted as return-flag windows, not actual delistings occurring during the holding interval. DelAmtDt and successor/payment details are required before a return recorded in the window can be used as a b-time value. Do not append legacy delisting returns to CIZ returns already incorporating them.

**Boundary rule:** Actual ex-dates satisfy `entry_date < ex_date <= exit_date`. Entry-day entitlement is excluded; exit-day entitlement is included, but exit-day close-to-close/intraday returns are not. Stock/due-bill events require actual ex-dates/payment types, not record-date heuristics. The candidate economic ledger holds cash/fixed receivables without reinvestment or interest; this is proposed only, not locked or used to construct labels. Nonordinary amounts cannot be assumed cash or a quantity adjustment without event details.

**Integrity and counts:** Reused 32 fingerprinted cache partitions and the global trading calendar, with 6,699,101 unique signal keys. Right-censored: 8,686 (0.129659%). Historical missing entry open: 7,596 (0.113388%). Historical missing exit after valid entry: 7,703 (0.114986%), of which 6,916 have a stored return flag and 787 do not. All missing entry rows exist; 6,012 are TR with positive volume, so an absent open is not proof of no execution. Exit missing-row count after valid entry is 5,531. The remaining quoted/missing/delisting price-flag counts and metadata are preserved in local QA outputs and the proposal.

**Distribution coverage (overlapping proxies):** Ordinary amounts at entry/interior/exit: 60,316 / 240,523 / 60,020; offsets 2–6 union 300,514 (4.485885%). Nonordinary amounts at entry/interior/exit: 1,472 / 5,584 / 1,390; offsets 2–6 union 6,974 (0.104104%). No observed source multi-period amount/factor event occurs in offsets 2–6, but daily amounts still do not identify payment types or received securities. Daily delisting-return flags offsets 1–6 total 8,416, offsets 2–6 total 6,948; neither substitutes for the missing event history.

**Mutually exclusive review paths:** Price-only candidate 6,363,239 (94.986462%); ordinary-cash candidate 299,291 (4.467629%); nonordinary/factor review 12,586 (0.187876%); right-censoring 8,686; missing entry 7,596; return-flag delisting review after entry 6,916; missing exit without flag 787. These sum to the full denominator. The 27,885 historical noncandidate cases are review/availability cases, not a proven census of irreducibly unpriceable holdings. Conservative event review includes entry-day events; obtaining event details may clear some. No sample was deleted or model-ready complete-case panel approved.

**Unresolved:** Current local files lack StkDelists actual delisting and amount dates, payment form, completion/missing-return reason and successor links; StkDistributions event payment type/share factors/ex-dates/received-security links; DlyPrevDt and DlyRetMissFlg. Some execution opens are simply unobserved even with trading activity. Scalar cumulative price factors, source multi-period returns or later settlement values cannot safely manufacture those endpoints. Do not interpolate, forward-fill, assume zero/-100% loss, or extend exit to the next observed row. Holdings after verified entry must remain in the ledger until valued or explicitly unresolved, preventing retrospective disappearance.

**QA:** Five boundary/calendar/coverage tests passed. Aggregate coverage reproduces prior endpoint diagnostics, with preserved overlapping counts and a unique-key audit. No raw daily scan, target construction, model training, or new stage. Only documentation, reproducible diagnostic code and tests are committed; licensed row-level outputs remain local.

**Decision:** Stage 1G OPEN; primary target remains unfrozen. The proposal does not yet cover every path without data or valuation ambiguity.

**One next action:** Obtain compact CIZ delisting and distribution histories for flagged securities to resolve event timing, payment and successor links, then continue this same gate. Event history will not by itself fix missing opening-price measurements.


---

## RL-036 — Stage 1G complete cache-only exception extraction inventory
**Date:** 2026-10-03

**Methodology check:** Re-read AGENTS.md, methodology and RL-033–035 before execution. Permitted evidence: cached coverage, keys, dates, missingness and existing definition-grounded field requirements. No IC, Sharpe, PnL, model fit or forecasting-performance evidence; no locked specification change, target construction, data download or new stage.

**Small diagnostic:** `scripts/16_inventory_target_exceptions.py` / `src/data/target_exception_inventory.py` read only the existing 32 boundary-audit parquet partitions. No raw daily scan or audit regeneration. Complete input: 6,699,101 unique signal keys. Local outputs: `target_exception_inventory.csv` (18 summary categories with observation/security counts, signal/window/endpoint date ranges, source tables, required fields and limitations) and `target_exception_extraction_selectors.csv` (23,442 category/PERMNO conservative date envelopes). Licensed selectors and generated CSVs are not committed. Envelopes can include intervening dates without exceptions; use original cached keys to narrow exact date requests. Aggregated audit flags cannot identify exact interior event dates. Daily amount dates remain proxies, not verified ex-dates.

**Complete endpoint coverage:** Non-censored missing entry: 7,596 observations / 1,711 PERMNOs, entry dates 1993-01-28–2025-12-16. Missing exit with a stored delisting-return flag: 8,416 / 1,509, exit dates 1993-11-18–2025-12-23. Missing exit without that flag: 6,150 / 469, exit dates 1993-04-02–2024-11-08. These exit counts include invalid entries, unlike the earlier valid-entry subsets of 6,916 / 1,448 and 787 / 465. Both endpoints missing: 6,863 / 1,482. Right-censoring remains separate: 8,686 / 1,477, signal dates 2025-12-23–2025-12-31; absent future dates are not invented.

**Overlapping event/integrity coverage, excluding censoring:** Nonordinary entry boundary 1,472 / 1,468 PERMNOs; exit boundary 1,390 / 1,386; interior 5,584 / 1,436. Factor/nonordinary union 21,065 / 2,282, full observation windows 1993-02-12–2025-12-31. Delisting-return/DA review 8,416 / 1,509; interior missing price 5,843 / 1,523; missing event fields 7,031 / 1,498; invalid factor 8,416 / 1,509. Aggregated event interval: zero. Ordinary boundary validation controls: entry 60,265 / 1,870 and exit 60,020 / 1,877. Censor exclusion explains differences from older overlapping full-calendar counts. Union of historical endpoint/event/integrity review flags: 28,037 observations / 2,357 securities; ordinary boundary controls are additional. This broader union includes interior-price flags that do not necessarily prevent endpoint valuation and differs from the mutually exclusive 27,885 review-path count. No count proves irreducible unpriceability.

**Extraction requirements:** StkDly opening measurements and source-interval fields DlyPrevDt/DlyRetMissFlg; StkDelists actual DelistingDt/DelDlyDt/DelAmtDt, payment/status/action/reason, missing-return reason, amounts and successor identifiers; StkDistributions actual DisExDt/sequence, ordinary/payment/type/detail, amounts/share and price factors, payment dates and received-security links. Exact field lists are retained in the summary and reproducible code, based on the existing RL-035 proposal; provider-specific availability/schema still needs confirmation. Cumulative-factor data already local should substitute wherever sufficient. Select delisting histories by actual OR storage dates and retain later amount/payment information as dated evidence, never as an automatic exit-time value. Linked security opening quotes may require a second narrowly scoped request after successor IDs are known. Re-extracting StkDly can reproduce null opens; no existing field is proven to recover them safely.

**QA and decision:** Counts reproduce prior missing-entry, valid-entry missing-exit, both-missing and censoring totals; input uniqueness and partition completeness verified. Five existing boundary/calendar tests passed. Commands completed well below two minutes. No rows dropped, prices filled, methodology edited or gate closed. Stage 1G OPEN. AGENTS.md and README unchanged as requested scope permits code/log changes only.

**One next action:** Review this inventory to authorize a compact CIZ event-history/endpoint extraction using per-security selectors and cached exact windows; do not assume the extraction will resolve absent opening measurements.


---

## RL-037 — Stage 1G exact local WRDS extraction selectors prepared
**Date:** 2026-10-03

**Methodology check:** Re-read AGENTS.md, methodology and latest log. Scope limited to local selector construction under the approved extraction design; permitted evidence is coverage, timing, provenance and key integrity. No performance evidence, methodological change, target labels or new stage. User supplied manually confirmed live SQL table/column names; no WRDS connection was made here.

**Construction:** `scripts/17_build_stage1g_extraction_selectors.py` / `src/data/stage1g_extraction_selectors.py` reuse the 32 cached boundary-audit partitions and existing selected daily parquet only. Administrative censoring is excluded. Delisting windows use signal date through planned exit for missing endpoints, delisting/DA flags, interior missing prices and missing event fields. Distribution windows use entry through exit for factor/nonordinary, missing fields and ordinary entry/exit controls. Merge overlap/calendar-day adjacency within security using a running maximum endpoint; preserve disjoint intervals. Every merged window retains the full list of original signal dates, intervals and category lists. Daily selectors contain only existing rows with missing endpoint opens, prices, returns or event fields, multi-period returns or delisting/DA; both missing metadata fields are requested on these affected rows. No dates are manufactured for absent rows.

**Results:** Delisting: 15,451 source windows -> 2,202 merged windows, 1,774 PERMNOs, 1993-01-27–2025-12-23. Distributions: 141,090 -> 64,671, 3,064 PERMNOs, 1993-01-25–2025-12-31. Daily: 7,900 unique existing keys, 1,774 PERMNOs, 1993-01-28–2025-12-16. Candidate-existing-row count before daily reason filtering is recorded in manifest. Longest delisting windows: PERMNO 69032 1997-05-22–2004-01-27 (2,442 calendar days); 64995 1997-07-07–2000-07-25 (1,115); 66157 2001-02-16–2004-01-27 (1,076). Longest distribution windows: 32803 2012-08-16–2012-09-28 (44 days); 32678 2017-12-22–2018-01-25 (35); 89626 2020-12-02–2021-01-04 (34). The longest delisting interval is a genuine chain of 1,669 selected signal windows, each 9–18 calendar days, including 1,667 missing-entry and 1,664 unflagged missing-exit reasons (overlapping); it is not a global min/max envelope bridging disjoint windows. Long histories of unavailable opens remain data questions, not newly inferred physical causes.

**QA:** Complete 6,699,101 unique input keys. No censored source signals selected. Merged windows neither overlap nor remain adjacent per PERMNO; every selected source window maps to exactly one merged interval. Daily keys are unique and all exist in the daily cache. Input size/mtime fingerprints unchanged. Six merge/boundary tests passed, including nested intervals, adjacency, disjointness, security isolation and provenance retention. An initial diagnostic SQL alias was rejected as a reserved word; corrected before successful completion. All commands completed below two minutes.

**Outputs and extraction design:** Local ignored `data/interim/stage1g_extraction/` contains delist_windows.parquet, distribution_windows.parquet, daily_missing_field_dates.parquet and manifest.json. Manifest records timestamp, source fingerprints, selection rules, counts/date ranges, longest windows, confirmed WRDS tables/request columns, batches of 200 delisting PERMNOs / 100 distribution PERMNOs / 5,000 daily keys and explicit no-query statement. These licensed selectors are not committed. Future delisting query must OR-match delistingdt, deldlydt or delamtdt and retain the complete event; distribution query restricts disexdt only, retaining later payment information. Neither later settlement nor a missing open authorizes invented exit values.

**Decision:** Stage 1G remains OPEN; target methodology unchanged. No raw daily scan, WRDS query, download or successor extraction. AGENTS handoff remains at RL-035; this entry records preparation only and does not close or advance any research gate.

**One next action:** Review long selectors and authorize the narrow WRDS extraction before any remote query.


---

## RL-038 — Stage 1G resumable WRDS extraction code prepared, not executed
**Date:** 2026-10-03

**Methodology check:** Re-read project instructions, methodology and latest log. Scope: extraction execution design only, using user-confirmed live schemas/table sizes and existing selectors. No performance evidence, target methodology change or new stage.

**Revised approved strategy:** User reports approximately 29,833 delisting rows, 1.10 million distribution rows and 110 million daily rows. Download all stkdelists rows with the 19 required columns; delist_windows remains a local analysis object, not a server restriction. Choose distribution method B: all event dates for only 3,064 selected PERMNOs, 13 columns, then apply exact windows locally during later analysis. No payment-date restriction. Selected distributions are bounded by the reported 1.10 million table rows; actual selected count remains unknown. Daily extraction uses only the 7,900 exact keys and four columns, no existing daily-field re-download. No source table COUNT or schema query is added.

**Implementation:** `scripts/18_extract_stage1g_wrds.py` / `src/data/stage1g_wrds_extraction.py`. Default execution prints a local plan only; --execute is required before importing WRDS/connecting. Existing WRDS connection may be supplied to run(connection). One delisting query, seven distribution batches of <=500 PERMNOs, four daily batches of <=2,000 keys: 12 data queries on a fresh run. Bound parameters, EXISTS daily-key matching, no server writes. Atomic batch files and download_manifest.json support resume, selector SHA256 binding, completed-batch checksum validation and final output consolidation. Incomplete/invalid daily coverage fails rather than silently dropping or creating keys. Duplicate distribution/daily keys and unexpected columns/security/date keys fail. Manifest records row counts, security counts, date ranges, checksums, completion and batch error type without persisting connection exception text.

**Expected local ignored outputs:** data/interim/stage1g_extraction/stkdelists.parquet, stkdistributions.parquet, stkdlysecuritydata.parquet, download_batches/*.parquet and download_manifest.json. Existing selector manifest is preserved. No licensed outputs committed.

**Validation/decision:** Local dry run reports 12 queries and wrds_query_executed=false. Three tests passed: query restrictions, missing daily-key rejection and fake-connection resume/checksum corruption handling. No real WRDS connection, remote query, data download or raw-daily scan. Stage 1G remains OPEN. Runtime WRDS dependency/environment is required when extraction is explicitly authorized; it is not installed by this change.

**One next action:** Review the prepared script and authorize execution in the existing WRDS-capable environment.


---

## RL-039 — Stage 1G authorized extraction blocked before queries by connection timeout
**Date:** 2026-10-03

**Scope/preflight:** User authorized the approved full 19-column delisting table, 3,064-PERMNO distribution batches of 500 and exact 7,900 daily-key batches of 2,000. Re-read instructions/methodology/latest log. Source-cache size/mtime fingerprints match; selector counts, date ranges, original-window provenance counts and daily-key uniqueness match construction manifest. Download outputs are gitignored; no licensed files staged. No methodology change or interpretation.

**Execution attempt:** Default WRDS username initially resolved to local neil and fell back to interactive input, yielding EOFError before connection. Added optional --wrds-username and retried with user-confirmed neilqian using the home-directory pgpass. Stalled connection stopped before any extraction, then retried with SSL required and 30-second connection timeout. WRDS wrapper again fell back to interactive input/EOFError. A bounded direct PostgreSQL connection diagnostic, without observation queries, exposed the underlying OperationalError: connection to server at wrds-pgdata.wharton.upenn.edu (165.123.60.118), port 9737 failed: timeout expired. This is not evidence of wrong credentials or a CRSP subscription denial. User-terminal connectivity does not establish connectivity from this Codex process.

**Recovery code:** Extraction now prints batch progress, stops only a failing source while preserving completed batch files, and continues independent sources without scope expansion. Confirmed username can be passed without password; connection timeout bounded. Existing three local tests pass. No server observation query executed and no downloaded batches exist.

**Record/decision:** Local ignored download_manifest.json records approved query plan/selector SHA256, preflight checks, connection error, zero completed batches/downloaded rows and untested daily coverage. All 7,900 daily keys remain pending; no source-unmatched conclusion is possible. Stage 1G remains OPEN; extraction QA NOT RUN, preflight QA passed. No raw daily scan, target interpretation or licensed-data commit.

**One next action:** Restore WRDS PostgreSQL connectivity from the Codex execution environment, then resume the same approved extraction without broadening scope.


---

## RL-040 — Stage 1G approved WRDS extraction completed; extraction QA passed
**Date:** 2026-10-05

**Methodology check:** Re-read instructions, methodology and latest log. Scope restricted to approved extraction and schema/key/coverage/checksum QA; no endpoint/delisting economic interpretation, performance evidence, target-methodology change or new stage. User confirmed successful same-IP website/Duo login and authorized extraction with exactly one API login attempt.

**Preflight/authentication:** Source-cache size/mtime fingerprints and download-manifest selector SHA256 match. Twelve approved query jobs; no previously completed batches. Licensed selector/output directory confirmed gitignored. Updated extraction entry point to create WRDS Connection(autoconnect=False) and call the installed package's single engine-connection method, bypassing automatic fallback/retry. Explicit confirmed username, SSL and 90-second login timeout; no password printed or stored in repository. Exactly one API login succeeded, followed by one information_schema existence check; no authentication retry or reconnection. Connection closed cleanly after extraction. Session-loss handling prevents remaining data queries from implicitly reconnecting; completed batches remain intact.

**Approved extraction/row counts:** Full crsp.stkdelists, approved 19 columns: 1/1 batch, 29,833 rows / 29,833 PERMNOs. crsp.stkdistributions, approved 13 columns, all event dates for 3,064 selected PERMNOs, batches <=500: 7/7 batches, 223,291 rows / 3,061 returned PERMNOs. All selected securities were included in the batch predicates; three have no returned distribution records, explicitly recorded in the local manifest without inferring why. No payment-date restriction. crsp.stkdlysecuritydata, four columns and only 7,900 exact requested keys, batches <=2,000: 4/4 batches, 7,900 rows / 1,774 PERMNOs. Twelve observation queries completed, no WRDS errors, no broadened scope.

**QA:** Approved column lists match all batch/final outputs; dates parse; nonnull security keys. Distribution keys (permno,disexdt,disseqnbr) and daily keys (permno,dlycaldt) unique; no unexpected securities/daily dates. Final row counts equal completed-batch sums, SHA256 checksums verified for every batch/final file. No exact duplicate rows; delisting security/date keys unique. All 7,900 requested daily keys match: zero unmatched or unexpected keys. Four local extraction tests passed, including single-login failure without retry. A local QA reporting conversion incorrectly called item() on a Python integer, then was corrected; no remote query was repeated.

**Local outputs:** data/interim/stage1g_extraction/stkdelists.parquet, stkdistributions.parquet, stkdlysecuritydata.parquet, download_batches/*.parquet and updated download_manifest.json. Manifest records row counts, source coverage, no-record distribution securities, unmatched daily keys, checksums, authentication attempt count and extraction QA. Licensed outputs/manifests remain uncommitted; only code/tests/log committed. Existing selectors preserved. No local raw daily scan.

**Decision:** Extraction QA PASSED. Stage 1G remains OPEN and primary target unfrozen. No event-ledger interpretation or target construction performed.

**One next action:** Obtain authorization for the cache-only endpoint/delisting/distribution-boundary diagnostic using the newly extracted event histories; do not execute that diagnostic in this step.

---

## RL-041 — Stage 1G event histories leave opening-price and received-asset valuation unresolved
**Date:** 2026-10-05

**Methodology check:** Re-read AGENTS.md, locked methodology, log through RL-040, boundary proposal, cached diagnostics and download manifest. Permitted evidence: official local CRSP definitions, exact event dates, observed prices/status, coverage, field integrity and numerical consistency. IC, Sharpe, PnL, model fit and forecasting performance prohibited. No target specification change, WRDS connection, download, raw-daily scan or new stage.

**Cache-only diagnostic:** scripts/19_audit_stage1g_event_resolution.py and src/data/stage1g_event_resolution.py verify all three extracted-file checksums and 6,699,101 unique cached signal keys. Administrative right-censoring excluded from the event-resolution cohort; the existing 8,686 censored signals retain their explicit censoring status. Local official CIZ Guide (July 2026) and calculations distinguish actual delisting, storage, amount and payment dates; source return flags/previous closing dates do not identify an opening fill. Ownership is entry_date < DisExDt <= exit_date. Contextual events between signal and entry are retained for explanation, never assigned to the new buyer. Pure same-security splits use 1+DisFacShr with six-decimal factor-precision checks. Same-date cash/split source amounts require the documented previous-share basis and a verified single-trading-period daily interval. No prices or received quantities imputed.

**Unresolved endpoint paths:** All 7,596 missing-entry observations (1,711 PERMNOs) lack a defensible observed opening execution price. DlyPrevDt, DlyRetMissFlg, positive volume, closing prices and event histories cannot supply that price. Among 6,916 flagged missing exits after valid entry (1,448 PERMNOs), 3,300 remain unresolved: 2,623 noncash/incomplete event terms (683 PERMNOs), and 677 amount/valuation timing cases (663 PERMNOs; 661 amount dates on exit and 16 after exit). The latter lack independent fixed-claim evidence establishing exit-opening wealth. The other 3,616 cases have complete cash-only matched bundles under the existing proposed no-reinvestment ledger, with terminal payment dated before exit and entitlement by exit; 723 have amount dates on exit and pass only through independent established cash-claim evidence, never amount-date equality alone. DelRet is checked for arithmetic consistency but is not substituted for an exit open or multiplied again into an already accounted payment. All 787 unflagged missing exits (465 PERMNOs) remain unresolved; 31 coincide with actual delisting on the exit date, 756 do not. Neither future next prices nor later aggregate payments establish planned exit-opening wealth.

**Unresolved distribution paths:** Broad factor/nonordinary review: 21,065 observations, 14,227 accounting-sufficient / 6,838 unresolved. With both observed endpoints: 12,586 observations (1,199 PERMNOs), 10,611 sufficient / 1,975 unresolved (296 PERMNOs). Received securities, rights, property or compound units lack confirmed conversion quantities and/or exit-time received-asset values; DisDivAmt cash-equivalent valuations and successor identifiers cannot replace those terms. Entry nonordinary boundary: 1,472, 11 sufficient / 1,461 unresolved; exit: 1,390, 726 / 664; interior: 5,584, 2,905 / 2,679. These are whole-path classifications: excluded entry-day entitlement does not resolve a missing opening price. Ordinary entry controls: 60,265, 60,144 / 121; ordinary exit controls: 60,020, 59,884 / 136. Categories overlap. Unique unresolved observations in the diagnostic cohort: 13,665 across 1,905 PERMNOs; no observation removed or assigned an invented zero/-100% label. Accounting-sufficient is not a frozen target or a full-panel target-validation result.

**Local outputs/QA:** results/tables/stage1g/event_resolution_paths.csv contains counts, rules, fields and limitations; event_resolution_reasons.csv, missing_entry_event_attribution.csv, missing_exit_event_attribution.csv, event_boundary_matches.csv and event_unresolved_cases.csv retain attribution and exact unresolved keys. data/interim/stage1g_extraction/event_resolution_cases.parquet retains the classified ledger. Licensed outputs remain local/uncommitted. Seven event/boundary tests pass, covering ownership boundaries, key uniqueness, unchanged endpoint counts and conservative cash-claim timing. Initial SQL alias parsing error was corrected locally; provisional conservative cash/boundary classifications were refined using documented source bases and independent event claims, without changing locked methodology.

**Decision:** Stage 1G remains OPEN; no complete final five-day target rule is available. Missing entry execution cannot be recovered; unresolved held positions must remain explicitly unvalued rather than being retrospectively discarded. Current extracts lack opening measurements, received-asset conversion terms and/or opening-time claim values. AGENTS.md, README and methodology unchanged because the gate cannot close.

**One next action:** Review the exact unresolved-key inventory to decide whether an independently observed opening-price/received-asset terms source can resolve these measurements under the same economic horizon; do not extract more data or freeze exclusions in this step.

---

## RL-042 — Stage 1G target constructed; approved accounting and missing-label contract frozen
**Date:** 2026-10-05

**Authorization/methodology check:** User approved the Stage 1G closure proposal and explicitly froze the five-day next-open retained-asset/cash/receivable ledger and missing-label policy. Re-read AGENTS.md, methodology, RL-041, boundary proposal and reusable diagnostics. Evidence restricted to coverage, key/date integrity, official field/event accounting and numerical consistency. No IC, Sharpe, PnL, model fit, WRDS queries, new sources or raw-daily scans. No changes to eligibility, horizon or other locked specifications.

**Frozen specification:** Signal after close t; buy one post-event share at observed open t+1; planned exit open t+6 on the global calendar. Target is (retained parent/successor boundary values + cash + established measurable receivables)/entry_open - 1. Entitlement entry_date < DisExDt <= exit_date. No reinvestment and zero cash interest. Pure split quantities use verified event share multipliers; same-date cash/split amounts preserve CRSP's previous-share basis. Measurable cash-only settlements replace the parent with independently established cash claims, without also multiplying DelRet. Received assets require verified quantities and exit-boundary values; unresolved claims remain missing. No interpolation, forward-fill, later price, shifted horizon or unsupported zero/-100% labels.

**Implementation:** scripts/20_construct_stage1g_targets.py and src/data/stage1g_targets.py reuse 32 cached boundary partitions, the RL-041 ledger, extracted event histories and the existing daily cache. Output has identifiers, signal/entry/exit dates, target_5d, mutually exclusive label_status, explicit label_reason, retained-parent quantity, security/cash-claim components and robustness event flags. All output metadata are outcomes/labels, not predictors; no future-eligibility re-filtering. Fixed ordinary cash-only paths use complete single-period source daily amounts; explicit event paths check amount sums against that source share basis, transport quantities chronologically, and retain cash without reinvestment. Unknown successor/rights/property paths never acquire manufactured quantities or numeric labels.

**Exact category reconciliation:** 6,699,101 rows / 6,699,101 unique eligible keys. measurable_ordinary_event_adjusted 6,673,134; missing_entry_measurement 7,596; measurable_cash_only_delisting 3,616; valid_entry_unresolved_exit_wealth 4,087; administrative_right_censoring 8,686; other_unresolved_corporate_action 1,982. Numeric labels 6,676,750 (99.6663582173%); missing labels 22,351. No discrepancy from the approved closure proposal. The 6,069 valid-entry unvalued paths remain explicitly present for later bounds/sensitivity analysis; numeric-label evaluation is conditional on measurability, not asserted to be unbiased for the full eligible population.

**QA:** Input extraction checksums verified. No duplicate/missing/extra eligible keys; entry/exit dates unchanged by full outer-join verification. All missing labels have reasons. Numeric labels exist only in the two measurable categories; all numeric labels finite. All entitled event-path cash dates represented, source cash-basis checks passed, explicit share products reconcile to RL-041 quantities. Cash delistings have zero terminal parent quantity/value and positive verified cash wealth. Wealth identity maximum absolute error 1.1641532183e-10 dollars. Twelve focused tests passed: plain opening-price identity; entry exclusion/exit inclusion; no reinvestment; same-date pre-share cash with split; exit split; cash-settlement replacement without double return; unavailable entry; local full-dataset integrity; inherited ownership/calendar/cached-conservative-resolution checks. No classification contradiction found.

**Local licensed outputs:** data/interim/stage1g_targets/targets_5d.parquet, part_00.parquet through part_31.parquet, manifest.json. Manifest includes construction timestamp, source fingerprints, category/label counts, metadata-only role and QA. Directory confirmed gitignored; no licensed outputs or secrets staged. Only code/tests/documentation committed.

**Decision:** Stage 1G CLOSED; target specification and explicit missing-label contract frozen in docs/methodology.md. AGENTS.md and README handoff synchronized; old boundary proposal marked historical/superseded. No feature engineering, training or new stage started. Later validation must report coverage against the original denominator and assess selection/bounds for unresolved entered holdings rather than silently deleting them.

**Next stage:** Stage 2 — Feature engineering. Not begun.

---

## RL-043 — Stage 2A feature framework proposed; computation not started
**Date:** 2026-10-06

**Methodology check/current state:** Read AGENTS.md, methodology, log through RL-042, README, Stage 1G target manifest and final dataset schema. Stage 1G CLOSED: 6,699,101 eligible keys, 6,676,750 numeric labels; outcome metadata are not predictor inputs. Scope is proposal only. Evidence allowed: economics/interpretability, official field definitions, point-in-time timing and data integrity. IC, Sharpe, PnL, model fit and any forecasting-performance evidence prohibited. No Stage 1 contract change.

**Proposal:** docs/stage2a_feature_framework_proposal.md defines reversal_5, momentum_60_skip5 (55 daily returns ending t-5), volatility_20, turnover_20, dollar_liquidity_20, dollar-volume shock versus the previous 20 days, event-free gap_1 and intraday_1. Features end at close t, use global-calendar windows and historical rows without retrospective eligibility filtering. Strict admitted-return windows exclude multi-period/delisting/ambiguous received-asset amounts unavailable at the as-of close. Ordinary cash and verified pure splits require source consistency. Gap-event adjustment deferred rather than misclassifying ex-date effects as gaps. DlyCap dollar conversion is 1000; turnover is a total-cap proxy, not free float. Historical revision-free vintages are not established by the existing snapshot.

**Preprocessing/missingness proposal:** Same-date all close-t eligible observations, independently of future label availability; finite-value 1st/99th percentile clipping with linear quantiles, population z-scores, >=30 observations, explicit constant-section flag. Return windows complete; liquidity windows >=15/20 with full calendar span and recorded valid count. Missing raw/z values and reasons preserved; optional later zero/mask model encoding is not performed now. Reject global normalization, forward/back-filling, performance-based windows and learned imputation at this stage. Sector/industry neutralization deferred pending point-in-time classification and separately logged interpretation. These are proposals, not frozen feature settings.

**Architecture/output assessment:** Separate allowlisted feature inputs from targets; reusable src/features modules and scripts entry points planned but not written. Preserve every target key/status through a later left join. Reproducible coverage, missingness, distributions, clipping/dispersion and pairwise feature-correlation tables and descriptive heatmaps/time series proposed under results/tables/stage2a and results/figures/stage2a. Explicitly assess outputs at every material later sub-stage. No full feature computation, feature code, charts or predictive result produced in this proposal step. Data-driven figures await real validated features.

**Remaining QA/decision:** Small synthetic/local-fixture tests must verify availability masks, units/status, after-t perturbation invariance, calendar/gap/warm-up handling, same-date preprocessing and label-mask independence before scaling. Stage 2A proposal prepared; Stage 1G frozen specification unchanged. No WRDS, raw-daily scan, ML or portfolio work.

**One next action:** Approve the proposal, then implement only the small feature-framework QA fixture before full-scale computation.

---

## RL-044 — Stage 2A synthetic feature framework QA passed; historical scaling not authorized
**Date:** 2026-10-06

**Methodology check:** Re-read approved feature proposal, AGENTS.md, methodology and latest log through RL-043. User authorized only small synthetic/local-fixture implementation. Evidence restricted to calendar positions, unit/accounting identities, missingness, point-in-time isolation and numerical preprocessing. No CRSP panel read, raw scan, WRDS, IC, Sharpe, PnL, model or portfolio results. Stage 1G contract/labels unchanged.

**Implementation decisions:** src/features/baseline.py implements all eight baseline definitions on an externally supplied unique sorted global calendar. Missing security rows remain absent positions; return windows are strict; turnover/liquidity permit >=15/20 and shock requires >=15 prior observations plus valid current volume. Dollar cap conversion is exactly 1000*DlyCap. Zero observed volume remains valid; unknown volume is not zero. src/features/returns.py checks synthetic single-period anchors, actual-price evidence, source identity, known-by-source-close event evidence, and conservative delisting/nonordinary exclusions. Verification fields are explicit fixture evidence; live provider/status/event mapping remains a required small-sample check.

**Exact gap convention:** Numerator observed DlyOpen_t; denominator observed actual DlyPrc at the preceding global calendar date, never source previous-price fallback or an older available row. Require positive observed prices, adjacent source date and verified event-free interval. Intraday denominator is observed same-day DlyOpen. Event-day gap decomposition remains deferred, not silently adjusted with later values. Source return admission additionally compares DlyPrevPrc to the observed adjacent close. Definitions match the approved proposal; no window/performance tuning.

**Preprocessing:** src/features/preprocessing.py groups date x feature using finite values independently of target/status: linear 1st/99th percentiles, preserved raw/clipped/z columns, same-date mean/population SD, >=30 finite observations. Constant cross-sections have observed z=0 plus degeneracy flag; insufficient sections and invalid/missing inputs retain explicit reasons. No filling. Review found nonfinite raw values could inherit an observed reason; corrected to explicit nonfinite_or_invalid_raw and added regression coverage.

**QA/results:** 24 focused tests passed: fixed calendar windows despite absent rows; exactly 55 momentum returns t-59:t-5 and exclusion of latest five; compounded reversal t-4:t; sample volatility on 20 complete returns; unit conversion and 15/14-valid thresholds; excluded-current shock denominator; zero volume; missing/invalid/quote-only prices; event-free gap/intraday identity; pure split/dollar-volume consistency; ordinary cash reconstruction; multi-period/delisting/future-known/nonordinary rejection; after-t perturbation invariance; target/status independence; no filling; separate raw/clipped/z; date-local quantiles/population SD; constant and insufficient cross-sections; duplicate-feature-key rejection. Initial collection failed on Python 3.9 evaluating float|None; postponed annotations fixed compatibility before rerun. No specification change.

**Reproducible outputs/visual assessment:** src/features/qa.py generates 85 synthetic weekday-calendar rows only. scripts/21_qa_stage2a_fixture.py writes the 16-row results/tables/stage2a/synthetic_feature_qa.csv (complete/missing-row scenarios). Synthetic data are not licensed CRSP observations. A table is sufficient to inspect counts, fixed boundaries and reasons; an additional figure was judged unnecessary for this fixture step. docs/stage2a_fixture_qa.md records reproduction, exact denominator and limitations. No empirical historical coverage claim.

**Decision/next action:** Synthetic Stage 2A QA PASSED. Ready for a small bounded historical sample to validate the live field/event adapters, authoritative calendar and admission-mask coverage. Not yet approved or run for full-panel computation; no ML. Snapshot revision-free availability remains unresolved. Next action: authorize a small historical sample framework QA.

---

## RL-045 — Stage 2A bounded historical source audit exposes event-verification ambiguity; full construction stopped
**Date:** 2026-10-06

**Authorization/methodology check:** User authorized autonomous bounded historical QA and full construction only if that QA passes without material methodology/PIT issues, with explicit stop gates. Re-read AGENTS.md, methodology, approved feature proposal, fixture documentation and log through RL-044. Evidence permitted: official CRSP field/flag definitions, source coverage, exact event-date/source-field consistency, keys/calendar and numerical integrity. No target correlation, IC, Sharpe, PnL, forecasting/model/portfolio evidence. No target values/status read, WRDS connection, raw-daily scan or target-contract change.

**Bounded source audit:** Existing partition 00 restricted to 2020-11-01 through 2021-04-30: 32,010 rows, 275 PERMNOs, 124 consecutive locked global-calendar positions, 4,971 close-date eligible keys, zero duplicate sample keys. Single-period TR/TR previous-price checks find zero mismatches against the cached preceding observed price (this numerical check does not alone certify calendar or event availability). Local official CIZ User Guide July 2026 p17 confirms DlyVol is raw shares and DlyCap thousands of dollars; price flags p89 confirm TR closing trade; duration codes p90 establish D1/D2/D3/D4/DU as one trading period with different calendar-day lengths. These unit/flag definitions agree with synthetic QA.

**Material counterexample:** Independently inspect at most 50 existing event records dated 1993–2025 with zero/null event amount and zero share/price factors (actual census eight records), using only their exact cached security/date rows. Two eligible, positive-open/TR-close observations have DlyFacPrc=1, DlyOrdDivAmt=DlyNonOrdDivAmt=0 and DlyDelFlg=N, yet matched StkDistributions detail types are URTSD (Unknown Rights Distribution) and SECRD (Rights Distribution, payment OP). Thus the daily zero-effect screen does NOT certify an event-free interval or verified absence of ambiguous received rights. No inference is made that the observed parent-price ratios are numerically incorrect; the issue is the approved event-free/admitted-total-return definition and missingness policy. Other corner cases include delisting/payment events, which are not mistaken for this screen. Exact licensed identifiers/dates/source prices remain in data/interim/stage2a_historical_qa/event_screen_counterexamples.json, not committed.

**Coverage and selection concern:** Existing StkDistributions extraction is restricted to 3,064 PERMNOs chosen from Stage 1G holding-window exceptions/controls, as documented in source selector code. In this bounded sample, 5,251 rows/43 securities belong to that extracted set; 26,759 rows/232 securities do not. Among 4,971 eligible sample keys, 974 belong to securities outside the selected extraction. This is event-history scope, not measured feature coverage. No returned event for an unqueried security is not evidence of no event. Using this outcome-selected scope itself as event_verified or a feature-missingness/predictor mask risks dependence on future holding-window outcomes. No such mask or feature value was constructed.

**Field evidence/alternatives:** Official daily schema documents DlyDistRetFlg as distribution-return impact type. It is absent from existing daily-cache schemas and the saved original daily schema; additional flags cannot be assumed available. Its no-effect interpretation must be checked before treating it as event-free certification; a return-impact flag may not establish actual absence of a zero-valued rights event. Alternatives are a globally consistent, through-t event-verification source/admission policy, or a revised explicitly daily-effect-based gap/return policy. Those choices change event admissibility/missingness or require additional source evidence and need research-lead review. Existing subset histories can expose inconsistencies but cannot automatically become a population feature mask. No new data sought/downloaded.

**Reproducibility/outputs/QA:** scripts/22_audit_stage2a_historical_sources.py and src/features/historical_source_qa.py reproduce the bounded audit without constructing feature labels or consulting target status. results/tables/stage2a/historical_source_verification_qa.csv records compact safe aggregate counts. results/figures/stage2a/historical_event_history_coverage.svg visualizes only bounded source coverage, explicitly not feature coverage or predictive performance. Local manifest records failed historical feature-verification gate. Twenty-five fixture/source tests pass, including a regression demonstrating that zero-effect fields alone cannot establish verified event-free status. Aggregate outputs and code/docs only committed; licensed details stay ignored.

**Decision:** Stage 2A remains OPEN at the mandatory material ambiguity / uncertain point-in-time verification gate. Full 1993–2025 feature construction and preprocessing NOT RUN; no full-panel coverage counts available. No approved feature/preprocessing definition silently changed. Stage 1G stays CLOSED/frozen. Prior full-panel authorization was conditional on passing historical QA; condition is not met. Push not attempted while this incomplete sub-stage awaits review.

**Required review / one next action:** Decide the globally consistent through-t corporate-action verification/admission rule and supporting evidence before further historical feature construction. Do not resolve this by declaring missing histories event-free or by applying an outcome-selected coverage mask.

---

## RL-046 — Stage 2A review preserves feature definitions; global outcome-independent event evidence authorized
**Date:** 2026-10-06

**Review decision:** User rejected the daily-impact-only alternative and preserved existing Stage 2A definitions/preprocessing. Authorized minimum global CRSP event evidence: complete StkDelists history and complete StkDistributions with DisExDt in 1993–2025, retaining zero-valued, rights, unknown and all other event types. Only through-t effective dates/evidence may influence features; no target/status/exception-set selection. DlyDistRetFlg cannot alone certify event absence without official supporting semantics. Stage 1G unchanged.

**Methodology check/execution plan:** Re-read instructions, methodology, proposal and log. Existing 29,833-row complete delisting extract will be checksum-verified/reused, not re-downloaded. Global distributions use all PERMNOs and only ex-date bounds, four disjoint batches (1993–2001, 2002–2010, 2011–2019, 2020–2025); no payment-date/value/type filters. Confirmed fields from earlier live schema, adding DisDeclareDt as supporting dated evidence. Local ignored outputs under data/interim/stage2a_events/. Reusable extraction code supports completed-batch checksum resume; no reconnect or authentication retry. Existing outcome-selected event cache is not a substitute. Exactly one login attempt authorized, with Duo approval; stop immediately on failure. No passwords printed/stored and no raw daily scan. Full feature processing remains conditional on adapter/source QA passing.

**Next action:** Execute this single-login extraction; record the outcome before any adapter/full feature processing. No performance evidence permitted.

---

## RL-047 — Global Stage 2A event extraction and adapter QA completed; declaration/ex-date timing review gate
**Date:** 2026-10-06

**Execution/QA:** Exactly one authorized WRDS login succeeded with Duo; no authentication retry or reconnection. Four global DisExDt batches returned 149,586 / 155,421 / 194,996 / 170,974 rows: 670,977 distributions, 24,384 PERMNOs, 1993-01-04 through 2025-12-31. All securities/event types/zero-null amounts retained; no outcome, amount, type or payment-date restrictions. Confirmed schema includes DisDeclareDt as supporting timing evidence. Batch/final keys, dates, counts and checksums pass. Complete 29,833-row delisting table reused after checksum verification. Connection closed cleanly. No WRDS daily observations downloaded, no raw daily scan; licensed files/manifests remain ignored under data/interim/stage2a_events/.

**Outcome-independent layer:** src/features/events.py implements complete-scope per-PERMNO (start,end] effective-date evidence, end <= as_of, with explicit true/false/REVIEW states. No target/status or Stage 1G extraction-membership inputs. Payment dates, eventual amounts/statuses and DelRet are not admission inputs. Zero-valued rights/unknown/property events remain events. Actual last-price DelistingDt is not treated as a public notice date to retrospectively mask an earlier feature; stored delisting-return intervals use DelDlyDt and source flag checks. This is evidence/admissibility scaffolding, not a silently adopted new feature/missingness definition.

**Bounded rerun:** 32,010 rows, 275 securities, 124 market dates, 4,971 eligible keys. Global event scope verified and both original eligible rights/unknown-rights counterexamples detected. Previously outside-scope sample keys do not inherit missingness from the Stage 1G extraction. Source-date reason census: 31,629 globally event-absent intervals, 324 supported dated event intervals, 50 cash-term declaration timestamps missing, seven stored-delisting-return intervals. Among eligible sample keys: 4,930 absent / 41 supported. These are evidence classifications, not computed feature coverage or permission to ignore unresolved time provenance elsewhere in the full history.

**New material timing ambiguity:** Local official CIZ User Guide (July 2026), pp12–13, defines DisExDt as first trade without distribution rights and DisDeclareDt as board declaration date, not a database publication/revision timestamp. Global history has 109 DisDeclareDt > DisExDt records: 81 USD CDIV, ten USD SDIV, and other event types. A prespecified bounded probe of the first 20 such CD/SD cash records by ex-date finds all 20 daily rows carrying nonzero cash amounts on the earlier ex-date; one belongs to the locked close-date eligible sample. Fields cannot distinguish erroneous/later-restated declaration metadata from retrospectively assigned amounts or different effective/information dates. This is not proof that earlier market information was absent, but verified through-t availability cannot be asserted. Another 61,542 declaration dates are missing across all distribution kinds; absence of that field does not itself establish look-ahead. Adapter flags contradictory chronology REVIEW; it does not automatically admit values, introduce future-derived blackouts or choose a new missingness policy. Full construction STOPPED at the user-defined ambiguous-evidence/PIT gate, not at a routine engineering choice. No daily-impact-only alternative adopted; Stage 1G unchanged.

**Reproducibility/outputs:** scripts/23_extract_stage2a_events.py (explicit execution, single login, checksum resume, complete-cache no-login path) / src/data/stage2a_event_extraction.py. scripts/24_qa_stage2a_global_events.py / src/features/global_event_qa.py reproduce offline source/corner-case/timing QA. Safe aggregate tables global_event_verification_qa.csv and bounded_global_event_adapter_reasons.csv under results/tables/stage2a; global_event_declaration_chronology.svg under results/figures/stage2a; documentation docs/stage2a_global_event_layer.md. Exact licensed cases, batches and manifests are local only. No IC, target correlations, Sharpe, PnL, forecasts, models, portfolios or full-panel features/preprocessing.

**Engineering/tests:** Initial package-version probe used absent wrds.__version__; runtime import itself succeeded and no login was attempted by that probe. Removed hardcoded username from reusable extraction code in favor of explicit CLI argument; passwords remain in the existing user authentication setup, never printed/stored. Thirty-three Stage 2A fixture/adapter tests pass. Full repository run initially had two stale uppercase-fixture vs lowercase-default failures; corrected explicit test schema mapping/native cap units and added lowercase-default coverage, without changing production data handling or methods. All 59 repository tests now pass. SVG source and code/diff checks completed; only safe aggregate outputs/code/tests/docs staged.

**Decision/required review:** Stage 2A remains OPEN. The RL-045 global-coverage problem is resolved, but the historical point-in-time gate is not closed. Review the authoritative information-time meaning and treatment of conflicting/missing declaration dates before population feature construction. No automatic data substitution or missingness change. No push while this incomplete sub-stage awaits review; stop here. No predictive evaluation started.

---

## RL-048 — Review approves effective-date event timing with daily-term reconciliation
**Date:** 2026-10-06

**Review decision/methodology check:** Preserve approved Stage 2A features. Provider spelling is DisDeclareDt (SQL disdeclaredt); the review's DisDeclaredDt refers to this same field. Economic event dates, not declaration metadata chronology, govern through-t admission. Declaration date is QA only. Conflicting chronology must reconcile to contemporaneous/earlier cached daily terms; failed reconciliation produces explicit timing_ambiguous affected intervals, never later repairs. Missing/conflicting declaration dates do not imply event absence. No frozen Stage 1 changes; no outcomes/performance evidence. Re-read methodology, proposal, handoff and RL-047.

**Smallest action:** Offline census of all 109 conflicts, exact ex-date daily rows and same-date complete event groups, checking cash/factor totals and source-return identity. Record current eligible exposure as QA only; it cannot determine admission. No WRDS/authentication or raw-file scan. Continue only after this bounded timing QA and source adapter tests establish the approved missingness treatment.

---

## RL-049 — All chronology conflicts audited; effective-date timing gate passed with explicit ambiguity masks
**Date:** 2026-10-06

**Result:** All 109 conflicting records / 109 security-exdate pairs audited: 92 reconcile to same-exdate complete cash/factor groups and daily return identity; 17 remain ambiguous. The first engineering pass wrongly inferred ordinary/nonordinary from payment frequency (CD vs SD); corrected to official DisOrdinaryFlg, reconciling 12 additional SD/ROC records without changing any feature definition. Remaining cases: one absent daily row; two factor mismatches; two missing price anchors; two rights; ten received-property/security/currency groups. Three ambiguous event-date records enter the close-date eligible sample. A conservative 60-global-date exposure bound contains 180 unique eligible keys; this is not an actual feature-missing count and does not select event admission. Reconciled events include six eligible event-date records. Full counts are in results/tables/stage2a/timing_conflict_reconciliation.csv; exact details local only.

**Decision:** The 17 unverified events can receive explicit timing_ambiguous source/affected-strict-window masks under the user-approved policy; supported cash/splits must still meet existing admission requirements. No numeric event value is invented. Received/nonordinary paths remain excluded as before. Missing declaration metadata no longer blocks otherwise supported dated events; conflicting metadata requires daily reconciliation. No unresolved material pattern requires a new feature definition. Timing gate PASSED under the explicit ambiguity policy, preserving snapshot-vintage limitations. Both legal-rights corner cases remain events. No later declaration/payment metadata repairs historical values; no outcomes used.

**Implementation/QA:** Effective-date index is globally complete and outcome-independent. Production event intervals use (previous global market date,current date], including effective events on nonmarket dates: 109 global event records are on nonmarket dates and map only to the containing subsequent market interval, never to an earlier feature. This is interval membership, not a shift of execution/target horizons. Range windows use market-calendar indices, not available-security rows. Initial census timestamp/string mismatch and bounded-report reserved SQL alias were corrected before outputs; no data or method changed. Pure fixture/calendar/units/admission/preprocessing tests pass. Bounded production-vs-pure raw feature/valid-count comparisons follow before full cached construction.

---

## RL-050 — Stage 2A full cached baseline construction/descriptive QA passed; stage CLOSED
**Date:** 2026-10-06

**Authorization/methodology check:** Proceeded under conditional full-panel authorization after RL-049 passed with explicit approved ambiguity masks. Eight feature definitions, clipping/minimum-count/standardization/missingness and deferred neutralization unchanged. No target/status availability used in construction or preprocessing; target relation read only for identifier reconciliation. No raw scan, network/authentication or new extraction. Frozen Stage 1G untouched.

**Implementation:** src/features/panel.py and scripts/26_construct_stage2a_features.py build calendar-RANGE windows from 64,959,561 cached daily rows across 32 partitions, avoiding dense filling or security-row shifts. All original close-t eligible keys retained. Fingerprinted/checksummed atomic raw batches and final outputs; contemporaneous source identity/actual trade-price/adjacent anchors; effective global event interval; explicit timing/event masks. Eight raw baselines exactly as approved; raw/clipped/z, valid counts and missingness reasons preserved. Dollar cap conversion is 1000*DlyCap. Industry/sector neutralization and model missing-value encoding remain deferred.

**Bounded QA:** 4,971 unique eligible keys preserved from the 32,010-row bounded source sample; deterministic first-three securities/latest-sample-date comparisons match pure fixture logic on all eight raw values and valid counts (24 comparisons). Production tests additionally perturb after-t inputs/eligibility, remove calendar rows, test skipped momentum and interval-local timing masks. Both original rights/unknown-rights corner keys remain in the final panel and have missing gap/reversal/volatility, demonstrating that daily zero-effect flags did not override legal events.

**Full reconciliation:** 6,699,101 rows / unique keys; zero duplicates and zero key-set differences in either direction against frozen target identifiers. Numeric/raw and standardized counts: reversal 6,696,422; momentum 6,635,431; volatility 6,681,241; turnover 6,698,418; dollar liquidity 6,698,418; volume shock 6,697,073; gap 6,630,530; intraday 6,693,015. Coverage ranges 98.976415% (gap) to 99.989805% (liquidity), not the preliminary commentary's momentum lower bound. All missing features retain reasons; no target-status attrition/re-filtering. Explicit timing masks affect 15 reversal / 165 momentum / 60 volatility / three gap keys, with overlap. Target/label status remains unchanged in its separate frozen relation.

**Additional factor/source QA and correction:** No comparable source factor changes lack global event histories. Twelve preliminary factor comparisons exceed nominal 1e-6 due rounding boundaries or simultaneous splits; four substantive combinations are not certified by a simple per-event product. Official Calculations p7 establishes simple-split factor+1 and dated interval scope, not a general multiple-event combination. Enforced existing exclusion of unverified factor changes instead of inventing a combination rule; regenerated all batches. The guard introduces no missing eligible feature observations. Nonconflicting metadata cash amounts are never substituted for contemporaneous daily terms. This is an admission-engine correction under the approved definition, not a new feature/missingness rule. Construction fingerprints sealed against actual panel/pure-reference modules; standalone adapter ordinary-flag alignment leaves SQL outputs unchanged.

**Preprocessing/integrity QA:** Same-date type-7 1st/99th clipping and mean/population-SD z-scores, minimum 30, constant zero/flag policy. Raw/clipped/z separate. Zero nonfinite, missing-reason, clipping-bound, cross-sectional-count or future-input violations. Maximum absolute daily z-mean error <7e-14 and nonconstant z-SD error <4e-15. No additional finite raw observations lost during preprocessing. Relevant full repository suite: 64 tests PASSED.

**Failures/engineering record:** Initial local .venv lacked DuckDB, so used existing analysis Python with required installed packages; no installation/authentication. Census normalized provider timestamps to dates. Bounded/report SQL reserved aliases corrected. Initial descriptive plot report redundantly rescanned exported dispersion aggregates and stalled; stopped only task-owned draft report, reused exported aggregates and sorted monthly-median dispersion for the figure; representative dates loaded once each. Regenerated final reports after factor guard and rights regressions. No method choice used performance evidence. Exact licensed observations/manifests remain ignored.

**Reproducible evidence/visual assessment:** scripts/25_qa_stage2a_timing.py, scripts/26_construct_stage2a_features.py (--full), scripts/27_report_stage2a_features.py and reusable src/features/{timing_qa,panel,report}. Tables under results/tables/stage2a: timing_conflict_reconciliation, bounded_feature_qa, feature_definitions, coverage_by_year, missingness_reasons, distribution_summary, cross_sectional_dispersion, preprocessing_diagnostics, correlation_after_preprocessing. Four descriptive figures under results/figures/stage2a: annual_feature_coverage, feature_correlation, raw_dispersion, representative_distributions. Representative dates fixed as first June market dates in 2000/2010/2020/2025; dispersion figure uses monthly medians of the complete daily table. Feature-to-feature equal-date mean correlation shows volatility/turnover overlap (~0.672); no selection/redefinition from that finding. No target correlations, IC, Sharpe, PnL, forecasts, models or portfolios.

**Decision/handoff:** Stage 2A CLOSED under the approved economic-date/missingness contract. Local licensed output data/interim/stage2a_features/parts/part_*.parquet plus raw batches, cross-sectional stats and QA manifest (qa_passed true). Methodology/README/AGENTS updated; safe code/tests/docs/aggregate tables/figures only committed. Static snapshot-vintage limitation and explicit missing paths remain documented; they are not hidden or imputed. Stop at predictive-evaluation boundary. Next action: obtain research-lead authorization/specification for baseline signal evaluation with walk-forward and overlapping-label controls; do not begin it automatically.
