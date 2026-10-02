# CRSP Extraction Plan — Stage 1A

## Verified source table
Primary daily panel:
- `crsp.StkDlySecurityData`

## Initial extraction window
- 1993-01-01 through 2025-12-31

## WRDS daily fields selected in the web query

Confirmed available and selected:
- permno
- dlycaldt
- permco
- dlyprc
- dlyopen
- dlyclose
- dlyhigh
- dlylow
- dlyprevprc
- dlyprcflg
- dlyprevprcflg
- dlyret
- dlyretx
- dlyreti
- dlyretdurflg
- dlyvol
- dlyprcvol
- dlybid
- dlyask
- dlycap
- dlycapflg
- dlyprevcap
- dlyprevcapflg
- dlydelflg
- dlyfacprc
- dlyorddivamt
- dlynonorddivamt

Fields originally considered but not exposed in this WRDS form, such as some cumulative adjustment or return-quality fields, are not required for Stage 1A and do not block the extraction.

## Query settings
- company selection: search entire database
- no price / size / volume / exchange filters at download time
- no sort option is available in the WRDS form; sorting will be done in Python
- preferred output: CSV or compressed CSV/gzip

## Important unit convention
`dlycap` is reported in **thousands of dollars**.

Therefore:
- $1bn = 1,000,000 in native `dlycap`
- $5bn = 5,000,000 in native `dlycap`

## Data handling
Licensed CRSP extracts remain local under:
- `data/raw/`

Suggested filename:
- `data/raw/crsp_daily_1993_2025.csv.gz`

## First QA outputs
After extraction:

```bash
python scripts/01_crsp_data_qa.py data/raw/crsp_daily_1993_2025.csv.gz
```

Initial decision outputs:
1. duplicate PERMNO-date count
2. yearly field coverage
3. opening-price coverage by ADV bucket
4. later: coverage by market-cap and exchange bucket
5. delisting incidence
6. size and liquidity distributions

No model is trained before these checks are reviewed.
