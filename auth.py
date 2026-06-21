import streamlit as st
import hashlib
from supabase_client import get_supabase


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def sign_up(email: str, password: str):
    supabase = get_supabase()
    existing = supabase.table("users").select("id").eq("email", email).execute()
    if existing.data:
        return False, "此 Email 已被註冊"

    password_hash = hash_password(password)
    result = supabase.table("users").insert({
        "email": email,
        "password_hash": password_hash,
    }).execute()

    if result.data:
        return True, "註冊成功！"
    return False, "註冊失敗，請稍後再試"


def sign_in(email: str, password: str):
    supabase = get_supabase()
    password_hash = hash_password(password)
    result = supabase.table("users").select("*").eq("email", email).eq("password_hash", password_hash).execute()

    if result.data:
        return True, result.data[0]
    return False, None


def show_login_page():
    st.title("💰 資產追蹤")
    st.subheader("登入 / 註冊")

    tab1, tab2 = st.tabs(["登入", "註冊"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("密碼", type="password")
            submitted = st.form_submit_button("登入", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("請輸入 Email 和密碼")
                else:
                    success, user = sign_in(email, password)
                    if success:
                        st.session_state["user_id"] = user["id"]
                        st.session_state["user_email"] = user["email"]
                        st.success("登入成功！")
                        st.rerun()
                    else:
                        st.error("Email 或密碼錯誤")

    with tab2:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("密碼", type="password", key="signup_password")
            confirm_password = st.text_input("確認密碼", type="password")
            submitted = st.form_submit_button("註冊", use_container_width=True)

            if submitted:
                if not new_email or not new_password:
                    st.error("請輸入 Email 和密碼")
                elif new_password != confirm_password:
                    st.error("兩次密碼不一致")
                elif len(new_password) < 6:
                    st.error("密碼至少需要 6 個字元")
                else:
                    success, message = sign_up(new_email, new_password)
                    if success:
                        st.success(message + "，請切換到登入頁籤")
                    else:
                        st.error(message)


def is_logged_in() -> bool:
    return "user_id" in st.session_state


def get_current_user_id():
    return st.session_state.get("user_id")


def logout():
    for key in ["user_id", "user_email"]:
        if key in st.session_state:
            del st.session_state[key]