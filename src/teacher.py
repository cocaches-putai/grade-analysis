# src/teacher.py
from typing import Dict, List, Tuple
import pandas as pd
from src.stats import get_subject_cols, class_stats


def teacher_summary(
    df: pd.DataFrame,
    teacher_map: Dict[str, Dict[str, str]]
) -> pd.DataFrame:
    """
    回傳各教師的班級成績摘要 DataFrame。
    teacher_map 格式: {"科目": {"班級": "教師姓名"}}
    """
    rows = []
    for subject, class_teacher in teacher_map.items():
        for grade_class, teacher_name in class_teacher.items():
            if df[df["班級"] == grade_class].empty:
                continue
            if subject not in df.columns:
                continue
            stats = class_stats(df, grade_class, subject)
            rows.append({
                "教師姓名": teacher_name,
                "科目": subject,
                "班級": grade_class,
                "人數": stats["人數"],
                "平均": stats["平均"],
                "不及格比例": stats["不及格比例"],
                "最高分": stats["最高分"],
                "最低分": stats["最低分"],
            })
    result = pd.DataFrame(rows).sort_values(["教師姓名", "科目"]).reset_index(drop=True)
    # 過濾掉本次考試無學生資料的班級（避免顯示 None）
    return result[result["人數"] > 0].reset_index(drop=True)


def teacher_trend(
    exams: List[Tuple[str, pd.DataFrame]],
    teacher_name: str,
    teacher_map: Dict[str, Dict[str, str]]
) -> pd.DataFrame:
    """
    回傳某教師跨多次考試的各班平均分走勢。
    exams: [("期中一", df1), ("期末", df2), ...]
    """
    rows = []
    for exam_name, df in exams:
        for subject, class_teacher in teacher_map.items():
            for grade_class, tname in class_teacher.items():
                if tname != teacher_name:
                    continue
                if df[df["班級"] == grade_class].empty or subject not in df.columns:
                    continue
                stats = class_stats(df, grade_class, subject)
                rows.append({
                    "考試": exam_name,
                    "科目": subject,
                    "班級": grade_class,
                    "平均": stats["平均"],
                })
    return pd.DataFrame(rows)
