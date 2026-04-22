# pages/02_班級分析.py
import streamlit as st
import pandas as pd
from auth import require_auth
from src.stats import get_subject_cols, class_stats, subject_distribution, student_rankings
from src.comparison import class_subject_deviation
from ui.charts import bar_chart, distribution_chart

st.set_page_config(page_title="班級分析", layout="wide")
require_auth()

if "exam" not in st.session_state:
    st.warning("請先在主頁選擇考試資料")
    st.stop()

exam = st.session_state["exam"]
df = exam.scores_df
subjects = get_subject_cols(df)
classes = sorted(df["班級"].unique().tolist())

st.title(f"🏫 班級分析 — {exam.exam_name}")

col1, col2 = st.columns(2)
with col1:
    selected_class = st.selectbox("選擇班級", classes)
with col2:
    selected_subject = st.selectbox("選擇科目", subjects)

st.divider()

# ── 統計摘要 ──────────────────────────────────────────────────
stats = class_stats(df, selected_class, selected_subject)
c1, c2, c3, c4 = st.columns(4)
c1.metric("平均分", stats["平均"])
c2.metric("最高分", stats["最高分"])
c3.metric("最低分", stats["最低分"])
fail_delta = f"{stats['不及格比例']:.0%}" if stats["不及格比例"] is not None else "—"
c4.metric("不及格人數", f"{stats['不及格人數']} 人",
          delta=fail_delta, delta_color="inverse")

# ── 分布圖 ────────────────────────────────────────────────────
dist = subject_distribution(df, selected_class, selected_subject)
fig = distribution_chart(dist, f"{selected_class} {selected_subject} 成績分布")
st.plotly_chart(fig, use_container_width=True)

# ── 學生排名 ──────────────────────────────────────────────────
st.subheader(f"{selected_class} 學生排名")
rankings = student_rankings(df, selected_class)
rank_col = f"班級排名_{selected_subject}"
display_cols = [c for c in ["姓名", selected_subject, rank_col] if c in rankings.columns]
st.dataframe(
    rankings[display_cols].sort_values(rank_col),
    use_container_width=True, hide_index=True
)

# ── 同班科際比較 ──────────────────────────────────────────────
st.subheader(f"{selected_class} 各科與全科平均比較")
st.caption("偏差 = 該科平均 − 全科平均，黃底標示偏低 8 分以上的科目。")
dev_df = class_subject_deviation(df, selected_class, subjects)
if not dev_df.empty:
    num_cols = [c for c in dev_df.columns if c != "科目" and c != "⚠️"]
    st.dataframe(
        dev_df.style
            .format({c: "{:.2f}" for c in num_cols})
            .apply(
                lambda row: ["background-color: #fef9c3" if row["偏差"] <= -8 else "" for _ in row],
                axis=1
            ),
        use_container_width=True, hide_index=True,
    )

st.divider()

# ── 各科統計 ──────────────────────────────────────────────────
st.subheader(f"{selected_class} 各科統計")
summary_rows = []
for subj in subjects:
    s = class_stats(df, selected_class, subj)
    fail_rate = f"{s['不及格比例']:.0%}" if s["不及格比例"] is not None else "—"
    summary_rows.append({
        "科目": subj, "平均": s["平均"], "最高": s["最高分"], "最低": s["最低分"],
        "不及格人數": s["不及格人數"], "不及格比例": fail_rate,
    })
st.dataframe(
    pd.DataFrame(summary_rows).style.format({"平均": "{:.2f}"}),
    use_container_width=True, hide_index=True,
)

# ── 跨考試趨勢（若有多筆資料）────────────────────────────────
from src.storage import list_exams, load_exam as _load_exam
from src.trends import class_trend
from ui.charts import line_chart

all_exam_ids = list_exams()
if len(all_exam_ids) >= 2:
    st.divider()
    st.subheader(f"{selected_class} 跨考試趨勢")
    exams_data = []
    for eid in all_exam_ids:
        rec = _load_exam(eid)
        if rec is not None:
            exams_data.append((rec.exam_name, rec.scores_df))
    if exams_data:
        trend_df = class_trend(exams_data, selected_class, selected_subject)
        fig_trend = line_chart(trend_df, "考試", "平均",
                               f"{selected_class} {selected_subject} 跨考試平均走勢")
        st.plotly_chart(fig_trend, use_container_width=True)
