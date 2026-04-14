# src/comparison.py
from typing import Dict, List
import pandas as pd
from src.stats import class_stats

_META_COLS = ["姓名", "年級", "班級"]


def cross_class_comparison(
    df: pd.DataFrame,
    subject: str,
    teacher_map: Dict[str, Dict[str, str]] = None,
    grade: str = None,
) -> pd.DataFrame:
    """
    回傳某科目所有班級的統計摘要 DataFrame，含任課教師欄位。
    teacher_map 格式: {"科目": {"班級": "教師姓名"}}
    grade: 若指定（如 "高一"），只比較該年段的班級
    """
    target_df = df[df["年級"] == grade] if grade else df
    rows = []
    for grade_class in target_df["班級"].unique():
        stats = class_stats(df, grade_class, subject)
        teacher = ""
        if teacher_map and subject in teacher_map:
            teacher = teacher_map[subject].get(grade_class, "")
        stats["任課教師"] = teacher
        rows.append(stats)
    result = pd.DataFrame(rows)
    # 過濾掉無資料的班級（該班沒有此科目）
    result = result[result["人數"] > 0]
    return result.sort_values("班級").reset_index(drop=True)


def get_grades(df: pd.DataFrame) -> List[str]:
    """回傳資料中所有年段，排序後加上『全部年段』選項"""
    grades = sorted(df["年級"].unique().tolist())
    return ["全部年段"] + grades


def fairness_check(
    df: pd.DataFrame,
    subject: str,
    teacher_map: Dict[str, Dict[str, str]],
    gap_threshold: float = 15.0,
    grade: str = None,
) -> List[str]:
    """
    偵測同科不同老師班級間的成績差距。
    只比較「不同老師」的班級。回傳警示訊息列表。
    """
    comparison = cross_class_comparison(df, subject, teacher_map, grade=grade)
    if len(comparison) < 2:
        return []

    unique_teachers = comparison["任課教師"].nunique()
    if unique_teachers <= 1:
        return []  # 同一位老師，不做公平性比較

    max_avg = comparison["平均"].max()
    min_avg = comparison["平均"].min()
    gap = max_avg - min_avg

    if gap < gap_threshold:
        return []

    max_class = comparison.loc[comparison["平均"].idxmax(), "班級"]
    min_class = comparison.loc[comparison["平均"].idxmin(), "班級"]
    return [
        f"【{subject}】{max_class}（{max_avg:.1f}分）與 {min_class}（{min_avg:.1f}分）"
        f"差距 {gap:.1f} 分，建議確認是否為出題難易度差異"
    ]
