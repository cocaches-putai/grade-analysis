# pages/04_試題分析.py
import streamlit as st
from auth import require_auth
from src.item_analysis import item_summary, cronbach_alpha

st.set_page_config(page_title="試題分析", layout="wide")
require_auth()

if "exam" not in st.session_state:
    st.warning("請先在主頁選擇考試資料")
    st.stop()

exam = st.session_state["exam"]

st.title(f"🔬 試題分析 — {exam.exam_name}")

if exam.items_df is None:
    st.info("本次考試尚未上傳試題得分資料。請在主頁重新上傳含試題得分的 Excel 檔案。")
    st.stop()

items_df = exam.items_df
subjects = items_df["科目"].unique().tolist()
selected_subject = st.selectbox("選擇科目", subjects)
subject_df = items_df[items_df["科目"] == selected_subject]

st.divider()

# ── 試卷信度 ──────────────────────────────────────────────────
alpha = cronbach_alpha(subject_df)
col1, col2 = st.columns(2)
col1.metric("Cronbach's α 信度係數", f"{alpha:.3f}",
            help="α > 0.7 良好，0.5–0.7 尚可，< 0.5 建議檢討")
if alpha >= 0.7:
    col2.success("試卷信度良好 ✅")
elif alpha >= 0.5:
    col2.warning("試卷信度尚可，可考慮調整題目")
else:
    col2.error("試卷信度偏低，建議檢討題目品質")

st.divider()

# ── 題目分析表 ─────────────────────────────────────────────────
st.subheader("各題分析")
summary = item_summary(subject_df)

def highlight_issue(val: str) -> str:
    return "color: green" if val == "正常" else "color: red; font-weight: bold"

st.dataframe(
    summary.style.map(highlight_issue, subset=["判定"]),
    use_container_width=True, hide_index=True
)

# ── 需檢討題目 ─────────────────────────────────────────────────
issues = summary[summary["判定"] != "正常"]
if len(issues) > 0:
    st.subheader(f"⚠️ 需檢討題目（共 {len(issues)} 題）")
    for _, row in issues.iterrows():
        st.write(f"• **{row['題目']}**：{row['判定']}（P值={row['難度P值']:.2f}，D值={row['鑑別度D值']:.2f}）")
else:
    st.success("所有題目指標均在正常範圍內 ✅")
