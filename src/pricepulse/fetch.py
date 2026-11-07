"""Download raw data into data/raw/.

Run from the project root:
    python -m src.pricepulse.fetch            # everything
    python -m src.pricepulse.fetch prices     # just the monthly PriceCatcher files
    python -m src.pricepulse.fetch lookups cpi

Monthly files that are already on disk are skipped, except the two most recent
months, which data.gov.my keeps updating (the current month grows daily).
"""
from __future__ import annotations

import sys
from datetime import date

import pandas as pd
import requests

from . import config


def _download(url: str, filename: str) -> bool:
    config.RAW.mkdir(parents=True, exist_ok=True)
    out = config.RAW / filename
    resp = requests.get(url, timeout=180)
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    out.write_bytes(resp.content)
    print(f"  saved {out.relative_to(config.ROOT)} ({len(resp.content) / 1e6:.1f} MB)")
    return True


def month_list(first: str = config.FIRST_MONTH, last: date | None = None) -> list[str]:
    """All months from `first` to `last` (default: this month) as 'YYYY-MM'."""
    last = last or date.today()
    return [p.strftime("%Y-%m") for p in pd.period_range(first, last.strftime("%Y-%m"), freq="M")]


def fetch_prices() -> None:
    months = month_list()
    refresh = set(months[-2:])
    for ym in months:
        name = f"pricecatcher_{ym}.parquet"
        if (config.RAW / name).exists() and ym not in refresh:
            continue
        print(f"Downloading {ym}")
        if not _download(config.MONTH_URL.format(ym=ym), name):
            print(f"  {ym} not published yet")


def fetch_lookups() -> None:
    print("Downloading lookups")
    _download(config.LOOKUP_ITEM_URL, "lookup_item.parquet")
    _download(config.LOOKUP_PREMISE_URL, "lookup_premise.parquet")


def fetch_cpi() -> None:
    print("Downloading DOSM CPI by state and by expenditure class")
    _download(config.CPI_STATE_URL, "cpi_2d_state.parquet")
    _download(config.CPI_CLASS_URL, "cpi_4d.parquet")


SOURCES = {"lookups": fetch_lookups, "prices": fetch_prices, "cpi": fetch_cpi}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(SOURCES)
    for name in wanted:
        SOURCES[name]()
