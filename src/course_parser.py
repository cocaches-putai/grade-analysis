# src/course_parser.py
"""
解析學校配課表 Excel，自動產生教師對應表。
支援「國英數」和「自社藝能」兩種工作表格式。
"""
import re
from typing import Dict, List, Tuple
import pandas as pd

# 從配課表科目名稱 → 成績系統科目名稱
_SUBJECT_MAP = {
    "英文": "英語文", "英語文": "英語文",
    "國文": "國語文", "國語文": "國語文",
    "數學": "數學", "數學A": "數學", "數學B": "數學",
    "地科": "地球科學", "地球科學": "地球科學",
    "物理": "物理", "化學": "化學",
    "生物": "生物", "理化": "理化",
    "歷史": "歷史", "地理": "地理",
    "公民": "公民與社會", "公民與社會": "公民與社會",
    "資訊": "資訊科技", "生科": "生活科技",
    "音樂": "音樂", "體育": "體育", "美術": "美術",
    "護理": "健康護理", "家政": "家政",
    "輔導": "輔導活動", "童軍": "童軍",
    "書法": "書法", "靜心": "靜心",
    "本土語": "本土語", "表演": "表演藝術",
}


def _clean_subject(raw: str) -> str:
    """'高中國文(6)' → '國語文'"""
    s = str(raw).strip()
    for prefix in ["高中", "國中"]:
        s = s.replace(prefix, "")
    s = s.split("(")[0].split("（")[0].replace("\n", "").strip()
    return _SUBJECT_MAP.get(s, s)


def _parse_one_sheet(
    df: pd.DataFrame,
    teacher_row_idx: int,
    subject_row_idx: int,
    start_col: int = 2,
) -> List[Dict]:
    """
    解析一張工作表，回傳 [{'科目', '班級', '教師姓名'}, ...] 列表。
    teacher_row_idx: 教師姓名所在列索引
    subject_row_idx: 科目名稱所在列索引
    """
    subjects_raw = df.iloc[subject_row_idx].tolist()
    teachers = df.iloc[teacher_row_idx].tolist()

    # 前向填充科目名稱（合併儲存格在 pandas 讀取後只有第一格有值）
    current_subj = None
    col_to_subj: Dict[int, str] = {}
    for i, s in enumerate(subjects_raw):
        if pd.notna(s) and str(s).strip() not in ("", "nan"):
            current_subj = _clean_subject(s)
        if i >= start_col and current_subj:
            col_to_subj[i] = current_subj

    results = []
    for row_idx in range(teacher_row_idx + 1, len(df)):
        cls_raw = str(df.iloc[row_idx, 0]).strip()
        # 班級欄需含年級字（一/二/三）及班別字（甲/乙/丙…）
        if not re.search(r"[一二三]", cls_raw) or not re.search(r"[甲乙丙丁戊己庚]", cls_raw):
            continue
        for col_idx, subj in col_to_subj.items():
            cell = df.iloc[row_idx, col_idx]
            if pd.isna(cell) or str(cell).strip() in ("", "nan", "0"):
                continue
            teacher = str(teachers[col_idx]).strip()
            if not teacher or teacher in ("nan", "班級導師"):
                continue
            results.append({"科目": subj, "班級": cls_raw, "教師姓名": teacher})
    return results


def parse_course_excel(file_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    解析學校配課表 Excel 檔案，自動偵測支援的工作表。

    回傳:
        (result_df, warnings)
        result_df: 欄位為 [科目, 班級, 教師姓名]，多師同班以「/」分隔
        warnings: 解析過程的提示訊息
    """
    warnings: List[str] = []
    all_rows: List[Dict] = []

    xl = pd.ExcelFile(file_path)
    sheet_names = xl.sheet_names

    # 偵測各工作表並以對應格式解析
    for sheet in sheet_names:
        sheet_stripped = sheet.strip()
        df = xl.parse(sheet, header=None)

        if sheet_stripped == "國英數":
            # 科目在 row1，教師在 row2
            rows = _parse_one_sheet(df, teacher_row_idx=2, subject_row_idx=1)
            all_rows.extend(rows)

        elif sheet_stripped in ("自社藝能", "自社藝能 "):
            # 大類在 row1，細科在 row2，教師在 row3
            rows = _parse_one_sheet(df, teacher_row_idx=3, subject_row_idx=2)
            all_rows.extend(rows)

        else:
            warnings.append(f"工作表「{sheet}」格式未知，已略過（僅支援「國英數」和「自社藝能」）")

    if not all_rows:
        return pd.DataFrame(columns=["科目", "班級", "教師姓名"]), warnings

    result_df = pd.DataFrame(all_rows).drop_duplicates()

    # 同一科目同一班若有多位老師，合併為「老師A/老師B」
    result_df = (
        result_df.groupby(["科目", "班級"])["教師姓名"]
        .apply(lambda x: "/".join(sorted(set(x))))
        .reset_index()
    )

    return result_df, warnings


def to_teacher_map(df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    """將解析結果 DataFrame 轉換成系統使用的 teacher_map 格式"""
    teacher_map: Dict[str, Dict[str, str]] = {}
    for _, row in df.iterrows():
        subj = row["科目"]
        cls = row["班級"]
        name = row["教師姓名"]
        teacher_map.setdefault(subj, {})[cls] = name
    return teacher_map
