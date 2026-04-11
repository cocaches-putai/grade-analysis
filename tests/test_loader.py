# tests/test_loader.py
import pytest
import pandas as pd
from src.loader import validate_scores_df, validate_items_df, load_scores_from_df, load_items_from_df


def test_validate_scores_df_passes_with_valid_data(sample_scores_df):
    errors = validate_scores_df(sample_scores_df)
    assert errors == []


def test_validate_scores_df_missing_required_column():
    df = pd.DataFrame({"姓名": ["王小明"], "年級": ["國一"], "國文": [80]})  # 缺「班級」
    errors = validate_scores_df(df)
    assert any("班級" in e for e in errors)


def test_validate_scores_df_no_subject_columns():
    df = pd.DataFrame({"姓名": ["王小明"], "年級": ["國一"], "班級": ["國一甲"]})
    errors = validate_scores_df(df)
    assert any("科目" in e for e in errors)


def test_validate_scores_df_invalid_score():
    df = pd.DataFrame({"姓名": ["王小明"], "年級": ["國一"], "班級": ["國一甲"], "國文": [150]})
    errors = validate_scores_df(df)
    assert any("超出範圍" in e for e in errors)


def test_load_scores_from_df_returns_correct_shape(sample_scores_df):
    result = load_scores_from_df(sample_scores_df)
    assert len(result) == 10
    assert "國文" in result.columns


def test_validate_items_df_passes_with_valid_data(sample_items_df):
    errors = validate_items_df(sample_items_df)
    assert errors == []


def test_validate_items_df_missing_subject_column():
    df = pd.DataFrame({"姓名": ["王小明"], "年級": ["國一"], "班級": ["國一甲"], "題1": [1]})
    errors = validate_items_df(df)
    assert any("科目" in e for e in errors)
