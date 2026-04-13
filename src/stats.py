# src/stats.py
from typing import Dict, List
import pandas as pd
import numpy as np
from config import (
    PASSING_SCORE, SCORE_BANDS, SCORE_BAND_LABELS,
    ALERT_ANOMALY_STD_MULTIPLIER
)

_META_COLS = ["姓名", "年級", "班級"]


def get_subject_cols(df: pd.DataFrame) -> List[str]:
    """回傳成績 DataFrame 中的科目欄位列表"""
    return [c for c in df.columns if c not in _META_COLS]


def class_stats(df: pd.DataFrame, grade_class: str, subject: str) -> Dict:
    """計算單一班級單一科目的統計摘要"""
    subset = df[df["班級"] == grade_class][subject].dropna()
    if subset.empty:
        return {
            "班級": grade_class, "科目": subject, "人數": 0,
            "平均": None, "最高分": None, "最低分": None,
            "標準差": None, "不及格人數": 0, "不及格比例": None,
        }
    fail_mask = subset < PASSING_SCORE
    return {
        "班級": grade_class,
        "科目": subject,
        "人數": len(subset),
        "平均": round(subset.mean(), 2),
        "最高分": int(subset.max()),
        "最低分": int(subset.min()),
        "標準差": round(subset.std(), 2),
        "不及格人數": int(fail_mask.sum()),
        "不及格比例": round(fail_mask.mean(), 4),
    }


def subject_distribution(df: pd.DataFrame, grade_class: str, subject: str) -> Dict[str, int]:
    """計算分數分布（五個區間）"""
    subset = df[df["班級"] == grade_class][subject].dropna()
    result = {}
    for (lo, hi), label in zip(SCORE_BANDS, SCORE_BAND_LABELS):
        result[label] = int(((subset >= lo) & (subset <= hi)).sum())
    return result


def student_rankings(df: pd.DataFrame, grade_class: str) -> pd.DataFrame:
    """計算班級內各科排名，回傳含排名欄位的 DataFrame"""
    subset = df[df["班級"] == grade_class].copy()
    subjects = get_subject_cols(df)
    for subj in subjects:
        subset[f"班級排名_{subj}"] = subset[subj].rank(ascending=False, method="min").astype("Int64")
    return subset.reset_index(drop=True)


def grade_rankings(df: pd.DataFrame, grade: str) -> pd.DataFrame:
    """計算年級內各科排名"""
    subset = df[df["年級"] == grade].copy()
    subjects = get_subject_cols(df)
    for subj in subjects:
        subset[f"年級排名_{subj}"] = subset[subj].rank(ascending=False, method="min").astype("Int64")
    return subset.reset_index(drop=True)


def detect_anomalies(df: pd.DataFrame, prev_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    偵測異常成績：
    1. 任一科分數低於班級平均 2 個標準差
    2. 若有上次資料，任一科與上次相差 >= 30 分
    回傳異常學生 DataFrame，含「異常原因」欄
    """
    subjects = get_subject_cols(df)
    anomaly_rows = []

    for subj in subjects:
        class_means = df.groupby("班級")[subj].transform("mean")
        class_stds = df.groupby("班級")[subj].transform("std").fillna(0)
        threshold = class_means - ALERT_ANOMALY_STD_MULTIPLIER * class_stds
        flagged = df[df[subj] < threshold].copy()
        if len(flagged) > 0:
            flagged = flagged.copy()
            flagged["異常原因"] = f"{subj}分數異常偏低（低於班級平均 2 個標準差）"
            anomaly_rows.append(flagged[["姓名", "年級", "班級", subj, "異常原因"]])

    if prev_df is not None:
        merged = df.merge(prev_df, on=["姓名", "年級", "班級"], suffixes=("_本次", "_上次"))
        for subj in subjects:
            col_curr = f"{subj}_本次"
            col_prev = f"{subj}_上次"
            if col_curr in merged.columns and col_prev in merged.columns:
                diff = merged[col_prev] - merged[col_curr]
                flagged = merged[diff >= 30].copy()
                if len(flagged) > 0:
                    flagged["異常原因"] = f"{subj}與上次相比退步超過 30 分"
                    anomaly_rows.append(flagged[["姓名", "年級", "班級", "異常原因"]])

    # 第二條件：所有科目皆不及格
    fail_all_mask = (df[subjects] < PASSING_SCORE).all(axis=1)
    flagged_all = df[fail_all_mask].copy()
    if len(flagged_all) > 0:
        flagged_all["異常原因"] = "全科不及格"
        anomaly_rows.append(flagged_all[["姓名", "年級", "班級", "異常原因"]])

    if not anomaly_rows:
        return pd.DataFrame(columns=["姓名", "年級", "班級", "異常原因"])
    return pd.concat(anomaly_rows, ignore_index=True).drop_duplicates(subset=["姓名", "異常原因"])
