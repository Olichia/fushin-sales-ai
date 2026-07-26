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

st.title("活動成效分析")

st.write(
    "本頁比較商品活動前、活動期間與活動後的銷量，"
    "並計算活動期間的銷量變化與資料完整度。"
)

st.warning(
    "目前結果只能描述活動期間與銷量變化的關聯，"
    "不能直接證明活動造成銷量提升。"
)


# =========================================================
# 取得資料
# =========================================================

integrated_dataframe = st.session_state.get(
    "integrated_sales_activity_dataframe"
)

activity_dataframe = st.session_state.get(
    "activity_standardized_dataframe"
)


missing_sources = []

if integrated_dataframe is None:
    missing_sources.append("每日商品活動整合資料")

if activity_dataframe is None:
    missing_sources.append("商品活動價格資料")


if missing_sources:
    st.error(
        "尚缺少："
        + "、".join(missing_sources)
        + "。請先完成「銷量活動整合」。"
    )
    st.stop()


integrated = integrated_dataframe.copy()
activities = activity_dataframe.copy()


# =========================================================
# 共用清理函式
# =========================================================

def normalize_product_id(
    series: pd.Series,
) -> pd.Series:
    """
    將商品編號轉成一致文字格式。
    """

    return (
        series.astype("string")
        .str.strip()
        .str.replace(
            r"\.0$",
            "",
            regex=True,
        )
        .replace("", pd.NA)
    )


def combine_unique_text(
    values: pd.Series,
) -> str | None:
    """
    合併不重複且非空白的文字。
    """

    results = []

    for value in values.dropna():
        text = str(value).strip()

        if text and text not in results:
            results.append(text)

    if not results:
        return None

    return "、".join(results)


def safe_percentage_change(
    current_value: float,
    baseline_value: float,
) -> float | None:
    """
    安全計算變化率。

    基準為 0 或空值時回傳 None。
    """

    if pd.isna(baseline_value):
        return None

    if baseline_value == 0:
        return None

    return (
        current_value - baseline_value
    ) / baseline_value


# =========================================================
# 整理每日銷量
# =========================================================

integrated["sale_date"] = pd.to_datetime(
    integrated["sale_date"],
    errors="coerce",
)

integrated["product_id"] = (
    normalize_product_id(
        integrated["product_id"]
    )
)

integrated["quantity"] = pd.to_numeric(
    integrated["quantity"],
    errors="coerce",
)

if "campaign_price" in integrated.columns:
    integrated["campaign_price"] = (
        pd.to_numeric(
            integrated["campaign_price"],
            errors="coerce",
        )
    )

integrated = integrated.dropna(
    subset=[
        "sale_date",
        "product_id",
        "quantity",
    ]
).copy()


daily_sales = (
    integrated.groupby(
        [
            "sale_date",
            "product_id",
        ],
        as_index=False,
    )
    .agg(
        product_name=(
            "product_name",
            combine_unique_text,
        ),
        quantity=(
            "quantity",
            "sum",
        ),
        campaign_price=(
            "campaign_price",
            "min",
        )
        if "campaign_price" in integrated.columns
        else (
            "quantity",
            lambda _: pd.NA,
        ),
        campaign_name=(
            "campaign_name",
            combine_unique_text,
        )
        if "campaign_name" in integrated.columns
        else (
            "quantity",
            lambda _: None,
        ),
        global_benefit_type=(
            "global_benefit_type",
            combine_unique_text,
        )
        if "global_benefit_type" in integrated.columns
        else (
            "quantity",
            lambda _: None,
        ),
        product_benefit_type=(
            "product_benefit_type",
            combine_unique_text,
        )
        if "product_benefit_type" in integrated.columns
        else (
            "quantity",
            lambda _: None,
        ),
    )
)


data_min_date = daily_sales["sale_date"].min()
data_max_date = daily_sales["sale_date"].max()


# =========================================================
# 整理活動資料
# =========================================================

activities["product_id"] = (
    normalize_product_id(
        activities["product_id"]
    )
)

activities["activity_start_date"] = (
    pd.to_datetime(
        activities["activity_start_date"],
        errors="coerce",
    )
)

activities["activity_end_date"] = (
    pd.to_datetime(
        activities["activity_end_date"],
        errors="coerce",
    )
)

activities["campaign_price"] = pd.to_numeric(
    activities["campaign_price"],
    errors="coerce",
)

activities = activities.dropna(
    subset=[
        "product_id",
        "activity_start_date",
        "activity_end_date",
    ]
).copy()

activities = activities[
    activities["activity_end_date"]
    >= activities["activity_start_date"]
].copy()


if activities.empty:
    st.error(
        "目前沒有可用的商品活動期間資料。"
    )
    st.stop()


# =========================================================
# 側邊欄設定
# =========================================================

st.sidebar.header("活動分析設定")

baseline_days = st.sidebar.number_input(
    "活動前基準天數",
    min_value=1,
    max_value=30,
    value=7,
    step=1,
)

post_days = st.sidebar.number_input(
    "活動後觀察天數",
    min_value=1,
    max_value=30,
    value=7,
    step=1,
)

fill_missing_dates_with_zero = (
    st.sidebar.checkbox(
        "沒有銷量紀錄的日期視為 0",
        value=True,
        help=(
            "若未出現的日期代表零銷量，建議勾選；"
            "若可能是資料缺失，應取消勾選。"
        ),
    )
)

require_complete_periods = (
    st.sidebar.checkbox(
        "排行榜只顯示完整觀察期間",
        value=True,
    )
)


# =========================================================
# 建立活動分析函式
# =========================================================

def get_period_daily_sales(
    product_id: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    fill_zero: bool,
) -> tuple[pd.DataFrame, int, int]:
    """
    取得指定商品與日期區間的每日銷量。

    回傳：
    1. 每日資料
    2. 預期日數
    3. 原始有紀錄日數
    """

    expected_dates = pd.date_range(
        start_date,
        end_date,
        freq="D",
    )

    product_period_sales = daily_sales[
        (
            daily_sales["product_id"]
            == product_id
        )
        & (
            daily_sales["sale_date"].between(
                start_date,
                end_date,
            )
        )
    ][
        [
            "sale_date",
            "quantity",
            "campaign_price",
            "campaign_name",
            "global_benefit_type",
            "product_benefit_type",
        ]
    ].copy()

    recorded_day_count = (
        product_period_sales[
            "sale_date"
        ].nunique()
    )

    if fill_zero:
        calendar_dataframe = pd.DataFrame(
            {
                "sale_date": expected_dates,
            }
        )

        product_period_sales = (
            calendar_dataframe.merge(
                product_period_sales,
                on="sale_date",
                how="left",
            )
        )

        product_period_sales["quantity"] = (
            product_period_sales["quantity"]
            .fillna(0)
        )

    return (
        product_period_sales,
        len(expected_dates),
        recorded_day_count,
    )


