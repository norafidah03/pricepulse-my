# PricePulse MY: plan

The full, editable plan lives in the project doc. This is the short version kept with the code.

## Questions
| # | Question |
|---|----------|
| Q1 | How fast are observed food prices rising in each state (year on year, last 3 months), and where fastest? |
| Q2 | Which items and categories drive each state's change? |
| Q3 | How much does the same basket of staples cost in each state, and how has the gap changed since 2022? |
| Q4 | Does our index agree with DOSM's official food CPI by state? |
| Q5 (stretch) | Did policy events show up in prices (chicken controls lifted Nov 2023, diesel targeting Jun 2024, SST expansion Jul 2025, egg subsidy end Aug 2025)? |
| Q6 (stretch) | Do prices rise faster at wet markets, supermarkets or sundry shops, and in which districts? |

## Method
1. Median daily price per shop, item and month (`clean.py`, DuckDB).
2. Flag prices more than 3x or less than 1/3 of the item's national median that month.
3. Matched pairs: a shop's price for an item this month vs the same shop last month.
4. Item index per state = geometric mean of those price relatives (Jevons), chained, Jan 2022 = 100.
5. 14 categories weighted with DOSM CPI food class weights (CPI 2024 annual publication, Table 9).
6. Headline: last 3 months vs the same 3 months a year earlier. Plus each category's contribution in percentage points.
7. Staples basket (~20 items) priced at each state's median.
8. Validate against DOSM `cpi_2d_state` division 01.

## Scope of "food"
Groceries: BARANGAN SEGAR, BARANGAN KERING, BARANGAN BERBUNGKUS, MINUMAN, SUSU DAN BARANGAN BAYI (minus diapers).
Eating out (MAKANAN SIAP MASAK) is only published Jan to May 2022, so it is dropped. Not used: household/personal care and convenience-store items.

## Dashboard (from the design brief)
Overview · Price Trends · Compare by State (map + ranked bars) · Grocery Basket · Insights · About the data.
Light background, deep teal and navy, amber for rises, green for falls. Plain language for the public.

## Milestones
1. M1 Data foundation: fetch, clean, EDA. **(done)**
2. M2 Index (Q1) with tests. FINDINGS_01. **(done)**
3. M3 Drivers and basket (Q2, Q3). FINDINGS_02, 03.
4. M4 Validation vs DOSM CPI (Q4). FINDINGS_04.
5. M5 Streamlit dashboard, deploy, README, portfolio card.
6. M6 Stretch (Q5, Q6).
