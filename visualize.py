import csv
from collections import defaultdict
from datetime import datetime
import plotly.graph_objects as go
import os

CSV_PATH = "prices_dummy.csv"
OUTPUT_DIR = "charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- load data ---
data = defaultdict(list)

with open(CSV_PATH, newline="") as f:
    for row in csv.DictReader(f):
        data[row["asin"]].append({
            "timestamp": datetime.fromisoformat(row["timestamp"]),
            "price": float(row["price"]),
        })

for asin in data:
    data[asin].sort(key=lambda r: r["timestamp"])

# --- generate one chart per asin ---
for asin, records in data.items():
    timestamps = [r["timestamp"] for r in records]
    prices     = [r["price"] for r in records]

    min_price = min(prices)
    max_price = max(prices)
    latest    = prices[-1]
    first     = prices[0]
    change_pct = ((latest - first) / first) * 100
    change_color = "#16a34a" if change_pct >= 0 else "#dc2626"
    change_arrow = "▲" if change_pct >= 0 else "▼"

    min_idx = prices.index(min_price)
    max_idx = prices.index(max_price)

    fig = go.Figure()

    # --- gradient fill area ---
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=prices,
        fill="tozeroy",
        fillcolor="rgba(99, 102, 241, 0.06)",
        line=dict(color="rgba(0,0,0,0)", width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # --- main line ---
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=prices,
        mode="lines",
        line=dict(color="#6366f1", width=2.5, shape="spline", smoothing=0.5),
        showlegend=False,
        hovertemplate="<b>$%{y:.2f}</b><br>%{x|%b %d, %Y  %H:%M}<extra></extra>",
    ))

    # --- low point marker ---
    fig.add_trace(go.Scatter(
        x=[timestamps[min_idx]],
        y=[min_price],
        mode="markers+text",
        marker=dict(color="#16a34a", size=10, symbol="circle",
                    line=dict(color="white", width=2)),
        text=[f"  ${min_price:.2f}"],
        textposition="middle right",
        textfont=dict(color="#16a34a", size=12),
        showlegend=False,
        hoverinfo="skip",
    ))

    # --- high point marker ---
    fig.add_trace(go.Scatter(
        x=[timestamps[max_idx]],
        y=[max_price],
        mode="markers+text",
        marker=dict(color="#dc2626", size=10, symbol="circle",
                    line=dict(color="white", width=2)),
        text=[f"  ${max_price:.2f}"],
        textposition="middle right",
        textfont=dict(color="#dc2626", size=12),
        showlegend=False,
        hoverinfo="skip",
    ))

    # --- current price reference line ---
    fig.add_hline(
        y=latest,
        line=dict(color="#6366f1", width=1, dash="dot"),
        opacity=0.4,
    )

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e5e7eb",
            font=dict(color="#111827", size=13),
        ),
        margin=dict(t=110, b=60, l=70, r=40),
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor="#e5e7eb",
            tickfont=dict(color="#6b7280", size=11),
            tickformat="%b %d",
            title=None,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f3f4f6",
            zeroline=False,
            showline=False,
            range=[min_price * 0.97, max_price * 1.03],
            tickprefix="$",
            tickfont=dict(color="#6b7280", size=11),
            title=None,
        ),
        annotations=[
            dict(
                xref="paper", yref="paper", x=0, y=1.22,
                text=f"<b style='font-size:18px;color:#111827'>{asin}</b>",
                showarrow=False, align="left",
            ),
            dict(
                xref="paper", yref="paper", x=0, y=1.10,
                text=f"<span style='font-size:26px;font-weight:700;color:#111827'>${latest:.2f}</span>",
                showarrow=False, align="left",
            ),
            dict(
                xref="paper", yref="paper", x=0.18, y=1.10,
                text=f"<span style='font-size:14px;color:{change_color}'>{change_arrow} {abs(change_pct):.1f}%</span>",
                showarrow=False, align="left",
            ),
            dict(
                xref="paper", yref="paper", x=0.60, y=1.12,
                text=f"<span style='color:#6b7280;font-size:11px'>LOW</span><br><b style='color:#16a34a'>${min_price:.2f}</b>",
                showarrow=False, align="center",
            ),
            dict(
                xref="paper", yref="paper", x=0.78, y=1.12,
                text=f"<span style='color:#6b7280;font-size:11px'>HIGH</span><br><b style='color:#dc2626'>${max_price:.2f}</b>",
                showarrow=False, align="center",
            ),
            dict(
                xref="paper", yref="paper", x=0.96, y=1.12,
                text=f"<span style='color:#6b7280;font-size:11px'>CHECKS</span><br><b style='color:#374151'>{len(prices)}</b>",
                showarrow=False, align="center",
            ),
        ],
    )

    out_path = os.path.join(OUTPUT_DIR, f"{asin}.html")
    fig.write_html(out_path, include_plotlyjs="cdn")
    print(f"Saved: {out_path}")

print(f"\nDone — {len(data)} charts in ./{OUTPUT_DIR}/")