# -*- coding: utf-8 -*-
"""Агрегаты для дашборда: по сотрудникам, по проектам, матрица."""

import pandas as pd


def by_employee(df):
    """Количество ссылок по сотрудникам. DataFrame с колонками employee, count."""
    if df.empty or "employee" not in df.columns:
        return pd.DataFrame(columns=["employee", "count"])
    g = df.groupby("employee", as_index=False).size()
    g = g.rename(columns={"size": "count"})
    return g.sort_values("count", ascending=False).reset_index(drop=True)


def by_project(df):
    """Количество ссылок по проектам. DataFrame с колонками project, count."""
    if df.empty or "project" not in df.columns:
        return pd.DataFrame(columns=["project", "count"])
    g = df.groupby("project", as_index=False).size()
    g = g.rename(columns={"size": "count"})
    return g.sort_values("count", ascending=False).reset_index(drop=True)


def pivot_employee_project(df):
    """Матрица: строки — сотрудники, столбцы — проекты, значения — число ссылок. Последний столбец — Итого."""
    if df.empty or "employee" not in df.columns or "project" not in df.columns:
        return pd.DataFrame()
    pt = df.pivot_table(index="employee", columns="project", aggfunc="size", fill_value=0)
    pt["Итого"] = pt.sum(axis=1)
    return pt


def last_placements(df, n=50, employee_filter=None, project_filter=None):
    """Последние n размещений (сортировка по дате убыв.). Опционально фильтр по сотруднику и проекту."""
    if df.empty:
        return df
    out = df.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"])
        out = out.sort_values("date", ascending=False)
    if employee_filter:
        out = out[out["employee"] == employee_filter]
    if project_filter:
        out = out[out["project"] == project_filter]
    return out.head(n)
