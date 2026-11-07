"""Cost of the same grocery basket in every state.

Each item is priced at the median of all shop-month prices in the state over a 3-month window
(e.g. Aug to Oct 2026), which gives enough shops even in Labuan and Putrajaya.
The basket cost is the sum of those medians, one unit of each item.

Run from the project root after `clean`:
    python -m src.pricepulse.basket
"""
from __future__ import annotations

import pandas as pd

from . import config


def basket_rows(monthly: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """Keep only basket items and give each a label. Rice packs of any brand share one label."""
    rice_codes = items[(items["item_category"] == config.BASKET_RICE_CATEGORY)
                       & (items["unit"].str.strip() == config.BASKET_RICE_UNIT)
                       & items["item"].str.contains("IMPORT|SST|5%", regex=True)]["item_code"]
    labels = pd.Series(config.BASKET_ITEMS)
    labels = pd.concat([labels, pd.Series(config.BASKET_RICE_LABEL, index=rice_codes)])
    out = monthly[monthly["item_code"].isin(labels.index)].copy()
    out["label"] = out["item_code"].map(labels)
    return out


def window_prices(rows: pd.DataFrame, end: pd.Timestamp, window: int = config.BASKET_WINDOW) -> pd.DataFrame:
    """Median price and shop count per state and basket item over the `window` months ending at `end`."""
    start = end - pd.DateOffset(months=window - 1)
    w = rows[(rows["month"] >= start) & (rows["month"] <= end)]
    return (w.groupby(["state", "label"])
             .agg(price=("price", "median"), shops=("premise_code", "nunique"))
             .reset_index().assign(window_end=end))


def basket_cost(prices: pd.DataFrame, labels: list[str], min_shops: int = config.BASKET_MIN_SHOPS) -> pd.DataFrame:
    """Sum of item prices per state and window. `complete` is False if any item is missing or thin."""
    full = (prices.set_index(["window_end", "state", "label"])
                  .unstack("label").stack("label", future_stack=True).reset_index())
    full = full[full["label"].isin(labels)]
    ok = full["price"].notna() & (full["shops"].fillna(0) >= min_shops)
    full["ok"] = ok
    return (full.groupby(["window_end", "state"])
                .agg(cost=("price", "sum"), items=("ok", "sum"))
                .assign(complete=lambda d: d["items"] == len(labels))
                .reset_index())


def build(monthly: pd.DataFrame, premises: pd.DataFrame, items: pd.DataFrame, last_month: pd.Timestamp) -> dict:
    df = monthly[(monthly["scope"] == "grocery") & ~monthly["outlier"]]
    df = df.merge(premises[["premise_code", "state"]], on="premise_code").dropna(subset=["state"])
    rows = basket_rows(df, items)
    rows = rows[rows["month"] <= last_month]
    # Add a national pseudo-state so Malaysia gets a basket too.
    rows = pd.concat([rows, rows.assign(state="Malaysia")])
    labels = sorted(rows["label"].unique())
    ends = pd.date_range(rows["month"].min() + pd.DateOffset(months=config.BASKET_WINDOW - 1), last_month, freq="MS")
    prices = pd.concat([window_prices(rows, e) for e in ends], ignore_index=True)
    cost = basket_cost(prices, labels)
    return {"prices": prices, "cost": cost}


def main() -> None:
    import duckdb
    from .index import last_complete_month

    monthly = pd.read_parquet(config.PROCESSED / "monthly_prices.parquet")
    premises = pd.read_parquet(config.RAW / "lookup_premise.parquet")
    items = pd.read_parquet(config.RAW / "lookup_item.parquet")
    latest = duckdb.sql(f"SELECT max(CAST(date AS DATE)) FROM '{config.RAW}/pricecatcher_*.parquet'").fetchall()[0][0]
    last_month = last_complete_month(pd.Timestamp(latest))
    out = build(monthly, premises, items, last_month)
    for name, t in out.items():
        t.to_parquet(config.PROCESSED / f"basket_{name}.parquet", index=False)
    c = out["cost"]
    now = c[c["window_end"] == last_month].set_index("state")
    year_ago = c[c["window_end"] == last_month - pd.DateOffset(months=12)].set_index("state")
    first = c[c["window_end"] == c["window_end"].min()].set_index("state")
    table = pd.DataFrame({"now": now["cost"], "year_ago": year_ago["cost"], "first": first["cost"],
                          "complete": now["complete"] & year_ago["complete"] & first["complete"]})
    table["vs_year_ago_pct"] = 100 * (table["now"] / table["year_ago"] - 1)
    print(f"Basket of {c['items'].max()} items, RM, 3 months to {last_month:%b %Y} vs a year earlier vs Jan-Mar 2022")
    print(table.sort_values("now").round(2).to_string())


if __name__ == "__main__":
    main()
