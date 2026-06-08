import streamlit as st
import plotly.graph_objects as go
from datetime import date

st.set_page_config(page_title="ИС Статус. Дэшборд", layout="wide")

# ── фирменная палитра РСХБ ─────────────────────────────────────────────────
BLACK       = "#1A1A1A"
DARK_GREEN  = "#0F4D17"
GREEN       = "#2A7E2E"
LIME        = "#6BB934"
LIME_LIGHT  = "#97D147"
YELLOW      = "#F2C014"
YELLOW_LT   = "#F9D63E"
ORANGE      = "#E07B1B"
ORANGE_LT   = "#F0A040"
GREY_TXT    = "#5F5E5A"
BG          = "rgba(0,0,0,0)"
GRID        = "rgba(0,0,0,0.05)"

CARD_STYLES = {
    "black":      (f"linear-gradient(135deg,{BLACK} 0%,#333333 100%)",       "#fff", YELLOW_LT,  "#FFC2A8"),
    "dark-green": (f"linear-gradient(135deg,{DARK_GREEN} 0%,{GREEN} 100%)",  "#fff", YELLOW_LT,  "#FFC2A8"),
    "green":      (f"linear-gradient(135deg,{GREEN} 0%,#4CA351 100%)",       "#fff", YELLOW_LT,  "#FFC2A8"),
    "lime":       (f"linear-gradient(135deg,{LIME} 0%,{LIME_LIGHT} 100%)",   BLACK,  DARK_GREEN, "#B23A0C"),
    "yellow":     (f"linear-gradient(135deg,{YELLOW} 0%,{YELLOW_LT} 100%)",  BLACK,  DARK_GREEN, "#B23A0C"),
    "orange":     (f"linear-gradient(135deg,{ORANGE} 0%,{ORANGE_LT} 100%)",  "#fff", YELLOW_LT,  "#FFC2A8"),
}

# ── session state ──────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "summary"
p = st.session_state.page

# ── глобальный CSS ─────────────────────────────────────────────────────────
st.markdown(f"""
<style>
.block-container {{ padding-top: 1.5rem !important; max-width: 100% !important; }}

/* кнопки навигации */
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondary"] {{
    white-space: nowrap !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 9px 24px !important;
    border-radius: 8px !important;
}}
button[data-testid="stBaseButton-secondary"] {{
    background-color: #ffffff !important;
    color: {GREEN} !important;
    border: 2px solid {GREEN} !important;
}}
button[data-testid="stBaseButton-secondary"]:hover {{
    background-color: #F0F8E8 !important;
    border-color: {GREEN} !important;
}}
button[data-testid="stBaseButton-primary"] {{
    background-color: {GREEN} !important;
    color: #fff !important;
    border: 2px solid {GREEN} !important;
}}
button[data-testid="stBaseButton-primary"]:hover {{
    background-color: {DARK_GREEN} !important;
    border-color: {DARK_GREEN} !important;
}}

/* поля даты — лаймовая рамка */
div[data-baseweb="input"] > div {{
    border-radius: 6px !important;
    border-color: #B6D87C !important;
}}
</style>
""", unsafe_allow_html=True)

# ── заголовок ──────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='font-size:28px;font-weight:600;color:{BLACK};margin:0 0 12px;letter-spacing:-0.3px;'>"
    "ИС Статус. Дэшборд</h1>",
    unsafe_allow_html=True,
)

# ── навигация ──────────────────────────────────────────────────────────────
n1, n2, _ = st.columns([0.9, 1.9, 7])
with n1:
    if st.button("Саммари", key="nav_s",
                 type="primary" if p == "summary" else "secondary",
                 use_container_width=True):
        st.session_state.page = "summary"; st.rerun()
with n2:
    if st.button("Влияние на бизнес. БМО", key="nav_b",
                 type="primary" if p == "bmo" else "secondary",
                 use_container_width=True):
        st.session_state.page = "bmo"; st.rerun()

st.markdown("<hr style='margin:10px 0 14px;border:none;border-top:1px solid #E0E0DA;'>",
            unsafe_allow_html=True)

