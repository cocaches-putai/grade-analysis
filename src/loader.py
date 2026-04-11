# src/loader.py
from typing import List
import pandas as pd

REQUIRED_SCORE_COLS = ["姓名", "年級", "班級"]
REQUIRED_ITEM_COLS = ["姓名", "年級", "班級", "科目"]
ITEM_COL_PREFIX = "題"


def validate_scores_df(df: pd.DataFrame) -> List[str]:
    """驗證成績 DataFrame，回傳錯誤訊息列表（空列表表示無誤）"""
    errors = []
    for col in REQUIRED_SCORE_COLS:
        if col not in df.columns:
            errors.append(f"缺少必要欄位：{col}")
    subject_cols = [c for c in df.columns if c not in REQUIRED_SCORE_COLS]
    if not subject_cols:
        errors.append("找不到任何科目欄位，請確認欄位名稱")
        return errors
    for col in subject_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            out_of_range = df[(df[col] < 0) | (df[col] > 100)][col].dropna()
            if len(out_of_range) > 0:
                errors.append(f"欄位「{col}」有分數超出範圍（0-100）：共 {len(out_of_range)} 筆")
    return errors


def validate_items_df(df: pd.DataFrame) -> List[str]:
    """驗證試題得分 DataFrame"""
    errors = []
    for col in REQUIRED_ITEM_COLS:
        if col not in df.columns:
            errors.append(f"缺少必要欄位：{col}")
    item_cols = [c for c in df.columns if c.startswith(ITEM_COL_PREFIX)]
    if not item_cols:
        errors.append("找不到任何題目欄位（欄位名稱需以「題」開頭，如「題1」）")
    return errors


def load_scores_from_df(df: pd.DataFrame) -> pd.DataFrame:
    """清理並回傳標準化的成績 DataFrame"""
    df = df.copy()
    subject_cols = [c for c in df.columns if c not in REQUIRED_SCORE_COLS]
    for col in subject_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.reset_index(drop=True)


def load_items_from_df(df: pd.DataFrame) -> pd.DataFrame:
    """清理並回傳標準化的試題得分 DataFrame"""
    df = df.copy()
    item_cols = [c for c in df.columns if c.startswith(ITEM_COL_PREFIX)]
    for col in item_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.reset_index(drop=True)
