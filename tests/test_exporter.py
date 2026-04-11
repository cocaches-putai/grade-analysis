# tests/test_exporter.py
import pytest
import pandas as pd
from src.exporter import export_to_excel


def test_export_to_excel_creates_file(tmp_path, sample_scores_df):
    output_path = tmp_path / "test_output.xlsx"
    sheets = {
        "成績總表": sample_scores_df,
        "摘要": pd.DataFrame({"欄位": ["測試"], "值": [1]}),
    }
    export_to_excel(sheets, str(output_path))
    assert output_path.exists()


def test_export_to_excel_correct_sheet_names(tmp_path, sample_scores_df):
    output_path = tmp_path / "test_output.xlsx"
    sheets = {"成績總表": sample_scores_df}
    export_to_excel(sheets, str(output_path))
    result = pd.ExcelFile(str(output_path))
    assert "成績總表" in result.sheet_names
