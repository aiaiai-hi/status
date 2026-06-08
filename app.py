import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import timedelta, date

st.set_page_config(page_title="ИС Статус. Дэшборд", layout="wide")

BLUE    = "#1D5FA5"
BLUE2   = "#2563EB"
TEAL    = "#0F766E"
PURPLE  = "#7C3AED"
INDIGO  = "#4338CA"
BAR_B   = "#378ADD"
BAR_T   = "#1D9E75"
LINE_C  = "#D85A30"
LINE_A  = "#BA7517"
LINE_P  = "#7F77DD"
BG      = "rgba(0,0,0,0)"
GRID    = "rgba(128,128,128,0.15)"

FUNNEL_COLORS_LIST = ["#378ADD", "#1D9E75", "#BA7517"]
FUNNEL_LABELS      = ["Тип А", "Тип Б", "Тип В"]

# ── загрузка данных ────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_excel("Metrics.xlsx", header=1)
    date_cols = [c for c in df.columns if hasattr(c, "year")]
    records = []
    for _, row in df.iterrows():
        mid   = str(row["Названия строк"]).strip()
        mname = str(row["metric_name"]).strip() if pd.notna(row["metric_name"]) else ""
        if not mid.startswith("metric_smr_"):
            continue
        for d in date_cols:
            v = row[d]
            if pd.notna(v):
                records.append({"metric_id": mid, "metric_name": mname,
                                 "date": pd.Timestamp(d), "value": float(v)})
    long = pd.DataFrame(records)
    long["date"] = pd.to_datetime(long["date"])
    long = long.groupby(["metric_id", "metric_name", "date"], as_index=False)["value"].sum()
    return long

