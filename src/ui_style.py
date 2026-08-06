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

            --ai-accent: #5DA9FF;
            --ai-accent-deep: #1D6FCC;
            --ai-accent-soft: rgba(93, 169, 255, 0.10);
            --ai-accent-border: rgba(93, 169, 255, 0.4);

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

        .product-page-title h3 {
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
            overflow-x: auto;
            overflow-y: hidden;

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
           主管報表中心
        ================================================== */

        .report-content-heading,
        .report-download-ready {
            display: flex;
            align-items: flex-start;
            gap: 0.85rem;
            margin-bottom: 1rem;
        }

        .report-content-icon,
        .report-download-icon {
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

        .report-content-title,
        .report-download-title {
            color: var(--text-primary);
            font-size: 1.05rem;
            font-weight: 850;
        }

        .report-content-description,
        .report-download-description {
            margin-top: 0.18rem;

            color: var(--text-secondary);
            font-size: 0.88rem;
            font-weight: 500;
            line-height: 1.55;
        }

        .management-activity-card {
            padding-top: 0.15rem;
        }

        .management-activity-best {
            border-top: 4px solid #178553;
        }

        .management-activity-worst {
            border-top: 4px solid #C62828;
        }

        .management-activity-eyebrow {
            margin-bottom: 0.3rem;

            color: var(--text-muted);
            font-size: 0.74rem;
            font-weight: 850;
            letter-spacing: 0.09em;
        }

        .management-activity-title {
            color: var(--text-primary);
            font-size: 1.05rem;
            font-weight: 850;
        }

        .management-activity-product {
            margin-top: 0.45rem;

            color: var(--text-primary);
            font-size: 1.15rem;
            font-weight: 800;
        }

        .management-activity-id {
            margin-top: 0.2rem;
            margin-bottom: 0.8rem;

            color: var(--text-secondary);
            font-size: 0.86rem;
            font-weight: 500;
        }


        /* ==================================================
           AI 策略顧問
        ================================================== */

        .advisor-panel-heading,
        .advisor-chat-heading {
            display: flex;
            align-items: flex-start;
            gap: 0.85rem;
            margin-bottom: 1rem;
        }

        .advisor-panel-icon,
        .advisor-chat-icon {
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

        .advisor-panel-title,
        .advisor-chat-title {
            color: var(--text-primary);
            font-size: 1.05rem;
            font-weight: 850;
        }

        .advisor-panel-description,
        .advisor-chat-description {
            margin-top: 0.18rem;

            color: var(--text-secondary);
            font-size: 0.88rem;
            font-weight: 500;
            line-height: 1.55;
        }

        .advisor-shortcut-note {
            margin-bottom: 0.8rem;
            padding: 0.8rem 0.9rem;

            background: #FFF6EF;
            border: 1px solid var(--brand-orange-border);
            border-radius: 10px;

            color: var(--text-secondary);
            font-size: 0.86rem;
            font-weight: 500;
            line-height: 1.6;
        }

        [data-testid="stChatMessage"] {
            padding: 0.85rem 1rem;
        }

        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
            color: #344054 !important;
        }

        [data-testid="stChatInput"] {
            background: var(--surface);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }

        @media (max-width: 900px) {
            .report-content-heading,
            .report-download-ready,
            .advisor-panel-heading,
            .advisor-chat-heading {
                gap: 0.7rem;
            }

            .report-content-icon,
            .report-download-icon,
            .advisor-panel-icon,
            .advisor-chat-icon {
                width: 40px;
                height: 40px;
                flex-basis: 40px;
            }
        }


        /* ==================================================
           Multiselect 最終可讀性修正
        ================================================== */

        /*
        Streamlit 不同版本可能把 data-baseweb="tag"
        放在 div、span 或其他元素上，因此不要限定 div。
        */

        [data-baseweb="tag"] {
            min-height: 30px !important;
            margin: 2px 2px !important;
            padding: 2px 7px !important;

            background: #EAF2FF !important;
            border: 1px solid #AFC8F5 !important;
            border-radius: 8px !important;

            box-shadow: none !important;
        }

        [data-baseweb="tag"],
        [data-baseweb="tag"] *,
        [data-baseweb="tag"] span,
        [data-baseweb="tag"] p,
        [data-baseweb="tag"] div {
            color: #123A70 !important;
            font-weight: 750 !important;
            line-height: 1.25 !important;
            opacity: 1 !important;
        }

        [data-baseweb="tag"] svg,
        [data-baseweb="tag"] button,
        [data-baseweb="tag"] button *,
        [data-baseweb="tag"] [role="button"],
        [data-baseweb="tag"] [role="button"] * {
            color: #123A70 !important;
            fill: #123A70 !important;
            opacity: 1 !important;
        }

        [data-baseweb="tag"]:hover {
            background: #DCEAFF !important;
            border-color: #7CA6E8 !important;
        }

        /* 確保多選框內容不會垂直擠在一起 */
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
            min-height: 48px !important;
            padding-top: 5px !important;
            padding-bottom: 5px !important;
        }

        [data-testid="stMultiSelect"] [data-baseweb="select"] > div > div {
            align-items: center !important;
            row-gap: 4px !important;
            column-gap: 4px !important;
        }

        /* 欄位文字與 placeholder */
        [data-testid="stMultiSelect"] input,
        [data-testid="stSelectbox"] input {
            color: #111827 !important;
            font-weight: 600 !important;
        }

        [data-testid="stMultiSelect"] input::placeholder,
        [data-testid="stSelectbox"] input::placeholder {
            color: #667085 !important;
            opacity: 1 !important;
        }

        /* ==================================================
           參考網站原始比例覆蓋
        ================================================== */

        :root {
            --reference-bg: #F7F8FA;
            --reference-panel: #FFFFFF;
            --reference-panel-raised: #F3F4F7;
            --reference-border: #E3E6EC;
            --reference-border-soft: #EEF0F4;
            --reference-text: #0E1015;
            --reference-text-secondary: #5B6472;
            --reference-text-faint: #8A93A3;
            --reference-orange: #F06020;
            --reference-orange-soft: rgba(240, 96, 32, 0.09);
            --reference-orange-line: rgba(240, 96, 32, 0.35);
            --reference-orange-deep: #C24500;
            --reference-sidebar-bg: #FFF8F3;
            --reference-sidebar-raised: #FFE9DA;
            --reference-sidebar-line: #F0DED0;
            --reference-shadow:
                0 1px 2px rgba(16, 24, 40, 0.04),
                0 1px 3px rgba(16, 24, 40, 0.04);
        }

        html {
            font-size: 14.5px !important;
        }

        body,
        .stApp {
            background: var(--reference-bg) !important;
            color: var(--reference-text) !important;

            font-family:
                "Noto Sans TC",
                "Segoe UI",
                "Microsoft JhengHei",
                sans-serif !important;

            line-height: 1.5 !important;
        }


        /* ==================================================
           側邊欄：完全採用參考網站原始尺寸
        ================================================== */

        section[data-testid="stSidebar"],
        [data-testid="stSidebar"] {
            width: 252px !important;
            min-width: 252px !important;
            max-width: 252px !important;
            flex: 0 0 252px !important;

            background:
                linear-gradient(
                    180deg,
                    var(--reference-sidebar-bg) 0%,
                    #FFFFFF 100%
                ) !important;

            border-right:
                1px solid
                var(--reference-border) !important;

            box-shadow:
                2px 0 16px
                rgba(16, 24, 40, 0.05) !important;
        }

        section[data-testid="stSidebar"]::before,
        [data-testid="stSidebar"]::before {
            height: 4px !important;
        }

        section[data-testid="stSidebar"][aria-expanded="false"] {
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            flex-basis: 0 !important;
        }

        /*
        原生 Header 只保留收合按鈕，不佔據品牌空間。
        */

        [data-testid="stSidebarHeader"] {
            min-height: 0 !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: 0 !important;
            background: transparent !important;
        }

        [data-testid="stSidebarCollapseButton"] {
            position: absolute !important;
            top: 8px !important;
            right: 8px !important;
            z-index: 100 !important;
        }

        /*
        側邊欄內容上方讓出 82px 品牌區。
        82px = 38px Logo + 上下各 22px padding。
        */

        [data-testid="stSidebarContent"] {
            position: relative !important;

            width: 252px !important;
            min-width: 252px !important;
            max-width: 252px !important;

            padding:
                86px
                10px
                0 !important;
        }

        /*
        品牌區使用真實圖片＋瀏覽器文字，
        不使用 PNG 文字、SVG 文字或偽元素文字。
        */

        .st-key-reference_brand_header {
            position: absolute !important;
            top: 4px !important;
            left: 0 !important;
            right: 0 !important;
            z-index: 50 !important;

            height: 82px !important;
            min-height: 82px !important;

            padding:
                22px
                18px !important;

            overflow: hidden !important;

            background:
                var(--reference-orange-soft) !important;

            border-bottom:
                1px solid
                var(--reference-sidebar-line) !important;
        }

        .st-key-reference_brand_header
        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        .reference-brand-wrap {
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;
            width: 100% !important;
        }

        .reference-brand-logo {
            display: block !important;

            width: 38px !important;
            height: 38px !important;
            min-width: 38px !important;
            max-width: 38px !important;
            flex: 0 0 38px !important;

            object-fit: contain !important;
        }

        .reference-brand-copy {
            min-width: 0 !important;
            flex: 1 1 auto !important;
        }

        .reference-brand-name {
            color: #241608 !important;

            font-size: 18px !important;
            font-weight: 800 !important;
            line-height: 1.3 !important;
            letter-spacing: 0.01em !important;
            white-space: normal !important;
            overflow-wrap: normal !important;
        }

        .reference-brand-x {
            margin: 0 3px !important;
            color: var(--reference-orange) !important;
            font-weight: 700 !important;
        }

        .reference-brand-sub {
            margin-top: 2px !important;

            color: #8A6A4E !important;
            font-size: 11.5px !important;
            font-weight: 400 !important;
            line-height: 1.5 !important;
            letter-spacing: 0.02em !important;
            white-space: nowrap !important;
        }


        /* ==================================================
           原生導覽：完全採用參考網站原始尺寸
        ================================================== */

        [data-testid="stSidebarNav"] {
            display: block !important;
            padding:
                14px
                0 !important;
        }

        [data-testid="stSidebarNav"]
        [data-testid="stNavSectionHeader"] {
            margin: 0 !important;

            padding:
                12px
                12px
                4px !important;

            color:
                var(--reference-text-faint) !important;

            font-size: 11px !important;
            font-weight: 700 !important;
            line-height: 1.5 !important;
            letter-spacing: 0.04em !important;
        }

        [data-testid="stSidebarNav"]
        [data-testid="stNavSectionHeader"]
        svg {
            display: none !important;
        }

        [data-testid="stSidebarNav"] a {
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;

            width: 100% !important;
            min-height: 40px !important;

            margin: 0 0 4px !important;
            padding:
                11px
                12px !important;

            border: 0 !important;
            border-radius: 10px !important;

            color:
                var(--reference-text-secondary) !important;

            background: transparent !important;

            font-size: 13px !important;
            font-weight: 500 !important;
            line-height: 1.35 !important;

            box-shadow: none !important;
            transform: none !important;
        }

        [data-testid="stSidebarNav"] a svg {
            width: 18px !important;
            height: 18px !important;
            flex: 0 0 18px !important;
        }

        [data-testid="stSidebarNav"] a:hover {
            color:
                var(--reference-orange-deep) !important;

            background:
                var(--reference-sidebar-raised) !important;

            transform: none !important;
        }

        [data-testid="stSidebarNav"]
        a[aria-current="page"] {
            color: #FFFFFF !important;

            background:
                var(--reference-orange) !important;

            font-weight: 700 !important;

            box-shadow:
                0 3px 10px
                var(--reference-orange-line) !important;
        }

        [data-testid="stSidebarNav"]
        a[aria-current="page"] *,
        [data-testid="stSidebarNav"]
        a[aria-current="page"] svg {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }


        /* ==================================================
           主內容：採用參考網站原始尺寸
        ================================================== */

        [data-testid="stMain"],
        .stMain {
            background:
                radial-gradient(
                    circle at 100% 0%,
                    rgba(240, 96, 32, 0.05),
                    transparent 32%
                ),
                radial-gradient(
                    circle at 0% 100%,
                    rgba(80, 80, 160, 0.05),
                    transparent 38%
                ),
                var(--reference-bg) !important;
        }

        .block-container,
        [data-testid="stMainBlockContainer"] {
            width: auto !important;
            max-width: 100% !important;

            padding:
                32px
                36px !important;
        }


        /* ==================================================
           取消整頁橫向滑動
           寬表格屬於 Flexbox 版面下的子元素，
           預設 min-width: auto 會讓外層容器
           被撐寬到內容的最小寬度，導致整個頁面
           出現橫向捲軸。這裡讓各層容器都能正常
           縮小到可視寬度，改由表格自己內部捲動。
        ================================================== */

        html,
        body,
        [data-testid="stAppViewContainer"],
        .stApp {
            overflow-x: hidden !important;
        }

        [data-testid="stMain"],
        .stMain,
        .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stHorizontalBlock"],
        [data-testid="stColumn"],
        [data-testid="stElementContainer"] {
            min-width: 0 !important;
        }

        [data-testid="stDataFrame"] {
            max-width: 100% !important;
        }


        /* ==================================================
           頁面標題
        ================================================== */

        .step-label {
            margin-bottom: 4px !important;

            color:
                var(--reference-orange) !important;

            font-size: 11px !important;
            font-weight: 600 !important;
            line-height: 1.5 !important;
            letter-spacing: 0.08em !important;
        }

        .product-page-title {
            gap: 10px !important;
            margin: 0 0 6px !important;
        }

        .product-page-title h1,
        h1 {
            margin: 0 0 6px !important;

            color:
                var(--reference-text) !important;

            font-size: 22px !important;
            font-weight: 800 !important;
            line-height: 1.35 !important;
            letter-spacing: -0.01em !important;
        }

        .product-page-title h3 {
            margin: 0 !important;
        }

        .product-page-title-bar {
            width: 5px !important;
            height: 20px !important;
            flex: 0 0 5px !important;

            border-radius: 3px !important;
        }

        .product-page-description {
            max-width: none !important;

            margin:
                6px
                0
                16px !important;

            color:
                var(--reference-text-secondary) !important;

            font-size: 12.3px !important;
            font-weight: 400 !important;
            line-height: 1.65 !important;
        }

        h2 {
            margin:
                0
                0
                16px !important;

            padding-left: 0 !important;

            color:
                var(--reference-text) !important;

            font-size: 22px !important;
            font-weight: 800 !important;
            line-height: 1.35 !important;
            letter-spacing: -0.01em !important;
        }

        h2::before {
            display: none !important;
        }

        h3 {
            color:
                var(--reference-text) !important;

            font-size: 16px !important;
            font-weight: 700 !important;
        }


        /* ==================================================
           一般文字
        ================================================== */

        p,
        li,
        label,
        [data-testid="stWidgetLabel"],
        [data-testid="stCaptionContainer"],
        .stMarkdown p,
        .stMarkdown li {
            color:
                var(--reference-text-secondary) !important;

            font-size: 13px !important;
            font-weight: 400 !important;
            line-height: 1.5 !important;
        }


        /* ==================================================
           卡片與 KPI
        ================================================== */

        [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0 !important;

            background:
                var(--reference-panel) !important;

            border:
                1px solid
                var(--reference-border) !important;

            border-radius: 12px !important;

            box-shadow:
                var(--reference-shadow) !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] > div {
            border-radius: 12px !important;
        }

        [data-testid="stMetric"] {
            min-height: 92px !important;
            height: 100% !important;

            padding:
                18px
                20px !important;

            background:
                var(--reference-panel) !important;

            border:
                1px solid
                var(--reference-border) !important;

            border-radius: 12px !important;

            box-shadow:
                var(--reference-shadow) !important;

            transform: none !important;
        }

        [data-testid="stMetric"]:hover {
            transform: none !important;
            border-color:
                var(--reference-border) !important;
            box-shadow:
                var(--reference-shadow) !important;
        }

        [data-testid="stMetricLabel"] {
            color:
                var(--reference-text-secondary) !important;

            font-size: 13px !important;
            font-weight: 500 !important;
        }

        [data-testid="stMetricValue"] {
            color:
                var(--reference-text) !important;

            font-size: 25px !important;
            font-weight: 600 !important;
            line-height: 1.2 !important;
        }


        /* ==================================================
           頁面自訂卡片同步縮放
        ================================================== */

        .next-step-panel {
            padding: 16px !important;
            border-radius: 12px !important;
        }

        .next-step-eyebrow,
        .workflow-step-number,
        .output-card-label {
            font-size: 11px !important;
        }

        .next-step-title,
        .workflow-step-title,
        .status-card-title,
        .analysis-action-title,
        .progress-card-title {
            font-size: 16px !important;
            line-height: 1.4 !important;
        }

        .next-step-description,
        .next-step-location,
        .workflow-step-subtitle,
        .status-card-subtitle,
        .analysis-action-description {
            font-size: 12px !important;
            line-height: 1.6 !important;
        }

        .workflow-step-icon,
        .status-card-icon,
        .analysis-action-icon {
            width: 36px !important;
            height: 36px !important;
            flex: 0 0 36px !important;
        }


        /* ==================================================
           表單元件
        ================================================== */

        div[data-baseweb="select"] > div,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            min-height: 38px !important;

            border-radius: 9px !important;

            background:
                var(--reference-panel-raised) !important;

            border:
                1px solid
                var(--reference-border) !important;

            font-size: 13px !important;
        }


        /* ==================================================
           手機版
        ================================================== */

        @media (max-width: 900px) {
            section[data-testid="stSidebar"],
            [data-testid="stSidebar"] {
                width: min(86vw, 252px) !important;
                min-width: min(86vw, 252px) !important;
                max-width: min(86vw, 252px) !important;
            }

            [data-testid="stSidebarContent"] {
                width: min(86vw, 252px) !important;
                min-width: min(86vw, 252px) !important;
                max-width: min(86vw, 252px) !important;
            }

            .block-container,
            [data-testid="stMainBlockContainer"] {
                padding:
                    20px
                    18px !important;
            }
        }


        /* ==================================================
           品牌區裁切修正
           只調整左上品牌區，不改主畫面與側邊欄比例
        ================================================== */

        /*
        原本品牌容器只有 82px，但品牌名稱會自然換成兩行，
        再加上副標後高度不足，因此最上方或最下方會被裁切。
        */

        [data-testid="stSidebarContent"] {
            padding-top: 122px !important;
        }

        .st-key-reference_brand_header {
            top: 4px !important;

            height: 116px !important;
            min-height: 116px !important;

            padding:
                18px
                14px
                16px !important;

            box-sizing: border-box !important;
            overflow: visible !important;
        }

        .reference-brand-wrap {
            min-height: 80px !important;
            align-items: center !important;
            gap: 12px !important;
        }

        .reference-brand-logo {
            width: 42px !important;
            height: 42px !important;
            min-width: 42px !important;
            max-width: 42px !important;
            flex-basis: 42px !important;
        }

        .reference-brand-copy {
            min-width: 0 !important;
            overflow: visible !important;
        }

        .reference-brand-name {
            margin: 0 !important;

            font-size: 18px !important;
            line-height: 1.28 !important;

            white-space: normal !important;
            overflow: visible !important;
        }

        .reference-brand-sub {
            margin-top: 4px !important;

            font-size: 11.5px !important;
            line-height: 1.35 !important;

            white-space: normal !important;
            overflow: visible !important;
        }

        @media (max-width: 900px) {
            [data-testid="stSidebarContent"] {
                padding-top: 118px !important;
            }

            .st-key-reference_brand_header {
                height: 112px !important;
                min-height: 112px !important;
                padding:
                    17px
                    13px
                    15px !important;
            }
        }


        /* ==================================================
           AI 顧問結構化回覆卡片
        ================================================== */

        .badge {
            display: inline-flex;
            align-items: center;

            padding: 0.2rem 0.6rem;
            border-radius: 999px;

            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.02em;
            white-space: nowrap;
        }

        .badge-confidence-high {
            background: #E8F7EF;
            color: #137A48;
            border: 1px solid rgba(19, 122, 72, 0.3);
        }

        .badge-confidence-mid {
            background: #FFF4E5;
            color: #A65300;
            border: 1px solid rgba(166, 83, 0, 0.3);
        }

        .badge-confidence-low {
            background: #FDEDED;
            color: #B45309;
            border: 1px solid rgba(180, 83, 9, 0.3);
        }

        .badge-neutral {
            background: #EEF1F5;
            color: #526076;
            border: 1px solid rgba(82, 96, 118, 0.25);
        }

        /* ==================================================
           情境模擬・方案卡片
        ================================================== */

        .scenario-card {
            padding: 0.9rem 1rem;

            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 13px;

            box-shadow: var(--shadow-sm);
        }

        .scenario-card-best {
            border-color: var(--success);

            box-shadow:
                0 0 0 2px rgba(21, 128, 61, 0.15),
                var(--shadow-sm);
        }

        .scenario-card-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.7rem;
        }

        .scenario-card-title {
            font-size: 0.92rem;
            font-weight: 800;
            color: var(--text-primary);
        }

        .scenario-row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 0.6rem;

            padding: 0.32rem 0;
            border-bottom: 1px dashed var(--border-soft);

            font-size: 0.86rem;
        }

        .scenario-row:last-child {
            border-bottom: none;
        }

        .scenario-row-label {
            color: var(--text-secondary);
            font-weight: 500;
        }

        .scenario-row-value {
            color: var(--text-primary);
            font-weight: 750;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }

        .advisor-card {
            padding: 1rem 1.2rem;
            margin: 0.4rem 0 0.2rem;

            background:
                linear-gradient(
                    135deg,
                    var(--ai-accent-soft) 0%,
                    #FFFFFF 55%
                );

            border: 1px solid var(--ai-accent-border);
            border-radius: 13px;

            box-shadow: var(--shadow-sm);
        }

        .advisor-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.65rem;
        }

        .advisor-tag,
        .advisor-tag-fallback {
            display: inline-flex;
            align-items: center;

            padding: 0.2rem 0.6rem;
            border-radius: 999px;

            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.02em;
        }

        .advisor-tag {
            background: var(--ai-accent);
            color: #FFFFFF;
        }

        .advisor-tag-fallback {
            background: #E7EBF0;
            color: #45526B;
            border: 1px dashed #B7C0CE;
        }

        .advisor-row {
            display: flex;
            gap: 0.55rem;
            align-items: baseline;
            margin-bottom: 0.45rem;
        }

        .advisor-row:last-child {
            margin-bottom: 0;
        }

        .advisor-row-label {
            flex: 0 0 auto;
            min-width: 4.4rem;

            color: var(--ai-accent-deep);
            font-size: 0.78rem;
            font-weight: 850;
        }

        .advisor-row-text {
            color: var(--text-secondary);
            font-size: 0.88rem;
            font-weight: 550;
            line-height: 1.6;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )