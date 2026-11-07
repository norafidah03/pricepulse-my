# %% [markdown]
# # 02 · Food price index by state (Q1)
# Before running, from the project root: `fetch`, `clean`, then `python -m src.pricepulse.index`.
#
# The index compares each shop's price for an item with the same shop's price a month earlier,
# so shops joining or leaving PriceCatcher do not move it. See src/pricepulse/index.py.
# These are **observed price changes** in PriceCatcher, not official inflation (that is DOSM's CPI, notebook 04).

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
from src.pricepulse import config
from src.pricepulse.index import yoy_contributions

REPORTS = ROOT / "reports"
P = config.PROCESSED
state = pd.read_parquet(P / "index_grocery_state.parquet")
contrib = pd.read_parquet(P / "index_grocery_contrib.parquet")
coverage = pd.read_parquet(P / "index_grocery_coverage.parquet")
category = pd.read_parquet(P / "index_grocery_category.parquet")
LAST = state["month"].max()
print(f"Index runs Jan 2022 = 100 to {LAST:%b %Y}")

# %% [markdown]
# ## 1. National trend
# Most of the rise happened in 2022. Since then the year-on-year change has stayed between about -0.3% and +3%.

# %%
nat = state[state["state"] == "Malaysia"]
fig = px.line(nat, x="month", y="index", title="Observed grocery prices, Malaysia (Jan 2022 = 100)")
fig.write_html(REPORTS / "02_national_index.html")
nat.set_index("month")[["index", "yoy_pct", "yoy3m_pct"]].iloc[::6].round(1)

# %% [markdown]
# ## 2. Which states are rising fastest now?
# Headline measure: the last 3 months vs the same 3 months a year earlier (`yoy3m_pct`).
# Single-month year-on-year rankings jump around a lot (see section 4), so we avoid them.

# %%
now = state[state["month"] == LAST].sort_values("yoy3m_pct")
fig = px.bar(now, x="yoy3m_pct", y="state", orientation="h",
             title=f"Change in observed grocery prices, Aug to Oct 2026 vs a year earlier (%)")
fig.write_html(REPORTS / "02_states_now.html")
now[["state", "index", "yoy_pct", "yoy3m_pct"]].round(1)

# %% [markdown]
# ## 3. What drives each state's change?
# Contribution of each category, in percentage points, to the year-on-year change in Oct 2026.
# The contributions add up to the state's total. Categories use DOSM CPI weights (config.CATEGORY_WEIGHTS).

# %%
c = yoy_contributions(state, contrib, LAST)
table = c.pivot(index="category", columns="state", values="pp").round(2)
fig = px.imshow(table, color_continuous_scale="RdBu_r", color_continuous_midpoint=0, aspect="auto",
                title="Contribution to year-on-year change, Oct 2026 (percentage points)")
fig.write_html(REPORTS / "02_drivers_heatmap.html")
table[["Malaysia", "Kedah", "Kelantan", "Sabah", "W.P. Labuan"]]

# %% [markdown]
# ## 4. How stable are the rankings?
# Rank of each state by single-month year-on-year change over the last 12 months (1 = fastest).

# %%
recent = state[(state["state"] != "Malaysia") & (state["month"] > LAST - pd.DateOffset(months=12))]
ranks = recent.pivot(index="state", columns="month", values="yoy_pct").rank(ascending=False)
ranks.columns = ranks.columns.strftime("%b %y")
ranks

# %%
spread = state[state["state"] != "Malaysia"].groupby("month")["yoy3m_pct"].agg(["min", "max"]).dropna()
print("Gap between the fastest and slowest state (yoy3m, percentage points):")
print((spread["max"] - spread["min"]).describe().round(2))

# %% [markdown]
# ## 5. How much does each state lean on the national figure?
# When a state has fewer than 2 matched shops for an item, it borrows the national item change.
# Small states lean on it more, so their index is closer to the national one by construction.

# %%
coverage[coverage["month"] == LAST].sort_values("imputed_share")[["state", "items", "imputed_share"]].round(2)

# %% [markdown]
# ## 6. Category indices, Malaysia

# %%
nat_cat = category[category["state"] == "Malaysia"]
fig = px.line(nat_cat, x="month", y="index", color="category", title="Observed grocery prices by category, Malaysia (Jan 2022 = 100)")
fig.write_html(REPORTS / "02_categories.html")
nat_cat[nat_cat["month"] == LAST].sort_values("index", ascending=False)[["category", "index", "yoy_pct", "yoy3m_pct"]].round(1)
