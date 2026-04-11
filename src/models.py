# src/models.py
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class ExamRecord:
    """單次考試的完整資料"""
    exam_id: str           # e.g. "2026-期中一"
    exam_name: str         # e.g. "114學年度上學期期中考"
    scores_df: pd.DataFrame   # 欄位: 姓名, 年級, 班級, [科目...]
    items_df: Optional[pd.DataFrame] = None  # 欄位: 姓名, 年級, 班級, 科目, 題1, 題2...
    teacher_map: dict = field(default_factory=dict)  # {"科目": {"班級": "教師姓名"}}


@dataclass
class TeacherMapping:
    """教師-班級-科目對應"""
    subject: str
    grade_class: str   # e.g. "國一甲"
    teacher_name: str
