import pandas as pd

from src.data.qa import CRSPColumns, duplicate_security_dates, yearly_coverage


def _panel():
    return pd.DataFrame(
        {
            "PERMNO": [1, 1, 2],
            "DlyCalDt": ["2025-01-02", "2025-01-03", "2025-01-02"],
            "DlyPrc": [10.0, 10.5, 20.0],
            "DlyOpen": [9.9, None, 19.8],
            "DlyRet": [0.01, 0.05, -0.01],
            "DlyVol": [1000, 1100, 500],
            "DlyCap": [1e6, 1.05e6, 2e6],  # CRSP native thousands of USD
        }
    )


def test_no_duplicates_in_fixture():
    out = duplicate_security_dates(_panel(), _ciz_columns())
    assert out.empty


def test_yearly_coverage_reports_open_missingness():
    out = yearly_coverage(_panel(), _ciz_columns())
    assert len(out) == 1
    assert out.loc[0, "DlyOpen_coverage"] == 2 / 3


def _ciz_columns():
    return CRSPColumns(date="DlyCalDt", permno="PERMNO", price="DlyPrc",
        open="DlyOpen", ret="DlyRet", volume="DlyVol", market_cap="DlyCap")


def test_wrds_lowercase_fixture_matches_default_schema():
    panel = _panel().rename(columns=str.lower)
    assert duplicate_security_dates(panel, CRSPColumns()).empty
    out = yearly_coverage(panel, CRSPColumns())
    assert out.loc[0, "dlyopen_coverage"] == 2 / 3
