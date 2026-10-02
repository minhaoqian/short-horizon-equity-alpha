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
            "DlyCap": [1e9, 1.05e9, 2e9],
        }
    )


def test_no_duplicates_in_fixture():
    out = duplicate_security_dates(_panel(), CRSPColumns())
    assert out.empty


def test_yearly_coverage_reports_open_missingness():
    out = yearly_coverage(_panel(), CRSPColumns())
    assert len(out) == 1
    assert out.loc[0, "DlyOpen_coverage"] == 2 / 3
