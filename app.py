import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="ИС Статус. Отчёт", layout="wide")

# ── палитра ────────────────────────────────────────────────────────────────
BLUE   = "#1D5FA5"
TEAL   = "#0F6E56"
BAR_B  = "#378ADD"
BAR_T  = "#1D9E75"
LINE_C = "#D85A30"
LINE_A = "#BA7517"
LINE_P = "#7F77DD"

FUNNEL_COLORS_LIST = ["#378ADD", "#1D9E75", "#BA7517"]
FUNNEL_LABELS      = ["Тип А", "Тип Б", "Тип В"]

# ── данные ─────────────────────────────────────────────────────────────────
weeks  = ["июл 24","авг 24","сен 24","окт 24","ноя 24",
          "дек 24","янв 25","фев 25","мар 25","апр 25"]
weeks8 = ["сен 24","окт 24","ноя 24","дек 24","янв 25","фев 25","мар 25","апр 25"]

affected  = [420,480,510,530,500,470,490,540,520,480]
resolved  = [600,650,680,720,750,790,820,850]
repeat_c  = [6.2,6.4,6.1,5.9,6.0,5.8,5.7,5.9,5.7,5.6]
speed_val = [1400,1430,1460,1490,1510,1525,1540,1560,1580,1600]

bmo_weeks  = ["нед 1","нед 2","нед 3","нед 4","нед 5","нед 6","нед 7","нед 8"]
bmo_vsp    = [9700,9800,10100,10300,10500,10200,10400,10500]
bmo_tasks  = [1300,1350,1400,1420,1450,1430,1460,1525]
bmo_share  = [22,26,24,22,25,23,26,24]
bmo_speed2 = [18,20,17,19,21,18,20,19]

funnel_stages = ["Всего отклонений","Выявлено в системе","Передано на устранение","Устранено"]
funnel_vals   = [1600, 1200, 950, 850]
funnel_parts  = {
    "Всего отклонений":       [600, 600, 400],
    "Выявлено в системе":     [460, 440, 300],
    "Передано на устранение": [360, 350, 240],
    "Устранено":              [320, 310, 220],
}

# ── глобальный CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
/* убираем padding-top у основного блока */
.block-container { padding-top: 1rem !important; }

/* кнопки навигации */
.nav-wrap { display: flex; gap: 0; margin-bottom: 0; }
.nav-btn {
    padding: 9px 32px;
    font-size: 14px;
    font-weight: 600;
    border-radius: 8px;
    border: 2px solid #1D5FA5;
    cursor: pointer;
    white-space: nowrap;
    line-height: 1;
    margin-right: 8px;
}
.nav-active   { background: #1D5FA5; color: #fff; }
.nav-inactive { background: #fff;    color: #1D5FA5; }
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "summary"

# ── кнопки-переключатели ──────────────────────────────────────────────────
c1, c2, _ = st.columns([1.4, 1.8, 8])
with c1:
    if st.button("ИС Статус. Summary", key="btn_s"):
        st.session_state.page = "summary"
        st.rerun()
with c2:
    if st.button("Влияние на бизнес. БМО", key="btn_b"):
        st.session_state.page = "bmo"
        st.rerun()

# Окрашиваем кнопки через CSS nth-child по ключу активной страницы
p = st.session_state.page
if p == "summary":
    s_bg, s_cl, b_bg, b_cl = "#1D5FA5","#fff","#fff","#1D5FA5"
else:
    s_bg, s_cl, b_bg, b_cl = "#fff","#1D5FA5","#1D5FA5","#fff"

st.markdown(f"""
<style>
section[data-testid="stMain"] div[data-testid="column"]:nth-child(1) button {{
    background-color:{s_bg}!important; color:{s_cl}!important;
    border:2px solid #1D5FA5!important; border-radius:8px!important;
    font-weight:600!important; padding:9px 18px!important;
}}
section[data-testid="stMain"] div[data-testid="column"]:nth-child(2) button {{
    background-color:{b_bg}!important; color:{b_cl}!important;
    border:2px solid #1D5FA5!important; border-radius:8px!important;
    font-weight:600!important; padding:9px 18px!important;
}}
</style>
""", unsafe_allow_html=True)

st.markdown("<hr style='margin:8px 0 16px;border:none;border-top:1px solid #ddd;'>",
            unsafe_allow_html=True)

# ── хелперы ────────────────────────────────────────────────────────────────
BG   = "rgba(0,0,0,0)"
GRID = "rgba(128,128,128,0.15)"

def L(h=210, t=14, r=8, l=42, b=32):
    """Базовые параметры layout — возвращает dict, никогда не распаковываем с доп-ключами."""
    return dict(
        height=h,
        margin=dict(t=t, b=b, l=l, r=r),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=11, color="#888780"),
        xaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        showlegend=False,
    )

def metric_card(label, value, bg=BLUE):
    st.markdown(
        f'<div style="background:{bg};border-radius:10px;padding:10px 14px;'
        f'color:#fff;margin-bottom:10px;">'
        f'<div style="font-size:11px;opacity:.85;line-height:1.3;margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:20px;font-weight:500;">{value}</div></div>',
        unsafe_allow_html=True)

def chart_title(txt):
    st.markdown(
        f'<p style="font-size:16px;font-weight:600;margin:0 0 2px;color:{BLUE};">{txt}</p>',
        unsafe_allow_html=True)

def build_funnel_svg():
    W, H     = 520, 460
    label_w  = 185
    bar_area = W - label_w - 60
    max_val  = funnel_vals[0]
    row_h, gap, top_m = 68, 14, 16

    out = []
    for i, stage in enumerate(funnel_stages):
        total     = funnel_vals[i]
        top_frac  = (funnel_vals[i-1] / max_val) if i > 0 else 1.0
        bot_frac  = total / max_val
        bw_top    = bar_area * top_frac
        bw_bot    = bar_area * bot_frac
        cx        = label_w + bar_area / 2
        yt        = top_m + i * (row_h + gap)
        yb        = yt + row_h

        xl_top, xr_top = cx - bw_top/2, cx + bw_top/2
        xl_bot, xb_bot = cx - bw_bot/2, cx + bw_bot/2

        parts      = funnel_parts[stage]
        total_p    = sum(parts)
        cur_top    = xl_top
        cur_bot    = xl_bot

        for j in range(3):
            frac_j   = parts[j] / total_p
            sw_top   = bw_top * frac_j
            sw_bot   = bw_bot * frac_j
            pts      = (f"{cur_top:.1f},{yt} {cur_top+sw_top:.1f},{yt} "
                        f"{cur_bot+sw_bot:.1f},{yb} {cur_bot:.1f},{yb}")
            tx       = cur_top + sw_top/2
            ty       = yt + row_h/2 + 5
            out.append(
                f'<polygon points="{pts}" fill="{FUNNEL_COLORS_LIST[j]}" '
                f'opacity="0.88" stroke="white" stroke-width="1.5"/>')
            out.append(
                f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" '
                f'font-size="12" font-weight="600" fill="white">{parts[j]}</text>')
            cur_top += sw_top
            cur_bot += sw_bot

        # подпись этапа слева
        mid_y = yt + row_h/2 + 5
        out.append(
            f'<text x="{label_w-10}" y="{mid_y:.1f}" text-anchor="end" '
            f'font-size="12" fill="#444">{stage}</text>')
        # итог справа
        out.append(
            f'<text x="{cx+bw_bot/2+10}" y="{mid_y:.1f}" text-anchor="start" '
            f'font-size="13" font-weight="700" fill="#222">{total}</text>')

    # легенда
    lx, ly = label_w, H - 28
    for k, (lbl, clr) in enumerate(zip(FUNNEL_LABELS, FUNNEL_COLORS_LIST)):
        out.append(f'<rect x="{lx+k*90}" y="{ly}" width="13" height="13" '
                   f'fill="{clr}" rx="3"/>')
        out.append(f'<text x="{lx+k*90+17}" y="{ly+11}" font-size="12" fill="#444">{lbl}</text>')

    return (f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" '
            f'style="font-family:sans-serif;">{"".join(out)}</svg>')


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
if p == "summary":

    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        m1, g1 = st.columns([1, 2])
        with m1:
            metric_card("Кол-во видов отклонений", "16 шт.")
            metric_card("Кол-во человек с отклонениями", "1 000 чел.")
        with g1:
            chart_title("Динамика пораженности по неделям")
            f1 = go.Figure(go.Bar(x=weeks, y=affected, marker_color=BAR_B, opacity=.85))
            f1.update_layout(**L())
            st.plotly_chart(f1, use_container_width=True)

        st.divider()

        m2, g2 = st.columns([1, 2])
        with m2:
            metric_card("Кол-во ВСП с отклонениями", "850 шт.")
            metric_card("Кол-во задач / хроник", "1 600 / 1 525")
        with g2:
            chart_title("Доля устранённых отклонений (8 нед.)")
            f2 = go.Figure(go.Bar(x=weeks8, y=resolved, marker_color=BAR_T, opacity=.85))
            f2.update_layout(**L())
            st.plotly_chart(f2, use_container_width=True)

    with col_r:
        g3, m3 = st.columns([2, 1])
        with g3:
            chart_title("Средний счётчик повторов")
            f3 = go.Figure(go.Scatter(x=weeks, y=repeat_c, mode="lines+markers",
                                      line=dict(color=LINE_C, width=2), marker=dict(size=6)))
            f3.update_layout(**L())
            st.plotly_chart(f3, use_container_width=True)
        with m3:
            metric_card("Доля устранённых", "850 шт.", TEAL)

        st.divider()

        g4, m4 = st.columns([2, 1])
        with g4:
            chart_title("Скорость устранения по неделям")
            f4 = go.Figure(go.Scatter(x=weeks, y=speed_val, mode="lines+markers",
                                      line=dict(color=LINE_A, width=2), marker=dict(size=6)))
            f4.update_layout(**L())
            st.plotly_chart(f4, use_container_width=True)
        with m4:
            metric_card("Скорость устранения", "1 600 / 1 525", TEAL)

    st.caption("* Методологию расчёта разработали. Считаем за 4 недели.")


# ══════════════════════════════════════════════════════════════════════════
# БМО
# ══════════════════════════════════════════════════════════════════════════
else:
    mc = st.columns(6)
    labels_vals = [("Доля по Банку","50,1%","+0,2%"),("Целевое значение","—",None),
                   ("Счётчик повторов","5,6 нед.","-0,2"),("Задач / хроник","—",None),
                   ("Доля устранённых","—",None),("Скорость устранения","—",None)]
    for col, (lbl, val, delta) in zip(mc, labels_vals):
        with col:
            st.metric(lbl, val, delta)

    st.divider()

    graphs_col, funnel_col = st.columns([11, 9], gap="large")

    with graphs_col:
        # ── График 1: ВСП + задачи (двойная ось) ──
        # Полностью ручной layout — НЕ используем L() чтобы избежать конфликта yaxis2
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
            yaxis2=dict(overlaying="y", side="right", gridcolor="rgba(0,0,0,0)",
                        tickfont=dict(size=10),
                        title=dict(text="Задачи", font=dict(size=10))),
        )
        st.plotly_chart(f5, use_container_width=True)

        # ── График 2: доля + скорость (одна ось) ──
        # Полностью ручной layout — НЕ используем L() со смешанными kwargs
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
