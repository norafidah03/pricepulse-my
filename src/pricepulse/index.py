"""Matched-sample food price index by state.

    shop x item monthly prices
      -> price relatives: same shop, same item, this month vs last month
      -> item link per state: geometric mean of the relatives (Jevons)
         (a state with fewer than MIN_PAIRS shops for an item borrows the national link)
      -> category link: geometric mean of its item links
      -> state link: weighted geometric mean of its category links
      -> index: links chained month to month, base month = 100

Everything works on log relatives, so means of logs are geometric means of prices and
contributions add up exactly.

Run from the project root after `clean`:
    python -m src.pricepulse.index
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from . import config


def last_complete_month(latest_date: pd.Timestamp) -> pd.Timestamp:
    """The last month whose final day is on or before the latest observation."""
    latest_date = pd.Timestamp(latest_date)
    month_start = latest_date.to_period("M").to_timestamp()
    if latest_date == month_start + pd.offsets.MonthEnd(0):
        return month_start
    return month_start - pd.DateOffset(months=1)


def price_relatives(monthly: pd.DataFrame, max_relative: float = config.MAX_RELATIVE) -> pd.DataFrame:
    """Log price relative for every shop x item seen in two consecutive months.

    `monthly` needs month, premise_code, item_code, price (outliers already removed).
    Extra columns (state, category ...) are carried through from the current month.
    """
    cur = monthly.copy()
    prev = monthly[["month", "premise_code", "item_code", "price"]].copy()
    prev["month"] = prev["month"] + pd.DateOffset(months=1)
    rel = cur.merge(prev, on=["month", "premise_code", "item_code"], suffixes=("", "_prev"))
    rel["log_rel"] = np.log(rel["price"] / rel["price_prev"])
    keep = rel["log_rel"].abs() <= np.log(max_relative)
    return rel[keep].drop(columns=["price_prev"])


def item_links(rel: pd.DataFrame, min_pairs: int = config.MIN_PAIRS) -> pd.DataFrame:
    """Log link per month, state and item, with national links filled in for thin cells.

    Returns month, state, item_code, category, log_link, n_pairs, imputed.
    """
    national = (
        rel.groupby(["month", "item_code", "category"])["log_rel"].agg(log_link="mean", n_pairs="size").reset_index()
    )
    by_state = rel.groupby(["month", "state", "item_code"])["log_rel"].agg(log_link="mean", n_pairs="size").reset_index()

    # Every state x item that has a national link that month gets a row.
    states = rel[["state"]].drop_duplicates()
    grid = national.merge(states, how="cross")
    out = grid.merge(by_state, on=["month", "state", "item_code"], how="left", suffixes=("_nat", ""))
    out["n_pairs"] = out["n_pairs"].fillna(0).astype(int)
    out["imputed"] = out["n_pairs"] < min_pairs
    out["log_link"] = np.where(out["imputed"], out["log_link_nat"], out["log_link"])
    return out[["month", "state", "item_code", "category", "log_link", "n_pairs", "imputed"]]


def category_links(links: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Geometric mean of item links within each category. `keys` e.g. ['month', 'state']."""
    return links.groupby(keys + ["category"])["log_link"].mean().rename("log_link").reset_index()


def weights_for(categories: list[str], weights: dict[str, float] | None = config.CATEGORY_WEIGHTS) -> pd.Series:
    if weights is None:
        w = pd.Series(1.0, index=sorted(categories))
    else:
        w = pd.Series({c: weights.get(c, 0.0) for c in categories})
    return w / w.sum()


def aggregate_links(cat: pd.DataFrame, keys: list[str], w: pd.Series) -> pd.DataFrame:
    """Weighted mean of category log links, re-normalising weights when a category is missing that month.

    Also returns each category's share of the link (`contrib`), which sums to `log_link`.
    """
    cat = cat.copy()
    cat["w"] = cat["category"].map(w).fillna(0.0)
    cat["w"] = cat["w"] / cat.groupby(keys)["w"].transform("sum")
    cat["contrib"] = cat["w"] * cat["log_link"]
    total = cat.groupby(keys)["contrib"].sum().rename("log_link").reset_index()
    return total, cat[keys + ["category", "w", "contrib"]]


def chain(links: pd.DataFrame, keys: list[str], base: str = config.INDEX_BASE) -> pd.DataFrame:
    """Turn monthly log links into an index (base month = 100). `keys` are the series ids, e.g. ['state']."""
    links = links.sort_values("month").copy()
    base = pd.Timestamp(base)
    links = links[links["month"] > base]
    links["index"] = 100 * np.exp(links.groupby(keys)["log_link"].cumsum()) if keys else 100 * np.exp(links["log_link"].cumsum())
    first = links[keys].drop_duplicates() if keys else pd.DataFrame(index=[0])
    base_rows = first.assign(month=base, log_link=0.0, index=100.0)
    return pd.concat([base_rows, links], ignore_index=True).sort_values(keys + ["month"]).reset_index(drop=True)


