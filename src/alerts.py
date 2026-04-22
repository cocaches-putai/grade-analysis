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


def _infer_science_classes(
    df: pd.DataFrame,
    social_classes: List[str],
) -> List[str]:
    """自然組 = 高二/高三班級扣掉社會組"""
    upper_grades = {"高二", "高三"}
    all_upper = [
        c for c in df["班級"].unique()
        if any(c.startswith(g) for g in upper_grades)
    ]
    return [c for c in all_upper if c not in social_classes]


def fail_rate_alerts(
    df: pd.DataFrame,
    threshold: float = ALERT_FAIL_RATE_THRESHOLD,
    baseline_classes: List[str] = [],
    social_classes: List[str] = [],
    social_excluded_subjects: List[str] = [],
    science_excluded_subjects: List[str] = [],
) -> Dict[str, List[Dict]]:
    """
    回傳警示清單，分為兩組：
    - "一般": 排除基準班、社會組理科、自然組史地公
    - "基準班": 甲/己等基準班的獨立警示（門檻 70%）
    """
    main_alerts = []
    baseline_alerts = []
    subjects = get_subject_cols(df)

    # 自然組由社會組反向推論
    science_classes = _infer_science_classes(df, social_classes) if social_classes else []

    for grade_class in df["班級"].unique():
        is_baseline = grade_class in baseline_classes
        is_social = grade_class in social_classes
        is_science = grade_class in science_classes

        for subj in subjects:
            # 社會組 + 理科 → 略過
            if is_social and subj in social_excluded_subjects:
                continue
            # 自然組 + 史地公 → 略過
            if is_science and subj in science_excluded_subjects:
                continue

            stats = class_stats(df, grade_class, subj)
            if stats["不及格比例"] is None:
                continue

            alert = {
                "班級": grade_class,
                "科目": subj,
                "不及格比例": stats["不及格比例"],
                "不及格人數": stats["不及格人數"],
                "訊息": (
                    f"【{grade_class}】{subj} 不及格比例 {stats['不及格比例']:.0%}"
                    f"（{stats['不及格人數']}/{stats['人數']}人）"
                )
            }

            if is_baseline:
                if stats["不及格比例"] >= 0.70:
                    baseline_alerts.append(alert)
            else:
                if stats["不及格比例"] >= threshold:
                    main_alerts.append(alert)

    return {
        "一般": sorted(main_alerts, key=lambda x: x["不及格比例"], reverse=True),
        "基準班": sorted(baseline_alerts, key=lambda x: x["不及格比例"], reverse=True),
    }


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
