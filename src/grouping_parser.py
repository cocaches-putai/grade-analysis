# src/grouping_parser.py
"""
解析教務處提供的英數分組 Excel（如 114-2高中英文數學分組.xlsx）。

工作表格式：
  Row 3: 「班級：10MA1  NaN  高一庚」 → 分組代碼 + 主要班級標籤
  Row 4: 「授課教師：洪誌陽」
  Row 5: 序號 班級 座號 姓名（欄頭）
  Row 6+: 學生名單
  每組佔 5 欄（序號/班級/座號/姓名/空白分隔），從第 0 欄開始
"""
import re
from typing import Dict, List
import pandas as pd

# 工作表名稱 → (科目系統名稱, 年段)
_SHEET_SUBJECT_MAP = {
    "高一數學": ("數學", "高一"),
    "高二數學": ("數學", "高二"),
    "高三數學": ("數學", "高三"),
    "高一英文": ("英語文", "高一"),
    "高二英文": ("英語文", "高二"),
    "高三英文": ("英語文", "高三"),
}


def _extract_code_label(cell_val: str, next_cell=None) -> tuple[str, str]:
    """
    從「班級：10MA1」中提取分組代碼，
    再從同行第3欄（通常是主要班級如「高一庚」）組成顯示標籤。
    """
    code = re.sub(r"^班級[：:]?\s*", "", str(cell_val)).strip()
    label_parts = [code]
    if next_cell and str(next_cell).strip() not in ("", "nan", "NaN"):
        label_parts.append(str(next_cell).strip())
    return code, "/".join(label_parts)


def _extract_teacher(cell_val: str) -> str:
    """從「授課教師：洪誌陽」或「教師：洪誌陽」中提取老師姓名"""
    return re.sub(r"^[授課]*教師[：:]?\s*", "", str(cell_val)).strip()


def _parse_sheet(df: pd.DataFrame) -> List[Dict]:
    """解析一個工作表，回傳分組列表"""
    groups = []
    ncols = df.shape[1]

    # 每 5 欄為一組（0,5,10,15,20...）
    for start_col in range(0, ncols, 5):
        if start_col + 3 >= ncols:
            break

        # Row 3 (index 3): 分組代碼
        code_cell = df.iloc[3, start_col]
        if pd.isna(code_cell) or str(code_cell).strip() in ("", "nan"):
            continue
        if "班級" not in str(code_cell):
            continue

        # 主要班級標籤在 start_col+2（如「高一庚」）
        label_cell = df.iloc[3, start_col + 2] if start_col + 2 < ncols else None
        code, label = _extract_code_label(code_cell, label_cell)

        # Row 4 (index 4): 老師
        teacher_cell = df.iloc[4, start_col]
        teacher = _extract_teacher(teacher_cell) if pd.notna(teacher_cell) else ""

        # Row 6+ (index 6+): 學生（col+1=班級, col+3=姓名）
        students = []
        for row_idx in range(6, len(df)):
            name_cell = df.iloc[row_idx, start_col + 3]
            if pd.isna(name_cell) or str(name_cell).strip() in ("", "nan"):
                continue
            # 姓名欄有時是「姓 名」分兩格，嘗試合併
            name = str(name_cell).replace(" ", "").strip()
            if name:
                students.append(name)

        if students:
            groups.append({
                "code": code,
                "label": label,
                "teacher": teacher,
                "students": students,
            })

    return groups


def parse_grouping_excel(file_path: str) -> Dict:
    """
    解析英數分組 Excel，回傳：
    {
      "數學": {
        "高一": [{"code": "10MA1", "label": "10MA1/高一庚", "teacher": "洪誌陽",
                  "students": ["郭旻農", ...]}, ...],
        "高二": [...],
      },
      "英語文": {
        "高二": [...],
      }
    }
    """
    xl = pd.ExcelFile(file_path)
    result: Dict = {}

    for raw_sheet in xl.sheet_names:
        key = raw_sheet.strip()
        if key not in _SHEET_SUBJECT_MAP:
            continue
        subject, grade = _SHEET_SUBJECT_MAP[key]
        df = xl.parse(raw_sheet, header=None)
        groups = _parse_sheet(df)
        if groups:
            result.setdefault(subject, {})[grade] = groups

    return result
