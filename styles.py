import streamlit as st


def apply_dark_theme():
    st.markdown("""
    <style>
    /* ── 整體背景與字體 ─────────────────────────────────── */
    .stApp {
        background-color: #0E1117;
        color: #E6E6E6;
    }

    [data-testid="stSidebar"] {
        background-color: #161A23;
        border-right: 1px solid #2A2F3A;
    }

    /* ── 標題淡入動畫 ───────────────────────────────────── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    h1, h2, h3 {
        animation: fadeInUp 0.4s ease-out;
    }

    .block-container {
        animation: fadeInUp 0.35s ease-out;
        padding-top: 2rem;
    }

    /* ── Metric 卡片美化 ───────────────────────────────── */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1A1F2B, #161A23);
        border: 1px solid #2A2F3A;
        border-radius: 14px;
        padding: 16px 20px;
        transition: all 0.25s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }

    [data-testid="stMetric"]:hover {
        border-color: #3D7FFF;
        box-shadow: 0 4px 16px rgba(61,127,255,0.15);
        transform: translateY(-2px);
    }

    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        color: #F2F4F8 !important;
    }

    [data-testid="stMetricLabel"] {
        color: #9AA3B2 !important;
        font-size: 0.85rem !important;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }

    /* ── 按鈕美化 ───────────────────────────────────────── */
    .stButton > button {
        border-radius: 10px;
        border: 1px solid #2A2F3A;
        background: linear-gradient(145deg, #1E2330, #161A23);
        color: #E6E6E6;
        transition: all 0.2s ease;
        font-weight: 500;
    }

    .stButton > button:hover {
        border-color: #3D7FFF;
        background: linear-gradient(145deg, #232940, #1A1F2B);
        color: #FFFFFF;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(61,127,255,0.2);
    }

    .stButton > button:active {
        transform: translateY(0px);
    }

    /* primary 按鈕（表單送出鍵）特別強調 */
    button[kind="primaryFormSubmit"], button[kind="formSubmit"] {
        background: linear-gradient(145deg, #3D7FFF, #2C5FD9) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
    }

    button[kind="primaryFormSubmit"]:hover, button[kind="formSubmit"]:hover {
        box-shadow: 0 4px 16px rgba(61,127,255,0.4) !important;
        transform: translateY(-1px);
    }

    /* ── 輸入框美化 ─────────────────────────────────────── */
    .stTextInput input, .stNumberInput input, .stDateInput input,
    .stSelectbox > div > div {
        background-color: #161A23 !important;
        border: 1px solid #2A2F3A !important;
        border-radius: 8px !important;
        color: #E6E6E6 !important;
        transition: border-color 0.2s ease;
    }

    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #3D7FFF !important;
        box-shadow: 0 0 0 2px rgba(61,127,255,0.15) !important;
    }

    /* ── Tabs 美化 ──────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid #2A2F3A;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        color: #9AA3B2;
        transition: all 0.2s ease;
        padding: 8px 16px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1A1F2B !important;
        color: #3D7FFF !important;
        font-weight: 600;
    }

    /* ── Expander 美化 ──────────────────────────────────── */
    [data-testid="stExpander"] {
        background-color: #161A23;
        border: 1px solid #2A2F3A;
        border-radius: 12px;
        transition: border-color 0.2s ease;
    }

    [data-testid="stExpander"]:hover {
        border-color: #3D7FFF55;
    }

    /* ── DataFrame / Table 美化 ─────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #2A2F3A;
    }

    /* ── Radio button 橫向選單美化 ──────────────────────── */
    .stRadio [role="radiogroup"] label {
        background-color: #161A23;
        border: 1px solid #2A2F3A;
        border-radius: 8px;
        padding: 6px 14px;
        margin-right: 6px;
        transition: all 0.2s ease;
    }

    .stRadio [role="radiogroup"] label:hover {
        border-color: #3D7FFF;
    }

    /* ── 分隔線淡化 ─────────────────────────────────────── */
    hr {
        border-color: #2A2F3A !important;
        margin: 1.2rem 0 !important;
    }

    /* ── 成功/錯誤/警告訊息圓角化 ───────────────────────── */
    .stAlert {
        border-radius: 10px;
        animation: fadeInUp 0.3s ease-out;
    }

    /* ── Sidebar radio（頁面選單）卡片化 ─────────────────── */
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
        width: 100%;
        margin-bottom: 4px;
    }

    /* ── 捲動條美化 ─────────────────────────────────────── */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0E1117;
    }
    ::-webkit-scrollbar-thumb {
        background: #2A2F3A;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #3D7FFF;
    }
    </style>
    """, unsafe_allow_html=True)