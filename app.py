import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import timedelta

st.set_page_config(page_title="ИС Статус. Дэшборд", layout="wide")

BLUE   = "#1D5FA5"
TEAL   = "#0F6E56"
BAR_B  = "#378ADD"
BAR_T  = "#1D9E75"
LINE_C = "#D85A30"
LINE_A = "#BA7517"
LINE_P = "#7F77DD"
BG     = "rgba(0,0,0,0)"
GRID   = "rgba(128,128,128,0.15)"

FUNNEL_COLORS_LIST = ["#378ADD", "#1D9E75", "#BA7517"]
FUNNEL_LABELS      = ["Тип А", "Тип Б", "Тип В"]

# ── загрузка данных ────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_excel("Книга2.xlsx", header=1)
    date_cols = [c for c in df.columns if hasattr(c, "year")]
    id_cols   = ["Названия строк", "metric_name", "deviation_name"]

    # строим длинный формат: одна строка = один metric_id + дата + значение
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
    # агрегируем по metric_id + date (на случай нескольких строк)
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
    white-space: nowrap !important;
    font-size: 14px !important;
    font-weight: 600 !important;
}}
button[data-testid="stBaseButton-secondary"] {{
    background-color: #ffffff !important;
    color: {BLUE} !important;
    border: 2px solid {BLUE} !important;
}}
button[data-testid="stBaseButton-secondary"]:hover {{
    background-color: #e8f0fb !important;
}}
button[data-testid="stBaseButton-primary"] {{
    background-color: {BLUE} !important;
    color: #ffffff !important;
    border: 2px solid {BLUE} !important;
}}
button[data-testid="stBaseButton-primary"]:hover {{
    background-color: #164d8a !important;
    border-color: #164d8a !important;
}}
</style>
""", unsafe_allow_html=True)

# ── заголовок ──────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='font-size:28px;font-weight:700;color:{BLUE};margin-bottom:12px;'>"
    "ИС Статус. Дэшборд</h1>",
    unsafe_allow_html=True,
)

# ── кнопки навигации ───────────────────────────────────────────────────────
c1, c2, _ = st.columns([0.9, 1.9, 7])
with c1:
    if st.button("Саммари", key="nav_summary",
                 type="primary" if p == "summary" else "secondary",
                 use_container_width=True):
        st.session_state.page = "summary"
        st.rerun()
with c2:
    if st.button("Влияние на бизнес. БМО", key="nav_bmo",
                 type="primary" if p == "bmo" else "secondary",
                 use_container_width=True):
        st.session_state.page = "bmo"
        st.rerun()

st.markdown("<hr style='margin:10px 0 18px;border:none;border-top:1px solid #ddd;'>",
            unsafe_allow_html=True)

# ── хелперы ────────────────────────────────────────────────────────────────
def chart_title(txt):
    st.markdown(
        f'<p style="font-size:16px;font-weight:600;margin:0 0 4px;color:{BLUE};">{txt}</p>',
        unsafe_allow_html=True)

def manual_layout(h=210, right_margin=8):
    return dict(
        height=h,
        margin=dict(t=10, b=32, l=42, r=right_margin),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=11, color="#888780"),
        showlegend=False,
        xaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
    )

def get_metric_series(df_long, metric_id, date_from, date_to):
    """Вернуть серию значений метрики за период."""
    mask = (
        (df_long["metric_id"] == metric_id) &
        (df_long["date"] >= pd.Timestamp(date_from)) &
        (df_long["date"] <= pd.Timestamp(date_to))
    )
    return df_long[mask].sort_values("date")

def get_metric_name(df_long, metric_id):
    rows = df_long[df_long["metric_id"] == metric_id]["metric_name"]
    return rows.iloc[0] if not rows.empty else metric_id

def metric_card_data(df_long, metric_id, date_from, date_to, fmt="{:.0f}", label=None):
    """Отрисовать плашку метрики с динамикой."""
    series = get_metric_series(df_long, metric_id, date_from, date_to)
    name   = label or get_metric_name(df_long, metric_id)

    if series.empty:
        val_str   = "—"
        delta_str = ""
        arrow     = ""
        col_arrow = "#888"
    else:
        last_val  = series["value"].iloc[-1]
        val_str   = fmt.format(last_val)
        if len(series) >= 2:
            prev_val  = series["value"].iloc[-2]
            delta     = last_val - prev_val
            pct       = (delta / prev_val * 100) if prev_val != 0 else 0
            sign      = "+" if delta >= 0 else ""
            arrow     = "▲" if delta > 0 else ("▼" if delta < 0 else "→")
            col_arrow = BAR_T if delta > 0 else (LINE_C if delta < 0 else "#888")
            delta_str = f"{sign}{pct:.1f}%"
        else:
            arrow     = ""
            col_arrow = "#888"
            delta_str = ""

    st.markdown(f"""
    <div style="background:{BLUE};border-radius:10px;padding:10px 14px;
                color:#fff;margin-bottom:10px;">
      <div style="font-size:11px;opacity:.85;line-height:1.3;margin-bottom:4px;">{name}</div>
      <div style="display:flex;align-items:baseline;gap:8px;">
        <span style="font-size:22px;font-weight:600;">{val_str}</span>
        <span style="font-size:14px;color:{col_arrow};font-weight:600;">
          {arrow} {delta_str}
        </span>
      </div>
    </div>""", unsafe_allow_html=True)

def metric_card_teal(df_long, metric_id1, metric_id2, date_from, date_to, fmt="{:.0f}"):
    """Плашка с двумя метриками (38/39) зелёного цвета."""
    s1 = get_metric_series(df_long, metric_id1, date_from, date_to)
    s2 = get_metric_series(df_long, metric_id2, date_from, date_to)
    n1 = get_metric_name(df_long, metric_id1)
    n2 = get_metric_name(df_long, metric_id2)

    def _val_delta(series):
        if series.empty:
            return "—", "", "#888"
        last = series["value"].iloc[-1]
        vstr = fmt.format(last)
        if len(series) >= 2:
            prev  = series["value"].iloc[-2]
            delta = last - prev
            pct   = (delta / prev * 100) if prev != 0 else 0
            sign  = "+" if delta >= 0 else ""
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "→")
            col   = BAR_T if delta > 0 else (LINE_C if delta < 0 else "#888")
            return vstr, f"{arrow} {sign}{pct:.1f}%", col
        return vstr, "", "#888"

    v1, d1, c1 = _val_delta(s1)
    v2, d2, c2 = _val_delta(s2)

    st.markdown(f"""
    <div style="background:{TEAL};border-radius:10px;padding:10px 14px;
                color:#fff;margin-bottom:10px;">
      <div style="font-size:11px;opacity:.85;line-height:1.3;margin-bottom:6px;">
        {n1} / {n2}
      </div>
      <div style="display:flex;gap:16px;align-items:baseline;">
        <div>
          <span style="font-size:20px;font-weight:600;">{v1}</span>
          <span style="font-size:13px;color:{c1};font-weight:600;margin-left:4px;">{d1}</span>
        </div>
        <div style="opacity:.6;font-size:18px;">/</div>
        <div>
          <span style="font-size:20px;font-weight:600;">{v2}</span>
          <span style="font-size:13px;color:{c2};font-weight:600;margin-left:4px;">{d2}</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

def metric_card_right(df_long, metric_id, date_from, date_to, fmt="{:.1f}", bg=None):
    """Плашка для правой колонки (метрики 36, 37)."""
    bg = bg or BLUE
    series = get_metric_series(df_long, metric_id, date_from, date_to)
    name   = get_metric_name(df_long, metric_id)

    if series.empty:
        val_str, arrow, col_arrow, delta_str = "—", "", "#ccc", ""
    else:
        last_val = series["value"].iloc[-1]
        val_str  = fmt.format(last_val)
        if len(series) >= 2:
            prev_val  = series["value"].iloc[-2]
            delta     = last_val - prev_val
            pct       = (delta / prev_val * 100) if prev_val != 0 else 0
            sign      = "+" if delta >= 0 else ""
            arrow     = "▲" if delta > 0 else ("▼" if delta < 0 else "→")
            col_arrow = BAR_T if delta > 0 else (LINE_C if delta < 0 else "#888")
            delta_str = f"{sign}{pct:.1f}%"
        else:
            arrow, col_arrow, delta_str = "", "#ccc", ""

    st.markdown(f"""
    <div style="background:{bg};border-radius:10px;padding:12px 16px;
                color:#fff;margin-bottom:12px;">
      <div style="font-size:11px;opacity:.85;line-height:1.3;margin-bottom:6px;">{name}</div>
      <div style="display:flex;align-items:baseline;gap:8px;">
        <span style="font-size:26px;font-weight:600;">{val_str}</span>
        <span style="font-size:14px;color:{col_arrow};font-weight:600;">
          {arrow} {delta_str}
        </span>
      </div>
    </div>""", unsafe_allow_html=True)

def build_bar_pct_chart(df_long, metric_ids, colors, date_from, date_to, height=220):
    """Столбчатая диаграмма % изменений по нескольким метрикам."""
    fig = go.Figure()
    for mid, color in zip(metric_ids, colors):
        series = get_metric_series(df_long, mid, date_from, date_to)
        name   = get_metric_name(df_long, mid)
        if series.empty or len(series) < 2:
            continue
        # считаем % изменение к предыдущей точке
        series = series.copy()
        series["pct"] = series["value"].pct_change() * 100
        series = series.dropna(subset=["pct"])
        dates_fmt = series["date"].dt.strftime("%d.%m")
        fig.add_trace(go.Bar(
            x=dates_fmt,
            y=series["pct"].round(1),
            name=name,
            marker_color=color,
            opacity=0.85,
            text=series["pct"].round(1).astype(str) + "%",
            textposition="outside",
            textfont=dict(size=9),
        ))

    fig.update_layout(
        height=height,
        margin=dict(t=10, b=32, l=42, r=8),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=11, color="#888780"),
        barmode="group",
        showlegend=True,
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
        xaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID, tickfont=dict(size=10),
                   ticksuffix="%", zeroline=True,
                   zerolinecolor="rgba(128,128,128,0.3)"),
    )
    return fig

def build_funnel_svg():
    funnel_stages = ["Всего отклонений","Выявлено в системе","Передано на устранение","Устранено"]
    funnel_vals   = [1600, 1200, 950, 850]
    funnel_parts  = {
        "Всего отклонений":       [600, 600, 400],
        "Выявлено в системе":     [460, 440, 300],
        "Передано на устранение": [360, 350, 240],
        "Устранено":              [320, 310, 220],
    }
    W, H    = 520, 460
    label_w = 185
    bar_area= W - label_w - 60
    max_val = funnel_vals[0]
    row_h, gap, top_m = 68, 14, 16
    out = []
    for i, stage in enumerate(funnel_stages):
        total    = funnel_vals[i]
        top_frac = (funnel_vals[i-1]/max_val) if i > 0 else 1.0
        bot_frac = total/max_val
        bw_top   = bar_area*top_frac
        bw_bot   = bar_area*bot_frac
        cx       = label_w + bar_area/2
        yt       = top_m + i*(row_h+gap)
        yb       = yt + row_h
        xl_top   = cx - bw_top/2
        xl_bot   = cx - bw_bot/2
        parts    = funnel_parts[stage]
        total_p  = sum(parts)
        ct, cb   = xl_top, xl_bot
        for j in range(3):
            fj  = parts[j]/total_p
            swt = bw_top*fj; swb = bw_bot*fj
            pts = (f"{ct:.1f},{yt} {ct+swt:.1f},{yt} "
                   f"{cb+swb:.1f},{yb} {cb:.1f},{yb}")
            tx  = ct + swt/2; ty = yt + row_h/2 + 5
            out.append(f'<polygon points="{pts}" fill="{FUNNEL_COLORS_LIST[j]}" '
                       f'opacity="0.88" stroke="white" stroke-width="1.5"/>')
            out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" '
                       f'font-size="12" font-weight="600" fill="white">{parts[j]}</text>')
            ct += swt; cb += swb
        mid_y = yt + row_h/2 + 5
        out.append(f'<text x="{label_w-10}" y="{mid_y:.1f}" text-anchor="end" '
                   f'font-size="12" fill="#444">{stage}</text>')
        out.append(f'<text x="{cx+bw_bot/2+10}" y="{mid_y:.1f}" text-anchor="start" '
                   f'font-size="13" font-weight="700" fill="#222">{total}</text>')
    lx, ly = label_w, H-28
    for k, (lbl, clr) in enumerate(zip(FUNNEL_LABELS, FUNNEL_COLORS_LIST)):
        out.append(f'<rect x="{lx+k*90}" y="{ly}" width="13" height="13" '
                   f'fill="{clr}" rx="3"/>')
        out.append(f'<text x="{lx+k*90+17}" y="{ly+11}" font-size="12" fill="#444">{lbl}</text>')
    return (f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" '
            f'style="font-family:sans-serif;">{"".join(out)}</svg>')


