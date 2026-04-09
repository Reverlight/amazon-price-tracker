import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- config ---
CSV_PATH      = "prices_dummy.csv"       # point to your real file
REFRESH_SEC   = 300                # 5 minutes

st.set_page_config(
    page_title="Amazon Price Tracker",
    page_icon="📦",
    layout="wide",
)

# --- auto refresh ---
st.markdown(
    f"""
    <script>
        setTimeout(function() {{ window.location.reload(); }}, {REFRESH_SEC * 1000});
    </script>
    """,
    unsafe_allow_html=True,
)

# --- custom css ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.5rem;
    }
    .metric-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { font-size: 28px; font-weight: 700; color: #0f172a; line-height: 1.2; }
    .metric-sub   { font-size: 13px; color: #64748b; margin-top: 2px; }
    .up   { color: #16a34a; font-weight: 600; }
    .down { color: #dc2626; font-weight: 600; }
    .neutral { color: #64748b; font-weight: 600; }
    div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
    .stSelectbox label { font-weight: 600; color: #374151; }
    h1 { color: #0f172a; }
    h3 { color: #374151; }
</style>
""", unsafe_allow_html=True)


# --- data loading ---
@st.cache_data(ttl=REFRESH_SEC)
def load_data(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, parse_dates=["timestamp"])
        df = df.sort_values("timestamp")
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["asin", "url", "price", "timestamp"])


def get_summary(df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.utcnow()
    rows = []

    for asin, group in df.groupby("asin"):
        group = group.sort_values("timestamp")
        current_price = group["price"].iloc[-1]
        last_checked  = group["timestamp"].iloc[-1]
        low           = group["price"].min()
        high          = group["price"].max()

        # 24h change
        cutoff = pd.Timestamp(now - timedelta(hours=24))
        before_24h = group[group["timestamp"] <= cutoff]
        if not before_24h.empty:
            price_24h_ago = before_24h["price"].iloc[-1]
            change_pct    = ((current_price - price_24h_ago) / price_24h_ago) * 100
        else:
            change_pct = 0.0

        # product name placeholder (replace with real scraped name later)
        name = asin

        rows.append({
            "ASIN":          asin,
            "Product":       name,
            "Price":         current_price,
            "24h Change":    change_pct,
            "Low":           low,
            "High":          high,
            "Last Checked":  last_checked,
        })

    return pd.DataFrame(rows)


def change_badge(val: float) -> str:
    if val > 0:
        return f'<span class="up">▲ {val:.1f}%</span>'
    elif val < 0:
        return f'<span class="down">▼ {abs(val):.1f}%</span>'
    return f'<span class="neutral">— 0.0%</span>'


def make_chart(df: pd.DataFrame, asin: str) -> go.Figure:
    data = df[df["asin"] == asin].sort_values("timestamp")
    prices     = data["price"].tolist()
    timestamps = data["timestamp"].tolist()

    if not prices:
        return go.Figure()

    min_price = min(prices)
    max_price = max(prices)
    min_idx   = prices.index(min_price)
    max_idx   = prices.index(max_price)

    fig = go.Figure()

    # fill area
    fig.add_trace(go.Scatter(
        x=timestamps, y=prices,
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.07)",
        line=dict(color="rgba(0,0,0,0)", width=0),
        showlegend=False, hoverinfo="skip",
    ))

    # main line
    fig.add_trace(go.Scatter(
        x=timestamps, y=prices,
        mode="lines",
        line=dict(color="#6366f1", width=2.5, shape="spline", smoothing=0.5),
        showlegend=False,
        hovertemplate="<b>$%{y:.2f}</b><br>%{x|%b %d  %H:%M}<extra></extra>",
    ))

    # low marker
    fig.add_trace(go.Scatter(
        x=[timestamps[min_idx]], y=[min_price],
        mode="markers+text",
        marker=dict(color="#16a34a", size=9, line=dict(color="white", width=2)),
        text=[f"  ${min_price:.2f}"], textposition="middle right",
        textfont=dict(color="#16a34a", size=11),
        showlegend=False, hoverinfo="skip",
    ))

    # high marker
    fig.add_trace(go.Scatter(
        x=[timestamps[max_idx]], y=[max_price],
        mode="markers+text",
        marker=dict(color="#dc2626", size=9, line=dict(color="white", width=2)),
        text=[f"  ${max_price:.2f}"], textposition="middle right",
        textfont=dict(color="#dc2626", size=11),
        showlegend=False, hoverinfo="skip",
    ))

    # current price line
    fig.add_hline(
        y=prices[-1],
        line=dict(color="#6366f1", width=1, dash="dot"),
        opacity=0.35,
    )

    price_padding = (max_price - min_price) * 0.15 or 0.5

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(t=20, b=40, l=50, r=20),
        height=260,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor="#e2e8f0", font=dict(size=13)),
        xaxis=dict(
            showgrid=False, showline=True, linecolor="#e2e8f0",
            tickfont=dict(color="#94a3b8", size=11), tickformat="%b %d", title=None,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#f1f5f9", zeroline=False,
            tickprefix="$", tickfont=dict(color="#94a3b8", size=11), title=None,
            range=[min_price - price_padding, max_price + price_padding],
        ),
    )
    return fig


# ===================== UI =====================

df = load_data(CSV_PATH)

# --- header ---
col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.markdown("## 📦 Amazon Price Tracker")
with col_refresh:
    if st.button("↻ Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown(f"<p style='color:#94a3b8;font-size:13px;margin-top:-12px'>Auto-refreshes every 5 minutes &nbsp;·&nbsp; Last loaded: {datetime.utcnow().strftime('%H:%M:%S')} UTC</p>", unsafe_allow_html=True)

if df.empty:
    st.warning("No data found. Make sure `prices.csv` exists and has data.")
    st.stop()

# --- summary metrics ---
summary = get_summary(df)
total   = len(summary)
drops   = (summary["24h Change"] < -1).sum()
rises   = (summary["24h Change"] > 1).sum()
avg     = summary["Price"].mean()

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Tracked Products</div>
        <div class="metric-value">{total}</div>
    </div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Price Drops (24h)</div>
        <div class="metric-value" style="color:#16a34a">{drops}</div>
    </div>""", unsafe_allow_html=True)
with m3:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Price Rises (24h)</div>
        <div class="metric-value" style="color:#dc2626">{rises}</div>
    </div>""", unsafe_allow_html=True)
with m4:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Avg Current Price</div>
        <div class="metric-value">${avg:.2f}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- summary table ---
st.markdown("### All Products")

table_df = summary.copy()
table_df["Last Checked"] = pd.to_datetime(table_df["Last Checked"]).dt.strftime("%b %d  %H:%M")
table_df["Price"]        = table_df["Price"].map("${:.2f}".format)
table_df["Low"]          = table_df["Low"].map("${:.2f}".format)
table_df["High"]         = table_df["High"].map("${:.2f}".format)
table_df["24h Change"]   = table_df["24h Change"].map(lambda v: f"▲ {v:.1f}%" if v > 0 else (f"▼ {abs(v):.1f}%" if v < 0 else "— 0.0%"))

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "ASIN":         st.column_config.TextColumn("ASIN", width="medium"),
        "Product":      st.column_config.TextColumn("Product", width="large"),
        "Price":        st.column_config.TextColumn("Price", width="small"),
        "24h Change":   st.column_config.TextColumn("24h Change", width="small"),
        "Low":          st.column_config.TextColumn("Low", width="small"),
        "High":         st.column_config.TextColumn("High", width="small"),
        "Last Checked": st.column_config.TextColumn("Last Checked", width="medium"),
    },
)

st.markdown("<br>", unsafe_allow_html=True)

# --- charts ---
st.markdown("### Price History")

asins = summary["ASIN"].tolist()
selected = st.selectbox("Select product", asins, label_visibility="collapsed")

if selected:
    product_data = df[df["asin"] == selected]
    row = summary[summary["ASIN"] == selected].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Current Price</div>
            <div class="metric-value">${row['Price']:.2f}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        badge = change_badge(row['24h Change'])
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">24h Change</div>
            <div class="metric-value" style="font-size:22px">{badge}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">All-time Low</div>
            <div class="metric-value" style="color:#16a34a">${row['Low']:.2f}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">All-time High</div>
            <div class="metric-value" style="color:#dc2626">${row['High']:.2f}</div>
        </div>""", unsafe_allow_html=True)

    # time range filter
    range_col, _ = st.columns([2, 5])
    with range_col:
        range_opt = st.selectbox(
            "Time range",
            ["Last 7 days", "Last 14 days", "Last 30 days", "All time"],
            index=2,
        )

    range_map = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30, "All time": 9999}
    days = range_map[range_opt]
    cutoff = pd.Timestamp(datetime.utcnow() - timedelta(days=days))
    filtered = product_data[product_data["timestamp"] >= cutoff] if days < 9999 else product_data

    fig = make_chart(filtered, selected)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # raw data expander
    with st.expander("Raw data"):
        st.dataframe(
            filtered[["timestamp", "price"]].sort_values("timestamp", ascending=False).reset_index(drop=True),
            use_container_width=True,
        )