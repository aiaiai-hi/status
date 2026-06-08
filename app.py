import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from io import BytesIO

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
    """
    Возвращает (значение, delta_pct, delta_dir).
    Логика: текущее = последняя точка метрики в выбранном периоде.
    Предыдущее = точка ровно за 7 дней до date_from.
    Если данных за эту дату нет — динамика не считается.
    """
    cur = get_period_value(df, metric_id, date_from, date_to)
    if cur is None:
        return None, None, None
    prev_date = (pd.Timestamp(date_from) - timedelta(days=7)).date()
    prev = get_period_value(df, metric_id, prev_date, prev_date)
    if prev is None or prev == 0:
        return cur, None, None
    pct = (cur - prev) / prev * 100
    direction = "up" if pct >= 0 else "down"
    return cur, abs(pct), direction


def get_delta_abs(df, metric_id, date_from, date_to):
    """Абсолютная разница: (cur, abs_delta, direction). Сравнение с точкой ровно за 7 дней до date_from."""
    cur = get_period_value(df, metric_id, date_from, date_to)
    if cur is None:
        return None, None, None
    prev_date = (pd.Timestamp(date_from) - timedelta(days=7)).date()
    prev = get_period_value(df, metric_id, prev_date, prev_date)
    if prev is None:
        return cur, None, None
    delta = cur - prev
    direction = "up" if delta >= 0 else "down"
    return cur, abs(delta), direction

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
/* фон страницы — мягкий бежевый (как в макете) */
.stApp {{ background-color: #F4F1E8 !important; }}
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
/* Высота для download и обычных кнопок — одинаковая, чтобы Скачать и Обновить выровнялись */
.stDownloadButton button, .stButton button {{
    height: 42px !important;
}}
/* Кнопка "Обновить данные" — серая, через маркерный класс */
div[data-testid="column"]:has(div.refresh-marker) button {{
    background-color: #fff !important;
    color: #777 !important;
    border: 1px solid #C8C8C4 !important;
    font-weight: 500 !important;
}}
div[data-testid="column"]:has(div.refresh-marker) button:hover {{
    color: {GREEN} !important;
    border-color: {GREEN} !important;
    background-color: #F0F8E8 !important;
}}
/* белая "коробочка" для графика — нативный st.container(border=True) */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: #fff !important;
    border-radius: 12px !important;
    border: 0.5px solid #E0E0DA !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    padding: 12px 14px 8px !important;
    margin-bottom: 8px !important;
}}
/* круглый бейдж ⓘ с подсказкой (CSS-tooltip) */
.info-badge {{
    display: inline-flex; position: relative;
    align-items: center; justify-content: center;
    width: 16px; height: 16px;
    border: 1px solid #C8C8C4;
    border-radius: 50%;
    font-size: 11px; color: {GREY_TXT};
    cursor: help;
    margin-left: 8px;
    line-height: 1;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    font-style: normal; font-weight: 500;
    vertical-align: middle;
}}
.info-badge:hover {{ border-color: {GREEN}; color: {GREEN}; }}
.info-badge::after {{
    content: attr(data-tip);
    position: absolute;
    bottom: calc(100% + 6px); left: 50%;
    transform: translateX(-50%);
    background: #1A1A1A; color: #fff;
    font-size: 11px; font-weight: 500;
    padding: 5px 9px; border-radius: 6px;
    white-space: nowrap;
    opacity: 0; pointer-events: none;
    transition: opacity 0.15s;
    z-index: 1000;
}}
.info-badge:hover::after {{ opacity: 1; }}
/* Plotly график сам белый */
div[data-testid="stPlotlyChart"] {{
    background-color: #ffffff !important;
    border-radius: 8px !important;
}}
</style>
""", unsafe_allow_html=True)

# ── JS-инжектор через iframe для надёжного применения стиля ───────────────
components.html("""
<script>
const parentDoc = window.parent.document;
function paintCards() {
  // Красим только Plotly-графики и их непосредственного border-родителя
  parentDoc.querySelectorAll('[data-testid="stPlotlyChart"]').forEach(plot => {
    plot.style.backgroundColor = '#ffffff';
    plot.style.borderRadius = '8px';
    // Идём вверх по дереву, ищем ближайший stVerticalBlockBorderWrapper
    let p = plot.parentElement;
    for (let i = 0; i < 10 && p; i++) {
      if (p.getAttribute && p.getAttribute('data-testid') === 'stVerticalBlockBorderWrapper') {
        p.style.backgroundColor = '#ffffff';
        p.style.borderRadius = '12px';
        break;
      }
      p = p.parentElement;
    }
  });
}
paintCards();
const obs = new MutationObserver(() => paintCards());
obs.observe(parentDoc.body, { childList: true, subtree: true });
setInterval(paintCards, 500);
</script>
""", height=0)

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

def chart_title(t, tooltip=None):
    tip_html = ""
    if tooltip:
        tip_html = (f'<span class="info-badge" data-tip="{tooltip}" '
                    f'title="{tooltip}" aria-label="{tooltip}">i</span>')
    st.markdown(
        f'<div style="font-size:13px;font-weight:600;color:{BLACK};margin:0 0 6px;'
        f'display:flex;align-items:center;position:relative;overflow:visible;">{t}{tip_html}</div>',
        unsafe_allow_html=True
    )


def chart_card():
    """Container с явно белым фоном и рамкой."""
    # st.container с border + дополнительный CSS поверх (на случай прозрачности)
    return st.container(border=True)

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


def build_excel_export(df_long, metric_ids, date_from, date_to, sheet_name="Summary"):
    """Сборка Excel: лист данных + лист саммари + лист сравнения с предыдущим периодом."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        # Лист 1: сырые данные за период
        mask = ((df_long["metric_id"].isin(metric_ids)) &
                (df_long["date_end"] >= pd.Timestamp(date_from)) &
                (df_long["date_end"] <= pd.Timestamp(date_to)))
        raw = df_long[mask][["date_end", "metric_id", "metric_name", "value_s"]].copy()
        raw["date_end"] = raw["date_end"].dt.strftime("%d.%m.%Y")
        raw.columns = ["Дата", "ID метрики", "Название метрики", "Значение"]
        raw.to_excel(wr, sheet_name="Данные", index=False)

        # Лист 2: саммари
        summary_rows = []
        for mid in metric_ids:
            cur = get_period_value(df_long, mid, date_from, date_to)
            if cur is None:
                continue
            name = get_metric_name(df_long, mid)
            summary_rows.append({"ID метрики": mid, "Метрика": name, "Значение": cur})
        if summary_rows:
            pd.DataFrame(summary_rows).to_excel(wr, sheet_name="Саммари", index=False)

        # Лист 3: сравнение — точно за 7 дней до date_from
        prev_date_from = pd.Timestamp(date_from) - timedelta(days=7)
        prev_date_to   = pd.Timestamp(date_to)   - timedelta(days=7)
        comp_rows = []
        for mid in metric_ids:
            cur = get_period_value(df_long, mid, date_from, date_to)
            prev = get_period_value(df_long, mid, prev_date_from.date(), prev_date_to.date())
            comp_rows.append({
                "ID метрики": mid,
                "Метрика":   get_metric_name(df_long, mid),
                "Текущий период":     cur,
                "Предыдущий период":  prev,
                "Δ абс.":   (cur - prev) if (cur is not None and prev is not None) else None,
                "Δ %":      ((cur - prev) / prev * 100) if (cur is not None and prev not in (None, 0)) else None,
            })
        meta = pd.DataFrame([
            {"Параметр": "Текущий период с",    "Значение": pd.Timestamp(date_from).strftime("%d.%m.%Y")},
            {"Параметр": "Текущий период по",   "Значение": pd.Timestamp(date_to).strftime("%d.%m.%Y")},
            {"Параметр": "Сравниваемый период с",  "Значение": prev_date_from.strftime("%d.%m.%Y")},
            {"Параметр": "Сравниваемый период по", "Значение": prev_date_to.strftime("%d.%m.%Y")},
        ])
        meta.to_excel(wr, sheet_name="Сравнение", index=False, startrow=0)
        pd.DataFrame(comp_rows).to_excel(wr, sheet_name="Сравнение", index=False, startrow=6)
    buf.seek(0)
    return buf.getvalue()


