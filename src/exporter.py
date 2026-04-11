# src/exporter.py
from typing import Dict
import pandas as pd


def export_to_excel(sheets: Dict[str, pd.DataFrame], output_path: str) -> None:
    """
    將多個 DataFrame 匯出為多頁 Excel 檔案。
    sheets: {"工作表名稱": DataFrame}
    """
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