# ══════════════════════════════════════════════════════════════════════════
# ЗАГРУЖАЕМ ДАННЫЕ
# ══════════════════════════════════════════════════════════════════════════
try:
    df_long = load_data()
    data_ok = True
except Exception as e:
    st.error(f"Не удалось загрузить Книга2.xlsx: {e}")
    data_ok = False


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
if p == "summary":

    if data_ok:
        # ── выбор периода ─────────────────────────────────────────────
        all_dates = sorted(df_long["date"].unique())
        max_date  = pd.Timestamp(all_dates[-1])
        min_date  = pd.Timestamp(all_dates[0])

        # по умолчанию — последние 3 недели
        default_from = max_date - timedelta(weeks=3)
        if default_from < min_date:
            default_from = min_date

        f_col, t_col, _ = st.columns([1.2, 1.2, 6])
        with f_col:
            date_from = st.date_input("Период с", value=default_from.date(),
                                      min_value=min_date.date(), max_value=max_date.date(),
                                      key="date_from")
        with t_col:
            date_to = st.date_input("по", value=max_date.date(),
                                    min_value=min_date.date(), max_value=max_date.date(),
                                    key="date_to")

        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        # ── layout: левая колонка (метрики) | центр (график) | правая (метрики) ──
        left_col, center_col, right_col = st.columns([1, 2.5, 1], gap="medium")

        with left_col:
            # Метрика 1
            metric_card_data(df_long, "metric_smr_1", date_from, date_to, fmt="{:.0f}")
            # Метрика 3
            metric_card_data(df_long, "metric_smr_3", date_from, date_to, fmt="{:.0f}")
            # Метрика 2
            metric_card_data(df_long, "metric_smr_2", date_from, date_to, fmt="{:.0f}")
            # Метрика 38 / 39 в одной плашке
            metric_card_teal(df_long, "metric_smr_38", "metric_smr_39",
                             date_from, date_to, fmt="{:.0f}")

        with center_col:
            chart_title("% изменений: метрики 4 и 5 по неделям")
            fig_bar = build_bar_pct_chart(
                df_long,
                metric_ids=["metric_smr_4", "metric_smr_5"],
                colors=[BAR_B, BAR_T],
                date_from=date_from,
                date_to=date_to,
                height=420,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with right_col:
            # Метрика 36
            metric_card_right(df_long, "metric_smr_36", date_from, date_to,
                              fmt="{:.1f}%", bg=BLUE)
            # Метрика 37
            metric_card_right(df_long, "metric_smr_37", date_from, date_to,
                              fmt="{:.1f}", bg=TEAL)

        st.caption("Данные: Книга2.xlsx")
    else:
        st.info("Разместите файл Книга2.xlsx в корневой папке приложения.")


# ══════════════════════════════════════════════════════════════════════════
# БМО
# ══════════════════════════════════════════════════════════════════════════
else:
    if data_ok:
        all_dates = sorted(df_long["date"].unique())
        max_date  = pd.Timestamp(all_dates[-1])
        min_date  = pd.Timestamp(all_dates[0])
        default_from = max_date - timedelta(weeks=3)
        if default_from < min_date:
            default_from = min_date

        f_col, t_col, _ = st.columns([1.2, 1.2, 6])
        with f_col:
            date_from = st.date_input("Период с", value=default_from.date(),
                                      min_value=min_date.date(), max_value=max_date.date(),
                                      key="bmo_date_from")
        with t_col:
            date_to = st.date_input("по", value=max_date.date(),
                                    min_value=min_date.date(), max_value=max_date.date(),
                                    key="bmo_date_to")
        st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    mc = st.columns(6)
    lv_bmo = [("Доля по Банку","50,1%","+0,2%"),("Целевое значение","—",None),
              ("Счётчик повторов","5,6 нед.","-0,2"),("Задач / хроник","—",None),
              ("Доля устранённых","—",None),("Скорость устранения","—",None)]
    for col, (lbl, val, delta) in zip(mc, lv_bmo):
        with col:
            st.metric(lbl, val, delta)

    st.divider()

    graphs_col, funnel_col = st.columns([11, 9], gap="large")

    with graphs_col:
        bmo_weeks  = ["нед 1","нед 2","нед 3","нед 4","нед 5","нед 6","нед 7","нед 8"]
        bmo_vsp    = [9700,9800,10100,10300,10500,10200,10400,10500]
        bmo_tasks  = [1300,1350,1400,1420,1450,1430,1460,1525]
        bmo_share  = [22,26,24,22,25,23,26,24]
        bmo_speed2 = [18,20,17,19,21,18,20,19]

        chart_title("Динамика ВСП и задач по неделям")
        f5 = go.Figure()
        f5.add_trace(go.Bar(name="ВСП", x=bmo_weeks, y=bmo_vsp,
                            marker_color=BAR_B, opacity=.8, yaxis="y1"))
        f5.add_trace(go.Scatter(name="Задачи", x=bmo_weeks, y=bmo_tasks,
                                mode="lines+markers",
                                line=dict(color=LINE_C, width=2),
                                marker=dict(size=5), yaxis="y2"))
        f5.update_layout(
            height=230, margin=dict(t=10, b=32, l=42, r=50),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=11, color="#888780"),
            showlegend=True,
            legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
            xaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=10),
                       title=dict(text="ВСП", font=dict(size=10))),
            yaxis2=dict(overlaying="y", side="right",
                        gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10),
                        title=dict(text="Задачи", font=dict(size=10))),
        )
        st.plotly_chart(f5, use_container_width=True)

        chart_title("Доля и скорость устранения")
        f6 = go.Figure()
        f6.add_trace(go.Bar(name="Доля (%)", x=bmo_weeks, y=bmo_share,
                            marker_color=LINE_P, opacity=.85))
        f6.add_trace(go.Scatter(name="Скорость", x=bmo_weeks, y=bmo_speed2,
                                mode="lines+markers",
                                line=dict(color=LINE_A, width=2),
                                marker=dict(size=5)))
        f6.update_layout(
            height=230, margin=dict(t=10, b=32, l=42, r=8),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=11, color="#888780"),
            showlegend=True,
            legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
            barmode="overlay",
            xaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        )
        st.plotly_chart(f6, use_container_width=True)

    with funnel_col:
        chart_title("Воронка метрик БА по БМО")
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.markdown(build_funnel_svg(), unsafe_allow_html=True)

    st.caption("* Заменяем термин «Срок жизни». Методологию расчёта разработали. За 4 недели.")