# ── хелперы ────────────────────────────────────────────────────────────────
def metric_card(label, value, delta=None, delta_dir="up", style="green"):
    bg, fg, up_col, down_col = CARD_STYLES[style]
    delta_html = ""
    if delta:
        col = up_col if delta_dir == "up" else down_col
        arrow = "▲" if delta_dir == "up" else "▼"
        delta_html = (f'<div style="font-size:11px;color:{col};font-weight:600;margin-top:4px;">'
                      f'{arrow} {delta}</div>')
    st.markdown(f"""
    <div style="background:{bg};border-radius:12px;padding:11px 13px 12px;
                color:{fg};box-shadow:0 1px 4px rgba(0,0,0,0.10);
                min-height:108px;display:flex;flex-direction:column;
                margin-bottom:8px;">
      <div style="font-size:11px;opacity:0.9;line-height:1.25;font-weight:500;margin-bottom:6px;">
        {label}
      </div>
      <div style="font-size:22px;font-weight:600;letter-spacing:-0.5px;">{value}</div>
      {delta_html}
    </div>""", unsafe_allow_html=True)

def metric_pair(label, v1, d1, v2, d2, style="yellow"):
    bg, fg, up_col, down_col = CARD_STYLES[style]
    st.markdown(f"""
    <div style="background:{bg};border-radius:12px;padding:11px 13px 12px;
                color:{fg};box-shadow:0 1px 4px rgba(0,0,0,0.10);
                min-height:108px;display:flex;flex-direction:column;
                margin-bottom:8px;">
      <div style="font-size:11px;opacity:0.85;line-height:1.25;font-weight:500;margin-bottom:6px;">{label}</div>
      <div style="font-size:20px;font-weight:600;letter-spacing:-0.5px;">{v1}</div>
      <div style="font-size:10px;color:{up_col};font-weight:600;margin-top:2px;">▲ {d1}</div>
      <div style="font-size:15px;font-weight:600;letter-spacing:-0.3px;margin-top:4px;">/ {v2}</div>
      <div style="font-size:10px;color:{up_col};font-weight:600;margin-top:2px;">▲ {d2}</div>
    </div>""", unsafe_allow_html=True)

def chart_title(t):
    st.markdown(
        f'<p style="font-size:13px;font-weight:600;color:{BLACK};margin:0 0 4px;">{t}</p>',
        unsafe_allow_html=True)

def base_layout(h=210, right=8, dual_y=False):
    """Базовый layout — без распаковки если есть doп-параметры."""
    return dict(
        height=h,
        margin=dict(t=14, b=32, l=42, r=right),
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(size=10, color=GREY_TXT),
        showlegend=False,
        xaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
    )


