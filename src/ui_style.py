import streamlit as st


def apply_product_styles(dark_mode: bool = False) -> None:
    """
    套用產品版共用視覺樣式。

    僅調整外觀，不修改任何資料處理、分析或 Session State 邏輯。
    dark_mode=True 時，會在既有（亮色）樣式後方再疊加一份深色
    模式覆寫樣式（只新增規則、不修改既有規則），對應側邊欄／
    首頁的亮／暗模式切換鈕。因為 CSS 自訂變數可以重複宣告、
    後宣告者覆蓋前者，深色覆寫只要重新宣告 :root 的顏色變數，
    絕大部分沿用變數的既有規則就會自動換色；只有少數直接寫死
    色碼（例如白色漸層終點、徽章底色）的規則需要額外針對同一個
    選擇器補一條深色版本。
    """

    base_style = """
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
           KPI 卡片（彩色圓形 icon 徽章版，取代部分頁面的
           st.metric()，配色沿用既有品牌變數，亮／暗模式自動換色）
        ================================================== */

        .kpi-card {
            position: relative;
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

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: var(--brand-orange-border);
            box-shadow: var(--shadow-md);
        }

        .kpi-card-icon {
            position: absolute;
            top: 0.95rem;
            right: 0.95rem;

            display: flex;
            align-items: center;
            justify-content: center;

            width: 2.15rem;
            height: 2.15rem;
            border-radius: 50%;

            background: transparent;
            border: 1.5px solid;

            font-size: 1.05rem;
        }

        .kpi-card-icon--blue {
            border-color: var(--brand-blue);
            color: var(--brand-blue);
        }

        .kpi-card-icon--green {
            border-color: var(--brand-green);
            color: var(--brand-green);
        }

        .kpi-card-icon--orange {
            border-color: var(--brand-orange);
            color: var(--brand-orange);
        }

        .kpi-card-icon--red {
            border-color: var(--danger);
            color: var(--danger);
        }

        .kpi-card-label {
            padding-right: 2.6rem;

            color: var(--text-secondary);
            font-size: 1.04rem;
            font-weight: 650;
        }

        .kpi-card-value {
            margin-top: 0.35rem;

            color: var(--text-primary);
            font-size: 1.2rem;
            font-weight: 850;
            line-height: 1.3;
        }

        .kpi-card-value--lg {
            font-size: 1.5rem;
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

        /*
        原生頂部工具列（stHeader）預設是不透明淺色，之前完全
        沒有樣式碰過，在深色模式或深色 hero 版面上方會露出一條
        突兀的白條。改成透明，讓底下當下主題的頁面背景透出來，
        亮／暗模式都適用，不需要另外在深色覆寫區塊重複一份。
        */
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        /* 原生「Deploy」按鈕，這是本機/內部工具不需要的功能 */
        [data-testid="stAppDeployButton"] {
            display: none !important;
        }

        /*
        側邊欄收合／展開按鈕是 Streamlit 原生元件，本身背景其實
        是透明的：亮色模式下之所以看起來「有灰底」，只是因為
        透出來的頁面背景本來就偏亮，深色模式時透出來的是深色
        頁面背景，深色圖示疊上去就看不見。這裡不再依賴透出來的
        頁面背景，直接給按鈕一個固定的淺灰底（不隨 dark_mode
        變動），讓它在兩種模式下都跟亮色模式一樣「看起來有灰底
        可以看見」。
        */
        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stExpandSidebarButton"] {
            background: #E7EBF0 !important;
            border-radius: 8px !important;
        }

        [data-testid="stSidebarCollapseButton"] svg,
        [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
        [data-testid="stSidebarCollapseButton"] *,
        [data-testid="stExpandSidebarButton"] svg,
        [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
        [data-testid="stExpandSidebarButton"] * {
            color: #344054 !important;
            fill: #344054 !important;
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

            /* 保險措施：就算樣式不是一次性插入，寬度變化也不會
               有動畫過渡，不會被使用者看到「彈出又收回」的過程 */
            transition: none !important;

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

        /*
        找到真正的根因了：這條規則把收合狀態的側邊欄寬度歸零，
        但從來沒有搭配 overflow:hidden。子元素（品牌文字、導覽
        圖示、收合鈕本身）原本的寬度不會因為外層變 0 就自動消失，
        沒有 overflow:hidden 的話會直接溢出到寬度 0 的容器外面，
        變成畫面上看到的「破損窄條、文字被裁一半、兩顆按鈕疊在
        一起」。這是原本程式碼裡就存在的規則（這次對話開始前就
        有），只是先前測試都停留在首頁自訂的 96px 收合列，一直
        沒有人實際點原生收合鈕觸發到這條規則，才沒被發現。
        */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            flex-basis: 0 !important;
            overflow: hidden !important;
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

        /*
        上一版用 aria-expanded 條件式定位造成側邊欄本身版面
        跑掉（收合時整個側邊欄卡在一個破損的窄條狀態，且不會
        自己恢復），已還原成單一固定定位，不再依展開/收合狀態
        切換 CSS 規則，避免同樣的問題再發生。按鈕在側邊欄外側
        的精確定位之後再處理。
        */
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

        /*
        :material/xxx: 圖示實際上是連字型渲染的
        <span data-testid="stIconMaterial">，不是 <svg>，
        圖示大小要用 font-size 控制。字型是 Google 的
        Material Symbols Rounded 可變字型，預設沒有指定
        FILL 軸，瀏覽器會落在字型原始預設值（偏向實心），
        這裡明確指定 FILL 0，改成只有外框線條、內部不填滿色。
        */
        [data-testid="stSidebarNav"] a [data-testid="stIconMaterial"] {
            font-size: 21px !important;
            width: 21px !important;
            height: 21px !important;
            line-height: 1 !important;
            text-align: center !important;

            font-variation-settings:
                "FILL" 0,
                "wght" 400,
                "GRAD" 0,
                "opsz" 24 !important;
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

            font-size: 33px !important;
            font-weight: 800 !important;
            line-height: 1.35 !important;
            letter-spacing: -0.01em !important;
        }

        .product-page-title h3 {
            margin: 0 !important;
            font-size: 19px !important;
            line-height: 1 !important;
        }

        .product-page-title-bar {
            width: 8px !important;
            height: 30px !important;
            flex: 0 0 8px !important;

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

        h3,
        h5,
        h6 {
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

        .scenario-card-adopted {
            border-color: var(--brand-orange);

            box-shadow:
                0 0 0 2px rgba(244, 91, 27, 0.18),
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

        .scenario-card-badges {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.35rem;
        }

        .badge-adopted {
            background: var(--brand-orange);
            color: #FFFFFF;
            border: 1px solid var(--brand-orange-dark);
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
            background: var(--brand-blue);
            color: #FFFFFF;
        }

        .advisor-tag--blue {
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

            color: var(--brand-blue);
            font-size: 0.78rem;
            font-weight: 850;
        }

        .advisor-row-label--blue {
            color: var(--ai-accent-deep);
        }

        .advisor-row-text {
            color: var(--text-secondary);
            font-size: 0.88rem;
            font-weight: 550;
            line-height: 1.6;
        }


        /* ==================================================
           訊息框背景（沿用共用卡片變數，亮／暗模式皆適用）
        ================================================== */

        [data-testid="stAlert"] {
            background: var(--surface);
            border: 1px solid var(--border);
        }


        /* ==================================================
           亮／暗模式切換鈕：固定在畫面右上角
        ================================================== */

        .st-key-theme_toggle_root {
            position: fixed !important;
            top: 14px !important;
            right: 22px !important;
            left: auto !important;
            bottom: auto !important;
            width: fit-content !important;
            max-width: fit-content !important;
            z-index: 2147483647 !important;
        }

        .st-key-theme_toggle_root .stButton > button {
            min-height: 2.2rem !important;
            padding: 0.3rem 0.85rem !important;
            border-radius: 999px !important;

            background: var(--surface) !important;
            color: var(--text-secondary) !important;
            border: 1px solid var(--border) !important;

            font-size: 0.82rem !important;
            font-weight: 700 !important;

            box-shadow: var(--shadow-sm) !important;
        }

        .st-key-theme_toggle_root .stButton > button:hover {
            border-color: var(--brand-orange-border) !important;
            color: var(--brand-orange-dark) !important;
            transform: none !important;
        }

        @media (max-width: 900px) {
            .st-key-theme_toggle_root {
                top: 10px !important;
                right: 12px !important;
            }
        }

        </style>
        """

    # 亮／暗模式切換時（尤其是切成深色）觀察到側邊欄會短暫
    # 「彈出又收回」一下：原因是亮色樣式跟深色覆寫樣式分兩次
    # st.markdown() 呼叫、分兩次插入 DOM，瀏覽器可能先畫出
    # 亮色版側邊欄寬度，深色覆寫才接著套用，中間那一瞬間就是
    # 使用者看到的閃爍。改成組成同一個字串、一次性插入，讓
    # 瀏覽器一次拿到最終樣式，不會有中間態可以畫出來。
    combined_style = (
        base_style + _DARK_OVERRIDE_STYLE
        if dark_mode
        else base_style
    )

    st.markdown(combined_style, unsafe_allow_html=True)


