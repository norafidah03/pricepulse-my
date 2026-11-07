"""Paths, URLs and the item scope used across the project."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
APP_DATA = ROOT / "app" / "data"

PRICECATCHER_BASE = "https://storage.data.gov.my/pricecatcher"
MONTH_URL = PRICECATCHER_BASE + "/pricecatcher_{ym}.parquet"
LOOKUP_ITEM_URL = PRICECATCHER_BASE + "/lookup_item.parquet"
LOOKUP_PREMISE_URL = PRICECATCHER_BASE + "/lookup_premise.parquet"
CPI_STATE_URL = "https://storage.dosm.gov.my/cpi/cpi_2d_state.parquet"

FIRST_MONTH = "2022-01"  # PriceCatcher files on data.gov.my start here

# Item groups (lookup_item.item_group) and what we do with them.
GROCERY_GROUPS = [
    "BARANGAN SEGAR",          # fresh: chicken, meat, fish, vegetables, eggs, fruit
    "BARANGAN KERING",         # dry: onions, dried chilli, nuts, potatoes
    "BARANGAN BERBUNGKUS",     # packaged: rice, sugar, flour, cooking oil, bread
    "MINUMAN",                 # drinks and drink ingredients (coffee, tea, milo)
    "SUSU DAN BARANGAN BAYI",  # milk powder and baby food (diapers excluded below)
]
EATING_OUT_GROUPS = ["MAKANAN SIAP MASAK"]  # cooked food at restaurants: a separate index
EXCLUDED_CATEGORIES = ["LAMPIN PAKAI BUANG"]  # diapers are not food
# Not used: PRODUK KEBERSIHAN (household and personal care),
# BARANGAN KEDAI SERBANEKA (convenience-store items, mostly non-food).

# Outlier rule: a shop's monthly price is flagged if it is more than OUTLIER_RATIO times,
# or less than 1/OUTLIER_RATIO of, the national median for that item in that month.
OUTLIER_RATIO = 3.0
