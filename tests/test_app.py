"""Basket calculator logic, plus a smoke test that the dashboard starts."""
import sys
from pathlib import Path

import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
from calculator import compare, every_state  # noqa: E402


def _prices():
    rows = [  # state, item, price now, shops, price a year ago
        ("A", 1, 10.0, 5, 9.0), ("B", 1, 12.0, 4, 11.0),
        ("A", 2, 3.0, 3, 3.0), ("B", 2, 2.5, 3, 2.5),
        ("A", 3, 7.0, 3, 7.0), ("B", 3, 6.0, 1, 6.0),     # only 1 shop in B: not comparable
        ("C", 1, 11.0, 2, 10.0), ("C", 2, 3.5, 2, 3.0),
    ]
    df = pd.DataFrame(rows, columns=["state", "item_code", "price", "shops", "price_year_ago"])
    return df.set_index(["state", "item_code"])


def test_compare_uses_quantities_and_drops_items_missing_in_either_state():
    basket = pd.DataFrame({"item_code": [1, 2, 3, 4], "qty": [2, 3, 1, 0]})
    lines, missing, tot = compare(basket, _prices(), "A", "B")
    assert list(lines["item_code"]) == [1, 2]
    assert list(missing["item_code"]) == [3]          # item 4 has qty 0, so it is simply not in the basket
    assert tot["a"] == pytest.approx(2 * 10 + 3 * 3)  # 29
    assert tot["b"] == pytest.approx(2 * 12 + 3 * 2.5)  # 31.5
    assert tot["diff"] == pytest.approx(2.5)
    assert tot["a_year_ago"] == pytest.approx(2 * 9 + 3 * 3)


def test_every_state_needs_all_items():
    basket = pd.DataFrame({"item_code": [1, 2], "qty": [1, 1]})
    lines, _, _ = compare(basket, _prices(), "A", "B")
    every = every_state(lines, _prices(), ["A", "B", "C", "D"]).set_index("state")["cost"]
    assert every.to_dict() == pytest.approx({"A": 13.0, "B": 14.5, "C": 14.5})


@pytest.mark.skipif(not (APP / "data" / "meta.json").exists(), reason="app/data not built")
def test_dashboard_starts():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
