import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="ИС Статус. Отчёт", layout="wide")

BLUE   = "#1D5FA5"
TEAL   = "#0F6E56"
BAR_B  = "#378ADD"
BAR_T  = "#1D9E75"
LINE_C = "#D85A30"
LINE_A = "#BA7517"
LINE_P = "#7F77DD"

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
funnel_vals   = [1600,1200,950,850]
funnel_parts  = {
    "Всего отклонений":       {"Тип А":600,"Тип Б":600,"Тип В":400},
    "Выявлено в системе":     {"Тип А":460,"Тип Б":440,"Тип В":300},
    "Передано на устранение": {"Тип А":360,"Тип Б":350,"Тип В":240},
    "Устранено":              {"Тип А":320,"Тип Б":310,"Тип В":220},
}
FUNNEL_COLORS = {"Тип А":"#378ADD","Тип Б":"#1D9E75","Тип В":"#BA7517"}


def base_layout(height=200, title=""):
    return dict(
        height=height,
        margin=dict(t=30, b=32, l=42, r=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11, color="#888780"),
        title_text=title,
        title_font_size=11,
        title_x=0,
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


def section_title(text):
    st.markdown(
        f"""<div style="background:{BLUE};color:#fff;font-size:15px;font-weight:500;
                border-radius:8px;padding:8px 14px;margin-bottom:14px;
                display:inline-block;">{text}</div>""",
        unsafe_allow_html=True,
    )


tab1, tab2 = st.tabs(["ИС Статус. Summary", "Влияние на бизнес. БМО"])


# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — SUMMARY
# Левая колонка:  метрики(слева) + граф1, метрики(слева) + граф2
# Правая колонка: граф3 + метрика(справа), граф4 + метрика(справа)
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    section_title("ИС Статус. Summary")

    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        # блок 1: метрики слева, график справа
        m1, g1 = st.columns([1, 2])
        with m1:
            metric_card("Кол-во видов отклонений", "16 шт.", BLUE)
            metric_card("Кол-во человек с отклонениями", "1 000 чел.", BLUE)
        with g1:
            fig1 = go.Figure(go.Bar(x=weeks, y=affected, marker_color=BAR_B, opacity=0.85))
            fig1.update_layout(**base_layout(title="Динамика пораженности"))
            st.plotly_chart(fig1, use_container_width=True)

        st.divider()

        # блок 2: метрики слева, график справа
        m2, g2 = st.columns([1, 2])
        with m2:
            metric_card("Кол-во ВСП с отклонениями", "850 шт.", BLUE)
            metric_card("Кол-во задач / хроник", "1 600 / 1 525", BLUE)
        with g2:
            fig2 = go.Figure(go.Bar(x=weeks8, y=resolved, marker_color=BAR_T, opacity=0.85))
            fig2.update_layout(**base_layout(title="Доля устранённых (8 нед.)"))
            st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        # блок 3: график слева, метрика справа
        g3, m3 = st.columns([2, 1])
        with g3:
            fig3 = go.Figure(go.Scatter(
                x=weeks, y=repeat_c, mode="lines+markers",
                line=dict(color=LINE_C, width=2), marker=dict(size=6)
            ))
            fig3.update_layout(**base_layout(title="Средний счётчик повторов"))
            st.plotly_chart(fig3, use_container_width=True)
        with m3:
            metric_card("Доля устранённых отклонений", "850 шт.", TEAL)

        st.divider()

        # блок 4: график слева, метрика справа
        g4, m4 = st.columns([2, 1])
        with g4:
            fig4 = go.Figure(go.Scatter(
                x=weeks, y=speed_val, mode="lines+markers",
                line=dict(color=LINE_A, width=2), marker=dict(size=6)
            ))
            fig4.update_layout(**base_layout(title="Скорость устранения"))
            st.plotly_chart(fig4, use_container_width=True)
        with m4:
            metric_card("Скорость устранения", "1 600 / 1 525", TEAL)

    st.caption("* Методологию расчёта разработали. Считаем за 4 недели.")


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — БМО
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    section_title("ИС Статус. Влияние на бизнес. БМО")

    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
    with mc1: st.metric("Доля по Банку", "50,1%", "+0,2%")
    with mc2: st.metric("Целевое значение", "—")
    with mc3: st.metric("Счётчик повторов", "5,6 нед.", "-0,2")
    with mc4: st.metric("Задач / хроник", "—")
    with mc5: st.metric("Доля устранённых", "—")
    with mc6: st.metric("Скорость устранения", "—")

    st.divider()

    graphs_col, funnel_col = st.columns([2, 1])

    with graphs_col:
        # График 1 — ВСП (bars) + задачи (line), два Y-axis
        # Строим вручную без распаковки base_layout, чтобы не конфликтовало
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            name="ВСП", x=bmo_weeks, y=bmo_vsp,
            marker_color=BAR_B, opacity=0.8, yaxis="y1"
        ))
        fig5.add_trace(go.Scatter(
            name="Задачи", x=bmo_weeks, y=bmo_tasks,
            mode="lines+markers",
            line=dict(color=LINE_C, width=2),
            marker=dict(size=5),
            yaxis="y2"
        ))
        fig5.update_layout(
            height=220,
            margin=dict(t=40, b=32, l=42, r=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#888780"),
            title_text="Динамика ВСП и задач по неделям",
            title_font_size=11,
            title_x=0,
            showlegend=True,
            legend=dict(orientation="h", y=1.22, x=0, font=dict(size=10)),
            xaxis=dict(
                gridcolor="rgba(128,128,128,0.15)",
                tickfont=dict(size=10)
            ),
            yaxis=dict(
                gridcolor="rgba(128,128,128,0.15)",
                tickfont=dict(size=10),
                title="ВСП",
                title_font_size=10,
            ),
            yaxis2=dict(
                overlaying="y",
                side="right",
                gridcolor="rgba(0,0,0,0)",
                tickfont=dict(size=10),
                title="Задачи",
                title_font_size=10,
            ),
        )
        st.plotly_chart(fig5, use_container_width=True)

        # График 2 — доля (bars) + скорость (line)
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            name="Доля (%)", x=bmo_weeks, y=bmo_share,
            marker_color=LINE_P, opacity=0.85
        ))
        fig6.add_trace(go.Scatter(
            name="Скорость", x=bmo_weeks, y=bmo_speed2,
            mode="lines+markers",
            line=dict(color=LINE_A, width=2),
            marker=dict(size=5)
        ))
        fig6.update_layout(
            **base_layout(height=220, title="Доля и скорость устранения"),
            showlegend=True,
            legend=dict(orientation="h", y=1.22, x=0, font=dict(size=10)),
            barmode="overlay",
        )
        st.plotly_chart(fig6, use_container_width=True)

    with funnel_col:
        st.markdown(
            "<div style='font-size:12px;color:#5F5E5A;margin-bottom:6px;'>"
            "Воронка метрик БА по БМО</div>",
            unsafe_allow_html=True
        )
        fig_f = go.Figure()
        for part, color in FUNNEL_COLORS.items():
            fig_f.add_trace(go.Bar(
                name=part,
                y=funnel_stages,
                x=[funnel_parts[s][part] for s in funnel_stages],
                orientation="h",
                marker_color=color,
                opacity=0.85,
                text=[str(funnel_parts[s][part]) for s in funnel_stages],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="#fff", size=10),
            ))

        annotations = [
            dict(
                x=funnel_vals[i] + 40, y=stage,
                text=f"<b>{funnel_vals[i]}</b>",
                showarrow=False,
                font=dict(size=11, color="#444441"),
                xanchor="left",
            )
            for i, stage in enumerate(funnel_stages)
        ]

        fig_f.update_layout(
            height=480,
            margin=dict(t=10, b=10, l=10, r=70),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#888780"),
            barmode="stack",
            showlegend=True,
            legend=dict(orientation="h", y=-0.06, x=0, font=dict(size=10)),
            xaxis=dict(visible=False),
            yaxis=dict(
                autorange="reversed",
                tickfont=dict(size=10),
                gridcolor="rgba(0,0,0,0)",
            ),
            annotations=annotations,
        )
        st.plotly_chart(fig_f, use_container_width=True)

    st.caption("* Заменяем термин «Срок жизни». Методологию расчёта разработали. За 4 недели.")