def render_theme_toggle() -> None:
    """
    在畫面右上角顯示固定位置的亮／暗模式切換鈕。

    切換鈕本身的樣式已隨 apply_product_styles() 一起注入
    （.st-key-theme_toggle_root），這裡只負責渲染按鈕與寫回
    Session State；實際的顏色變換交由 apply_product_styles()
    的 dark_mode 參數處理。
    """

    dark_mode = bool(st.session_state.get("dark_mode", False))

    with st.container(key="theme_toggle_root"):
        toggle_label = "☀️ 亮色模式" if dark_mode else "🌙 深色模式"

        if st.button(toggle_label, key="theme_toggle_button"):
            st.session_state["dark_mode"] = not dark_mode
            st.rerun()


# =========================================================
# 側邊欄：icon-only 精簡模式
#
# 跟首頁（0_首頁.py）收合列用的是同一套視覺（寬度 96px、
# 只顯示圖示、隱藏文字標籤），這裡另外提供一份給「其他頁面」
# 依使用者切換自由套用，形成兩級收合：
# 1. 「精簡為 icon」（這裡）：仍是完整的 Streamlit 導覽，
#    只是視覺上縮成 icon 列，隨時可以點連結切頁。
# 2. 原生「收合」按鈕：側邊欄寬度直接歸零、整個隱藏。
# 首頁本身的收合列已經有自己獨立的樣板檔案（一直運作穩定，
# 這裡不去動它），這份是特地給「其他頁面」用的等效版本。
# =========================================================

