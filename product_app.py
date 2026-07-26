from pathlib import Path

import pandas as pd
import streamlit as st

from src.floating_chatbot import render_floating_chatbot
from src.session_helpers import initialize_session_state
from src.ui_style import apply_product_styles


st.set_page_config(
    page_title="富信新零售資料分析系統",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_session_state()

PROJECT_ROOT = Path(__file__).resolve().parent
PAGES_DIR = PROJECT_ROOT / "pages"

apply_product_styles()


def dataframe_ready(dataframe: object) -> bool:
    return isinstance(dataframe, pd.DataFrame) and not dataframe.empty


def render_sidebar_status(*, label: str, completed: bool) -> None:
    status_class = (
        "sidebar-status-completed"
        if completed
        else "sidebar-status-pending"
    )
    status_text = "已完成" if completed else "待完成"

    st.markdown(
        f"""
        <div class="sidebar-status-row">
            <div class="sidebar-status-label">{label}</div>
            <div class="sidebar-status-pill {status_class}">
                {status_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-mark">FS</div>
            <div class="sidebar-brand-content">
                <div class="sidebar-brand-title">富信新零售</div>
                <div class="sidebar-brand-subtitle">
                    SALES INTELLIGENCE
                </div>
            </div>
        </div>

        <div class="sidebar-brand-description">
            銷售與活動成效決策系統
        </div>
        """,
        unsafe_allow_html=True,
    )


navigation = st.navigation(
    {
        "開始使用": [data_management_page],
        "資料準備": [
            sales_processing_page,
            activity_processing_page,
        ],
        "分析流程": [full_analysis_page],
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


sales_dataframe = st.session_state.get("standardized_dataframe")
activity_dataframe = st.session_state.get(
    "activity_standardized_dataframe"
)
performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)
strategy_dataframe = st.session_state.get(
    "strategy_report_dataframe"
)

sales_completed = (
    dataframe_ready(sales_dataframe)
    and bool(st.session_state.get("sales_data_confirmed", False))
)

activity_completed = (
    dataframe_ready(activity_dataframe)
    and bool(st.session_state.get("activity_data_confirmed", False))
)

analysis_completed = (
    dataframe_ready(performance_dataframe)
    and dataframe_ready(strategy_dataframe)
    and bool(st.session_state.get("full_analysis_completed", False))
)


with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-section-divider"></div>
        <div class="sidebar-section-title">資料進度</div>
        """,
        unsafe_allow_html=True,
    )

    render_sidebar_status(
        label="銷量資料",
        completed=sales_completed,
    )
    render_sidebar_status(
        label="活動資料",
        completed=activity_completed,
    )
    render_sidebar_status(
        label="完整分析",
        completed=analysis_completed,
    )

    completed_count = sum(
        [
            sales_completed,
            activity_completed,
            analysis_completed,
        ]
    )

    st.progress(
        completed_count / 3,
        text=f"已完成 {completed_count}／3",
    )

    st.markdown(
        """
        <div class="sidebar-section-divider"></div>
        <div class="sidebar-footer">
            <div class="sidebar-footer-name">Fushin Sales AI</div>
            <div class="sidebar-footer-version">
                Product MVP · Version 1.0
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_floating_chatbot()

navigation.run()