# ── session state ──────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "summary"
p = st.session_state.page

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
.block-container {{ padding-top: 1.5rem !important; }}
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondary"] {{
    white-space: nowrap !important; font-size: 14px !important; font-weight: 600 !important;
}}
button[data-testid="stBaseButton-secondary"] {{
    background-color: #ffffff !important; color: {BLUE} !important;
    border: 2px solid {BLUE} !important;
}}
button[data-testid="stBaseButton-secondary"]:hover {{ background-color: #e8f0fb !important; }}
button[data-testid="stBaseButton-primary"] {{
    background-color: {BLUE} !important; color: #ffffff !important;
    border: 2px solid {BLUE} !important;
}}
button[data-testid="stBaseButton-primary"]:hover {{
    background-color: #164d8a !important; border-color: #164d8a !important;
}}
/* убрать стрелки из date_input */
input[type=date]::-webkit-calendar-picker-indicator {{ opacity: 0.6; }}
</style>
""", unsafe_allow_html=True)

# ── заголовок + навигация ──────────────────────────────────────────────────
st.markdown(
    f"<h1 style='font-size:28px;font-weight:700;color:{BLUE};margin-bottom:12px;'>"
    "ИС Статус. Дэшборд</h1>", unsafe_allow_html=True)

c1, c2, _ = st.columns([0.9, 1.9, 7])
with c1:
    if st.button("Саммари", key="nav_summary",
                 type="primary" if p == "summary" else "secondary",
                 use_container_width=True):
        st.session_state.page = "summary"; st.rerun()
with c2:
    if st.button("Влияние на бизнес. БМО", key="nav_bmo",
                 type="primary" if p == "bmo" else "secondary",
                 use_container_width=True):
        st.session_state.page = "bmo"; st.rerun()

st.markdown("<hr style='margin:10px 0 14px;border:none;border-top:1px solid #ddd;'>",
            unsafe_allow_html=True)

# ── хелперы ────────────────────────────────────────────────────────────────
def chart_title(txt, size=15):
    st.markdown(
        f'<p style="font-size:{size}px;font-weight:600;margin:0 0 4px;color:{BLUE};">{txt}</p>',
        unsafe_allow_html=True)

def get_series(df_long, metric_id, date_from, date_to):
    mask = ((df_long["metric_id"] == metric_id) &
            (df_long["date"] >= pd.Timestamp(date_from)) &
            (df_long["date"] <= pd.Timestamp(date_to)))
    return df_long[mask].sort_values("date")

def get_name(df_long, metric_id):
    rows = df_long[df_long["metric_id"] == metric_id]["metric_name"]
    return rows.iloc[0] if not rows.empty else metric_id

def last_val_delta(series):
    if series.empty:
        return None, None, None
    last = series["value"].iloc[-1]
    if len(series) >= 2:
        prev  = series["value"].iloc[-2]
        delta = last - prev
        pct   = (delta / prev * 100) if prev != 0 else 0.0
        return last, pct, delta
    return last, None, None

CARD_STYLES = {
    "blue":   ("linear-gradient(135deg,#1D5FA5 0%,#2563EB 100%)", "#fff"),
    "teal":   ("linear-gradient(135deg,#0F766E 0%,#14B8A6 100%)", "#fff"),
    "purple": ("linear-gradient(135deg,#7C3AED 0%,#A78BFA 100%)", "#fff"),
    "indigo": ("linear-gradient(135deg,#4338CA 0%,#818CF8 100%)", "#fff"),
    "slate":  ("linear-gradient(135deg,#334155 0%,#64748B 100%)", "#fff"),
}

def metric_card(label, value_str, delta_pct=None, delta_raw=None, style="blue"):
    bg, fg = CARD_STYLES[style]
    if delta_pct is not None:
        arrow     = "▲" if delta_raw > 0 else ("▼" if delta_raw < 0 else "→")
        sign      = "+" if delta_pct >= 0 else ""
        col_arrow = "#86EFAC" if delta_raw > 0 else ("#FCA5A5" if delta_raw < 0 else "#CBD5E1")
        delta_html = (f'<span style="font-size:13px;color:{col_arrow};'
                      f'font-weight:600;margin-left:6px;">'
                      f'{arrow} {sign}{delta_pct:.1f}%</span>')
    else:
        delta_html = ""

    st.markdown(f"""
    <div style="background:{bg};border-radius:14px;padding:14px 16px;
                color:{fg};margin-bottom:10px;
                box-shadow:0 4px 15px rgba(0,0,0,0.12);">
      <div style="font-size:13px;opacity:.85;line-height:1.3;
                  margin-bottom:6px;font-weight:500;">{label}</div>
      <div style="display:flex;align-items:baseline;gap:4px;flex-wrap:wrap;">
        <span style="font-size:26px;font-weight:700;letter-spacing:-0.5px;">{value_str}</span>
        {delta_html}
      </div>
    </div>""", unsafe_allow_html=True)

def render_metric(df_long, metric_id, date_from, date_to, fmt="{:.0f}", style="blue"):
    s    = get_series(df_long, metric_id, date_from, date_to)
    name = get_name(df_long, metric_id)
    v, pct, raw = last_val_delta(s)
    val_str = fmt.format(v) if v is not None else "—"
    metric_card(name, val_str, pct, raw, style)

def render_metric_pair(df_long, id1, id2, date_from, date_to, fmt="{:.0f}", style="teal"):
    s1 = get_series(df_long, id1, date_from, date_to)
    s2 = get_series(df_long, id2, date_from, date_to)
    n1 = get_name(df_long, id1)
    n2 = get_name(df_long, id2)
    v1, p1, r1 = last_val_delta(s1)
    v2, p2, r2 = last_val_delta(s2)

    def _dhtml(pct, raw):
        if pct is None: return ""
        arrow = "▲" if raw > 0 else ("▼" if raw < 0 else "→")
        sign  = "+" if pct >= 0 else ""
        col   = "#86EFAC" if raw > 0 else ("#FCA5A5" if raw < 0 else "#CBD5E1")
        return f'<span style="font-size:12px;color:{col};font-weight:600;">{arrow} {sign}{pct:.1f}%</span>'

    bg, fg = CARD_STYLES[style]
    st.markdown(f"""
    <div style="background:{bg};border-radius:14px;padding:14px 16px;
                color:{fg};margin-bottom:10px;
                box-shadow:0 4px 15px rgba(0,0,0,0.12);">
      <div style="font-size:12px;opacity:.8;margin-bottom:8px;font-weight:500;">
        {n1} / {n2}
      </div>
      <div style="display:flex;gap:12px;align-items:center;">
        <div>
          <span style="font-size:22px;font-weight:700;">{fmt.format(v1) if v1 else "—"}</span>
          <span style="margin-left:4px;">{_dhtml(p1,r1)}</span>
        </div>
        <div style="opacity:.5;font-size:20px;">/</div>
        <div>
          <span style="font-size:22px;font-weight:700;">{fmt.format(v2) if v2 else "—"}</span>
          <span style="margin-left:4px;">{_dhtml(p2,r2)}</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

def line_chart(df_long, metric_ids, colors, names, date_from, date_to,
               height=200, pct_change=False, title=None):
    fig = go.Figure()
    for mid, color, name in zip(metric_ids, colors, names):
        s = get_series(df_long, mid, date_from, date_to)
        if s.empty: continue
        if pct_change:
            s = s.copy()
            s["plot_val"] = s["value"].pct_change() * 100
            s = s.dropna(subset=["plot_val"])
            y_vals = s["plot_val"].round(2)
            ysuffix = "%"
        else:
            y_vals  = s["value"]
            ysuffix = ""
        # используем реальные даты как категории
        x_dates = s["date"].dt.strftime("%d.%m.%y").tolist()
        # конвертируем hex в rgba для fillcolor
        def _hex_to_rgba(h, a=0.1):
            h = h.lstrip("#")
            r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            return f"rgba({r},{g},{b},{a})"
        fill_color = _hex_to_rgba(color) if color.startswith("#") else "rgba(100,100,200,0.1)"
        fig.add_trace(go.Scatter(
            x=x_dates, y=y_vals, name=name, mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5, color=color),
            fill="tozeroy" if len(metric_ids) == 1 else None,
            fillcolor=fill_color,
            hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.2f}<extra></extra>",
        ))
    layout = dict(
        height=height,
        margin=dict(t=8, b=50, l=42, r=8),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=10, color="#888780"),
        showlegend=len(metric_ids) > 1,
        legend=dict(orientation="h", y=1.1, x=0, font=dict(size=10)),
        xaxis=dict(type="category", gridcolor=GRID,
                   tickfont=dict(size=9), tickangle=-35),
        yaxis=dict(gridcolor=GRID, tickfont=dict(size=9), ticksuffix=ysuffix,
                   zeroline=pct_change,
                   zerolinecolor="rgba(128,128,128,0.3)"),
    )
    fig.update_layout(**layout)
    return fig

