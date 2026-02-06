# -*- coding: utf-8 -*-
"""
Дашборд: размещения ссылок по сотрудникам и проектам за период.
Запуск: streamlit run app/dashboard/app.py  (из корня проекта)
"""
import sys
from pathlib import Path

# Чтобы импорт app.dashboard находился при запуске app/dashboard/app.py
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import date, timedelta

import streamlit as st
import pandas as pd

from app.dashboard.data_loader import (
    SOURCES,
    get_service_account_email,
    load_all_from_gsheets,
    load_from_dataframe,
    records_to_dataframe,
    filter_by_period,
)
from app.dashboard.aggregates import by_employee, by_project, pivot_employee_project, last_placements
from app.dashboard import charts

# Путь к ключу Google (от корня проекта)
CREDS_PATH = _PROJECT_ROOT / "service_account.json"


def _get_creds_source():
    """Источник учётных данных: секреты (облако), env или файл. Локально без secrets.toml — используем файл."""
    try:
        if hasattr(st, "secrets") and st.secrets.get("service_account_json"):
            return st.secrets["service_account_json"]
    except Exception:
        pass  # Локально нет secrets.toml — переходим к файлу или env
    import os
    if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if CREDS_PATH.exists():
        return str(CREDS_PATH)
    creds_alt = _PROJECT_ROOT / "service_account.json.json"  # двойное расширение в Windows
    if creds_alt.exists():
        return str(creds_alt)
    return None


def get_date_range(period_type, month, year, date_from, date_to):
    """Вычислить date_from и date_to по выбору пользователя."""
    today = date.today()
    if period_type == "Неделя":
        date_to = today
        date_from = today - timedelta(days=6)
        return date_from, date_to
    if period_type == "Месяц":
        if month and year:
            # первый и последний день месяца
            from calendar import monthrange
            _, last = monthrange(year, month)
            date_from = date(year, month, 1)
            date_to = date(year, month, last)
        else:
            date_from = date(today.year, today.month, 1)
            date_to = today
        return date_from, date_to
    if period_type == "Произвольный период":
        return (date_from or today), (date_to or today)
    return today - timedelta(days=6), today