def render_weeks_buttons(df_long, date_from, date_to, key_prefix):
    """Рендерит ряд кнопок дат + 'Все'. Возвращает (eff_from, eff_to)."""
    weeks_in_period = get_weeks_in_period(df_long, date_from, date_to)
    state_key = f"selected_week_{key_prefix}"
    if not weeks_in_period:
        return date_from, date_to
    # По умолчанию выбираем первую неделю в периоде
    first_wkey = weeks_in_period[0].strftime("%Y-%m-%d")
    if state_key not in st.session_state:
        st.session_state[state_key] = first_wkey
    # Если выбранная неделя больше не входит в период — переключаемся на первую
    avail_keys = {d.strftime("%Y-%m-%d") for d in weeks_in_period}
    if st.session_state[state_key] not in avail_keys:
        st.session_state[state_key] = first_wkey

    st.markdown(
        f"""<p style='font-size:11px;color:{GREY_TXT};margin:0 0 4px;font-weight:600;'>
        Недели в периоде:</p>
        <style>
        div.weeks-row-{key_prefix} ~ div button[data-testid="stBaseButton-primary"],
        div.weeks-row-{key_prefix} ~ div button[data-testid="stBaseButton-secondary"] {{
            font-size: 11px !important; padding: 6px 4px !important;
            min-width: 0 !important; white-space: nowrap !important;
        }}
        </style>
        <div class="weeks-row-{key_prefix}"></div>""",
        unsafe_allow_html=True
    )
    items = [(d.strftime("%Y-%m-%d"), d.strftime("%d.%m")) for d in weeks_in_period[:10]]
    cols_w = st.columns(len(items))
    for i, (val, lbl) in enumerate(items):
        with cols_w[i]:
            if st.button(lbl, key=f"{key_prefix}_wk_{val}",
                         type="primary" if st.session_state[state_key] == val else "secondary",
                         use_container_width=True):
                st.session_state[state_key] = val
                st.rerun()

    try:
        wd = pd.Timestamp(st.session_state[state_key]).date()
        return wd, wd
    except Exception:
        return date_from, date_to


