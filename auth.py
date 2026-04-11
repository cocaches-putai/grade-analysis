# auth.py
import streamlit as st
from config import APP_PASSWORD


def require_auth() -> None:
    """
    檢查 session_state 中的登入狀態。
    若未登入，顯示密碼輸入表單並停止頁面渲染（st.stop）。
    """
    if st.session_state.get("authenticated"):
        return

    st.title("普台高中成績分析系統")
    st.subheader("請輸入密碼登入")

    with st.form("login_form"):
        password = st.text_input("密碼", type="password")
        submitted = st.form_submit_button("登入")

    if submitted:
        if password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("密碼錯誤，請重新輸入")

    st.stop()
