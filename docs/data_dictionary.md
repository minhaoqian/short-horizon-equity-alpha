# Data Dictionary — v0.2

The first data layer is CRSP CIZ daily US stock data. WRDS currently references the complete daily security table as `crsp.StkDlySecurityData`.

## Identification

| Field | Purpose |
|---|---|
| PERMNO | primary historical security identifier |
| PERMCO | company identifier |
| DlyCalDt | trading date |
| ticker | display only; never the primary historical join key |
| company/security name | diagnostics and reporting |

## Prices

Candidate fields:
- DlyPrc
- DlyOpen
- DlyClose
- DlyHigh
- DlyLow
- DlyPrevPrc

Uses:
- execution-price QA
- range and volatility features
- price-based eligibility filters
- forward return construction

CRSP defines `DlyPrc` as the last regular-session trade price, using a bid/ask average when a closing trade price is unavailable. Price flags must therefore remain available for diagnostics.

## Returns

Candidate fields:
- DlyRet
- DlyRetx
- available return flags / indexes needed for robust compounding

The distinction between total return and ex-distribution price return must be maintained. In CIZ, delisting returns are incorporated into the return framework rather than appended later using the legacy FIZ/SIZ workflow.

## Volume and liquidity

Candidate fields:
- DlyVol
- DlyPrcVol where available
- DlyBid
- DlyAsk

Derived candidates:
- ADV_20
- turnover
- relative volume
- quoted spread proxy
- Amihud illiquidity

## Size

Primary field:
- DlyCap

**Critical unit convention:** CRSP CIZ reports `DlyCap` in **thousands of dollars**.

Therefore:
- $1bn market cap = `DlyCap = 1,000,000`
- $5bn market cap = `DlyCap = 5,000,000`

All code must either retain the native `*_thousands` convention explicitly or convert once to dollars using a named field such as `market_cap_usd`. Silent unit conversion is prohibited.

Uses:
- universe eligibility
- cross-sectional controls
- size exposure diagnostics

## Corporate actions / data quality

Candidate fields and flags:
- DlyDelFlg
- DlyPrcFlg
- return-missing / return flags where available
- DlyCapFlg
- distribution / adjustment information

No missing observation will be automatically treated as zero return.

## Initial feature families

### Returns / reversal
- r_1
- r_2
- r_5
- r_10

### Momentum
- r_20
- r_60
- r_120
- r_252
- optional skip-period momentum

### Volatility
- vol_5
- vol_20
- vol_60
- downside volatility

### Liquidity
- ADV_20
- turnover
- relative volume
- spread proxy
- Amihud illiquidity

### Market-relative / risk
- market-adjusted return
- rolling beta
- residual volatility
- industry-relative return, subject to a point-in-time industry mapping

Every final feature must receive:
1. economic rationale,
2. exact formula,
3. information timestamp,
4. minimum-history rule,
5. missing-data treatment,
6. winsorisation / normalisation rule,
7. source-unit convention.
