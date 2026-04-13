# src/loader.py
import re
from typing import List, Tuple
import pandas as pd

REQUIRED_SCORE_COLS = ["姓名", "年級", "班級"]
REQUIRED_ITEM_COLS = ["姓名", "年級", "班級", "科目"]
ITEM_COL_PREFIX = "題"

# 學校成績系統匯出格式中，已知的非科目欄位
_SCHOOL_META_COLS = {
    "座號", "學號", "姓名", "班級", "年級", "總分", "平均", "不及格數", "部修",
    "班排", "班群排", "學程排", "年排",
    "班級百分等級", "班群百分等級", "學程百分等級", "年百分等級",
    "選修",  # 「選修」是彙總欄，跳過
}

_YEAR_MAP = {"一年": "一", "二年": "二", "三年": "三"}


def is_school_format(df: pd.DataFrame) -> bool:
    """判斷是否為學校成績系統原始匯出格式（無年級欄、班級值含「班」字）"""
    if "年級" in df.columns:
        return False
    classes = df["班級"].dropna().astype(str)
    return any("班" in c and "年" in c for c in classes)


def _clean_subject_name(col: str) -> str:
    """'國語文Ⅱ(4)' → '國語文'，'選修物理-力Ⅰ(2)' → '選修物理-力'"""
    col = re.sub(r"[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+", "", col)
    col = re.sub(r"\(.*?\)", "", col)
    return col.strip()


def _map_class_name(raw: str, prefix: str) -> str:
    """'一年甲班' + '高' → '高一甲'"""
    for year_str, year_num in _YEAR_MAP.items():
        if raw.startswith(year_str):
            return prefix + year_num + raw[len(year_str):].replace("班", "")
    return raw


def preprocess_school_excel(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    將學校成績系統原始匯出格式轉換為系統標準格式。

    學校 Excel 的特殊結構：每個班級前都有一列獨立表頭（科目名稱不同），
    整份檔案按班級依序排列。本函式逐段解析各班的科目欄，再合併成一份寬表。

    回傳 (標準化 DataFrame, 警告訊息列表)
    """
    warnings: List[str] = []
    orig_cols = df.columns.tolist()

    # ── 找出內嵌表頭列（班級欄值 == '班級'）────────────────────────
    emb_header_positions = df.index[
        df["班級"].astype(str).str.strip() == "班級"
    ].tolist()

    # ── 建立各班段的 (起始列, 欄位名稱列表) ────────────────────────
    # 第一段：從第 0 列到第一個內嵌表頭之前，欄位名稱用 pd.read_excel 讀出的原始欄名
    section_defs: List[Tuple[int, List]] = [(0, orig_cols)]
    for h_pos in emb_header_positions:
        new_col_names = df.loc[h_pos].tolist()
        section_defs.append((h_pos + 1, new_col_names))

    # 各段的結束列（含）
    section_ends = emb_header_positions + [None]

    # ── 判斷高中 / 國中（庚班為高中獨有，需看全檔才能確定）────────
    all_classes = df["班級"].astype(str)
    school_prefix = "高" if any("庚" in c for c in all_classes) else "國"

    # ── 逐段處理 ──────────────────────────────────────────────────
    all_student_dfs = []

    for (sec_start, col_names), sec_end in zip(section_defs, section_ends):
        # 取出這一段的原始資料列
        raw = df.iloc[sec_start:sec_end].copy()

        # 將欄位位置對應到這段的實際科目名稱
        col_rename = {
            orig_cols[j]: str(col_names[j])
            for j in range(min(len(orig_cols), len(col_names)))
        }
        raw = raw.rename(columns=col_rename)
        # 去除重複欄名（如多個 Unnamed 都被重命名為 'nan'）
        raw = raw.loc[:, ~raw.columns.duplicated()]

        # 過濾有效學生列
        valid_mask = (
            raw["班級"].astype(str).str.contains("班", na=False)
            & raw["姓名"].notna()
        )
        students = raw[valid_mask].copy()
        if students.empty:
            continue

        # 轉換班級名稱並補建年級欄（prefix 已在迴圈外統一判斷）
        students["班級"] = students["班級"].astype(str).apply(
            lambda x: _map_class_name(x, school_prefix)
        )
        students["年級"] = students["班級"].str[:2]

        # 識別本段的科目欄（排除已知非科目欄及 Unnamed）
        subj_cols = [
            c for c in students.columns
            if c not in _SCHOOL_META_COLS
            and not str(c).startswith("Unnamed")
            and str(c).strip() not in ("nan", "")
        ]

        # 清理科目欄名稱
        rename_subj = {c: _clean_subject_name(c) for c in subj_cols}
        students = students.rename(columns=rename_subj)
        clean_subjs = list(rename_subj.values())

        # 去星號、轉數值、超過 100 設為 NaN
        for col in clean_subjs:
            students[col] = (
                students[col].astype(str).str.replace("*", "", regex=False)
            )
            students[col] = pd.to_numeric(students[col], errors="coerce")
            n_bad = int((students[col] > 100).sum())
            if n_bad > 0:
                class_name = students["班級"].iloc[0]
                warnings.append(
                    f"「{col}」（{class_name}）有 {n_bad} 筆分數超過 100，"
                    f"已設為空值（可能是不同班的科目名稱相同但內容不同）"
                )
                students.loc[students[col] > 100, col] = None

        keep = ["姓名", "年級", "班級"] + clean_subjs
        all_student_dfs.append(students[keep])

    if not all_student_dfs:
        return pd.DataFrame(columns=["姓名", "年級", "班級"]), warnings

    # 合併所有班段（各班科目不同，缺少的科目填 NaN）
    combined = pd.concat(all_student_dfs, ignore_index=True)
    return combined, warnings


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
