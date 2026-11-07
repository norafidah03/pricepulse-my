# Findings 05 · Policy events, types of shop and districts (Q5, Q6)

Data: KPDN PriceCatcher, Jan 2022 to Oct 2026, the same matched shop-and-item price changes as the main index.
Code: `src/pricepulse/events.py`, `src/pricepulse/outlets.py`. Notebook: `notebooks/05_events_outlets.py`.

## Q5 · Did policy changes show up in prices?

Method: each change is compared with a group of prices it should not have touched. The gap is the treated
group's change minus the comparison group's change, from the month before the change to 2 months after
(3 monthly steps). To judge whether a gap is unusual, the same gap is worked out for every other 3-month spell
at least 6 months away from the change (a placebo test). The p-value is the share of those spells with a gap
at least as large.

| Change | Treated | Comparison | Treated, 3 months | Comparison | Gap | Share of other spells as large |
|---|---|---|---|---|---|---|
| Chicken subsidy and price ceiling ended, 1 Nov 2023 | Fresh and live chicken | All other groceries | +4.6% | +2.0% | +2.5 pts | 45% |
| Diesel subsidy targeted, 10 Jun 2024 (Peninsula only) | Groceries in the Peninsula | Groceries in Sabah, Sarawak, Labuan | -0.1% | -0.2% | +0.1 pts | 93% |
| Egg subsidy halved 1 May 2025, ended 1 Aug 2025 | Eggs, grades A to C, trays of 30 | All other groceries | +18.6% | +0.9% | +17.5 pts | 7% |
| Sales tax on imported fruit, 1 Jul 2025 | Grapes (taxed 5%) | Other fruit (local, or exempted apples and oranges) | -20.3% | -3.1% | -17.7 pts | 27% |

1. **Only the end of the egg subsidy left a clear mark.** Egg prices rose 18.6% in the 3 months from August 2025,
   while other groceries barely moved. Only 3 of 44 other 3-month spells had a gap that large. Eggs also swing
   on their own (they dipped about 10% in April 2025 and again in April 2026), which is why the test is not stronger.
2. **The end of chicken price controls did not push prices up.** Chicken fell 1.6% in November 2023 and rose
   4.6% over three months, within its usual range. This matches news reports that most shops stayed under the old
   RM9.40 ceiling.
3. **Targeted diesel did not open a gap between the Peninsula and East Malaysia.** If higher transport costs
   passed into shelf prices, it was too small or too slow to see against normal monthly noise.
4. **The sales tax on imported fruit is not visible.** Grapes fell after July 2025, but grape prices are highly
   seasonal, and the government exempted apples, oranges and dates days before the tax started, so only a
   few PriceCatcher fruits were taxed.

Caveat: this is an observational comparison. Other things happened at the same time (for example RON95 targeting
in Sep 2025), and the p-values come from 41 to 46 other windows, so they are rough guides, not formal tests.

Sources on the changes: chicken ([Malay Mail](https://www.malaymail.com/news/malaysia/2023/10/31/chicken-prices-can-be-lower-than-rm940-per-kg-after-november-1-says-armizan/99473)),
diesel ([MOF](https://mof.gov.my/portal/en/news/press-release/government-implements-targeted-diesel-subsidy-for-peninsular-malaysia-effective-10-june-2024)),
eggs ([The Star](https://www.thestar.com.my/news/nation/2025/04/30/egg-subsidy-rate-reduced-from-rm010-to-rm005-per-egg-effective-may-1)),
fruit tax ([FreshPlaza](https://www.freshplaza.com/asia/article/9745616/malaysia-exempts-imported-fruits-from-sales-and-service-tax)).
Reports differ on whether the egg price ceiling stayed after August 2025, so the dashboard only says the subsidy ended.

## Q6 · Does it matter where you shop?

Method, price levels: for the same item in the same state, Aug to Oct 2026, each type of shop's median price
is compared with the supermarket median, then averaged (geometric mean) over about 1,700 to 3,000 item-state pairs.
Method, growth: a grocery index for each type of shop, using only items that every type of shop priced in that
month (155 items in Oct 2026), so the shopping lists match.

5. **Hypermarkets are the cheapest and have risen least.** They are 2.5% cheaper than supermarkets for the same
   items, and their prices are up 8.2% since January 2022.
6. **Wet markets and sundry shops are dearer than supermarkets for the same items**: +10.1% and +8.3%. The gap is
   biggest for vegetables (+19.5% at wet markets, +26.1% at sundry shops) and onions, chilli and spices (+16.8%).
   Beef and mutton is the exception: cheaper at wet markets and sundry shops. PriceCatcher records a standard item
   (for example 1 kg of a named vegetable), but quality and freshness can still differ between shops.
7. **Wet market prices have also risen fastest**, +12.2% since January 2022 against +8.2% at hypermarkets.
   In the past year the types of shop moved within 1.1 percentage points of each other (+0.6% to +1.7%).

## Q6 · Which districts?

Method: a grocery index for each district, built like the state index. Where a district has fewer than 2
matching shops for an item, it uses the state's change for that item. A district is ranked only if it had at
least 10 shops in the last 3 months and used the state's change for under half its items in the past year.
92 of 171 districts pass.

8. **Fastest-rising districts (Aug to Oct 2026 on a year ago):** Larut, Matang & Selama, Perak (+3.0%);
   Putrajaya (+2.9%); Bera, Pahang (+2.8%); Kuala Kangsar, Perak (+2.7%); and four Kelantan districts
   (Tumpat, Pasir Mas, Tanah Merah, Machang, +2.6% to +2.7%).
9. **Prices fell in all five ranked Sabah districts**, most in Kota Kinabalu (-3.6%) and Tawau (-3.2%), and in
   Lawas, Sarawak (-0.4%). This agrees with Sabah being the only falling state (Findings 02).
10. **Districts within a state mostly move together.** The gap between a state's fastest and slowest ranked
    districts is usually around 1 percentage point. Sarawak is the widest (2.4 points), from Lawas (-0.4%) to +2.0%.
