# Stage 1A Data QA — First Pass

## Input summary

- Raw observations: **64,974,442**
- Unique PERMNOs: **30,363**
- Date range: **1993-01-04 to 2025-12-31**
- Exported variables: 29

## Schema

The WRDS extract contains the planned core fields, including:
- PERMNO / PERMCO
- OHLC / CRSP price
- total / price / income returns
- volume / price-volume
- bid / ask
- daily capitalisation
- delisting flag
- price flags
- dividend amounts
- price-adjustment factor

No Stage 1A blocker is present in the observed schema.

## Raw field coverage

Raw all-security coverage is lower than liquid-universe coverage, especially for opening prices.

Examples:

| Year | Price | Open | Return | Volume | Cap |
|---|---:|---:|---:|---:|---:|
| 1993 | 98.30% | 87.48% | 98.23% | 98.28% | 98.28% |
| 1998 | 98.73% | 92.13% | 98.69% | 98.68% | 98.68% |
| 2003 | 96.93% | 92.05% | 96.91% | 96.89% | 96.89% |
| 2008 | 98.49% | 95.39% | 98.47% | 98.46% | 98.46% |
| 2013 | 98.63% | 96.09% | 98.60% | 98.61% | 98.61% |
| 2018 | 99.35% | 95.96% | 99.31% | 99.32% | 99.32% |
| 2025 | 99.87% | 98.51% | 99.81% | 99.84% | 99.84% |

This pattern is economically plausible: missing opening prices are concentrated in less liquid securities.

## Candidate liquid-sample opening-price coverage

The first-pass candidate liquid screen shows extremely high opening-price coverage:

- minimum annual coverage: **99.27%**
- mean annual coverage: **99.83%**
- from 2007 onward, annual coverage is effectively 100% in most years

This is strong evidence that next-open execution is feasible for a liquid-equity universe.

**However:** the first-pass diagnostic used same-day dollar volume rather than the pre-specified trailing 20-day ADV. Therefore next-open execution is not yet formally locked. A second-pass coverage test using lag-safe ADV20 is required.

## Size / liquidity distributions

The full raw CRSP panel contains many very small and illiquid securities, confirming that an investability filter is necessary.

Examples of median market capitalisation, in CRSP native thousand-USD units:

- 1993: 72,717.5 = about $72.7m
- 2003: 173,546.8 = about $173.5m
- 2013: 372,967.1 = about $373.0m
- 2025: 264,721.9 = about $264.7m

The candidate $1bn market-cap floor therefore removes a substantial part of the raw panel rather than being a trivial screen.

## Duplicate PERMNO-date issue

The QA found:

- **14,016** duplicated PERMNO-date groups
- maximum multiplicity: **12**
- excess duplicated rows: **14,881**
- excess-row share of the full extract: approximately **0.0229%**

The rate is small, but any duplicate security-date key is unacceptable for the modelling panel.

**Status:** unresolved.

Before deduplication, inspect the full source rows for a sample of duplicate keys to identify whether the cause is:
- multiple source records in the CIZ daily table,
- identifier / header joins performed by WRDS,
- corporate-action / metadata effects,
- or another extraction issue.

No arbitrary `drop_duplicates` rule will be used.

## Gate status

- Core schema: PASS
- Date coverage: PASS
- Raw missingness: PASS for continued research
- Liquid-sample open coverage: STRONG PRELIMINARY PASS
- Next-open execution: PENDING ADV20 confirmation
- Unique PERMNO-date panel: FAIL / INVESTIGATE

## Required next actions

1. inspect representative duplicate PERMNO-date source rows with all extracted fields;
2. compute true trailing 20-day ADV using point-in-time daily data;
3. recompute open coverage under candidate price / market-cap / ADV20 filters;
4. only then lock the execution convention;
5. proceed to historical security-metadata extraction and common-equity universe construction.
