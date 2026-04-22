# pages/03_科目分析.py
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from auth import require_auth
from src.stats import get_subject_cols
from src.comparison import (
    cross_class_comparison, fairness_check, get_grades,
    below_class_average_summary, teacher_consistency,
)
from ui.charts import bar_chart

_TEACHER_MAP_PATH = Path("data/teacher_map.json")
_ABILITY_CLASSES_PATH = Path("data/ability_classes.json")

st.set_page_config(page_title="科目分析", layout="wide")
require_auth()

if "exam" not in st.session_state:
    st.warning("請先在主頁選擇考試資料")
    st.stop()

exam = st.session_state["exam"]
df = exam.scores_df
subjects = get_subject_cols(df)

if _TEACHER_MAP_PATH.exists():
    with open(_TEACHER_MAP_PATH, "r", encoding="utf-8") as f:
        teacher_map = json.load(f)
else:
    teacher_map = exam.teacher_map

ability_classes: set = set()
if _ABILITY_CLASSES_PATH.exists():
    with open(_ABILITY_CLASSES_PATH, "r", encoding="utf-8") as f:
        ability_classes = set(json.load(f))

st.title(f"📚 科目分析 — {exam.exam_name}")

col1, col2 = st.columns(2)
with col1:
    selected_subject = st.selectbox("選擇科目", subjects)
with col2:
    all_grades = get_grades(df)
    selected_grade = st.selectbox("年段篩選", all_grades)

grade_filter = selected_grade

st.divider()

# ── 跨班比較 ──────────────────────────────────────────────────
st.subheader(f"{selected_subject} 跨班成績比較（{selected_grade}）")
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

st.divider()

# ── 方向一：同班科際比較（科目視角）─────────────────────────────
st.subheader("同班科際比較")
st.caption("找出「這科平均明顯低於該班全科平均」的班級，排除班際能力差異的影響。")

deviation_threshold = st.slider("偏差警示門檻（分）", min_value=5, max_value=20, value=8, step=1,
                                 key="dev_threshold")
below_df = below_class_average_summary(
    df, selected_subject, subjects, teacher_map,
    grade=grade_filter, deviation_threshold=deviation_threshold,
)
if below_df.empty:
    st.info("無足夠資料")
else:
    flagged = below_df[below_df["⚠️"] == "偏低"]
    if not flagged.empty:
        for _, row in flagged.iterrows():
            teacher_note = f"（{row['任課教師']}）" if row["任課教師"] else ""
            st.warning(
                f"【{row['班級']}】{teacher_note} {selected_subject} 平均 {row[f'{selected_subject}平均']:.2f} 分，"
                f"低於該班全科平均 {row['全科平均']:.2f} 分，偏差 {abs(row['偏差']):.2f} 分"
            )
    else:
        st.success(f"各班 {selected_subject} 成績均在自身全科平均水準內 ✅")

    display_below = below_df[[c for c in below_df.columns if c != "⚠️"]]
    float_fmt = {c: "{:.2f}" for c in display_below.columns if display_below[c].dtype == "float64"}
    st.dataframe(
        display_below.style.format(float_fmt).apply(
            lambda row: ["background-color: #fef9c3" if row["偏差"] <= -deviation_threshold
                         else "" for _ in row],
            axis=1
        ),
        use_container_width=True, hide_index=True,
    )

st.divider()

# ── 方向二：出題公平性檢查（分層）────────────────────────────────
st.subheader("出題公平性檢查")
if ability_classes:
    st.caption(f"資優班（{', '.join(sorted(ability_classes))}）與普通班分開比較。")
else:
    st.caption("尚未設定資優班，目前為全班比較。可在主頁設定資優班以啟用分層模式。")

if not teacher_map:
    st.info("尚未設定教師對應表，請先在主頁設定後再使用此功能")
else:
    alerts = fairness_check(
        df, selected_subject, teacher_map,
        gap_threshold=15.0, grade=grade_filter,
        ability_classes=ability_classes if ability_classes else None,
    )
    if alerts:
        for a in alerts:
            st.warning(a)
    else:
        st.success("本科目各班成績差距在合理範圍內 ✅")

st.divider()

# ── 方向三：教師多班一致性 ────────────────────────────────────────
st.subheader("教師多班一致性")
st.caption("同一位老師教多個班時，比較各班成績差距。適合評估是否有特定班級需要加強輔導。")

if not teacher_map:
    st.info("尚未設定教師對應表，請先在主頁設定後再使用此功能")
else:
    consistency_df = teacher_consistency(
        df, selected_subject, teacher_map,
        gap_threshold=10.0, grade=grade_filter,
    )
    if consistency_df.empty:
        st.info("此科目無同一老師教多班的資料")
    else:
        flagged_teachers = consistency_df[consistency_df["⚠️"] == "差距偏大"]["教師姓名"].unique()
        if len(flagged_teachers) > 0:
            st.warning(f"以下老師各班差距偏大（≥10分）：{', '.join(flagged_teachers)}")

        display_cons = consistency_df[[c for c in consistency_df.columns if c != "⚠️"]]
        st.dataframe(
            display_cons.style.format({"平均": "{:.2f}", "班間最大差距": "{:.2f}"}).apply(
                lambda row: ["background-color: #fef9c3" if row["班間最大差距"] >= 10
                             else "" for _ in row],
                axis=1
            ),
            use_container_width=True, hide_index=True,
        )