def bar_pct_chart(df_long, metric_ids, colors, names, date_from, date_to, height=200):
    fig = go.Figure()
    for mid, color, name in zip(metric_ids, colors, names):
        s = get_series(df_long, mid, date_from, date_to)
        if s.empty or len(s) < 2: continue
        s = s.copy()
        s["pct"] = s["value"].pct_change() * 100
        s = s.dropna(subset=["pct"])
        x_fmt = s["date"].dt.strftime("%d.%m")
        fig.add_trace(go.Bar(
            x=x_fmt, y=s["pct"].round(1), name=name,
            marker_color=color, opacity=0.85,
            text=s["pct"].round(1).astype(str) + "%",
            textposition="outside", textfont=dict(size=8),
        ))
    fig.update_layout(
        height=height,
        margin=dict(t=8, b=30, l=42, r=8),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=10, color="#888780"),
        barmode="group",
        showlegend=True,
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
        xaxis=dict(gridcolor=GRID, tickfont=dict(size=9), tickangle=-30),
        yaxis=dict(gridcolor=GRID, tickfont=dict(size=9), ticksuffix="%",
                   zeroline=True, zerolinecolor="rgba(128,128,128,0.3)"),
    )
    return fig

def build_funnel_svg():
    funnel_stages = ["Всего отклонений","Выявлено в системе","Передано на устранение","Устранено"]
    funnel_vals   = [1600,1200,950,850]
    funnel_parts  = {
        "Всего отклонений":       [600,600,400],
        "Выявлено в системе":     [460,440,300],
        "Передано на устранение": [360,350,240],
        "Устранено":              [320,310,220],
    }
    W,H = 520,460; label_w=185; bar_area=W-label_w-60
    max_val=funnel_vals[0]; row_h,gap,top_m=68,14,16
    out=[]
    for i,stage in enumerate(funnel_stages):
        total=funnel_vals[i]
        top_frac=(funnel_vals[i-1]/max_val) if i>0 else 1.0
        bot_frac=total/max_val
        bw_top=bar_area*top_frac; bw_bot=bar_area*bot_frac
        cx=label_w+bar_area/2; yt=top_m+i*(row_h+gap); yb=yt+row_h
        xl_top=cx-bw_top/2; xl_bot=cx-bw_bot/2
        parts=funnel_parts[stage]; total_p=sum(parts); ct,cb=xl_top,xl_bot
        for j in range(3):
            fj=parts[j]/total_p; swt=bw_top*fj; swb=bw_bot*fj
            pts=(f"{ct:.1f},{yt} {ct+swt:.1f},{yt} {cb+swb:.1f},{yb} {cb:.1f},{yb}")
            tx=ct+swt/2; ty=yt+row_h/2+5
            out.append(f'<polygon points="{pts}" fill="{FUNNEL_COLORS_LIST[j]}" opacity="0.88" stroke="white" stroke-width="1.5"/>')
            out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="white">{parts[j]}</text>')
            ct+=swt; cb+=swb
        mid_y=yt+row_h/2+5
        out.append(f'<text x="{label_w-10}" y="{mid_y:.1f}" text-anchor="end" font-size="12" fill="#444">{stage}</text>')
        out.append(f'<text x="{cx+bw_bot/2+10}" y="{mid_y:.1f}" text-anchor="start" font-size="13" font-weight="700" fill="#222">{total}</text>')
    lx,ly=label_w,H-28
    for k,(lbl,clr) in enumerate(zip(FUNNEL_LABELS,FUNNEL_COLORS_LIST)):
        out.append(f'<rect x="{lx+k*90}" y="{ly}" width="13" height="13" fill="{clr}" rx="3"/>')
        out.append(f'<text x="{lx+k*90+17}" y="{ly+11}" font-size="12" fill="#444">{lbl}</text>')
    return (f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="font-family:sans-serif;">{"".join(out)}</svg>')


# ══════════════════════════════════════════════════════════════════════════
# ЗАГРУЗКА
# ══════════════════════════════════════════════════════════════════════════
try:
    df_long = load_data()
    data_ok = True
    all_dates = sorted(df_long["date"].unique())
    max_date  = pd.Timestamp(all_dates[-1])
    min_date  = pd.Timestamp(all_dates[0])
except Exception as e:
    st.error(f"Не удалось загрузить metrics.xlsx: {e}")
    data_ok = False


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
if p == "summary":
    if not data_ok:
        st.info("Разместите файл metrics.xlsx в корневой папке приложения.")
        st.stop()

    # ── выбор периода ─────────────────────────────────────────────────────
    default_from = (max_date - timedelta(weeks=3)).date()
    if default_from < min_date.date():
        default_from = min_date.date()

    fc, tc, _ = st.columns([1.3, 1.3, 6])
    with fc:
        date_from = st.date_input("Период с", value=default_from,
                                  min_value=min_date.date(), max_value=max_date.date(),
                                  format="DD.MM.YYYY", key="d_from")
    with tc:
        date_to = st.date_input("по", value=max_date.date(),
                                min_value=min_date.date(), max_value=max_date.date(),
                                format="DD.MM.YYYY", key="d_to")

    # период 3 месяца назад от конца для графиков
    date_3m = (max_date - pd.DateOffset(months=3)).date()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    n4  = get_name(df_long, "metric_smr_4")
    n5  = get_name(df_long, "metric_smr_5")
    n36 = get_name(df_long, "metric_smr_36")
    n37 = get_name(df_long, "metric_smr_37")
    n38 = get_name(df_long, "metric_smr_38")
    n39 = get_name(df_long, "metric_smr_39")

    def grouped_bar(metric_ids, colors, names, d_from, d_to, height=220):
        fig = go.Figure()
        for mid, color, name in zip(metric_ids, colors, names):
            s = get_series(df_long, mid, d_from, d_to)
            if s.empty: continue
            # используем строки дат как категории, чтобы Plotly не путал с числами
            x_labels = s["date"].dt.strftime("%d.%m.%y").tolist()
            fig.add_trace(go.Bar(
                x=x_labels, y=s["value"], name=name,
                marker_color=color, opacity=0.9,
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.0f}<extra></extra>",
            ))
        fig.update_layout(
            height=height, margin=dict(t=8,b=50,l=42,r=8),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=10,color="#888780"),
            barmode="group",
            bargap=0.2,       # зазор между группами
            bargroupgap=0.05, # зазор внутри группы
            showlegend=True,
            legend=dict(orientation="h",y=1.14,x=0,font=dict(size=9)),
            xaxis=dict(
                type="category",  # строго категориальная ось
                gridcolor=GRID, tickfont=dict(size=9), tickangle=-35,
                tickmode="array",
                tickvals=list(range(len(s["date"]))),
            ),
            yaxis=dict(gridcolor=GRID,tickfont=dict(size=9)),
        )
        return fig

    def bar_with_trend(metric_ids, bar_colors, line_colors, names, d_from, d_to, height=240):
        fig = go.Figure()
        for mid, bc, lc, name in zip(metric_ids, bar_colors, line_colors, names):
            s = get_series(df_long, mid, d_from, d_to)
            if s.empty: continue
            x_fmt = s["date"].dt.strftime("%d.%m")
            fig.add_trace(go.Bar(x=x_fmt, y=s["value"], name=name,
                                 marker_color=bc, opacity=0.55, yaxis="y1"))
            s2 = s.copy()
            s2["pct"] = s2["value"].pct_change() * 100
            s2 = s2.dropna(subset=["pct"])
            if not s2.empty:
                x2 = s2["date"].dt.strftime("%d.%m")
                fig.add_trace(go.Scatter(
                    x=x2, y=s2["pct"].round(1), name=f"{name} %",
                    mode="lines+markers",
                    line=dict(color=lc, width=2, dash="dot"),
                    marker=dict(size=4), yaxis="y2"))
        fig.update_layout(
            height=height, margin=dict(t=10,b=30,l=42,r=42),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=10,color="#888780"), barmode="group",
            showlegend=True,
            legend=dict(orientation="h",y=1.14,x=0,font=dict(size=9)),
            xaxis=dict(gridcolor=GRID,tickfont=dict(size=9),tickangle=-30),
            yaxis=dict(gridcolor=GRID,tickfont=dict(size=9)),
            yaxis2=dict(overlaying="y",side="right",gridcolor="rgba(0,0,0,0)",
                        tickfont=dict(size=9),ticksuffix="%",zeroline=True,
                        zerolinecolor="rgba(128,128,128,0.3)"),
        )
        return fig

    # Q1 верх-лево: метрики 1,3 | bar+trend 4,5
    q1, q2 = st.columns([1, 1], gap="large")
    with q1:
        mc1, gc1 = st.columns([1, 1.8], gap="small")
        with mc1:
            render_metric(df_long, "metric_smr_1", date_from, date_to, fmt="{:.0f}", style="blue")
            render_metric(df_long, "metric_smr_3", date_from, date_to, fmt="{:.0f}", style="indigo")
        with gc1:
            chart_title(f"{n4} / {n5}", size=11)
            fig45 = grouped_bar(
                metric_ids=["metric_smr_4","metric_smr_5"],
                colors=[BAR_B, BAR_T],
                names=[n4, n5],
                d_from=date_3m, d_to=max_date.date(), height=240)
            st.plotly_chart(fig45, use_container_width=True)

    # Q2 верх-право: линия тренда отклонений | метрика 36
    with q2:
        gc2, mc2 = st.columns([1.8, 1], gap="small")
        with gc2:
            chart_title(get_name(df_long,"metric_smr_1") + " (3 мес.)", size=11)
            fig36g = line_chart(df_long, ["metric_smr_1"], [BAR_B],
                                [get_name(df_long,"metric_smr_1")],
                                date_3m, max_date.date(), height=130)
            st.plotly_chart(fig36g, use_container_width=True)
        with mc2:
            render_metric(df_long, "metric_smr_36", date_from, date_to, fmt="{:.1f}", style="teal")

    st.markdown("<hr style='margin:8px 0;border:none;border-top:1px solid #eee;'>",
                unsafe_allow_html=True)

    # Q3 низ-лево: метрики 2, 38/39 | grouped bar 38+39
    q3, q4 = st.columns([1, 1], gap="large")
    with q3:
        mc3, gc3 = st.columns([1, 1.8], gap="small")
        with mc3:
            render_metric(df_long, "metric_smr_2", date_from, date_to, fmt="{:.0f}", style="slate")
            render_metric_pair(df_long, "metric_smr_38", "metric_smr_39",
                               date_from, date_to, fmt="{:.0f}", style="teal")
        with gc3:
            chart_title(f"{n38} / {n39}", size=11)
            fig3839 = grouped_bar(
                metric_ids=["metric_smr_38","metric_smr_39"],
                colors=[LINE_C, LINE_P], names=[n38, n39],
                d_from=date_3m, d_to=max_date.date(), height=240)
            st.plotly_chart(fig3839, use_container_width=True)

    # Q4 низ-право: линия тренда скорости | метрика 37
    with q4:
        gc4, mc4 = st.columns([1.8, 1], gap="small")
        with gc4:
            chart_title(n37 + " (3 мес.)", size=11)
            fig37g = line_chart(df_long, ["metric_smr_37"], [PURPLE],
                                [n37], date_3m, max_date.date(), height=130)
            st.plotly_chart(fig37g, use_container_width=True)
        with mc4:
            render_metric(df_long, "metric_smr_37", date_from, date_to, fmt="{:.1f}", style="purple")

    st.caption(f"Данные: metrics.xlsx · последнее обновление {max_date.strftime('%d.%m.%Y')}")


