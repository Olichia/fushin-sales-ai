from pathlib import Path
import html
import sys

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.session_helpers import initialize_session_state
from src.analysis_pipeline import (
    AnalysisSettings,
    analyze_activity_performance,
    coerce_arrow_strings_to_object,
    generate_strategy_report,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.markdown(
    """
    <div class="step-label">STRATEGY CENTER</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>策略中心</h1>
    </div>

    <p class="product-page-description">
        根據活動成效分析與規則式策略報告，
        整理建議延續、建議優化、建議檢討與待補資料的活動。
        策略分類屬於決策輔助，實際執行仍應搭配成本、
        毛利、庫存與商業目標判斷。
    </p>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 取得既有資料
# =========================================================

strategy_dataframe = st.session_state.get(
    "strategy_report_dataframe"
)

strategy_report_text = st.session_state.get(
    "strategy_report_text"
)

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)

standardized_dataframe = st.session_state.get(
    "standardized_dataframe"
)

integrated_dataframe = st.session_state.get(
    "integrated_sales_activity_dataframe"
)

activity_dataframe = st.session_state.get(
    "activity_standardized_dataframe"
)

# 舊版分析結果／pickle 可能保留 Pandas 3 的 PyArrow 字串欄位與欄名索引。
# 頁面一開始就全部轉成 Python object，避免任何篩選、圖表或按鈕重跑時
# 進入不穩定的 Arrow 原生 take/unique/serialization 路徑。
if strategy_dataframe is not None:
    strategy_dataframe = coerce_arrow_strings_to_object(
        strategy_dataframe
    )

if performance_dataframe is not None:
    performance_dataframe = coerce_arrow_strings_to_object(
        performance_dataframe
    )

if standardized_dataframe is not None:
    standardized_dataframe = coerce_arrow_strings_to_object(
        standardized_dataframe
    )

if integrated_dataframe is not None:
    integrated_dataframe = coerce_arrow_strings_to_object(
        integrated_dataframe
    )

if activity_dataframe is not None:
    activity_dataframe = coerce_arrow_strings_to_object(
        activity_dataframe
    )

saved_analysis_settings = st.session_state.get(
    "analysis_settings"
) or {}

default_analysis_settings = AnalysisSettings()

baseline_days = int(
    saved_analysis_settings.get(
        "baseline_days",
        default_analysis_settings.baseline_days,
    )
)
post_days = int(
    saved_analysis_settings.get(
        "post_days",
        default_analysis_settings.post_days,
    )
)
high_uplift_threshold = float(
    saved_analysis_settings.get(
        "high_uplift_threshold",
        default_analysis_settings.high_uplift_threshold,
    )
)
low_uplift_threshold = float(
    saved_analysis_settings.get(
        "low_uplift_threshold",
        default_analysis_settings.low_uplift_threshold,
    )
)
minimum_campaign_sales = float(
    saved_analysis_settings.get(
        "minimum_campaign_sales",
        default_analysis_settings.minimum_campaign_sales,
    )
)
only_complete_periods = bool(
    saved_analysis_settings.get(
        "only_complete_periods",
        default_analysis_settings.only_complete_periods,
    )
)
fill_missing_dates_with_zero = bool(
    saved_analysis_settings.get(
        "fill_missing_dates_with_zero",
        default_analysis_settings.fill_missing_dates_with_zero,
    )
)


# =========================================================
# 可調整觀察窗口
# =========================================================

st.subheader("分析窗口設定")

with st.form(
    "analysis_window_settings_form",
    border=True,
):
    st.markdown(
        "**活動起訖日由活動 Excel 決定。** 使用者可調整的是活動前基準"
        "與活動後觀察窗口；變更後會重新計算全部活動。"
    )

    window_options = sorted(
        {
            1,
            3,
            5,
            7,
            10,
            14,
            21,
            28,
            baseline_days,
            post_days,
        }
    )

    window_col1, window_col2, window_col3 = st.columns(
        [2, 2, 1]
    )

    with window_col1:
        selected_baseline_days = st.select_slider(
            "活動前基準天數",
            options=window_options,
            value=baseline_days,
            help="用活動開始前幾天的平均日銷量建立比較基準。",
        )

    with window_col2:
        selected_post_days = st.select_slider(
            "活動後觀察天數",
            options=window_options,
            value=post_days,
            help="用活動結束後幾天觀察銷量是否延續或回落。",
        )

    can_recalculate = (
        integrated_dataframe is not None
        and not integrated_dataframe.empty
        and activity_dataframe is not None
        and not activity_dataframe.empty
    )

    with window_col3:
        st.write("")
        recalculate_clicked = st.form_submit_button(
            "套用並重新估算",
            type="primary",
            width="stretch",
            disabled=not can_recalculate,
        )

    st.caption(
        "縮短窗口可能讓更多活動具備完整資料，但不會把原本不存在的"
        "日期變成有效資料；活動本身若超出銷量資料範圍，仍會標示待補。"
    )

if recalculate_clicked:
    try:
        recalculation_settings = AnalysisSettings(
            baseline_days=int(selected_baseline_days),
            post_days=int(selected_post_days),
            fill_missing_dates_with_zero=(
                fill_missing_dates_with_zero
            ),
            high_uplift_threshold=high_uplift_threshold,
            low_uplift_threshold=low_uplift_threshold,
            minimum_campaign_sales=minimum_campaign_sales,
            only_complete_periods=True,
        )

        with st.spinner("正在重新估算 63 筆活動…"):
            recalculated_performance = (
                analyze_activity_performance(
                    integrated_dataframe=integrated_dataframe,
                    activity_dataframe=activity_dataframe,
                    settings=recalculation_settings,
                )
            )
            (
                recalculated_strategy,
                recalculated_report,
            ) = generate_strategy_report(
                performance_dataframe=recalculated_performance,
                settings=recalculation_settings,
            )
    except Exception as error:
        st.error(
            "重新估算失敗，原本結果仍保留。"
            f"錯誤內容：{error}"
        )
        st.stop()

    st.session_state["activity_performance_dataframe"] = (
        recalculated_performance
    )
    st.session_state["strategy_report_dataframe"] = (
        recalculated_strategy
    )
    st.session_state["strategy_report_text"] = (
        recalculated_report
    )
    st.session_state["analysis_settings"] = {
        "baseline_days": recalculation_settings.baseline_days,
        "post_days": recalculation_settings.post_days,
        "fill_missing_dates_with_zero": (
            recalculation_settings.fill_missing_dates_with_zero
        ),
        "high_uplift_threshold": (
            recalculation_settings.high_uplift_threshold
        ),
        "low_uplift_threshold": (
            recalculation_settings.low_uplift_threshold
        ),
        "minimum_campaign_sales": (
            recalculation_settings.minimum_campaign_sales
        ),
        "only_complete_periods": True,
    }

    performance_dataframe = recalculated_performance
    strategy_dataframe = recalculated_strategy
    strategy_report_text = recalculated_report
    baseline_days = recalculation_settings.baseline_days
    post_days = recalculation_settings.post_days
    only_complete_periods = True

    st.success("已依新的觀察天數重新估算全部活動。")


if strategy_dataframe is None:
    st.warning(
        "尚未產生策略建議資料。"
        "請先完成「03 執行完整分析」。"
    )
    st.stop()


if strategy_dataframe.empty:
    st.warning(
        "目前沒有可顯示的策略建議。"
    )
    st.stop()


strategy = coerce_arrow_strings_to_object(strategy_dataframe)


# =========================================================
# 欄位整理
# =========================================================

def safe_unique_text_options(series: pd.Series) -> list[str]:
    """用純 Python 去重，避開 ArrowStringArray.unique 的原生崩潰。"""

    options: list[str] = []

    for value in series:
        if pd.isna(value):
            continue

        text = str(value).strip()

        if text and text not in options:
            options.append(text)

    return options


def safe_text_series(series: pd.Series) -> pd.Series:
    """以 Python object 字串建立 Series，避免 Arrow 原生字串轉型。"""

    return pd.Series(
        ["" if pd.isna(value) else str(value) for value in series],
        index=series.index,
        dtype=object,
        name=series.name,
    )


PERCENT_TABLE_COLUMNS = {
    "活動提升率",
    "活動後銷量延續率",
}

INTEGER_TABLE_COLUMNS = {
    "排序",
    "活動總銷量",
    "活動增量銷量",
    "推估營收",
    "推估增量營收",
}

STRATEGY_HEADER_HELP = {
    "策略分類": (
        "依資料完整度、活動提升率與活動總銷量門檻，判定為延續、優化、"
        "檢討或待補資料；分類是決策輔助，不等同獲利判斷。"
    ),
    "商品活動": (
        "由商品編號、商品名稱與活動 Excel 的起訖日期組成，"
        "每一列代表一筆活動。"
    ),
    "活動提升率": (
        "公式：（活動期平均日銷量－活動前平均日銷量）÷活動前平均日銷量。"
        "例：基準日均 10 件、活動日均 12 件，提升率為 20%。"
    ),
    "活動總銷量": (
        "公式：Excel 活動起訖日內，每日商品銷量加總。"
        "這是活動期間觀察到的總件數，不等於活動帶來的增量。"
    ),
    "推估營收": (
        "公式：活動總銷量 × 活動價格。尚未扣除折扣、平台抽成、"
        "廣告、物流、贈品及退貨。"
    ),
    "活動增量銷量": (
        "公式：活動總銷量－（活動前平均日銷量 × 活動天數）。"
        "負值表示活動期銷量低於原本基準；前後比較不等於證明因果。"
    ),
    "推估增量營收": (
        "公式：活動增量銷量 × 活動價格。尚未扣除各項成本，"
        "因此不是增量毛利。"
    ),
    "活動後銷量延續率": (
        "公式：活動後觀察期間平均日銷量 ÷ 活動期平均日銷量。"
        "這不是顧客留存率，也不能直接代表回購。"
    ),
    "資料完整度": (
        "依活動前、活動中、活動後所需日期是否落在銷量資料範圍內判斷，"
        "不是主觀信心分數。"
    ),
    "可能影響檔期／活動": (
        "優先讀取活動 Excel 記載的主活動、同期檔期與優惠，"
        "列為銷量變動的候選原因，不代表已證明單一活動的因果。"
    ),
    "檔期判讀來源": (
        "顯示檔期名稱取自活動 Excel、既有活動欄位或日期輔助推估；"
        "目前以 Excel 明確記載為優先。"
    ),
    "活動／優惠重疊": (
        "活動期間若同時出現其他檔期、滿額贈、平台幣或其他優惠即標記。"
        "有重疊時，增量不能直接全部歸因於單一活動。"
    ),
    "資料缺漏說明": (
        "逐筆列出缺少活動前基準、活動期間或活動後觀察日期的原因，"
        "用來判斷需要補哪一段銷量資料。"
    ),
    "判斷依據": (
        "把該活動的提升率、總銷量與目前分類門檻寫成文字，"
        "說明為何得到這個策略分類。"
    ),
    "檔期／歸因判讀": (
        "綜合 Excel 檔期、同期活動／優惠與活動後銷量變化提出關聯性判讀；"
        "仍建議用對照商品、渠道或同期去年驗證。"
    ),
    "建議": (
        "依該商品的活動成效、歷史可比活動、檔期重疊與活動後表現，"
        "產生個別化的診斷、下一檔行動、備貨參考與驗證方式。"
    ),
}


def format_html_table_value(column: str, value: object) -> str:
    """格式化 HTML 表格內容，不交給 Streamlit／PyArrow 序列化。"""

    if pd.isna(value):
        return "—"

    if column in PERCENT_TABLE_COLUMNS:
        return f"{float(value):.1%}"

    if column in INTEGER_TABLE_COLUMNS:
        return f"{float(value):,.0f}"

    return html.escape(str(value))


def render_safe_html_table(
    dataframe: pd.DataFrame,
    header_help: dict[str, str] | None = None,
    max_height: int = 520,
) -> None:
    """用可捲動 HTML 表格呈現資料，避開 Streamlit Arrow 原生崩潰。"""

    header_help = header_help or {}
    headers: list[str] = []

    for column in dataframe.columns:
        label = html.escape(str(column))
        help_text = header_help.get(str(column))

        if help_text:
            headers.append(
                "<th><span class='strategy-header-help' tabindex='0' "
                "data-tooltip='"
                + html.escape(help_text, quote=True)
                + "'>"
                + label
                + " <span class='strategy-info-badge'>i</span></span></th>"
            )
        else:
            headers.append(f"<th>{label}</th>")

    rows: list[str] = []

    for row_values in dataframe.itertuples(index=False, name=None):
        cells = [
            "<td>"
            + format_html_table_value(str(column), value)
            + "</td>"
            for column, value in zip(dataframe.columns, row_values)
        ]
        rows.append("<tr>" + "".join(cells) + "</tr>")

    table_html = (
        "<div class='strategy-table-wrap' style='max-height:"
        + str(max_height)
        + "px'><table class='strategy-safe-table'><thead><tr>"
        + "".join(headers)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )

    st.markdown(
        """
        <style>
        .strategy-table-wrap {
            overflow: auto;
            width: 100%;
            border: 1px solid #d9dee8;
            border-radius: 12px;
            background: white;
        }
        .strategy-safe-table {
            border-collapse: collapse;
            min-width: 100%;
            width: max-content;
            font-size: 0.88rem;
        }
        .strategy-safe-table th {
            position: sticky;
            top: 0;
            z-index: 5;
            padding: 10px 12px;
            background: #f5f7fb;
            border-bottom: 1px solid #d9dee8;
            text-align: left;
            white-space: nowrap;
        }
        .strategy-safe-table td {
            max-width: 440px;
            padding: 9px 12px;
            border-bottom: 1px solid #e8ebf1;
            vertical-align: top;
            line-height: 1.45;
            white-space: normal;
        }
        .strategy-safe-table tr:hover td {
            background: #fff7f0;
        }
        .strategy-header-help {
            position: relative;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            cursor: help;
            text-decoration: underline dotted;
            text-underline-offset: 3px;
            outline: none;
        }
        .strategy-info-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #315a9b;
            color: white;
            font-size: 12px;
            font-weight: 700;
            line-height: 1;
            text-decoration: none;
        }
        .strategy-header-help::after {
            content: attr(data-tooltip);
            position: absolute;
            top: calc(100% + 8px);
            left: 0;
            z-index: 100;
            width: 330px;
            padding: 10px 12px;
            border-radius: 8px;
            background: #172033;
            color: white;
            box-shadow: 0 8px 24px rgba(23, 32, 51, 0.24);
            font-size: 13px;
            font-weight: 400;
            line-height: 1.55;
            text-align: left;
            white-space: normal;
            opacity: 0;
            visibility: hidden;
            transform: translateY(-3px);
            transition: opacity 0.15s ease, transform 0.15s ease;
            pointer-events: none;
        }
        .strategy-header-help:hover::after,
        .strategy-header-help:focus::after {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }
        .strategy-safe-table th:nth-last-child(-n + 4)
        .strategy-header-help::after {
            right: 0;
            left: auto;
        }
        </style>
        """
        + table_html,
        unsafe_allow_html=True,
    )

numeric_columns = [
    "活動提升率",
    "活動總銷量",
    "推估營收",
    "活動天數",
    "基準日均銷量",
    "活動日均銷量",
    "活動增量銷量",
    "推估增量營收",
    "活動日均營收",
    "活動後銷量延續率",
    "活動後較基準變化",
]

for column in numeric_columns:
    if column in strategy.columns:
        strategy[column] = pd.to_numeric(
            strategy[column],
            errors="coerce",
        )


required_columns = [
    "策略分類",
    "商品活動",
    "活動提升率",
    "活動總銷量",
    "推估營收",
    "資料完整度",
    "建議",
]

missing_columns = [
    column
    for column in required_columns
    if column not in strategy.columns
]

if missing_columns:
    st.error(
        "策略資料缺少必要欄位："
        + "、".join(missing_columns)
    )
    st.stop()


# =========================================================
# 篩選器
# =========================================================

st.subheader("策略篩選")

with st.container(border=True):
    st.markdown(
        """
        <div class="analysis-filter-heading">
            <div class="analysis-filter-icon">🧭</div>
            <div>
                <div class="analysis-filter-title">篩選策略資料</div>
                <div class="analysis-filter-description">
                    可依策略分類、資料完整度與最低活動總銷量縮小範圍。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filter_col1, filter_col2, filter_col3 = st.columns(3)


    strategy_category_options = safe_unique_text_options(
        strategy["策略分類"]
    )


    with filter_col1:
        selected_categories = st.multiselect(
            "策略分類",
            options=strategy_category_options,
            default=strategy_category_options,
        )


    completeness_options = safe_unique_text_options(
        strategy["資料完整度"]
    )


    with filter_col2:
        selected_completeness = st.multiselect(
            "資料完整度",
            options=completeness_options,
            default=completeness_options,
        )


    with filter_col3:
        minimum_sales = st.number_input(
            "最低活動總銷量",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )

filtered_strategy = strategy.copy()


if selected_categories:
    filtered_strategy = filtered_strategy[
        safe_text_series(
            filtered_strategy["策略分類"]
        ).isin(
            selected_categories
        )
    ].copy()


if selected_completeness:
    filtered_strategy = filtered_strategy[
        safe_text_series(
            filtered_strategy["資料完整度"]
        ).isin(
            selected_completeness
        )
    ].copy()


filtered_strategy = filtered_strategy[
    filtered_strategy[
        "活動總銷量"
    ].fillna(0) >= minimum_sales
].copy()


if filtered_strategy.empty:
    st.warning(
        "目前篩選條件下沒有策略資料。"
    )
    st.stop()


# =========================================================
# KPI
# =========================================================

st.divider()

st.subheader("策略摘要")


st.markdown("#### 分類判斷標準")

with st.container(border=True):
    st.markdown(
        (
            "**活動提升率公式：**（活動期間平均每日銷量－"
            f"活動前 {baseline_days} 天平均每日銷量）÷ "
            f"活動前 {baseline_days} 天平均每日銷量。"
        )
    )

    standard_col1, standard_col2, standard_col3, standard_col4 = (
        st.columns(4)
    )

    with standard_col1:
        st.success(
            "建議延續\n\n"
            f"提升率 **≥ {high_uplift_threshold:.1%}**，且活動總銷量 "
            f"**≥ {minimum_campaign_sales:,.0f}**。兩個條件必須同時成立。"
        )

    with standard_col2:
        st.info(
            "建議優化\n\n"
            f"**{low_uplift_threshold:.1%} ≤ 提升率 < "
            f"{high_uplift_threshold:.1%}**；或提升率已達高門檻，"
            "但活動總銷量未達最低規模。"
        )

    with standard_col3:
        st.error(
            "建議檢討\n\n"
            f"提升率 **< {low_uplift_threshold:.1%}**。"
            "等於低門檻時歸入建議優化。"
        )

    with standard_col4:
        st.warning(
            "資料不足／待補資料\n\n"
            "活動前、中、後任一觀察期間未完整，或活動前日均銷量為 0；"
            "活動仍保留在清單，但暫不套用三種正式分類。"
        )

    observation_scope_text = (
        f"目前只將活動前、中、後（活動後 {post_days} 天）"
        "觀察期間皆完整，且可計算提升率的活動列入正式分類；"
        "其他活動列為資料不足，不會被刪除。"
        if only_complete_periods
        else (
            "目前允許觀察期間不完整的活動進入分類；"
            "請同時查看「資料完整度」，避免過度解讀。"
        )
    )

    st.caption(
        observation_scope_text
        + " 分類是銷量規則，不等同獲利判斷；"
        "若要決定是否加碼，仍需搭配毛利、媒體成本與庫存。"
    )

    st.caption(
        f"活動後 {post_days} 天是短檔的預設觀察窗，不是唯一正確答案。"
        "若商品購買週期較長、活動超過一週或檔期密集，可改用 14／28 天，"
        "或比較相同星期結構；資料未覆蓋完整只代表暫不能正式判讀。"
    )

    with st.expander("資料完整度的判斷標準", expanded=True):
        st.markdown(
            f"""
            - **完整（活動前、中、後皆齊）：** 銷量資料日期範圍完整覆蓋活動前 **{baseline_days} 天**、Excel 活動起訖日，以及活動後 **{post_days} 天**。
            - **部分（活動期完整，前或後缺漏）：** Excel 活動期間已完整落在銷量資料範圍內，但活動前基準或活動後觀察期間有缺口。
            - **不足（活動期本身未完整）：** Excel 活動起訖日已超出目前銷量資料的日期範圍。
            - **正式分類的額外條件：** 活動前平均日銷量必須大於 0，才能計算提升率。

            這是「日期覆蓋完整度」，不是主觀信心分數。若設定「沒有銷量紀錄的日期視為 0」，期間內未出現的商品日期會按零銷量計算。
            """
        )


continue_count = int(
    (
        filtered_strategy[
            "策略分類"
        ] == "建議延續"
    ).sum()
)

optimize_count = int(
    (
        filtered_strategy[
            "策略分類"
        ] == "建議優化"
    ).sum()
)

review_count = int(
    (
        filtered_strategy[
            "策略分類"
        ] == "建議檢討"
    ).sum()
)

insufficient_count = int(
    (
        filtered_strategy[
            "策略分類"
        ] == "資料不足／待補資料"
    ).sum()
)

formal_strategy = filtered_strategy[
    filtered_strategy["策略分類"]
    != "資料不足／待補資料"
].copy()


(
    strategy_card_col1,
    strategy_card_col2,
    strategy_card_col3,
    strategy_card_col4,
) = (
    st.columns(4)
)

strategy_cards = [
    {
        "column": strategy_card_col1,
        "class_name": "strategy-summary-card strategy-summary-continue",
        "eyebrow": "CONTINUE",
        "title": "建議延續",
        "count": continue_count,
        "description": (
            f"提升率至少 {high_uplift_threshold:.1%}，"
            f"且總銷量至少 {minimum_campaign_sales:,.0f}。"
        ),
    },
    {
        "column": strategy_card_col2,
        "class_name": "strategy-summary-card strategy-summary-optimize",
        "eyebrow": "OPTIMIZE",
        "title": "建議優化",
        "count": optimize_count,
        "description": "介於高低門檻，或高提升但銷量規模不足。",
    },
    {
        "column": strategy_card_col3,
        "class_name": "strategy-summary-card strategy-summary-review",
        "eyebrow": "REVIEW",
        "title": "建議檢討",
        "count": review_count,
        "description": (
            f"提升率低於 {low_uplift_threshold:.1%}，"
            "應先查明負向原因。"
        ),
    },
    {
        "column": strategy_card_col4,
        "class_name": "strategy-summary-card strategy-summary-insufficient",
        "eyebrow": "NEED DATA",
        "title": "資料不足／待補資料",
        "count": insufficient_count,
        "description": "仍列出活動與缺漏日期，補齊後再正式分類。",
    },
]

for card in strategy_cards:
    with card["column"]:
        st.markdown(
            f"""
            <div class="{card['class_name']}">
                <div class="strategy-summary-eyebrow">
                    {card['eyebrow']}
                </div>
                <div class="strategy-summary-title">
                    {card['title']}
                </div>
                <div class="strategy-summary-count">
                    {card['count']:,}
                </div>
                <div class="strategy-summary-description">
                    {card['description']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = (
    st.columns(5)
)


kpi_col1.metric(
    "活動總筆數",
    f"{len(filtered_strategy):,}",
)

kpi_col2.metric(
    "可正式判讀",
    f"{len(formal_strategy):,}",
)

kpi_col3.metric(
    "資料待補",
    f"{insufficient_count:,}",
)

kpi_col4.metric(
    "Excel 檔期判讀",
    f"{filtered_strategy.get('檔期判讀來源', pd.Series(dtype=str)).eq('活動 Excel').sum():,}",
)

kpi_col5.metric(
    "活動／優惠重疊",
    f"{filtered_strategy.get('活動／優惠重疊', pd.Series(dtype=bool)).fillna(False).sum():,}",
)


with st.expander(
    "建議下一階段補充的代營運資料與指標",
    expanded=False,
):
    st.markdown(
        """
        目前資料可以估算銷量增量、營收增量、日均營收與活動後銷量延續率；
        若要回答「是否值得加碼」及「是哪個環節造成變動」，建議再串接：

        - **流量與轉換：** 曝光、商品頁瀏覽、加購率、結帳轉換率；用來區分流量不足或頁面轉換問題。
        - **投放效率：** 廣告花費、ROAS、每筆訂單成本、每位新客成本；用來判斷擴大曝光是否仍划算。
        - **獲利品質：** 實付價、折扣成本、平台抽成、毛利、贈品與物流成本；用增量毛利取代單看推估營收。
        - **商品與庫存：** 缺貨時數、售罄率、庫存週轉天數、取消率與退貨率；避免把缺貨造成的低銷誤判為活動無效。
        - **顧客品質：** 新客占比、回購率、客單價、連帶購買率與會員分群；確認活動帶來的是一次性促購或可留存顧客。
        - **歸因驗證：** 渠道、區域、對照商品、去年同期與活動重疊標記；用來拆分平台大檔、季節性與單一活動效果。
        """
    )


# =========================================================
# 月度銷量趨勢、MoM 與 YoY
# =========================================================

st.divider()

st.subheader("月度銷量趨勢")

monthly_sales = pd.DataFrame()

if (
    standardized_dataframe is not None
    and not standardized_dataframe.empty
    and {
        "sale_date",
        "quantity",
    }.issubset(standardized_dataframe.columns)
):
    monthly_source = standardized_dataframe[
        [
            "sale_date",
            "quantity",
        ]
    ].copy()

    monthly_source["sale_date"] = pd.to_datetime(
        monthly_source["sale_date"],
        errors="coerce",
    )

    monthly_source["quantity"] = pd.to_numeric(
        monthly_source["quantity"],
        errors="coerce",
    )

    monthly_source = monthly_source.dropna(
        subset=[
            "sale_date",
            "quantity",
        ]
    )

    if not monthly_source.empty:
        monthly_source["sale_month"] = (
            monthly_source["sale_date"]
            .dt.to_period("M")
        )

        monthly_sales = (
            monthly_source.groupby(
                "sale_month",
                as_index=False,
            )["quantity"]
            .sum()
            .rename(
                columns={
                    "quantity": "monthly_quantity",
                }
            )
            .sort_values("sale_month")
        )

        monthly_sales["month_label"] = (
            monthly_sales["sale_month"]
            .astype(str)
        )


if monthly_sales.empty:
    st.info(
        "目前沒有足夠的標準化銷量資料，"
        "因此無法計算月銷量、MoM 與 YoY。"
    )

else:
    latest_period = monthly_sales[
        "sale_month"
    ].max()
    latest_data_date = monthly_source["sale_date"].max()
    latest_month_end = latest_data_date + pd.offsets.MonthEnd(0)
    latest_is_partial = (
        latest_data_date.normalize()
        < latest_month_end.normalize()
    )
    comparison_day = int(latest_data_date.day)

    previous_period = latest_period - 1
    previous_year_period = latest_period - 12

    monthly_lookup = monthly_sales.set_index(
        "sale_month"
    )["monthly_quantity"]

    latest_quantity = float(
        monthly_lookup.get(
            latest_period,
            0,
        )
    )

    def period_quantity(period: pd.Period):
        period_rows = monthly_source[
            monthly_source["sale_month"] == period
        ]

        if latest_is_partial:
            period_rows = period_rows[
                period_rows["sale_date"].dt.day
                <= comparison_day
            ]

        if period_rows.empty:
            return None

        return float(period_rows["quantity"].sum())

    previous_quantity = period_quantity(previous_period)
    previous_year_quantity = period_quantity(
        previous_year_period
    )

    def calculate_growth_rate(
        current_value: float,
        comparison_value,
    ):
        if (
            comparison_value is None
            or pd.isna(comparison_value)
            or comparison_value == 0
        ):
            return None

        return (
            current_value
            / float(comparison_value)
            - 1
        )

    mom_rate = calculate_growth_rate(
        latest_quantity,
        previous_quantity,
    )

    yoy_rate = calculate_growth_rate(
        latest_quantity,
        previous_year_quantity,
    )

    latest_col, mom_col, yoy_col = st.columns(3)

    with latest_col:
        st.metric(
            f"{latest_period} 月銷量",
            f"{latest_quantity:,.0f}",
        )

        st.caption(
            (
                f"目前資料只到 {latest_data_date.strftime('%Y-%m-%d')}，"
                "此月仍是部分月份。"
                if latest_is_partial
                else "此月資料已覆蓋至月底。"
            )
        )

    with mom_col:
        st.metric(
            (
                f"MoM（截至 {comparison_day} 日）"
                if latest_is_partial
                else "MoM（月成長率）"
            ),
            (
                f"{mom_rate:.1%}"
                if mom_rate is not None
                else "-"
            ),
            delta=(
                f"{latest_quantity - float(previous_quantity):+,.0f} 銷量"
                if mom_rate is not None
                else None
            ),
        )

        st.caption(
            (
                f"{latest_period}：{latest_quantity:,.0f}；"
                f"{previous_period}：{float(previous_quantity):,.0f}"
                if mom_rate is not None
                else f"缺少 {previous_period} 或其銷量為 0，無法計算。"
            )
        )

    with yoy_col:
        st.metric(
            (
                f"YoY（截至 {comparison_day} 日）"
                if latest_is_partial
                else "YoY（年成長率）"
            ),
            (
                f"{yoy_rate:.1%}"
                if yoy_rate is not None
                else "-"
            ),
            delta=(
                f"{latest_quantity - float(previous_year_quantity):+,.0f} 銷量"
                if yoy_rate is not None
                else None
            ),
        )

        st.caption(
            (
                f"{latest_period}：{latest_quantity:,.0f}；"
                f"{previous_year_period}：{float(previous_year_quantity):,.0f}"
                if yoy_rate is not None
                else (
                    f"缺少 {previous_year_period} 或其銷量為 0，"
                    "無法計算。"
                )
            )
        )

    monthly_figure = px.line(
        monthly_sales,
        x="month_label",
        y="monthly_quantity",
        markers=True,
        labels={
            "month_label": "月份",
            "monthly_quantity": "總銷量",
        },
    )

    monthly_figure.update_traces(
        line={
            "width": 3,
        },
        marker={
            "size": 8,
        },
        hovertemplate=(
            "月份：%{x}<br>"
            "總銷量：%{y:,.0f}"
            "<extra></extra>"
        ),
    )

    monthly_figure.update_layout(
        xaxis_title="月份",
        yaxis_title="總銷量",
        margin={
            "l": 10,
            "r": 10,
            "t": 20,
            "b": 10,
        },
    )

    st.plotly_chart(
        monthly_figure,
        use_container_width=True,
    )

    st.caption(
        "最新月份未到月底時，MoM／YoY 會改用相同日序比較，"
        "避免拿部分月份直接對完整月份。"
    )


# =========================================================
# 活動提升率與總銷量圖
# =========================================================

st.divider()

st.subheader("活動成效與銷量對照")


chart_dataframe = formal_strategy.dropna(
    subset=[
        "活動提升率",
        "活動總銷量",
    ]
).copy()


if chart_dataframe.empty:
    st.info(
        "目前沒有足夠資料繪製活動成效圖。"
    )

else:
    chart_dataframe[
        "活動提升率百分比"
    ] = (
        chart_dataframe[
            "活動提升率"
        ] * 100
    )

    strategy_scatter_figure = px.scatter(
        chart_dataframe,
        x="活動總銷量",
        y="活動提升率百分比",
        color="策略分類",
        hover_name="商品活動",
        hover_data={
            "推估營收": ":,.0f",
            "資料完整度": True,
            "活動提升率百分比": ":.1f",
        },
        labels={
            "活動總銷量": "活動總銷量",
            "活動提升率百分比": "活動提升率（%）",
            "策略分類": "策略分類",
        },
    )

    strategy_scatter_figure.add_hline(
        y=low_uplift_threshold * 100,
        line_dash="dash",
        annotation_text=(
            "檢討門檻 "
            f"{low_uplift_threshold:.1%}"
        ),
    )

    strategy_scatter_figure.add_hline(
        y=high_uplift_threshold * 100,
        line_dash="dot",
        annotation_text=(
            "延續提升率門檻 "
            f"{high_uplift_threshold:.1%}"
        ),
    )

    strategy_scatter_figure.update_layout(
        xaxis_title="活動總銷量",
        yaxis_title="活動提升率（%）",
        margin={
            "l": 10,
            "r": 10,
            "t": 20,
            "b": 10,
        },
    )

    st.plotly_chart(
        strategy_scatter_figure,
        use_container_width=True,
    )

    st.caption(
        "右上方通常代表銷量較高且活動提升率較高；"
        "但沒有毛利與成本資料時，不能直接解讀為高獲利。"
    )


# =========================================================
# 活動策略與成效清單
# =========================================================

st.divider()

st.subheader("活動策略與成效清單")

st.caption(
    "每一列代表一筆商品活動，集中呈現活動成效、策略分類、檔期判讀與"
    "後續建議。將滑鼠移到欄名旁的藍色 i，可查看指標公式或欄位來源。"
)

preferred_strategy_columns = [
    "策略分類",
    "商品活動",
    "活動提升率",
    "活動總銷量",
    "活動增量銷量",
    "推估營收",
    "推估增量營收",
    "活動後銷量延續率",
    "資料完整度",
    "可能影響檔期／活動",
    "檔期判讀來源",
    "活動／優惠重疊",
    "資料缺漏說明",
    "判斷依據",
    "檔期／歸因判讀",
    "建議",
]

display_strategy_columns = [
    column
    for column in preferred_strategy_columns
    if column in filtered_strategy.columns
]

render_safe_html_table(
    filtered_strategy[display_strategy_columns],
    header_help=STRATEGY_HEADER_HELP,
    max_height=560,
)

with st.expander(
    "查看單一活動完整判讀與建議",
    expanded=True,
):
    detail_activity = st.selectbox(
        "選擇商品活動",
        options=(
            safe_text_series(
                filtered_strategy["商品活動"]
            ).tolist()
        ),
        key="strategy_detail_activity",
    )

    detail_row = filtered_strategy[
        safe_text_series(filtered_strategy["商品活動"])
        == detail_activity
    ].iloc[0]

    st.markdown(
        f"### {detail_row['策略分類']}｜"
        f"{detail_row.get('可能影響檔期／活動', '檔期未判定')}"
    )

    detail_col1, detail_col2, detail_col3, detail_col4 = (
        st.columns(4)
    )

    detail_col1.metric(
        "活動提升率",
        (
            f"{detail_row['活動提升率']:.1%}"
            if pd.notna(detail_row["活動提升率"])
            else "-"
        ),
    )
    detail_col2.metric(
        "活動總銷量",
        (
            f"{detail_row['活動總銷量']:,.0f}"
            if pd.notna(detail_row["活動總銷量"])
            else "-"
        ),
    )
    detail_col3.metric(
        "推估增量銷量",
        (
            f"{detail_row.get('活動增量銷量'):+,.0f}"
            if pd.notna(
                detail_row.get("活動增量銷量")
            )
            else "-"
        ),
    )
    detail_col4.metric(
        "活動後銷量延續率",
        (
            f"{detail_row.get('活動後銷量延續率'):.1%}"
            if pd.notna(
                detail_row.get("活動後銷量延續率")
            )
            else "-"
        ),
    )

    if detail_row.get("策略分類") == "資料不足／待補資料":
        st.warning(detail_row.get("資料缺漏說明"))

    if has_reason := detail_row.get("判斷依據"):
        st.markdown("**分類依據**")
        st.write(has_reason)

    if attribution_text := detail_row.get(
        "檔期／歸因判讀"
    ):
        st.markdown("**檔期與歸因判讀**")
        st.write(attribution_text)

    st.markdown("**個別化行動建議**")
    st.write(detail_row["建議"])


# =========================================================
# 文字策略報告
# =========================================================

st.divider()

st.subheader("主管策略摘要")


if strategy_report_text:
    with st.expander(
        "展開完整文字報告",
        expanded=False,
    ):
        st.markdown(
            strategy_report_text
        )

else:
    st.info(
        "目前沒有策略文字報告。"
    )


# =========================================================
# 下載
# =========================================================

st.divider()

st.subheader("匯出策略資料")


download_col1, download_col2 = st.columns(2)


strategy_csv = (
    filtered_strategy.to_csv(
        index=False,
        encoding="utf-8-sig",
    )
    .encode("utf-8-sig")
)


with download_col1:
    st.download_button(
        "下載篩選後策略清單",
        data=strategy_csv,
        file_name=(
            "filtered_strategy_recommendations.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )


with download_col2:
    if strategy_report_text:
        st.download_button(
            "下載策略文字報告",
            data=strategy_report_text.encode(
                "utf-8"
            ),
            file_name="strategy_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    else:
        st.button(
            "目前沒有文字報告可下載",
            disabled=True,
            use_container_width=True,
        )


# =========================================================
# 下一步提示
# =========================================================

st.info(
    "需要進一步解讀活動原因或規劃下一期促銷時，"
    "可前往「AI 策略顧問」進行提問。"
)