def render_export_button(df_long, metric_ids, date_from, date_to, key, file_label):
    """Кнопка скачивания Excel."""
    xlsx_bytes = build_excel_export(df_long, metric_ids, date_from, date_to)
    fname = f"{file_label}_{pd.Timestamp(date_from).strftime('%Y%m%d')}_{pd.Timestamp(date_to).strftime('%Y%m%d')}.xlsx"
    st.download_button(
        label="⬇ Скачать Excel",
        data=xlsx_bytes,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
        use_container_width=True,
    )


def render_refresh_button(key):
    """Серая кнопка «Обновить данные» — обновляет JSON из xlsx и сбрасывает кэш."""
    st.markdown('<div class="refresh-marker" style="display:none;"></div>', unsafe_allow_html=True)
    if st.button("Обновить данные", key=key, use_container_width=True):
        try:
            if os.path.exists(XLSX_PATH):
                _convert_xlsx_to_json()
        except Exception as e:
            st.error(f"Ошибка обновления: {e}")
        st.cache_data.clear()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# СТРАНИЦА: САММАРИ
# ══════════════════════════════════════════════════════════════════════════
if p == "summary":
    # ── даты + кнопки недель в одной строке ────────────────────────────
    d1c, d2c, weeks_col = st.columns([1.1, 1.1, 6.8])
    with d1c:
        date_from = st.date_input("Период с", value=default_from,
                                  min_value=min_d, max_value=max_d,
                                  format="DD.MM.YYYY", key="d_from")
    with d2c:
        date_to = st.date_input("по", value=max_d,
                                min_value=min_d, max_value=max_d,
                                format="DD.MM.YYYY", key="d_to")
    with weeks_col:
        eff_from, eff_to = render_weeks_buttons(df, date_from, date_to, "sum")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── получаем значения метрик из value_s ────────────────────────────
    v_1,  abs_d_1, dir_1d = get_delta_abs(df, "metric_smr_1",  eff_from, eff_to)
    v_11, p_11,    d_11  = get_delta    (df, "metric_smr_11", eff_from, eff_to)
    v_3   = get_period_value(df, "metric_smr_3",  eff_from, eff_to)
    v_2,  p_2,  d_2  = get_delta(df, "metric_smr_2",  eff_from, eff_to)
    v_4,  p_4,  d_4  = get_delta(df, "metric_smr_4",  eff_from, eff_to)
    v_5,  p_5,  d_5  = get_delta(df, "metric_smr_5",  eff_from, eff_to)

    # Метрика 1: дельта в абсолюте к предыдущей точке, доля от 11
    delta_1_str = f"{abs_d_1:.0f}" if abs_d_1 is not None else None
    dir_1 = dir_1d or "up"
    share_1 = (v_1 / v_11 * 100) if (v_1 is not None and v_11 and v_11 != 0) else None
    right_1 = f"{share_1:.1f}% от {fmt_num(v_11)}" if share_1 is not None else None

    # Метрика 3: доля от 3000
    _, p_3, d_3 = get_delta(df, "metric_smr_3", eff_from, eff_to)
    share_3 = (v_3 / 3000 * 100) if v_3 is not None else None
    right_3 = f"{share_3:.1f}% от 3000" if share_3 is not None else None

    # Метрика 2: доля от 1275
    share_2 = (v_2 / 1275 * 100) if v_2 is not None else None
    right_2 = f"{share_2:.1f}% от 1275" if share_2 is not None else None

    # Пара 38/39: динамика к предыдущей точке (как и все остальные)
    v_38, p_38, d_38 = get_delta(df, "metric_smr_38", eff_from, eff_to)
    v_39, p_39, d_39 = get_delta(df, "metric_smr_39", eff_from, eff_to)

    # вспомогательное: 3 месяца от eff_to (последняя выбранная неделя)
    df3m_from = (pd.Timestamp(eff_to) - pd.DateOffset(months=3)).date()

    # ════ Q1 + Q2: Q1 = метрики 1,11 + график "Качество работы"; Q2 = график "Задачи" + метрики 38, 39 ════
    q1, q2 = st.columns([1, 1], gap="large")

    with q1:
        m, g = st.columns([1, 2.2], gap="small")
        with m:
            metric_card(get_metric_name(df, "metric_smr_4") + " (неделя)",
                        fmt_num(v_4, "", 2),
                        delta=fmt_delta(p_4), delta_dir=d_4 or "up", style="lime")
            metric_card(get_metric_name(df, "metric_smr_5") + " (неделя)",
                        fmt_num(v_5, "", 2),
                        delta=fmt_delta(p_5), delta_dir=d_5 or "up", style="yellow")
        with g:
            with chart_card():
                chart_title("Качество работы с отклонениями", tooltip="Динамика за 3 месяца")
                s_4 = get_series(df, "metric_smr_4", df3m_from, eff_to)
                s_5 = get_series(df, "metric_smr_5", df3m_from, eff_to)
                all_w = sorted(set(s_4["date_end"].tolist()) | set(s_5["date_end"].tolist()))
                x_lbl = [d.strftime("%d.%m") for d in all_w]
                map_4 = dict(zip(s_4["date_end"], s_4["value_s"]))
                map_5 = dict(zip(s_5["date_end"], s_5["value_s"]))
                y_4 = [map_4.get(d) for d in all_w]
                y_5 = [map_5.get(d) for d in all_w]
                n4 = get_metric_name(df, "metric_smr_4")
                n5 = get_metric_name(df, "metric_smr_5")
                f_q = go.Figure()
                f_q.add_trace(go.Bar(name=n4, x=x_lbl, y=y_4,
                    marker_color=LIME, opacity=0.9,
                    hovertemplate="<b>%{x}</b><br>"+n4+": %{y:.2f}<extra></extra>"))
                f_q.add_trace(go.Bar(name=n5, x=x_lbl, y=y_5,
                    marker_color=YELLOW, opacity=0.9,
                    hovertemplate="<b>%{x}</b><br>"+n5+": %{y:.2f}<extra></extra>"))
                f_q.update_layout(
                    height=210, margin=dict(t=14, b=32, l=42, r=8),
                    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                    font=dict(size=10, color=GREY_TXT),
                    barmode="group", bargap=0.25, bargroupgap=0.05,
                    showlegend=True,
                    legend=dict(orientation="h", y=1.14, x=0, font=dict(size=9)),
                    xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                    yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
                )
                st.plotly_chart(f_q, use_container_width=True, config={"displayModeBar": False})

    with q2:
        g, m = st.columns([2.2, 1], gap="small")
        with g:
            with chart_card():
                chart_title("Задачи", tooltip="Динамика за 3 месяца")
                s_38 = get_series(df, "metric_smr_38", df3m_from, eff_to)
                s_39 = get_series(df, "metric_smr_39", df3m_from, eff_to)
                all_w = sorted(set(s_38["date_end"].tolist()) | set(s_39["date_end"].tolist()))
                x_lbl = [d.strftime("%d.%m") for d in all_w]
                map_38 = dict(zip(s_38["date_end"], s_38["value_s"]))
                map_39 = dict(zip(s_39["date_end"], s_39["value_s"]))
                y_38 = [map_38.get(d) for d in all_w]
                y_39 = [map_39.get(d) for d in all_w]
                n38 = get_metric_name(df, "metric_smr_38")
                n39 = get_metric_name(df, "metric_smr_39")
                f_t = go.Figure()
                f_t.add_trace(go.Bar(name=n38, x=x_lbl, y=y_38,
                    marker_color=DARK_GREEN, opacity=0.9,
                    hovertemplate="<b>%{x}</b><br>"+n38+": %{y:,.0f}<extra></extra>"))
                f_t.add_trace(go.Bar(name=n39, x=x_lbl, y=y_39,
                    marker_color=LIME, opacity=0.9,
                    hovertemplate="<b>%{x}</b><br>"+n39+": %{y:,.0f}<extra></extra>"))
                f_t.update_layout(
                    height=210, margin=dict(t=14, b=32, l=42, r=8),
                    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                    font=dict(size=10, color=GREY_TXT),
                    barmode="stack", bargap=0.3,
                    showlegend=True,
                    legend=dict(orientation="h", y=1.14, x=0, font=dict(size=9)),
                    xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                    yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
                )
                st.plotly_chart(f_t, use_container_width=True, config={"displayModeBar": False})
        with m:
            metric_card("Кол-во родит.задач (неделя)",
                        fmt_num(v_38),
                        delta=fmt_delta(p_38), delta_dir=d_38 or "up", style="dark-green")
            metric_card("Кол-во эскалированных (неделя)",
                        fmt_num(v_39),
                        delta=fmt_delta(p_39), delta_dir=d_39 or "up", style="lime")

    st.markdown("<hr style='margin:8px 0 12px;border:none;border-top:1px solid #D8E8D0;'>",
                unsafe_allow_html=True)

    # ════ Q3 + Q4: Q3 = метрики 1,11 + график "Отклонения"; Q4 = график "Кол-во сотрудников/ВСП" + метрики 3, 2 ════
    q3, q4 = st.columns([1, 1], gap="large")

    with q3:
        m, g = st.columns([1, 2.2], gap="small")
        with m:
            metric_card("Количество видов отклонений (неделя)",
                        fmt_num(v_1),
                        delta=delta_1_str, delta_dir=dir_1, style="dark-green",
                        right_text=right_1)
            metric_card(get_metric_name(df, "metric_smr_11") + " (неделя)",
                        fmt_num(v_11),
                        delta=fmt_delta(p_11), delta_dir=d_11 or "up", style="yellow")
        with g:
            with chart_card():
                chart_title("Отклонения", tooltip="Динамика за 3 месяца")
                s_1  = get_series(df, "metric_smr_1",  df3m_from, eff_to)
                s_11 = get_series(df, "metric_smr_11", df3m_from, eff_to)
                all_w = sorted(set(s_1["date_end"].tolist()) | set(s_11["date_end"].tolist()))
                x_lbl = [d.strftime("%d.%m") for d in all_w]
                map_1  = dict(zip(s_1["date_end"],  s_1["value_s"]))
                map_11 = dict(zip(s_11["date_end"], s_11["value_s"]))
                y_1  = [map_1.get(d)  for d in all_w]
                y_11 = [map_11.get(d) for d in all_w]
                n1  = get_metric_name(df, "metric_smr_1")
                n11 = get_metric_name(df, "metric_smr_11")
                # area chart как в примере (Area chart): плавные линии + заливка
                AREA_GREEN  = "#2A7E2E"
                AREA_YELLOW = "#F2C014"
                f_dev = go.Figure()
                f_dev.add_trace(go.Scatter(
                    name=n11, x=x_lbl, y=y_11,
                    mode="lines+markers",
                    line=dict(color=AREA_YELLOW, width=2.5, shape="spline", smoothing=1.0),
                    marker=dict(size=5, color=AREA_YELLOW),
                    fill="tozeroy",
                    fillcolor="rgba(242,192,20,0.25)",
                    hovertemplate="<b>%{x}</b><br>"+n11+": %{y:,.0f}<extra></extra>",
                ))
                f_dev.add_trace(go.Scatter(
                    name=n1, x=x_lbl, y=y_1,
                    mode="lines+markers",
                    line=dict(color=AREA_GREEN, width=2.5, shape="spline", smoothing=1.0),
                    marker=dict(size=5, color=AREA_GREEN),
                    fill="tozeroy",
                    fillcolor="rgba(42,126,46,0.25)",
                    hovertemplate="<b>%{x}</b><br>"+n1+": %{y:,.0f}<extra></extra>",
                ))
                f_dev.update_layout(
                    height=210, margin=dict(t=14, b=32, l=42, r=8),
                    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                    font=dict(size=10, color=GREY_TXT),
                    showlegend=True,
                    legend=dict(orientation="h", y=1.14, x=0, font=dict(size=9)),
                    xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                    yaxis=dict(gridcolor=GRID, tickfont=dict(size=10), rangemode="tozero"),
                )
                st.plotly_chart(f_dev, use_container_width=True, config={"displayModeBar": False})

    with q4:
        g, m = st.columns([2.2, 1], gap="small")
        with g:
            with chart_card():
                chart_title("Кол-во сотрудников / ВСП", tooltip="Динамика за 3 месяца")
                s_3 = get_series(df, "metric_smr_3", df3m_from, eff_to)
                s_2 = get_series(df, "metric_smr_2", df3m_from, eff_to)
                all_w = sorted(set(s_3["date_end"].tolist()) | set(s_2["date_end"].tolist()))
                x_lbl = [d.strftime("%d.%m") for d in all_w]
                map_3 = dict(zip(s_3["date_end"], s_3["value_s"]))
                map_2 = dict(zip(s_2["date_end"], s_2["value_s"]))
                y_3 = [map_3.get(d) for d in all_w]
                y_2 = [map_2.get(d) for d in all_w]
                n3 = get_metric_name(df, "metric_smr_3")
                n2 = get_metric_name(df, "metric_smr_2")
                f_pv = go.Figure()
                f_pv.add_trace(go.Scatter(name=n3, x=x_lbl, y=y_3, mode="lines+markers",
                    line=dict(color=GREEN, width=2.5),
                    marker=dict(size=6, color=GREEN),
                    hovertemplate="<b>%{x}</b><br>"+n3+": %{y:,.0f}<extra></extra>"))
                f_pv.add_trace(go.Scatter(name=n2, x=x_lbl, y=y_2, mode="lines+markers",
                    line=dict(color=ORANGE, width=2.5),
                    marker=dict(size=6, color=ORANGE),
                    hovertemplate="<b>%{x}</b><br>"+n2+": %{y:,.0f}<extra></extra>"))
                f_pv.update_layout(
                    height=210, margin=dict(t=14, b=32, l=42, r=8),
                    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                    font=dict(size=10, color=GREY_TXT),
                    showlegend=True,
                    legend=dict(orientation="h", y=1.14, x=0, font=dict(size=9)),
                    xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                    yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
                )
                st.plotly_chart(f_pv, use_container_width=True, config={"displayModeBar": False})
        with m:
            metric_card("Количество сотрудников с отклонениями (неделя)",
                        fmt_num(v_3),
                        delta=fmt_delta(p_3), delta_dir=d_3 or "up", style="green",
                        right_text=right_3)
            metric_card("Кол-во ВСП с отклонениями (неделя)",
                        fmt_num(v_2),
                        delta=fmt_delta(p_2), delta_dir=d_2 or "up", style="orange",
                        right_text=right_2)

    # ── кнопки внизу страницы: Скачать слева, Обновить справа ──────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    dl_col, _spacer, rf_col = st.columns([1.5, 7, 1.5])
    with dl_col:
        render_export_button(
            df,
            ["metric_smr_1","metric_smr_11","metric_smr_3","metric_smr_2",
             "metric_smr_38","metric_smr_39","metric_smr_4","metric_smr_5",
             "metric_smr_10","metric_smr_7"],
            eff_from, eff_to,
            key="dl_summary", file_label="Саммари"
        )
    with rf_col:
        render_refresh_button("refresh_summary")