def add_changes(idx: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Changes of an index, all in %.

    yoy_pct    this month vs the same month a year earlier
    yoy3m_pct  average of the last 3 months vs the same 3 months a year earlier
               (smoother than yoy_pct, and fair to seasonal items: the headline measure)
    ann3m_pct  last 3 months' change, annualised (very noisy for food; kept for reference)
    """
    idx = idx.sort_values(keys + ["month"]).copy()
    g = idx.groupby(keys)["index"] if keys else idx["index"]
    avg3 = g.transform(lambda x: x.rolling(3).mean()) if keys else g.rolling(3).mean()
    avg3_prev = avg3.groupby([idx[k] for k in keys]).shift(12) if keys else avg3.shift(12)
    idx["yoy_pct"] = 100 * (idx["index"] / g.shift(12) - 1)
    idx["yoy3m_pct"] = 100 * (avg3 / avg3_prev - 1)
    idx["ann3m_pct"] = 100 * ((idx["index"] / g.shift(3)) ** 4 - 1)
    return idx


def prepare(monthly: pd.DataFrame, premises: pd.DataFrame, items: pd.DataFrame, scope: str) -> pd.DataFrame:
    """Keep one scope, drop outliers and the partial month, attach state and category."""
    mapping = config.GROCERY_CATEGORIES if scope == "grocery" else config.EATING_OUT_CATEGORIES
    df = monthly[(monthly["scope"] == scope) & ~monthly["outlier"]]
    df = df.merge(premises[["premise_code", "state"]], on="premise_code").dropna(subset=["state"])
    df = df.merge(items[["item_code", "item_category"]], on="item_code")
    df["category"] = df["item_category"].map(mapping)
    return df.dropna(subset=["category"])


def build_index(df: pd.DataFrame, last_month: pd.Timestamp) -> dict[str, pd.DataFrame]:
    """All index tables for one scope (grocery or eating out)."""
    rel = price_relatives(df)
    rel = rel[rel["month"] <= last_month]
    links = item_links(rel)
    w = weights_for(links["category"].unique().tolist())

    cat_state = category_links(links, ["month", "state"])
    state_links, state_contrib = aggregate_links(cat_state, ["month", "state"], w)
    # National item links are the ones computed from all shops, i.e. the imputation source.
    nat_items = (
        rel.groupby(["month", "item_code", "category"])["log_rel"].mean().rename("log_link").reset_index()
    )
    cat_nat = category_links(nat_items.assign(state="Malaysia"), ["month", "state"])
    nat_links, nat_contrib = aggregate_links(cat_nat, ["month", "state"], w)

    state_idx = add_changes(chain(pd.concat([state_links, nat_links]), ["state"]), ["state"])
    cat_idx = add_changes(
        chain(pd.concat([cat_state, cat_nat])[["month", "state", "category", "log_link"]], ["state", "category"]),
        ["state", "category"],
    )
    item_idx = add_changes(chain(nat_items[["month", "item_code", "log_link"]], ["item_code"]), ["item_code"])
    contrib = pd.concat([state_contrib, nat_contrib])
    coverage = links.groupby(["month", "state"]).agg(items=("item_code", "size"), imputed_share=("imputed", "mean")).reset_index()
    return {"state": state_idx, "category": cat_idx, "item": item_idx, "contrib": contrib, "coverage": coverage,
            "weights": w.rename("weight").rename_axis("category").reset_index()}


def yoy_contributions(state_idx: pd.DataFrame, contrib: pd.DataFrame, month: pd.Timestamp) -> pd.DataFrame:
    """Each category's contribution, in percentage points, to a state's year-on-year change at `month`."""
    window = contrib[(contrib["month"] > month - pd.DateOffset(months=12)) & (contrib["month"] <= month)]
    logs = window.groupby(["state", "category"])["contrib"].sum().rename("log_contrib").reset_index()
    tot = logs.groupby("state")["log_contrib"].transform("sum")
    yoy = state_idx[state_idx["month"] == month].set_index("state")["yoy_pct"]
    logs["pp"] = logs["log_contrib"] / tot * logs["state"].map(yoy)
    return logs


def main() -> None:
    monthly = pd.read_parquet(config.PROCESSED / "monthly_prices.parquet")
    premises = pd.read_parquet(config.RAW / "lookup_premise.parquet")
    items = pd.read_parquet(config.RAW / "lookup_item.parquet")
    latest = duckdb.sql(f"SELECT max(CAST(date AS DATE)) FROM '{config.RAW}/pricecatcher_*.parquet'").fetchall()[0][0]
    last_month = last_complete_month(pd.Timestamp(latest))
    print(f"Latest observation {latest}; index runs to {last_month:%b %Y}")
    # Eating out (MAKANAN SIAP MASAK) is only published Jan to May 2022, so only groceries get an index.
    for scope in ["grocery"]:
        tables = build_index(prepare(monthly, premises, items, scope), last_month)
        for name, t in tables.items():
            out = config.PROCESSED / f"index_{scope}_{name}.parquet"
            t.to_parquet(out, index=False)
        s = tables["state"]
        latest_rows = s[s["month"] == last_month].sort_values("yoy3m_pct", ascending=False)
        print(f"\n{scope}: % change on a year earlier, {last_month:%b %Y} (yoy3m = Aug-Oct average)")
        print(latest_rows[["state", "index", "yoy_pct", "yoy3m_pct"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
