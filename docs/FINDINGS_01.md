# Findings 01 · How fast are grocery prices rising in each state? (Q1)

Data: KPDN PriceCatcher via data.gov.my, Jan 2022 to Oct 2026 (latest complete month; data to 7 Nov 2026).
These are **observed price changes** for about 290 grocery items in PriceCatcher shops, not official inflation.
Categories are weighted with DOSM's CPI food weights (see Method). Notebook: `notebooks/02_index.py`.

## Headlines
1. **Observed grocery prices in Malaysia are 9.7% higher than in January 2022.** Most of that came in 2022
   (+6.3% in the year to Jan 2023). Since then the yearly change has stayed between about -0.3% and +3%.
2. **Right now prices are rising slowly: +1.2% for Aug to Oct 2026 compared with a year earlier.**
3. **Kedah is rising fastest (+2.3%), followed by Kelantan, Selangor and Putrajaya (+1.9%).**
   Sabah (-1.2%) and Labuan (-0.2%) are the only states where prices fell.
4. **The gap between states is small.** The fastest and slowest state are typically 1.5 percentage points apart.
   Month-to-month rankings reshuffle a lot, so the dashboard ranks states on a 3-month average.
5. **Since Jan 2022, Putrajaya (+11.8%) and Perlis (+11.1%) have risen most; Sabah (+7.5%) and Melaka (+7.8%) least.**

## What drives it (contribution to the year-on-year change, Oct 2026, percentage points)
- Malaysia: up from beef and mutton (+0.43), vegetables (+0.37), onions, chilli and spices (+0.33), chicken (+0.28);
  down from fruit and coconut (-0.30), rice (-0.13) and fish and seafood (-0.12).
- Kedah leads because fish and seafood went **up** there (+0.61 pp), against the national trend.
- Kelantan: onions, chilli and spices (+0.74) and chicken (+0.56).
- Sabah fell because fish and seafood dropped sharply (-2.27 pp). Fish is the largest food-at-home weight in the CPI.

## Category view, Malaysia (Jan 2022 = 100, Oct 2026)
Eggs 127.5 is the biggest rise since 2022, and very volatile since the subsidy ended in Aug 2025.
Sauces 121.3, onions/chilli/spices 117.7, beef and mutton 114.2. Vegetables 97.5, cooking oil 101.7 and
rice 102.7 are the lowest. Cooking oil and sugar are largely price-controlled.

## Method: weights
Each of our 14 categories is mapped to a DOSM CPI expenditure class and gets that class's weight,
split equally when two categories share a class (Meat 2.3 -> chicken 1.15, beef and mutton 1.15).
Weights are DOSM's national weights (HES 2022 basket), from the
[CPI Malaysia 2024 annual publication, Table 9](https://www.dosm.gov.my/uploads/release-content/file_20260518103117.pdf):
cereals 2.3, meat 2.3, fish and seafood 3.9, milk/dairy/eggs 1.3, oils and fats 0.7, fruits and nuts 1.1,
vegetables 1.8, sugar and confectionery 0.5, ready-made and other food 1.7, non-alcoholic drinks 0.8 (% of the CPI).

With equal weights instead, the national figure is +1.4% (vs +1.2%) and Kelantan and Kedah tie for fastest;
Sabah moves from -1.2% to +0.2% because fish counts for less. The overall picture is the same.

## Caveats
- **National weights for every state.** DOSM's publication gives weights for Malaysia, urban, rural and
  households under RM3,000, not per state.
- **Equal split inside a class** (e.g. chicken and beef share meat equally) is our assumption.
- **Small states borrow the national figure** for items with fewer than 2 matched shops: 12% of items in KL,
  31% in Perlis, 44% in Labuan. Their indices are pulled towards the national one.
- **10-day gap (30 Sep to 9 Oct 2026):** October 2026 prices come from 10 to 31 October.
- **Eating out is not covered.** PriceCatcher published restaurant prices only from Jan to May 2022.
- Fresh produce bounces from month to month, so a chained index can drift slightly.
