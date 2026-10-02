# Data Dictionary — v0.1

The first data layer is CRSP CIZ daily US stock data. Exact WRDS table names and field availability will be verified against the user's current subscription before extraction code is finalised.

## Identification

| Field | Purpose |
|---|---|
| PERMNO | primary historical security identifier |
| PERMCO | company identifier |
| date / DlyCalDt | trading date |
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

## Returns

Candidate fields:
- DlyRet
- DlyRetx
- any available return-index / adjusted-return fields required for robust compounding

The distinction between total return and ex-distribution price return must be maintained.

## Volume and liquidity

Candidate fields:
- DlyVol
- DlyPrcVol / dollar-volume equivalent
- DlyBid
- DlyAsk

Derived candidates:
- ADV_20
- turnover
- relative volume
- quoted spread proxy
- Amihud illiquidity

## Size

Candidate field:
- DlyCap

Uses:
- universe eligibility
- cross-sectional controls
- size exposure diagnostics

## Corporate actions / data quality

Candidate fields and flags:
- delisting indicator(s)
- price flags
- return-missing flags
- market-cap flags
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
6. winsorisation / normalisation rule.
