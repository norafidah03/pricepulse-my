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

# ---- Index settings (M2) ----
INDEX_BASE = "2022-01"   # index = 100 in this month
MIN_PAIRS = 2            # matched shops needed for a state's item link; fewer -> use the national link
MAX_RELATIVE = 3.0       # drop month-on-month price relatives above 3x or below 1/3 (likely unit mix-ups)

# PriceCatcher item_category -> the plain-English category shown on the dashboard.
GROCERY_CATEGORIES = {
    "BERAS": "Rice", "TEPUNG": "Flour, bread & noodles", "BIHUN": "Flour, bread & noodles",
    "MEE/KUETIAU": "Flour, bread & noodles", "MI SEGERA": "Flour, bread & noodles", "ROTI": "Flour, bread & noodles",
    "AYAM": "Chicken",
    "DAGING": "Beef & mutton",
    "BAHAN LAUT": "Fish & seafood", "IKAN DARAT": "Fish & seafood", "HASIL LAUT KERING": "Fish & seafood",
    "IKAN DALAM TIN": "Fish & seafood",
    "TELUR": "Eggs",
    "KRIMER DAN SUSU TEPUNG": "Milk & baby food", "MENTEGA": "Milk & baby food", "SUSU BAYI": "Milk & baby food",
    "MAKANAN BAYI": "Milk & baby food",
    "MINYAK DAN LEMAK": "Cooking oil",
    "SAYUR-SAYURAN": "Vegetables", "UBI KENTANG": "Vegetables", "TAUHU DAN TEMPE": "Vegetables",
    "BAWANG": "Onions, chilli & spices", "CILI KERING": "Onions, chilli & spices",
    "REMPAH RATUS (BERBUNGKUS)": "Onions, chilli & spices", "REMPAH RATUS (TIDAK BERBUNGKUS)": "Onions, chilli & spices",
    "ESEN DAN RAGI": "Onions, chilli & spices",
    "BUAH-BUAHAN": "Fruit & coconut", "KELAPA": "Fruit & coconut", "SANTAN (KOTAK)": "Fruit & coconut",
    "GULA": "Sugar, spreads & nuts", "SAPUAN (SPREADS)": "Sugar, spreads & nuts", "KACANG": "Sugar, spreads & nuts",
    "KICAP DAN SOS": "Sauces",
    "BAHAN-BAHAN MINUMAN": "Drinks", "TERSEDIA MINUM": "Drinks",
}
EATING_OUT_CATEGORIES = {
    "NASI": "Rice dishes", "LAUK": "Side dishes (lauk)", "MEE / BIHUN / KUEY TEOW": "Noodle dishes",
    "MINUMAN": "Drinks (restaurant)", "LAIN-LAIN": "Other cooked food",
}
# ---- Category weights ----
# DOSM CPI weights (% of the whole CPI basket) for the "Food at home" expenditure classes plus
# non-alcoholic beverages, Malaysia, weight reference period 2022 (HES 2022), used from Jan 2024.
# Source: DOSM, Consumer Price Index Malaysia 2024 annual publication, Table 9 (Jadual 9), "Wajaran / Weight" row:
# https://www.dosm.gov.my/uploads/release-content/file_20260518103117.pdf
DOSM_CLASS_WEIGHTS = {
    "Cereals & cereal products": 2.3,
    "Meat": 2.3,
    "Fish & seafood": 3.9,
    "Milk, other dairy products & eggs": 1.3,
    "Oils & fats": 0.7,
    "Fruits & nuts": 1.1,
    "Vegetables": 1.8,
    "Sugar, confectionery & desserts": 0.5,
    "Ready-made food & other food products n.e.c.": 1.7,
    "Non-alcoholic beverages": 0.8,
}
# Which DOSM class each of our categories belongs to. A class's weight is split equally
# between our categories in it (e.g. Meat 2.3 -> Chicken 1.15, Beef & mutton 1.15).
CATEGORY_TO_DOSM_CLASS = {
    "Rice": "Cereals & cereal products",
    "Flour, bread & noodles": "Cereals & cereal products",
    "Chicken": "Meat",
    "Beef & mutton": "Meat",
    "Fish & seafood": "Fish & seafood",
    "Milk & baby food": "Milk, other dairy products & eggs",
    "Eggs": "Milk, other dairy products & eggs",
    "Cooking oil": "Oils & fats",
    "Fruit & coconut": "Fruits & nuts",
    "Vegetables": "Vegetables",
    "Onions, chilli & spices": "Vegetables",
    "Sugar, spreads & nuts": "Sugar, confectionery & desserts",
    "Sauces": "Ready-made food & other food products n.e.c.",
    "Drinks": "Non-alcoholic beverages",
}


def _category_weights() -> dict[str, float]:
    per_class = {}
    for cat, cls in CATEGORY_TO_DOSM_CLASS.items():
        per_class.setdefault(cls, []).append(cat)
    return {cat: DOSM_CLASS_WEIGHTS[cls] / len(cats) for cls, cats in per_class.items() for cat in cats}


# Weights used in the state index (normalised to sum to 1 when used). Set to None for equal weights.
CATEGORY_WEIGHTS: dict[str, float] | None = _category_weights()

# ---- Grocery basket (M3) ----
# One of each item, priced at the state's median shop price. Chosen because every state has at least
# BASKET_MIN_SHOPS shops pricing it in every comparison window since 2022 (checked in notebook 03).
# item_code -> plain-English label shown on the dashboard.
BASKET_ITEMS = {
    1: "Chicken, standard (1 kg)",
    1110: "Eggs, grade B (30)",
    70: "Fish, ikan selar (1 kg)",
    191: "Sardines in tomato sauce, Cap Ayam (425 g)",
    1601: "Cooking oil, Cap Buruh (2 kg)",
    1589: "White sugar, coarse (1 kg)",
    917: "Wheat flour, Cap Sauh (1 kg)",
    1976: "Instant noodles, Maggi curry (5 x 79 g)",
    129: "Yellow onion (1 kg)",
    1564: "Garlic, imported (1 kg)",
    1899: "Dried chilli (1 kg)",
    114: "Tomato (1 kg)",
    113: "Cucumber (1 kg)",
    109: "Carrot (1 kg)",
    1131: "Potato, imported (1 kg)",
    1611: "Coconut milk, Kara (200 ml)",
    214: "Sweet soy sauce, Kipas Udang (345 ml)",
    180: "Tea bags, BOH (100)",
    929: "Instant coffee, Nescafe Classic (200 g)",
}
# Rice has no single brand sold in every state (Sabah and Sarawak sell different brands), so the basket
# uses the median price of any 10 kg imported white rice pack in the state. Flagged on the dashboard.
BASKET_RICE_LABEL = "Rice, imported white, any brand (10 kg)*"
BASKET_RICE_CATEGORY = "BERAS"
BASKET_RICE_UNIT = "10 kg"
BASKET_MIN_SHOPS = 2      # shops per state per item in a 3-month window
BASKET_WINDOW = 3         # months pooled for each basket price (e.g. Aug to Oct)
