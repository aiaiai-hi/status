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
def metric_card(label, value, delta=None, delta_dir="up", style="green",
                right_text=None, delta_label=None):
    """
    label       — название метрики
    value       — основное значение
    delta       — значение дельты для показа (строка, например "1.5%" или "+3")
    delta_dir   — "up"/"down" — направление (цвет/стрелка)
    right_text  — текст справа от value (например доля от итога)
    delta_label — подпись возле дельты (например "к ср. за 3 нед.")
    """
    bg, fg, up_col, down_col = CARD_STYLES[style]
    delta_html = ""
    if delta:
        col = up_col if delta_dir == "up" else down_col
        arrow = "▲" if delta_dir == "up" else "▼"
        suffix = f' <span style="opacity:.75;font-weight:500;">{delta_label}</span>' if delta_label else ""
        delta_html = (f'<div style="font-size:11px;color:{col};font-weight:600;margin-top:4px;">'
                      f'{arrow} {delta}{suffix}</div>')
    right_html = ""
    if right_text:
        right_html = (f'<span style="font-size:13px;opacity:0.85;font-weight:500;'
                      f'margin-left:auto;">{right_text}</span>')
    st.markdown(f"""
    <div style="background:{bg};border-radius:12px;padding:11px 13px 12px;
                color:{fg};box-shadow:0 1px 4px rgba(0,0,0,0.10);
                min-height:108px;display:flex;flex-direction:column;margin-bottom:8px;">
      <div style="font-size:11px;opacity:0.9;line-height:1.25;font-weight:500;margin-bottom:6px;">{label}</div>
      <div style="display:flex;align-items:baseline;">
        <span style="font-size:22px;font-weight:600;letter-spacing:-0.5px;">{value}</span>
        {right_html}
      </div>
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

# ── доп. хелперы для новых требований ─────────────────────────────────────
def get_avg_last_n_weeks(df_long, metric_id, ref_date, n=3):
    """Среднее значение метрики за последние n недель до ref_date (не включая её)."""
    from_d = (pd.Timestamp(ref_date) - timedelta(weeks=n)).date()
    to_d   = (pd.Timestamp(ref_date) - timedelta(days=1)).date()
    sub = get_series(df_long, metric_id, from_d, to_d)
    if sub.empty:
        return None
    return float(sub["value_s"].mean())

def get_delta_vs_avg(df_long, metric_id, date_from, date_to, n_weeks_avg=3):
    """Текущее значение и сравнение со средним за n_weeks_avg недель до date_from."""
    cur = get_period_value(df_long, metric_id, date_from, date_to)
    if cur is None:
        return None, None, None
    avg = get_avg_last_n_weeks(df_long, metric_id, date_from, n_weeks_avg)
    if avg is None or avg == 0:
        return cur, None, None
    pct = (cur - avg) / avg * 100
    return cur, abs(pct), ("up" if pct >= 0 else "down")

def monthly_avg(df_long, metric_id, date_to, months_back=6):
    """Помесячное среднее метрики за последние months_back месяцев до date_to."""
    from_d = (pd.Timestamp(date_to) - pd.DateOffset(months=months_back)).date()
    sub = get_series(df_long, metric_id, from_d, date_to)
    if sub.empty:
        return [], []
    tmp = sub.copy()
    tmp["month"] = tmp["date_end"].dt.to_period("M")
    m = tmp.groupby("month")["value_s"].mean().reset_index()
    m["lbl"] = m["month"].dt.strftime("%b %y")
    return m["lbl"].tolist(), m["value_s"].tolist()

def get_weeks_in_period(df_long, date_from, date_to):
    """Список уникальных date_end из данных, попадающих в выбранный период."""
    mask = ((df_long["date_end"] >= pd.Timestamp(date_from)) &
            (df_long["date_end"] <= pd.Timestamp(date_to)))
    dates = sorted(df_long[mask]["date_end"].dt.date.unique())
    return dates


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

    # ── кнопки недель из date_end в выбранном периоде ──────────────────
    weeks_in_period = get_weeks_in_period(df, date_from, date_to)
    if weeks_in_period:
        if "selected_week" not in st.session_state:
            st.session_state.selected_week = "all"

        st.markdown(
            f"<p style='font-size:11px;color:{GREY_TXT};margin:8px 0 4px;font-weight:600;'>"
            f"Недели в периоде:</p>",
            unsafe_allow_html=True
        )
        # +1 кнопка "Весь период"
        n_btns = len(weeks_in_period) + 1
        cols_w = st.columns(min(n_btns, 10))
        # кнопка "весь период"
        with cols_w[0]:
            if st.button("Весь период",
                         key="wk_all",
                         type="primary" if st.session_state.selected_week == "all" else "secondary",
                         use_container_width=True):
                st.session_state.selected_week = "all"
                st.rerun()
        for i, wd in enumerate(weeks_in_period[:9]):  # макс 9 недель в кнопках
            with cols_w[i+1]:
                wkey = wd.strftime("%Y-%m-%d")
                if st.button(wd.strftime("%d.%m"),
                             key=f"wk_{wkey}",
                             type="primary" if st.session_state.selected_week == wkey else "secondary",
                             use_container_width=True):
                    st.session_state.selected_week = wkey
                    st.rerun()

        # Эффективный период: если выбрана неделя — только она
        if st.session_state.selected_week != "all":
            try:
                wd = pd.Timestamp(st.session_state.selected_week).date()
                eff_from, eff_to = wd, wd
            except Exception:
                eff_from, eff_to = date_from, date_to
        else:
            eff_from, eff_to = date_from, date_to
    else:
        eff_from, eff_to = date_from, date_to

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── получаем значения и динамику для метрик ───────────────────────
    # все берутся из столбца value_s
    v_1   = get_period_value(df, "metric_smr_1",  eff_from, eff_to)
    v_11  = get_period_value(df, "metric_smr_11", eff_from, eff_to)
    v_3   = get_period_value(df, "metric_smr_3",  eff_from, eff_to)
    v_2,  p_2,  d_2  = get_delta(df, "metric_smr_2",  eff_from, eff_to)
    v_36, p_36, d_36 = get_delta(df, "metric_smr_36", eff_from, eff_to)
    v_37, p_37, d_37 = get_delta(df, "metric_smr_37", eff_from, eff_to)

    # для метрики 1: дельта в абсолютном значении, доля от 11
    prev_v_1 = get_period_value(
        df, "metric_smr_1",
        (pd.Timestamp(eff_from) - timedelta(weeks=1)).date(),
        (pd.Timestamp(eff_from) - timedelta(days=1)).date(),
    )
    if v_1 is not None and prev_v_1 is not None:
        abs_delta_1 = v_1 - prev_v_1
        dir_1 = "up" if abs_delta_1 >= 0 else "down"
        delta_1_str = f"{abs(abs_delta_1):.0f}"
    else:
        dir_1, delta_1_str = "up", None
    share_1 = (v_1 / v_11 * 100) if (v_1 is not None and v_11 and v_11 != 0) else None
    right_1 = f"{share_1:.1f}% от {fmt_num(v_11)}" if share_1 is not None else None

    # для метрики 3: дельта обычная, доля от 1000
    _, p_3, d_3 = get_delta(df, "metric_smr_3", eff_from, eff_to)
    share_3 = (v_3 / 1000 * 100) if v_3 is not None else None
    right_3 = f"{share_3:.1f}% от 1000" if share_3 is not None else None

    # для пары 38/39: динамика к среднему за 3 недели до eff_from
    v_38, p_38_avg, d_38_avg = get_delta_vs_avg(df, "metric_smr_38", eff_from, eff_to, 3)
    v_39, p_39_avg, d_39_avg = get_delta_vs_avg(df, "metric_smr_39", eff_from, eff_to, 3)

    # ════ Q1 + Q2 ════
    q1, q2 = st.columns([1, 1], gap="large")

    with q1:
        m, g = st.columns([1, 2.2], gap="small")
        with m:
            metric_card("Количество видов отклонений",
                        fmt_num(v_1),
                        delta=delta_1_str, delta_dir=dir_1, style="dark-green",
                        right_text=right_1, delta_label="к пред. неделе")
            metric_card("Количество человек с отклонениями",
                        fmt_num(v_3),
                        delta=fmt_delta(p_3), delta_dir=d_3 or "up", style="green",
                        right_text=right_3, delta_label="к пред. периоду")
        with g:
            chart_title("Качество работы с отклонениями")
            df3m_from = (pd.Timestamp(eff_to) - pd.DateOffset(months=3)).date()
            s_4 = get_series(df, "metric_smr_4", df3m_from, eff_to)
            s_5 = get_series(df, "metric_smr_5", df3m_from, eff_to)
            # объединённый набор недель
            all_weeks = sorted(set(s_4["date_end"].tolist()) | set(s_5["date_end"].tolist()))
            x_lbl = [d.strftime("%d.%m") for d in all_weeks]
            map_4 = dict(zip(s_4["date_end"], s_4["value_s"]))
            map_5 = dict(zip(s_5["date_end"], s_5["value_s"]))
            y_4 = [map_4.get(d) for d in all_weeks]
            y_5 = [map_5.get(d) for d in all_weeks]
            n4 = get_metric_name(df, "metric_smr_4")
            n5 = get_metric_name(df, "metric_smr_5")
            f1 = go.Figure()
            f1.add_trace(go.Bar(
                name=n4, x=x_lbl, y=y_4,
                marker_color=DARK_GREEN, opacity=0.9,
                hovertemplate="<b>%{x}</b><br>"+n4+": %{y:.2f}<extra></extra>",
            ))
            f1.add_trace(go.Bar(
                name=n5, x=x_lbl, y=y_5,
                marker_color=YELLOW, opacity=0.9,
                hovertemplate="<b>%{x}</b><br>"+n5+": %{y:.2f}<extra></extra>",
            ))
            f1.update_layout(
                height=220, margin=dict(t=14, b=32, l=42, r=8),
                paper_bgcolor=BG, plot_bgcolor=BG,
                font=dict(size=10, color=GREY_TXT),
                barmode="group", bargap=0.25, bargroupgap=0.05,
                showlegend=True,
                legend=dict(orientation="h", y=1.14, x=0, font=dict(size=9)),
                xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
            )
            st.plotly_chart(f1, use_container_width=True, config={"displayModeBar": False})

    with q2:
        g, m = st.columns([2.2, 1], gap="small")
        with g:
            chart_title("Средний счётчик повторов")
            x_lbl, y_vals = monthly_avg(df, "metric_smr_36", eff_to, 6)
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
            metric_pair("Кол-во родит.задач / экскалированных",
                        fmt_num(v_38), fmt_delta(p_38_avg),
                        fmt_num(v_39), fmt_delta(p_39_avg),
                        "yellow", d_38_avg or "up", d_39_avg or "up")
        with g:
            chart_title("Задачи")
            df3m_from = (pd.Timestamp(eff_to) - pd.DateOffset(months=3)).date()
            s_38 = get_series(df, "metric_smr_38", df3m_from, eff_to)
            s_39 = get_series(df, "metric_smr_39", df3m_from, eff_to)
            all_weeks = sorted(set(s_38["date_end"].tolist()) | set(s_39["date_end"].tolist()))
            x_lbl = [d.strftime("%d.%m") for d in all_weeks]
            map_38 = dict(zip(s_38["date_end"], s_38["value_s"]))
            map_39 = dict(zip(s_39["date_end"], s_39["value_s"]))
            y_38 = [map_38.get(d) for d in all_weeks]
            y_39 = [map_39.get(d) for d in all_weeks]
            n38 = get_metric_name(df, "metric_smr_38")
            n39 = get_metric_name(df, "metric_smr_39")
            f3 = go.Figure()
            f3.add_trace(go.Bar(
                name=n38, x=x_lbl, y=y_38,
                marker_color=DARK_GREEN, opacity=0.9,
                hovertemplate="<b>%{x}</b><br>"+n38+": %{y:,.0f}<extra></extra>",
            ))
            f3.add_trace(go.Bar(
                name=n39, x=x_lbl, y=y_39,
                marker_color=LIME, opacity=0.9,
                hovertemplate="<b>%{x}</b><br>"+n39+": %{y:,.0f}<extra></extra>",
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
            x_lbl, y_vals = monthly_avg(df, "metric_smr_37", eff_to, 6)
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

    # ── значения метрик для БМО ────────────────────────────────────────
    v_46, p_46, d_46 = get_delta(df, "metric_smr_46", date_from, date_to)  # Доля по Банку
    v_45             = get_period_value(df, "metric_smr_45", date_from, date_to)  # Целевое значение
    v_40, p_40, d_40 = get_delta(df, "metric_smr_40", date_from, date_to)  # родит. задачи
    v_41, p_41, d_41 = get_delta(df, "metric_smr_41", date_from, date_to)  # эскалированные
    v_34, p_34, d_34 = get_delta(df, "metric_smr_34", date_from, date_to)  # доля устраненных
    v_10, p_10, d_10 = get_delta(df, "metric_smr_10", date_from, date_to)  # пораженность
    v_7,  p_7,  d_7  = get_delta(df, "metric_smr_7",  date_from, date_to)  # средн. счётчик повторов
    v_9              = get_period_value(df, "metric_smr_9", date_from, date_to)  # чел.
    v_8              = get_period_value(df, "metric_smr_8", date_from, date_to)  # ВСП
    v_35, p_35, d_35 = get_delta(df, "metric_smr_35", date_from, date_to)  # скорость устранения

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

    qty_pair = (f"{fmt_num(v_40)} / {fmt_num(v_41)}"
                if v_40 is not None and v_41 is not None else "—")
    chel_vsp = (f"{fmt_num(v_9)} / {fmt_num(v_8)}"
                if v_9 is not None and v_8 is not None else "—")

    cards = [
        ("Доля по Банку",             fmt_num(v_46, "%", 1),                    fmt_delta(p_46), d_46 or "up", GREEN),
        ("Целевое значение",          fmt_num(v_45, "%", 1) if v_45 is not None else "—", "цель", "up", "#5F5E5A"),
        ("Кол-во родит.задач / эскал.", qty_pair,                              fmt_delta(p_40), d_40 or "up", YELLOW),
        ("Доля устранённых",          fmt_num(v_34, "%", 1),                    fmt_delta(p_34), d_34 or "up", LIME),
        ("Пораженность",              fmt_num(v_10, "%", 1),                    fmt_delta(p_10), d_10 or "up", GREEN),
        ("Средний счётчик повторов",  fmt_num(v_7, "", 2),                      fmt_delta(p_7),  d_7 or "up",  ORANGE),
        ("Кол-во объектов чел / ВСП", chel_vsp,                                "",              "up",         DARK_GREEN),
        ("Скорость устранения",       fmt_num(v_35, " нед.", 1),                fmt_delta(p_35), d_35 or "up", BLACK),
    ]
    cols = st.columns(8)
    for c_, (lbl, v, d, dr, ac) in zip(cols, cards):
        with c_:
            st.markdown(bmo_card(lbl, v, d, dr, ac), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    g_col, f_col = st.columns([1.4, 1], gap="large")

    with g_col:
        # ── График 1: Доля БМО vs Целевое значение ──
        chart_title("Доля по Банку vs Целевое значение")
        s_46 = get_series(df, "metric_smr_46", date_from, date_to)
        s_45 = get_series(df, "metric_smr_45", date_from, date_to)
        all_d = sorted(set(s_46["date_end"].tolist()) | set(s_45["date_end"].tolist()))
        x_lbl = [d.strftime("%d.%m") for d in all_d]
        map_46 = dict(zip(s_46["date_end"], s_46["value_s"]))
        map_45 = dict(zip(s_45["date_end"], s_45["value_s"]))
        y_46 = [map_46.get(d) for d in all_d]
        y_45 = [map_45.get(d) for d in all_d]
        f5 = go.Figure()
        f5.add_trace(go.Bar(
            name="Доля БМО, %", x=x_lbl, y=y_46,
            marker_color=GREEN, opacity=0.85,
            hovertemplate="<b>%{x}</b><br>Доля БМО: %{y:.1f}%<extra></extra>",
        ))
        f5.add_trace(go.Scatter(
            name="Целевое значение", x=x_lbl, y=y_45,
            mode="lines+markers",
            line=dict(color=ORANGE, width=2.5, dash="dash"),
            marker=dict(size=6, color=ORANGE),
            hovertemplate="<b>%{x}</b><br>Цель: %{y:.1f}%<extra></extra>",
        ))
        f5.update_layout(
            height=210, margin=dict(t=10, b=30, l=42, r=8),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=10, color=GREY_TXT),
            bargap=0.3,
            showlegend=True,
            legend=dict(orientation="h", y=1.14, x=0, font=dict(size=10)),
            xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=10), ticksuffix="%"),
        )
        st.plotly_chart(f5, use_container_width=True, config={"displayModeBar": False})

        # ── График 2: Кол-во задач vs Доля устранённых ──
        chart_title("Количество задач и доля устранённых")
        s_40 = get_series(df, "metric_smr_40", date_from, date_to)
        s_34 = get_series(df, "metric_smr_34", date_from, date_to)
        all_d = sorted(set(s_40["date_end"].tolist()) | set(s_34["date_end"].tolist()))
        x_lbl = [d.strftime("%d.%m") for d in all_d]
        map_40 = dict(zip(s_40["date_end"], s_40["value_s"]))
        map_34 = dict(zip(s_34["date_end"], s_34["value_s"]))
        y_40 = [map_40.get(d) for d in all_d]
        # абс. кол-во устранённых = задачи * доля/100
        y_resolved = [(map_40[d] * map_34[d] / 100) if (d in map_40 and d in map_34) else None for d in all_d]
        f6 = go.Figure()
        f6.add_trace(go.Bar(
            name="Всего задач", x=x_lbl, y=y_40,
            marker_color=LIME, opacity=0.5,
            hovertemplate="<b>%{x}</b><br>Всего: %{y:,.0f}<extra></extra>",
        ))
        f6.add_trace(go.Bar(
            name="Устранено", x=x_lbl, y=y_resolved,
            marker_color=DARK_GREEN, opacity=0.95,
            hovertemplate="<b>%{x}</b><br>Устранено: %{y:,.0f}<extra></extra>",
        ))
        f6.update_layout(
            height=210, margin=dict(t=10, b=30, l=42, r=8),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=10, color=GREY_TXT),
            barmode="overlay", bargap=0.3,
            showlegend=True,
            legend=dict(orientation="h", y=1.14, x=0, font=dict(size=10)),
            xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
        )
        st.plotly_chart(f6, use_container_width=True, config={"displayModeBar": False})

        # ── График 3: Счётчик повторов + Скорость устранения (две линии) ──
        chart_title("Средний счётчик повторов и скорость устранения")
        s_7  = get_series(df, "metric_smr_7",  date_from, date_to)
        s_35 = get_series(df, "metric_smr_35", date_from, date_to)
        all_d = sorted(set(s_7["date_end"].tolist()) | set(s_35["date_end"].tolist()))
        x_lbl = [d.strftime("%d.%m") for d in all_d]
        map_7  = dict(zip(s_7["date_end"],  s_7["value_s"]))
        map_35 = dict(zip(s_35["date_end"], s_35["value_s"]))
        y_7  = [map_7.get(d)  for d in all_d]
        y_35 = [map_35.get(d) for d in all_d]
        f7 = go.Figure()
        f7.add_trace(go.Scatter(
            name="Средний счётчик повторов", x=x_lbl, y=y_7,
            mode="lines+markers",
            line=dict(color=GREEN, width=2.5),
            marker=dict(size=6, color=GREEN),
            hovertemplate="<b>%{x}</b><br>Повторы: %{y:.2f}<extra></extra>",
        ))
        f7.add_trace(go.Scatter(
            name="Скорость устранения", x=x_lbl, y=y_35,
            mode="lines+markers",
            line=dict(color=ORANGE, width=2.5),
            marker=dict(size=6, color=ORANGE), yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Скорость: %{y:.2f}<extra></extra>",
        ))
        f7.update_layout(
            height=210, margin=dict(t=10, b=30, l=42, r=42),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(size=10, color=GREY_TXT),
            showlegend=True,
            legend=dict(orientation="h", y=1.14, x=0, font=dict(size=10)),
            xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(size=10),
                       title=dict(text="Повторы", font=dict(size=10, color=GREY_TXT))),
            yaxis2=dict(overlaying="y", side="right", gridcolor="rgba(0,0,0,0)",
                        tickfont=dict(size=10),
                        title=dict(text="Скорость", font=dict(size=10, color=GREY_TXT))),
        )
        st.plotly_chart(f7, use_container_width=True, config={"displayModeBar": False})

    with f_col:
        chart_title("Воронка метрик БА по БМО")
        # пока статичные доли по типам (нет в данных детализации)
        v_share = v_46 if v_46 is not None else 73
        stages = ["Всего", "Выявлено", "Передано", "Устранено"]
        # пропорциональные значения от текущей доли
        base = int(v_40 if v_40 else 1600)
        totals = [base, int(base * 0.75), int(base * 0.6), int(base * 0.53)]
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
        max_val = totals[0] if totals[0] > 0 else 1
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
            total_p = sum(parts_i) or 1
            ct, cb = xl_top, xl_bot
            for j in range(3):
                fj = parts_i[j] / total_p
                swt = bw_top * fj
                swb = bw_bot * fj
                pts = (f"{ct:.1f},{yt} {ct+swt:.1f},{yt} "
                       f"{cb+swb:.1f},{yb} {cb:.1f},{yb}")
                tx = ct + swt / 2
                ty = yt + row_h / 2 + 5
                out.append(f'<polygon points="{pts}" fill="{COLORS[j]}" stroke="white" stroke-width="1.5"/>')
                out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="{TEXT_COLORS[j]}">{parts_i[j]}</text>')
                ct += swt; cb += swb
            mid_y = yt + row_h / 2 + 5
            out.append(f'<text x="{label_w-8}" y="{mid_y:.1f}" text-anchor="end" font-size="11" fill="#444441">{stage}</text>')
            out.append(f'<text x="{cx+bw_bot/2+8}" y="{mid_y:.1f}" text-anchor="start" font-size="13" font-weight="700" fill="{BLACK}">{total}</text>')

        ly = H - 30
        for k, (lbl, clr) in enumerate(zip(["Тип А", "Тип Б", "Тип В"], COLORS)):
            out.append(f'<rect x="{label_w+k*80}" y="{ly}" width="13" height="13" fill="{clr}" rx="2"/>')
            out.append(f'<text x="{label_w+k*80+18}" y="{ly+11}" font-size="11" fill="#444441">{lbl}</text>')

        svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" '
               f'style="font-family:sans-serif;">{"".join(out)}</svg>')
        st.markdown(svg, unsafe_allow_html=True)

    st.caption(f"* Данные: metrics.xlsx · последняя дата {max_d.strftime('%d.%m.%Y')}")
