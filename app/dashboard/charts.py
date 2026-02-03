# -*- coding: utf-8 -*-
"""Построение графиков для дашборда (Plotly)."""

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def bar_employees(df_employees, title="Ссылок по сотрудникам", max_bars=30):
    """Столбчатая диаграмма по сотрудникам. df_employees: колонки employee, count."""
    if not HAS_PLOTLY or df_employees is None or df_employees.empty:
        return None
    df = df_employees.head(max_bars)
    fig = go.Figure(
        data=[go.Bar(x=df["employee"], y=df["count"], marker_color="#1f77b4", text=df["count"], textposition="outside")],
        layout=go.Layout(
            title=title,
            xaxis_title="Сотрудник",
            yaxis_title="Количество ссылок",
            height=400,
            margin=dict(b=120),
            xaxis_tickangle=-45,
        ),
    )
    return fig


def bar_projects(df_projects, title="Ссылок по проектам", max_bars=25):
    """Столбчатая диаграмма по проектам."""
    if not HAS_PLOTLY or df_projects is None or df_projects.empty:
        return None
    df = df_projects.head(max_bars)
    fig = go.Figure(
        data=[go.Bar(x=df["project"], y=df["count"], marker_color="#2ca02c", text=df["count"], textposition="outside")],
        layout=go.Layout(
            title=title,
            xaxis_title="Проект",
            yaxis_title="Количество ссылок",
            height=400,
            margin=dict(b=150),
            xaxis_tickangle=-45,
        ),
    )
    return fig


def pie_projects(df_projects, title="Доля по проектам", max_slices=15):
    """Круговая диаграмма по проектам."""
    if not HAS_PLOTLY or df_projects is None or df_projects.empty:
        return None
    df = df_projects.head(max_slices)
    fig = go.Figure(
        data=[go.Pie(labels=df["project"], values=df["count"], hole=0.4, textinfo="label+percent")],
        layout=go.Layout(title=title, height=400, margin=dict(t=40)),
    )
    return fig
