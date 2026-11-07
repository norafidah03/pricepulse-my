"""Q6: do prices rise faster at wet markets, supermarkets or sundry shops, and in which districts?

Outlet types
    Each outlet type gets its own matched-sample grocery index, built like the state index but
    like for like: an item counts in a month only if every outlet type has at least MIN_PAIRS
    matched shops for it, so differences are not a different shopping list.
    Price levels: for the same item in the same state over the last 3 months, the median price at
    each outlet type against the supermarket median (geometric mean of the ratios).

Districts
    Each district gets a grocery index. An item link with fewer than MIN_PAIRS matched shops in a
    district borrows that state's link, and a district is only ranked if it has at least
    MIN_DISTRICT_SHOPS shops and borrowed for less than MAX_BORROWED of its item links in the last year.

Run from the project root after `index`:
    python -m src.pricepulse.outlets
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from . import config
from .index import add_changes, aggregate_links, category_links, chain, last_complete_month, prepare, price_relatives, weights_for

OUTLETS = {
    "Pasar Basah": "Wet market",
    "Pasar Raya / Supermarket": "Supermarket",
    "Hypermarket": "Hypermarket",
    "Pasar Mini": "Mini market",
    "Kedai Runcit": "Sundry shop",
}
MIN_DISTRICT_SHOPS = 10
MAX_BORROWED = 0.5


def outlet_of(premises: pd.DataFrame) -> pd.DataFrame:
    p = premises[["premise_code", "premise_type", "district"]].copy()
    p["outlet"] = p["premise_type"].str.strip().map(OUTLETS)
    return p


def matched_group_index(rel: pd.DataFrame, group: str, min_pairs: int = config.MIN_PAIRS) -> pd.DataFrame:
    """Weighted grocery index per `group`, using only item-months that every group covers."""
    links = rel.groupby(["month", group, "item_code", "category"])["log_rel"].agg(log_link="mean", n_pairs="size").reset_index()
    links = links[links["n_pairs"] >= min_pairs]
    n_groups = rel[group].nunique()
    full = links.groupby(["month", "item_code"])[group].transform("nunique") == n_groups
    links = links[full].rename(columns={group: "state"})
    w = weights_for(links["category"].unique().tolist())
    total, _ = aggregate_links(category_links(links, ["month", "state"]), ["month", "state"], w)
    idx = add_changes(chain(total, ["state"]), ["state"]).rename(columns={"state": group})
    items = links.groupby("month")["item_code"].nunique().rename("items").reset_index()
    return idx.merge(items, on="month", how="left")


def price_levels(df: pd.DataFrame, last_month: pd.Timestamp, window: int = 3) -> pd.DataFrame:
    """Each outlet type's median price against the supermarket median, same item and state, last `window` months."""
    recent = df[(df["month"] > last_month - pd.DateOffset(months=window)) & (df["month"] <= last_month)].dropna(subset=["outlet"])
    med = recent.groupby(["state", "item_code", "category", "outlet"]).agg(price=("price", "median"), shops=("premise_code", "nunique")).reset_index()
    med = med[med["shops"] >= config.MIN_PAIRS]
    wide = med.pivot_table(index=["state", "item_code", "category"], columns="outlet", values="price")
    rows = []
    for outlet in wide.columns:
        if outlet == "Supermarket":
            continue
        pair = wide[[outlet, "Supermarket"]].dropna()
        lr = np.log(pair[outlet] / pair["Supermarket"])
        by_cat = lr.groupby(level="category").agg(["mean", "size"])
        rows.append({"outlet": outlet, "category": "All groceries", "gap_pct": 100 * (np.exp(lr.mean()) - 1),
                     "cheaper_share": float((lr < 0).mean()), "pairs": len(lr)})
        for cat, r in by_cat.iterrows():
            rows.append({"outlet": outlet, "category": cat, "gap_pct": 100 * (np.exp(r["mean"]) - 1),
                         "cheaper_share": float((lr.xs(cat, level="category") < 0).mean()), "pairs": int(r["size"])})
    return pd.DataFrame(rows)


