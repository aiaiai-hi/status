import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta

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

# ══════════════════════════════════════════════════════════════════════════
# ЗАГРУЗКА ДАННЫХ
# ══════════════════════════════════════════════════════════════════════════
import json
import os

XLSX_PATH  = "metrics.xlsx"
JSON_PATH  = "metrics.json"
XLSX_SHEET = "Основное"


def _convert_xlsx_to_json():
    """Читает metrics.xlsx (лист «Основное») и сохраняет metrics.json. Возвращает dict."""
    if not os.path.exists(XLSX_PATH):
        raise FileNotFoundError(
            f"Нет файла {XLSX_PATH} в папке приложения. "
            "Положите его рядом с app.py."
        )

    df_xl = pd.read_excel(XLSX_PATH, sheet_name=XLSX_SHEET)

    needed = ["date_end", "value_s", "metric_id", "metric_name"]
    missing = [c for c in needed if c not in df_xl.columns]
    if missing:
        raise ValueError(
            f"В листе «{XLSX_SHEET}» нет колонок: {missing}. "
            f"Есть только: {list(df_xl.columns)[:15]}"
        )

    df_xl = df_xl[needed].copy()
    df_xl = df_xl.dropna(subset=["date_end", "value_s", "metric_id"])
    df_xl["value_s"]    = pd.to_numeric(df_xl["value_s"], errors="coerce")
    df_xl = df_xl.dropna(subset=["value_s"])
    df_xl["date_end"]   = pd.to_datetime(df_xl["date_end"]).dt.strftime("%Y-%m-%d")
    df_xl["metric_id"]  = df_xl["metric_id"].astype(str)
    df_xl["metric_name"]= df_xl["metric_name"].fillna("").astype(str)

    data = {
        "version": 1,
        "source":  XLSX_PATH,
        "sheet":   XLSX_SHEET,
        "rows":    len(df_xl),
        "records": df_xl.to_dict(orient="records"),
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


@st.cache_data
def load_data():
    """
    Стратегия:
    1. Если metrics.json валидный и не пустой — берём из него.
    2. Иначе — читаем metrics.xlsx, конвертируем в JSON, перезаписываем metrics.json.
    """
    data = None

    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                txt = f.read().strip()
            if txt:
                data = json.loads(txt)
                if not data.get("records"):
                    data = None
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None

    if data is None:
        data = _convert_xlsx_to_json()

    df = pd.DataFrame(data["records"])
    df["date_end"] = pd.to_datetime(df["date_end"])
    df["value_s"]  = pd.to_numeric(df["value_s"], errors="coerce")
    df = df.dropna(subset=["date_end", "value_s", "metric_id"])
    return df

def get_period_value(df, metric_id, date_from, date_to, agg="last"):
    """Значение метрики за период (по умолчанию последнее в диапазоне)."""
    mask = ((df["metric_id"] == metric_id) &
            (df["date_end"] >= pd.Timestamp(date_from)) &
            (df["date_end"] <= pd.Timestamp(date_to)))
    sub = df[mask].sort_values("date_end")
    if sub.empty:
        return None
    if agg == "last":
        return float(sub["value_s"].iloc[-1])
    if agg == "sum":
        return float(sub["value_s"].sum())
    if agg == "mean":
        return float(sub["value_s"].mean())
    return float(sub["value_s"].iloc[-1])

def get_delta(df, metric_id, date_from, date_to):
    """Возвращает (значение, delta_pct, delta_dir) сравнивая с предыдущим периодом (−1 неделя)."""
    cur = get_period_value(df, metric_id, date_from, date_to)
    if cur is None:
        return None, None, None
    # предыдущий период — на неделю раньше с тем же интервалом длиной
    prev_to   = pd.Timestamp(date_from) - timedelta(days=1)
    prev_from = prev_to - (pd.Timestamp(date_to) - pd.Timestamp(date_from))
    prev = get_period_value(df, metric_id, prev_from.date(), prev_to.date())
    if prev is None or prev == 0:
        return cur, None, None
    pct = (cur - prev) / prev * 100
    direction = "up" if pct >= 0 else "down"
    return cur, abs(pct), direction

def fmt_num(v, suffix="", decimals=0):
    if v is None: return "—"
    if decimals == 0:
        return f"{int(round(v)):,}".replace(",", " ") + suffix
    return f"{v:.{decimals}f}{suffix}"

def fmt_delta(pct):
    if pct is None: return "—"
    return f"{pct:.1f}%"

def get_series(df, metric_id, date_from, date_to):
    """Серия (date_end, value_s) за период."""
    mask = ((df["metric_id"] == metric_id) &
            (df["date_end"] >= pd.Timestamp(date_from)) &
            (df["date_end"] <= pd.Timestamp(date_to)))
    return df[mask].sort_values("date_end")

def get_metric_name(df, metric_id):
    sub = df[df["metric_id"] == metric_id]
    return sub["metric_name"].iloc[0] if not sub.empty else metric_id


# ── session state ──────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "summary"
p = st.session_state.page

# ── глобальный CSS ─────────────────────────────────────────────────────────
st.markdown(f"""
<style>
.block-container {{ padding-top: 1.5rem !important; max-width: 100% !important; }}
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondary"] {{
    white-space: nowrap !important; font-size: 14px !important; font-weight: 500 !important;
    padding: 9px 24px !important; border-radius: 8px !important;
}}
button[data-testid="stBaseButton-secondary"] {{
    background-color: #fff !important; color: {GREEN} !important;
    border: 2px solid {GREEN} !important;
}}
button[data-testid="stBaseButton-secondary"]:hover {{ background-color: #F0F8E8 !important; border-color: {GREEN} !important; }}
button[data-testid="stBaseButton-primary"] {{
    background-color: {GREEN} !important; color: #fff !important; border: 2px solid {GREEN} !important;
}}
button[data-testid="stBaseButton-primary"]:hover {{
    background-color: {DARK_GREEN} !important; border-color: {DARK_GREEN} !important;
}}
div[data-baseweb="input"] > div {{
    border-radius: 6px !important; border-color: #B6D87C !important;
}}
</style>
""", unsafe_allow_html=True)

# ── загружаем данные ──────────────────────────────────────────────────────
try:
    df = load_data()
    available_dates = sorted(df["date_end"].dt.date.unique())
    data_ok = True
except Exception as e:
    st.error(f"Не удалось загрузить данные: {e}")
    data_ok = False
    df = None
    available_dates = []

# ── заголовок ──────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='font-size:28px;font-weight:600;color:{BLACK};margin:0 0 12px;letter-spacing:-0.3px;'>"
    "ИС Статус. Дэшборд</h1>",
    unsafe_allow_html=True,
)

