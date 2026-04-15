# pages/06_行政報告.py
import io
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from auth import require_auth
from src.stats import get_subject_cols, grade_rankings, sort_grades
from src.teacher import teacher_summary, teacher_trend
from src.storage import list_exams, load_exam as _load_exam
from src.exporter import export_to_excel, export_analysis_excel
from ui.charts import bar_chart, line_chart

_TEACHER_MAP_PATH = Path("data/teacher_map.json")

st.set_page_config(page_title="行政報告", layout="wide")
require_auth()

if "exam" not in st.session_state:
    st.warning("請先在主頁選擇考試資料")
    st.stop()

exam = st.session_state["exam"]
df = exam.scores_df

# 優先使用磁碟上最新的教師對應表，確保匯入配課表後立即生效
if _TEACHER_MAP_PATH.exists():
    with open(_TEACHER_MAP_PATH, "r", encoding="utf-8") as f:
        teacher_map = json.load(f)
else:
    teacher_map = exam.teacher_map
subjects = get_subject_cols(df)

st.title(f"📊 行政報告 — {exam.exam_name}")

tab1, tab2 = st.tabs(["年級摘要", "教師教學成果"])

# ── 年級摘要 ──────────────────────────────────────────────────────
with tab1:
    st.subheader("各年級各科平均分")

    grade_rows = []
    for grade in sort_grades(df["年級"].unique()):
        grade_df = df[df["年級"] == grade]
        row = {"年級": grade, "班級數": grade_df["班級"].nunique(), "學生數": len(grade_df)}
        for subj in subjects:
            row[subj] = round(grade_df[subj].mean(), 2)
        grade_rows.append(row)

    grade_summary = pd.DataFrame(grade_rows)
    float_fmt = {c: "{:.2f}" for c in subjects}
    st.dataframe(
        grade_summary.style.format(float_fmt, na_rep="—").highlight_between(
            subset=subjects, left=0, right=59, color="#fecaca"
        ),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # 年級內學生排名（可選）
    st.subheader("年級排名查詢")
    grades = sort_grades(df["年級"].unique().tolist())
    selected_grade = st.selectbox("選擇年級", grades)
    selected_subject_rank = st.selectbox("排名科目", subjects, key="grade_rank_subject")

    ranked = grade_rankings(df, selected_grade)
    rank_col = f"年級排名_{selected_subject_rank}"
    display_cols = [c for c in ["姓名", "班級", selected_subject_rank, rank_col] if c in ranked.columns]
    top_n = st.slider("顯示前幾名", min_value=5, max_value=50, value=20, step=5)
    st.dataframe(
        ranked[display_cols].sort_values(rank_col).head(top_n),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # 匯出全校成績
    st.subheader("匯出全校成績報告")
    if st.button("產生並下載完整報告 Excel"):
        sheets = {"總覽": grade_summary}
        for grade in sort_grades(df["年級"].unique()):
            sheets[grade] = df[df["年級"] == grade].reset_index(drop=True)
        export_to_excel(sheets, "/tmp/_full_report.xlsx")
        with open("/tmp/_full_report.xlsx", "rb") as f:
            data = f.read()
        st.download_button(
            label="⬇ 下載完整報告",
            data=data,
            file_name=f"{exam.exam_name}_完整報告.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ── 教師教學成果 ──────────────────────────────────────────────────
with tab2:
    st.subheader("教師教學成果")

    if not teacher_map:
        st.info("尚未設定教師對應表，請先在主頁設定後再使用此功能")
    else:
        summary = teacher_summary(df, teacher_map)

        if summary.empty:
            st.warning("根據教師對應表，找不到對應的班級成績資料")
        else:
            summary_display = summary.copy()
            summary_display["不及格比例"] = summary_display["不及格比例"].apply(
                lambda v: f"{v:.0%}" if v is not None else "—"
            )
            st.dataframe(summary_display, use_container_width=True, hide_index=True)

            st.divider()

            # 個別教師趨勢（若有多次考試）
            all_exam_ids = list_exams()
            if len(all_exam_ids) >= 2:
                st.subheader("教師跨考試趨勢")
                teacher_names = sorted(summary["教師姓名"].unique().tolist())
                selected_teacher = st.selectbox("選擇教師", teacher_names)

                exams_data = []
                for eid in all_exam_ids:
                    rec = _load_exam(eid)
                    if rec is not None:
                        exams_data.append((rec.exam_name, rec.scores_df))

                trend_df = teacher_trend(exams_data, selected_teacher, teacher_map)
                if not trend_df.empty:
                    fig = line_chart(
                        trend_df, x_col="考試", y_col="平均",
                        title=f"{selected_teacher} 各班跨考試平均走勢",
                        group_col="班級"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("該教師在歷次考試中無對應資料")

            st.divider()

            # 匯出教師成果
            if st.button("下載教師成果 Excel"):
                export_to_excel({"教師成果": summary}, "/tmp/_teacher_report.xlsx")
                with open("/tmp/_teacher_report.xlsx", "rb") as f:
                    data = f.read()
                st.download_button(
                    label="⬇ 下載教師成果",
                    data=data,
                    file_name=f"{exam.exam_name}_教師成果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

st.divider()

# ── 一鍵匯出完整分析報告 ────────────────────────────────────────────
st.subheader("一鍵匯出完整成績分析報告")
st.caption("格式與同仁現有手動製作的分析 Excel 相同，包含：各年級各科分布、各科平均總表、各班前三名。")

_SUBJECT_GROUPS_PATH = Path("data/subject_groups.json")
subject_groups = None
if _SUBJECT_GROUPS_PATH.exists():
    with open(_SUBJECT_GROUPS_PATH, "r", encoding="utf-8") as f:
        subject_groups = json.load(f)

if st.button("產生完整分析報告", type="primary"):
    with st.spinner("產生中…"):
        export_analysis_excel(
            df=df,
            teacher_map=teacher_map,
            exam_name=exam.exam_name,
            output_path="/tmp/_analysis_report.xlsx",
            subject_groups=subject_groups,
        )
    with open("/tmp/_analysis_report.xlsx", "rb") as f:
        data = f.read()
    st.download_button(
        label="⬇ 下載完整分析報告",
        data=data,
        file_name=f"{exam.exam_name}_成績分析報告.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
