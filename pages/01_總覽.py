# pages/01_總覽.py
import json
from pathlib import Path
import streamlit as st
import pandas as pd
from auth import require_auth
from src.alerts import fail_rate_alerts, difficulty_alerts
from src.stats import detect_anomalies, get_subject_cols, class_stats, sort_grades
from ui.charts import fail_rate_color

st.set_page_config(page_title="總覽", layout="wide")
require_auth()

if "exam" not in st.session_state:
    st.warning("請先在主頁選擇考試資料")
    st.stop()

exam = st.session_state["exam"]
df = exam.scores_df

DATA_DIR = Path("data")
CLASS_CONFIG_PATH = DATA_DIR / "class_config.json"

# 讀取班級分組設定
class_config = {}
if CLASS_CONFIG_PATH.exists():
    with open(CLASS_CONFIG_PATH, "r", encoding="utf-8") as f:
        class_config = json.load(f)

baseline_classes = class_config.get("baseline_classes", [])
social_classes = class_config.get("social_classes", [])
social_excluded_subjects = class_config.get("social_excluded_subjects", [])
science_excluded_subjects = class_config.get("science_excluded_subjects", [])

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

alert_groups = fail_rate_alerts(
    df,
    baseline_classes=baseline_classes,
    social_classes=social_classes,
    social_excluded_subjects=social_excluded_subjects,
    science_excluded_subjects=science_excluded_subjects,
)
diff_alerts = difficulty_alerts(df)
anomalies = detect_anomalies(df)

main_alerts = alert_groups["一般"]
baseline_alerts = alert_groups["基準班"]

has_any = main_alerts or baseline_alerts or diff_alerts or len(anomalies) > 0

if not has_any:
    st.success("本次考試無需特別關注的警示項目 ✅")
else:
    # 一般班級警示
    if main_alerts:
        st.markdown("**不及格比例過高（一般班級）：**")
        for a in main_alerts[:10]:
            icon = fail_rate_color(a["不及格比例"])
            st.write(f"{icon} {a['訊息']}")

    # 基準班獨立區塊
    if baseline_alerts:
        st.markdown("---")
        st.markdown("**甲／己班狀況（供參考，門檻 70%）：**")
        st.caption("甲、己班學生成績基準較低，以下為特別嚴重的項目。")
        for a in baseline_alerts[:8]:
            icon = fail_rate_color(a["不及格比例"])
            st.write(f"{icon} {a['訊息']}")

    if diff_alerts:
        st.markdown("---")
        st.markdown("**試卷難易度警示：**")
        for a in diff_alerts:
            st.write(f"📌 {a}")

    if len(anomalies) > 0:
        st.markdown(f"**成績異常學生：** 共 {len(anomalies)} 筆（詳見名單管理頁面）")

    # 設定提示
    if not baseline_classes and not social_classes:
        st.info("💡 可在主頁「班級分組設定」中設定基準班與社會組，讓警示更精準。")

st.divider()

# ── 各年級平均摘要 ──────────────────────────────────────────────
st.subheader("各年級各科平均分")

_fmt = lambda v: f"{v:.2f}" if pd.notna(v) else "—"
for grade in sort_grades(df["年級"].unique()):
    grade_df = df[df["年級"] == grade]
    grade_subjs = [s for s in subjects if grade_df[s].notna().any()]
    row = {"班級數": grade_df["班級"].nunique(), "學生數": len(grade_df)}
    for subj in grade_subjs:
        row[subj] = round(float(grade_df[subj].mean()), 2)
    grade_summary = pd.DataFrame([row])
    float_fmt = {c: _fmt for c in grade_subjs}
    st.markdown(f"**{grade}**")
    st.dataframe(
        grade_summary.style.format(float_fmt).highlight_between(
            subset=grade_subjs, left=0, right=59, color="#fecaca"
        ),
        use_container_width=True,
        hide_index=True
    )
