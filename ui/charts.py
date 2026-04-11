# ui/charts.py
from typing import Dict, Optional
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    color_col: str = None,
    threshold_line: float = None
) -> go.Figure:
    """通用長條圖，可選擇性加入門檻線"""
    fig = px.bar(df, x=x_col, y=y_col, title=title, color=color_col, text_auto=".1f")
    if threshold_line is not None:
        fig.add_hline(
            y=threshold_line,
            line_dash="dash",
            line_color="red",
            annotation_text=f"門檻 {threshold_line}",
            annotation_position="bottom right"
        )
    fig.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False)
    return fig


def distribution_chart(dist: Dict[str, int], title: str) -> go.Figure:
    """成績分布長條圖（五個區間）"""
    fig = go.Figure(go.Bar(
        x=list(dist.keys()),
        y=list(dist.values()),
        text=list(dist.values()),
        textposition="outside",
        marker_color=["#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6"]
    ))
    fig.update_layout(title=title, xaxis_title="分數區間", yaxis_title="人數", showlegend=False)
    return fig


def line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    group_col: str = None
) -> go.Figure:
    """折線圖，用於趨勢分析"""
    fig = px.line(df, x=x_col, y=y_col, title=title, color=group_col, markers=True)
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    return fig


def fail_rate_color(rate: float) -> str:
    """根據不及格比例回傳對應警示符號"""
    if rate >= 0.50:
        return "🔴"
    elif rate >= 0.30:
        return "🟡"
    return "🟢"
