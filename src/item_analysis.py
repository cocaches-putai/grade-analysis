# src/item_analysis.py
from typing import List
import pandas as pd
import numpy as np

_META_COLS = ["姓名", "年級", "班級", "科目"]
_ITEM_PREFIX = "題"

P_TOO_HARD = 0.30
P_TOO_EASY = 0.80
D_LOW = 0.20


def get_item_cols(df: pd.DataFrame) -> List[str]:
    """回傳試題得分 DataFrame 中的題目欄位列表"""
    return [c for c in df.columns if c.startswith(_ITEM_PREFIX)]


def difficulty_index(df: pd.DataFrame, item_col: str) -> float:
    """難度指數 P = 答對率"""
    series = df[item_col].dropna()
    if len(series) == 0:
        return 0.0
    return round(float(series.mean()), 4)


def discrimination_index(df: pd.DataFrame, item_col: str) -> float:
    """
    鑑別度 D = 高分組答對率 - 低分組答對率
    高/低分組各取前後 27%（以所有題目總分排序）
    """
    item_cols = get_item_cols(df)
    df = df.copy()
    df["_total"] = df[item_cols].sum(axis=1)
    n = len(df)
    cutoff = max(1, int(n * 0.27))
    high_group = df.nlargest(cutoff, "_total")[item_col]
    low_group = df.nsmallest(cutoff, "_total")[item_col]
    if len(high_group) == 0 or len(low_group) == 0:
        return 0.0
    return round(float(high_group.mean() - low_group.mean()), 4)


def cronbach_alpha(df: pd.DataFrame) -> float:
    """Cronbach's α 信度係數"""
    item_cols = get_item_cols(df)
    if len(item_cols) < 2:
        return float("nan")
    data = df[item_cols].dropna()
    n_items = len(item_cols)
    item_variances = data.var(axis=0, ddof=1).sum()
    total_variance = data.sum(axis=1).var(ddof=1)
    if total_variance == 0:
        return 0.0
    alpha = (n_items / (n_items - 1)) * (1 - item_variances / total_variance)
    return round(float(alpha), 4)


def item_summary(df: pd.DataFrame) -> pd.DataFrame:
    """回傳所有題目的分析摘要，含難度、鑑別度、判定"""
    item_cols = get_item_cols(df)
    rows = []
    for col in item_cols:
        p = difficulty_index(df, col)
        d = discrimination_index(df, col)
        flags = []
        if p > P_TOO_EASY:
            flags.append("太易")
        elif p < P_TOO_HARD:
            flags.append("太難")
        if d < D_LOW:
            flags.append("鑑別度不足")
        判定 = "、".join(flags) if flags else "正常"
        rows.append({"題目": col, "難度P值": p, "鑑別度D值": d, "判定": 判定})
    return pd.DataFrame(rows)
