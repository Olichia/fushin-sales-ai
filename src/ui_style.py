import streamlit as st


def apply_product_styles() -> None:
    """
    套用產品版共用視覺樣式。

    僅調整外觀，不修改任何資料或分析邏輯。
    """

    st.markdown(
        """
        <style>
        /* ==================================================
           頁面整體寬度與間距
        ================================================== */

        .block-container {
            max-width: 1500px;
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            padding-left: 2.5rem;
            padding-right: 2.5rem;
        }


        /* ==================================================
           標題
        ================================================== */

        h1 {
            color: #172033;
            font-weight: 750;
            letter-spacing: -0.03em;
            margin-bottom: 0.5rem;
        }

        h2 {
            color: #202A3B;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        h3 {
            color: #293448;
            font-weight: 650;
        }


        /* ==================================================
           側邊欄
        ================================================== */

        [data-testid="stSidebar"] {
            background-color: #F3F6FA;
            border-right: 1px solid #E1E7F0;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.2rem;
        }

        [data-testid="stSidebarNav"] a {
            border-radius: 9px;
            margin-bottom: 0.15rem;
        }

        [data-testid="stSidebarNav"] a:hover {
            background-color: #E5EDF9;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background-color: #DDE8FA;
            color: #073F99;
            font-weight: 650;
        }


        /* ==================================================
           KPI 指標
        ================================================== */

        [data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 2px 8px rgba(18, 38, 63, 0.04);
            min-height: 112px;
        }

        [data-testid="stMetricLabel"] {
            color: #667085;
            font-weight: 500;
        }

        [data-testid="stMetricValue"] {
            color: #172033;
            font-weight: 720;
        }


        /* ==================================================
           容器與卡片
        ================================================== */

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #E2E8F0;
            border-radius: 14px;
            box-shadow: 0 2px 8px rgba(18, 38, 63, 0.035);
        }


        /* ==================================================
           按鈕
        ================================================== */

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 9px;
            min-height: 2.65rem;
            font-weight: 600;
            transition:
                border-color 0.15s ease,
                background-color 0.15s ease,
                transform 0.15s ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-1px);
        }


        /* ==================================================
           輸入元件
        ================================================== */

        [data-testid="stSelectbox"] > div > div,
        [data-testid="stMultiSelect"] > div > div,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input {
            border-radius: 9px;
        }


        /* ==================================================
           資料表
        ================================================== */

        [data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            overflow: hidden;
        }


        /* ==================================================
           訊息框
        ================================================== */

        [data-testid="stAlert"] {
            border-radius: 11px;
        }


        /* ==================================================
           分隔線
        ================================================== */

        hr {
            border-color: #E5EAF1;
            margin-top: 2rem;
            margin-bottom: 2rem;
        }


        /* ==================================================
           Chat
        ================================================== */

        [data-testid="stChatMessage"] {
            border-radius: 12px;
        }

        [data-testid="stChatInput"] {
            border-radius: 12px;
        }


        /* ==================================================
           手機與窄螢幕
        ================================================== */

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1.2rem;
            }

            [data-testid="stMetric"] {
                min-height: auto;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )