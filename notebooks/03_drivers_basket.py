# %% [markdown]
# # 03 · What drives prices, and what does a basket cost in each state? (Q2, Q3)
# Before running, from the project root: `fetch`, `clean`, `index`, then
# `python -m src.pricepulse.drivers` and `python -m src.pricepulse.basket`.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
from src.pricepulse import config

REPORTS = ROOT / "reports"
P = config.PROCESSED
contrib = pd.read_parquet(P / "drivers_contributions.parquet")
movers = pd.read_parquet(P / "drivers_movers.parquet")
prices = pd.read_parquet(P / "basket_prices.parquet")
cost = pd.read_parquet(P / "basket_cost.parquet")
LAST = movers["month"].iloc[0]
YEAR_AGO = LAST - pd.DateOffset(months=12)
FIRST = cost["window_end"].min()

# %% [markdown]
# ## Q2 · Drivers
# ### Category contributions to each state's year-on-year change (percentage points)
# Contributions add up to the state's total change. Weights are DOSM's CPI food weights.

# %%
table = contrib.pivot(index="category", columns="state", values="pp")
order = table.sum().sort_values().index
fig = px.bar(contrib, y="state", x="pp", color="category", orientation="h",
             category_orders={"state": list(order)},
             title=f"What moved grocery prices, year to {LAST:%b %Y} (percentage points)")
fig.write_html(REPORTS / "03_contributions.html", include_plotlyjs="cdn")
table.round(2)

# %% [markdown]
# ### Items rising and falling fastest, Malaysia
# Last 3 months vs the same 3 months a year earlier. Only items priced by at least 100 matched shops.

# %%
nat = movers[movers["state"] == "Malaysia"]
nat[["direction", "item", "unit", "category", "yoy3m_pct"]].round(1)

# %% [markdown]
# ### Fastest-rising items in each state
# Items with at least 3 matched shops in the state in each of the last 3 months.

# %%
up = movers[(movers["state"] != "Malaysia") & (movers["direction"] == "up")]
up.sort_values(["state", "yoy3m_pct"], ascending=[True, False]).groupby("state").head(3)[["state", "item", "yoy3m_pct"]].round(1)

# %% [markdown]
# ## Q3 · Grocery basket
# 20 staples, one of each, priced at the state's median over 3 months (config.BASKET_ITEMS).
# Rice is "any 10 kg imported white rice" because no single brand is sold everywhere.

# %%
def snapshot(end):
    return cost[cost["window_end"] == end].set_index("state")

summary = pd.DataFrame({
    "now_rm": snapshot(LAST)["cost"],
    "year_ago_rm": snapshot(YEAR_AGO)["cost"],
    "jan_mar_2022_rm": snapshot(FIRST)["cost"],
    "complete": snapshot(LAST)["complete"],
})
summary["vs_year_ago_pct"] = 100 * (summary["now_rm"] / summary["year_ago_rm"] - 1)
summary["vs_2022_pct"] = 100 * (summary["now_rm"] / summary["jan_mar_2022_rm"] - 1)
summary = summary.sort_values("now_rm")
fig = px.bar(summary.reset_index(), x="now_rm", y="state", orientation="h",
             title=f"Cost of the 20-item basket, Aug to Oct 2026 (RM)")
fig.write_html(REPORTS / "03_basket_by_state.html", include_plotlyjs="cdn")
summary.round(2)

# %%
nat_cost = cost[cost["state"] == "Malaysia"]
fig = px.line(nat_cost, x="window_end", y="cost", title="Cost of the 20-item basket, Malaysia (RM, rolling 3 months)")
fig.write_html(REPORTS / "03_basket_trend.html", include_plotlyjs="cdn")
nat_cost.set_index("window_end")["cost"].iloc[::6].round(2)

# %% [markdown]
# ### Which items differ most between states?

# %%
now = prices[prices["window_end"] == LAST].pivot(index="label", columns="state", values="price")
states_only = now.drop(columns="Malaysia")
pd.DataFrame({
    "malaysia_rm": now["Malaysia"],
    "cheapest": states_only.idxmin(axis=1), "dearest": states_only.idxmax(axis=1),
    "gap_rm": states_only.max(axis=1) - states_only.min(axis=1),
}).sort_values("gap_rm", ascending=False).round(2)