def calculate_activity_performance(
    activity_row: pd.Series,
) -> dict:
    """
    計算單一商品活動前、中、後的成效。
    """

    product_id = str(
        activity_row["product_id"]
    )

    activity_start = (
        activity_row[
            "activity_start_date"
        ]
    )

    activity_end = (
        activity_row[
            "activity_end_date"
        ]
    )

    baseline_start = (
        activity_start
        - pd.Timedelta(
            days=int(baseline_days)
        )
    )

    baseline_end = (
        activity_start
        - pd.Timedelta(days=1)
    )

    post_start = (
        activity_end
        + pd.Timedelta(days=1)
    )

    post_end = (
        activity_end
        + pd.Timedelta(
            days=int(post_days)
        )
    )

    (
        baseline_sales,
        baseline_expected_days,
        baseline_recorded_days,
    ) = get_period_daily_sales(
        product_id,
        baseline_start,
        baseline_end,
        fill_missing_dates_with_zero,
    )

    (
        campaign_sales,
        campaign_expected_days,
        campaign_recorded_days,
    ) = get_period_daily_sales(
        product_id,
        activity_start,
        activity_end,
        fill_missing_dates_with_zero,
    )

    (
        post_sales,
        post_expected_days,
        post_recorded_days,
    ) = get_period_daily_sales(
        product_id,
        post_start,
        post_end,
        fill_missing_dates_with_zero,
    )

    baseline_average = (
        baseline_sales["quantity"].mean()
        if not baseline_sales.empty
        else pd.NA
    )

    campaign_average = (
        campaign_sales["quantity"].mean()
        if not campaign_sales.empty
        else pd.NA
    )

    post_average = (
        post_sales["quantity"].mean()
        if not post_sales.empty
        else pd.NA
    )

    campaign_total = (
        campaign_sales["quantity"].sum()
        if not campaign_sales.empty
        else 0
    )

    uplift_rate = safe_percentage_change(
        campaign_average,
        baseline_average,
    )

    post_change_rate = (
        safe_percentage_change(
            post_average,
            campaign_average,
        )
    )

    baseline_complete = (
        baseline_start >= data_min_date
        and baseline_end <= data_max_date
    )

    campaign_complete = (
        activity_start >= data_min_date
        and activity_end <= data_max_date
    )

    post_complete = (
        post_start >= data_min_date
        and post_end <= data_max_date
    )

    all_periods_complete = (
        baseline_complete
        and campaign_complete
        and post_complete
    )

    campaign_price_values = (
        campaign_sales["campaign_price"]
        .dropna()
        if (
            not campaign_sales.empty
            and "campaign_price"
            in campaign_sales.columns
        )
        else pd.Series(dtype=float)
    )

    if not campaign_price_values.empty:
        effective_campaign_price = (
            campaign_price_values.min()
        )
    else:
        effective_campaign_price = (
            activity_row.get(
                "campaign_price",
                pd.NA,
            )
        )

    if pd.notna(effective_campaign_price):
        estimated_revenue = (
            campaign_total
            * effective_campaign_price
        )
    else:
        estimated_revenue = pd.NA

    overlapping_campaigns = (
        campaign_sales["campaign_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .unique()
        .tolist()
        if not campaign_sales.empty
        else []
    )

    overlapping_benefits = []

    if not campaign_sales.empty:
        for benefit_column in [
            "global_benefit_type",
            "product_benefit_type",
        ]:
            if benefit_column in campaign_sales.columns:
                values = (
                    campaign_sales[
                        benefit_column
                    ]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .unique()
                    .tolist()
                )

                for value in values:
                    if value not in overlapping_benefits:
                        overlapping_benefits.append(
                            value
                        )

    if all_periods_complete:
        data_confidence = "較高"
    elif campaign_complete:
        data_confidence = "中等"
    else:
        data_confidence = "較低"

    return {
        "product_id": product_id,
        "product_name": (
            activity_row.get(
                "product_name",
                None,
            )
        ),
        "activity_start_date": (
            activity_start
        ),
        "activity_end_date": activity_end,
        "activity_days": (
            activity_end
            - activity_start
        ).days + 1,
        "campaign_price": (
            effective_campaign_price
        ),
        "activity_tag": (
            activity_row.get(
                "activity_tag",
                None,
            )
        ),
        "activity_gift": (
            activity_row.get(
                "activity_gift",
                None,
            )
        ),
        "baseline_start_date": (
            baseline_start
        ),
        "baseline_end_date": (
            baseline_end
        ),
        "post_start_date": post_start,
        "post_end_date": post_end,
        "baseline_average_daily_sales": (
            baseline_average
        ),
        "campaign_average_daily_sales": (
            campaign_average
        ),
        "post_average_daily_sales": (
            post_average
        ),
        "campaign_total_sales": (
            campaign_total
        ),
        "uplift_rate": uplift_rate,
        "post_change_rate": (
            post_change_rate
        ),
        "estimated_revenue": (
            estimated_revenue
        ),
        "baseline_expected_days": (
            baseline_expected_days
        ),
        "baseline_recorded_days": (
            baseline_recorded_days
        ),
        "campaign_expected_days": (
            campaign_expected_days
        ),
        "campaign_recorded_days": (
            campaign_recorded_days
        ),
        "post_expected_days": (
            post_expected_days
        ),
        "post_recorded_days": (
            post_recorded_days
        ),
        "baseline_complete": (
            baseline_complete
        ),
        "campaign_complete": (
            campaign_complete
        ),
        "post_complete": post_complete,
        "all_periods_complete": (
            all_periods_complete
        ),
        "overlapping_campaigns": (
            "、".join(
                overlapping_campaigns
            )
            if overlapping_campaigns
            else None
        ),
        "overlapping_benefits": (
            "、".join(
                overlapping_benefits
            )
            if overlapping_benefits
            else None
        ),
        "data_confidence": (
            data_confidence
        ),
    }


# =========================================================
# 執行全部活動分析
# =========================================================

if st.button(
    "執行活動成效分析",
    type="primary",
):
    try:
        with st.spinner(
            "正在計算活動前、中、後銷量……"
        ):
            performance_records = []

            for _, activity_row in (
                activities.iterrows()
            ):
                performance_records.append(
                    calculate_activity_performance(
                        activity_row
                    )
                )

            performance_dataframe = (
                pd.DataFrame(
                    performance_records
                )
            )

            performance_dataframe = (
                performance_dataframe
                .sort_values(
                    by=[
                        "activity_start_date",
                        "product_id",
                    ]
                )
                .reset_index(drop=True)
            )

        st.session_state[
            "activity_performance_dataframe"
        ] = performance_dataframe

        st.success(
            "活動成效分析完成。"
        )

    except Exception as error:
        st.error(
            f"活動成效分析失敗：{error}"
        )


# =========================================================
# 顯示分析結果
# =========================================================

performance_dataframe = (
    st.session_state.get(
        "activity_performance_dataframe"
    )
)


if performance_dataframe is None:
    st.info(
        "請按下「執行活動成效分析」。"
    )
    st.stop()


if performance_dataframe.empty:
    st.warning(
        "沒有產生活動成效資料。"
    )
    st.stop()


# =========================================================
# 篩選完整資料
# =========================================================

ranking_dataframe = (
    performance_dataframe.copy()
)

if require_complete_periods:
    ranking_dataframe = (
        ranking_dataframe[
            ranking_dataframe[
                "all_periods_complete"
            ]
        ].copy()
    )


valid_uplift_dataframe = (
    ranking_dataframe.dropna(
        subset=["uplift_rate"]
    ).copy()
)


# =========================================================
# 整體 KPI
# =========================================================

st.divider()

st.subheader("活動分析摘要")

total_activities = len(
    performance_dataframe
)

complete_activities = int(
    performance_dataframe[
        "all_periods_complete"
    ].sum()
)

positive_uplift_count = int(
    (
        performance_dataframe[
            "uplift_rate"
        ] > 0
    ).sum()
)

median_uplift = (
    performance_dataframe[
        "uplift_rate"
    ].median()
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "活動分析筆數",
    f"{total_activities:,}",
)

col2.metric(
    "完整觀察期間",
    f"{complete_activities:,}",
)

col3.metric(
    "活動期銷量上升",
    f"{positive_uplift_count:,}",
)

col4.metric(
    "活動提升率中位數",
    (
        f"{median_uplift:.1%}"
        if pd.notna(median_uplift)
        else "-"
    ),
)


# =========================================================
# 分頁
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "提升率排行",
        "單一活動檢視",
        "全部分析結果",
        "資料限制",
    ]
)


# =========================================================
# 提升率排行
# =========================================================

with tab1:
    st.subheader("活動提升率排行")

    if valid_uplift_dataframe.empty:
        st.info(
            "目前沒有可計算提升率的完整資料。"
        )

    else:
        top_n_max = min(
            30,
            len(valid_uplift_dataframe),
        )

        if top_n_max <= 1:
            top_n = 1
        else:
            top_n = st.slider(
                "顯示前幾名活動",
                min_value=1,
                max_value=top_n_max,
                value=min(
                    10,
                    top_n_max,
                ),
                key="activity_ranking_top_n",
            )

        ranking_display = (
            valid_uplift_dataframe
            .sort_values(
                "uplift_rate",
                ascending=False,
            )
            .head(top_n)
            .copy()
        )

        ranking_display[
            "activity_label"
        ] = (
            ranking_display[
                "product_id"
            ].astype(str)
            + "｜"
            + ranking_display[
                "product_name"
            ].fillna(
                "未提供名稱"
            ).astype(str)
            + "｜"
            + ranking_display[
                "activity_start_date"
            ].dt.strftime(
                "%m/%d"
            )
        )

        ranking_display[
            "uplift_percentage"
        ] = (
            ranking_display[
                "uplift_rate"
            ] * 100
        )

        ranking_figure = px.bar(
            ranking_display.sort_values(
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
                "activity_label": "活動",
            },
        )

        ranking_figure.update_layout(
            xaxis_title="活動提升率（%）",
            yaxis_title="商品活動",
        )

        st.plotly_chart(
            ranking_figure,
            use_container_width=True,
        )

        display_columns = [
            "product_id",
            "product_name",
            "activity_start_date",
            "activity_end_date",
            "baseline_average_daily_sales",
            "campaign_average_daily_sales",
            "uplift_rate",
            "campaign_total_sales",
            "estimated_revenue",
            "data_confidence",
        ]

        ranking_table = (
            ranking_display[
                display_columns
            ].rename(
                columns={
                    "product_id": "商品編號",
                    "product_name": "商品名稱",
                    "activity_start_date": (
                        "活動開始日"
                    ),
                    "activity_end_date": (
                        "活動結束日"
                    ),
                    "baseline_average_daily_sales": (
                        "活動前平均日銷量"
                    ),
                    "campaign_average_daily_sales": (
                        "活動期平均日銷量"
                    ),
                    "uplift_rate": "活動提升率",
                    "campaign_total_sales": (
                        "活動總銷量"
                    ),
                    "estimated_revenue": (
                        "推估營收"
                    ),
                    "data_confidence": (
                        "資料信心"
                    ),
                }
            )
        )

        st.dataframe(
            ranking_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "活動提升率": (
                    st.column_config.NumberColumn(
                        format="%.1%%"
                    )
                ),
                "推估營收": (
                    st.column_config.NumberColumn(
                        format="%.0f"
                    )
                ),
            },
        )


