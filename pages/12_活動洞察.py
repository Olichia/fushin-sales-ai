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
    <div class="step-label">ACTIVITY INSIGHTS</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>活動洞察</h1>
    </div>

    <p class="product-page-description">
        比較不同商品活動的成效，並查看單一活動在活動前、
        活動期間與活動後的每日銷量變化。活動提升率僅代表
        活動期間與銷量變化的關聯，不等於已證明因果關係。
    </p>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 取得既有資料
# =========================================================

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)

integrated_dataframe = st.session_state.get(
    "integrated_sales_activity_dataframe"
)


if performance_dataframe is None:
    st.warning(
        "尚未產生活動成效分析結果。"
        "請先完成「03 執行完整分析」。"
    )
    st.stop()


if performance_dataframe.empty:
    st.warning(
        "目前沒有可顯示的活動成效資料。"
    )
    st.stop()


performance = performance_dataframe.copy()


# =========================================================
# 欄位型別整理
# =========================================================

date_columns = [
    "activity_start_date",
    "activity_end_date",
    "baseline_start_date",
    "baseline_end_date",
    "post_start_date",
    "post_end_date",
]

for column in date_columns:
    if column in performance.columns:
        performance[column] = pd.to_datetime(
            performance[column],
            errors="coerce",
        )


numeric_columns = [
    "baseline_average_daily_sales",
    "campaign_average_daily_sales",
    "post_average_daily_sales",
    "campaign_total_sales",
    "uplift_rate",
    "post_change_rate",
    "campaign_price",
    "estimated_revenue",
]

for column in numeric_columns:
    if column in performance.columns:
        performance[column] = pd.to_numeric(
            performance[column],
            errors="coerce",
        )


boolean_columns = [
    "baseline_complete",
    "campaign_complete",
    "post_complete",
    "all_periods_complete",
]

for column in boolean_columns:
    if column in performance.columns:
        performance[column] = (
            performance[column]
            .fillna(False)
            .astype(bool)
        )


performance["product_id"] = (
    performance["product_id"]
    .astype("string")
    .str.strip()
)

performance["product_name"] = (
    performance["product_name"]
    .fillna("未提供商品名稱")
    .astype(str)
    .str.strip()
)


# =========================================================
# 活動成效分類
# =========================================================

performance["performance_category"] = (
    "無法判定"
)

performance.loc[
    performance["uplift_rate"] >= 0.20,
    "performance_category",
] = "高成效"

performance.loc[
    (
        performance["uplift_rate"] >= 0
    )
    & (
        performance["uplift_rate"] < 0.20
    ),
    "performance_category",
] = "一般成效"

performance.loc[
    performance["uplift_rate"] < 0,
    "performance_category",
] = "低成效"


performance["activity_label"] = (
    performance["product_id"].astype(str)
    + "｜"
    + performance["product_name"].astype(str)
    + "｜"
    + performance["activity_start_date"]
    .dt.strftime("%Y-%m-%d")
    + "～"
    + performance["activity_end_date"]
    .dt.strftime("%Y-%m-%d")
)


# =========================================================
# 頁面上方篩選器
# =========================================================

st.subheader("分析篩選")

