# src/comparison.py
from typing import Dict, List, Optional, Set
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
    ability_classes: Optional[Set[str]] = None,
) -> List[str]:
    """
    偵測同科不同老師班級間的成績差距。
    ability_classes: 若提供，分資優/普通兩層分別比較，不跨層。
    """
    comparison = cross_class_comparison(df, subject, teacher_map, grade=grade)
    if len(comparison) < 2:
        return []

    alerts = []

    if ability_classes:
        tiers = {
            "資優班": comparison[comparison["班級"].isin(ability_classes)],
            "普通班": comparison[~comparison["班級"].isin(ability_classes)],
        }
        for tier_name, tier_df in tiers.items():
            if len(tier_df) < 2:
                continue
            if tier_df["任課教師"].nunique() <= 1:
                continue
            max_avg = tier_df["平均"].max()
            min_avg = tier_df["平均"].min()
            gap = max_avg - min_avg
            if gap < gap_threshold:
                continue
            max_class = tier_df.loc[tier_df["平均"].idxmax(), "班級"]
            min_class = tier_df.loc[tier_df["平均"].idxmin(), "班級"]
            alerts.append(
                f"【{subject}｜{tier_name}】{max_class}（{max_avg:.1f}分）與"
                f" {min_class}（{min_avg:.1f}分）差距 {gap:.1f} 分，"
                f"建議確認是否為出題難易度差異"
            )
    else:
        if comparison["任課教師"].nunique() <= 1:
            return []
        max_avg = comparison["平均"].max()
        min_avg = comparison["平均"].min()
        gap = max_avg - min_avg
        if gap >= gap_threshold:
            max_class = comparison.loc[comparison["平均"].idxmax(), "班級"]
            min_class = comparison.loc[comparison["平均"].idxmin(), "班級"]
            alerts.append(
                f"【{subject}】{max_class}（{max_avg:.1f}分）與"
                f" {min_class}（{min_avg:.1f}分）差距 {gap:.1f} 分，"
                f"建議確認是否為出題難易度差異"
            )

    return alerts


def class_subject_deviation(
    df: pd.DataFrame,
    grade_class: str,
    subjects: List[str],
    deviation_threshold: float = 8.0,
) -> pd.DataFrame:
    """
    方向一：同班科際比較。
    計算某班各科平均與該班全科平均的偏差，標記顯著偏低的科目。
    """
    class_df = df[df["班級"] == grade_class]
    subj_avgs = {}
    for subj in subjects:
        vals = class_df[subj].dropna()
        if len(vals) > 0:
            subj_avgs[subj] = vals.mean()

    if not subj_avgs:
        return pd.DataFrame()

    overall_avg = sum(subj_avgs.values()) / len(subj_avgs)

    rows = []
    for subj, avg in subj_avgs.items():
        deviation = avg - overall_avg
        rows.append({
            "科目": subj,
            "科目平均": round(avg, 1),
            "全科平均": round(overall_avg, 1),
            "偏差": round(deviation, 1),
            "⚠️": "偏低" if deviation <= -deviation_threshold else "",
        })

    return pd.DataFrame(rows).sort_values("偏差").reset_index(drop=True)


def below_class_average_summary(
    df: pd.DataFrame,
    subject: str,
    subjects: List[str],
    teacher_map: Dict[str, Dict[str, str]] = None,
    grade: str = None,
    deviation_threshold: float = 8.0,
) -> pd.DataFrame:
    """
    方向一（科目視角）：找出「這科平均明顯低於該班全科平均」的班級。
    排除樣本不足的班級（人數 < 5）。
    """
    target_df = df[df["年級"] == grade] if grade else df
    rows = []
    for grade_class in sorted(target_df["班級"].unique()):
        class_df = df[df["班級"] == grade_class]
        vals = class_df[subject].dropna()
        if len(vals) < 5:
            continue
        subj_avg = vals.mean()

        # 全科平均（只計算該班有資料的科目）
        other_avgs = [
            class_df[s].dropna().mean()
            for s in subjects if s != subject and len(class_df[s].dropna()) > 0
        ]
        if not other_avgs:
            continue
        overall_avg = (subj_avg + sum(other_avgs)) / (1 + len(other_avgs))
        deviation = subj_avg - overall_avg

        teacher = ""
        if teacher_map and subject in teacher_map:
            teacher = teacher_map[subject].get(grade_class, "")

        rows.append({
            "班級": grade_class,
            "任課教師": teacher,
            f"{subject}平均": round(subj_avg, 1),
            "全科平均": round(overall_avg, 1),
            "偏差": round(deviation, 1),
            "⚠️": "偏低" if deviation <= -deviation_threshold else "",
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("偏差").reset_index(drop=True)


def teacher_consistency(
    df: pd.DataFrame,
    subject: str,
    teacher_map: Dict[str, Dict[str, str]],
    gap_threshold: float = 10.0,
    grade: str = None,
) -> pd.DataFrame:
    """
    方向三：同一老師教多班時，比較其各班成績差距。
    只顯示有多班資料的老師。
    """
    if subject not in teacher_map:
        return pd.DataFrame()

    target_df = df[df["年級"] == grade] if grade else df
    available_classes = set(target_df["班級"].unique())

    teacher_classes: Dict[str, List[str]] = {}
    for cls, teacher in teacher_map[subject].items():
        if cls in available_classes:
            teacher_classes.setdefault(teacher, []).append(cls)

    rows = []
    for teacher, classes in teacher_classes.items():
        class_avgs = []
        for cls in classes:
            s = class_stats(df, cls, subject)
            if s["平均"] is not None:
                class_avgs.append({"班級": cls, "平均": s["平均"]})

        if len(class_avgs) < 2:
            continue

        avgs = [r["平均"] for r in class_avgs]
        gap = round(max(avgs) - min(avgs), 1)
        for r in class_avgs:
            rows.append({
                "教師姓名": teacher,
                "班級": r["班級"],
                "平均": round(r["平均"], 1),
                "班間最大差距": gap,
                "⚠️": "差距偏大" if gap >= gap_threshold else "",
            })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["教師姓名", "班級"]).reset_index(drop=True)
