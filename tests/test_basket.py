import pandas as pd

from src.pricepulse.basket import basket_cost, window_prices
from src.pricepulse.drivers import top_movers


def _rows():
    return pd.DataFrame({
        "month": pd.to_datetime(["2026-08-01", "2026-09-01", "2026-10-01", "2026-10-01", "2026-10-01", "2026-07-01"]),
        "state": ["A", "A", "A", "A", "B", "A"],
        "premise_code": [1, 2, 3, 1, 9, 1],
        "label": ["Eggs"] * 3 + ["Rice", "Eggs", "Eggs"],
        "price": [10.0, 12.0, 14.0, 30.0, 11.0, 99.0],  # July is outside the Aug-Oct window
    })


def test_window_prices_pools_three_months():
    p = window_prices(_rows(), pd.Timestamp("2026-10-01")).set_index(["state", "label"])
    assert p.loc[("A", "Eggs"), "price"] == 12.0      # median of 10, 12, 14; July ignored
    assert p.loc[("A", "Eggs"), "shops"] == 3


def test_basket_cost_flags_missing_and_thin_items():
    p = window_prices(_rows(), pd.Timestamp("2026-10-01"))
    c = basket_cost(p, ["Eggs", "Rice"], min_shops=2).set_index("state")
    assert c.loc["A", "cost"] == 42.0
    assert not c.loc["A", "complete"]   # rice priced by 1 shop only
    assert not c.loc["B", "complete"]   # no rice at all, and eggs from 1 shop


def test_top_movers_per_group_keeps_group_column():
    t = pd.DataFrame({"state": ["A", "A", "A", "B", "B"], "item": list("vwxyz"), "chg": [5, -3, 1, 2, -8]})
    m = top_movers(t, "chg", 1, group="state")
    up = m[m["direction"] == "up"].set_index("state")["item"].to_dict()
    down = m[m["direction"] == "down"].set_index("state")["item"].to_dict()
    assert up == {"A": "v", "B": "y"} and down == {"A": "w", "B": "z"}
