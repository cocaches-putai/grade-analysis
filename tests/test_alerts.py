# tests/test_alerts.py
import pytest
from src.alerts import (
    fail_rate_alerts, difficulty_alerts,
    tutoring_list, makeup_exam_list
)


def test_fail_rate_alerts_flags_high_fail_rate(sample_scores_df):
    alerts = fail_rate_alerts(sample_scores_df, threshold=0.30)
    assert len(alerts) > 0
    subjects_flagged = [a["科目"] for a in alerts]
    assert "數學" in subjects_flagged or "國文" in subjects_flagged


def test_fail_rate_alerts_no_alert_below_threshold(sample_scores_df):
    alerts = fail_rate_alerts(sample_scores_df, threshold=0.99)
    assert alerts == []


def test_difficulty_alerts_flags_low_average(sample_scores_df):
    import pandas as pd
    low_df = sample_scores_df.copy()
    low_df["國文"] = 45
    alerts = difficulty_alerts(low_df, threshold=50.0)
    assert any("國文" in a for a in alerts)


def test_tutoring_list_returns_multi_fail_students(sample_scores_df):
    result = tutoring_list(sample_scores_df, min_fail_subjects=2)
    assert len(result) > 0
    assert "林小玲" in result["姓名"].tolist()


def test_makeup_exam_list(sample_scores_df):
    result = makeup_exam_list(sample_scores_df)
    assert "姓名" in result.columns
    assert "科目" in result.columns
    assert "分數" in result.columns
    rows_for_lingling = result[result["姓名"] == "林小玲"]
    assert len(rows_for_lingling) >= 1
