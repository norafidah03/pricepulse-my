"""What is driving price changes: categories and items rising fastest, nationally and by state.

Run from the project root after `index`:
    python -m src.pricepulse.drivers
"""
from __future__ import annotations

import pandas as pd

from . import config
from .index import yoy_contributions

MIN_PAIRS_NATIONAL = 100  # matched shops per month for an item to be ranked nationally
MIN_PAIRS_STATE = 3       # ... and in a state (in each of the last 3 months, never imputed)


def reliable_items(state_item: pd.DataFrame, month: pd.Timestamp, min_pairs: int) -> pd.DataFrame:
    """State x item rows at `month` whose last 3 months each had at least `min_pairs` matched shops."""
    recent = state_item[(state_item["month"] > month - pd.DateOffset(months=3)) & (state_item["month"] <= month)]
    ok = (recent.assign(good=(recent["n_pairs"] >= min_pairs) & ~recent["imputed"].astype(bool))
                .groupby(["state", "item_code"])["good"].agg(["sum", "size"]))
    keep = ok[(ok["sum"] == 3) & (ok["size"] == 3)].index
    now = state_item[state_item["month"] == month].set_index(["state", "item_code"])
    return now.loc[now.index.intersection(keep)].reset_index()


def top_movers(table: pd.DataFrame, by: str, n: int, group: str | None = None) -> pd.DataFrame:
    """The n biggest rises and n biggest falls of `by`, optionally within each `group`."""
    t = table.dropna(subset=[by])
    if group is None:
        up, down = t.nlargest(n, by).assign(direction="up"), t.nsmallest(n, by).assign(direction="down")
    else:
        up = t.sort_values(by, ascending=False).groupby(group).head(n).assign(direction="up")
        down = t.sort_values(by).groupby(group).head(n).assign(direction="down")
    return pd.concat([up, down], ignore_index=True)


def build(P=config.PROCESSED, raw=config.RAW) -> dict[str, pd.DataFrame]:
    state = pd.read_parquet(P / "index_grocery_state.parquet")
    contrib = pd.read_parquet(P / "index_grocery_contrib.parquet")
    item = pd.read_parquet(P / "index_grocery_item.parquet")
    state_item = pd.read_parquet(P / "index_grocery_state_item.parquet")
    items = pd.read_parquet(raw / "lookup_item.parquet")[["item_code", "item", "unit", "item_category"]]
    items["category"] = items["item_category"].map(config.GROCERY_CATEGORIES)
    last = state["month"].max()

    contributions = yoy_contributions(state, contrib, last).assign(month=last)

    # National: use the state-level pair counts summed, to judge how widely an item is priced.
    pairs = state_item[state_item["month"] > last - pd.DateOffset(months=3)].groupby(["item_code", "month"])["n_pairs"].sum()
    wide = pairs.groupby("item_code").min()
    nat = item[(item["month"] == last) & item["item_code"].isin(wide[wide >= MIN_PAIRS_NATIONAL].index)]
    nat = nat.merge(items, on="item_code").assign(state="Malaysia")
    by_state = reliable_items(state_item, last, MIN_PAIRS_STATE).merge(items, on="item_code")

    cols = ["state", "item_code", "item", "unit", "category", "yoy3m_pct", "yoy_pct", "index"]
    movers = pd.concat([top_movers(nat[cols], "yoy3m_pct", 10),
                        top_movers(by_state[cols], "yoy3m_pct", 5, group="state")], ignore_index=True)
    return {"contributions": contributions, "movers": movers.assign(month=last)}


def main() -> None:
    out = build()
    for name, t in out.items():
        t.to_parquet(config.PROCESSED / f"drivers_{name}.parquet", index=False)
    m = out["movers"]
    nat = m[m["state"] == "Malaysia"]
    print(f"Items rising and falling fastest, Malaysia (3 months to {m['month'].iloc[0]:%b %Y} vs a year earlier, %)")
    print(nat[["direction", "item", "unit", "category", "yoy3m_pct"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