# ══════════════════════════════════════════════════════════════════════════
# СТРАНИЦА: САММАРИ
# ══════════════════════════════════════════════════════════════════════════
if p == "summary":
    # ── даты ───────────────────────────────────────────────────────────
    d1, d2, _ = st.columns([1.2, 1.2, 6])
    with d1:
        st.date_input("Период с", value=date(2026, 3, 20),
                      format="DD.MM.YYYY", key="d_from")
    with d2:
        st.date_input("по", value=date(2026, 4, 10),
                      format="DD.MM.YYYY", key="d_to")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    weeks  = ["20.03", "27.03", "03.04", "10.04"]
    months = ["янв 26", "фев 26", "мар 26", "апр 26"]

    # ════ Q1 + Q2 ════
    q1, q2 = st.columns([1, 1], gap="large")

    # Q1: метрики слева | график справа
    with q1:
        m, g = st.columns([1, 2.2], gap="small")
        with m:
            metric_card("Кол-во видов отклонений", "16", "+6.7%", "up", "dark-green")
            metric_card("Кол-во ВСП с отклонениями", "850", "+3.2%", "up", "green")
        with g:
            chart_title("Пораженность / Счётчик повторов")
            f1 = go.Figure()
            f1.add_trace(go.Bar(name="Пораженность", x=weeks, y=[120, 135, 128, 142],
                                marker_color=GREEN, opacity=0.9,
                                hovertemplate="<b>%{x}</b><br>Пораженность: %{y}<extra></extra>"))
            f1.add_trace(go.Bar(name="Счётчик повторов", x=weeks, y=[5.4, 5.8, 5.6, 5.6],
                                marker_color=YELLOW, opacity=0.9,
                                hovertemplate="<b>%{x}</b><br>Счётчик: %{y}<extra></extra>"))
            lay1 = base_layout(h=220)
            lay1.update(
                barmode="group",
                bargap=0.25, bargroupgap=0.08,
                showlegend=True,
                legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
                xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
            )
            f1.update_layout(**lay1)
            st.plotly_chart(f1, use_container_width=True, config={"displayModeBar": False})

    # Q2: график слева | метрика справа
    with q2:
        g, m = st.columns([2.2, 1], gap="small")
        with g:
            chart_title("Динамика видов отклонений (3 мес.)")
            f2 = go.Figure(go.Scatter(
                x=months, y=[14, 15, 16, 16], mode="lines+markers",
                line=dict(color=GREEN, width=2.5),
                marker=dict(size=6, color=GREEN),
                fill="tozeroy", fillcolor="rgba(42,126,46,0.14)",
                hovertemplate="<b>%{x}</b><br>Виды: %{y}<extra></extra>",
            ))
            lay2 = base_layout(h=220)
            lay2["xaxis"] = dict(type="category", gridcolor=GRID, tickfont=dict(size=10))
            f2.update_layout(**lay2)
            st.plotly_chart(f2, use_container_width=True, config={"displayModeBar": False})
        with m:
            metric_card("Доля устранённых отклонений", "50.1%", "+0.2%", "up", "orange")

    st.markdown("<hr style='margin:8px 0 12px;border:none;border-top:1px solid #E0E0DA;'>",
                unsafe_allow_html=True)

    # ════ Q3 + Q4 ════
    q3, q4 = st.columns([1, 1], gap="large")

    # Q3: метрики слева | график справа
    with q3:
        m, g = st.columns([1, 2.2], gap="small")
        with m:
            metric_card("Кол-во человек с отклонениями", "1 000", "-2.1%", "down", "black")
            metric_pair("Задачи / Хроники", "1 600", "+4%", "1 525", "+2%", "yellow")
        with g:
            chart_title("Задачи / Хроники по неделям")
            f3 = go.Figure()
            f3.add_trace(go.Bar(name="Задачи", x=weeks, y=[1450, 1520, 1580, 1600],
                                marker_color=DARK_GREEN, opacity=0.9,
                                hovertemplate="<b>%{x}</b><br>Задачи: %{y:,}<extra></extra>"))
            f3.add_trace(go.Bar(name="Хроники", x=weeks, y=[1400, 1465, 1500, 1525],
                                marker_color=LIME, opacity=0.9,
                                hovertemplate="<b>%{x}</b><br>Хроники: %{y:,}<extra></extra>"))
            lay3 = base_layout(h=220)
            lay3.update(
                barmode="group",
                bargap=0.25, bargroupgap=0.08,
                showlegend=True,
                legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
                xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
            )
            f3.update_layout(**lay3)
            st.plotly_chart(f3, use_container_width=True, config={"displayModeBar": False})

    # Q4: график слева | метрика справа
    with q4:
        g, m = st.columns([2.2, 1], gap="small")
        with g:
            chart_title("Скорость устранения (3 мес.)")
            f4 = go.Figure(go.Scatter(
                x=months, y=[5.8, 5.7, 5.7, 5.6], mode="lines+markers",
                line=dict(color=ORANGE, width=2.5),
                marker=dict(size=6, color=ORANGE),
                fill="tozeroy", fillcolor="rgba(224,123,27,0.14)",
                hovertemplate="<b>%{x}</b><br>Скорость: %{y}<extra></extra>",
            ))
            lay4 = base_layout(h=220)
            lay4["xaxis"] = dict(type="category", gridcolor=GRID, tickfont=dict(size=10))
            f4.update_layout(**lay4)
            st.plotly_chart(f4, use_container_width=True, config={"displayModeBar": False})
        with m:
            metric_card("Скорость устранения", "5.6 нед.", "-0.2", "down", "lime")

    st.caption("Данные: Metrics.xlsx · обновлено 10.04.2026")


