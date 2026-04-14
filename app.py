# app.py
import io
import json
from pathlib import Path
import streamlit as st
import pandas as pd
from auth import require_auth
from src.loader import (
    validate_scores_df, load_scores_from_df,
    validate_items_df, load_items_from_df,
    is_school_format, preprocess_school_excel,
)
from src.course_parser import parse_course_excel, to_teacher_map
from src.models import ExamRecord
from src.storage import save_exam, load_exam, list_exams, delete_exam

DATA_DIR = Path("data")
TEACHER_MAP_PATH = DATA_DIR / "teacher_map.json"
ABILITY_CLASSES_PATH = DATA_DIR / "ability_classes.json"

st.set_page_config(page_title="普台成績分析", page_icon="📊", layout="wide")
require_auth()

st.title("📊 普台高中成績分析系統")

# ── 考試選擇 ──────────────────────────────────────────────────
st.header("考試資料管理")

exams = list_exams()
col1, col2 = st.columns([3, 1])

with col1:
    if exams:
        selected = st.selectbox(
            "選擇要分析的考試",
            exams,
            index=0,
            key="selected_exam_id"
        )
        if st.button("載入考試資料", type="primary"):
            record = load_exam(selected)
            if record:
                st.session_state["exam"] = record
                st.success(f"✅ 已載入：{record.exam_name}")
            else:
                st.error("載入失敗，請重試")
    else:
        st.info("尚無考試資料，請先上傳")

with col2:
    if exams and st.button("🗑️ 刪除此考試", type="secondary"):
        delete_exam(st.session_state.get("selected_exam_id", ""))
        if "exam" in st.session_state:
            del st.session_state["exam"]
        st.rerun()

# ── 上傳新考試 ─────────────────────────────────────────────────
with st.expander("➕ 上傳新考試成績"):
    exam_id = st.text_input("考試代號（唯一識別，如 2026-期中一）", placeholder="2026-期中一")
    exam_name = st.text_input("考試名稱（顯示用）", placeholder="114學年度上學期期中考")
    scores_file = st.file_uploader("成績 Excel（必填）", type=["xlsx"], key="upload_scores")
    items_file = st.file_uploader("試題得分 Excel（選填，供試題分析用）", type=["xlsx"], key="upload_items")

    if st.button("上傳並儲存") and exam_id and exam_name and scores_file:
        df = pd.read_excel(scores_file)
        preprocess_warnings = []
        if is_school_format(df):
            df, preprocess_warnings = preprocess_school_excel(df)
            st.info("✅ 偵測到學校成績系統格式，已自動轉換")
        for w in preprocess_warnings:
            st.warning(f"⚠️ {w}")
        errors = validate_scores_df(df)
        if errors:
            for e in errors:
                st.error(e)
        else:
            scores_df = load_scores_from_df(df)
            items_df = None
            if items_file:
                idf = pd.read_excel(items_file)
                ierrors = validate_items_df(idf)
                if ierrors:
                    for e in ierrors:
                        st.warning(f"試題資料：{e}")
                else:
                    items_df = load_items_from_df(idf)

            teacher_map = {}
            if TEACHER_MAP_PATH.exists():
                with open(TEACHER_MAP_PATH, "r", encoding="utf-8") as f:
                    teacher_map = json.load(f)

            record = ExamRecord(
                exam_id=exam_id,
                exam_name=exam_name,
                scores_df=scores_df,
                items_df=items_df,
                teacher_map=teacher_map,
            )
            save_exam(record)
            st.session_state["exam"] = record
            st.success(f"✅ 考試「{exam_name}」已儲存並載入")
            st.rerun()

# ── 目前載入狀態 ───────────────────────────────────────────────
if "exam" in st.session_state:
    exam = st.session_state["exam"]
    st.info(f"📋 目前載入：**{exam.exam_name}**（{len(exam.scores_df)} 位學生）")

st.divider()

# ── 教師對應表管理 ─────────────────────────────────────────────
st.header("教師對應表")
st.caption("設定哪位老師教哪個班的哪個科目，設定後會自動套用到所有考試分析。")

teacher_map: dict = {}
if TEACHER_MAP_PATH.exists():
    with open(TEACHER_MAP_PATH, "r", encoding="utf-8") as f:
        teacher_map = json.load(f)

