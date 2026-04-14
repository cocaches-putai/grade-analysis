# pages/01_總覽.py
import streamlit as st
import pandas as pd
from auth import require_auth
from src.alerts import fail_rate_alerts, difficulty_alerts
from src.stats import detect_anomalies, get_subject_cols, class_stats
from ui.charts import fail_rate_color

st.set_page_config(page_title="總覽", layout="wide")
require_auth()

if "exam" not in st.session_state:
    st.warning("請先在主頁選擇考試資料")
    st.stop()

exam = st.session_state["exam"]
df = exam.scores_df

st.title(f"📋 總覽 — {exam.exam_name}")

# ── 關鍵指標 ───────────────────────────────────────────────────
subjects = get_subject_cols(df)
c1, c2, c3 = st.columns(3)
c1.metric("學生總數", len(df))
c2.metric("班級數", df["班級"].nunique())
c3.metric("考試科目數", len(subjects))

st.divider()

# ── 警示區 ─────────────────────────────────────────────────────
st.subheader("⚠️ 需要關注")

fail_alerts = fail_rate_alerts(df)
diff_alerts = difficulty_alerts(df)
anomalies = detect_anomalies(df)

if not fail_alerts and not diff_alerts and len(anomalies) == 0:
    st.success("本次考試無需特別關注的警示項目 ✅")
else:
    if fail_alerts:
        st.markdown("**不及格比例過高：**")
        for a in fail_alerts[:10]:
            icon = fail_rate_color(a["不及格比例"])
            st.write(f"{icon} {a['訊息']}")

    if diff_alerts:
        st.markdown("**試卷難易度警示：**")
        for a in diff_alerts:
            st.write(f"📌 {a}")

    if len(anomalies) > 0:
        st.markdown(f"**成績異常學生：** 共 {len(anomalies)} 筆（詳見名單管理頁面）")

st.divider()

# ── 各年級平均摘要 ──────────────────────────────────────────────
st.subheader("各年級各科平均分")

grade_rows = []
for grade in sorted(df["年級"].unique()):
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