# ══════════════════════════════════════════════════════════════════════════
# СТРАНИЦА: БМО
# ══════════════════════════════════════════════════════════════════════════
else:
    d1c, d2c, weeks_col = st.columns([1.1, 1.1, 6.8])
    with d1c:
        date_from = st.date_input("Период с", value=default_from,
                                  min_value=min_d, max_value=max_d,
                                  format="DD.MM.YYYY", key="bd_from")
    with d2c:
        date_to = st.date_input("по", value=max_d,
                                min_value=min_d, max_value=max_d,
                                format="DD.MM.YYYY", key="bd_to")
    with weeks_col:
        eff_from_b, eff_to_b = render_weeks_buttons(df, date_from, date_to, "bmo")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── значения метрик БМО (все из value_s) ───────────────────────────
    v_46, p_46, d_46 = get_delta(df, "metric_smr_46", eff_from_b, eff_to_b)  # Доля по Банку
    v_45             = get_period_value(df, "metric_smr_45", eff_from_b, eff_to_b)  # Целевое
    v_40, p_40, d_40 = get_delta(df, "metric_smr_40", eff_from_b, eff_to_b)
    v_41, p_41, d_41 = get_delta(df, "metric_smr_41", eff_from_b, eff_to_b)
    v_34, p_34, d_34 = get_delta(df, "metric_smr_34", eff_from_b, eff_to_b)
    v_10, p_10, d_10 = get_delta(df, "metric_smr_10", eff_from_b, eff_to_b)
    v_7,  p_7,  d_7  = get_delta(df, "metric_smr_7",  eff_from_b, eff_to_b)
    v_9              = get_period_value(df, "metric_smr_9", eff_from_b, eff_to_b)
    v_8              = get_period_value(df, "metric_smr_8", eff_from_b, eff_to_b)
    v_35, p_35, d_35 = get_delta(df, "metric_smr_35", eff_from_b, eff_to_b)

    def bmo_card(label, value, delta, delta_dir, accent):
        col = GREEN if delta_dir == "up" else ORANGE
        arrow = "▲" if delta_dir == "up" else "▼"
        delta_html = (f'<div style="font-size:10px;font-weight:600;color:{col};margin-top:auto;">{arrow} {delta}</div>'
                      if delta else '<div style="margin-top:auto;height:13px;"></div>')
        return f"""
        <div style="background:#fff;border:0.5px solid #E0E0DA;border-radius:10px;
                    padding:9px 11px;border-left:3px solid {accent};
                    height:96px;display:flex;flex-direction:column;">
          <div style="font-size:10px;color:{GREY_TXT};line-height:1.25;margin-bottom:4px;min-height:26px;">{label}</div>
          <div style="font-size:18px;font-weight:600;color:{BLACK};">{value}</div>
          {delta_html}
        </div>"""

    qty_pair = (f"{fmt_num(v_40)} / {fmt_num(v_41)}"
                if v_40 is not None and v_41 is not None else "—")
    chel_vsp = (f"{fmt_num(v_9)} / {fmt_num(v_8)}"
                if v_9 is not None and v_8 is not None else "—")

    cards = [
        ("Доля по Банку",              fmt_num(v_46, "%", 1),                    fmt_delta(p_46), d_46 or "up", GREEN),
        ("Целевое значение",           fmt_num(v_45, "%", 1) if v_45 is not None else "—", "", "up", "#5F5E5A"),
        ("Кол-во родит.задач / эскалированных", qty_pair,                       fmt_delta(p_40), d_40 or "up", YELLOW),
        ("Пораженность",               fmt_num(v_10, "%", 1),                    fmt_delta(p_10), d_10 or "up", GREEN),
        ("Средний счётчик повторов",   fmt_num(v_7, "", 2),                      fmt_delta(p_7),  d_7 or "up",  ORANGE),
        ("Кол-во объектов: Сотрудников / ВСП", chel_vsp,                          "",              "up",         DARK_GREEN),
    ]
    cols = st.columns(6)
    for c_, (lbl, v, d, dr, ac) in zip(cols, cards):
        with c_:
            st.markdown(bmo_card(lbl, v, d, dr, ac), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    g_col, q_col = st.columns([1, 1], gap="large")

    with g_col:
        # ── График 1: Доля по Банку / Целевое значение ──
        with chart_card():
            chart_title("Доля по Банку / Целевое значение", tooltip="Динамика за 3 месяца")
            df3m_from_b = (pd.Timestamp(eff_to_b) - pd.DateOffset(months=3)).date()
            s_46 = get_series(df, "metric_smr_46", df3m_from_b, eff_to_b)
            s_45 = get_series(df, "metric_smr_45", df3m_from_b, eff_to_b)
            all_d = sorted(set(s_46["date_end"].tolist()) | set(s_45["date_end"].tolist()))
            x_lbl = [d.strftime("%d.%m") for d in all_d]
            map_46 = dict(zip(s_46["date_end"], s_46["value_s"]))
            map_45 = dict(zip(s_45["date_end"], s_45["value_s"]))
            y_46 = [map_46.get(d) for d in all_d]
            y_45 = [map_45.get(d) for d in all_d]
            # Если данных мало — расширяем категориальную ось с отступом слева,
            # столбец становится умеренной ширины и не прижат к краю
            n_pts = max(len(x_lbl), 1)
            if n_pts == 1:
                xaxis_cfg = dict(
                    type="category", gridcolor=GRID, tickfont=dict(size=10),
                    range=[-1.0, 4.0],
                )
                bar_width = [0.7]
            elif n_pts <= 3:
                xaxis_cfg = dict(
                    type="category", gridcolor=GRID, tickfont=dict(size=10),
                    range=[-0.7, max(5.5, n_pts + 2)],
                )
                bar_width = [0.7] * n_pts
            else:
                xaxis_cfg = dict(type="category", gridcolor=GRID, tickfont=dict(size=10))
                bar_width = [0.45] * n_pts
    
            f5 = go.Figure()
            f5.add_trace(go.Bar(name="Доля БМО, %", x=x_lbl, y=y_46,
                marker_color=GREEN, opacity=0.85,
                width=bar_width,
                hovertemplate="<b>%{x}</b><br>Доля БМО: %{y:.1f}%<extra></extra>"))
            f5.add_trace(go.Scatter(name="Целевое значение", x=x_lbl, y=y_45,
                mode="lines+markers",
                line=dict(color=ORANGE, width=2.5, dash="dash"),
                marker=dict(size=6, color=ORANGE),
                hovertemplate="<b>%{x}</b><br>Цель: %{y:.1f}%<extra></extra>"))
            f5.update_layout(
                height=240, margin=dict(t=10, b=30, l=42, r=8),
                paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                font=dict(size=10, color=GREY_TXT),
                bargap=0.4,
                showlegend=True,
                legend=dict(orientation="h", y=1.14, x=0, font=dict(size=10)),
                xaxis=xaxis_cfg,
                yaxis=dict(gridcolor=GRID, tickfont=dict(size=10), ticksuffix="%"),
            )
            st.plotly_chart(f5, use_container_width=True, config={"displayModeBar": False})

    with q_col:
        # ── График 2: Качество работы с отклонениями (10 и 7) ──
        with chart_card():
            chart_title("Качество работы с отклонениями: пораженность и счётчик повторов", tooltip="Динамика за 3 месяца")
            df3m_from = (pd.Timestamp(eff_to_b) - pd.DateOffset(months=3)).date()
            s_10 = get_series(df, "metric_smr_10", df3m_from, eff_to_b)
            s_7  = get_series(df, "metric_smr_7",  df3m_from, eff_to_b)
            all_w = sorted(set(s_10["date_end"].tolist()) | set(s_7["date_end"].tolist()))
            x_lbl2 = [d.strftime("%d.%m") for d in all_w]
            map_10 = dict(zip(s_10["date_end"], s_10["value_s"]))
            map_7  = dict(zip(s_7["date_end"],  s_7["value_s"]))
            y_10 = [map_10.get(d) for d in all_w]
            y_7  = [map_7.get(d)  for d in all_w]
            n10 = get_metric_name(df, "metric_smr_10")
            n7  = get_metric_name(df, "metric_smr_7")
            fQ = go.Figure()
            # Чтобы две метрики на разных осях шли рядом, используем offsetgroup
            fQ.add_trace(go.Bar(name=n10, x=x_lbl2, y=y_10,
                marker_color=GREEN, opacity=0.9,
                offsetgroup="g1", yaxis="y1",
                hovertemplate="<b>%{x}</b><br>"+n10+": %{y:.2f}<extra></extra>"))
            fQ.add_trace(go.Bar(name=n7, x=x_lbl2, y=y_7,
                marker_color=YELLOW, opacity=0.9,
                offsetgroup="g2", yaxis="y2",
                hovertemplate="<b>%{x}</b><br>"+n7+": %{y:.2f}<extra></extra>"))
            fQ.update_layout(
                height=240, margin=dict(t=10, b=30, l=42, r=46),
                paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                font=dict(size=10, color=GREY_TXT),
                barmode="group", bargap=0.25, bargroupgap=0.05,
                showlegend=True,
                legend=dict(orientation="h", y=1.14, x=0, font=dict(size=9)),
                xaxis=dict(type="category", gridcolor=GRID, tickfont=dict(size=10)),
                yaxis=dict(gridcolor=GRID, tickfont=dict(size=10)),
                yaxis2=dict(overlaying="y", side="right",
                            gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10)),
            )
            st.plotly_chart(fQ, use_container_width=True, config={"displayModeBar": False})

    # ── кнопки внизу страницы: Скачать слева, Обновить справа ──────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    dl_col, _spacer, rf_col = st.columns([1.5, 7, 1.5])
    with dl_col:
        render_export_button(
            df,
            ["metric_smr_46","metric_smr_45","metric_smr_40","metric_smr_41",
             "metric_smr_34","metric_smr_10","metric_smr_7","metric_smr_9",
             "metric_smr_8","metric_smr_35"],
            eff_from_b, eff_to_b,
            key="dl_bmo", file_label="БМО"
        )
    with rf_col:
        render_refresh_button("refresh_bmo")
