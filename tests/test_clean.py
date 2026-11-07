import pandas as pd

from src.pricepulse.clean import flag_outliers, item_scope


def test_item_scope_groups():
    items = pd.DataFrame({
        "item_code": [-1, 1, 2, 3, 4],
        "item_group": [None, "BARANGAN SEGAR", "MAKANAN SIAP MASAK", "PRODUK KEBERSIHAN", "SUSU DAN BARANGAN BAYI"],
        "item_category": [None, "AYAM", "NASI", "PENJAGAAN DIRI", "LAMPIN PAKAI BUANG"],
    })
    assert item_scope(items)["scope"].tolist() == [None, "grocery", "eating_out", None, None]


def test_flag_outliers_uses_item_month_median():
    df = pd.DataFrame({
        "month": ["2025-01"] * 5 + ["2025-02"],
        "item_code": [1, 1, 1, 1, 2, 1],
        "price": [10.0, 11.0, 9.0, 100.0, 0.0, 2.0],  # 100 is a typo; 0 is invalid
    })
    # item 1 in Jan: median 10.5 -> 100 is >3x. Item 2: price 0 is invalid.
    # Feb has one shop only, so its price equals its own median and is kept.
    assert flag_outliers(df).tolist() == [False, False, False, True, True, False]