_SIDEBAR_ICON_ONLY_STYLE = """
<style>
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
    width: 96px !important;
    min-width: 96px !important;
    max-width: 96px !important;
    flex: 0 0 96px !important;
}

[data-testid="stSidebarContent"] {
    width: 96px !important;
    min-width: 96px !important;
    max-width: 96px !important;
}

.reference-brand-copy {
    display: none !important;
}

.reference-brand-wrap {
    justify-content: center !important;
}

[data-testid="stSidebarNav"] a {
    display: flex !important;
    justify-content: flex-start !important;
    align-items: center !important;
    gap: 0 !important;
}

[data-testid="stSidebarNav"] a p {
    display: none !important;
}

[data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"] {
    display: none !important;
}
</style>
"""


def apply_sidebar_icon_only_style() -> None:
    """套用側邊欄「只顯示 icon」精簡樣式（給首頁以外的頁面用）。"""

    st.markdown(_SIDEBAR_ICON_ONLY_STYLE, unsafe_allow_html=True)


def render_sidebar_icon_only_toggle() -> None:
    """側邊欄「精簡為 icon」／「顯示完整選單」切換鈕。"""

    icon_only = bool(st.session_state.get("sidebar_icon_only", False))

    # icon-only 模式下側邊欄只有 96px 寬，按鈕文字要夠短才不會
    # 擠壓變形，完整說明改放到 help 提示文字裡。
    toggle_label = "展開" if icon_only else "精簡"

    if st.button(
        toggle_label,
        key="sidebar_icon_only_toggle",
        use_container_width=True,
        help=(
            "顯示完整選單（含文字標籤）"
            if icon_only
            else "精簡側邊欄為只顯示 icon"
        ),
    ):
        st.session_state["sidebar_icon_only"] = not icon_only
        st.rerun()


