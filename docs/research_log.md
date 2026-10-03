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
