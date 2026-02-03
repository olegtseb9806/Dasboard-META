# -*- coding: utf-8 -*-
"""
Загрузка данных из 4 Google Таблиц или из CSV.
Нормализация в общий формат: employee, project, date, source.
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd

# Конфиг источников: spreadsheet_id, sheet_name, индексы колонок (0-based), есть ли статус
SOURCES = [
    {
        "id": "1DaiRFqU2d_85cXr0fDmyhzIY4V9fm0zxh4KraZMOFnw",
        "sheet": "СНГ Outreach",
        "name": "MR Anchors",
        "status_col": 1,
        "project_col": 3,
        "version_col": 4,
        "employee_col": 5,
        "date_col": 8,
        "status_ok": ["Готово"],
    },
    {
        "id": "1v_cheF0k0UCl9CniUWu-pTTYbl0CIOjE0BH0rzW3HXE",
        "sheet": "Размещенные ссылки",
        "name": "Основная РФ и СНГ",
        "status_col": None,
        "project_col": 1,
        "version_col": 2,
        "employee_col": 3,
        "date_col": 6,
        "status_ok": None,
    },
    {
        "id": "1S5lk-ya4iWwq5znY_vebAuTqloyTlWTcsNuXydZXT00",
        "sheet": "Outreach",
        "name": "TelecomAsia",
        "status_col": 4,
        "project_col": 1,
        "version_col": 2,
        "employee_col": 3,
        "date_col": 5,
        "status_ok": ["Готово"],
    },
    {
        "id": "1yj3eWqTpjxZFU0e9yg5A6TIh79N-s9g1Zmz3U-Q_54E",
        "sheet": "Posted links",
        "name": "International",
        "status_col": 4,
        "project_col": 1,
        "version_col": 2,
        "employee_col": 3,
        "date_col": 5,
        "status_ok": ["Готово"],
    },
]

# Форматы дат для парсинга
DATE_FORMATS = [
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S",
    "%d.%m.%Y %H:%M",
]


def _creds_to_dict(creds_path):
    """Преобразовать creds_path (файл, dict или JSON-строка) в dict с ключами сервисного аккаунта."""
    import json
    if creds_path is None:
        return None
    if isinstance(creds_path, dict):
        return creds_path
    if isinstance(creds_path, str) and creds_path.strip().startswith("{"):
        return json.loads(creds_path)
    path = Path(creds_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_service_account_email(creds_path):
    """Прочитать client_email из service_account (файл, dict или JSON-строка). Нужен для подсказки «Поделиться»."""
    data = _creds_to_dict(creds_path)
    return (data.get("client_email") or None) if data else None


def parse_date(value):
    """Парсинг даты из ячейки. Возвращает date или None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s[:10] if len(s) > 10 else s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_row(row, cfg, source_name):
    """Из списка ячеек строки извлечь employee, project, date. Вернуть dict или None."""
    try:
        employee = row[cfg["employee_col"]] if cfg["employee_col"] < len(row) else ""
        project = row[cfg["project_col"]] if cfg["project_col"] < len(row) else ""
        version = row[cfg["version_col"]] if cfg["version_col"] < len(row) else ""
        date_val = row[cfg["date_col"]] if cfg["date_col"] < len(row) else ""
    except (IndexError, KeyError, TypeError):
        return None
    employee = str(employee).strip() if employee else ""
    project = str(project).strip() if project else ""
    version = str(version).strip() if version else ""
    if not employee and not project:
        return None
    date_parsed = parse_date(date_val)
    if cfg["status_col"] is not None and cfg["status_ok"] and cfg["status_col"] < len(row):
        status = str(row[cfg["status_col"]]).strip()
        if status not in cfg["status_ok"]:
            return None
    project_label = f"{project} {version}".strip() if version else project
    return {
        "employee": employee or "—",
        "project": project_label or "—",
        "date": date_parsed,
        "source": source_name,
    }


def load_from_gsheet(cfg, creds_path=None):
    """Загрузить один лист через gspread. creds_path — путь к JSON, dict или JSON-строка. Возвращает list[dict]."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return []
    scope = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    source = creds_path or os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH") or "service_account.json"
    info = _creds_to_dict(source)
    if info:
        creds = Credentials.from_service_account_info(info, scopes=scope)
    else:
        path = Path(source)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        if not path.exists():
            return []
        creds = Credentials.from_service_account_file(str(path), scopes=scope)
    gc = gspread.authorize(creds)
    try:
        sh = gc.open_by_key(cfg["id"])
        ws = sh.worksheet(cfg["sheet"])
        rows = ws.get_all_values()
    except Exception:
        return []
    if len(rows) < 2:
        return []
    out = []
    for r in rows[1:]:
        rec = normalize_row(r, cfg, cfg["name"])
        if rec and rec["date"]:
            out.append(rec)
    return out


def load_all_from_gsheets(creds_path=None, which=None):
    """Загрузить все 4 источника из Google Sheets. which = список индексов 0..3 или None = все."""
    which = which if which is not None else [0, 1, 2, 3]
    all_records = []
    for i in which:
        if i < 0 or i >= len(SOURCES):
            continue
        recs = load_from_gsheet(SOURCES[i], creds_path=creds_path)
        all_records.extend(recs)
    return all_records


def load_from_dataframe(df, source_name, project_col="Проект", version_col="Версия", employee_col="Линкбилдер", date_col="Дата публикации", status_col=None, status_ok=None):
    """Из DataFrame (например из CSV) извлечь записи. Колонки могут называться по-русски или по-английски."""
    # Нормализация названий колонок (в экспорте из Sheets бывают переносы строк)
    df = df.copy()
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    # Попытка найти колонки по разным именам
    def find_col(candidates):
        for c in candidates:
            if c in df.columns:
                return df[c]
        return None
    employee_ser = find_col([employee_col, "Linkbuilder", "Линкбилдер", "Сотрудник"])
    project_ser = find_col([project_col, "Project", "Проект"])
    version_ser = find_col([version_col, "Версия проекта", "Версия"])
    date_ser = find_col([date_col, "Date of posting", "Date", "Дата публикации", "Дата"])
    status_ser = find_col([status_col, "Status", "Статус"]) if status_col or status_ok else None
    if employee_ser is None or date_ser is None:
        return []
    out = []
    for i in range(len(df)):
        emp = str(employee_ser.iloc[i]).strip() if pd.notna(employee_ser.iloc[i]) else ""
        proj = str(project_ser.iloc[i]).strip() if project_ser is not None and pd.notna(project_ser.iloc[i]) else ""
        ver = str(version_ser.iloc[i]).strip() if version_ser is not None and pd.notna(version_ser.iloc[i]) else ""
        if status_ok and status_ser is not None:
            st = str(status_ser.iloc[i]).strip() if pd.notna(status_ser.iloc[i]) else ""
            if st not in status_ok:
                continue
        dt = parse_date(date_ser.iloc[i])
        if not dt:
            continue
        project_label = f"{proj} {ver}".strip() if ver else proj
        out.append({"employee": emp or "—", "project": project_label or "—", "date": dt, "source": source_name})
    return out


def records_to_dataframe(records):
    """Список dict с полями employee, project, date, source -> DataFrame."""
    if not records:
        return pd.DataFrame(columns=["employee", "project", "date", "source"])
    return pd.DataFrame(records)


def filter_by_period(df, date_from, date_to):
    """Оставить строки с date в [date_from, date_to] включительно."""
    if df.empty or "date" not in df.columns:
        return df
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    if date_from:
        df = df[df["date"] >= date_from]
    if date_to:
        df = df[df["date"] <= date_to]
    return df
