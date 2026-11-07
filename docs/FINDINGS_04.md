# Findings 04 · Does PricePulse agree with DOSM's official CPI? (Q4)

PricePulse shows observed price changes in KPDN PriceCatcher shops; DOSM's Consumer Price Index (CPI) is
the official inflation measure. Data: DOSM `cpi_4d` (Malaysia, by expenditure class) and `cpi_2d_state`
(by state), to Sep 2026. Notebook: `notebooks/04_validation.py`.

## Headlines
1. **Nationally, PricePulse tracks the official figure closely.** Against DOSM's food-at-home and drinks classes,
   combined with the same weights, the two year-on-year series have a correlation of 0.92 over 45 months.
   They differ by 0.51 percentage points on average and point the same way 91% of the time.
2. **PricePulse runs slightly hotter** (+0.28 pp on average). The biggest gap was Sep 2025 to Jan 2026
   (up to 2.2 pp, Dec 2025), mostly from eggs and milk, then vegetables, fish and fruit. PriceCatcher's shops
   picked up the egg price jump after the subsidy ended (Aug 2025) faster and more fully than the CPI.
3. **Class by class, agreement is strongest for fish (0.96), vegetables (0.93) and cereals (0.92)**, and weakest
   for fruit and nuts (0.17), where PriceCatcher's fruit list is short and seasonal.
4. **By state, trends agree (correlation 0.61 to 0.93) but rankings do not** (median rank correlation 0.26).
   DOSM only publishes the whole Food & Beverages division by state, and almost half of it (13.4 of 29.8 weight
   points nationally) is eating out, which PriceCatcher no longer covers. For example, in Sep 2026 DOSM has Johor
   fastest (+3.6%) because of restaurant prices; PricePulse has Kedah fastest for groceries.

## What this means for the dashboard
- The national PricePulse figure can be shown with confidence, next to the official CPI and clearly labelled.
- State rankings are about **grocery shelf prices only**. The About page must say they are not state inflation
  rates and can differ from DOSM's state figures, which include eating out.

## Agreement by DOSM class (year-on-year %, Jan 2023 to Sep 2026)
| DOSM class | CPI weight | Correlation | Avg gap (pp) | PricePulse Sep 2026 | DOSM Sep 2026 |
|---|---|---|---|---|---|
| Fish & seafood | 3.9 | 0.96 | 1.11 | 0.9 | 1.5 |
| Vegetables | 1.8 | 0.93 | 1.81 | 2.7 | 0.9 |
| Cereals & cereal products | 2.3 | 0.92 | 1.72 | -1.4 | 0.2 |
| Non-alcoholic beverages | 0.8 | 0.88 | 1.19 | 0.2 | -0.3 |
| Meat | 2.3 | 0.77 | 1.95 | 5.4 | 2.8 |
| Oils & fats | 0.7 | 0.76 | 1.86 | -0.1 | -0.1 |
| Sugar, confectionery & desserts | 0.5 | 0.74 | 1.03 | 1.7 | 0.4 |
| Milk, other dairy products & eggs | 1.3 | 0.64 | 2.28 | -0.1 | 2.1 |
| Ready-made food & other food n.e.c. | 1.7 | 0.64 | 1.79 | 0.1 | 0.7 |
| Fruits & nuts | 1.1 | 0.17 | 2.68 | 2.7 | 1.0 |

## Caveats
- DOSM's comparable series is a fixed-weight average of class indices rebased to Jan 2022, an approximation
  of how DOSM itself aggregates.
- DOSM weights changed in Jan 2024 (new HES 2022 basket); we use the new weights for the whole period.
