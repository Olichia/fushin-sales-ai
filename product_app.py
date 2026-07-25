from pathlib import Path

import streamlit as st

from src.floating_chatbot import render_floating_chatbot
from src.session_helpers import initialize_session_state
from src.ui_style import apply_product_styles

initialize_session_state()


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
PAGES_DIR = PROJECT_ROOT / "pages"


# =========================================================
# 全站樣式
# =========================================================

apply_product_styles()


# =========================================================
# 決策分析介面
# =========================================================

product_home_page = st.Page(
    PAGES_DIR / "11_產品首頁.py",
    title="分析總覽",
    icon=":material/dashboard:",
    default=True,
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
    title="主管報表",
    icon=":material/picture_as_pdf:",
)

ai_advisor_page = st.Page(
    PAGES_DIR / "14_AI顧問.py",
    title="AI 策略顧問",
    icon=":material/smart_toy:",
)


# =========================================================
# 資料管理
# =========================================================

data_management_page = st.Page(
    PAGES_DIR / "15_資料管理中心.py",
    title="資料管理中心",
    icon=":material/folder_managed:",
)

sales_processing_page = st.Page(
    PAGES_DIR / "1_資料上傳.py",
    title="銷量資料處理",
    icon=":material/upload_file:",
)

activity_processing_page = st.Page(
    PAGES_DIR / "5_活動資料上傳.py",
    title="活動資料處理",
    icon=":material/event_note:",
)


# =========================================================
# 系統處理
# =========================================================

integration_page = st.Page(
    PAGES_DIR / "7_銷量活動整合.py",
    title="建立整合資料",
    icon=":material/merge:",
)

performance_analysis_page = st.Page(
    PAGES_DIR / "8_活動成效分析.py",
    title="執行成效分析",
    icon=":material/analytics:",
)

strategy_generation_page = st.Page(
    PAGES_DIR / "9_策略建議報表.py",
    title="產生策略報告",
    icon=":material/description:",
)


# =========================================================
# 建立分組導覽
# =========================================================

navigation = st.navigation(
    {
        "決策分析": [
            product_home_page,
            activity_insight_page,
            strategy_center_page,
            management_report_page,
            ai_advisor_page,
        ],
        "資料管理": [
            data_management_page,
            sales_processing_page,
            activity_processing_page,
        ],
        "系統處理": [
            integration_page,
            performance_analysis_page,
            strategy_generation_page,
        ],
    },
    position="sidebar",
    expanded=True,
)


# =========================================================
# 側邊欄共同資訊
# =========================================================

with st.sidebar:
    st.divider()

    st.caption(
        "富信新零售資料分析系統"
    )

    st.caption(
        "產品版 MVP｜UI Redesign"
    )


# =========================================================
# 全站共用：浮動 AI 顧問視窗
# =========================================================
#
# 必須放在 navigation.run() 之前執行。
# 許多分頁在資料尚未備妥時會呼叫 st.stop()，
# 這會讓「整個腳本」（不只該分頁）立刻停止，
# 若浮動視窗寫在 navigation.run() 之後，
# 遇到這種分頁就完全不會渲染。

render_floating_chatbot()


# =========================================================
# 執行目前選擇的頁面
# =========================================================

navigation.run()