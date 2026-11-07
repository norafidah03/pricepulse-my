"""Q5: did policy events show up in observed prices?

For each event we compare a treated group with a control group on the same matched-sample
price relatives the main index uses, and ask how unusual the gap is.

    gap(k) = treated log change - control log change, from the month before the event (t-1) to t+k
    placebo: the same gap for every other start month at least 6 months away from the event
    p-value: share of placebo gaps at least as large in absolute size (empirical, two-sided)

Events
    Chicken subsidy and price ceiling ended, 1 Nov 2023 (fresh chicken vs all other groceries)
    Diesel subsidy targeted, 10 Jun 2024, Peninsula only (Peninsula vs Sabah, Sarawak, Labuan)
    Sales tax extended to imported fruit, 1 Jul 2025 (grapes, taxed, vs other fruit; apples,
        oranges and dates were exempted before it started)
    Egg subsidy halved 1 May 2025 and ended 1 Aug 2025 (chicken eggs vs all other groceries)

Run from the project root after `index`:
    python -m src.pricepulse.events
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from . import config
from .index import aggregate_links, category_links, item_links, last_complete_month, prepare, price_relatives, weights_for

WINDOW = 6       # months shown either side of the event
HORIZONS = [0, 2, 5]   # t+k horizons reported (event month, 3 months, 6 months)
PLACEBO_GAP = 6  # placebo windows must start at least this many months from the event
EAST = ["Sabah", "Sarawak", "W.P. Labuan"]

EVENTS = [
    {"id": "chicken", "date": "2023-11-01", "title": "Chicken subsidy and price ceiling ended",
     "when": "1 Nov 2023", "kind": "items",
     "treated": [1, 2, 3], "treated_label": "Fresh and live chicken (formerly price-controlled)",
     "control": "other", "control_label": "All other groceries",
     "source": "https://www.malaymail.com/news/malaysia/2023/10/31/chicken-prices-can-be-lower-than-rm940-per-kg-after-november-1-says-armizan/99473"},
    {"id": "diesel", "date": "2024-06-01", "title": "Diesel subsidy targeted in the Peninsula",
     "when": "10 Jun 2024", "kind": "regions",
     "treated_label": "Groceries in the Peninsula (diesel RM2.15 to RM3.35)",
     "control_label": "Groceries in Sabah, Sarawak and Labuan (diesel unchanged)",
     "source": "https://mof.gov.my/portal/en/news/press-release/government-implements-targeted-diesel-subsidy-for-peninsular-malaysia-effective-10-june-2024"},
    {"id": "egg", "date": "2025-08-01", "title": "Egg subsidy ended",
     "when": "halved 1 May 2025, ended 1 Aug 2025", "kind": "items",
     "treated": [1109, 1110, 1111], "treated_label": "Chicken eggs, grades A to C (trays of 30)",
     "control": "other", "control_label": "All other groceries", "also": "2025-05-01",
     "source": "https://www.thestar.com.my/news/nation/2025/04/30/egg-subsidy-rate-reduced-from-rm010-to-rm005-per-egg-effective-may-1"},
    {"id": "sst_fruit", "date": "2025-07-01", "title": "Sales tax extended to imported fruit",
     "when": "1 Jul 2025", "kind": "items",
     "treated": [26, 27], "treated_label": "Grapes (imported, 5% sales tax)",
     "control": "BUAH-BUAHAN", "control_label": "Other fruit (local, or exempted apples and oranges)",
     "source": "https://www.freshplaza.com/asia/article/9745616/malaysia-exempts-imported-fruits-from-sales-and-service-tax"},
]


def group_links(rel: pd.DataFrame, items: list[int] | None = None) -> pd.Series:
    """Monthly log link of a group of items: geometric mean over items of each item's Jevons link."""
    r = rel if items is None else rel[rel["item_code"].isin(items)]
    return r.groupby(["month", "item_code"])["log_rel"].mean().groupby("month").mean()


def region_links(rel: pd.DataFrame) -> pd.DataFrame:
    """Weighted grocery link for Peninsula and East Malaysia, computed like the state index."""
    r = rel.assign(state=np.where(rel["state"].isin(EAST), "East Malaysia", "Peninsula"))
    links = item_links(r)
    w = weights_for(links["category"].unique().tolist())
    total, _ = aggregate_links(category_links(links, ["month", "state"]), ["month", "state"], w)
    return total.pivot(index="month", columns="state", values="log_link")


