# pages/03_科目分析.py
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from auth import require_auth
from src.stats import get_subject_cols
from src.comparison import cross_class_comparison, fairness_check, get_grades
from ui.charts import bar_chart

_TEACHER_MAP_PATH = Path("data/teacher_map.json")

st.set_page_config(page_title="科目分析", layout="wide")
require_auth()

if "exam" not in st.session_state:
    st.warning("請先在主頁選擇考試資料")
    st.stop()

exam = st.session_state["exam"]
df = exam.scores_df
subjects = get_subject_cols(df)

# 優先使用磁碟上最新的教師對應表，確保匯入配課表後立即生效
if _TEACHER_MAP_PATH.exists():
    with open(_TEACHER_MAP_PATH, "r", encoding="utf-8") as f:
        teacher_map = json.load(f)
else:
    teacher_map = exam.teacher_map

st.title(f"📚 科目分析 — {exam.exam_name}")

col1, col2 = st.columns(2)
with col1:
    selected_subject = st.selectbox("選擇科目", subjects)
with col2:
    all_grades = get_grades(df)
    selected_grade = st.selectbox("年段篩選", all_grades)

grade_filter = None if selected_grade == "全部年段" else selected_grade

st.divider()

# ── 跨班比較 ──────────────────────────────────────────────────
grade_label = selected_grade if selected_grade != "全部年段" else "全年段"
st.subheader(f"{selected_subject} 跨班成績比較（{grade_label}）")
comparison = cross_class_comparison(df, selected_subject, teacher_map, grade=grade_filter)
fig = bar_chart(comparison, x_col="班級", y_col="平均",
                title=f"{selected_subject} 各班平均分", threshold_line=60.0)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    comparison[["班級", "任課教師", "平均", "最高分", "最低分", "不及格人數", "不及格比例"]].assign(
        不及格比例=lambda x: x["不及格比例"].apply(
            lambda v: f"{v:.0%}" if v is not None else "—"
        )
    ),
    use_container_width=True, hide_index=True
)

# ── 公平性警示 ─────────────────────────────────────────────────
st.subheader("出題公平性檢查")
if not teacher_map:
    st.info("尚未設定教師對應表，請先在主頁設定後再使用此功能")
else:
    alerts = fairness_check(df, selected_subject, teacher_map, gap_threshold=15.0, grade=grade_filter)
    if alerts:
        for a in alerts:
            st.warning(a)
    else:
        st.success("本科目各班成績差距在合理範圍內 ✅")
