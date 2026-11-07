# %% [markdown]
# # 05 · Policy events, types of shop and districts (Q5, Q6)
# Before running, from the project root: `fetch`, `clean`, `index`, then
# `python -m src.pricepulse.events` and `python -m src.pricepulse.outlets`.
#
# **Q5.** Did four policy changes show up in observed prices? Each is compared with a group of prices it
# should not have touched, and the gap is set against the same gap in every other 3-month spell (a placebo test).
#
# **Q6.** Do prices rise faster at wet markets, supermarkets or sundry shops, and in which districts?

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
paths = pd.read_parquet(P / "events_paths.parquet")
effects = pd.read_parquet(P / "events_effects.parquet")
meta = pd.read_parquet(P / "events_meta.parquet")
outlet_index = pd.read_parquet(P / "outlet_index.parquet")
levels = pd.read_parquet(P / "outlet_levels.parquet")
ranking = pd.read_parquet(P / "district_ranking.parquet")

# %% [markdown]
# ## 1. Policy events
# Gap = treated change minus control change, from the month before the event to k months after.
# p_value = share of other 3-month spells (at least 6 months from the event) with a gap at least as large.

# %%
eff = effects.merge(meta[["id", "title", "when"]], left_on="event", right_on="id")
eff[["title", "when", "k", "treated_pct", "control_pct", "gap_pct", "p_value", "n_placebo"]].round(3)

# %%
p = paths.merge(meta[["id", "title"]], left_on="event", right_on="id")
fig = px.line(p, x="k", y="level", color="group", facet_col="title", facet_col_wrap=2,
              title="Prices around each policy change (month before = 100; k = months from the change)")
fig.write_html(REPORTS / "05_events.html", include_plotlyjs="cdn")

# %% [markdown]
# ## 2. Types of shop
# Index built only from item-months that every type of shop covers (like for like).

# %%
last = outlet_index["month"].max()
outlet_index[outlet_index["month"] == last][["outlet", "index", "yoy3m_pct", "items"]].round(2)

# %%
fig = px.line(outlet_index, x="month", y="index", color="outlet", title="Grocery price index by type of shop (Jan 2022 = 100)")
fig.write_html(REPORTS / "05_outlet_index.html", include_plotlyjs="cdn")
levels.pivot(index="category", columns="outlet", values="gap_pct").round(1)

# %% [markdown]
# ## 3. Districts
# Ranked only with at least 10 shops and under half of item links borrowed from the state.

# %%
r = ranking[ranking["ranked"]]
print(f"{len(r)} of {len(ranking)} districts ranked")
spread = r.groupby("state")["yoy3m_pct"].agg(["min", "max", "size"]).assign(range_pp=lambda d: d["max"] - d["min"])
spread.sort_values("range_pp", ascending=False).round(2)

# %%
fig = px.strip(r, x="yoy3m_pct", y="state", hover_name="district",
               title="Districts: change in grocery prices on a year ago (%)")
fig.write_html(REPORTS / "05_districts.html", include_plotlyjs="cdn")
pd.concat([r.head(5), r.tail(5)])[["state", "district", "yoy3m_pct", "shops", "borrowed_share"]].round(2)
