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


def _parse_subject_detail_sheet(
    df: pd.DataFrame,
    subject_name: str,
    main_course_keywords: List[str],
) -> List[Dict]:
    """
    解析「高中英文/國中英文/高中數學/國中數學」格式的科目專屬工作表。
    找「教室」列，用該列確認真實班級，往上找最近的主課老師列。
    主課老師列以 main_course_keywords 識別；若無，fallback 為「老師/教師」列。
    """
    results = []
    classroom_rows = df.index[
        df.iloc[:, 0].astype(str).str.strip().isin(["教室"])
    ].tolist()

    for cr in classroom_rows:
        classroom_row = df.iloc[cr]

        # 往上找主課老師列
        main_teacher_row = None
        for r in range(cr - 1, max(-1, cr - 7), -1):
            cell0 = str(df.iloc[r, 0]).strip()
            if any(kw in cell0 for kw in main_course_keywords):
                main_teacher_row = r
                break
        if main_teacher_row is None:
            # fallback：「老師」或「教師」列
            for r in range(cr - 1, max(-1, cr - 7), -1):
                cell0 = str(df.iloc[r, 0]).strip()
                if cell0 in ("老師", "教師"):
                    main_teacher_row = r
                    break
        if main_teacher_row is None:
            continue

        for col in range(1, len(classroom_row)):
            cls_val = str(classroom_row.iloc[col]).strip()
            # 需是真實班級（含一/二/三 + 甲/乙/丙…）
            if not re.search(r"[一二三][年]?[甲乙丙丁戊己庚]", cls_val):
                continue
            teacher_cell = str(df.iloc[main_teacher_row, col]).strip()
            if not teacher_cell or teacher_cell == "nan":
                continue
            # 去除括號內課時數及換行後的備注
            teacher_name = re.sub(r"[\(（].*?[\)）]", "", teacher_cell)
            teacher_name = re.sub(r"\n.*", "", teacher_name).strip()
            if teacher_name:
                results.append({
                    "科目": subject_name, "班級": cls_val, "教師姓名": teacher_name
                })
    return results


def parse_course_excel(file_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    解析學校配課表 Excel 檔案，自動偵測支援的工作表。

    解析優先順序：
    - 「高中英文」「國中英文」「高中數學」「國中數學」分頁
      使用教室列精確對應主課老師，結果會覆蓋「國英數」分頁的同科目資料。
    - 「國英數」分頁：負責其他未有專屬分頁的科目（本土語等）。
    - 「自社藝能」分頁：社會、自然、藝能各科。

    回傳:
        (result_df, warnings)
        result_df: 欄位為 [科目, 班級, 教師姓名]
        warnings: 解析過程的提示訊息
    """
    warnings: List[str] = []
    xl = pd.ExcelFile(file_path)
    sheet_names = [s.strip() for s in xl.sheet_names]

    # ── 先解析有專屬分頁的科目（英文、數學）── ──────────────────
    precise_rows: List[Dict] = []
    precise_subjects: set = set()

    _DETAIL_SHEETS = {
        "高中英文": ("英語文", ["英文", "+閱", "閱讀"]),
        "國中英文": ("英語文", ["部編", "讀本"]),
        "高中數學": ("數學",  ["老師", "教師"]),  # fallback-only keywords
        "國中數學": ("數學",  ["老師", "教師"]),
    }
    for raw_sheet in xl.sheet_names:
        key = raw_sheet.strip()
        if key in _DETAIL_SHEETS:
            subj, keywords = _DETAIL_SHEETS[key]
            df = xl.parse(raw_sheet, header=None)
            rows = _parse_subject_detail_sheet(df, subj, keywords)
            precise_rows.extend(rows)
            precise_subjects.add(subj)

    # ── 解析國英數（跳過已有精確分頁的科目）─────────────────────
    broad_rows: List[Dict] = []
    if "國英數" in sheet_names:
        df = xl.parse("國英數", header=None)
        for row in _parse_one_sheet(df, teacher_row_idx=2, subject_row_idx=1):
            if row["科目"] not in precise_subjects:
                broad_rows.append(row)

    # ── 解析自社藝能 ───────────────────────────────────────────
    yishe_rows: List[Dict] = []
    for raw_sheet in xl.sheet_names:
        if raw_sheet.strip() in ("自社藝能", "自社藝能 "):
            df = xl.parse(raw_sheet, header=None)
            yishe_rows = _parse_one_sheet(df, teacher_row_idx=3, subject_row_idx=2)
            break

    # ── 未知工作表提示 ─────────────────────────────────────────
    known = set(_DETAIL_SHEETS.keys()) | {"國英數", "自社藝能", "自社藝能 "}
    for raw_sheet in xl.sheet_names:
        if raw_sheet.strip() not in known:
            warnings.append(
                f"工作表「{raw_sheet}」格式未知，已略過"
                f"（支援：國英數、自社藝能、高中英文、國中英文、高中數學、國中數學）"
            )

    all_rows = precise_rows + broad_rows + yishe_rows
    if not all_rows:
        return pd.DataFrame(columns=["科目", "班級", "教師姓名"]), warnings

    result_df = pd.DataFrame(all_rows).drop_duplicates()

    # 同一科目同一班有多位老師時合併（正常情況下不應再發生，保留為保險）
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
