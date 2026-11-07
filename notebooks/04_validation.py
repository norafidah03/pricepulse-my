# %% [markdown]
# # 04 · Does PricePulse agree with DOSM's official CPI? (Q4)
# Before running, from the project root: `fetch`, `clean`, `index`, then `python -m src.pricepulse.validate`.
#
# PricePulse shows **observed price changes** in KPDN PriceCatcher shops. DOSM's Consumer Price Index is the
# official measure of inflation. They use different shops, items and methods, so they should agree on
# direction and rough size, not to the decimal.

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
national = pd.read_parquet(P / "validate_national.parquet")
classes = pd.read_parquet(P / "validate_classes.parquet")
states = pd.read_parquet(P / "validate_states.parquet")
rank_corr = pd.read_parquet(P / "validate_state_rank_corr.parquet")
summary = pd.read_parquet(P / "validate_summary.parquet")

# %% [markdown]
# ## 1. National, like for like
# DOSM's 10 food-at-home and drink classes (cpi_4d), combined with the same weights as PricePulse.

# %%
long = national.melt(id_vars="month", value_vars=["ours_yoy", "dosm_yoy"], var_name="series", value_name="yoy_pct").dropna()
long["series"] = long["series"].map({"ours_yoy": "PricePulse (observed prices)", "dosm_yoy": "DOSM CPI, food at home + drinks"})
fig = px.line(long, x="month", y="yoy_pct", color="series", title="Change on a year earlier, Malaysia (%)")
fig.write_html(REPORTS / "04_national_vs_dosm.html", include_plotlyjs="cdn")
summary.round(2)

# %%
national.assign(gap_pp=national["ours_yoy"] - national["dosm_yoy"]).dropna().nlargest(5, "gap_pp")[
    ["month", "ours_yoy", "dosm_yoy", "gap_pp"]].round(2)

# %% [markdown]
# ## 2. Class by class

# %%
classes[["class", "weight", "corr", "mean_abs_diff_pp", "ours_yoy_last", "dosm_yoy_last"]].round(2)

# %% [markdown]
# ## 3. States
# DOSM publishes only the whole Food & Beverages division by state. It includes eating out
# (13.4 of its 29.8 weight points nationally), which PriceCatcher no longer covers.

# %%
fig = px.scatter(states, x="dosm_yoy_last", y="ours_yoy_last", text="state",
                 title="Change on a year earlier, Sep 2026: PricePulse groceries vs DOSM food division (%)")
fig.write_html(REPORTS / "04_states_vs_dosm.html", include_plotlyjs="cdn")
states[["state", "corr", "mean_abs_diff_pp", "ours_yoy_last", "dosm_yoy_last"]].sort_values("corr").round(2)

# %%
print(f"Do the two agree on which states rise fastest? Median rank correlation across months: "
      f"{rank_corr['rank_corr'].median():.2f} (1 = same order, 0 = unrelated)")
rank_corr.set_index("month")["rank_corr"].describe().round(2)
