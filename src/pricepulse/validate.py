"""Check PricePulse's index against DOSM's official Consumer Price Index (Q4).

Two comparisons:
1. National, like for like: DOSM's 10 food-at-home and non-alcoholic drink classes (cpi_4d), combined with
   the same weights we use, vs our Malaysia index. Also class by class.
2. States: DOSM publishes only the whole Food & Beverages division (01) by state, which includes
   eating out (about 45% of its weight). So we compare trends over time, and expect rankings to differ.

Run from the project root after `index`:
    python -m src.pricepulse.validate
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .index import add_changes, chain

BASE = pd.Timestamp(config.INDEX_BASE)


def dosm_classes(cpi_4d: pd.DataFrame) -> pd.DataFrame:
    """DOSM class indices from the base month on, rebased to base = 100. Columns = class names."""
    d = cpi_4d.assign(date=pd.to_datetime(cpi_4d["date"]))
    d = d[d["class"].isin(config.DOSM_CLASS_CODES)].assign(cls=lambda x: x["class"].map(config.DOSM_CLASS_CODES))
    wide = d.pivot(index="date", columns="cls", values="index").loc[BASE:]
    return 100 * wide / wide.iloc[0]


def dosm_comparable(classes: pd.DataFrame, weights: dict[str, float] = config.DOSM_CLASS_WEIGHTS) -> pd.Series:
    """Fixed-weight average of the rebased class indices: DOSM's 'groceries' on our basis."""
    w = pd.Series(weights)[classes.columns]
    return (classes * w).sum(axis=1) / w.sum()


def our_classes(category_idx: pd.DataFrame) -> pd.DataFrame:
    """Our Malaysia category indices regrouped into DOSM classes (geometric mean of category links)."""
    c = category_idx[(category_idx["state"] == "Malaysia") & (category_idx["month"] > BASE)].copy()
    c["cls"] = c["category"].map(config.CATEGORY_TO_DOSM_CLASS)
    links = c.groupby(["month", "cls"])["log_link"].mean().rename("log_link").reset_index()
    return chain(links, ["cls"], base=config.INDEX_BASE).pivot(index="month", columns="cls", values="index")


def yoy(wide: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    wide = wide.asfreq("MS")
    return 100 * (wide / wide.shift(12) - 1)


def agreement(ours: pd.Series, dosm: pd.Series) -> dict[str, float]:
    """How closely two year-on-year series agree over the months both have."""
    both = pd.concat([ours, dosm], axis=1, keys=["ours", "dosm"], sort=True).dropna()
    diff = both["ours"] - both["dosm"]
    return {"months": len(both), "corr": both.corr().iloc[0, 1], "mean_abs_diff_pp": diff.abs().mean(),
            "mean_diff_pp": diff.mean(), "same_direction_share": (np.sign(both["ours"]) == np.sign(both["dosm"])).mean()}


def build(P=config.PROCESSED, raw=config.RAW) -> dict[str, pd.DataFrame]:
    state = pd.read_parquet(P / "index_grocery_state.parquet")
    category = pd.read_parquet(P / "index_grocery_category.parquet")
    cpi4 = pd.read_parquet(raw / "cpi_4d.parquet")
    cpis = pd.read_parquet(raw / "cpi_2d_state.parquet")

    # 1. National, like for like
    d_cls = dosm_classes(cpi4)
    d_nat = dosm_comparable(d_cls)
    o_nat = state[state["state"] == "Malaysia"].set_index("month")["index"]
    national = pd.DataFrame({"ours_index": o_nat, "dosm_index": d_nat,
                             "ours_yoy": yoy(o_nat), "dosm_yoy": yoy(d_nat)}).rename_axis("month").reset_index()

    # 1b. Class by class
    o_cls = our_classes(category)
    rows = []
    for cls in config.DOSM_CLASS_CODES.values():
        a = agreement(yoy(o_cls[cls]), yoy(d_cls[cls]))
        last = d_cls.index.max()
        rows.append({"class": cls, "weight": config.DOSM_CLASS_WEIGHTS[cls], **a,
                     "ours_yoy_last": yoy(o_cls[cls]).get(last), "dosm_yoy_last": yoy(d_cls[cls]).get(last),
                     "month": last})
    classes = pd.DataFrame(rows)

    # 2. States: our groceries vs DOSM's whole food division (includes eating out)
    s = cpis.assign(date=pd.to_datetime(cpis["date"]))
    s = s[s["division"] == "01"].pivot(index="date", columns="state", values="index")
    o_st = state.pivot(index="month", columns="state", values="index")
    rows = []
    last = s.index.max()
    for st in s.columns.intersection(o_st.columns):
        a = agreement(yoy(o_st[st]), yoy(s[st]))
        rows.append({"state": st, **a, "ours_yoy_last": yoy(o_st[st]).get(last), "dosm_yoy_last": yoy(s[st]).get(last),
                     "month": last})
    states = pd.DataFrame(rows)
    # Rank agreement across states, month by month
    yo, yd = yoy(o_st[states["state"]]), yoy(s[states["state"]])
    months = yo.dropna().index.intersection(yd.dropna().index)
    rank_corr = pd.Series({m: yo.loc[m].rank().corr(yd.loc[m].rank()) for m in months}, name="rank_corr")

    summary = pd.DataFrame([{"comparison": "Malaysia groceries vs DOSM food at home + drinks",
                             **agreement(national.set_index("month")["ours_yoy"], national.set_index("month")["dosm_yoy"])}])
    return {"national": national, "classes": classes, "states": states,
            "state_rank_corr": rank_corr.rename_axis("month").reset_index(), "summary": summary}


def main() -> None:
    out = build()
    for name, t in out.items():
        t.to_parquet(config.PROCESSED / f"validate_{name}.parquet", index=False)
    print(out["summary"].round(2).to_string(index=False))
    print("\nBy DOSM class:")
    print(out["classes"][["class", "corr", "mean_abs_diff_pp", "ours_yoy_last", "dosm_yoy_last"]].round(2).to_string(index=False))
    print("\nBy state (vs DOSM Food & Beverages division, which includes eating out):")
    print(out["states"][["state", "corr", "mean_abs_diff_pp", "ours_yoy_last", "dosm_yoy_last"]].round(2).to_string(index=False))
    print(f"\nState ranking agreement (Spearman), median over months: {out['state_rank_corr']['rank_corr'].median():.2f}")


if __name__ == "__main__":
    main()
