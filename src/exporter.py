# src/exporter.py
from typing import Dict, List, Optional
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from src.stats import get_subject_cols, sort_grades


def export_to_excel(sheets: Dict[str, pd.DataFrame], output_path: str) -> None:
    """將多個 DataFrame 匯出為多頁 Excel 檔案。"""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)


# ── 班別排序 key ──────────────────────────────────────────────────
_CLASS_SUFFIX_ORDER = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

def _sort_classes(classes) -> list:
    def key(c):
        for i, ch in enumerate(_CLASS_SUFFIX_ORDER):
            if c.endswith(ch):
                return i
        return 99
    return sorted(classes, key=key)


# ── 樣式輔助 ──────────────────────────────────────────────────────
_HEADER_FILL   = PatternFill("solid", fgColor="D9E1F2")
_SUBJ_FILL     = PatternFill("solid", fgColor="BDD7EE")
_AVG_FILL      = PatternFill("solid", fgColor="E2EFDA")
_TEACHER_FILL  = PatternFill("solid", fgColor="FFF2CC")
_THIN          = Side(style="thin")
_BORDER        = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)

def _cell(ws, row, col, value=None, bold=False, fill=None, align="center", num_fmt=None):
    c = ws.cell(row=row, column=col, value=value)
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=False)
    c.border = _BORDER
    if bold:
        c.font = Font(bold=True)
    if fill:
        c.fill = fill
    if num_fmt:
        c.number_format = num_fmt
    return c


# ── 年級各科分頁 ──────────────────────────────────────────────────
_BANDS = [
    ("90-100", 90, 101), ("80-89", 80, 90), ("70-79", 70, 80),
    ("60-69", 60, 70), ("50-59", 50, 60), ("40-49", 40, 50),
    ("30-39", 30, 40), ("20-29", 20, 30), ("10-19", 10, 20), ("0-9", 0, 10),
]
_BLOCK_ROWS = 4 + len(_BANDS) + 2  # 科目/班級/到考/不及格 + bands + 平均/老師


def _write_grade_sheet(wb, grade: str, grade_df: pd.DataFrame,
                       subjects: List[str], teacher_map: dict):
    ws = wb.create_sheet(title=f"{grade}各科")
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 10

    current_row = 1

    for subj in subjects:
        # 只顯示該年段有此科目資料的班級
        valid_classes = _sort_classes([
            cls for cls in grade_df["班級"].unique()
            if len(grade_df[grade_df["班級"] == cls][subj].dropna()) > 0
        ])
        if not valid_classes:
            continue

        nc = len(valid_classes)

        # 科目標題列（跨欄）
        _cell(ws, current_row, 2, "科目", bold=True, fill=_SUBJ_FILL)
        _cell(ws, current_row, 3, subj, bold=True, fill=_SUBJ_FILL)
        if nc > 1:
            ws.merge_cells(
                start_row=current_row, start_column=3,
                end_row=current_row, end_column=2 + nc
            )
        current_row += 1

        # 班級列
        _cell(ws, current_row, 2, "班級", bold=True, fill=_HEADER_FILL)
        for i, cls in enumerate(valid_classes):
            ws.column_dimensions[get_column_letter(3 + i)].width = 8
            _cell(ws, current_row, 3 + i, cls, bold=True, fill=_HEADER_FILL)
        current_row += 1

        # 到考人數
        _cell(ws, current_row, 2, "到考人數", fill=_HEADER_FILL)
        for i, cls in enumerate(valid_classes):
            n = len(grade_df[grade_df["班級"] == cls][subj].dropna())
            _cell(ws, current_row, 3 + i, n)
        current_row += 1

        # 不及格人數
        _cell(ws, current_row, 2, "不及格人數", fill=_HEADER_FILL)
        for i, cls in enumerate(valid_classes):
            subset = grade_df[grade_df["班級"] == cls][subj].dropna()
            _cell(ws, current_row, 3 + i, int((subset < 60).sum()))
        current_row += 1

        # 分數區間
        for label, lo, hi in _BANDS:
            _cell(ws, current_row, 2, label)
            for i, cls in enumerate(valid_classes):
                subset = grade_df[grade_df["班級"] == cls][subj].dropna()
                cnt = int(((subset >= lo) & (subset < hi)).sum())
                _cell(ws, current_row, 3 + i, cnt)
            current_row += 1

        # 平均
        _cell(ws, current_row, 2, "平均", bold=True, fill=_AVG_FILL)
        for i, cls in enumerate(valid_classes):
            subset = grade_df[grade_df["班級"] == cls][subj].dropna()
            val = round(float(subset.mean()), 2) if len(subset) > 0 else None
            _cell(ws, current_row, 3 + i, val, fill=_AVG_FILL, num_fmt="0.00")
        current_row += 1

        # 任課老師
        _cell(ws, current_row, 2, "任課老師", fill=_TEACHER_FILL)
        for i, cls in enumerate(valid_classes):
            teacher = teacher_map.get(subj, {}).get(cls, "")
            _cell(ws, current_row, 3 + i, teacher or None, fill=_TEACHER_FILL)
        current_row += 1

        # 空行
        current_row += 3


