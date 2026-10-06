# Stage 4C successor quantity recovery — ratio verified, executable inventory OPEN

## Evidence gate and scope

Preserve Stage4A strict identification and Stage4B capped-exit assumptions and every prior artifact. No prices, price ratios, later values, target returns or portfolio outcomes establish quantity. No WRDS login, extraction, raw daily scan, holdout access or portfolio performance. Review cached fields first, then official CRSP documentation, then independent contemporaneous terms. A new economic ambiguity requires review before execution.

## CRSP evidence

The cached March31 event and delisting record agree on a stock merger and a linked ADS successor. Local CRSP CIZ User Guide July2026, printed pages12–13: DisPERMNO links the received security; DelPERMNO links the subsequent security. Neither specifies quantity. DisFacPr is explicitly set to -1 for delisting distributions. DisFacShr adjusts the original security's shares/volume across distributions; no documented rule identifies a merger entitlement by interpreting its -1 as a zero quantity or exchange ratio. Appendix codes OS=Other Security, SP=Security Payment, SECMRG=Security Payment–Merger and STK=Stock support event classification, not a quantity. DisDivAmt and DelDivAmt are amounts, not received-share counts. The calculations guide's cumulative factor rules do not supply the missing merger quantity.

All documented StkDistributions and StkDelists columns were reviewed. No explicit received-share entitlement/exchange-ratio field appears. A repeated narrow extraction of those tables cannot repair this omission, so no Duo login or WRDS query was justified. Security names/classification cache identifies Household International ordinary common stock and HSBC Holdings ADS, excluding a mistaken ordinary-share/ADS basis.

## Independent legal terms

[Household November14,2002 Form8-K](https://www.sec.gov/Archives/edgar/data/48681/000004868102000447/mergerhihsbc8k.htm) independently states 2.675 HSBC ordinary shares per Household common share, with an ADS election of0.535; each ADS represents five ordinary shares. This is a legal ratio, not a price-derived estimate.

[HSBC February27,2003 acquisition circular](https://www1.hkexnews.hk/listedco/listconews/sehk/2003/0227/ltn20030227105.pdf), printed pp81–84 (PDF indices86–89), §§2.1–2.2 and5.1–5.5: the choice belongs to the holder; missing elections must be completed. Delivery follows certificate surrender/election. Fractional interests become cash under one of two issuer-selected methods: agent sale proceeds or the effective-date closing quotation. These methods are not interchangeable. Whole-security delivery, fractional cash and an entitlement claim must remain distinct. The source predates all three cohorts; later employee-plan conversions cannot certify this simulated account's election, settlement or short lender terms.

The linked CRSP security and legal ratio establish the **ADS-equivalent economic entitlement**, not evidence of an account election or opening tradability:

```
ordinary_share_entitlement = signed_verified_parent_quantity * 2.675
ADS_equivalent_entitlement = ordinary_share_entitlement / 5
                          = signed_verified_parent_quantity * 0.535
```

## Cohort and obligation QA

All six cached unresolved positions (three cohorts per candidate) pass exact entitlement arithmetic and side preservation. Both candidates have the same two long cohorts signaled March21/24 and one short cohort signaled March27. Entries March24/25/28 all precede the effective merger boundary; no entry-day rights assumed. Each ADS-equivalent result is nonintegral. Long amounts are positive economic rights; the short amount is a negative equivalent obligation, not automatically a verified lender delivery basket. Earlier established parent cash entitlements remain separate; no double counting into the exchange ratio.

Licensed per-cohort signed parent quantities, equivalent claims, deadlines and mapping reasons remain local in data/interim/stage4c/cohort_entitlement_mapping.parquet. Safe counts/ratio evidence are results/tables/stage4c/successor_recovery_gate.csv. No rounding, cross-sleeve aggregation or netting establishes actual inventory. All tradable_successor_quantity values remain missing. Focused historical recheck of the Stage4B inventory prerequisite therefore remains unresolved for all six positions.

## Decision

**Legal ratio identification PASSED; executable inventory recovery OPEN.** Full Stage4B feasibility rerun is deferred at the newly identified material election/fractional-cash/delivery/short-obligation gate. It would require an unapproved assumption to feed the gross fractional claim to a market liquidation. A positive successor open cannot eliminate these unknowns. Preserve prior Stage4B report and halt result as originally computed; do not present it as an updated full-period result.

119 repository tests pass, including five successor tests for exact ADS basis, signed fractional obligation, no automatic inventory certification and invalid/sentinel ratios. scripts/34_stage4c_successor_gate.py reproduces the six-cohort arithmetic and aggregate table and verifies Stage4A/4B artifact hashes unchanged. A compact table is sufficient; a new figure adds no evidence at this identification gate.

Next action: research-lead review of how verified entitlements become executable inventory, including ADS election, exchange delivery, fractional cash and short lender obligations. Do not assume fractional ADS trading, zero cash-in-lieu or automatic next-open delivery, expand the cap, rewrite frozen Stage1 labels or compute performance.
