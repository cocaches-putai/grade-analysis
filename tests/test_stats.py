# tests/test_stats.py
import pytest
from src.stats import (
    get_subject_cols, class_stats, subject_distribution,
    student_rankings, detect_anomalies
)


def test_get_subject_cols(sample_scores_df):
    cols = get_subject_cols(sample_scores_df)
    assert cols == ["國文", "英文", "數學"]


def test_class_stats_returns_expected_columns(sample_scores_df):
    result = class_stats(sample_scores_df, "國一甲", "國文")
    assert result["平均"] == pytest.approx(70.2)
    assert result["不及格人數"] == 2
    assert result["不及格比例"] == pytest.approx(0.4)


def test_class_stats_max_min(sample_scores_df):
    result = class_stats(sample_scores_df, "國一甲", "國文")
    assert result["最高分"] == 91
    assert result["最低分"] == 48


def test_subject_distribution(sample_scores_df):
    dist = subject_distribution(sample_scores_df, "國一甲", "國文")
    assert dist["59以下"] == 2
    assert dist["80-89"] == 1
    assert dist["90-100"] == 1


def test_student_rankings(sample_scores_df):
    result = student_rankings(sample_scores_df, "國一甲")
    assert "班級排名_國文" in result.columns
    assert result.loc[result["姓名"] == "陳大明", "班級排名_國文"].values[0] == 1


def test_detect_anomalies_flags_outlier(sample_scores_df):
    anomalies = detect_anomalies(sample_scores_df)
    assert len(anomalies) > 0
    flagged_names = anomalies["姓名"].tolist()
    assert "周淑芬" in flagged_names
