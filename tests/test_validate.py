import numpy as np
import pandas as pd
import pytest

from src.pricepulse.validate import agreement, dosm_classes, dosm_comparable


def test_dosm_classes_rebased_and_named():
    df = pd.DataFrame({"date": ["2021-12-01", "2022-01-01", "2022-02-01"] * 2,
                       "class": ["0111"] * 3 + ["0112"] * 3,
                       "index": [90.0, 120.0, 132.0, 50.0, 150.0, 150.0]})
    c = dosm_classes(df)
    assert list(c.index.strftime("%Y-%m")) == ["2022-01", "2022-02"]   # starts at the base month
    assert c.loc["2022-02-01", "Cereals & cereal products"] == pytest.approx(110.0)
    assert c.loc["2022-02-01", "Meat"] == pytest.approx(100.0)


def test_dosm_comparable_uses_weights():
    classes = pd.DataFrame({"A": [100.0, 110.0], "B": [100.0, 100.0]})
    assert dosm_comparable(classes, {"A": 3.0, "B": 1.0}).iloc[1] == pytest.approx(107.5)


def test_agreement_stats():
    idx = pd.date_range("2023-01-01", periods=4, freq="MS")
    a = agreement(pd.Series([1.0, 2.0, 3.0, -1.0], idx), pd.Series([1.5, 2.5, 3.5, 0.5], idx))
    assert a["months"] == 4
    assert a["mean_abs_diff_pp"] == pytest.approx(0.75)
    assert a["same_direction_share"] == pytest.approx(0.75)
    assert a["corr"] > 0.9
