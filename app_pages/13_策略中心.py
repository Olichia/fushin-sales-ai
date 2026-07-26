from pathlib import Path
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
        整理建議延續、建議優化與建議檢討的活動。
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


strategy = strategy_dataframe.copy()


# =========================================================
# 欄位整理
# =========================================================

numeric_columns = [
    "活動提升率",
    "活動總銷量",
    "推估營收",
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
    "資料信心",
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
                    可依策略分類、資料信心與最低活動總銷量縮小範圍。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filter_col1, filter_col2, filter_col3 = st.columns(3)


    strategy_category_options = (
        strategy["策略分類"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


    with filter_col1:
        selected_categories = st.multiselect(
            "策略分類",
            options=strategy_category_options,
            default=strategy_category_options,
        )


    confidence_options = (
        strategy["資料信心"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


    with filter_col2:
        selected_confidence = st.multiselect(
            "資料信心",
            options=confidence_options,
            default=confidence_options,
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
        filtered_strategy[
            "策略分類"
        ].astype(str).isin(
            selected_categories
        )
    ].copy()


if selected_confidence:
    filtered_strategy = filtered_strategy[
        filtered_strategy[
            "資料信心"
        ].astype(str).isin(
            selected_confidence
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

median_uplift = filtered_strategy[
    "活動提升率"
].median()

total_estimated_revenue = filtered_strategy[
    "推估營收"
].sum(
    min_count=1
)


strategy_card_col1, strategy_card_col2, strategy_card_col3 = (
    st.columns(3)
)

strategy_cards = [
    {
        "column": strategy_card_col1,
        "class_name": "strategy-summary-card strategy-summary-continue",
        "eyebrow": "CONTINUE",
        "title": "建議延續",
        "count": continue_count,
        "description": "優先保留成效較佳、資料可信度較高的活動。",
    },
    {
        "column": strategy_card_col2,
        "class_name": "strategy-summary-card strategy-summary-optimize",
        "eyebrow": "OPTIMIZE",
        "title": "建議優化",
        "count": optimize_count,
        "description": "調整優惠、價格、期間或商品組合後再次測試。",
    },
    {
        "column": strategy_card_col3,
        "class_name": "strategy-summary-card strategy-summary-review",
        "eyebrow": "REVIEW",
        "title": "建議檢討",
        "count": review_count,
        "description": "檢視活動設計、重疊優惠與資料完整性。",
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
    "建議延續",
    f"{continue_count:,}",
)

kpi_col2.metric(
    "建議優化",
    f"{optimize_count:,}",
)

kpi_col3.metric(
    "建議檢討",
    f"{review_count:,}",
)

kpi_col4.metric(
    "提升率中位數",
    (
        f"{median_uplift:.1%}"
        if pd.notna(median_uplift)
        else "-"
    ),
)

kpi_col5.metric(
    "推估營收合計",
    (
        f"{total_estimated_revenue:,.0f}"
        if pd.notna(total_estimated_revenue)
        else "-"
    ),
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

    previous_quantity = monthly_lookup.get(
        previous_period
    )

    previous_year_quantity = monthly_lookup.get(
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
            "以資料中最新月份為比較基準。"
        )

    with mom_col:
        st.metric(
            "MoM（月成長率）",
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
            "YoY（年成長率）",
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


# =========================================================
# 活動提升率與總銷量圖
# =========================================================

st.divider()

st.subheader("活動成效與銷量對照")


chart_dataframe = filtered_strategy.dropna(
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
            "資料信心": True,
            "活動提升率百分比": ":.1f",
        },
        labels={
            "活動總銷量": "活動總銷量",
            "活動提升率百分比": "活動提升率（%）",
            "策略分類": "策略分類",
        },
    )

    strategy_scatter_figure.add_hline(
        y=0,
        line_dash="dash",
        annotation_text="無提升",
    )

    strategy_scatter_figure.add_hline(
        y=20,
        line_dash="dot",
        annotation_text="高成效門檻 20%",
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
# 活動策略清單
# =========================================================

st.divider()

st.subheader("活動策略清單")

st.dataframe(
    filtered_strategy,
    use_container_width=True,
    hide_index=True,
    column_config={
        "活動提升率": (
            st.column_config.NumberColumn(
                format="percent"
            )
        ),
        "活動總銷量": (
            st.column_config.NumberColumn(
                format="%.0f"
            )
        ),
        "推估營收": (
            st.column_config.NumberColumn(
                format="%.0f"
            )
        ),
    },
)

st.caption(
    "清單內容與完整分析產生的活動策略清單一致，"
    "並套用本頁上方的策略分類、資料信心與最低銷量篩選。"
)


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