# ══════════════════════════════════════════════════════════════════════════
# СТРАНИЦА: БМО
# ══════════════════════════════════════════════════════════════════════════
else:
    d1, d2, _ = st.columns([1.2, 1.2, 6])
    with d1:
        st.date_input("Период с", value=date(2026, 3, 20),
                      format="DD.MM.YYYY", key="bd_from")
    with d2:
        st.date_input("по", value=date(2026, 4, 10),
                      format="DD.MM.YYYY", key="bd_to")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── 6 метрик-карточек в одну строку ────────────────────────────────
    def bmo_card(label, value, delta, delta_dir, accent):
        col = GREEN if delta_dir == "up" else ORANGE
        arrow = "▲" if delta_dir == "up" else "▼"
        return f"""
        <div style="background:#fff;border:0.5px solid #E0E0DA;border-radius:10px;
                    padding:9px 11px;border-left:3px solid {accent};min-height:78px;">
          <div style="font-size:10px;color:{GREY_TXT};line-height:1.2;margin-bottom:4px;">{label}</div>
          <div style="font-size:18px;font-weight:600;color:{BLACK};">{value}</div>
          <div style="font-size:10px;font-weight:600;color:{col};margin-top:2px;">
            {arrow} {delta}</div>
        </div>"""

    cards = [
        ("Доля по Банку", "50.1%", "+0.2%", "up", GREEN),
        ("Целевое значение", "52%", "цель", "up", "#5F5E5A"),
        ("Счётчик повторов", "5.6 нед.", "-0.2", "down", ORANGE),
        ("Задачи / хроники", "1 600", "+4%", "up", YELLOW),
        ("Доля устранённых", "53%", "+1.1%", "up", LIME),
        ("Скорость устранения", "82%", "-2%", "down", DARK_GREEN),
    ]
    cols = st.columns(6)
    for c, (lbl, v, d, dr, ac) in zip(cols, cards):
        with c:
            st.markdown(bmo_card(lbl, v, d, dr, ac), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── основная секция: [2 графика] | [воронка] ───────────────────────
    bmo_weeks = ["нед 1","нед 2","нед 3","нед 4","нед 5","нед 6","нед 7","нед 8"]

    g_col, f_col = st.columns([1.4, 1], gap="large")

    with g_col:
        # ── График 1: ВСП + Задачи (двойная ось) ──
        chart_title("Динамика ВСП и задач по неделям")
        f5 = go.Figure()
        f5.add_trace(go.Bar(
            name="ВСП", x=bmo_weeks,
            y=[9700, 9800, 10100, 10300, 10500, 10200, 10400, 10500],
            marker_color=GREEN, opacity=0.85, yaxis="y1",
            hovertemplate="<b>%{x}</b><br>ВСП: %{y:,}<extra></extra>",
        ))
        f5.add_trace(go.Scatter(
            name="Задачи", x=bmo_weeks,
            y=[1300, 1350, 1400, 1420, 1450, 1430, 1460, 1525],
            mode="lines+markers",
            line=dict(color=ORANGE, width=2.5),
            marker=dict(size=5, color=ORANGE), yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Задачи: %{y:,}<extra></extra>",
        ))
        f5.update_layout(
            height=210,
            margin=dict(t=10, b=30, l=42, r=46),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=10, color=GREY_TXT),
            barmode="group", bargap=0.3,
            showlegend=True,
            legend=dict(orientation="h", y=1.14, x=0, font=dict(size=10)),
            xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=10),
                       title=dict(text="ВСП", font=dict(size=10, color=GREY_TXT))),
            yaxis2=dict(overlaying="y", side="right",
                        gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10),
                        title=dict(text="Задачи", font=dict(size=10, color=GREY_TXT))),
        )
        st.plotly_chart(f5, use_container_width=True, config={"displayModeBar": False})

        # ── График 2: Доля + Скорость ──
        chart_title("Доля и скорость устранения")
        f6 = go.Figure()
        f6.add_trace(go.Bar(
            name="Доля (%)", x=bmo_weeks, y=[22, 26, 24, 22, 25, 23, 26, 24],
            marker_color=LIME, opacity=0.9,
            hovertemplate="<b>%{x}</b><br>Доля: %{y}%<extra></extra>",
        ))
        f6.add_trace(go.Scatter(
            name="Скорость", x=bmo_weeks, y=[18, 20, 17, 19, 21, 18, 20, 19],
            mode="lines+markers",
            line=dict(color=YELLOW, width=2.5),
            marker=dict(size=5, color=YELLOW),
            hovertemplate="<b>%{x}</b><br>Скорость: %{y}<extra></extra>",
        ))
        f6.update_layout(
            height=210,
            margin=dict(t=10, b=30, l=42, r=8),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=10, color=GREY_TXT),
            barmode="overlay",
            showlegend=True,
            legend=dict(orientation="h", y=1.14, x=0, font=dict(size=10)),
            xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        )
        st.plotly_chart(f6, use_container_width=True, config={"displayModeBar": False})

    # ── воронка (SVG, трапеции) ──
    with f_col:
        chart_title("Воронка метрик БА по БМО")
        stages = ["Всего", "Выявлено", "Передано", "Устранено"]
        totals = [1600, 1200, 950, 850]
        parts = {
            "Всего":     [600, 600, 400],
            "Выявлено":  [460, 440, 300],
            "Передано":  [360, 350, 240],
            "Устранено": [320, 310, 220],
        }
        COLORS = [GREEN, LIME, YELLOW]
        TEXT_COLORS = ["#fff", BLACK, BLACK]
        W, H = 480, 460
        label_w = 80
        bar_area = W - label_w - 70
        max_val = totals[0]
        row_h, gap, top_m = 70, 14, 18

        out = []
        for i, stage in enumerate(stages):
            total = totals[i]
            top_frac = (totals[i-1] / max_val) if i > 0 else 1.0
            bot_frac = total / max_val
            bw_top = bar_area * top_frac
            bw_bot = bar_area * bot_frac
            cx = label_w + bar_area / 2
            yt = top_m + i * (row_h + gap)
            yb = yt + row_h
            xl_top = cx - bw_top / 2
            xl_bot = cx - bw_bot / 2
            parts_i = parts[stage]
            total_p = sum(parts_i)
            ct, cb = xl_top, xl_bot
            for j in range(3):
                fj = parts_i[j] / total_p
                swt = bw_top * fj
                swb = bw_bot * fj
                pts = (f"{ct:.1f},{yt} {ct+swt:.1f},{yt} "
                       f"{cb+swb:.1f},{yb} {cb:.1f},{yb}")
                tx = ct + swt / 2
                ty = yt + row_h / 2 + 5
                out.append(f'<polygon points="{pts}" fill="{COLORS[j]}" '
                           f'stroke="white" stroke-width="1.5"/>')
                out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" '
                           f'font-size="12" font-weight="600" fill="{TEXT_COLORS[j]}">{parts_i[j]}</text>')
                ct += swt
                cb += swb
            mid_y = yt + row_h / 2 + 5
            out.append(f'<text x="{label_w-8}" y="{mid_y:.1f}" text-anchor="end" '
                       f'font-size="11" fill="#444441">{stage}</text>')
            out.append(f'<text x="{cx+bw_bot/2+8}" y="{mid_y:.1f}" text-anchor="start" '
                       f'font-size="13" font-weight="700" fill="{BLACK}">{total}</text>')

        # легенда
        ly = H - 30
        for k, (lbl, clr) in enumerate(zip(["Тип А", "Тип Б", "Тип В"], COLORS)):
            out.append(f'<rect x="{label_w+k*80}" y="{ly}" width="13" height="13" '
                       f'fill="{clr}" rx="2"/>')
            out.append(f'<text x="{label_w+k*80+18}" y="{ly+11}" font-size="11" '
                       f'fill="#444441">{lbl}</text>')

        svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" '
               f'style="font-family:sans-serif;">{"".join(out)}</svg>')
        st.markdown(svg, unsafe_allow_html=True)

    st.caption("* Данные: Metrics.xlsx · обновлено 10.04.2026")
