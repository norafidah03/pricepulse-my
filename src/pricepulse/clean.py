"""Turn ~100M daily price rows into one price per shop, item and month.

Run from the project root after `fetch`:
    python -m src.pricepulse.clean

Writes data/processed/monthly_prices.parquet with columns
    month, premise_code, item_code, scope, price, n_obs, outlier
where `price` is the median of that shop's daily prices for the item in that month,
`scope` is 'grocery' or 'eating_out', and `outlier` marks prices we leave out of the index.
"""
from __future__ import annotations

import duckdb
import pandas as pd

from . import config


def item_scope(items: pd.DataFrame) -> pd.DataFrame:
    """Add a `scope` column to the item lookup: 'grocery', 'eating_out' or None (not used)."""
    out = items.copy()
    out["scope"] = None
    out.loc[out["item_group"].isin(config.GROCERY_GROUPS), "scope"] = "grocery"
    out.loc[out["item_group"].isin(config.EATING_OUT_GROUPS), "scope"] = "eating_out"
    out.loc[out["item_category"].isin(config.EXCLUDED_CATEGORIES), "scope"] = None
    out.loc[out["item_code"] < 0, "scope"] = None  # the "-1 unknown" placeholder row
    return out


def flag_outliers(monthly: pd.DataFrame, ratio: float = config.OUTLIER_RATIO) -> pd.Series:
    """True where a shop's monthly price is far from that item's national median that month.

    Also flags non-positive prices. `monthly` needs month, item_code and price columns.
    """
    med = monthly.groupby(["month", "item_code"])["price"].transform("median")
    rel = monthly["price"] / med
    return (monthly["price"] <= 0) | (rel > ratio) | (rel < 1 / ratio)


def monthly_shop_prices(con: duckdb.DuckDBPyConnection, files: list[str], items: pd.DataFrame) -> pd.DataFrame:
    """Median daily price per month, shop and in-scope item, computed by DuckDB straight from parquet."""
    con.register("items", items[items["scope"].notna()][["item_code", "scope"]])
    return con.execute(
        """
        SELECT date_trunc('month', CAST(p.date AS DATE))::DATE AS month,
               p.premise_code, p.item_code, i.scope,
               median(p.price) AS price,
               count(*)        AS n_obs
        FROM read_parquet(?) p
        JOIN items i USING (item_code)
        WHERE p.price IS NOT NULL
        GROUP BY ALL
        """,
        [files],
    ).df()


def main() -> None:
    files = sorted(str(f) for f in config.RAW.glob("pricecatcher_*.parquet"))
    if not files:
        raise SystemExit("No PriceCatcher files in data/raw/. Run `python -m src.pricepulse.fetch` first.")
    items = item_scope(pd.read_parquet(config.RAW / "lookup_item.parquet"))
    con = duckdb.connect()
    print(f"Collapsing {len(files)} monthly files ...")
    monthly = monthly_shop_prices(con, files, items)
    monthly["month"] = pd.to_datetime(monthly["month"])
    monthly["outlier"] = flag_outliers(monthly)
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    out = config.PROCESSED / "monthly_prices.parquet"
    monthly.sort_values(["month", "premise_code", "item_code"]).to_parquet(out, index=False)
    print(f"  saved {out.relative_to(config.ROOT)}: {len(monthly):,} rows, "
          f"{monthly['outlier'].mean():.2%} flagged as outliers")


if __name__ == "__main__":
    main()
