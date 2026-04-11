# src/trends.py
from typing import List, Tuple
import pandas as pd


def class_trend(
    exams: List[Tuple[str, pd.DataFrame]],
    grade_class: str,
    subject: str
) -> pd.DataFrame:
    """回傳某班某科目跨多次考試的平均分走勢。exams: [("期中一", df1), ...]"""
    rows = []
    for exam_name, df in exams:
        subset = df[df["班級"] == grade_class][subject].dropna()
        rows.append({"考試": exam_name, "平均": round(subset.mean(), 2), "人數": len(subset)})
    return pd.DataFrame(rows)


def student_trend(
    exams: List[Tuple[str, pd.DataFrame]],
    student_name: str,
    subject: str
) -> pd.DataFrame:
    """回傳某學生某科目跨多次考試的分數走勢"""
    rows = []
    for exam_name, df in exams:
        row = df[df["姓名"] == student_name]
        score = row[subject].values[0] if len(row) > 0 and subject in row.columns else None
        rows.append({"考試": exam_name, "分數": score})
    return pd.DataFrame(rows)


def top_movers(
    prev_df: pd.DataFrame,
    curr_df: pd.DataFrame,
    subject: str,
    top_n: int = 5
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """比較兩次考試，找出進步/退步最多的學生。回傳 (improvers_df, regressors_df)"""
    merged = curr_df[["姓名", "年級", "班級", subject]].merge(
        prev_df[["姓名", subject]],
        on="姓名",
        suffixes=("_本次", "_上次")
    )
    merged["變化"] = merged[f"{subject}_本次"] - merged[f"{subject}_上次"]
    cols = ["姓名", "班級", f"{subject}_上次", f"{subject}_本次", "變化"]
    rename = {f"{subject}_上次": "上次", f"{subject}_本次": "本次"}
    merged = merged[cols].rename(columns=rename)
    improvers = merged.nlargest(top_n, "變化")
    regressors = merged.nsmallest(top_n, "變化")
    return improvers.reset_index(drop=True), regressors.reset_index(drop=True)