def main():
    st.set_page_config(page_title="Дашборд: ссылки по сотрудникам и проектам", layout="wide")
    st.title("Дашборд: размещения ссылок по сотрудникам и проектам")

    # --- Фильтры ---
    period_type = st.selectbox(
        "Период",
        ["Неделя", "Месяц", "Произвольный период"],
        index=0,
    )
    date_from_widget = None
    date_to_widget = None
    month_widget = None
    year_widget = None
    if period_type == "Месяц":
        today = date.today()
        year_widget = st.number_input("Год", min_value=2020, max_value=2030, value=today.year)
        month_widget = st.number_input("Месяц", min_value=1, max_value=12, value=today.month)
    elif period_type == "Произвольный период":
        date_from_widget = st.date_input("Дата с", value=date.today() - timedelta(days=30))
        date_to_widget = st.date_input("Дата по", value=date.today())

    # Всегда только 2 таблицы: MR Anchors и TelecomAsia (без выбора в интерфейсе)
    which_sources = None  # все из SOURCES

    # Загрузка данных: сначала пробуем Google Sheets (файл, секреты или env)
    creds_source = _get_creds_source()
    df_raw = None
    if creds_source:
        with st.spinner("Загрузка из Google Таблиц..."):
            recs = load_all_from_gsheets(creds_path=creds_source, which=which_sources)
            df_raw = records_to_dataframe(recs)
    if not creds_source:
        st.info(
            "**Минимум:** 1) [Google Cloud → Credentials](https://console.cloud.google.com/apis/credentials) → Create Credentials → Service account → Keys → JSON. "
            "Файл сохрани как `service_account.json` в `c:\\project\\anchor_checker`. "
            "2) В каждой из 2 таблиц нажми «Поделиться» и добавь email из JSON (строка `client_email`) с правом «Читатель». "
            "Email можно увидеть командой: `python show_share_email.py`. Подробно — файл **docs/МИНИМУМ_ДЕЙСТВИЙ.md** в проекте."
        )
        uploaded = st.file_uploader("Или загрузи CSV листов (СНГ Outreach, Outreach)", type="csv", accept_multiple_files=True)
        if uploaded:
            all_recs = []
            names = ["MR Anchors", "TelecomAsia"]
            for i, f in enumerate(uploaded):
                try:
                    df_up = pd.read_csv(f, encoding="utf-8")
                except Exception:
                    df_up = pd.read_csv(f, encoding="cp1251")
                name = names[i] if i < len(names) else f.name
                recs = load_from_dataframe(df_up, name, status_ok=["Готово"])
                all_recs.extend(recs)
            df_raw = records_to_dataframe(all_recs)

    if df_raw is None or df_raw.empty:
        share_email = get_service_account_email(creds_source) if creds_source else get_service_account_email(CREDS_PATH) if CREDS_PATH.exists() else None
        if share_email:
            st.warning(
                "Данных нет. В каждой из 2 таблиц нажми **«Поделиться»** и добавь этот email с правом **«Читатель»:**\n\n"
                f"**{share_email}**"
            )
            st.markdown(
                "[MR Anchors (СНГ Outreach)](https://docs.google.com/spreadsheets/d/1DaiRFqU2d_85cXr0fDmyhzIY4V9fm0zxh4KraZMOFnw/edit?gid=1088920242) · "
                "[TelecomAsia (Outreach)](https://docs.google.com/spreadsheets/d/1S5lk-ya4iWwq5znY_vebAuTqloyTlWTcsNuXydZXT00/edit?gid=728254189)"
            )
        else:
            st.warning("Нет данных. Положи `service_account.json` в корень проекта или загрузи CSV. См. **docs/МИНИМУМ_ДЕЙСТВИЙ.md**")
        return

    date_from, date_to = get_date_range(
        period_type,
        month_widget,
        year_widget,
        date_from_widget,
        date_to_widget,
    )
    df = filter_by_period(df_raw, date_from, date_to)
    st.caption(f"Период: {date_from} — {date_to}. Записей за период: {len(df)}")

    if df.empty:
        st.warning("За выбранный период записей нет.")
        return

    # --- Блок: по сотрудникам ---
    st.subheader("По сотрудникам")
    df_emp = by_employee(df)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(df_emp.rename(columns={"employee": "Сотрудник", "count": "Ссылок"}), use_container_width=True, hide_index=True)
    with col2:
        fig_emp = charts.bar_employees(df_emp)
        if fig_emp:
            st.plotly_chart(fig_emp, use_container_width=True)
        else:
            st.bar_chart(df_emp.set_index("employee"))

    # --- Блок: по проектам ---
    st.subheader("По проектам")
    df_proj = by_project(df)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(df_proj.rename(columns={"project": "Проект", "count": "Ссылок"}), use_container_width=True, hide_index=True)
    with col2:
        fig_proj = charts.bar_projects(df_proj)
        if fig_proj:
            st.plotly_chart(fig_proj, use_container_width=True)
        else:
            st.bar_chart(df_proj.set_index("project"))

    # --- Матрица сотрудник × проект ---
    st.subheader("Матрица: сотрудник × проект")
    pivot = pivot_employee_project(df)
    if not pivot.empty:
        st.dataframe(pivot.astype(int), use_container_width=True, hide_index=True)

    # --- Последние размещения ---
    st.subheader("Последние размещения")
    n_last = st.slider("Показать записей", 10, 100, 30)
    emp_filter = st.selectbox("Сотрудник (все)", ["— Все —"] + list(df["employee"].dropna().unique().tolist()))
    proj_filter = st.selectbox("Проект (все)", ["— Все —"] + list(df["project"].dropna().unique().tolist()))
    emp_f = None if emp_filter == "— Все —" else emp_filter
    proj_f = None if proj_filter == "— Все —" else proj_filter
    last_df = last_placements(df, n=n_last, employee_filter=emp_f, project_filter=proj_f)
    if not last_df.empty:
        show_cols = ["date", "employee", "project", "source"]
        show_cols = [c for c in show_cols if c in last_df.columns]
        st.dataframe(
            last_df[show_cols].rename(columns={"date": "Дата", "employee": "Сотрудник", "project": "Проект", "source": "Источник"}),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