# =========================================================
# 單一活動檢視
# =========================================================

with tab2:
    st.subheader("單一商品活動檢視")

    activity_options = (
        performance_dataframe.copy()
    )

    activity_options[
        "selection_label"
    ] = (
        activity_options[
            "product_id"
        ].astype(str)
        + "｜"
        + activity_options[
            "product_name"
        ].fillna(
            "未提供名稱"
        ).astype(str)
        + "｜"
        + activity_options[
            "activity_start_date"
        ].dt.strftime(
            "%Y-%m-%d"
        )
        + "～"
        + activity_options[
            "activity_end_date"
        ].dt.strftime(
            "%Y-%m-%d"
        )
    )

    selected_label = st.selectbox(
        "選擇商品活動",
        options=activity_options[
            "selection_label"
        ].tolist(),
    )

    selected_activity = (
        activity_options[
            activity_options[
                "selection_label"
            ] == selected_label
        ].iloc[0]
    )

    product_id = str(
        selected_activity[
            "product_id"
        ]
    )

    chart_start = (
        selected_activity[
            "baseline_start_date"
        ]
    )

    chart_end = (
        selected_activity[
            "post_end_date"
        ]
    )

    product_chart_sales = (
        daily_sales[
            (
                daily_sales[
                    "product_id"
                ] == product_id
            )
            & (
                daily_sales[
                    "sale_date"
                ].between(
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
    )

    full_chart_dates = pd.DataFrame(
        {
            "sale_date": pd.date_range(
                chart_start,
                chart_end,
                freq="D",
            )
        }
    )

    product_chart_sales = (
        full_chart_dates.merge(
            product_chart_sales,
            on="sale_date",
            how="left",
        )
    )

    if fill_missing_dates_with_zero:
        product_chart_sales[
            "quantity"
        ] = (
            product_chart_sales[
                "quantity"
            ].fillna(0)
        )

    activity_start = (
        selected_activity[
            "activity_start_date"
        ]
    )

    activity_end = (
        selected_activity[
            "activity_end_date"
        ]
    )

    product_chart_sales["period"] = (
        "活動後"
    )

    product_chart_sales.loc[
        product_chart_sales[
            "sale_date"
        ] < activity_start,
        "period",
    ] = "活動前"

    product_chart_sales.loc[
        product_chart_sales[
            "sale_date"
        ].between(
            activity_start,
            activity_end,
        ),
        "period",
    ] = "活動期間"

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
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

    col2.metric(
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

    col3.metric(
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

    col4.metric(
        "活動期總銷量",
        (
            f"{selected_activity['campaign_total_sales']:,.0f}"
        ),
    )

    trend_figure = px.line(
        product_chart_sales,
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
        hovermode="x unified",
        xaxis_title="日期",
        yaxis_title="銷量",
    )

    st.plotly_chart(
        trend_figure,
        use_container_width=True,
    )

    st.write("**活動與資料資訊**")

    detail_dataframe = pd.DataFrame(
        [
            {
                "項目": "商品編號",
                "內容": selected_activity[
                    "product_id"
                ],
            },
            {
                "項目": "商品名稱",
                "內容": selected_activity[
                    "product_name"
                ],
            },
            {
                "項目": "活動期間",
                "內容": (
                    f"{activity_start:%Y-%m-%d}"
                    f" ～ "
                    f"{activity_end:%Y-%m-%d}"
                ),
            },
            {
                "項目": "活動價格",
                "內容": selected_activity[
                    "campaign_price"
                ],
            },
            {
                "項目": "活動標籤",
                "內容": selected_activity[
                    "activity_tag"
                ],
            },
            {
                "項目": "重疊平台活動",
                "內容": selected_activity[
                    "overlapping_campaigns"
                ],
            },
            {
                "項目": "重疊優惠",
                "內容": selected_activity[
                    "overlapping_benefits"
                ],
            },
            {
                "項目": "資料信心",
                "內容": selected_activity[
                    "data_confidence"
                ],
            },
        ]
    )

    st.dataframe(
        detail_dataframe,
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# 全部結果
# =========================================================

with tab3:
    st.subheader("全部活動分析結果")

    st.dataframe(
        performance_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "uplift_rate": (
                st.column_config.NumberColumn(
                    "活動提升率",
                    format="%.1%%",
                )
            ),
            "post_change_rate": (
                st.column_config.NumberColumn(
                    "活動後變化率",
                    format="%.1%%",
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


# =========================================================
# 資料限制
# =========================================================

with tab4:
    st.subheader("資料限制與判讀原則")

    incomplete_dataframe = (
        performance_dataframe[
            ~performance_dataframe[
                "all_periods_complete"
            ]
        ].copy()
    )

    zero_baseline_dataframe = (
        performance_dataframe[
            performance_dataframe[
                "baseline_average_daily_sales"
            ].fillna(0) == 0
        ].copy()
    )

    overlap_dataframe = (
        performance_dataframe[
            performance_dataframe[
                "overlapping_campaigns"
            ].notna()
            | performance_dataframe[
                "overlapping_benefits"
            ].notna()
        ].copy()
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "觀察期間不完整",
        len(incomplete_dataframe),
    )

    col2.metric(
        "基準銷量為 0",
        len(zero_baseline_dataframe),
    )

    col3.metric(
        "存在重疊活動",
        len(overlap_dataframe),
    )

    st.markdown(
        """
        **判讀原則**

        1. 活動前平均為 0 時，不計算提升率。
        2. 活動後資料不足時，不應評估活動結束後效果。
        3. 活動期間若同時有平台檔期、折價券、平台幣或贈品，
           無法將銷量變化完全歸因於單一活動。
        4. 推估營收僅使用銷量乘以活動價，
           尚未納入退貨、實際成交價格、平台幣與贈品成本。
        5. 未出現的日期是否代表零銷量，仍需由企業確認。
        """
    )

    if not incomplete_dataframe.empty:
        st.write("**觀察期間不完整的活動**")

        st.dataframe(
            incomplete_dataframe[
                [
                    "product_id",
                    "product_name",
                    "activity_start_date",
                    "activity_end_date",
                    "baseline_complete",
                    "campaign_complete",
                    "post_complete",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# 下載
# =========================================================

st.divider()

performance_csv = (
    performance_dataframe.to_csv(
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )
    .encode("utf-8-sig")
)

st.download_button(
    "下載活動成效分析結果",
    data=performance_csv,
    file_name=(
        "activity_performance_analysis.csv"
    ),
    mime="text/csv",
)