def district_index(rel: pd.DataFrame, min_pairs: int = config.MIN_PAIRS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Grocery index per district; thin item links borrow the state's link."""
    state_links = rel.groupby(["month", "state", "item_code", "category"])["log_rel"].mean().rename("log_link_state").reset_index()
    by_d = rel.groupby(["month", "state", "district", "item_code"])["log_rel"].agg(log_link="mean", n_pairs="size").reset_index()
    districts = rel[["state", "district"]].drop_duplicates()
    grid = state_links.merge(districts, on="state")
    links = grid.merge(by_d, on=["month", "state", "district", "item_code"], how="left")
    links["n_pairs"] = links["n_pairs"].fillna(0).astype(int)
    links["borrowed"] = links["n_pairs"] < min_pairs
    links["log_link"] = np.where(links["borrowed"], links["log_link_state"], links["log_link"])
    links["key"] = links["state"] + "|" + links["district"]
    w = weights_for(links["category"].unique().tolist())
    cat = links.groupby(["month", "key", "category"])["log_link"].mean().reset_index().rename(columns={"key": "state"})
    total, _ = aggregate_links(cat, ["month", "state"], w)
    idx = add_changes(chain(total, ["state"]), ["state"])
    idx[["state", "district"]] = idx["state"].str.split("|", n=1, expand=True)
    borrowed = links.groupby(["month", "state", "district"])["borrowed"].mean().rename("borrowed_share").reset_index()
    return idx, borrowed


def district_ranking(idx: pd.DataFrame, borrowed: pd.DataFrame, shops: pd.DataFrame, last_month: pd.Timestamp) -> pd.DataFrame:
    year = borrowed[borrowed["month"] > last_month - pd.DateOffset(months=12)]
    b = year.groupby(["state", "district"])["borrowed_share"].mean().reset_index()
    now = idx[idx["month"] == last_month][["state", "district", "index", "yoy3m_pct"]]
    out = now.merge(b, on=["state", "district"]).merge(shops, on=["state", "district"], how="left")
    out["shops"] = out["shops"].fillna(0).astype(int)
    out["ranked"] = (out["shops"] >= MIN_DISTRICT_SHOPS) & (out["borrowed_share"] < MAX_BORROWED)
    return out.sort_values("yoy3m_pct", ascending=False).reset_index(drop=True)


def build(P=config.PROCESSED, raw=config.RAW) -> dict[str, pd.DataFrame]:
    monthly = pd.read_parquet(P / "monthly_prices.parquet")
    premises = pd.read_parquet(raw / "lookup_premise.parquet")
    items = pd.read_parquet(raw / "lookup_item.parquet")
    latest = duckdb.sql(f"SELECT max(CAST(date AS DATE)) FROM '{raw}/pricecatcher_*.parquet'").fetchall()[0][0]
    last_month = last_complete_month(pd.Timestamp(latest))
    df = prepare(monthly, premises, items, "grocery").merge(outlet_of(premises), on="premise_code", how="left")
    df = df[df["month"] <= last_month]
    rel = price_relatives(df)

    outlet_idx = matched_group_index(rel.dropna(subset=["outlet"]), "outlet")
    levels = price_levels(df, last_month)

    drel = rel.dropna(subset=["district"])
    d_idx, borrowed = district_index(drel)
    recent = df[df["month"] > last_month - pd.DateOffset(months=3)]
    shops = recent.groupby(["state", "district"])["premise_code"].nunique().rename("shops").reset_index()
    ranking = district_ranking(d_idx, borrowed, shops, last_month)
    return {"outlet_index": outlet_idx, "outlet_levels": levels, "district_index": d_idx, "district_ranking": ranking}


def main() -> None:
    out = build()
    for name, t in out.items():
        t.to_parquet(config.PROCESSED / f"{name}.parquet", index=False)
    o = out["outlet_index"]
    last = o["month"].max()
    print(o[o["month"] == last][["outlet", "index", "yoy3m_pct", "items"]].round(2).to_string(index=False))
    lv = out["outlet_levels"]
    print(lv[lv["category"] == "All groceries"].round(3).to_string(index=False))
    r = out["district_ranking"]
    print(f"{r['ranked'].sum()} of {len(r)} districts ranked")
    print(r[r["ranked"]].head(8).round(2).to_string(index=False))
    print(r[r["ranked"]].tail(8).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
