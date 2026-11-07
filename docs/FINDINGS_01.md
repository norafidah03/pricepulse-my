# Findings 01 · How fast are grocery prices rising in each state? (Q1)

Data: KPDN PriceCatcher via data.gov.my, Jan 2022 to Oct 2026 (latest complete month; data to 7 Nov 2026).
These are **observed price changes** for about 290 grocery items in PriceCatcher shops, not official inflation.
Notebook: `notebooks/02_index.py`.

## Headlines
1. **Observed grocery prices in Malaysia are 10.9% higher than in January 2022.** Most of that came in 2022
   (+6.5% in the year to Jan 2023). Since 2023 the yearly change has stayed between about -1% and +3%.
2. **Right now prices are rising slowly: +1.4% for Aug to Oct 2026 compared with a year earlier.**
3. **Kelantan and Kedah are rising fastest (+2.2%), followed by KL and Selangor (+2.0%).**
   Sabah (+0.2%) and Labuan (0.0%) are nearly flat.
4. **The gap between states is small.** The fastest and slowest state are typically only 1.25 percentage
   points apart. Month-to-month rankings reshuffle a lot, so the dashboard ranks states on a 3-month average.
5. **Since Jan 2022, Putrajaya (+13.0%) and Perlis (+12.6%) have risen most; Melaka (+9.7%) least.**

## What drives it (contribution to the national year-on-year change, Oct 2026)
- Up: vegetables (+0.48 pp), beef and mutton (+0.44), onions, chilli and spices (+0.42), chicken (+0.28).
- Down: fruit and coconut (-0.32), eggs (-0.15), rice (-0.14).
- Kelantan's lead comes from onions, chilli and spices (+0.96 pp) and chicken (+0.58).
- Sabah is flat mainly because fish and seafood fell (-0.69 pp).

## Category view, Malaysia (Jan 2022 = 100, Oct 2026)
Eggs 127.5 is the biggest rise since 2022, and very volatile since the subsidy ended in Aug 2025.
Sauces 121.3, onions/chilli/spices 117.7, beef and mutton 114.2. Rice 102.7, cooking oil 101.7 and
vegetables 97.5 are the lowest. Cooking oil and sugar are largely price-controlled.

## Caveats
- **Equal weights per category.** DOSM's food sub-group weights are not published as a dataset, so each of the
  14 categories counts the same. Rice counts as much as sauces. The weights live in `config.CATEGORY_WEIGHTS`
  and can be switched to DOSM's weights later.
- **Small states borrow the national figure** for items with fewer than 2 matched shops: 12% of items in KL,
  31% in Perlis, 44% in Labuan. Their indices are pulled towards the national one.
- **10-day gap (30 Sep to 9 Oct 2026):** October 2026 prices come from 10 to 31 October.
- **Eating out is not covered.** PriceCatcher published restaurant prices only from Jan to May 2022.
- Fresh produce bounces from month to month, so a chained index can drift slightly. For example, the tomato
  index ends about 7% below the simple median price ratio.