# ══════════════════════════════════════════════════════════════════════════
# БМО
# ══════════════════════════════════════════════════════════════════════════
else:
    if data_ok:
        default_from_b = (max_date - timedelta(weeks=3)).date()
        fc2, tc2, _ = st.columns([1.3, 1.3, 6])
        with fc2:
            date_from_b = st.date_input("Период с", value=default_from_b,
                                        min_value=min_date.date(), max_value=max_date.date(),
                                        format="DD.MM.YYYY", key="bmo_from")
        with tc2:
            date_to_b = st.date_input("по", value=max_date.date(),
                                      min_value=min_date.date(), max_value=max_date.date(),
                                      format="DD.MM.YYYY", key="bmo_to")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    mc = st.columns(6)
    lv_bmo = [("Доля по Банку","50,1%","+0,2%"),("Целевое значение","—",None),
              ("Счётчик повторов","5,6 нед.","-0,2"),("Задач / хроник","—",None),
              ("Доля устранённых","—",None),("Скорость устранения","—",None)]
    for col,(lbl,val,delta) in zip(mc,lv_bmo):
        with col: st.metric(lbl,val,delta)

    st.divider()

    graphs_col, funnel_col = st.columns([11,9], gap="large")
    bmo_weeks  = ["нед 1","нед 2","нед 3","нед 4","нед 5","нед 6","нед 7","нед 8"]
    bmo_vsp    = [9700,9800,10100,10300,10500,10200,10400,10500]
    bmo_tasks  = [1300,1350,1400,1420,1450,1430,1460,1525]
    bmo_share  = [22,26,24,22,25,23,26,24]
    bmo_speed2 = [18,20,17,19,21,18,20,19]

    with graphs_col:
        chart_title("Динамика ВСП и задач по неделям")
        f5 = go.Figure()
        f5.add_trace(go.Bar(name="ВСП", x=bmo_weeks, y=bmo_vsp,
                            marker_color=BAR_B, opacity=.8, yaxis="y1"))
        f5.add_trace(go.Scatter(name="Задачи", x=bmo_weeks, y=bmo_tasks,
                                mode="lines+markers",
                                line=dict(color=LINE_C,width=2),
                                marker=dict(size=5), yaxis="y2"))
        f5.update_layout(
            height=230, margin=dict(t=10,b=32,l=42,r=50),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=11,color="#888780"), showlegend=True,
            legend=dict(orientation="h",y=1.12,x=0,font=dict(size=10)),
            xaxis=dict(gridcolor=GRID,tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID,tickfont=dict(size=10),title=dict(text="ВСП",font=dict(size=10))),
            yaxis2=dict(overlaying="y",side="right",gridcolor="rgba(0,0,0,0)",
                        tickfont=dict(size=10),title=dict(text="Задачи",font=dict(size=10))),
        )
        st.plotly_chart(f5, use_container_width=True)

        chart_title("Доля и скорость устранения")
        f6 = go.Figure()
        f6.add_trace(go.Bar(name="Доля (%)", x=bmo_weeks, y=bmo_share,
                            marker_color=LINE_P, opacity=.85))
        f6.add_trace(go.Scatter(name="Скорость", x=bmo_weeks, y=bmo_speed2,
                                mode="lines+markers",
                                line=dict(color=LINE_A,width=2), marker=dict(size=5)))
        f6.update_layout(
            height=230, margin=dict(t=10,b=32,l=42,r=8),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=11,color="#888780"), showlegend=True,
            legend=dict(orientation="h",y=1.12,x=0,font=dict(size=10)),
            barmode="overlay",
            xaxis=dict(gridcolor=GRID,tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID,tickfont=dict(size=10)),
        )
        st.plotly_chart(f6, use_container_width=True)

    with funnel_col:
        chart_title("Воронка метрик БА по БМО")
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.markdown(build_funnel_svg(), unsafe_allow_html=True)

    st.caption("* Заменяем термин «Срок жизни». Методологию расчёта разработали. За 4 недели.")
