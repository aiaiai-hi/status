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

FUNNEL_COLORS = {
    "Тип А": "#378ADD",
    "Тип Б": "#1D9E75",
    "Тип В": "#BA7517",
}

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

funnel_stages = [
    "Всего отклонений",
    "Выявлено в системе",
    "Передано на устранение",
    "Устранено",
]
funnel_vals  = [1600, 1200, 950, 850]
funnel_parts = {
    "Всего отклонений":       {"Тип А": 600, "Тип Б": 600, "Тип В": 400},
    "Выявлено в системе":     {"Тип А": 460, "Тип Б": 440, "Тип В": 300},
    "Передано на устранение": {"Тип А": 360, "Тип Б": 350, "Тип В": 240},
    "Устранено":              {"Тип А": 320, "Тип Б": 310, "Тип В": 220},
}

# ── CSS: кастомные кнопки-переключатели ───────────────────────────────────
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div { align-items: center; }

.nav-btn-active {
    background-color: #1D5FA5;
    color: white;
    border: 2px solid #1D5FA5;
    border-radius: 8px;
    padding: 8px 28px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    width: 100%;
}
.nav-btn-inactive {
    background-color: white;
    color: #1D5FA5;
    border: 2px solid #1D5FA5;
    border-radius: 8px;
    padding: 8px 28px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    width: 100%;
}
.nav-btn-active:hover { background-color: #174d8a; }
.nav-btn-inactive:hover { background-color: #e8f0fb; }

/* убираем дефолтные отступы вокруг st.button */
div.stButton > button {
    border-radius: 8px;
    padding: 8px 0;
    font-size: 15px;
    font-weight: 600;
    width: 100%;
    transition: 0.15s;
}
div.stButton > button:focus { outline: none; box-shadow: none; }
</style>
""", unsafe_allow_html=True)

# ── навигация через session_state + кнопки ────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "summary"

btn_col1, btn_col2, spacer = st.columns([1.6, 1.6, 5])

with btn_col1:
    if st.button("ИС Статус. Summary",
                 key="btn_summary",
                 type="primary" if st.session_state.page == "summary" else "secondary"):
        st.session_state.page = "summary"
        st.rerun()

with btn_col2:
    if st.button("Влияние на бизнес. БМО",
                 key="btn_bmo",
                 type="primary" if st.session_state.page == "bmo" else "secondary"):
        st.session_state.page = "bmo"
        st.rerun()

# дополнительный CSS для активной/неактивной кнопки
active_page = st.session_state.page
st.markdown(f"""
<style>
div[data-testid="column"]:nth-child(1) div.stButton > button {{
    background-color: {"#1D5FA5" if active_page == "summary" else "white"};
    color: {"white" if active_page == "summary" else "#1D5FA5"};
    border: 2px solid #1D5FA5;
}}
div[data-testid="column"]:nth-child(2) div.stButton > button {{
    background-color: {"#1D5FA5" if active_page == "bmo" else "white"};
    color: {"white" if active_page == "bmo" else "#1D5FA5"};
    border: 2px solid #1D5FA5;
}}
</style>
""", unsafe_allow_html=True)

st.markdown("<hr style='margin:8px 0 18px;border:none;border-top:1px solid #ddd;'>",
            unsafe_allow_html=True)

# ── хелперы ────────────────────────────────────────────────────────────────
def simple_layout(height=210):
    return dict(
        height=height,
        margin=dict(t=14, b=32, l=42, r=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11, color="#888780"),
        xaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=10)),
        showlegend=False,
    )

def metric_card(label, value, bg=BLUE):
    st.markdown(
        f"""<div style="background:{bg};border-radius:10px;padding:10px 14px;
                color:#fff;margin-bottom:10px;">
          <div style="font-size:11px;opacity:0.85;line-height:1.3;margin-bottom:4px;">{label}</div>
          <div style="font-size:20px;font-weight:500;">{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )

def chart_title(text):
    st.markdown(
        f"<p style='font-size:16px;font-weight:600;margin:0 0 2px 0;"
        f"color:#1D5FA5;'>{text}</p>",
        unsafe_allow_html=True,
    )

def build_funnel_svg():
    """
    Рисует воронку в виде трапеций, сужающихся книзу.
    Каждая ступень — горизонтальный stacked bar в форме трапеции (SVG polygon).
    """
    W = 520        # ширина SVG
    H = 480        # высота SVG
    label_w = 170  # ширина зоны подписей слева
    bar_area = W - label_w - 60  # ширина зоны баров
    n = len(funnel_stages)
    row_h = 72
    gap = 14
    top_margin = 20

    max_val = funnel_vals[0]

    # Собираем полигоны для каждой ступени
    shapes_html = []
    legend_items = []

    # Легенда
    lx = label_w
    ly = H - 36
    for i, (part, color) in enumerate(FUNNEL_COLORS.items()):
        legend_items.append(
            f'<rect x="{lx + i*90}" y="{ly}" width="14" height="14" fill="{color}" rx="3"/>'
            f'<text x="{lx + i*90 + 18}" y="{ly + 11}" font-size="12" fill="#444">{part}</text>'
        )

    for i, stage in enumerate(funnel_stages):
        total = funnel_vals[i]
        # ширина трапеции для этой ступени (сужается книзу)
        frac = total / max_val
        top_frac = funnel_vals[i - 1] / max_val if i > 0 else 1.0

        bar_w_top = bar_area * top_frac
        bar_w_bot = bar_area * frac

        cx = label_w + bar_area / 2  # центр по X

        y_top = top_margin + i * (row_h + gap)
        y_bot = y_top + row_h

        x_left_top  = cx - bar_w_top / 2
        x_right_top = cx + bar_w_top / 2
        x_left_bot  = cx - bar_w_bot / 2
        x_right_bot = cx + bar_w_bot / 2

        # Разбиваем горизонтально на части
        parts = funnel_parts[stage]
        part_keys = list(parts.keys())
        part_vals = [parts[k] for k in part_keys]
        total_parts = sum(part_vals)

        cursor_top = x_left_top
        cursor_bot = x_left_bot

        for j, part in enumerate(part_keys):
            frac_part = part_vals[j] / total_parts
            seg_w_top = bar_w_top * frac_part
            seg_w_bot = bar_w_bot * frac_part

            pts = (
                f"{cursor_top:.1f},{y_top} "
                f"{cursor_top + seg_w_top:.1f},{y_top} "
                f"{cursor_bot + seg_w_bot:.1f},{y_bot} "
                f"{cursor_bot:.1f},{y_bot}"
            )
            color = list(FUNNEL_COLORS.values())[j]

            shapes_html.append(
                f'<polygon points="{pts}" fill="{color}" opacity="0.88" '
                f'stroke="white" stroke-width="1.5"/>'
            )

            # текст внутри сегмента
            tx = cursor_top + seg_w_top / 2
            ty = y_top + row_h / 2 + 5
            shapes_html.append(
                f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" '
                f'font-size="12" font-weight="600" fill="white">{part_vals[j]}</text>'
            )

            cursor_top += seg_w_top
            cursor_bot += seg_w_bot

        # подпись этапа слева
        ty_label = y_top + row_h / 2 + 5
        shapes_html.append(
            f'<text x="{label_w - 10}" y="{ty_label:.1f}" text-anchor="end" '
            f'font-size="12" fill="#444">{stage}</text>'
        )

        # итоговое значение справа
        shapes_html.append(
            f'<text x="{cx + bar_w_bot/2 + 10}" y="{ty_label:.1f}" '
            f'text-anchor="start" font-size="13" font-weight="700" fill="#222">{total}</text>'
        )

    svg = f"""
    <svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg"
         style="font-family:sans-serif;">
      {''.join(shapes_html)}
      {''.join(legend_items)}
    </svg>
    """
    return svg


# ══════════════════════════════════════════════════════════════════════════
# СТРАНИЦА 1 — SUMMARY
# ══════════════════════════════════════════════════════════════════════════
if active_page == "summary":

    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        m1, g1 = st.columns([1, 2])
        with m1:
            metric_card("Кол-во видов отклонений", "16 шт.", BLUE)
            metric_card("Кол-во человек с отклонениями", "1 000 чел.", BLUE)
        with g1:
            chart_title("Динамика пораженности по неделям")
            fig1 = go.Figure(go.Bar(x=weeks, y=affected, marker_color=BAR_B, opacity=0.85))
            fig1.update_layout(**simple_layout())
            st.plotly_chart(fig1, use_container_width=True)

        st.divider()

        m2, g2 = st.columns([1, 2])
        with m2:
            metric_card("Кол-во ВСП с отклонениями", "850 шт.", BLUE)
            metric_card("Кол-во задач / хроник", "1 600 / 1 525", BLUE)
        with g2:
            chart_title("Доля устранённых отклонений (8 нед.)")
            fig2 = go.Figure(go.Bar(x=weeks8, y=resolved, marker_color=BAR_T, opacity=0.85))
            fig2.update_layout(**simple_layout())
            st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        g3, m3 = st.columns([2, 1])
        with g3:
            chart_title("Средний счётчик повторов")
            fig3 = go.Figure(go.Scatter(
                x=weeks, y=repeat_c, mode="lines+markers",
                line=dict(color=LINE_C, width=2), marker=dict(size=6),
            ))
            fig3.update_layout(**simple_layout())
            st.plotly_chart(fig3, use_container_width=True)
        with m3:
            metric_card("Доля устранённых отклонений", "850 шт.", TEAL)

        st.divider()

        g4, m4 = st.columns([2, 1])
        with g4:
            chart_title("Скорость устранения по неделям")
            fig4 = go.Figure(go.Scatter(
                x=weeks, y=speed_val, mode="lines+markers",
                line=dict(color=LINE_A, width=2), marker=dict(size=6),
            ))
            fig4.update_layout(**simple_layout())
            st.plotly_chart(fig4, use_container_width=True)
        with m4:
            metric_card("Скорость устранения", "1 600 / 1 525", TEAL)

    st.caption("* Методологию расчёта разработали. Считаем за 4 недели.")


# ══════════════════════════════════════════════════════════════════════════
# СТРАНИЦА 2 — БМО
# ══════════════════════════════════════════════════════════════════════════
else:
    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
    with mc1: st.metric("Доля по Банку", "50,1%", "+0,2%")
    with mc2: st.metric("Целевое значение", "—")
    with mc3: st.metric("Счётчик повторов", "5,6 нед.", "-0,2")
    with mc4: st.metric("Задач / хроник", "—")
    with mc5: st.metric("Доля устранённых", "—")
    with mc6: st.metric("Скорость устранения", "—")

    st.divider()

    # [графики 55%] | [воронка 45%]
    graphs_col, funnel_col = st.columns([11, 9], gap="large")

    with graphs_col:
        # График 1 — двойная ось (без распаковки simple_layout)
        chart_title("Динамика ВСП и задач по неделям")
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            name="ВСП", x=bmo_weeks, y=bmo_vsp,
            marker_color=BAR_B, opacity=0.8, yaxis="y1",
        ))
        fig5.add_trace(go.Scatter(
            name="Задачи", x=bmo_weeks, y=bmo_tasks,
            mode="lines+markers",
            line=dict(color=LINE_C, width=2),
            marker=dict(size=5),
            yaxis="y2",
        ))
        fig5.update_layout(
            height=230,
            margin=dict(t=10, b=32, l=42, r=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#888780"),
            showlegend=True,
            legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
            xaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=10)),
            yaxis=dict(
                gridcolor="rgba(128,128,128,0.15)",
                tickfont=dict(size=10),
                title=dict(text="ВСП", font=dict(size=10)),
            ),
            yaxis2=dict(
                overlaying="y", side="right",
                gridcolor="rgba(0,0,0,0)",
                tickfont=dict(size=10),
                title=dict(text="Задачи", font=dict(size=10)),
            ),
        )
        st.plotly_chart(fig5, use_container_width=True)

        # График 2 — без двойной оси, можно распаковать
        chart_title("Доля и скорость устранения")
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            name="Доля (%)", x=bmo_weeks, y=bmo_share,
            marker_color=LINE_P, opacity=0.85,
        ))
        fig6.add_trace(go.Scatter(
            name="Скорость", x=bmo_weeks, y=bmo_speed2,
            mode="lines+markers",
            line=dict(color=LINE_A, width=2),
            marker=dict(size=5),
        ))
        fig6.update_layout(
            **simple_layout(height=230),
            showlegend=True,
            legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
            barmode="overlay",
        )
        st.plotly_chart(fig6, use_container_width=True)

    with funnel_col:
        chart_title("Воронка метрик БА по БМО")
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        svg = build_funnel_svg()
        st.markdown(svg, unsafe_allow_html=True)

    st.caption("* Заменяем термин «Срок жизни». Методологию расчёта разработали. За 4 недели.")
