# app.py
import json
from pathlib import Path
import streamlit as st
import pandas as pd
from auth import require_auth
from src.loader import validate_scores_df, load_scores_from_df, validate_items_df, load_items_from_df
from src.models import ExamRecord
from src.storage import save_exam, load_exam, list_exams, delete_exam

DATA_DIR = Path("data")
TEACHER_MAP_PATH = DATA_DIR / "teacher_map.json"

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
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("➕ 新增 / 修改教師對應"):
    c1, c2, c3 = st.columns(3)
    with c1:
        t_subject = st.text_input("科目", placeholder="國文")
    with c2:
        t_class = st.text_input("班級", placeholder="國一甲")
    with c3:
        t_name = st.text_input("教師姓名", placeholder="王老師")

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
if st.button("登出"):
    st.session_state.clear()
    st.rerun()