def gaps(treated: pd.Series, control: pd.Series, k: int) -> pd.Series:
    """Gap in log change from t-1 to t+k, indexed by t (event month), for every possible t."""
    d = (treated - control).sort_index()
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="MS"))
    # links at month m are changes from m-1 to m, so t-1 -> t+k sums links t..t+k
    return d.rolling(k + 1).sum().shift(-k)


def event_study(treated: pd.Series, control: pd.Series, date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Path around the event (t-1 = 100) and the gap at each horizon with its placebo p-value."""
    t0 = pd.Timestamp(date)
    months = pd.date_range(t0 - pd.DateOffset(months=WINDOW), t0 + pd.DateOffset(months=WINDOW), freq="MS")
    path = []
    for name, s in [("treated", treated), ("control", control)]:
        s = s.sort_index()
        s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="MS"))
        cs = s.fillna(0).cumsum()
        lvl = 100 * np.exp(cs - cs.get(t0 - pd.DateOffset(months=1), np.nan))
        lvl = lvl.where(s.notna()).reindex(months)
        lvl.loc[t0 - pd.DateOffset(months=1)] = 100.0
        path.append(pd.DataFrame({"month": months, "group": name, "level": lvl.values}))
    path = pd.concat(path, ignore_index=True)
    path["k"] = ((path["month"].dt.year - t0.year) * 12 + path["month"].dt.month - t0.month)

    rows = []
    for k in HORIZONS:
        g = gaps(treated, control, k).dropna()
        if t0 not in g.index:
            continue
        observed = g.loc[t0]
        far = np.abs((g.index.year - t0.year) * 12 + g.index.month - t0.month) >= PLACEBO_GAP
        placebo = g[far]
        rows.append({"k": k, "gap_pct": 100 * (np.exp(observed) - 1),
                     "treated_pct": 100 * (np.exp(treated.reindex(pd.date_range(t0, periods=k + 1, freq="MS")).sum()) - 1),
                     "control_pct": 100 * (np.exp(control.reindex(pd.date_range(t0, periods=k + 1, freq="MS")).sum()) - 1),
                     "p_value": float((np.abs(placebo) >= abs(observed)).mean()), "n_placebo": len(placebo),
                     "placebo_sd_pct": 100 * placebo.std()})
    return path, pd.DataFrame(rows)


def build(P=config.PROCESSED, raw=config.RAW) -> dict[str, pd.DataFrame]:
    monthly = pd.read_parquet(P / "monthly_prices.parquet")
    premises = pd.read_parquet(raw / "lookup_premise.parquet")
    items = pd.read_parquet(raw / "lookup_item.parquet")
    latest = duckdb.sql(f"SELECT max(CAST(date AS DATE)) FROM '{raw}/pricecatcher_*.parquet'").fetchall()[0][0]
    last_month = last_complete_month(pd.Timestamp(latest))
    df = prepare(monthly, premises, items, "grocery")
    rel = price_relatives(df)
    rel = rel[rel["month"] <= last_month]

    paths, effects = [], []
    regions = None
    for ev in EVENTS:
        if ev["kind"] == "regions":
            regions = region_links(rel) if regions is None else regions
            treated, control = regions["Peninsula"], regions["East Malaysia"]
        else:
            treated = group_links(rel, ev["treated"])
            pool = rel[~rel["item_code"].isin(ev["treated"])]
            if ev["control"] != "other":
                pool = pool[pool["item_category"] == ev["control"]]
            control = group_links(pool)
        path, eff = event_study(treated, control, ev["date"])
        paths.append(path.assign(event=ev["id"]))
        effects.append(eff.assign(event=ev["id"]))
    meta = pd.DataFrame([{k: v for k, v in ev.items() if k not in ("treated",)} for ev in EVENTS])
    return {"paths": pd.concat(paths, ignore_index=True), "effects": pd.concat(effects, ignore_index=True), "meta": meta}


def main() -> None:
    out = build()
    for name, t in out.items():
        t.to_parquet(config.PROCESSED / f"events_{name}.parquet", index=False)
    e = out["effects"].merge(out["meta"][["id", "title"]], left_on="event", right_on="id")
    print(e[["title", "k", "treated_pct", "control_pct", "gap_pct", "p_value", "n_placebo"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
