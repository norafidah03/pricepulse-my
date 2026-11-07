"""Grocery basket calculator logic, kept separate from the page so it can be tested.

A state's price for an item is the median shop price over the latest 3 months (built into
app/data/calculator_prices.parquet). An item counts only where at least MIN_SHOPS shops priced it.
Items without a price in either state are left out of BOTH totals, so the comparison stays like for like.
"""
from __future__ import annotations

import pandas as pd

MIN_SHOPS = 2


def unit_price(prices: pd.DataFrame, state: str, code: int, col: str = "price") -> float | None:
    """`prices` is calculator_prices indexed by (state, item_code)."""
    try:
        row = prices.loc[(state, code)]
    except KeyError:
        return None
    value = row[col]
    return float(value) if row["shops"] >= MIN_SHOPS and pd.notna(value) else None


def compare(basket: pd.DataFrame, prices: pd.DataFrame, state_a: str, state_b: str):
    """Cost of `basket` (columns item_code, qty) in two states.

    Returns (lines, missing, totals). `lines` has unit prices A and B and costs per item;
    `missing` the basket rows left out; `totals` a dict with a, b, diff, a_year_ago (None if incomplete).
    """
    b = basket[basket["qty"] > 0].copy()
    b["A"] = [unit_price(prices, state_a, c) for c in b["item_code"]]
    b["B"] = [unit_price(prices, state_b, c) for c in b["item_code"]]
    ok = b["A"].notna() & b["B"].notna()
    lines, missing = b[ok].copy(), b[~ok].copy()
    lines["cost_a"] = lines["qty"] * lines["A"]
    lines["cost_b"] = lines["qty"] * lines["B"]
    lines["gap"] = lines["cost_b"] - lines["cost_a"]
    ago = [unit_price(prices, state_a, c, "price_year_ago") for c in lines["item_code"]]
    a_year_ago = float(sum(q * p for q, p in zip(lines["qty"], ago))) if ago and all(p is not None for p in ago) else None
    totals = {"a": float(lines["cost_a"].sum()), "b": float(lines["cost_b"].sum()), "a_year_ago": a_year_ago}
    totals["diff"] = totals["b"] - totals["a"]
    return lines, missing, totals


def every_state(lines: pd.DataFrame, prices: pd.DataFrame, states: list[str]) -> pd.DataFrame:
    """Cost of the (already comparable) basket in every state that prices all its items."""
    rows = []
    for s in states:
        ps = [unit_price(prices, s, c) for c in lines["item_code"]]
        if all(p is not None for p in ps):
            rows.append({"state": s, "cost": float(sum(q * p for q, p in zip(lines["qty"], ps)))})
    return pd.DataFrame(rows, columns=["state", "cost"])