# =========================================================
# 深色模式覆寫樣式
#
# 只新增規則、不修改亮色版任何一行：
# 1. 重新宣告 :root 的顏色變數（兩組：品牌變數＋參考網站
#    變數），沿用變數的規則會自動換色。
# 2. 針對少數直接寫死色碼、沒有走變數的規則（白色漸層終點、
#    上傳框、停用按鈕、徽章、標籤晶片……等），逐一補上深色
#    版本，選擇器與亮色版完全一致，靠後宣告 + !important
#    取得優先權。
# =========================================================

_DARK_OVERRIDE_STYLE = """
<style>
:root {
    --app-bg: #0A0F1E;
    --surface: #131A2C;
    --surface-soft: #1B2338;
    --surface-warm: #1F2A3D;

    --text-primary: #EDF1F7;
    --text-secondary: #AEB9CC;
    --text-muted: #8590A6;

    --border: #2A3448;
    --border-soft: #232C3E;

    --brand-orange: #FF7A3D;
    --brand-orange-dark: #FFAB7A;
    --brand-orange-soft: rgba(255, 122, 61, 0.26);
    --brand-orange-border: rgba(255, 122, 61, 0.5);

    --brand-magenta: #E8629E;
    --brand-blue: #8891E0;
    --brand-green: #35D0A0;

    --success: #34D399;
    --warning: #FBBF24;
    --danger: #F87171;

    --ai-accent: #7FC4FF;
    --ai-accent-deep: #B8E0FF;
    --ai-accent-soft: rgba(127, 196, 255, 0.24);
    --ai-accent-border: rgba(127, 196, 255, 0.42);

    --shadow-sm:
        0 1px 2px rgba(0, 0, 0, 0.4),
        0 3px 10px rgba(0, 0, 0, 0.35);

    --shadow-md:
        0 10px 26px rgba(0, 0, 0, 0.5);

    --reference-bg: #0A0F1E;
    --reference-panel: #131A2C;
    --reference-panel-raised: #1B2338;
    --reference-border: #2A3448;
    --reference-border-soft: #232C3E;
    --reference-text: #EDF1F7;
    --reference-text-secondary: #AEB9CC;
    --reference-text-faint: #7C87A0;
    --reference-orange: #FF7A3D;
    --reference-orange-soft: rgba(255, 122, 61, 0.26);
    --reference-orange-line: rgba(255, 122, 61, 0.45);
    --reference-orange-deep: #FFC29E;
    --reference-sidebar-bg: #0E1526;
    --reference-sidebar-raised: #1E2A46;
    --reference-sidebar-line: #2B3855;
    --reference-shadow:
        0 1px 2px rgba(0, 0, 0, 0.35),
        0 1px 4px rgba(0, 0, 0, 0.3);
}

/* 側邊欄漸層終點原本寫死白色 */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            var(--reference-sidebar-bg) 0%,
            #0A0F1E 100%
        ) !important;

    box-shadow:
        2px 0 16px rgba(0, 0, 0, 0.4) !important;
}

.reference-brand-name {
    color: #F5EDE4 !important;
}

.reference-brand-sub {
    color: #C9B7A4 !important;
}

/* 上傳框 */
[data-testid="stFileUploaderDropzone"] {
    background: #1B2338 !important;
    border-color: #34405A !important;
}

[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] span {
    color: #AEB9CC !important;
}

/* 停用按鈕 */
.stButton > button:disabled {
    background: #1B2338 !important;
    color: #667085 !important;
    border-color: #2A3448 !important;
}

/* 聊天訊息文字（比對話泡泡更高特異性的既有規則寫死了顏色） */
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
    color: #EDF1F7 !important;
}

/*
訊息框（st.info/warning/success/error）文字：亮色版寫死
#344054（深灰藍），背景已經改用 var(--surface) 跟著變深，
文字沒有對應深色覆寫的話，就會在深色背景上出現幾乎看不清的
深色文字，這裡補上淺色文字。
*/
[data-testid="stAlert"] p,
[data-testid="stAlert"] li,
[data-testid="stAlert"] span {
    color: #EDF1F7 !important;
}

/* 分頁標籤文字（st.tabs()）同樣沒有深色覆寫，寫死的中灰色
   在深色背景上會很難辨識 */
[data-baseweb="tab"] {
    color: #AEB9CC !important;
}

/* 多選標籤晶片 */
[data-baseweb="tag"] {
    background: rgba(127, 196, 255, 0.26) !important;
    border: 1px solid rgba(127, 196, 255, 0.4) !important;
}

[data-baseweb="tag"],
[data-baseweb="tag"] *,
[data-baseweb="tag"] span,
[data-baseweb="tag"] p,
[data-baseweb="tag"] div {
    color: #D7EBFF !important;
}

[data-baseweb="tag"] svg,
[data-baseweb="tag"] button,
[data-baseweb="tag"] button *,
[data-baseweb="tag"] [role="button"],
[data-baseweb="tag"] [role="button"] * {
    color: #D7EBFF !important;
    fill: #D7EBFF !important;
}

[data-baseweb="tag"]:hover {
    background: rgba(127, 196, 255, 0.26) !important;
    border-color: rgba(127, 196, 255, 0.6) !important;
}

[data-testid="stMultiSelect"] input,
[data-testid="stSelectbox"] input {
    color: #EDF1F7 !important;
}

[data-testid="stMultiSelect"] input::placeholder,
[data-testid="stSelectbox"] input::placeholder {
    color: #8590A6 !important;
}

/* 主管報表：最佳／較差活動色條 */
.management-activity-best {
    border-top-color: #34D399 !important;
}

.management-activity-worst {
    border-top-color: #F87171 !important;
}

/* 流程徽章 */
.workflow-badge-completed {
    background: rgba(52, 211, 153, 0.26) !important;
    color: #6EE7B7 !important;
    border-color: rgba(52, 211, 153, 0.35) !important;
}

.workflow-badge-pending {
    background: rgba(251, 191, 36, 0.26) !important;
    color: #FCD34D !important;
    border-color: rgba(251, 191, 36, 0.35) !important;
}

/* 下一步提示卡漸層終點原本寫死白色 */
.next-step-panel {
    background:
        linear-gradient(
            135deg,
            rgba(255, 122, 61, 0.2) 0%,
            var(--surface) 100%
        ) !important;
}

/* AI 策略顧問捷徑提示 */
.advisor-shortcut-note {
    background: rgba(255, 122, 61, 0.2) !important;
}

[data-testid="stChatMessage"] {
    background: var(--surface) !important;
}

/* AI 洞察卡漸層終點原本寫死白色 */
.advisor-card {
    background:
        linear-gradient(
            135deg,
            var(--ai-accent-soft) 0%,
            var(--surface) 55%
        ) !important;
}

.advisor-tag-fallback {
    background: rgba(231, 235, 240, 0.24) !important;
    color: #C3CBDA !important;
    border-color: rgba(183, 192, 206, 0.4) !important;
}

/* 信心／情境徽章 */
.badge-confidence-high {
    background: rgba(52, 211, 153, 0.26) !important;
    color: #6EE7B7 !important;
    border-color: rgba(52, 211, 153, 0.4) !important;
}

.badge-confidence-mid {
    background: rgba(251, 191, 36, 0.26) !important;
    color: #FCD34D !important;
    border-color: rgba(251, 191, 36, 0.4) !important;
}

.badge-confidence-low {
    background: rgba(248, 113, 113, 0.26) !important;
    color: #FCA5A5 !important;
    border-color: rgba(248, 113, 113, 0.4) !important;
}

.badge-neutral {
    background: rgba(174, 185, 204, 0.26) !important;
    color: #C7D0E0 !important;
    border-color: rgba(174, 185, 204, 0.35) !important;
}
</style>
"""