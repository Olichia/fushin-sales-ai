import streamlit as st


def apply_product_styles() -> None:
    """
    套用產品版共用視覺樣式。

    僅調整外觀，不修改任何資料處理、分析或 Session State 邏輯。
    """

    st.markdown(
        """
        <style>
        /* ==================================================
           品牌與介面變數
        ================================================== */

        :root {
            --app-bg: #F7F8FA;
            --surface: #FFFFFF;
            --surface-soft: #F2F4F7;
            --surface-warm: #FFF6EF;

            --text-primary: #111827;
            --text-secondary: #42526A;
            --text-muted: #667085;

            --border: #D9E0E8;
            --border-soft: #E9EDF2;

            --brand-orange: #F45B1B;
            --brand-orange-dark: #C93F00;
            --brand-orange-soft: #FFF0E7;
            --brand-orange-border: rgba(244, 91, 27, 0.38);

            --brand-magenta: #C02070;
            --brand-blue: #4E56A6;
            --brand-green: #009B73;

            --success: #15803D;
            --warning: #B45309;
            --danger: #C62828;

            --shadow-sm:
                0 1px 2px rgba(16, 24, 40, 0.05),
                0 3px 8px rgba(16, 24, 40, 0.05);

            --shadow-md:
                0 8px 20px rgba(16, 24, 40, 0.08);
        }


        /* ==================================================
           全站背景與字體
        ================================================== */

        html,
        body,
        [data-testid="stAppViewContainer"],
        .stApp {
            background:
                radial-gradient(
                    circle at 100% 0%,
                    rgba(244, 91, 27, 0.045),
                    transparent 30%
                ),
                var(--app-bg);

            color: var(--text-primary);

            font-family:
                "Noto Sans TC",
                "Microsoft JhengHei",
                "Segoe UI",
                sans-serif;

            -webkit-font-smoothing: auto;
            text-rendering: optimizeLegibility;
        }


        /* ==================================================
           主內容區
        ================================================== */

        .block-container,
        [data-testid="stMainBlockContainer"] {
            max-width: 1500px;
            padding-top: 2.1rem;
            padding-bottom: 3rem;
            padding-left: 2.5rem;
            padding-right: 2.5rem;
        }


        /* ==================================================
           一般文字
        ================================================== */

        p,
        li,
        label,
        [data-testid="stWidgetLabel"],
        [data-testid="stCaptionContainer"] {
            color: var(--text-secondary);
        }

        .stMarkdown {
            color: var(--text-primary);
        }

        .stMarkdown p,
        .stMarkdown li {
            color: var(--text-secondary);
            font-weight: 500;
            line-height: 1.75;
        }

        .stMarkdown strong {
            color: var(--text-primary);
            font-weight: 750;
        }


        /* ==================================================
           標題
        ================================================== */

        h1 {
            color: var(--text-primary);
            font-size: 2rem;
            font-weight: 850;
            letter-spacing: -0.03em;
            margin-bottom: 0.5rem;
        }

        h2 {
            position: relative;
            color: #1B2433;
            font-weight: 800;
            letter-spacing: -0.02em;
            padding-left: 14px;
        }

        h2::before {
            content: "";
            position: absolute;
            top: 0.18em;
            bottom: 0.18em;
            left: 0;
            width: 5px;
            border-radius: 5px;

            background:
                linear-gradient(
                    180deg,
                    var(--brand-orange) 0%,
                    var(--brand-magenta) 52%,
                    var(--brand-blue) 100%
                );
        }

        h3 {
            color: #253047;
            font-weight: 750;
        }


        /* ==================================================
           側邊欄
        ================================================== */

        [data-testid="stSidebar"] {
            position: relative;

            background:
                linear-gradient(
                    180deg,
                    var(--surface-warm) 0%,
                    #FFFFFF 75%
                );

            border-right: 1px solid var(--border);

            box-shadow:
                2px 0 16px rgba(16, 24, 40, 0.05);
        }

        [data-testid="stSidebar"]::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            z-index: 10;

            background:
                linear-gradient(
                    90deg,
                    var(--brand-orange) 0%,
                    var(--brand-magenta) 35%,
                    var(--brand-blue) 68%,
                    var(--brand-green) 100%
                );
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.1rem;
        }

        [data-testid="stSidebarContent"] {
            padding-top: 0.7rem;
        }

        [data-testid="stSidebarNav"] a {
            border-radius: 10px;
            margin-bottom: 0.15rem;
            color: #4B5565;
            font-weight: 650;

            transition:
                color 0.15s ease,
                background-color 0.15s ease,
                box-shadow 0.15s ease,
                transform 0.15s ease;
        }

        [data-testid="stSidebarNav"] a span,
        [data-testid="stSidebarNav"] a p {
            color: inherit !important;
        }

        [data-testid="stSidebarNav"] a:hover {
            background-color: var(--brand-orange-soft);
            color: var(--brand-orange-dark);
            transform: translateX(1px);
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background:
                linear-gradient(
                    135deg,
                    var(--brand-orange) 0%,
                    #EA4E10 100%
                ) !important;

            color: #FFFFFF !important;
            font-weight: 800;

            box-shadow:
                0 5px 14px var(--brand-orange-border);
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] *,
        [data-testid="stSidebarNav"] a[aria-current="page"] svg {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }


        /* ==================================================
           流程頁標題
        ================================================== */

        .step-label {
            margin-bottom: 0.5rem;

            color: var(--brand-orange);
            font-size: 0.9rem;
            font-weight: 850;
            letter-spacing: 0.14em;
        }

        .product-page-title {
            display: flex;
            align-items: center;
            gap: 0.9rem;
            margin-bottom: 0.55rem;
        }

        .product-page-title h1 {
            margin: 0;
            color: var(--text-primary);
        }

        .product-page-title-bar {
            width: 7px;
            height: 36px;
            flex: 0 0 7px;
            border-radius: 7px;

            background:
                linear-gradient(
                    180deg,
                    var(--brand-orange) 0%,
                    var(--brand-magenta) 52%,
                    var(--brand-blue) 100%
                );
        }

        .product-page-description {
            max-width: 1180px;
            margin-top: 0;
            margin-bottom: 1.7rem;

            color: var(--text-secondary) !important;
            font-size: 1rem;
            font-weight: 500;
            line-height: 1.85;
        }


        /* ==================================================
           一般容器與卡片
        ================================================== */

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 15px;
            box-shadow: var(--shadow-sm);
        }

        [data-testid="stVerticalBlockBorderWrapper"] > div {
            border-radius: 15px;
        }


        /* ==================================================
           上傳卡片
        ================================================== */

        .upload-card-heading {
            display: flex;
            align-items: flex-start;
            gap: 0.9rem;
            margin-bottom: 1rem;
        }

        .upload-card-icon {
            display: flex;
            align-items: center;
            justify-content: center;

            width: 48px;
            height: 48px;
            flex: 0 0 48px;

            border-radius: 13px;
            background: var(--brand-orange-soft);

            font-size: 1.4rem;
        }

        .upload-card-title {
            margin-bottom: 0.25rem;

            color: var(--text-primary);
            font-size: 1.2rem;
            font-weight: 800;
        }

        .upload-card-description {
            max-width: 900px;

            color: var(--text-secondary);
            font-size: 0.94rem;
            font-weight: 500;
            line-height: 1.65;
        }


        /* ==================================================
           File uploader
        ================================================== */

        [data-testid="stFileUploader"] {
            padding: 1rem;

            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;

            box-shadow: var(--shadow-sm);
        }

        [data-testid="stFileUploaderDropzone"] {
            min-height: 135px;
            padding: 1.8rem 1rem;

            display: flex;
            align-items: center;

            background: #F4F6F8;

            border:
                1.5px dashed
                #CFD7E3;

            border-radius: 12px;

            transition:
                border-color 0.15s ease,
                background-color 0.15s ease;
        }

        [data-testid="stFileUploaderDropzone"]:hover {
            background: var(--brand-orange-soft);
            border-color: var(--brand-orange);
        }

        [data-testid="stFileUploaderDropzone"] button {
            border-radius: 9px;
            border-color: var(--brand-orange-border);
            color: var(--brand-orange-dark);
            font-weight: 700;
        }

        [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] span {
            color: #4C5A70 !important;
            font-weight: 500;
        }


        /* ==================================================
           KPI 指標
        ================================================== */

        [data-testid="stMetric"] {
            min-height: 112px;
            height: 100%;

            padding: 1rem 1.1rem;

            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;

            box-shadow: var(--shadow-sm);

            transition:
                transform 0.15s ease,
                box-shadow 0.15s ease,
                border-color 0.15s ease;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: var(--brand-orange-border);
            box-shadow: var(--shadow-md);
        }

        [data-testid="stMetricLabel"] {
            color: #526076;
            font-weight: 650;
        }

        [data-testid="stMetricValue"] {
            color: var(--text-primary);
            font-weight: 850;
        }

        [data-testid="stMetricDelta"] {
            font-weight: 700;
        }


        /* ==================================================
           按鈕
        ================================================== */

        .stButton > button,
        .stDownloadButton > button {
            min-height: 2.65rem;
            border-radius: 10px;
            font-weight: 750;

            transition:
                border-color 0.15s ease,
                background-color 0.15s ease,
                color 0.15s ease,
                box-shadow 0.15s ease,
                transform 0.15s ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-1px);
        }

        .stButton > button[kind="primary"],
        button[data-testid="stBaseButton-primary"] {
            background:
                linear-gradient(
                    135deg,
                    var(--brand-orange) 0%,
                    #EA4E10 100%
                ) !important;

            color: #FFFFFF !important;
            border-color: var(--brand-orange) !important;

            box-shadow:
                0 4px 12px var(--brand-orange-border);
        }

        .stButton > button[kind="primary"] *,
        button[data-testid="stBaseButton-primary"] * {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }

        .stButton > button p,
        .stButton > button span,
        button[data-testid="stBaseButton-primary"] p,
        button[data-testid="stBaseButton-primary"] span {
            color: inherit !important;
            font-weight: 800 !important;
        }

        .stButton > button[kind="primary"]:hover,
        button[data-testid="stBaseButton-primary"]:hover {
            background:
                linear-gradient(
                    135deg,
                    var(--brand-orange-dark) 0%,
                    #B93B05 100%
                ) !important;

            color: #FFFFFF !important;
            border-color: var(--brand-orange-dark) !important;

            box-shadow:
                0 6px 16px rgba(201, 63, 0, 0.25);
        }

        .stButton > button[kind="secondary"],
        .stDownloadButton > button,
        button[data-testid="stBaseButton-secondary"] {
            background: var(--surface) !important;
            color: var(--brand-orange-dark) !important;
            border-color: var(--brand-orange-border) !important;
        }

        .stButton > button[kind="secondary"]:hover,
        .stDownloadButton > button:hover,
        button[data-testid="stBaseButton-secondary"]:hover {
            background: var(--brand-orange-soft) !important;
            color: var(--brand-orange-dark) !important;
            border-color: var(--brand-orange) !important;
        }

        .stButton > button:disabled {
            background: #E7EBF0 !important;
            color: #8791A3 !important;
            border-color: #D8DEE7 !important;
            box-shadow: none;
            transform: none;
        }


        /* ==================================================
           輸入元件
        ================================================== */

        [data-testid="stSelectbox"] > div > div,
        [data-testid="stMultiSelect"] > div > div,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] > div {
            background: var(--surface-soft);
            border-color: var(--border);
            border-radius: 9px;
            color: var(--text-primary);
        }

        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] span {
            color: var(--text-primary) !important;
        }

        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within {
            border-color: var(--brand-orange);
            box-shadow: 0 0 0 1px var(--brand-orange);
        }

        label,
        [data-testid="stWidgetLabel"] {
            color: #344054;
            font-weight: 700;
        }


        /* ==================================================
           資料表
        ================================================== */

        [data-testid="stDataFrame"] {
            overflow: hidden;

            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;

            box-shadow: var(--shadow-sm);
        }


        /* ==================================================
           Expander
        ================================================== */

        [data-testid="stExpander"] {
            overflow: hidden;

            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;

            box-shadow: var(--shadow-sm);
        }

        [data-testid="stExpander"] summary {
            color: var(--text-primary);
            font-weight: 750;
        }

        [data-testid="stExpander"] summary:hover {
            color: var(--brand-orange-dark);
        }


        /* ==================================================
           Tabs
        ================================================== */

        [data-baseweb="tab-list"] {
            gap: 0.35rem;
            border-bottom: 1px solid var(--border);
        }

        [data-baseweb="tab"] {
            padding-left: 1rem;
            padding-right: 1rem;
            border-radius: 9px 9px 0 0;

            color: #526076;
            font-weight: 700;
        }

        [data-baseweb="tab"]:hover {
            color: var(--brand-orange-dark);
            background: var(--brand-orange-soft);
        }

        [aria-selected="true"][data-baseweb="tab"] {
            color: var(--brand-orange-dark);
        }

        [data-baseweb="tab-highlight"] {
            background-color: var(--brand-orange);
        }


        /* ==================================================
           訊息框
        ================================================== */

        [data-testid="stAlert"] {
            border-radius: 11px;
            box-shadow: var(--shadow-sm);
        }

        [data-testid="stAlert"] p,
        [data-testid="stAlert"] li,
        [data-testid="stAlert"] span {
            color: #344054 !important;
            font-weight: 550;
        }


        /* ==================================================
           Status
        ================================================== */

        [data-testid="stStatusWidget"] {
            overflow: hidden;

            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;

            box-shadow: var(--shadow-sm);
        }


        /* ==================================================
           Progress
        ================================================== */

        [data-testid="stProgress"] > div > div > div {
            background:
                linear-gradient(
                    90deg,
                    var(--brand-orange),
                    var(--brand-magenta)
                );
        }


        /* ==================================================
           Chat
        ================================================== */

        [data-testid="stChatMessage"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: var(--shadow-sm);
        }

        [data-testid="stChatInput"] {
            border-radius: 12px;
        }

        [data-testid="stChatInput"] textarea {
            border-radius: 10px;
            color: var(--text-primary);
        }


        /* ==================================================
           Checkbox / Radio
        ================================================== */

        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label {
            color: #344054;
            font-weight: 650;
        }


        /* ==================================================
           分隔線
        ================================================== */

        hr {
            margin-top: 2rem;
            margin-bottom: 2rem;
            border-color: var(--border-soft);
        }


        /* ==================================================
           Streamlit 預設工具列
        ================================================== */

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }


        /* ==================================================
           手機與窄螢幕
        ================================================== */

        @media (max-width: 900px) {
            .block-container,
            [data-testid="stMainBlockContainer"] {
                padding-top: 1.2rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            h1 {
                font-size: 1.65rem;
            }

            h2 {
                font-size: 1.25rem;
            }

            [data-testid="stMetric"] {
                min-height: auto;
            }

            [data-testid="stSidebar"] {
                box-shadow: none;
            }
        }


        /* ==================================================
           首頁與流程頁額外元件
        ================================================== */

        .workflow-badge {
            display: inline-flex;
            align-items: center;
            width: fit-content;
            margin: 0.35rem 0 0.8rem;
            padding: 0.28rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 800;
        }

        .workflow-badge-completed {
            background: #E8F7EF;
            color: #137A48;
            border: 1px solid #B9E5CB;
        }

        .workflow-badge-pending {
            background: #FFF4E5;
            color: #A65300;
            border: 1px solid #F2D19B;
        }

        .progress-card-title {
            margin-bottom: 0.7rem;
            color: var(--text-primary);
            font-weight: 800;
        }

        .next-step-panel {
            margin: 1rem 0 1.8rem;
            padding: 1.25rem 1.4rem;

            background:
                linear-gradient(
                    135deg,
                    #FFF5ED 0%,
                    #FFFFFF 100%
                );

            border: 1px solid var(--brand-orange-border);
            border-radius: 14px;
            box-shadow: var(--shadow-sm);
        }

        .next-step-eyebrow {
            margin-bottom: 0.3rem;

            color: var(--brand-orange);
            font-size: 0.78rem;
            font-weight: 850;
            letter-spacing: 0.1em;
        }

        .next-step-title {
            margin-bottom: 0.45rem;

            color: var(--text-primary);
            font-size: 1.15rem;
            font-weight: 850;
        }

        .next-step-description {
            color: var(--text-secondary);
            font-weight: 500;
            line-height: 1.7;
        }

        .next-step-location {
            margin-top: 0.65rem;

            color: var(--brand-orange-dark);
            font-weight: 750;
        }

        .workflow-step-header,
        .status-card-heading,
        .analysis-action-heading {
            display: flex;
            align-items: flex-start;
            gap: 0.85rem;
            margin-bottom: 0.75rem;
        }

        .workflow-step-icon,
        .status-card-icon,
        .analysis-action-icon {
            display: flex;
            align-items: center;
            justify-content: center;

            width: 46px;
            height: 46px;
            flex: 0 0 46px;

            border-radius: 13px;
            background: var(--brand-orange-soft);

            font-size: 1.3rem;
        }

        .workflow-step-number {
            margin-bottom: 0.18rem;

            color: var(--brand-orange);
            font-size: 0.75rem;
            font-weight: 850;
            letter-spacing: 0.08em;
        }

        .workflow-step-title,
        .status-card-title,
        .analysis-action-title {
            color: var(--text-primary);
            font-size: 1.05rem;
            font-weight: 850;
        }

        .status-card-subtitle,
        .analysis-action-description {
            margin-top: 0.18rem;

            color: var(--text-secondary);
            font-size: 0.88rem;
            font-weight: 500;
            line-height: 1.55;
        }

        .output-card-label {
            margin-bottom: 0.25rem;

            color: var(--brand-orange-dark);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.04em;
        }

        /* 讓分析流程卡片高度較一致 */
        .workflow-step-header + div,
        .status-card-heading + div,
        .analysis-action-heading + div {
            color: var(--text-secondary);
        }

        /* 手機版流程卡片微調 */
        @media (max-width: 900px) {
            .next-step-panel {
                padding: 1rem;
            }

            .workflow-step-icon,
            .status-card-icon,
            .analysis-action-icon {
                width: 42px;
                height: 42px;
                flex-basis: 42px;
            }

            .workflow-step-title,
            .status-card-title,
            .analysis-action-title {
                font-size: 1rem;
            }
        }


        /* ==================================================
           分析總覽與活動洞察
        ================================================== */

        .overview-status-number {
            margin-bottom: 0.25rem;

            color: var(--brand-orange);
            font-size: 0.76rem;
            font-weight: 850;
            letter-spacing: 0.08em;
        }

        .overview-status-title {
            margin-bottom: 0.7rem;

            color: var(--text-primary);
            font-size: 1.05rem;
            font-weight: 850;
        }

        .analysis-filter-heading {
            display: flex;
            align-items: flex-start;
            gap: 0.85rem;
            margin-bottom: 1rem;
        }

        .analysis-filter-icon {
            display: flex;
            align-items: center;
            justify-content: center;

            width: 44px;
            height: 44px;
            flex: 0 0 44px;

            border-radius: 12px;
            background: var(--brand-orange-soft);

            font-size: 1.25rem;
        }

        .analysis-filter-title {
            color: var(--text-primary);
            font-size: 1.02rem;
            font-weight: 850;
        }

        .analysis-filter-description {
            margin-top: 0.18rem;

            color: var(--text-secondary);
            font-size: 0.88rem;
            font-weight: 500;
            line-height: 1.55;
        }

        /* Plotly 圖表外層增加卡片感 */
        [data-testid="stPlotlyChart"] {
            overflow: hidden;
            padding: 0.35rem;

            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;

            box-shadow: var(--shadow-sm);
        }

        /* Plotly 圖表本體維持透明，避免出現灰底 */
        [data-testid="stPlotlyChart"] > div {
            border-radius: 12px;
        }

        /* 分析篩選卡內的輸入元件增加間距 */
        [data-testid="stVerticalBlockBorderWrapper"]
        .analysis-filter-heading {
            margin-top: 0.1rem;
        }

        /* 分析頁 KPI 與狀態卡內文字維持高對比 */
        .overview-status-title,
        .analysis-filter-title,
        .analysis-filter-description {
            text-rendering: optimizeLegibility;
        }

        @media (max-width: 900px) {
            .analysis-filter-heading {
                gap: 0.7rem;
            }

            .analysis-filter-icon {
                width: 40px;
                height: 40px;
                flex-basis: 40px;
            }

            .overview-status-title,
            .analysis-filter-title {
                font-size: 0.98rem;
            }

            [data-testid="stPlotlyChart"] {
                padding: 0.15rem;
            }
        }


        /* ==================================================
           策略中心
        ================================================== */

        .strategy-summary-card {
            height: 100%;
            min-height: 190px;
            padding: 1.15rem 1.2rem;

            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;

            box-shadow: var(--shadow-sm);
        }

        .strategy-summary-continue {
            border-top: 4px solid #178553;
        }

        .strategy-summary-optimize {
            border-top: 4px solid var(--brand-orange);
        }

        .strategy-summary-review {
            border-top: 4px solid #C62828;
        }

        .strategy-summary-eyebrow {
            margin-bottom: 0.35rem;

            color: var(--text-muted);
            font-size: 0.74rem;
            font-weight: 850;
            letter-spacing: 0.09em;
        }

        .strategy-summary-title {
            color: var(--text-primary);
            font-size: 1.05rem;
            font-weight: 850;
        }

        .strategy-summary-count {
            margin: 0.45rem 0;

            color: var(--text-primary);
            font-size: 2rem;
            font-weight: 900;
            line-height: 1;
        }

        .strategy-summary-description {
            color: var(--text-secondary);
            font-size: 0.88rem;
            font-weight: 500;
            line-height: 1.6;
        }

        @media (max-width: 900px) {
            .strategy-summary-card {
                min-height: auto;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )