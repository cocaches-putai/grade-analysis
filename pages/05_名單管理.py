# pages/05_名單管理.py
import io
import streamlit as st
import pandas as pd
from auth import require_auth
from src.alerts import tutoring_list, makeup_exam_list
from src.stats import detect_anomalies
from src.exporter import export_to_excel

st.set_page_config(page_title="名單管理", layout="wide")
require_auth()

if "exam" not in st.session_state:
    st.warning("請先在主頁選擇考試資料")
    st.stop()

exam = st.session_state["exam"]
df = exam.scores_df

st.title(f"📋 名單管理 — {exam.exam_name}")

tab1, tab2, tab3 = st.tabs(["輔導名單", "補考名單", "成績異常"])

# ── 輔導名單 ──────────────────────────────────────────────────────
with tab1:
    st.subheader("輔導名單")
    tutoring = tutoring_list(df)

    if tutoring.empty:
        st.success("本次考試無需列入輔導的學生 ✅")
    else:
        st.info(f"共 {len(tutoring)} 位學生列入輔導名單")
        classes = ["全部"] + sorted(tutoring["班級"].unique().tolist())
        selected_class = st.selectbox("篩選班級", classes, key="tutoring_class")
        display_df = tutoring if selected_class == "全部" else tutoring[tutoring["班級"] == selected_class]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        buf = io.BytesIO()
        export_to_excel({"輔導名單": tutoring}, "/tmp/_tutoring_tmp.xlsx")
        with open("/tmp/_tutoring_tmp.xlsx", "rb") as f:
            buf.write(f.read())
        st.download_button(
            label="⬇ 下載輔導名單 Excel",
            data=buf.getvalue(),
            file_name=f"{exam.exam_name}_輔導名單.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ── 補考名單 ──────────────────────────────────────────────────────
with tab2:
    st.subheader("補考名單")
    makeup = makeup_exam_list(df)

    if makeup.empty:
        st.success("本次考試無需補考的學生 ✅")
    else:
        st.info(f"共 {len(makeup)} 筆補考記錄（一人多科各計一筆）")

        subjects = makeup["科目"].unique().tolist()
        selected_subject = st.selectbox("篩選科目", ["全部"] + subjects, key="makeup_subject")
        display_df = makeup if selected_subject == "全部" else makeup[makeup["科目"] == selected_subject]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        buf2 = io.BytesIO()
        export_to_excel({"補考名單": makeup}, "/tmp/_makeup_tmp.xlsx")
        with open("/tmp/_makeup_tmp.xlsx", "rb") as f:
            buf2.write(f.read())
        st.download_button(
            label="⬇ 下載補考名單 Excel",
            data=buf2.getvalue(),
            file_name=f"{exam.exam_name}_補考名單.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ── 成績異常 ──────────────────────────────────────────────────────
with tab3:
    st.subheader("成績異常學生")
    anomalies = detect_anomalies(df)

    if anomalies.empty:
        st.success("本次考試未偵測到成績異常學生 ✅")
    else:
        st.warning(f"共偵測到 {len(anomalies)} 筆異常記錄")
        st.dataframe(anomalies, use_container_width=True, hide_index=True)

        buf3 = io.BytesIO()
        export_to_excel({"成績異常": anomalies}, "/tmp/_anomaly_tmp.xlsx")
        with open("/tmp/_anomaly_tmp.xlsx", "rb") as f:
            buf3.write(f.read())
        st.download_button(
            label="⬇ 下載異常名單 Excel",
            data=buf3.getvalue(),
            file_name=f"{exam.exam_name}_成績異常.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
