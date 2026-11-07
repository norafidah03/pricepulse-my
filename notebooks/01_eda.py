# %% [markdown]
# # 01 · First look at PriceCatcher
# Open this file in VS Code and run cell by cell.
# Before running, from the project root:
# `python -m src.pricepulse.fetch` then `python -m src.pricepulse.clean`.
#
# What we want to know before building any index:
# 1. Which days does the data cover, and where are the gaps?
# 2. How many shops report in each state, and does that change over time?
# 3. How stable is the panel? (Do the same shops price the same items month after month?)
# 4. What did the outlier rule throw away?
# 5. A first look at a few staples.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT))

import duckdb
import pandas as pd
import plotly.express as px
from src.pricepulse import config

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

items = pd.read_parquet(config.RAW / "lookup_item.parquet")
premises = pd.read_parquet(config.RAW / "lookup_premise.parquet")
monthly = pd.read_parquet(config.PROCESSED / "monthly_prices.parquet")
monthly = monthly.merge(premises[["premise_code", "state", "premise_type"]], on="premise_code", how="left")
grocery = monthly[monthly["scope"] == "grocery"]
print(f"{len(monthly):,} shop x item x month rows; {monthly['month'].min():%b %Y} to {monthly['month'].max():%b %Y}")

# %% [markdown]
# ## 1. Daily coverage and gaps
# Count raw rows per day straight from the parquet files with DuckDB (no need to load 100M rows into pandas).

# %%
daily = duckdb.sql(
    f"SELECT CAST(date AS DATE) AS date, count(*) AS rows FROM '{config.RAW}/pricecatcher_*.parquet' GROUP BY 1 ORDER BY 1"
).df()
daily["date"] = pd.to_datetime(daily["date"])
missing = pd.date_range(daily["date"].min(), daily["date"].max()).difference(daily["date"])
print(f"{len(daily)} days with data, {len(missing)} days missing, latest observation {daily['date'].max():%d %b %Y}")

# Group consecutive missing days into gaps and show the longer ones.
gaps = pd.Series(missing).groupby((pd.Series(missing).diff().dt.days != 1).cumsum()).agg(["min", "max", "count"])
gaps[gaps["count"] >= 3].rename(columns={"min": "from", "max": "to", "count": "days"})

# %%
fig = px.bar(daily, x="date", y="rows", title="Raw price rows per day")
fig.write_html(REPORTS / "01_rows_per_day.html", include_plotlyjs="cdn")
fig

# %% [markdown]
# ## 2. Shops reporting per state
# A state with few shops gives a noisier index. Watch for jumps where KPDN added shops.

# %%
shops = grocery.groupby(["month", "state"])["premise_code"].nunique().rename("shops").reset_index()
fig = px.line(shops, x="month", y="shops", color="state", title="Shops reporting grocery prices, by state")
fig.write_html(REPORTS / "01_shops_by_state.html", include_plotlyjs="cdn")
shops.pivot(index="state", columns="month", values="shops").iloc[:, [0, 12, 24, 36, 48, -2]]

# %% [markdown]
# ## 3. Panel stability
# The index will compare each shop's price for an item with the same shop's price a month earlier.
# So what matters is how many shop x item pairs show up in both months.

# %%
keys = grocery.loc[~grocery["outlier"], ["month", "premise_code", "item_code"]]
by_month = keys.groupby("month").apply(lambda d: set(zip(d["premise_code"], d["item_code"])))
matched = pd.Series(
    [len(by_month.iloc[k] & by_month.iloc[k - 1]) / len(by_month.iloc[k]) for k in range(1, len(by_month))],
    index=by_month.index[1:], name="matched_share",
)
print(f"Median share of pairs also seen the month before: {matched.median():.0%}; lowest {matched.min():.0%} in {matched.idxmin():%b %Y}")
fig = px.line(matched.reset_index(), x="month", y="matched_share", title="Share of shop x item prices that can be matched to the previous month")
fig.write_html(REPORTS / "01_matched_share.html", include_plotlyjs="cdn")
fig

# %% [markdown]
# ## 4. Outliers
# The rule (config.OUTLIER_RATIO) flags monthly prices above 3x or below 1/3 of the item's national median.

# %%
flagged = monthly[monthly["outlier"]].merge(items[["item_code", "item", "unit"]], on="item_code")
print(f"{len(flagged):,} rows flagged ({monthly['outlier'].mean():.2%} of all)")
flagged.groupby(["item", "unit"]).size().sort_values(ascending=False).head(15)

# %% [markdown]
# ## 5. A first look at staples
# Plain national medians of shop prices, before any index. Good for a sense of levels in RM.

# %%
STAPLES = {
    1: "Chicken, standard (1 kg)",
    1109: "Eggs grade A (30)",
    1589: "White sugar, coarse (1 kg)",
    917: "Wheat flour, Cap Sauh (1 kg)",
    1601: "Cooking oil, Cap Buruh (2 kg)",
    129: "Yellow onion (1 kg)",
    114: "Tomato (1 kg)",
}
staples = (
    grocery[grocery["item_code"].isin(STAPLES) & ~grocery["outlier"]]
    .groupby(["month", "item_code"])["price"].median().reset_index()
)
staples["item"] = staples["item_code"].map(STAPLES)
fig = px.line(staples, x="month", y="price", color="item", title="National median shop price (RM)")
fig.write_html(REPORTS / "01_staples.html", include_plotlyjs="cdn")
staples.pivot(index="item", columns="month", values="price").iloc[:, [0, 12, 24, 36, 48, -2]].round(2)
