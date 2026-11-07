import numpy as np
import pandas as pd
import pytest

from src.pricepulse.events import event_study, gaps
from src.pricepulse.outlets import district_index, matched_group_index

MONTHS = pd.date_range("2022-01-01", "2024-12-01", freq="MS")


def test_gaps_sums_links_from_event_month():
    treated = pd.Series(0.0, index=MONTHS)
    control = pd.Series(0.0, index=MONTHS)
    treated[pd.Timestamp("2023-06-01")] = 0.1
    treated[pd.Timestamp("2023-07-01")] = 0.05
    g = gaps(treated, control, 2)
    assert g[pd.Timestamp("2023-06-01")] == pytest.approx(0.15)
    assert g[pd.Timestamp("2023-05-01")] == pytest.approx(0.15)  # May to Jul window also covers both
    assert g[pd.Timestamp("2023-08-01")] == pytest.approx(0.0)


def test_event_study_finds_a_jump_and_rebases_to_month_before():
    rng = np.random.default_rng(0)
    treated = pd.Series(rng.normal(0, 0.005, len(MONTHS)), index=MONTHS)
    control = pd.Series(rng.normal(0, 0.005, len(MONTHS)), index=MONTHS)
    treated[pd.Timestamp("2023-06-01")] += np.log(1.2)
    path, eff = event_study(treated, control, "2023-06-01")
    before = path[(path["month"] == pd.Timestamp("2023-05-01"))]
    assert (before["level"] == 100).all()
    k0 = eff[eff["k"] == 0].iloc[0]
    assert k0["gap_pct"] == pytest.approx(20, abs=2)
    assert k0["p_value"] == 0  # no other window comes close


def _rel(rows):
    return pd.DataFrame(rows, columns=["month", "outlet", "item_code", "category", "log_rel"]).assign(
        month=lambda d: pd.to_datetime(d["month"]))


def test_matched_group_index_uses_only_items_every_group_has():
    rows = []
    for outlet, r in [("A", 0.10), ("B", 0.00)]:
        rows += [("2022-02-01", outlet, 1, "Rice", r)] * 2
    rows += [("2022-02-01", "A", 2, "Rice", 0.5)] * 2  # only A sells item 2: must be ignored
    idx = matched_group_index(_rel(rows), "outlet")
    feb = idx[idx["month"] == pd.Timestamp("2022-02-01")].set_index("outlet")["index"]
    assert feb["A"] == pytest.approx(100 * np.exp(0.10))
    assert feb["B"] == pytest.approx(100.0)


def test_district_borrows_state_link_when_thin():
    rows = [("2022-02-01", 1, "S", "D1", 1, "Rice", 0.2)] * 3 + [("2022-02-01", 2, "S", "D2", 1, "Rice", -0.4)]
    rel = pd.DataFrame(rows, columns=["month", "premise_code", "state", "district", "item_code", "category", "log_rel"])
    rel["month"] = pd.to_datetime(rel["month"])
    idx, borrowed = district_index(rel)
    feb = idx[idx["month"] == pd.Timestamp("2022-02-01")].set_index("district")["index"]
    state_link = np.mean([0.2, 0.2, 0.2, -0.4])
    assert feb["D1"] == pytest.approx(100 * np.exp(0.2))
    assert feb["D2"] == pytest.approx(100 * np.exp(state_link))  # 1 shop < MIN_PAIRS: uses the state
    assert borrowed.set_index("district").loc["D2", "borrowed_share"] == 1.0
