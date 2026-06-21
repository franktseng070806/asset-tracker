import streamlit as st
from market import get_usd_twd
from auth import show_login_page, is_logged_in, get_current_user_id, logout
from pages import overview, accounts, stocks, cash, transfers

# ── 頁面設定 ────────────────────────────────────────────────
st.set_page_config(
    page_title="資產追蹤",
    page_icon="💰",
    layout="wide",
)

# ── 檢查登入狀態 ────────────────────────────────────────────
if not is_logged_in():
    show_login_page()
    st.stop()

# ── 已登入：顯示主程式 ──────────────────────────────────────
st.sidebar.title("💰 資產追蹤")
st.sidebar.caption(f"已登入：{st.session_state.get('user_email')}")

if st.sidebar.button("登出"):
    logout()
    st.rerun()

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "選擇頁面",
    ["總覽", "帳戶管理", "股票交易", "現金流水帳", "資產轉移"],
)

usd_twd = get_usd_twd()
st.sidebar.markdown("---")
st.sidebar.metric("即時 USD/TWD", f"{usd_twd}")

user_id = get_current_user_id()

# ── 頁面路由 ────────────────────────────────────────────────
if page == "總覽":
    overview.show(user_id)
elif page == "帳戶管理":
    accounts.show(user_id)
elif page == "股票交易":
    stocks.show(user_id)
elif page == "現金流水帳":
    cash.show(user_id)
elif page == "資產轉移":
    transfers.show(user_id)