# Stage 1B Security Metadata QA

## Metadata integrity

The CRSP CIZ Names/history extract contains:
- 191,048 rows
- 40,518 unique PERMNOs
- no missing interval start/end dates
- no invalid date intervals
- no overlapping intervals

The historical range extends from 1925-12-31 through 2025-12-31.

## Point-in-time join

The candidate liquid daily panel was joined using:

```
daily.permno = names.permno
AND daily.date BETWEEN SecInfoStartDt AND SecInfoEndDt
```

The annual metadata match rate is 100% in every year from 1993 through 2025.

This closes the metadata completeness gate.

## Classification frequencies

Observed metadata classifications include:

- SecurityType: EQTY, FUND, DERV, and historical unknown/missing records
- SecuritySubType: COM, ETF, CEF, ATR, UNK
- ShareType: NS, AD, SB, UG, CE, and historical missing records
- IssuerType: CORP, ACOR, REIT
- USIncFlg: Y / N
- PrimaryExch: Q, N, X, A, R, B, I
- TradingStatusFlg: A, D, X, S, H

The historical unknown records are largely associated with non-active/dead historical states and do not invalidate the point-in-time join.

## Candidate common-equity definition

Baseline classification candidate:

```
SecurityType = EQTY
SecuritySubType = COM
ShareType = NS
USIncFlg = Y
IssuerType IN (ACOR, CORP)
```

This identifies 112,197 metadata intervals and 26,914 PERMNOs.

## Remaining decision

Before the universe is locked, we must specify:
- PrimaryExch eligibility
- whether TradingStatusFlg must be active at signal formation

The traditional CRSP NYSE / AMEX / NASDAQ baseline corresponds to PrimaryExch N / A / Q when combined with regular-way active trading in the CIZ-to-SIZ mapping.

A final cross-tab of exchange and trading status within the candidate common-equity liquid universe will determine whether exclusions of R/B/I/X materially affect breadth.