# ── 各科平均總表 ──────────────────────────────────────────────────
def _write_summary_sheet(wb, df: pd.DataFrame, subjects: List[str],
                         teacher_map: dict, exam_name: str, all_classes: List[str]):
    ws = wb.create_sheet(title="各科平均總表")

    # 欄頭
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 12
    _cell(ws, 1, 1, "班級", bold=True, fill=_HEADER_FILL)
    _cell(ws, 1, 2, "科目", bold=True, fill=_HEADER_FILL)
    for i, subj in enumerate(subjects):
        ws.column_dimensions[get_column_letter(3 + i)].width = 10
        _cell(ws, 1, 3 + i, subj, bold=True, fill=_HEADER_FILL)

    row = 2
    for cls in all_classes:
        # 任課老師列
        _cell(ws, row, 1, cls, bold=True, fill=_TEACHER_FILL)
        _cell(ws, row, 2, "任課老師", fill=_TEACHER_FILL)
        for i, subj in enumerate(subjects):
            teacher = teacher_map.get(subj, {}).get(cls, "")
            _cell(ws, row, 3 + i, teacher or None, fill=_TEACHER_FILL)
        row += 1

        # 成績列
        _cell(ws, row, 1, "", fill=_AVG_FILL)
        _cell(ws, row, 2, exam_name, fill=_AVG_FILL)
        for i, subj in enumerate(subjects):
            subset = df[df["班級"] == cls][subj].dropna()
            val = round(float(subset.mean()), 2) if len(subset) > 0 else None
            _cell(ws, row, 3 + i, val, fill=_AVG_FILL, num_fmt="0.00")
        row += 1


# ── 前三名 ────────────────────────────────────────────────────────
def _write_top3_sheet(wb, df: pd.DataFrame, subjects: List[str],
                      all_classes: List[str]):
    ws = wb.create_sheet(title="各班前三名")
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 8
    ws.column_dimensions["D"].width = 8

    headers = ["班級", "姓名", "班名次", "平均分"]
    for i, h in enumerate(headers):
        _cell(ws, 1, 1 + i, h, bold=True, fill=_HEADER_FILL)

    row = 2
    for cls in all_classes:
        class_df = df[df["班級"] == cls].copy()
        # 只計算有資料的科目
        avail = [s for s in subjects if class_df[s].notna().any()]
        if not avail:
            continue
        class_df["_avg"] = class_df[avail].mean(axis=1)
        class_df["_rank"] = class_df["_avg"].rank(ascending=False, method="min").astype(int)
        top3 = class_df.nsmallest(3, "_rank")[["姓名", "_rank", "_avg"]]

        fill = None
        for _, r in top3.iterrows():
            _cell(ws, row, 1, cls, fill=fill)
            _cell(ws, row, 2, r["姓名"], fill=fill)
            _cell(ws, row, 3, int(r["_rank"]), fill=fill)
            _cell(ws, row, 4, round(float(r["_avg"]), 2), fill=fill, num_fmt="0.00")
            row += 1

        # 空行間隔
        for col in range(1, 5):
            ws.cell(row=row, column=col, value=None)
        row += 1


# ── 主進入點 ──────────────────────────────────────────────────────
def export_analysis_excel(
    df: pd.DataFrame,
    teacher_map: dict,
    exam_name: str,
    output_path: str,
) -> None:
    """
    產生與學校現有「成績分析.xls」相同格式的 Excel。

    分頁：
    - 高一各科 / 高二各科 / 高三各科（國中年段同理）
    - 各科平均總表
    - 各班前三名
    """
    subjects = get_subject_cols(df)
    grades = sort_grades(df["年級"].unique().tolist())

    wb = openpyxl.Workbook()
    # 移除預設空白頁
    wb.remove(wb.active)

    # 年級各科分頁
    for grade in grades:
        grade_df = df[df["年級"] == grade]
        _write_grade_sheet(wb, grade, grade_df, subjects, teacher_map)

    # 所有班級（依年段排序）
    all_classes: List[str] = []
    for grade in grades:
        all_classes.extend(_sort_classes(
            df[df["年級"] == grade]["班級"].unique().tolist()
        ))

    # 各科平均總表
    _write_summary_sheet(wb, df, subjects, teacher_map, exam_name, all_classes)

    # 各班前三名
    _write_top3_sheet(wb, df, subjects, all_classes)

    wb.save(output_path)
