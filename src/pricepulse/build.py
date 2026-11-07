"""Write the small tables the dashboard reads into app/data/ (a few MB, committed to git).

Run from the project root after fetch, clean, index, drivers, basket and validate:
    python -m src.pricepulse.build
The app never touches data/raw or data/processed, so it runs on Streamlit Community Cloud as is.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from . import config
from .index import last_complete_month

NAMES_FILE = Path(__file__).with_name("item_names.psv")
RICE_CODE = 0          # pseudo item: any 10 kg imported white rice (see basket.py)
CALC_MIN_STATES = 14   # an item joins the calculator if at least this many states have >= BASKET_MIN_SHOPS shops


def english_names(items: pd.DataFrame) -> pd.Series:
    """item_code -> English label with unit, falling back to the Malay name in title case."""
    names = pd.read_csv(NAMES_FILE, sep="|").set_index("item_code")["name_en"]
    base = items.set_index("item_code")
    label = names.reindex(base.index).fillna(base["item"].str.title())
    unit = (base["unit"].fillna("").str.strip()
            .str.replace(r"^(\d+)kg$", r"\1 kg", regex=True)
            .str.replace(r"(?i)\s*biji$", " pcs", regex=True)
            .str.replace(r"(?i)\s*beg$", " bags", regex=True)
            .str.replace(r"(\d)\s*[Xx]\s*", r"\1 x ", regex=True)
            .str.replace(r"(\d)(g|ml|G)$", r"\1 \2", regex=True)
            .str.replace("+- ", "about ", regex=False).str.replace("+-", "about ", regex=False))
    return (label + " (" + unit + ")").rename("name")


def window(df: pd.DataFrame, end: pd.Timestamp, months: int = config.BASKET_WINDOW) -> pd.DataFrame:
    start = end - pd.DateOffset(months=months - 1)
    return df[(df["month"] >= start) & (df["month"] <= end)]


def calculator_prices(df: pd.DataFrame, items: pd.DataFrame, names: pd.Series, last: pd.Timestamp) -> pd.DataFrame:
    """Median price and shop count per state and item, now and a year earlier, for calculator items."""
    rice_codes = items[(items["item_category"] == config.BASKET_RICE_CATEGORY)
                       & (items["unit"].str.strip() == config.BASKET_RICE_UNIT)
                       & items["item"].str.contains("IMPORT|SST|5%", regex=True)]["item_code"]
    rice = df[df["item_code"].isin(rice_codes)].assign(item_code=RICE_CODE)
    df = pd.concat([df, rice, ], ignore_index=True)
    df = pd.concat([df, df.assign(state="Malaysia")], ignore_index=True)

    def stats(end):
        return (window(df, end).groupby(["state", "item_code"])
                .agg(price=("price", "median"), shops=("premise_code", "nunique")))

    now, ago = stats(last), stats(last - pd.DateOffset(months=12))
    out = now.join(ago, rsuffix="_year_ago", how="left").reset_index()
    ok = out[(out["state"] != "Malaysia") & (out["shops"] >= config.BASKET_MIN_SHOPS)]
    n_states = ok.groupby("item_code")["state"].nunique()
    keep = set(n_states[n_states >= CALC_MIN_STATES].index) | {RICE_CODE} | set(config.BASKET_ITEMS)
    out = out[out["item_code"].isin(keep)].copy()
    info = items.set_index("item_code")
    out["category"] = out["item_code"].map(info["item_category"].map(config.GROCERY_CATEGORIES))
    out["name"] = out["item_code"].map(names)
    out["name_my"] = out["item_code"].map(info["item"])
    rice_mask = out["item_code"] == RICE_CODE
    out.loc[rice_mask, ["category", "name", "name_my"]] = ["Rice", config.BASKET_RICE_LABEL, "BERAS IMPORT 10 KG (PELBAGAI JENAMA)"]
    out["enough"] = out["shops"] >= config.BASKET_MIN_SHOPS
    out["in_default_basket"] = out["item_code"].isin(set(config.BASKET_ITEMS) | {RICE_CODE})
    return out


def item_trends(df: pd.DataFrame, codes: set[int]) -> pd.DataFrame:
    """Monthly median shop price per item, nationally and by state, for the Price Trends page."""
    d = df[df["item_code"].isin(codes)]
    d = pd.concat([d, d.assign(state="Malaysia")], ignore_index=True)
    t = d.groupby(["item_code", "state", "month"]).agg(price=("price", "median"), shops=("premise_code", "nunique"))
    t = t.reset_index()
    t["price"] = t["price"].astype("float32")
    t["shops"] = t["shops"].astype("int16")
    return t


def simplify_geojson(src: Path, dst: Path, digits: int = 3) -> None:
    g = json.loads(src.read_text())

    def rnd(c):
        return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], digits), round(c[1], digits)]

    for f in g["features"]:
        f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
        f["properties"] = {"state": f["properties"]["state"]}
    dst.write_text(json.dumps(g, separators=(",", ":")))


def main() -> None:
    P, A = config.PROCESSED, config.APP_DATA
    A.mkdir(parents=True, exist_ok=True)
    items = pd.read_parquet(config.RAW / "lookup_item.parquet")
    premises = pd.read_parquet(config.RAW / "lookup_premise.parquet")
    names = english_names(items)
    latest = duckdb.sql(f"SELECT max(CAST(date AS DATE)) FROM '{config.RAW}/pricecatcher_*.parquet'").fetchall()[0][0]
    last = last_complete_month(pd.Timestamp(latest))

    monthly = pd.read_parquet(P / "monthly_prices.parquet")
    df = monthly[(monthly["scope"] == "grocery") & ~monthly["outlier"] & (monthly["month"] <= last)]
    df = df.merge(premises[["premise_code", "state"]], on="premise_code").dropna(subset=["state"])

    calc = calculator_prices(df, items, names, last)
    calc.to_parquet(A / "calculator_prices.parquet", index=False)
    item_trends(df, set(calc["item_code"]) - {RICE_CODE}).to_parquet(A / "item_trends.parquet", index=False)

    keep = ["state", "month", "index", "yoy_pct", "yoy3m_pct"]
    pd.read_parquet(P / "index_grocery_state.parquet")[keep].to_parquet(A / "state_index.parquet", index=False)
    cat = pd.read_parquet(P / "index_grocery_category.parquet")
    cat[["state", "category", "month", "index", "yoy_pct", "yoy3m_pct"]].to_parquet(A / "category_index.parquet", index=False)
    pd.read_parquet(P / "drivers_contributions.parquet").to_parquet(A / "contributions.parquet", index=False)
    movers = pd.read_parquet(P / "drivers_movers.parquet")
    movers["name"] = movers["item_code"].map(names)
    movers.drop(columns=["item"]).to_parquet(A / "movers.parquet", index=False)
    pd.read_parquet(P / "basket_cost.parquet").to_parquet(A / "basket_cost.parquet", index=False)
    cov = pd.read_parquet(P / "index_grocery_coverage.parquet")
    shops = df[df["month"] == last].groupby("state")["premise_code"].nunique().rename("shops")
    cov = cov[cov["month"] == last].set_index("state").join(shops).reset_index()
    cov.to_parquet(A / "coverage.parquet", index=False)
    for name in ["national", "classes", "states", "summary"]:
        pd.read_parquet(P / f"validate_{name}.parquet").to_parquet(A / f"validate_{name}.parquet", index=False)
    simplify_geojson(config.RAW / "state.geojson", A / "states.geojson")
    # M6: policy events, outlet types and districts
    for name in ["paths", "effects", "meta"]:
        pd.read_parquet(P / f"events_{name}.parquet").to_parquet(A / f"events_{name}.parquet", index=False)
    pd.read_parquet(P / "outlet_index.parquet")[["outlet", "month", "index", "yoy3m_pct", "items"]].to_parquet(
        A / "outlet_index.parquet", index=False)
    pd.read_parquet(P / "outlet_levels.parquet").to_parquet(A / "outlet_levels.parquet", index=False)
    pd.read_parquet(P / "district_ranking.parquet").to_parquet(A / "district_ranking.parquet", index=False)

    meta = {
        "latest_observation": str(latest),
        "last_complete_month": last.strftime("%Y-%m"),
        "window_label": f"{(last - pd.DateOffset(months=config.BASKET_WINDOW - 1)):%b} to {last:%b %Y}",
        "year_ago_label": f"{(last - pd.DateOffset(months=12 + config.BASKET_WINDOW - 1)):%b} to {(last - pd.DateOffset(months=12)):%b %Y}",
        "base_month": config.INDEX_BASE,
        "shops_last_month": int(df[df["month"] == last]["premise_code"].nunique()),
        "items_last_month": int(df[df["month"] == last]["item_code"].nunique()),
        "dosm_last_month": pd.read_parquet(P / "validate_states.parquet")["month"].max().strftime("%Y-%m"),
        "gaps": ["30 Sep to 9 Oct 2026: no PriceCatcher data published"],
        "category_weights": config.CATEGORY_WEIGHTS,
    }
    (A / "meta.json").write_text(json.dumps(meta, indent=2))
    size = sum(f.stat().st_size for f in A.iterdir()) / 1e6
    print(f"Wrote {len(list(A.iterdir()))} files to app/data/ ({size:.1f} MB); latest observation {latest}")


if __name__ == "__main__":
    main()
