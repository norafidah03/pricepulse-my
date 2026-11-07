# PricePulse MY: Malaysia Food Price Intelligence

*Know your prices. Understand your cost of living.*

PricePulse MY tracks everyday food prices across Malaysia using KPDN's PriceCatcher data, published on
[data.gov.my](https://data.gov.my). It answers: how fast are observed food prices changing in each state,
which items are driving it, and how much does the same grocery basket cost from state to state?

> Status: work in progress (milestone 3 of 5: price index, drivers and basket done). See [docs/PLAN.md](docs/PLAN.md).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.pricepulse.fetch      # downloads ~160 MB of monthly PriceCatcher files into data/raw/
python -m src.pricepulse.clean      # one price per shop, item and month -> data/processed/ (~20 s)
python -m src.pricepulse.index      # state food price index -> data/processed/ (~1 min)
python -m src.pricepulse.drivers    # categories and items driving the change
python -m src.pricepulse.basket     # 20-item grocery basket cost by state
pytest
# open notebooks/01_eda.py to 03_drivers_basket.py in VS Code and run the cells
```

## Data sources
- PriceCatcher daily item prices by premise, KPDN via data.gov.my (`storage.data.gov.my/pricecatcher/`), Jan 2022 onwards
- PriceCatcher item and premise lookups (same location)
- Consumer Price Index by state and division, DOSM via OpenDOSM (`cpi_2d_state`), used only to check our numbers
- CPI food weights, DOSM CPI Malaysia 2024 annual publication (Table 9), used to weight categories

PricePulse reports **observed price changes** in PriceCatcher. These are not official inflation statistics;
DOSM's CPI is shown separately and labelled as such.

## Findings so far
- Observed grocery prices in Malaysia are 9.7% higher than in January 2022, mostly from 2022.
- Aug to Oct 2026 vs a year earlier: +1.2% nationally; Kedah fastest (+2.3%); prices fell in Sabah (-1.2%) and Labuan.
- States differ by only about 1.5 percentage points; beef, vegetables, onions/chilli and chicken drive the current rise.

- Vegetables drive 2026: tomatoes are up 63% on a year earlier and lead the risers in 13 of 16 states.
- A 20-item staples basket costs RM212.50 (Aug to Oct 2026); RM20.84 more in Putrajaya than in Kedah.

Details: [FINDINGS_01](docs/FINDINGS_01.md) (index), [FINDINGS_02](docs/FINDINGS_02.md) (drivers), [FINDINGS_03](docs/FINDINGS_03.md) (basket).
