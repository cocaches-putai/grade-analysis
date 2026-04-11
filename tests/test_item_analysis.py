# tests/test_item_analysis.py
import pytest
import pandas as pd
from src.item_analysis import (
    difficulty_index, discrimination_index,
    cronbach_alpha, item_summary, get_item_cols
)


def test_get_item_cols(sample_items_df):
    cols = get_item_cols(sample_items_df)
    assert cols == ["題1", "題2", "題3", "題4", "題5"]


def test_difficulty_index(sample_items_df):
    # 題1: [1,0,1,1,0] -> p = 3/5 = 0.6
    p = difficulty_index(sample_items_df, "題1")
    assert p == pytest.approx(0.6)


def test_discrimination_index(sample_items_df):
    d = discrimination_index(sample_items_df, "題1")
    assert isinstance(d, float)
    assert -1.0 <= d <= 1.0


def test_cronbach_alpha(sample_items_df):
    alpha = cronbach_alpha(sample_items_df)
    assert 0.0 <= alpha <= 1.0


def test_item_summary_returns_expected_columns(sample_items_df):
    result = item_summary(sample_items_df)
    assert "題目" in result.columns
    assert "難度P值" in result.columns
    assert "鑑別度D值" in result.columns
    assert "判定" in result.columns


def test_item_summary_flags_too_easy():
    data = {
        "姓名": ["A", "B", "C", "D"],
        "年級": ["國一"] * 4,
        "班級": ["國一甲"] * 4,
        "科目": ["國文"] * 4,
        "題1": [1, 1, 1, 1],
        "題2": [1, 1, 0, 0],
    }
    df = pd.DataFrame(data)
    result = item_summary(df)
    flag = result.loc[result["題目"] == "題1", "判定"].values[0]
    assert "太易" in flag


def test_item_summary_flags_too_hard():
    data = {
        "姓名": ["A", "B", "C", "D"],
        "年級": ["國一"] * 4,
        "班級": ["國一甲"] * 4,
        "科目": ["國文"] * 4,
        "題1": [0, 0, 0, 0],
        "題2": [1, 0, 1, 0],
    }
    df = pd.DataFrame(data)
    result = item_summary(df)
    flag = result.loc[result["題目"] == "題1", "判定"].values[0]
    assert "太難" in flag
