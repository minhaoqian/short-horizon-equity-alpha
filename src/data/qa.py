"""Data-quality utilities for Stage 1A.

These functions intentionally perform no forecasting. Their purpose is to
validate the point-in-time security panel before any alpha research begins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CRSPColumns:
    date: str = "DlyCalDt"
    permno: str = "PERMNO"
    price: str = "DlyPrc"
    open: str = "DlyOpen"
    ret: str = "DlyRet"
    volume: str = "DlyVol"
    market_cap: str = "DlyCap"


def validate_required_columns(
    df: pd.DataFrame,
    columns: CRSPColumns = CRSPColumns(),
) -> None:
    required = [
        columns.date,
        columns.permno,
        columns.price,
        columns.open,
        columns.ret,
        columns.volume,
        columns.market_cap,
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def duplicate_security_dates(
    df: pd.DataFrame,
    columns: CRSPColumns = CRSPColumns(),
) -> pd.DataFrame:
    """Return duplicate PERMNO-date rows; empty output is the desired result."""
    mask = df.duplicated([columns.permno, columns.date], keep=False)
    return df.loc[mask].sort_values([columns.permno, columns.date])


def yearly_coverage(
    df: pd.DataFrame,
    columns: CRSPColumns = CRSPColumns(),
    fields: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Compute annual observation and non-missing coverage statistics."""
    validate_required_columns(df, columns)
    work = df.copy()
    work[columns.date] = pd.to_datetime(work[columns.date])
    work["year"] = work[columns.date].dt.year

    fields = list(fields or [
        columns.price,
        columns.open,
        columns.ret,
        columns.volume,
        columns.market_cap,
    ])

    grouped = work.groupby("year", observed=True)
    out = grouped.agg(
        observations=(columns.permno, "size"),
        securities=(columns.permno, "nunique"),
    )

    for field in fields:
        out[f"{field}_coverage"] = grouped[field].apply(
            lambda s: float(s.notna().mean())
        )

    return out.reset_index()


def add_trailing_adv(
    df: pd.DataFrame,
    columns: CRSPColumns = CRSPColumns(),
    window: int = 20,
    min_periods: int = 15,
) -> pd.DataFrame:
    """Add trailing average dollar volume using only current/past observations.

    Dollar volume uses abs(price) * share volume. The rolling mean includes the
    current day because the baseline signal is assumed to be formed after the
    close. If execution timing changes, this convention must be revisited.
    """
    work = df.sort_values([columns.permno, columns.date]).copy()
    work["dollar_volume"] = (
        pd.to_numeric(work[columns.price], errors="coerce").abs()
        * pd.to_numeric(work[columns.volume], errors="coerce")
    )
    work[f"adv_{window}"] = (
        work.groupby(columns.permno, observed=True)["dollar_volume"]
        .transform(lambda s: s.rolling(window, min_periods=min_periods).mean())
    )
    return work


def candidate_liquid_universe(
    df: pd.DataFrame,
    columns: CRSPColumns = CRSPColumns(),
    price_floor: float = 5.0,
    market_cap_floor: float = 1_000_000_000.0,
    adv_floor: float = 20_000_000.0,
    adv_col: str = "adv_20",
) -> pd.Series:
    """Candidate liquidity mask.

    Units of market capitalisation must be verified against the extracted CRSP
    field before this mask is used. This function is a QA scaffold, not a final
    sample-definition decision.
    """
    if adv_col not in df.columns:
        raise ValueError(f"{adv_col} not found; call add_trailing_adv first.")

    price = pd.to_numeric(df[columns.price], errors="coerce").abs()
    market_cap = pd.to_numeric(df[columns.market_cap], errors="coerce")
    adv = pd.to_numeric(df[adv_col], errors="coerce")

    return (
        (price > price_floor)
        & (market_cap > market_cap_floor)
        & (adv > adv_floor)
    )


def open_coverage_by_liquidity_bucket(
    df: pd.DataFrame,
    columns: CRSPColumns = CRSPColumns(),
    n_buckets: int = 5,
) -> pd.DataFrame:
    """Open-price coverage by year and lag-safe ADV bucket."""
    work = add_trailing_adv(df, columns=columns)
    work[columns.date] = pd.to_datetime(work[columns.date])
    work["year"] = work[columns.date].dt.year

    def _bucket(group: pd.DataFrame) -> pd.Series:
        ranked = group["adv_20"].rank(method="first")
        valid = ranked.notna()
        result = pd.Series(np.nan, index=group.index)
        if valid.sum() >= n_buckets:
            result.loc[valid] = pd.qcut(
                ranked.loc[valid],
                q=n_buckets,
                labels=False,
                duplicates="drop",
            ) + 1
        return result

    work["adv_bucket"] = (
        work.groupby(columns.date, group_keys=False, observed=True)
        .apply(_bucket, include_groups=False)
    )

    out = (
        work.dropna(subset=["adv_bucket"])
        .groupby(["year", "adv_bucket"], observed=True)
        .agg(
            observations=(columns.permno, "size"),
            securities=(columns.permno, "nunique"),
            open_coverage=(columns.open, lambda s: float(s.notna().mean())),
        )
        .reset_index()
    )
    return out
