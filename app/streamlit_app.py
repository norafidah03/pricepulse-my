"""PricePulse MY: Malaysia Food Price Intelligence (Streamlit dashboard).

Run locally:   streamlit run app/streamlit_app.py
Data:          app/data/*, built by `python -m src.pricepulse.build` (committed to git, so the deployed
               app on Streamlit Community Cloud works without downloading anything).
Styling:       .streamlit/config.toml (theme) + app/style.css (layout details).

This file only presents results. All calculations live in src/pricepulse/ and in the build step.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from calculator import compare, every_state  # app/calculator.py

APP = Path(__file__).parent
DATA = APP / "data"

# Paste the repo link here to show a "Code on GitHub" link in the footer.
GITHUB_URL = "https://github.com/norafidah03/pricepulse-my"

# Colours from the design brief. Rises are amber, falls are green; every number also carries a sign
# and an arrow, so the meaning never depends on colour alone (amber/green is close for some
# colour-blind readers: checked with a palette validator).
TEAL, NAVY, SLATE = "#0F6B6B", "#14294B", "#5A6B7B"
AMBER, GREEN, NEUTRAL, GRID = "#C77700", "#2E7D4F", "#E3E8EB", "#EDF1F3"
DIVERGING = [[0.0, GREEN], [0.5, "#F1F3F2"], [1.0, AMBER]]
FONT = "Source Sans Pro, system-ui, sans-serif"

st.set_page_config(page_title="PricePulse MY: Malaysia Food Price Intelligence", page_icon="🛒", layout="wide")
st.html(f"<style>{(APP / 'style.css').read_text()}</style>")


# ---------------------------------------------------------------- data

@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet")


@st.cache_data
def meta() -> dict:
    return json.loads((DATA / "meta.json").read_text())


@st.cache_data
def geojson() -> dict:
    return json.loads((DATA / "states.geojson").read_text())


M = meta()
LAST = pd.Timestamp(M["last_complete_month"] + "-01")
WINDOW, YEAR_AGO = M["window_label"], M["year_ago_label"]
LATEST = pd.Timestamp(M["latest_observation"])
LATEST_LONG = f"{LATEST.day} {LATEST:%B %Y}"  # no zero padding, works on every OS
LATEST_SHORT = f"{LATEST.day} {LATEST:%b %Y}"


def short_state(s: str) -> str:
    return s.replace("W.P. ", "")


# ---------------------------------------------------------------- formatting helpers

def pct(x: float, digits: int = 1) -> str:
    arrow = "▲" if x > 0.05 else "▼" if x < -0.05 else "■"
    return f"{arrow} {x:+.{digits}f}%"


def rm(x: float) -> str:
    return f"RM{x:,.2f}"


def tone(x: float) -> str:
    return "up" if x > 0.05 else "down" if x < -0.05 else "flat"


def html(s: str) -> None:
    st.html(s)


def tile(label: str, value: str, note: str = "", kind: str = "") -> str:
    return (f'<div class="pp-tile {kind}"><div class="pp-tile-label">{label}</div>'
            f'<div class="pp-tile-value">{value}</div><div class="pp-tile-note">{note}</div></div>')


def tiles(items: list[str]) -> None:
    html(f'<div class="pp-tiles">{"".join(items)}</div>')


def section(title: str, sub: str = "") -> None:
    html(f'<h2 class="pp-h2">{title}</h2>' + (f'<p class="pp-sub">{sub}</p>' if sub else ""))


def note(text: str) -> None:
    html(f'<p class="pp-note">{text}</p>')


def style(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=8, r=8, t=8, b=8),
                      paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", hovermode="closest",
                      font=dict(family=FONT, color=NAVY, size=13), legend_title_text="",
                      legend=dict(orientation="h", yanchor="top", y=-0.15, x=0, xanchor="left"),
                      hoverlabel=dict(font_family=FONT, bgcolor="#FFFFFF"))
    fig.update_xaxes(showgrid=False, linecolor=NEUTRAL, tickfont_color=SLATE, title_font_color=SLATE)
    fig.update_yaxes(gridcolor=GRID, linecolor=NEUTRAL, tickfont_color=SLATE, title_font_color=SLATE, zeroline=False)
    return fig


def chart(fig: go.Figure, title: str = "", height: int = 380) -> None:
    if title:
        html(f'<h3 class="pp-chart-title">{title}</h3>')
    st.plotly_chart(style(fig, height), width="stretch",
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["select2d", "lasso2d"]})


def signed_bars(df: pd.DataFrame, value: str, label: str, fmt=lambda v: f"{v:+.1f}%", height: int | None = None) -> go.Figure:
    """Horizontal bars, amber for rises and green for falls.

    Each value is written into its axis label ("Kedah  +2.3%") rather than at the bar end, so labels
    never collide with bars or get clipped on narrow phone screens.
    """
    df = df.sort_values(value)
    colors = [AMBER if v > 0 else GREEN for v in df[value]]
    ticks = [f"{l}  <b>{fmt(v)}</b>" for l, v in zip(df[label], df[value])]
    fig = go.Figure(go.Bar(x=df[value], y=ticks, orientation="h", marker_color=colors, marker_line_width=0,
                           customdata=[fmt(v) for v in df[value]],
                           hovertemplate="%{y}<extra></extra>"))
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=True, zerolinecolor=SLATE, zerolinewidth=1)
    fig.update_yaxes(showgrid=False, showline=False, ticksuffix="  ", automargin=True)
    fig.update_layout(height=height or max(260, 26 * len(df) + 40), bargap=0.35)
    return fig


def footer() -> None:
    link = f' · <a href="{GITHUB_URL}" target="_blank">Code on GitHub</a>' if GITHUB_URL else ""
    html(f'<div class="pp-footer">Source: KPDN PriceCatcher via <a href="https://data.gov.my" target="_blank">data.gov.my</a>; '
         f'official CPI from DOSM (OpenDOSM). Latest observation {LATEST_SHORT}. '
         f'PricePulse shows observed price changes, not official inflation statistics.{link}</div>')


# ---------------------------------------------------------------- shared numbers

state_idx = load("state_index")
now_states = state_idx[state_idx["month"] == LAST].set_index("state")
NAT = now_states.loc["Malaysia"]
ranked = now_states.drop(index="Malaysia").sort_values("yoy3m_pct", ascending=False)
movers = load("movers")
nat_up = movers[(movers["state"] == "Malaysia") & (movers["direction"] == "up")].sort_values("yoy3m_pct", ascending=False)
basket_cost = load("basket_cost")
calc = load("calculator_prices")
STATES = sorted(s for s in calc["state"].unique() if s != "Malaysia")


# ---------------------------------------------------------------- pages

def page_overview() -> None:
    html(f"""
    <div class="pp-hero">
      <div class="pp-eyebrow">Malaysia Food Price Intelligence</div>
      <h1>Know your prices. Understand your cost of living.</h1>
      <p>PricePulse MY tracks the prices of about 290 everyday groceries in over 2,000 shops across every state,
      using KPDN's PriceCatcher data. See what is getting more expensive, where, and what your groceries
      would cost in another state.</p>
      <div class="pp-stamp">Latest data: {LATEST_LONG} · Figures compare {WINDOW} with {YEAR_AGO}</div>
    </div>""")

    b = basket_cost.set_index(["window_end", "state"])["cost"]
    b_now, b_ago = b[(LAST, "Malaysia")], b[(LAST - pd.DateOffset(months=12), "Malaysia")]
    top_state, top_item = ranked.index[0], nat_up.iloc[0]
    html(f'<p class="pp-lead">Grocery prices observed in Malaysia are <b class="{tone(NAT.yoy3m_pct)}">'
         f'{pct(NAT.yoy3m_pct)}</b> on a year ago. They are rising fastest in <b>{short_state(top_state)}</b>, '
         f'and <b>{top_item["name"].split(" (")[0].lower()}</b> prices have jumped the most.</p>')
    tiles([
        tile("Grocery prices, Malaysia", pct(NAT.yoy3m_pct), f"{WINDOW} vs a year earlier", tone(NAT.yoy3m_pct)),
        tile("Fastest-rising state", short_state(top_state), f"{pct(ranked.iloc[0].yoy3m_pct)} on a year ago", "up"),
        tile("Fastest-rising item", top_item["name"].split(" (")[0], f"{pct(top_item.yoy3m_pct, 0)} on a year ago", "up"),
        tile("20-item staples basket", rm(b_now), f"{pct(100 * (b_now / b_ago - 1))} on a year ago", tone(b_now - b_ago)),
    ])

    nat = state_idx[state_idx["state"] == "Malaysia"]
    fig = go.Figure(go.Scatter(x=nat["month"], y=nat["index"], mode="lines", line=dict(color=TEAL, width=2.5),
                               hovertemplate="%{x|%b %Y}: %{y:.1f}<extra></extra>"))
    fig.add_hline(y=100, line_color=NEUTRAL, line_width=1)
    fig.add_annotation(x=nat["month"].iloc[-1], y=nat["index"].iloc[-1], text=f"{nat['index'].iloc[-1]:.1f}",
                       showarrow=False, xanchor="left", xshift=6, font=dict(color=NAVY, size=13))
    fig.update_yaxes(title="Index (Jan 2022 = 100)")
    chart(fig, f"Grocery prices are {nat['index'].iloc[-1] - 100:.1f}% higher than in January 2022, mostly from 2022", 340)
    note("PricePulse food price index for Malaysia. 100 = prices in January 2022; 110 means 10% higher. "
         "It follows the same shops and items month to month, so shops joining or leaving don't move it.")

    section("Explore")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.page_link(PAGES["basket"], label="**My Grocery Basket**: compare two states", icon=":material/shopping_basket:")
    with c2:
        st.page_link(PAGES["states"], label="**Compare by State**: where prices rise fastest", icon="🗺️")
    with c3:
        st.page_link(PAGES["trends"], label="**Price Trends**: 230 items since 2022", icon="📈")
    footer()


def page_trends() -> None:
    section("Price Trends", "How the typical shop price of an item has moved since January 2022.")
    trends = load("item_trends")
    names = calc.drop_duplicates("item_code").set_index("item_code")
    options = names[names.index > 0].sort_values("name")
    default = int(options.index[options["name"].str.startswith("Chicken, whole cleaned")][0])
    c1, c2 = st.columns([3, 2])
    with c1:
        code = st.selectbox("Item", options.index, index=list(options.index).index(default),
                            format_func=lambda c: options.loc[c, "name"], help="Type to search, e.g. eggs, telur, sardin")
    with c2:
        picked = st.multiselect("Compare states", STATES, placeholder="Malaysia only", max_selections=4)
    t = trends[(trends["item_code"] == code) & trends["state"].isin(["Malaysia"] + picked)]
    t = t[t["shops"] >= 2]
    nat_t = t[t["state"] == "Malaysia"].set_index("month")["price"]
    if nat_t.empty:
        st.info("Not enough shops price this item yet.")
        return
    last_p = nat_t.iloc[-1]
    ago = nat_t.get(nat_t.index[-1] - pd.DateOffset(months=12))
    first = nat_t.iloc[0]
    item_name = options.loc[code, "name"]
    tiles([
        tile("Typical price now", rm(last_p), f"Malaysia, {nat_t.index[-1]:%b %Y}"),
        tile("Change on a year ago", pct(100 * (last_p / ago - 1)) if ago else "n/a", "same month last year",
             tone(100 * (last_p / ago - 1)) if ago else ""),
        tile(f"Change since {nat_t.index[0]:%b %Y}", pct(100 * (last_p / first - 1)), f"from {rm(first)}",
             tone(100 * (last_p / first - 1))),
    ])
    palette = [TEAL, "#7A4FB3", "#B5487A", "#3C6FB0", "#8C6D1F"]  # Malaysia first, then states in pick order
    fig = go.Figure()
    for i, s in enumerate(["Malaysia"] + picked):
        d = t[t["state"] == s]
        fig.add_trace(go.Scatter(x=d["month"], y=d["price"], name=short_state(s), mode="lines",
                                 line=dict(color=palette[i], width=2.5 if s == "Malaysia" else 2),
                                 hovertemplate=f"{short_state(s)} %{{x|%b %Y}}: RM%{{y:.2f}}<extra></extra>"))
    fig.update_yaxes(title="RM", tickprefix="RM", rangemode="tozero")
    chart(fig, f"{item_name}: typical shop price", 380)
    note("Median of shop prices in the month (half of shops charge less, half more). Months with fewer than "
         "2 shops pricing the item in a state are left out. A 10-day gap (30 Sep to 9 Oct 2026) means October "
         "2026 uses 10 to 31 October only.")

    section("By category", "PricePulse index for each food category, Malaysia (January 2022 = 100).")
    cat = load("category_index")
    cat = cat[cat["state"] == "Malaysia"]
    last_cat = cat[cat["month"] == LAST].sort_values("index", ascending=False)
    chosen = st.multiselect("Categories", last_cat["category"], default=list(last_cat["category"].iloc[:3]))
    fig = go.Figure()
    for i, c in enumerate(chosen):
        d = cat[cat["category"] == c]
        fig.add_trace(go.Scatter(x=d["month"], y=d["index"], name=c, mode="lines",
                                 line=dict(color=palette[i % len(palette)], width=2),
                                 hovertemplate=f"{c} %{{x|%b %Y}}: %{{y:.1f}}<extra></extra>"))
    fig.add_hline(y=100, line_color=NEUTRAL, line_width=1)
    fig.update_yaxes(title="Index (Jan 2022 = 100)")
    chart(fig, "", 340)
    footer()


def page_states() -> None:
    section("Compare by State",
            f"How grocery prices changed in each state: {WINDOW} compared with {YEAR_AGO}.")
    html('<div class="pp-callout">These are changes in <b>grocery shelf prices</b> in PriceCatcher shops, not '
         "official state inflation rates. DOSM's state figures also include eating out, so they can rank states "
         "differently. See <i>About the data</i>.</div>")
    df = ranked.reset_index()[["state", "yoy3m_pct", "index"]]
    df["label"] = df["state"].map(short_state)
    lim = max(abs(df["yoy3m_pct"]).max(), 0.5)

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        # A blank base map ("white-bg") needs no external map tiles; the state shapes come from app/data.
        fig = px.choropleth_map(df, geojson=geojson(), locations="state", featureidkey="properties.state",
                                color="yoy3m_pct", color_continuous_scale=DIVERGING, range_color=(-lim, lim),
                                hover_name="label", custom_data=["yoy3m_pct"], map_style="white-bg",
                                center={"lat": 4.0, "lon": 109.4}, zoom=4.35)
        fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=0.8,
                          hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]:+.1f}% on a year ago<extra></extra>")
        fig.update_layout(coloraxis_colorbar=dict(title="", ticksuffix="%", orientation="h", y=-0.02, x=0.5,
                                                  len=0.6, thickness=10))
        chart(fig, "Change in grocery prices on a year ago", 400)
    with c2:
        chart(signed_bars(df, "yoy3m_pct", "label", height=470), "Ranked, fastest rising first")

    section("What is driving it")
    pick = st.selectbox("State", ["Malaysia"] + list(ranked.index), format_func=short_state)
    contrib = load("contributions")
    c = contrib[contrib["state"] == pick].copy()
    total = now_states.loc[pick, "yoy_pct"]
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        chart(signed_bars(c, "pp", "category", fmt=lambda v: f"{v:+.2f}"),
              f"{short_state(pick)}: what added to the {pct(total)} change, in percentage points")
        note(f"Each bar is a category's share of the year-on-year change to {LAST:%b %Y}. Bars add up to the total. "
             "Categories count by how much households spend on them (DOSM CPI weights), so fish counts most.")
    with c2:
        mv = movers[(movers["state"] == pick)].copy()
        mv["item"] = mv["name"].str.split(" \\(").str[0]
        up = mv[mv["direction"] == "up"].nlargest(5, "yoy3m_pct")
        down = mv[mv["direction"] == "down"].nsmallest(5, "yoy3m_pct")
        chart(signed_bars(pd.concat([up, down]), "yoy3m_pct", "item", fmt=lambda v: f"{v:+.0f}%"),
              "Items rising and falling fastest")
        note("Only items priced by enough of the same shops in each of the last 3 months.")

    cov = load("coverage").set_index("state")
    if pick != "Malaysia" and pick in cov.index and cov.loc[pick, "imputed_share"] > 0.25:
        st.info(f"{short_state(pick)} has fewer PriceCatcher shops ({int(cov.loc[pick, 'shops'])}), so for "
                f"{cov.loc[pick, 'imputed_share']:.0%} of items its index uses the national change. Treat its ranking with care.")

    section("Districts", f"Change in grocery prices on a year ago, {WINDOW}, for districts with enough shops.")
    dr = load("district_ranking")
    states_with = [s for s in ranked.index if dr[(dr["state"] == s) & dr["ranked"]].shape[0] > 0]
    default = states_with.index(pick) if pick in states_with else 0
    dpick = st.selectbox("State", states_with, index=default, format_func=short_state, key="district_state")
    d = dr[(dr["state"] == dpick) & dr["ranked"]]
    left = dr[(dr["state"] == dpick) & ~dr["ranked"]]
    chart(signed_bars(d, "yoy3m_pct", "district"), f"{short_state(dpick)}: districts, fastest rising first")
    msg = (f"Districts need at least 10 PriceCatcher shops, and enough matching shops for most items, to be shown. "
           f"Where a district has fewer than 2 matching shops for an item, it uses the state's change for that item.")
    if len(left):
        msg += f" Not shown for {short_state(dpick)}: {', '.join(sorted(left['district']))}."
    note(msg)
    footer()


def page_basket() -> None:
    section("My Grocery Basket", "Pick your groceries and quantities, choose two states, and compare what they would cost.")
    items = calc[calc["state"] == "Malaysia"].set_index("item_code")
    default_codes = list(items.index[items["in_default_basket"]])

    c1, c2 = st.columns(2)
    with c1:
        state_a = st.selectbox("Your state", STATES, index=STATES.index("Selangor"), format_func=short_state)
    with c2:
        others = [s for s in STATES if s != state_a]
        state_b = st.selectbox("Compare with", others, index=others.index("Kedah") if "Kedah" in others else 0,
                               format_func=short_state)

    if "basket" not in st.session_state:
        st.session_state.basket = pd.DataFrame({"item_code": default_codes, "qty": 1})
    with st.expander("➕ Add more items", expanded=False):
        choices = items[~items.index.isin(st.session_state.basket["item_code"])].sort_values("name")
        add = st.multiselect("Search 230 items", choices.index, format_func=lambda c: choices.loc[c, "name"],
                             placeholder="e.g. chicken wings, Milo, kangkung")
        cc1, cc2 = st.columns(2)
        if cc1.button("Add to basket", disabled=not add, type="primary"):
            st.session_state.basket = pd.concat([st.session_state.basket, pd.DataFrame({"item_code": add, "qty": 1})],
                                                ignore_index=True)
            st.rerun()
        if cc2.button("Reset to the 20 staples"):
            st.session_state.basket = pd.DataFrame({"item_code": default_codes, "qty": 1})
            st.rerun()

    b = st.session_state.basket.copy()
    b["Item"] = b["item_code"].map(items["name"])
    b["Category"] = b["item_code"].map(items["category"])
    edited = st.data_editor(
        b[["qty", "Item", "Category"]].rename(columns={"qty": "Qty"}), hide_index=True, width="stretch",
        num_rows="fixed", disabled=["Item", "Category"], key="basket_editor", height=35 * (len(b) + 1) + 3,
        column_config={"Qty": st.column_config.NumberColumn(min_value=0, max_value=50, step=1, width="small",
                                                                 help="Set to 0 to leave an item out")},
    )
    b["qty"] = edited["Qty"].fillna(0).values
    b = b[b["qty"] > 0]
    if b.empty:
        st.info("Set a quantity above 0 for at least one item.")
        return

    prices = calc.set_index(["state", "item_code"])
    both, missing, tot = compare(b, prices, state_a, state_b)
    if both.empty:
        st.warning("None of these items has enough shops in both states to compare.")
        return
    ta, tb, diff, ago_a = tot["a"], tot["b"], tot["diff"], tot["a_year_ago"]
    a_s, b_s = short_state(state_a), short_state(state_b)
    cheaper = a_s if ta < tb else b_s

    html(f'<p class="pp-lead">Your basket of <b>{int(both["qty"].sum())} items</b> costs about <b>{rm(ta)}</b> in {a_s} '
         f'and <b>{rm(tb)}</b> in {b_s}. That is <b>{rm(abs(diff))}</b> ({abs(100 * diff / ta):.1f}%) '
         f'{"more" if diff > 0 else "less"} in {b_s}.</p>' if abs(diff) >= 0.005 else
         f'<p class="pp-lead">Your basket costs about <b>{rm(ta)}</b> in both {a_s} and {b_s}.</p>')
    tiles([
        tile(a_s, rm(ta), f"{pct(100 * (ta / ago_a - 1))} vs {YEAR_AGO}" if ago_a else "", ""),
        tile(b_s, rm(tb), f"{'+' if diff >= 0 else '−'}{rm(abs(diff))} vs {a_s}", "up" if diff > 0 else "down"),
        tile("Cheaper here", cheaper, f"saves {rm(abs(diff))} per basket", ""),
    ])
    if len(missing):
        st.warning(f"Left out of both totals so the comparison stays fair: {', '.join(missing['Item'])}. "
                   "Not enough shops price it in one of the states.")

    detail = both.copy()
    detail["label"] = detail["Item"].str.split(" \\(").str[0]
    biggest = detail.reindex(detail["gap"].abs().sort_values(ascending=False).index).head(10)
    chart(signed_bars(biggest, "gap", "label", fmt=lambda v: f"{'+' if v >= 0 else '−'}RM{abs(v):.2f}"),
          f"Where {b_s} differs most from {a_s} (RM, for your quantities)")

    table = detail[["Item", "qty", "A", "B", "cost_a", "cost_b", "gap"]].rename(columns={
        "qty": "Qty", "A": f"Unit price {a_s}", "B": f"Unit price {b_s}", "cost_a": f"Total {a_s}",
        "cost_b": f"Total {b_s}", "gap": "Difference"})
    with st.expander("See every item"):
        st.dataframe(table, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="RM%.2f") for c in table.columns[2:]})

    # The same basket in every state
    every = every_state(both, prices, STATES)
    all_states = [{"state": short_state(r.state), "cost": r.cost} for r in every.itertuples()]
    if all_states:
        df = pd.DataFrame(all_states).sort_values("cost")
        cols = [TEAL if s in (a_s, b_s) else "#A9C4C4" for s in df["state"]]
        ticks = [f"{s}  <b>{rm(v)}</b>" for s, v in zip(df["state"], df["cost"])]
        fig = go.Figure(go.Bar(x=df["cost"], y=ticks, orientation="h", marker_color=cols, marker_line_width=0,
                               hovertemplate="%{y}<extra></extra>"))
        fig.update_xaxes(showticklabels=False, range=[0, df["cost"].max() * 1.02])
        fig.update_yaxes(showline=False, automargin=True)
        fig.update_layout(height=26 * len(df) + 40, bargap=0.35)
        chart(fig, "Your basket in every state")
        if len(df) < len(STATES):
            note(f"{len(STATES) - len(df)} state(s) left out because an item in your basket has too few shops there.")
    note(f"Prices are the median shop price in each state over {WINDOW}, from shops reporting to KPDN PriceCatcher. "
         "Your local shop may charge more or less. Rice (*) is any brand of 10 kg imported white rice, because no "
         "single brand is sold in every state.")
    footer()


def page_insights() -> None:
    section("Insights", "What the data shows, in plain language.")
    trends = load("item_trends")
    cat = load("category_index")

    def card(title: str, body: str) -> None:
        html(f'<div class="pp-insight"><h3>{title}</h3><p>{body}</p></div>')

    # 1. Vegetables
    tom = nat_up.iloc[0]
    card(f"1. Vegetables drive 2026: {tom['name'].split(' (')[0].lower()} up {tom['yoy3m_pct']:.0f}%",
         f"Tomatoes, kailan and mustard greens (sawi) cost 30 to 60% more than a year ago. Tomato is the fastest-rising "
         f"item in most states. Fresh vegetables swing with weather and supply, so these jumps can reverse quickly.")
    t = trends[(trends["item_code"] == 114) & (trends["state"] == "Malaysia")]
    fig = go.Figure(go.Scatter(x=t["month"], y=t["price"], mode="lines", line=dict(color=AMBER, width=2),
                               hovertemplate="%{x|%b %Y}: RM%{y:.2f}<extra></extra>"))
    fig.update_yaxes(tickprefix="RM", rangemode="tozero")
    chart(fig, "Tomato, typical price per kg, Malaysia", 260)

    # 2. Eggs
    e = trends[(trends["item_code"] == 1109) & (trends["state"] == "Malaysia")]
    e0, e1 = e["price"].iloc[0], e["price"].iloc[-1]
    card("2. Eggs have risen most since 2022, and swing more since the subsidy ended",
         f"A tray of 30 grade A eggs went from {rm(e0)} in January 2022 to {rm(e1)} in {e['month'].iloc[-1]:%B %Y}. "
         "After the egg subsidy ended in August 2025, prices started moving up and down "
         "by 10% or more from month to month.")
    fig = go.Figure(go.Scatter(x=e["month"], y=e["price"], mode="lines", line=dict(color=TEAL, width=2),
                               hovertemplate="%{x|%b %Y}: RM%{y:.2f}<extra></extra>"))
    fig.add_vline(x=pd.Timestamp("2025-08-01").timestamp() * 1000, line_dash="dot", line_color=SLATE)
    fig.add_annotation(x=pd.Timestamp("2025-08-01"), y=e["price"].max(), text="Subsidy ends", showarrow=False,
                       xanchor="right", xshift=-4, font=dict(color=SLATE, size=12))
    fig.update_yaxes(tickprefix="RM")
    chart(fig, "Eggs, grade A, tray of 30, typical price, Malaysia", 260)

    # 3. Basket by state
    bc = basket_cost.set_index(["window_end", "state"])["cost"]
    now_b = bc.xs(LAST, level=0).drop("Malaysia")
    ago_b = bc.xs(LAST - pd.DateOffset(months=12), level=0).drop("Malaysia")
    chg = (100 * (now_b / ago_b - 1)).rename("chg").reset_index()
    cheap, dear = now_b.idxmin(), now_b.idxmax()
    card("3. The north is cheapest, but catching up",
         f"The 20 staples cost {rm(now_b[cheap])} in {short_state(cheap)} and {rm(now_b[dear])} in "
         f"{short_state(dear)}, a gap of {rm(now_b[dear] - now_b[cheap])}. But the cheapest states, Perlis, Kedah "
         "and Perak, saw the biggest rises in the past year.")
    chg["label"] = chg["state"].map(short_state)
    chart(signed_bars(chg, "chg", "label"), f"Staples basket, change on a year ago ({WINDOW})")

    # 4. Fish
    card("4. Fish explains most of the gap between states",
         "Fish and seafood carry the biggest weight in household food spending. Cheaper fish pulled Sabah's grocery "
         "prices below last year's, while dearer fish pushed Kedah to the top of the ranking.")

    # 5. The long view
    nat = state_idx[state_idx["state"] == "Malaysia"].set_index("month")
    y23 = nat.loc[pd.Timestamp("2023-01-01"), "yoy_pct"]
    card("5. Most of the rise since 2022 happened in 2022",
         f"Observed grocery prices rose {y23:.1f}% in the year to January 2023. Since then, yearly changes have mostly "
         f"stayed between 0% and 3%. Overall, groceries are {nat['index'].iloc[-1] - 100:.1f}% dearer than in January 2022.")

    policy_events()
    where_you_shop()
    footer()


def event_verdict(e: pd.Series, m: pd.Series) -> str:
    """One plain sentence on the 3-month gap and how unusual it is."""
    seen = (f"none of the other {int(e['n_placebo'])}" if e["p_value"] == 0 else f"{e['p_value']:.0%} of other")
    ctrl = m["control_label"][0].lower() + m["control_label"][1:]
    moved = (f"{m['treated_label']}: {e['treated_pct']:+.1f}% in the 3 months from the change, against "
             f"{e['control_pct']:+.1f}% for {ctrl}.")
    if e["p_value"] < 0.1:
        return f"<b>A clear move.</b> {moved} A gap this large showed up in {seen} 3-month spells."
    return f"<b>No clear effect.</b> {moved} Gaps this large are common: they showed up in {seen} 3-month spells."


def policy_events() -> None:
    section("Did policy changes move prices?",
            "Four changes, each compared with a group of prices it should not have affected. "
            "Both lines start at 100 the month before the change.")
    paths, effects, metas = load("events_paths"), load("events_effects"), load("events_meta").set_index("id")
    ids = list(metas.index)
    for row in range(0, len(ids), 2):
        cols = st.columns(2, gap="large")
        for col, ev in zip(cols, ids[row:row + 2]):
            m = metas.loc[ev]
            p = paths[paths["event"] == ev]
            e = effects[(effects["event"] == ev) & (effects["k"] == 2)].iloc[0]
            fig = go.Figure()
            for grp, name, color, dash, width in [("control", m["control_label"], SLATE, "dot", 2),
                                                   ("treated", m["treated_label"], TEAL, "solid", 2.5)]:
                g = p[p["group"] == grp]
                fig.add_trace(go.Scatter(x=g["month"], y=g["level"], name=name, mode="lines",
                                         line=dict(color=color, width=width, dash=dash),
                                         hovertemplate=f"{name}<br>%{{x|%b %Y}}: %{{y:.1f}}<extra></extra>"))
            t0 = pd.Timestamp(m["date"])
            fig.add_vline(x=t0.timestamp() * 1000, line_dash="dot", line_color=SLATE)
            if isinstance(m.get("also"), str):
                fig.add_vline(x=pd.Timestamp(m["also"]).timestamp() * 1000, line_dash="dot", line_color=NEUTRAL)
            fig.add_hline(y=100, line_color=NEUTRAL, line_width=1)
            fig.update_layout(legend=dict(y=-0.2))
            with col:
                chart(fig, f"{m['title']} ({m['when']})", 300)
                note(event_verdict(e, m) + f' <a href="{m["source"]}" target="_blank">About the change</a>.')
    note("How to read this: the change in the first group minus the change in the comparison group, over the 3 months "
         "from the change, is set against the same gap for every other 3-month spell since 2022. Eggs use trays of 30, "
         "the sizes most shops price. Diesel compares the Peninsula, where the subsidy was cut, with Sabah, Sarawak and "
         "Labuan, where it was not.")


def where_you_shop() -> None:
    section("Does it matter where you shop?",
            f"The same items in the same state, {WINDOW}, compared with the supermarket price.")
    lv = load("outlet_levels")
    oi = load("outlet_index")
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        cats = ["All groceries"] + sorted(c for c in lv["category"].unique() if c != "All groceries")
        pick = st.selectbox("Category", cats, key="outlet_cat")
        d = lv[lv["category"] == pick]
        chart(signed_bars(d, "gap_pct", "outlet", height=240), f"{pick}: price compared with supermarkets", 240)
        note("Amber means dearer than a supermarket, green cheaper. Typical (median) prices, matched on item and state.")
    with c2:
        fig = go.Figure()
        highlight = {"Wet market": TEAL, "Hypermarket": NAVY}
        for outlet, g in oi.groupby("outlet"):
            color = highlight.get(outlet, "#B8C2CA")
            fig.add_trace(go.Scatter(x=g["month"], y=g["index"], name=outlet, mode="lines",
                                     line=dict(color=color, width=2.5 if outlet in highlight else 1.5),
                                     hovertemplate=f"{outlet} %{{x|%b %Y}}: %{{y:.1f}}<extra></extra>"))
        fig.update_layout(legend=dict(y=-0.15))
        chart(fig, "Price index by type of shop (Jan 2022 = 100)", 340)
        now = oi[oi["month"] == oi["month"].max()].set_index("outlet")["index"]
        note(f"Built only from items every type of shop sells, so the lists match. Since January 2022, prices rose "
             f"{now.max() - 100:.1f}% at {now.idxmax().lower()}s and {now.min() - 100:.1f}% at {now.idxmin().lower()}s.")


def page_about() -> None:
    section("About the data", "Where the numbers come from, what they cover, and what they don't.")
    cov = load("coverage")
    html(f"""
    <div class="pp-about">
      <h3>Source</h3>
      <p>Prices come from <b>PriceCatcher</b>, run by the Ministry of Domestic Trade and Cost of Living (KPDN) and
      published as open data on <a href="https://data.gov.my" target="_blank">data.gov.my</a>. Enforcement officers
      record shelf prices of about 300 grocery items in over 2,000 shops: wet markets, supermarkets, mini markets
      and sundry shops. The original data is unchanged; PricePulse only summarises it.</p>
      <p>Latest observation: <b>{LATEST_LONG}</b>. Monthly figures run to <b>{LAST:%B %Y}</b>, the last complete month.</p>

      <h3>Observed prices, not official inflation</h3>
      <p>PricePulse shows <b>observed price changes</b> in PriceCatcher shops. The official measure of inflation is
      the Consumer Price Index (CPI) from the Department of Statistics Malaysia (DOSM), which covers more items and
      shops and includes eating out. The two are compared below.</p>

      <h3>How it works</h3>
      <ul>
        <li><b>Typical price</b>: the median of shop prices, so a few very cheap or very dear shops don't skew it.</li>
        <li><b>Price index</b>: each shop's price for an item is compared with the same shop's price a month earlier,
        so shops joining or leaving PriceCatcher don't move it. Categories are combined using DOSM's CPI weights
        (how much households spend on each).</li>
        <li><b>Change on a year ago</b>: the last 3 months compared with the same 3 months a year earlier. This smooths
        out monthly noise and is fair to seasonal items.</li>
        <li><b>Prices that look like typing errors</b> (over 3 times or under a third of the national typical price)
        are left out. That is 0.06% of prices.</li>
      </ul>

      <h3>Limitations</h3>
      <ul>
        <li>No data was published from 30 September to 9 October 2026.</li>
        <li>Small states (Labuan, Putrajaya, Perlis, Melaka) have fewer shops, so their figures are less precise.
        Where a state has fewer than 2 matching shops for an item, it uses the national change for that item.</li>
        <li>Restaurant and cooked food prices were only published from January to May 2022, so eating out isn't covered.</li>
        <li>Rice brands differ between states, so the basket uses the typical price of any 10 kg imported white rice.</li>
      </ul>
    </div>""")

    section("Coverage by state", f"Shops reporting grocery prices in {LAST:%B %Y}.")
    c = cov.assign(State=cov["state"].map(short_state), imputed_share=(100 * cov["imputed_share"]).round()
                   ).sort_values("shops", ascending=False)
    st.dataframe(c[["State", "shops", "items", "imputed_share"]].rename(columns={
        "shops": "Shops", "items": "Items tracked", "imputed_share": "Items using the national change"}),
        hide_index=True, width="stretch", height=35 * (len(c) + 1) + 3,
        column_config={"Items using the national change": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100)})

    section("How PricePulse compares with the official CPI")
    v = load("validate_national").dropna()
    s = load("validate_summary").iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v["month"], y=v["dosm_yoy"], name="DOSM CPI, food at home and drinks (official)",
                             mode="lines", line=dict(color=SLATE, width=2, dash="dot"),
                             hovertemplate="DOSM %{x|%b %Y}: %{y:+.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=v["month"], y=v["ours_yoy"], name="PricePulse (observed prices)", mode="lines",
                             line=dict(color=TEAL, width=2.5), hovertemplate="PricePulse %{x|%b %Y}: %{y:+.1f}%<extra></extra>"))
    fig.add_hline(y=0, line_color=NEUTRAL, line_width=1)
    fig.update_yaxes(ticksuffix="%", title="Change on a year ago")
    chart(fig, "Nationally, the two move together", 340)
    note(f"Over {int(s['months'])} months the two series correlate at {s['corr']:.2f} and differ by "
         f"{s['mean_abs_diff_pp']:.1f} percentage points on average. PricePulse runs slightly higher, mostly because "
         "PriceCatcher shops picked up the egg price jump in late 2025 faster. DOSM data to "
         f"{pd.Timestamp(M['dosm_last_month'] + '-01'):%B %Y}.")
    html('<div class="pp-callout">By state, the two agree on trends over time but not on which state is rising '
         "fastest. DOSM publishes only total food by state, and almost half of it is eating out, which PriceCatcher "
         "no longer covers.</div>")
    footer()


PAGES = {
    "overview": st.Page(page_overview, title="Overview", icon="🏠", default=True),
    "trends": st.Page(page_trends, title="Price Trends", icon="📈", url_path="trends"),
    "states": st.Page(page_states, title="Compare by State", icon="🗺️", url_path="states"),
    "basket": st.Page(page_basket, title="Grocery Basket", icon=":material/shopping_basket:", url_path="basket"),
    "insights": st.Page(page_insights, title="Insights", icon="💡", url_path="insights"),
    "about": st.Page(page_about, title="About the data", icon="ℹ️", url_path="about"),
}
page = st.navigation(list(PAGES.values()), position="top")
if page.title != "Overview":  # the Overview hero already carries the name
    html('<div class="pp-brand"><span class="pp-logo">PricePulse <b>MY</b></span>'
         '<span class="pp-brand-sub">Malaysia Food Price Intelligence</span></div>')
page.run()
