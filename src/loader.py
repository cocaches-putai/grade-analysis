# src/loader.py
import re
from typing import List, Tuple
import pandas as pd

REQUIRED_SCORE_COLS = ["姓名", "年級", "班級"]
REQUIRED_ITEM_COLS = ["姓名", "年級", "班級", "科目"]
ITEM_COL_PREFIX = "題"

# 學校成績系統匯出格式中，已知的非科目欄位
_SCHOOL_NON_SUBJECT = {
    "座號", "學號", "姓名", "班級", "總分", "平均", "不及格數", "部修",
    "班排", "班群排", "學程排", "年排",
    "班級百分等級", "班群百分等級", "學程百分等級", "年百分等級",
}


def is_school_format(df: pd.DataFrame) -> bool:
    """判斷是否為學校成績系統原始匯出格式（無年級欄、班級值含「班」字）"""
    if "年級" in df.columns:
        return False
    classes = df["班級"].dropna().astype(str)
    return any("班" in c and "年" in c for c in classes)


def preprocess_school_excel(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    將學校成績系統原始匯出格式轉換為系統標準格式。
    回傳 (轉換後的 DataFrame, 警告訊息列表)
    """
    warnings: List[str] = []

    # 1. 過濾出有效學生列（班級含「班」字、姓名不為空、非表頭列）
    valid_mask = (
        df["班級"].astype(str).str.contains("班") &
        ~df["班級"].astype(str).str.strip().isin(["班級"]) &
        df["姓名"].notna()
    )
    df = df[valid_mask].copy()

    # 2. 識別科目欄（在加 年級 欄之前進行，避免誤判）
    subject_cols = [
        c for c in df.columns
        if c not in _SCHOOL_NON_SUBJECT
        and not str(c).startswith("Unnamed")
    ]

    # 3. 判斷高中 / 國中（庚班是高中獨有）
    has_geng = any("庚" in str(c) for c in df["班級"])
    prefix = "高" if has_geng else "國"

    # 4. 轉換班級名稱：'一年甲班' → '高一甲'
    _year_map = {"一年": "一", "二年": "二", "三年": "三"}

    def _map_class(raw: str) -> str:
        for y, n in _year_map.items():
            if raw.startswith(y):
                return prefix + n + raw[len(y):].replace("班", "")
        return raw

    df["班級"] = df["班級"].astype(str).apply(_map_class)

    # 5. 新增年級欄（取班級前兩字：'高一甲' → '高一'）
    df["年級"] = df["班級"].str[:2]

    # 6. 清理科目欄名稱：去除學期別（Ⅰ/Ⅱ等）及學分數（(4)等）
    def _clean_subject(col: str) -> str:
        col = re.sub(r"[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+", "", col)
        col = re.sub(r"\(.*?\)", "", col)
        return col.strip()

    rename_map = {c: _clean_subject(c) for c in subject_cols}
    df = df.rename(columns=rename_map)
    clean_subjects = list(rename_map.values())

    # 7. 去除分數前的 * 並轉為數值；超過 100 的值視為無效設為 NaN
    for col in clean_subjects:
        df[col] = df[col].astype(str).str.replace("*", "", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")
        out_of_range = (df[col] > 100).sum()
        if out_of_range > 0:
            warnings.append(
                f"「{col}」有 {out_of_range} 筆分數超過 100，已自動設為空值（可能是學校系統資料問題）"
            )
            df.loc[df[col] > 100, col] = None

    # 8. 只保留標準欄位
    keep_cols = ["姓名", "年級", "班級"] + clean_subjects
    return df[keep_cols].reset_index(drop=True), warnings


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
