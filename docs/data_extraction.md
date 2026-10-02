# CRSP Extraction Plan — Stage 1A

## Verified source tables

Primary daily panel:
- `crsp.StkDlySecurityData`

CRSP also provides:
- `StkDlySecurityPrimaryData` — smaller subset of commonly used daily fields
- `StkSecurityInfoHdr` — security identifiers / descriptors
- `StkSecurityInfoHist` — historical security identifiers / descriptors

The complete daily table is preferred initially because the project needs open/high/low/bid/ask and diagnostic fields beyond the smallest primary subset.

## Initial extraction window

Candidate raw extraction:
- 1993-01-01 through 2025-12-31

Reason:
- supports modern daily/open-price analysis
- provides long training history
- spans multiple market regimes
- leaves room for rolling-feature warm-up before the eventual OOS period

This date range is provisional until Stage 1A coverage statistics are inspected.

## Daily fields — first extraction

Required:
- PERMNO
- DlyCalDt
- DlyPrc
- DlyOpen
- DlyClose
- DlyHigh
- DlyLow
- DlyPrevPrc
- DlyRet
- DlyRetx
- DlyVol
- DlyPrcVol, if available
- DlyCap
- DlyBid
- DlyAsk
- DlyDelFlg
- DlyPrcFlg
- DlyCapFlg

Also retain any return / volume / open / close missingness or quality flags exposed by the query interface.

## Security metadata

Extract the corresponding historical security-information table for all available fields needed to distinguish ordinary US common equity from:
- funds / ETFs
- ADR-like or foreign-incorporated securities where relevant
- REITs if a later design decision excludes them
- special share types
- non-common equity

Candidate CIZ descriptors include:
- SecurityType
- SecuritySubType
- ShareType
- IssuerType
- USIncFlg
- exchange information
- industry classification
- PERMCO
- ticker / security name for reporting only

The final common-stock filter will not be frozen until actual field names and histories in the accessible WRDS extract are inspected.

## Important unit convention

`DlyCap` is reported in **thousands of dollars**.

Therefore:
- $1bn = 1,000,000 in native `DlyCap`
- $5bn = 5,000,000 in native `DlyCap`

## Data handling

Licensed CRSP extracts must remain local under:
- `data/raw/`

They are excluded by `.gitignore` and must never be committed to the public repository.

Preferred local format:
- Parquet for research use
- CSV only if the WRDS interface initially exports CSV

Suggested filenames:
- `data/raw/crsp_daily_1993_2025.parquet`
- `data/raw/crsp_security_info_hist.parquet`

## First QA outputs

After extraction, run:

```bash
python scripts/01_crsp_data_qa.py data/raw/crsp_daily_1993_2025.parquet
```

The first decision outputs are:
1. duplicate PERMNO-date count
2. yearly field coverage
3. opening-price coverage by ADV bucket
4. later: coverage by market-cap and exchange bucket
5. delisting incidence
6. size and liquidity distributions

No model is trained before these checks are reviewed.
