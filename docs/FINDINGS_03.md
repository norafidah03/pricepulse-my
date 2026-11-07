# Findings 03 · What does the same grocery basket cost in each state? (Q3)

Basket: 20 everyday staples, one of each (chicken, eggs, fish, sardines, cooking oil, sugar, flour, instant
noodles, onion, garlic, dried chilli, tomato, cucumber, carrot, potato, coconut milk, soy sauce, tea, coffee, rice).
Each priced at the state's median shop price over 3 months. List: `config.BASKET_ITEMS`.
Notebook: `notebooks/03_drivers_basket.py`.

## Headlines
1. **The basket costs RM212.50 in Malaysia (Aug to Oct 2026), up 2.0% on a year earlier and 13.8% on Jan to Mar 2022.**
2. **The same basket costs RM20.84 more in Putrajaya (RM226.55) than in Kedah (RM205.71).**
   KL (RM223.27) and Sarawak (RM222.54) are next most expensive; Kedah, Perak and Perlis are cheapest.
3. **Northern states are cheapest but rising fastest:** Perlis (+3.7%), Kedah (+3.6%) and Perak (+3.4%) on a year earlier.
   Sabah is the only state where the basket got cheaper (-0.3%).
4. **Since 2022, Terengganu's basket rose most (+17.6%), Sabah's least (+11.2%).**
5. **The basket peaked at RM217.27 in Sep to Nov 2023**, eased to RM201.50 by Mar to May 2026, then rose again with vegetable prices.

## Where states differ most (Aug to Oct 2026)
- Fish (ikan selar): RM9.90 per kg between the cheapest (Sabah) and dearest (Putrajaya).
- Rice, 10 kg: RM8.00 gap, cheapest in Sabah, dearest in Putrajaya (different brands; see caveat).
- Dried chilli: RM6.10; tomato: RM4.10; chicken: RM3.91 (cheapest Johor, dearest Sabah).
- Sugar and cooking oil are almost identical everywhere (price-controlled).

## Why the basket and the index differ
The basket rose 2.0% while the index rose 1.2% (Oct 2026, year on year). The basket adds up ringgit prices,
so expensive items (rice, fish, dried chilli, coffee) count more. The index weights categories by household
spending and covers about 290 items. Both are correct; they answer different questions.

## Caveats
- **Rice is any brand:** no single 10 kg rice brand is sold in every state, so rice is the median of all
  imported white rice 10 kg packs in the state. Sabah and Sarawak sell different, cheaper brands.
  Marked with * on the dashboard.
- **Labuan is flagged as incomplete:** standard chicken is priced by only 1 Labuan shop in recent windows.
- One of each item is not a real shopping list; the dashboard will let people untick items.
