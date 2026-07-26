from pathlib import Path
import base64

import pandas as pd
import streamlit as st

from src.floating_chatbot import render_floating_chatbot
from src.session_helpers import initialize_session_state
from src.ui_style import apply_product_styles


# =========================================================
# 頁面設定
# =========================================================

st.set_page_config(
    page_title="富信新零售資料分析系統",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 初始化
# =========================================================

initialize_session_state()

PROJECT_ROOT = Path(__file__).resolve().parent
PAGES_DIR = PROJECT_ROOT / "app_pages"
ASSETS_DIR = PROJECT_ROOT / "assets"
BRAND_LOGO_PATH = ASSETS_DIR / "logo-white.png"

apply_product_styles()


# =========================================================
# 頁面定義
# =========================================================

data_management_page = st.Page(
    PAGES_DIR / "15_資料管理中心.py",
    title="開始使用",
    icon=":material/home:",
    default=True,
)

sales_processing_page = st.Page(
    PAGES_DIR / "1_資料上傳.py",
    title="01 銷量資料處理",
    icon=":material/upload_file:",
)

activity_processing_page = st.Page(
    PAGES_DIR / "5_活動資料上傳.py",
    title="02 活動資料處理",
    icon=":material/event_note:",
)

full_analysis_page = st.Page(
    PAGES_DIR / "6_執行完整分析.py",
    title="03 執行完整分析",
    icon=":material/play_circle:",
)

product_home_page = st.Page(
    PAGES_DIR / "11_產品首頁.py",
    title="分析總覽",
    icon=":material/dashboard:",
)

activity_insight_page = st.Page(
    PAGES_DIR / "12_活動洞察.py",
    title="活動洞察",
    icon=":material/monitoring:",
)

strategy_center_page = st.Page(
    PAGES_DIR / "13_策略中心.py",
    title="策略中心",
    icon=":material/assignment:",
)

management_report_page = st.Page(
    PAGES_DIR / "16_主管報表中心.py",
    title="主管報表中心",
    icon=":material/picture_as_pdf:",
)

ai_advisor_page = st.Page(
    PAGES_DIR / "14_AI顧問.py",
    title="AI 策略顧問",
    icon=":material/smart_toy:",
)


# =========================================================
# 品牌區
#
# Streamlit 的原生 navigation 會優先渲染在側邊欄。
# 品牌區仍使用正常 Streamlit 元件，再由 ui_style.py
# 精確定位到導覽上方。
# =========================================================

with st.sidebar:
    with st.container(
        key="reference_brand_header",
    ):
        if BRAND_LOGO_PATH.exists():
            encoded_logo = base64.b64encode(
                BRAND_LOGO_PATH.read_bytes()
            ).decode("utf-8")

            brand_html = (
                '<div class="reference-brand-wrap">'
                f'<img class="reference-brand-logo" '
                f'src="data:image/png;base64,{encoded_logo}" '
                'alt="品牌 Logo">'
                '<div class="reference-brand-copy">'
                '<div class="reference-brand-name">'
                '富信新零售'
                '<span class="reference-brand-x">×</span>'
                '台灣大哥大'
                '</div>'
                '<div class="reference-brand-sub">'
                'AI 電商活動策略決策助手'
                '</div>'
                '</div>'
                '</div>'
            )

            st.markdown(
                brand_html,
                unsafe_allow_html=True,
            )


# =========================================================
# 原生分組導覽
# =========================================================

navigation = st.navigation(
    {
        "開始使用": [
            data_management_page,
        ],
        "資料準備": [
            sales_processing_page,
            activity_processing_page,
        ],
        "分析流程": [
            full_analysis_page,
        ],
        "成果與決策": [
            product_home_page,
            activity_insight_page,
            strategy_center_page,
            management_report_page,
            ai_advisor_page,
        ],
    },
    position="sidebar",
    expanded=True,
)


# =========================================================
# 側邊欄進度
# =========================================================

sales_dataframe = st.session_state.get(
    "standardized_dataframe"
)

activity_dataframe = st.session_state.get(
    "activity_standardized_dataframe"
)

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)

sales_ready = (
    isinstance(sales_dataframe, pd.DataFrame)
    and not sales_dataframe.empty
    and bool(
        st.session_state.get(
            "sales_data_confirmed",
            False,
        )
    )
)

activity_ready = (
    isinstance(activity_dataframe, pd.DataFrame)
    and not activity_dataframe.empty
    and bool(
        st.session_state.get(
            "activity_data_confirmed",
            False,
        )
    )
)

analysis_ready = (
    isinstance(performance_dataframe, pd.DataFrame)
    and not performance_dataframe.empty
    and bool(
        st.session_state.get(
            "full_analysis_completed",
            False,
        )
    )
)

completed_count = sum(
    [
        sales_ready,
        activity_ready,
        analysis_ready,
    ]
)

with st.sidebar:
    st.divider()
    st.caption("資料進度")
    st.progress(
        completed_count / 3,
        text=f"已完成 {completed_count}／3",
    )
    st.caption(
        "Fushin Sales AI · Product MVP 1.0"
    )


# =========================================================
# 浮動 AI 顧問
# =========================================================

render_floating_chatbot()


# =========================================================
# 執行頁面
# =========================================================

navigation.run()