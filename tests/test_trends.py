# tests/test_trends.py
import pytest
import pandas as pd
from src.trends import class_trend, student_trend, top_movers


@pytest.fixture
def two_exam_dfs(sample_scores_df):
    df2 = sample_scores_df.copy()
    df2.loc[df2["姓名"] == "王小明", "國文"] = 95
    df2.loc[df2["姓名"] == "林小玲", "國文"] = 40
    return sample_scores_df, df2


def test_class_trend_returns_trend_df(two_exam_dfs):
    df1, df2 = two_exam_dfs
    exams = [("期中一", df1), ("期中二", df2)]
    result = class_trend(exams, "國一甲", "國文")
    assert list(result["考試"]) == ["期中一", "期中二"]
    assert result.loc[result["考試"] == "期中一", "平均"].values[0] == pytest.approx(70.2)


def test_student_trend(two_exam_dfs):
    df1, df2 = two_exam_dfs
    exams = [("期中一", df1), ("期中二", df2)]
    result = student_trend(exams, "王小明", "國文")
    assert result.loc[result["考試"] == "期中二", "分數"].values[0] == 95


def test_top_movers_identifies_improver_and_regressor(two_exam_dfs):
    df1, df2 = two_exam_dfs
    improvers, regressors = top_movers(df1, df2, "國文", top_n=3)
    assert "王小明" in improvers["姓名"].tolist()
    assert "林小玲" in regressors["姓名"].tolist()