# ── навигация ──────────────────────────────────────────────────────────────
n1, n2, n3, _ = st.columns([0.9, 1.9, 1.3, 5.7])
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
with n3:
    if st.button("🔄 Обновить данные", key="nav_refresh",
                 type="secondary", use_container_width=True):
        try:
            if os.path.exists(XLSX_PATH):
                _convert_xlsx_to_json()
                st.success(f"Данные обновлены из {XLSX_PATH}")
            elif os.path.exists(JSON_PATH):
                st.info(f"{XLSX_PATH} не найден — перечитан существующий {JSON_PATH}")
            else:
                st.error(f"Нет ни {XLSX_PATH}, ни {JSON_PATH} в папке приложения")
        except Exception as e:
            st.error(f"Ошибка обновления: {e}")
        st.cache_data.clear()
        st.rerun()

st.markdown("<hr style='margin:10px 0 14px;border:none;border-top:1px solid #E0E0DA;'>",
            unsafe_allow_html=True)

if not data_ok:
    st.stop()

# ── даты по умолчанию ─────────────────────────────────────────────────────
max_d = available_dates[-1]
min_d = available_dates[0]
default_from = available_dates[-4] if len(available_dates) >= 4 else min_d

# ── хелперы для UI ─────────────────────────────────────────────────────────
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
                min-height:108px;display:flex;flex-direction:column;margin-bottom:8px;">
      <div style="font-size:11px;opacity:0.9;line-height:1.25;font-weight:500;margin-bottom:6px;">{label}</div>
      <div style="font-size:22px;font-weight:600;letter-spacing:-0.5px;">{value}</div>
      {delta_html}
    </div>""", unsafe_allow_html=True)

def metric_pair(label, v1, d1, v2, d2, style="yellow", d1_dir="up", d2_dir="up"):
    bg, fg, up_col, down_col = CARD_STYLES[style]
    def fmt(dir_, val):
        if not val: return ""
        a = "▲" if dir_ == "up" else "▼"
        c = up_col if dir_ == "up" else down_col
        return f'<div style="font-size:10px;color:{c};font-weight:600;">{a} {val}</div>'
    st.markdown(f"""
    <div style="background:{bg};border-radius:12px;padding:11px 13px 12px;
                color:{fg};box-shadow:0 1px 4px rgba(0,0,0,0.10);
                min-height:108px;display:flex;flex-direction:column;margin-bottom:8px;">
      <div style="font-size:11px;opacity:0.85;line-height:1.25;font-weight:500;margin-bottom:6px;">{label}</div>
      <div style="font-size:20px;font-weight:600;letter-spacing:-0.5px;">{v1} / {v2}</div>
      <div style="display:flex;gap:14px;margin-top:4px;">{fmt(d1_dir, d1)}{fmt(d2_dir, d2)}</div>
    </div>""", unsafe_allow_html=True)

def chart_title(t):
    st.markdown(f'<p style="font-size:13px;font-weight:600;color:{BLACK};margin:0 0 4px;">{t}</p>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# СТРАНИЦА: САММАРИ
# ══════════════════════════════════════════════════════════════════════════
if p == "summary":
    # ── даты ───────────────────────────────────────────────────────────
    d1c, d2c, _ = st.columns([1.2, 1.2, 6])
    with d1c:
        date_from = st.date_input("Период с", value=default_from,
                                  min_value=min_d, max_value=max_d,
                                  format="DD.MM.YYYY", key="d_from")
    with d2c:
        date_to = st.date_input("по", value=max_d,
                                min_value=min_d, max_value=max_d,
                                format="DD.MM.YYYY", key="d_to")

    st.markdown(
        f"<p style='font-size:11px;color:{GREY_TXT};margin:4px 0 8px;'>"
        f"Доступные даты в данных: {len(available_dates)} точек, "
        f"с <b>{min_d.strftime('%d.%m.%Y')}</b> по <b>{max_d.strftime('%d.%m.%Y')}</b></p>",
        unsafe_allow_html=True
    )

    # ── получаем значения и динамику для метрик ───────────────────────
    v_1,  p_1,  d_1  = get_delta(df, "metric_smr_1",  date_from, date_to)
    v_3,  p_3,  d_3  = get_delta(df, "metric_smr_3",  date_from, date_to)
    v_2,  p_2,  d_2  = get_delta(df, "metric_smr_2",  date_from, date_to)
    v_38, p_38, d_38 = get_delta(df, "metric_smr_38", date_from, date_to)
    v_39, p_39, d_39 = get_delta(df, "metric_smr_39", date_from, date_to)
    v_36, p_36, d_36 = get_delta(df, "metric_smr_36", date_from, date_to)
    v_37, p_37, d_37 = get_delta(df, "metric_smr_37", date_from, date_to)

    # ════ Q1 + Q2 ════
    q1, q2 = st.columns([1, 1], gap="large")

    with q1:
        m, g = st.columns([1, 2.2], gap="small")
        with m:
            metric_card("Количество видов отклонений",
                        fmt_num(v_1), fmt_delta(p_1), d_1 or "up", "dark-green")
            metric_card("Количество человек с отклонениями",
                        fmt_num(v_3), fmt_delta(p_3), d_3 or "up", "green")
        with g:
            chart_title("Качество работы с отклонениями")
            # 3 месяца от date_to
            df3m_from = (pd.Timestamp(date_to) - pd.DateOffset(months=3)).date()
            s_4 = get_series(df, "metric_smr_4", df3m_from, date_to)
            s_5 = get_series(df, "metric_smr_5", df3m_from, date_to)
            x_lbl = s_4["date_end"].dt.strftime("%d.%m").tolist()
            f1 = go.Figure()
            f1.add_trace(go.Bar(
                name="Счётчик повторов (шт.)",
                x=x_lbl, y=s_4["value_s"].tolist(),
                marker_color=DARK_GREEN, opacity=0.9, yaxis="y1",
                hovertemplate="<b>%{x}</b><br>Счётчик: %{y:.1f}<extra></extra>",
            ))
            f1.add_trace(go.Bar(
                name="Пораженность (%)",
                x=s_5["date_end"].dt.strftime("%d.%m").tolist(),
                y=s_5["value_s"].tolist(),
                marker_color=YELLOW, opacity=0.9, yaxis="y2",
                hovertemplate="<b>%{x}</b><br>Пораженность: %{y:.1f}%<extra></extra>",
            ))
            f1.update_layout(
                height=220, margin=dict(t=14, b=32, l=42, r=46),
                paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(size=10, color=GREY_TXT),
                barmode="group", bargap=0.25, bargroupgap=0.08,
                showlegend=True,
                legend=dict(orientation="h", y=1.14, x=0, font=dict(size=9)),
                xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                yaxis=dict(gridcolor=GRID, tickfont=dict(size=10),
                           title=dict(text="шт.", font=dict(size=10, color=GREY_TXT))),
                yaxis2=dict(overlaying="y", side="right",
                            gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10),
                            ticksuffix="%",
                            title=dict(text="%", font=dict(size=10, color=GREY_TXT))),
            )
            st.plotly_chart(f1, use_container_width=True, config={"displayModeBar": False})

    with q2:
        g, m = st.columns([2.2, 1], gap="small")
        with g:
            chart_title("Средний счётчик повторов")
            # 6 месяцев от date_to, помесячно (средний за месяц)
            df6m_from = (pd.Timestamp(date_to) - pd.DateOffset(months=6)).date()
            s_36 = get_series(df, "metric_smr_36", df6m_from, date_to)
            if not s_36.empty:
                tmp = s_36.copy()
                tmp["month"] = tmp["date_end"].dt.to_period("M")
                monthly = tmp.groupby("month")["value_s"].mean().reset_index()
                monthly["lbl"] = monthly["month"].dt.strftime("%b %y")
                x_lbl  = monthly["lbl"].tolist()
                y_vals = monthly["value_s"].tolist()
            else:
                x_lbl, y_vals = [], []
            f2 = go.Figure(go.Scatter(
                x=x_lbl, y=y_vals,
                mode="lines+markers",
                line=dict(color=GREEN, width=2.5),
                marker=dict(size=7, color=GREEN),
                fill="tozeroy", fillcolor="rgba(42,126,46,0.14)",
                hovertemplate="<b>%{x}</b><br>Значение: %{y:.2f}<extra></extra>",
            ))
            f2.update_layout(
                height=220, margin=dict(t=14, b=32, l=42, r=8),
                paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(size=10, color=GREY_TXT), showlegend=False,
                xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
            )
            st.plotly_chart(f2, use_container_width=True, config={"displayModeBar": False})
        with m:
            metric_card("Доля устранённых отклонений",
                        fmt_num(v_36, suffix="%", decimals=1),
                        fmt_delta(p_36), d_36 or "up", "orange")

    st.markdown("<hr style='margin:8px 0 12px;border:none;border-top:1px solid #E0E0DA;'>",
                unsafe_allow_html=True)

    # ════ Q3 + Q4 ════
    q3, q4 = st.columns([1, 1], gap="large")

    with q3:
        m, g = st.columns([1, 2.2], gap="small")
        with m:
            metric_card("Кол-во ВСП с отклонениями",
                        fmt_num(v_2), fmt_delta(p_2), d_2 or "up", "black")
            metric_pair("Кол-во задач / Хроник",
                        fmt_num(v_38), fmt_delta(p_38),
                        fmt_num(v_39), fmt_delta(p_39),
                        "yellow", d_38 or "up", d_39 or "up")
        with g:
            chart_title("Задачи")
            # 3 месяца недельно: 38 внизу (родительские), 39 сверху (эскалированные)
            df3m_from = (pd.Timestamp(date_to) - pd.DateOffset(months=3)).date()
            s_38 = get_series(df, "metric_smr_38", df3m_from, date_to)
            s_39 = get_series(df, "metric_smr_39", df3m_from, date_to)
            x_lbl = s_38["date_end"].dt.strftime("%d.%m").tolist()
            f3 = go.Figure()
            f3.add_trace(go.Bar(
                name=get_metric_name(df, "metric_smr_38"),
                x=x_lbl, y=s_38["value_s"].tolist(),
                marker_color=DARK_GREEN, opacity=0.9,
                hovertemplate="<b>%{x}</b><br>"+get_metric_name(df, "metric_smr_38")+": %{y:,.0f}<extra></extra>",
            ))
            f3.add_trace(go.Bar(
                name=get_metric_name(df, "metric_smr_39"),
                x=s_39["date_end"].dt.strftime("%d.%m").tolist(),
                y=s_39["value_s"].tolist(),
                marker_color=LIME, opacity=0.9,
                hovertemplate="<b>%{x}</b><br>"+get_metric_name(df, "metric_smr_39")+": %{y:,.0f}<extra></extra>",
            ))
            f3.update_layout(
                height=220, margin=dict(t=14, b=32, l=42, r=8),
                paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(size=10, color=GREY_TXT),
                barmode="stack", bargap=0.3,
                showlegend=True,
                legend=dict(orientation="h", y=1.14, x=0, font=dict(size=9)),
                xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
            )
            st.plotly_chart(f3, use_container_width=True, config={"displayModeBar": False})

    with q4:
        g, m = st.columns([2.2, 1], gap="small")
        with g:
            chart_title(get_metric_name(df, "metric_smr_37"))
            # 6 месяцев, помесячно
            df6m_from = (pd.Timestamp(date_to) - pd.DateOffset(months=6)).date()
            s_37 = get_series(df, "metric_smr_37", df6m_from, date_to)
            if not s_37.empty:
                tmp = s_37.copy()
                tmp["month"] = tmp["date_end"].dt.to_period("M")
                monthly = tmp.groupby("month")["value_s"].mean().reset_index()
                monthly["lbl"] = monthly["month"].dt.strftime("%b %y")
                x_lbl  = monthly["lbl"].tolist()
                y_vals = monthly["value_s"].tolist()
            else:
                x_lbl, y_vals = [], []
            f4 = go.Figure(go.Scatter(
                x=x_lbl, y=y_vals,
                mode="lines+markers",
                line=dict(color=ORANGE, width=2.5),
                marker=dict(size=7, color=ORANGE),
                fill="tozeroy", fillcolor="rgba(224,123,27,0.14)",
                hovertemplate="<b>%{x}</b><br>Значение: %{y:.2f}<extra></extra>",
            ))
            f4.update_layout(
                height=220, margin=dict(t=14, b=32, l=42, r=8),
                paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(size=10, color=GREY_TXT), showlegend=False,
                xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
            )
            st.plotly_chart(f4, use_container_width=True, config={"displayModeBar": False})
        with m:
            metric_card("Скорость устранения",
                        fmt_num(v_37, suffix=" нед.", decimals=1),
                        fmt_delta(p_37), d_37 or "up", "lime")

    st.caption(f"Данные: metrics.xlsx · последняя дата {max_d.strftime('%d.%m.%Y')}")


# ══════════════════════════════════════════════════════════════════════════
# СТРАНИЦА: БМО
# ══════════════════════════════════════════════════════════════════════════
else:
    d1c, d2c, _ = st.columns([1.2, 1.2, 6])
    with d1c:
        date_from = st.date_input("Период с", value=default_from,
                                  min_value=min_d, max_value=max_d,
                                  format="DD.MM.YYYY", key="bd_from")
    with d2c:
        date_to = st.date_input("по", value=max_d,
                                min_value=min_d, max_value=max_d,
                                format="DD.MM.YYYY", key="bd_to")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── получаем значения для карточек ─────────────────────────────────
    v_36, p_36, d_36 = get_delta(df, "metric_smr_36", date_from, date_to)
    v_37, p_37, d_37 = get_delta(df, "metric_smr_37", date_from, date_to)
    v_1,  p_1,  d_1  = get_delta(df, "metric_smr_1",  date_from, date_to)
    v_2,  p_2,  d_2  = get_delta(df, "metric_smr_2",  date_from, date_to)
    v_3,  p_3,  d_3  = get_delta(df, "metric_smr_3",  date_from, date_to)
    v_38, p_38, _    = get_delta(df, "metric_smr_38", date_from, date_to)

    def bmo_card(label, value, delta, delta_dir, accent):
        col = GREEN if delta_dir == "up" else ORANGE
        arrow = "▲" if delta_dir == "up" else "▼"
        delta_html = f'<div style="font-size:10px;font-weight:600;color:{col};margin-top:2px;">{arrow} {delta}</div>' if delta else ""
        return f"""
        <div style="background:#fff;border:0.5px solid #E0E0DA;border-radius:10px;
                    padding:9px 11px;border-left:3px solid {accent};min-height:78px;">
          <div style="font-size:10px;color:{GREY_TXT};line-height:1.2;margin-bottom:4px;">{label}</div>
          <div style="font-size:18px;font-weight:600;color:{BLACK};">{value}</div>
          {delta_html}
        </div>"""

    cards = [
        ("Доля по Банку",             fmt_num(v_36, "%", 1),                    fmt_delta(p_36), d_36 or "up", GREEN),
        ("Целевое значение",          "52%",                                    "цель",          "up",         "#5F5E5A"),
        ("Количество задач / хроник", fmt_num(v_38),                            fmt_delta(p_38), "up",         YELLOW),
        ("Доля устранённых",          fmt_num(v_36, "%", 1),                    fmt_delta(p_36), d_36 or "up", LIME),
        ("Пораженность",              fmt_num(v_1),                             fmt_delta(p_1),  d_1 or "up",  GREEN),
        ("Средний счётчик повторов",  fmt_num(v_37, " нед.", 1),                fmt_delta(p_37), d_37 or "up", ORANGE),
        ("Кол-во объектов чел / ВСП", f"{fmt_num(v_3)} / {fmt_num(v_2)}",       fmt_delta(p_3),  d_3 or "up",  DARK_GREEN),
        ("Скорость устранения",       fmt_num(v_37, " нед.", 1),                fmt_delta(p_37), d_37 or "up", BLACK),
    ]
    cols = st.columns(8)
    for c, (lbl, v, d, dr, ac) in zip(cols, cards):
        with c:
            st.markdown(bmo_card(lbl, v, d, dr, ac), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    g_col, f_col = st.columns([1.4, 1], gap="large")

    with g_col:
        chart_title("Динамика ВСП и задач по неделям")
        s_2  = get_series(df, "metric_smr_2",  date_from, date_to)
        s_38 = get_series(df, "metric_smr_38", date_from, date_to)
        x_lbl = s_2["date_end"].dt.strftime("%d.%m").tolist()
        f5 = go.Figure()
        f5.add_trace(go.Bar(name="ВСП", x=x_lbl, y=s_2["value_s"].tolist(),
                            marker_color=GREEN, opacity=0.85, yaxis="y1",
                            hovertemplate="<b>%{x}</b><br>ВСП: %{y:,}<extra></extra>"))
        f5.add_trace(go.Scatter(name="Задачи",
                                x=s_38["date_end"].dt.strftime("%d.%m").tolist(),
                                y=s_38["value_s"].tolist(),
                                mode="lines+markers",
                                line=dict(color=ORANGE, width=2.5),
                                marker=dict(size=5, color=ORANGE), yaxis="y2",
                                hovertemplate="<b>%{x}</b><br>Задачи: %{y:,}<extra></extra>"))
        f5.update_layout(
            height=210, margin=dict(t=10, b=30, l=42, r=46),
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

        chart_title("Доля и скорость устранения")
        s_3  = get_series(df, "metric_smr_3",  date_from, date_to)
        s_39 = get_series(df, "metric_smr_39", date_from, date_to)
        f6 = go.Figure()
        f6.add_trace(go.Bar(name="Сотрудники", x=s_3["date_end"].dt.strftime("%d.%m").tolist(),
                            y=s_3["value_s"].tolist(),
                            marker_color=LIME, opacity=0.9,
                            hovertemplate="<b>%{x}</b><br>Сотрудники: %{y:,}<extra></extra>"))
        f6.add_trace(go.Scatter(name="Эскалированные",
                                x=s_39["date_end"].dt.strftime("%d.%m").tolist(),
                                y=s_39["value_s"].tolist(),
                                mode="lines+markers",
                                line=dict(color=YELLOW, width=2.5),
                                marker=dict(size=5, color=YELLOW),
                                hovertemplate="<b>%{x}</b><br>Эскалированные: %{y:,}<extra></extra>"))
        f6.update_layout(
            height=210, margin=dict(t=10, b=30, l=42, r=8),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=10, color=GREY_TXT),
            barmode="overlay",
            showlegend=True,
            legend=dict(orientation="h", y=1.14, x=0, font=dict(size=10)),
            xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        )
        st.plotly_chart(f6, use_container_width=True, config={"displayModeBar": False})

    with f_col:
        chart_title("Воронка метрик БА по БМО")
        # пока статичные данные — нет в выгрузке детализации по типам
        stages = ["Всего", "Выявлено", "Передано", "Устранено"]
        totals = [int(v_1 or 1600) * 100,
                  int((v_1 or 1200) * 75),
                  int((v_1 or 950)  * 60),
                  int((v_1 or 850)  * 53)]
        # фиксированные доли по типам
        parts = {
            "Всего":     [int(totals[0]*0.375), int(totals[0]*0.375), totals[0] - 2*int(totals[0]*0.375)],
            "Выявлено":  [int(totals[1]*0.383), int(totals[1]*0.367), totals[1] - int(totals[1]*0.383) - int(totals[1]*0.367)],
            "Передано":  [int(totals[2]*0.379), int(totals[2]*0.368), totals[2] - int(totals[2]*0.379) - int(totals[2]*0.368)],
            "Устранено": [int(totals[3]*0.376), int(totals[3]*0.365), totals[3] - int(totals[3]*0.376) - int(totals[3]*0.365)],
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
                fj = parts_i[j] / total_p if total_p else 0.33
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
                ct += swt; cb += swb
            mid_y = yt + row_h / 2 + 5
            out.append(f'<text x="{label_w-8}" y="{mid_y:.1f}" text-anchor="end" '
                       f'font-size="11" fill="#444441">{stage}</text>')
            out.append(f'<text x="{cx+bw_bot/2+8}" y="{mid_y:.1f}" text-anchor="start" '
                       f'font-size="13" font-weight="700" fill="{BLACK}">{total}</text>')

        ly = H - 30
        for k, (lbl, clr) in enumerate(zip(["Тип А", "Тип Б", "Тип В"], COLORS)):
            out.append(f'<rect x="{label_w+k*80}" y="{ly}" width="13" height="13" fill="{clr}" rx="2"/>')
            out.append(f'<text x="{label_w+k*80+18}" y="{ly+11}" font-size="11" fill="#444441">{lbl}</text>')

        svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" '
               f'style="font-family:sans-serif;">{"".join(out)}</svg>')
        st.markdown(svg, unsafe_allow_html=True)

    st.caption(f"* Данные: metrics.xlsx · последняя дата {max_d.strftime('%d.%m.%Y')}")
