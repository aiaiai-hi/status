"""
Конвертер metrics.xlsx -> metrics.json
Запускается один раз вручную, когда обновляется исходный Excel:

    python convert_data.py

Скрипт читает лист "Выгрузка", оставляет нужные колонки и сохраняет
результат в metrics.json в корне приложения.
"""
import pandas as pd
import json
import sys
from pathlib import Path

SRC = "metrics.xlsx"
DST = "metrics.json"
SHEET = "Основное"


def convert():
    src_path = Path(SRC)
    if not src_path.exists():
        print(f"❌ Файл {SRC} не найден в текущей папке: {Path.cwd()}")
        sys.exit(1)

    print(f"📖 Читаю {SRC}, лист «{SHEET}»…")
    try:
        df = pd.read_excel(SRC, sheet_name=SHEET)
    except Exception as e:
        print(f"❌ Ошибка чтения: {e}")
        sys.exit(1)

    print(f"   Найдено строк: {len(df)}")
    print(f"   Колонки: {list(df.columns)[:10]}")

    # Оставляем нужные поля
    needed = ["date_end", "value_s", "metric_id", "metric_name"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print(f"❌ В листе нет колонок: {missing}")
        sys.exit(1)

    df = df[needed].copy()
    df = df.dropna(subset=["date_end", "value_s", "metric_id"])
    df["value_s"] = pd.to_numeric(df["value_s"], errors="coerce")
    df = df.dropna(subset=["value_s"])
    df["date_end"] = pd.to_datetime(df["date_end"]).dt.strftime("%Y-%m-%d")
    df["metric_id"] = df["metric_id"].astype(str)
    df["metric_name"] = df["metric_name"].fillna("").astype(str)

    records = df.to_dict(orient="records")

    out = {
        "version": 1,
        "source": SRC,
        "sheet": SHEET,
        "rows": len(records),
        "records": records,
    }

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✅ Сохранено {len(records)} записей в {DST}")
    print(f"   Уникальных метрик: {df['metric_id'].nunique()}")
    print(f"   Период: {df['date_end'].min()} — {df['date_end'].max()}")


if __name__ == "__main__":
    convert()
