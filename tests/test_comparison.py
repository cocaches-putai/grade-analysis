# tests/test_comparison.py
import pytest
from src.comparison import cross_class_comparison, fairness_check


def test_cross_class_comparison_returns_all_classes(sample_scores_df, sample_teacher_map):
    result = cross_class_comparison(sample_scores_df, "國文", sample_teacher_map)
    assert len(result) == 2  # 國一甲、國一乙
    assert "班級" in result.columns
    assert "任課教師" in result.columns
    assert "平均" in result.columns


def test_cross_class_comparison_correct_average(sample_scores_df, sample_teacher_map):
    result = cross_class_comparison(sample_scores_df, "國文", sample_teacher_map)
    jia = result[result["班級"] == "國一甲"]["平均"].values[0]
    assert jia == pytest.approx(70.2)


def test_fairness_check_flags_large_gap(sample_scores_df, sample_teacher_map):
    alerts = fairness_check(sample_scores_df, "國文", sample_teacher_map, gap_threshold=5.0)
    assert isinstance(alerts, list)


def test_fairness_check_no_false_alarm_for_same_teacher(sample_scores_df, sample_teacher_map):
    # 英文由同一位陳老師教，不應產生公平性警示
    alerts = fairness_check(sample_scores_df, "英文", sample_teacher_map, gap_threshold=5.0)
    assert alerts == []
