# src/alerts.py
from typing import List, Dict, Optional
import pandas as pd
from config import (
    PASSING_SCORE, ALERT_FAIL_RATE_THRESHOLD,
    ALERT_EASY_THRESHOLD, TUTORING_MIN_FAIL_SUBJECTS,
    ALERT_REGRESSION_THRESHOLD
)
from src.stats import get_subject_cols, class_stats

_META_COLS = ["姓名", "年級", "班級"]


def fail_rate_alerts(df: pd.DataFrame, threshold: float = ALERT_FAIL_RATE_THRESHOLD) -> List[Dict]:
    """回傳不及格比例超過門檻的班級-科目警示清單"""
    alerts = []
    subjects = get_subject_cols(df)
    for grade_class in df["班級"].unique():
        for subj in subjects:
            stats = class_stats(df, grade_class, subj)
            if stats["不及格比例"] is not None and stats["不及格比例"] >= threshold:
                alerts.append({
                    "班級": grade_class,
                    "科目": subj,
                    "不及格比例": stats["不及格比例"],
                    "不及格人數": stats["不及格人數"],
                    "訊息": (
                        f"【{grade_class}】{subj} 不及格比例 {stats['不及格比例']:.0%}"
                        f"（{stats['不及格人數']}/{stats['人數']}人）"
                    )
                })
    return sorted(alerts, key=lambda x: x["不及格比例"], reverse=True)


def difficulty_alerts(df: pd.DataFrame, threshold: float = ALERT_EASY_THRESHOLD) -> List[str]:
    """班級平均低於門檻，警示試卷可能偏難"""
    alerts = []
    subjects = get_subject_cols(df)
    for grade_class in df["班級"].unique():
        for subj in subjects:
            stats = class_stats(df, grade_class, subj)
            if stats["平均"] is not None and stats["平均"] < threshold:
                alerts.append(
                    f"【{grade_class}】{subj} 班級平均 {stats['平均']} 分，"
                    f"低於 {threshold} 分，試卷可能偏難"
                )
    return alerts


def tutoring_list(
    df: pd.DataFrame,
    min_fail_subjects: int = TUTORING_MIN_FAIL_SUBJECTS,
    prev_df: Optional[pd.DataFrame] = None,
    regression_threshold: float = ALERT_REGRESSION_THRESHOLD
) -> pd.DataFrame:
    """
    產生輔導名單：
    - 不及格科目數 >= min_fail_subjects，或
    - 與上次相比任一科退步 >= regression_threshold 分
    """
    subjects = get_subject_cols(df)
    df = df.copy()
    df["不及格科目數"] = (df[subjects] < PASSING_SCORE).sum(axis=1)
    flagged = df[df["不及格科目數"] >= min_fail_subjects].copy()

    if prev_df is not None:
        merged = df.merge(prev_df[["姓名"] + subjects], on="姓名", suffixes=("_本次", "_上次"))
        for subj in subjects:
            col_curr = f"{subj}_本次"
            col_prev = f"{subj}_上次"
            if col_curr in merged.columns and col_prev in merged.columns:
                diff = merged[col_prev] - merged[col_curr]
                regression_ids = merged.loc[diff >= regression_threshold, "姓名"]
                regression_rows = df[df["姓名"].isin(regression_ids)]
                flagged = pd.concat([flagged, regression_rows]).drop_duplicates(subset=["姓名"])

    result_cols = ["姓名", "年級", "班級", "不及格科目數"] + subjects
    return (
        flagged[result_cols]
        .sort_values(["班級", "不及格科目數"], ascending=[True, False])
        .reset_index(drop=True)
    )


def makeup_exam_list(df: pd.DataFrame) -> pd.DataFrame:
    """產生補考名單：每個學生每科不及格都列一筆"""
    subjects = get_subject_cols(df)
    rows = []
    for _, row in df.iterrows():
        for subj in subjects:
            score = row[subj]
            if pd.notna(score) and score < PASSING_SCORE:
                rows.append({
                    "姓名": row["姓名"],
                    "年級": row["年級"],
                    "班級": row["班級"],
                    "科目": subj,
                    "分數": score,
                })
    return pd.DataFrame(rows).sort_values(["班級", "姓名"]).reset_index(drop=True)
