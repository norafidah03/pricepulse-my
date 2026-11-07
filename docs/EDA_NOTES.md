# M1 EDA notes (data as of 7 Nov 2026)

From `notebooks/01_eda.py`.

- **Coverage:** 1 Jan 2022 to 7 Nov 2026. 1,670 days with data, 102 missing, mostly single days around public holidays.
  The longest gap is **30 Sep to 9 Oct 2026 (10 days)**, so October 2026 is built from 10 to 31 Oct only.
- **Partial month:** November 2026 has 7 days. The index will stop at the last complete month (Oct 2026) and say so.
- **Size:** 14.1M shop x item x month rows after collapsing daily prices; 491 grocery items and 191 eating-out items ever seen.
- **Shops per state** range from about 15 (Labuan) and 28 (Putrajaya) to 228 (Sarawak) for groceries in Oct 2026.
  Several states gained many shops in 2025 (Johor 142 to 214, Pahang 86 to 190, Melaka 27 to 53). A plain average
  would mix those new shops in; the matched-pair index does not.
- **Panel stability:** in a typical month 94% of shop x item prices can be matched to the same shop last month.
  The low point is Jul 2025 (75%), when KPDN changed the item list and many shops joined. Still plenty of pairs.
- **Outliers:** 0.06% of monthly prices flagged (8,332 rows), mostly dried squid, shallots and leafy greens where
  shops mix up per-100 g and per-kg prices.
- **Staples, national median shop price:** grade A eggs (30) went from RM12.90 (Jan 2022) to RM15.50 (Oct 2026),
  most of it after the egg subsidy ended in Aug 2025. Sugar stayed at RM2.85 (controlled). Cooking oil 2 kg at RM13.30
  since 2023. Chicken is roughly flat at RM8.60 to 9.40.
- **Small states** (Labuan, Putrajaya, Perlis, Melaka) will have noisy indices; the dashboard should show shop counts
  next to them.