with st.container(border=True):
    st.markdown(
        """
        <div class="analysis-filter-heading">
            <div class="analysis-filter-icon">🔎</div>
            <div>
                <div class="analysis-filter-title">篩選活動資料</div>
                <div class="analysis-filter-description">
                    可依商品、成效分類與資料信心縮小分析範圍。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filter_col1, filter_col2, filter_col3 = st.columns(
        [1.3, 1, 1]
    )


    product_options = (
        performance[
            [
                "product_id",
                "product_name",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "product_id",
                "product_name",
            ]
        )
    )


    product_label_mapping = {
        f"{row.product_id}｜{row.product_name}": (
            str(row.product_id)
        )
        for row in product_options.itertuples()
    }


    with filter_col1:
        selected_product_labels = st.multiselect(
            "商品",
            options=list(
                product_label_mapping.keys()
            ),
            default=[],
            placeholder="未選擇時顯示全部商品",
        )


    with filter_col2:
        selected_performance_categories = (
            st.multiselect(
                "成效分類",
                options=[
                    "高成效",
                    "一般成效",
                    "低成效",
                    "無法判定",
                ],
                default=[
                    "高成效",
                    "一般成效",
                    "低成效",
                    "無法判定",
                ],
            )
        )


    confidence_options = []

    if "data_confidence" in performance.columns:
        confidence_options = sorted(
            performance["data_confidence"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )


    with filter_col3:
        selected_confidence = st.multiselect(
            "資料信心",
            options=confidence_options,
            default=confidence_options,
        )

filtered_performance = performance.copy()


if selected_product_labels:
    selected_product_ids = [
        product_label_mapping[label]
        for label in selected_product_labels
    ]

    filtered_performance = (
        filtered_performance[
            filtered_performance[
                "product_id"
            ].astype(str).isin(
                selected_product_ids
            )
        ].copy()
    )


if selected_performance_categories:
    filtered_performance = (
        filtered_performance[
            filtered_performance[
                "performance_category"
            ].isin(
                selected_performance_categories
            )
        ].copy()
    )


if (
    confidence_options
    and selected_confidence
):
    filtered_performance = (
        filtered_performance[
            filtered_performance[
                "data_confidence"
            ].astype(str).isin(
                selected_confidence
            )
        ].copy()
    )


if filtered_performance.empty:
    st.warning(
        "目前篩選條件下沒有活動資料。"
    )
    st.stop()


# =========================================================
# KPI
# =========================================================

st.divider()

st.subheader("活動成效概況")


activity_count = len(
    filtered_performance
)

high_count = int(
    (
        filtered_performance[
            "performance_category"
        ] == "高成效"
    ).sum()
)

low_count = int(
    (
        filtered_performance[
            "performance_category"
        ] == "低成效"
    ).sum()
)

median_uplift = (
    filtered_performance[
        "uplift_rate"
    ].median()
)

complete_rate = (
    filtered_performance[
        "all_periods_complete"
    ].mean()
    if (
        "all_periods_complete"
        in filtered_performance.columns
        and len(filtered_performance) > 0
    )
    else pd.NA
)


kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = (
    st.columns(5)
)

kpi_col1.metric(
    "活動數",
    f"{activity_count:,}",
)

kpi_col2.metric(
    "高成效活動",
    f"{high_count:,}",
)

kpi_col3.metric(
    "低成效活動",
    f"{low_count:,}",
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
    "完整觀察率",
    (
        f"{complete_rate:.1%}"
        if pd.notna(complete_rate)
        else "-"
    ),
)


# =========================================================
# 提升率排行
# =========================================================

st.divider()

ranking_col, distribution_col = st.columns(
    [2, 1]
)


with ranking_col:
    st.subheader("活動提升率排行")

    ranking_data = (
        filtered_performance.dropna(
            subset=["uplift_rate"]
        )
        .sort_values(
            "uplift_rate",
            ascending=False,
        )
        .copy()
    )

    if ranking_data.empty:
        st.info(
            "目前沒有可計算提升率的活動。"
        )

    else:
        ranking_maximum = min(
            20,
            len(ranking_data),
        )

        if ranking_maximum <= 1:
            top_n = 1

        else:
            top_n = st.slider(
                "顯示前幾名活動",
                min_value=1,
                max_value=ranking_maximum,
                value=min(
                    10,
                    ranking_maximum,
                ),
                key="product_activity_insight_top_n",
            )

        ranking_data = (
            ranking_data.head(top_n)
        )

        ranking_data[
            "uplift_percentage"
        ] = (
            ranking_data[
                "uplift_rate"
            ] * 100
        )

        ranking_figure = px.bar(
            ranking_data.sort_values(
                "uplift_percentage",
                ascending=True,
            ),
            x="uplift_percentage",
            y="activity_label",
            orientation="h",
            labels={
                "uplift_percentage": (
                    "活動提升率（%）"
                ),
                "activity_label": (
                    "商品活動"
                ),
            },
            hover_data={
                "campaign_total_sales": True,
                "data_confidence": True,
                "uplift_percentage": ":.1f",
            },
        )

        ranking_figure.update_layout(
            xaxis_title="活動提升率（%）",
            yaxis_title="",
            margin={
                "l": 10,
                "r": 10,
                "t": 10,
                "b": 10,
            },
        )

        st.plotly_chart(
            ranking_figure,
            use_container_width=True,
        )


with distribution_col:
    st.subheader("成效分類分布")

    distribution_dataframe = (
        filtered_performance[
            "performance_category"
        ]
        .value_counts()
        .rename_axis(
            "成效分類"
        )
        .reset_index(
            name="活動數"
        )
    )

    distribution_figure = px.bar(
        distribution_dataframe,
        x="成效分類",
        y="活動數",
        text_auto=True,
        labels={
            "成效分類": "成效分類",
            "活動數": "活動數",
        },
    )

    distribution_figure.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title="活動數",
        margin={
            "l": 10,
            "r": 10,
            "t": 10,
            "b": 10,
        },
    )

    st.plotly_chart(
        distribution_figure,
        use_container_width=True,
    )


# =========================================================
# 單一活動檢視
# =========================================================

st.divider()

st.subheader("單一活動檢視")


activity_selection_options = (
    filtered_performance[
        "activity_label"
    ]
    .dropna()
    .tolist()
)


with st.container(border=True):
    st.markdown(
        """
        <div class="analysis-filter-heading">
            <div class="analysis-filter-icon">🎯</div>
            <div>
                <div class="analysis-filter-title">選擇單一活動</div>
                <div class="analysis-filter-description">
                    查看指定商品活動的銷量、提升率與資料風險。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_activity_label = st.selectbox(
        "選擇要查看的商品活動",
        options=activity_selection_options,
    )


selected_activity = (
    filtered_performance[
        filtered_performance[
            "activity_label"
        ] == selected_activity_label
    ].iloc[0]
)


activity_start = selected_activity[
    "activity_start_date"
]

activity_end = selected_activity[
    "activity_end_date"
]

baseline_start = selected_activity.get(
    "baseline_start_date"
)

post_end = selected_activity.get(
    "post_end_date"
)


detail_col1, detail_col2, detail_col3, detail_col4 = (
    st.columns(4)
)


detail_col1.metric(
    "活動前平均日銷量",
    (
        f"{selected_activity['baseline_average_daily_sales']:,.1f}"
        if pd.notna(
            selected_activity[
                "baseline_average_daily_sales"
            ]
        )
        else "-"
    ),
)


detail_col2.metric(
    "活動期平均日銷量",
    (
        f"{selected_activity['campaign_average_daily_sales']:,.1f}"
        if pd.notna(
            selected_activity[
                "campaign_average_daily_sales"
            ]
        )
        else "-"
    ),
)


detail_col3.metric(
    "活動後平均日銷量",
    (
        f"{selected_activity['post_average_daily_sales']:,.1f}"
        if pd.notna(
            selected_activity[
                "post_average_daily_sales"
            ]
        )
        else "-"
    ),
)


detail_col4.metric(
    "活動提升率",
    (
        f"{selected_activity['uplift_rate']:.1%}"
        if pd.notna(
            selected_activity[
                "uplift_rate"
            ]
        )
        else "無法計算"
    ),
)


second_metric_col1, second_metric_col2, second_metric_col3 = (
    st.columns(3)
)


second_metric_col1.metric(
    "活動總銷量",
    (
        f"{selected_activity.get('campaign_total_sales', 0):,.0f}"
    ),
)


second_metric_col2.metric(
    "活動價格",
    (
        f"{selected_activity.get('campaign_price'):,.0f}"
        if pd.notna(
            selected_activity.get(
                "campaign_price"
            )
        )
        else "-"
    ),
)


second_metric_col3.metric(
    "推估營收",
    (
        f"{selected_activity.get('estimated_revenue'):,.0f}"
        if pd.notna(
            selected_activity.get(
                "estimated_revenue"
            )
        )
        else "-"
    ),
)


# =========================================================
# 單一活動每日趨勢
# =========================================================

if (
    integrated_dataframe is None
    or integrated_dataframe.empty
):
    st.info(
        "目前沒有每日整合資料，"
        "無法顯示單一活動趨勢圖。"
    )

else:
    integrated = integrated_dataframe.copy()

    integrated["sale_date"] = pd.to_datetime(
        integrated["sale_date"],
        errors="coerce",
    )

    integrated["product_id"] = (
        integrated["product_id"]
        .astype("string")
        .str.strip()
    )

    integrated["quantity"] = pd.to_numeric(
        integrated["quantity"],
        errors="coerce",
    )


    selected_product_id = str(
        selected_activity[
            "product_id"
        ]
    )


    if pd.isna(baseline_start):
        chart_start = activity_start

    else:
        chart_start = baseline_start


    if pd.isna(post_end):
        chart_end = activity_end

    else:
        chart_end = post_end


    trend_dataframe = integrated[
        (
            integrated["product_id"]
            == selected_product_id
        )
        & (
            integrated["sale_date"].between(
                chart_start,
                chart_end,
            )
        )
    ][
        [
            "sale_date",
            "quantity",
        ]
    ].copy()


    full_dates = pd.DataFrame(
        {
            "sale_date": pd.date_range(
                chart_start,
                chart_end,
                freq="D",
            )
        }
    )


    trend_dataframe = full_dates.merge(
        trend_dataframe,
        on="sale_date",
        how="left",
    )


    trend_dataframe["quantity"] = (
        trend_dataframe["quantity"]
        .fillna(0)
    )


    trend_dataframe["period"] = (
        "活動後"
    )

    trend_dataframe.loc[
        trend_dataframe["sale_date"]
        < activity_start,
        "period",
    ] = "活動前"

    trend_dataframe.loc[
        trend_dataframe[
            "sale_date"
        ].between(
            activity_start,
            activity_end,
        ),
        "period",
    ] = "活動期間"


    trend_figure = px.line(
        trend_dataframe,
        x="sale_date",
        y="quantity",
        color="period",
        markers=True,
        labels={
            "sale_date": "日期",
            "quantity": "銷量",
            "period": "期間",
        },
    )

    trend_figure.update_layout(
        xaxis_title="日期",
        yaxis_title="銷量",
        hovermode="x unified",
        margin={
            "l": 10,
            "r": 10,
            "t": 20,
            "b": 10,
        },
    )

    st.plotly_chart(
        trend_figure,
        use_container_width=True,
    )


# =========================================================
# 活動判讀資訊
# =========================================================

st.subheader("活動判讀資訊")


information_col1, information_col2 = st.columns(2)


with information_col1:
    st.write("**活動資料**")

    activity_information = pd.DataFrame(
        [
            {
                "項目": "商品編號",
                "內容": selected_activity.get(
                    "product_id"
                ),
            },
            {
                "項目": "商品名稱",
                "內容": selected_activity.get(
                    "product_name"
                ),
            },
            {
                "項目": "活動期間",
                "內容": (
                    f"{activity_start:%Y-%m-%d}"
                    f"～"
                    f"{activity_end:%Y-%m-%d}"
                ),
            },
            {
                "項目": "成效分類",
                "內容": selected_activity.get(
                    "performance_category"
                ),
            },
            {
                "項目": "資料信心",
                "內容": selected_activity.get(
                    "data_confidence"
                ),
            },
        ]
    )

    st.dataframe(
        activity_information,
        use_container_width=True,
        hide_index=True,
    )


with information_col2:
    st.write("**風險與限制**")

    risk_messages = []

    if not bool(
        selected_activity.get(
            "all_periods_complete",
            False,
        )
    ):
        risk_messages.append(
            "活動前、中、後觀察期間並不完整。"
        )

    if pd.isna(
        selected_activity.get(
            "uplift_rate"
        )
    ):
        risk_messages.append(
            "目前無法計算活動提升率，"
            "可能是活動前基準銷量為 0 或缺漏。"
        )

    if pd.notna(
        selected_activity.get(
            "overlapping_campaigns"
        )
    ):
        risk_messages.append(
            "活動期間存在其他平台或品牌活動重疊。"
        )

    if pd.notna(
        selected_activity.get(
            "overlapping_benefits"
        )
    ):
        risk_messages.append(
            "活動期間存在其他優惠重疊。"
        )

    if not risk_messages:
        st.success(
            "目前未發現明顯的活動判讀風險。"
        )

    else:
        for message in risk_messages:
            st.warning(message)


    overlapping_campaigns = (
        selected_activity.get(
            "overlapping_campaigns"
        )
    )

    overlapping_benefits = (
        selected_activity.get(
            "overlapping_benefits"
        )
    )


    if pd.notna(overlapping_campaigns):
        st.caption(
            "重疊活動："
            f"{overlapping_campaigns}"
        )

    if pd.notna(overlapping_benefits):
        st.caption(
            "重疊優惠："
            f"{overlapping_benefits}"
        )


# =========================================================
# 全部活動明細
# =========================================================

st.divider()

with st.expander(
    "查看篩選後的完整活動分析資料"
):
    display_columns = [
        "product_id",
        "product_name",
        "activity_start_date",
        "activity_end_date",
        "baseline_average_daily_sales",
        "campaign_average_daily_sales",
        "post_average_daily_sales",
        "campaign_total_sales",
        "uplift_rate",
        "post_change_rate",
        "estimated_revenue",
        "performance_category",
        "data_confidence",
        "all_periods_complete",
        "overlapping_campaigns",
        "overlapping_benefits",
    ]

    available_display_columns = [
        column
        for column in display_columns
        if column in filtered_performance.columns
    ]


    detail_dataframe = (
        filtered_performance[
            available_display_columns
        ].copy()
    )


    st.dataframe(
        detail_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "uplift_rate": (
                st.column_config.NumberColumn(
                    "活動提升率",
                    format="percent",
                )
            ),
            "post_change_rate": (
                st.column_config.NumberColumn(
                    "活動後變化率",
                    format="percent",
                )
            ),
            "estimated_revenue": (
                st.column_config.NumberColumn(
                    "推估營收",
                    format="%.0f",
                )
            ),
        },
    )