if teacher_map:
    rows = []
    for subj, class_map in teacher_map.items():
        for cls, tname in class_map.items():
            rows.append({"科目": subj, "班級": cls, "教師姓名": tname})
    current_map_df = pd.DataFrame(rows)
    st.dataframe(current_map_df, use_container_width=True, hide_index=True)

    # 下載目前對應表
    buf = io.BytesIO()
    current_map_df.to_excel(buf, index=False)
    st.download_button(
        "⬇ 下載目前對應表 Excel",
        data=buf.getvalue(),
        file_name="教師對應表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("尚無資料，請下載範本填寫後上傳。")
    # 產生範本（含說明列）
    template_df = pd.DataFrame([
        {"科目": "國語文", "班級": "高一甲", "教師姓名": "王小明"},
        {"科目": "國語文", "班級": "高一乙", "教師姓名": "李美華"},
        {"科目": "數學",   "班級": "高一甲", "教師姓名": "陳志遠"},
    ])
    buf0 = io.BytesIO()
    template_df.to_excel(buf0, index=False)
    st.download_button(
        "⬇ 下載填寫範本",
        data=buf0.getvalue(),
        file_name="教師對應表_範本.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ── 從配課表自動匯入 ───────────────────────────────────────────
with st.expander("🗂️ 從配課表 Excel 自動匯入（推薦）"):
    st.caption("直接上傳學校配課表 Excel（含「國英數」和「自社藝能」工作表），系統自動解析。")
    uploaded_course = st.file_uploader("選擇配課表 Excel", type=["xlsx"], key="upload_course")
    if uploaded_course:
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded_course.read())
            tmp_path = tmp.name
        try:
            parsed_df, parse_warnings = parse_course_excel(tmp_path)
            for w in parse_warnings:
                st.warning(w)
            if parsed_df.empty:
                st.error("未能解析出任何對應資料，請確認工作表格式")
            else:
                st.info(f"解析完成，共 {len(parsed_df)} 筆對應。請確認後按「匯入」。")
                # 讓使用者篩選只想匯入的科目
                all_subjs = sorted(parsed_df["科目"].unique())
                selected_subjs = st.multiselect(
                    "選擇要匯入的科目（預設全選）",
                    all_subjs, default=all_subjs, key="course_subjs"
                )
                preview_df = parsed_df[parsed_df["科目"].isin(selected_subjs)]
                st.dataframe(preview_df, use_container_width=True, hide_index=True)

                if st.button("✅ 確認匯入") and not preview_df.empty:
                    new_map = to_teacher_map(preview_df)
                    DATA_DIR.mkdir(exist_ok=True)
                    with open(TEACHER_MAP_PATH, "w", encoding="utf-8") as f:
                        json.dump(new_map, f, ensure_ascii=False, indent=2)
                    st.success(f"✅ 匯入完成，共 {len(preview_df)} 筆對應")
                    st.rerun()
        finally:
            os.unlink(tmp_path)

# ── 批次上傳（手動整理格式）────────────────────────────────────
with st.expander("📤 批次匯入教師對應表（上傳已整理 Excel）"):
    st.caption("Excel 需包含三欄：**科目**、**班級**、**教師姓名**，一列一筆對應。")
    uploaded_map = st.file_uploader("選擇 Excel 檔", type=["xlsx"], key="upload_teacher_map")
    if uploaded_map and st.button("匯入並覆蓋現有對應表"):
        try:
            map_df = pd.read_excel(uploaded_map)
            required = {"科目", "班級", "教師姓名"}
            if not required.issubset(map_df.columns):
                st.error(f"Excel 缺少必要欄位，需包含：{required}")
            else:
                new_map: dict = {}
                for _, row in map_df.iterrows():
                    subj = str(row["科目"]).strip()
                    cls  = str(row["班級"]).strip()
                    name = str(row["教師姓名"]).strip()
                    if subj and cls and name:
                        new_map.setdefault(subj, {})[cls] = name
                DATA_DIR.mkdir(exist_ok=True)
                with open(TEACHER_MAP_PATH, "w", encoding="utf-8") as f:
                    json.dump(new_map, f, ensure_ascii=False, indent=2)
                st.success(f"✅ 匯入完成，共 {len(map_df)} 筆對應")
                st.rerun()
        except Exception as e:
            st.error(f"讀取失敗：{e}")

# ── 單筆新增 ──────────────────────────────────────────────────
with st.expander("➕ 單筆新增 / 修改"):
    c1, c2, c3 = st.columns(3)
    with c1:
        t_subject = st.text_input("科目", placeholder="國語文")
    with c2:
        t_class = st.text_input("班級", placeholder="高一甲")
    with c3:
        t_name = st.text_input("教師姓名", placeholder="王小明")

    if st.button("儲存對應") and t_subject and t_class and t_name:
        if t_subject not in teacher_map:
            teacher_map[t_subject] = {}
        teacher_map[t_subject][t_class] = t_name
        DATA_DIR.mkdir(exist_ok=True)
        with open(TEACHER_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(teacher_map, f, ensure_ascii=False, indent=2)
        st.success(f"✅ 已儲存：{t_subject} / {t_class} → {t_name}")
        st.rerun()

st.divider()

# ── 資優班設定 ─────────────────────────────────────────────────
st.header("資優班設定")
st.caption("設定哪些班為能力分班（資優班），公平性檢查時將分層比較，不與普通班混合。")

ability_classes: list = []
if ABILITY_CLASSES_PATH.exists():
    with open(ABILITY_CLASSES_PATH, "r", encoding="utf-8") as f:
        ability_classes = json.load(f)

# 從目前載入的考試取得班級清單（若有）
all_classes: list = []
if "exam" in st.session_state:
    all_classes = sorted(st.session_state["exam"].scores_df["班級"].unique().tolist())

if all_classes:
    selected_ability = st.multiselect(
        "選擇資優班（可多選）",
        options=all_classes,
        default=[c for c in ability_classes if c in all_classes],
        help="例如：高一乙、高一庚、高二乙、高二庚…",
    )
    if st.button("儲存資優班設定"):
        DATA_DIR.mkdir(exist_ok=True)
        with open(ABILITY_CLASSES_PATH, "w", encoding="utf-8") as f:
            json.dump(selected_ability, f, ensure_ascii=False)
        st.success(f"✅ 已儲存，共 {len(selected_ability)} 個資優班：{', '.join(selected_ability)}")
        st.rerun()
    if ability_classes:
        st.info(f"目前設定：{', '.join(ability_classes)}")
else:
    if ability_classes:
        st.info(f"目前設定：{', '.join(ability_classes)}（請先載入考試資料以編輯）")
    else:
        st.info("請先載入考試資料，再設定資優班。")

st.divider()
if st.button("登出"):
    st.session_state.clear()
    st.rerun()
