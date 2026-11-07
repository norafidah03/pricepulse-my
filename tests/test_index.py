import numpy as np
import pandas as pd
import pytest

from src.pricepulse.index import (
    add_changes, aggregate_links, chain, item_links, last_complete_month, price_relatives, weights_for,
)

M = pd.Timestamp


def _monthly(rows):
    return pd.DataFrame(rows, columns=["month", "premise_code", "item_code", "price", "state", "category"]).assign(
        month=lambda d: pd.to_datetime(d["month"])
    )


def test_last_complete_month():
    assert last_complete_month(M("2026-11-07")) == M("2026-10-01")
    assert last_complete_month(M("2026-10-31")) == M("2026-10-01")


def test_relatives_only_match_same_shop_and_item():
    df = _monthly([
        ("2025-01-01", 1, 10, 10.0, "A", "Eggs"),
        ("2025-02-01", 1, 10, 11.0, "A", "Eggs"),   # matched: +10%
        ("2025-02-01", 2, 10, 50.0, "A", "Eggs"),   # new shop: no pair, must not move the index
        ("2025-03-01", 1, 10, 11.0, "A", "Eggs"),   # matched: 0%
    ])
    rel = price_relatives(df)
    assert len(rel) == 2
    assert rel.sort_values("month")["log_rel"].round(6).tolist() == [round(np.log(1.1), 6), 0.0]


def test_relatives_drop_unit_mixups():
    df = _monthly([
        ("2025-01-01", 1, 10, 1.0, "A", "Spices"),
        ("2025-02-01", 1, 10, 10.0, "A", "Spices"),  # 10x jump: per-100g vs per-kg
    ])
    assert price_relatives(df).empty


def test_item_links_jevons_and_imputation():
    # State A has two shops (+10%, +21%): geometric mean = +15.36%. State B has one shop, so it borrows national.
    rel = pd.DataFrame({
        "month": [M("2025-02-01")] * 3, "item_code": [10] * 3, "category": ["Eggs"] * 3,
        "state": ["A", "A", "B"], "log_rel": np.log([1.10, 1.21, 2.0]),
    })
    links = item_links(rel, min_pairs=2).set_index("state")
    assert np.exp(links.loc["A", "log_link"]) == pytest.approx(np.sqrt(1.10 * 1.21))
    assert links.loc["B", "imputed"]
    assert np.exp(links.loc["B", "log_link"]) == pytest.approx((1.10 * 1.21 * 2.0) ** (1 / 3))


def test_aggregate_renormalises_missing_categories_and_contributions_add_up():
    cat = pd.DataFrame({"month": [M("2025-02-01")] * 2, "state": ["A"] * 2,
                        "category": ["Eggs", "Rice"], "log_link": [0.10, 0.0]})
    w = weights_for(["Eggs", "Rice", "Chicken"])  # Chicken missing this month
    total, contrib = aggregate_links(cat, ["month", "state"], w)
    assert total["log_link"].iloc[0] == pytest.approx(0.05)
    assert contrib["contrib"].sum() == pytest.approx(total["log_link"].iloc[0])


def test_chain_and_changes():
    months = pd.date_range("2022-02-01", periods=12, freq="MS")
    links = pd.DataFrame({"month": months, "state": "A", "log_link": np.log(1.01)})
    idx = add_changes(chain(links, ["state"], base="2022-01-01"), ["state"])
    assert idx["index"].iloc[0] == 100
    assert idx["index"].iloc[-1] == pytest.approx(100 * 1.01**12)
    assert idx["yoy_pct"].iloc[-1] == pytest.approx(100 * (1.01**12 - 1))
    assert idx["ann3m_pct"].iloc[-1] == pytest.approx(100 * (1.01**12 - 1))
    assert np.isnan(idx["yoy3m_pct"].iloc[-1])  # needs 14 months of history


def test_yoy3m_compares_same_three_months():
    months = pd.date_range("2022-01-01", periods=15, freq="MS")
    level = [100.0] * 12 + [110.0] * 3   # flat for a year, then 10% higher for 3 months
    idx = add_changes(pd.DataFrame({"month": months, "state": "A", "index": level}), ["state"])
    assert idx["yoy3m_pct"].iloc[-1] == pytest.approx(10.0)
