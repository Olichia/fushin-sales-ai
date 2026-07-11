from pathlib import Path

import streamlit as st


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
PAGES_DIR = PROJECT_ROOT / "pages"


# =========================================================
# 產品介面
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

ai_advisor_page = st.Page(
    PAGES_DIR / "14_AI顧問.py",
    title="AI 策略顧問",
    icon=":material/smart_toy:",
)


# =========================================================
# 資料管理
# =========================================================

sales_upload_page = st.Page(
    PAGES_DIR / "1_資料上傳.py",
    title="銷量資料上傳",
    icon=":material/upload_file:",
)

column_mapping_page = st.Page(
    PAGES_DIR / "2_欄位對應.py",
    title="欄位設定",
    icon=":material/schema:",
)

data_quality_page = st.Page(
    PAGES_DIR / "3_資料品質.py",
    title="銷量資料品質",
    icon=":material/fact_check:",
)

activity_upload_page = st.Page(
    PAGES_DIR / "5_活動資料上傳.py",
    title="活動資料上傳",
    icon=":material/upload:",
)

activity_standardization_page = st.Page(
    PAGES_DIR / "6_活動資料標準化.py",
    title="活動資料品質",
    icon=":material/checklist:",
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
            ai_advisor_page,
        ],
        "資料管理": [
            sales_upload_page,
            column_mapping_page,
            data_quality_page,
            activity_upload_page,
            activity_standardization_page,
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


# 執行使用者目前選擇的頁面
navigation.run()