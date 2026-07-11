from pathlib import Path
import sys

import pandas as pd
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

st.title("銷量與活動資料整合")

st.write(
    "本頁會將標準化銷量、商品活動價格、"
    "平台活動日曆與優惠內容整合成每日商品分析資料。"
)

st.warning(
    "目前同日同商品多筆銷量會直接加總；"
    "在企業確認資料粒度前，整合結果屬於初步分析。"
)


# =========================================================
# 取得標準化資料
# =========================================================

sales_dataframe = st.session_state.get(
    "standardized_dataframe"
)

main_activity_dataframe = st.session_state.get(
    "activity_standardized_dataframe"
)

calendar_dataframe = st.session_state.get(
    "activity_calendar_dataframe"
)

benefits_dataframe = st.session_state.get(
    "promotion_benefits_dataframe"
)


missing_sources = []

if sales_dataframe is None:
    missing_sources.append("標準化銷量資料")

if main_activity_dataframe is None:
    missing_sources.append("商品活動價格資料")

if calendar_dataframe is None:
    missing_sources.append("活動日曆資料")

if benefits_dataframe is None:
    missing_sources.append("優惠內容資料")


if missing_sources:
    st.error(
        "尚缺少："
        + "、".join(missing_sources)
        + "。請先完成前面的資料標準化流程。"
    )
    st.stop()


# =========================================================
# 共用清理函式
# =========================================================

def normalize_id(series: pd.Series) -> pd.Series:
    """
    將商品編號轉為乾淨文字。
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
    合併同一群組中的不重複文字。
    """

    cleaned_values = []

    for value in values.dropna():
        text = str(value).strip()

        if text and text not in cleaned_values:
            cleaned_values.append(text)

    if not cleaned_values:
        return None

    return "、".join(cleaned_values)


# =========================================================
# 銷量資料整理
# =========================================================

def prepare_daily_sales(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    將同日同商品銷量加總成每日商品粒度。
    """

    sales = dataframe.copy()

    sales["sale_date"] = pd.to_datetime(
        sales["sale_date"],
        errors="coerce",
    )

    sales["product_id"] = normalize_id(
        sales["product_id"]
    )

    sales["product_name"] = (
        sales["product_name"]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    sales["quantity"] = pd.to_numeric(
        sales["quantity"],
        errors="coerce",
    )

    sales = sales.dropna(
        subset=[
            "sale_date",
            "product_id",
            "quantity",
        ]
    ).copy()

    daily_sales = (
        sales.groupby(
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
            source_record_count=(
                "quantity",
                "size",
            ),
            had_exact_duplicate=(
                "exact_duplicate",
                "max",
            )
            if "exact_duplicate" in sales.columns
            else (
                "quantity",
                lambda series: False,
            ),
            had_same_day_multiple=(
                "same_day_product_multiple",
                "max",
            )
            if (
                "same_day_product_multiple"
                in sales.columns
            )
            else (
                "quantity",
                lambda series: False,
            ),
        )
    )

    return daily_sales


# =========================================================
# 商品活動價格整理
# =========================================================

def prepare_product_activity_days(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    將活動區間展開成每日商品活動資料。
    """

    activity = dataframe.copy()

    activity["product_id"] = normalize_id(
        activity["product_id"]
    )

    activity["activity_start_date"] = (
        pd.to_datetime(
            activity[
                "activity_start_date"
            ],
            errors="coerce",
        )
    )

    activity["activity_end_date"] = (
        pd.to_datetime(
            activity[
                "activity_end_date"
            ],
            errors="coerce",
        )
    )

    activity["campaign_price"] = (
        pd.to_numeric(
            activity[
                "campaign_price"
            ],
            errors="coerce",
        )
    )

    activity = activity.dropna(
        subset=[
            "product_id",
            "activity_start_date",
            "activity_end_date",
        ]
    ).copy()

    activity_records = []

    for row in activity.itertuples():
        if (
            row.activity_end_date
            < row.activity_start_date
        ):
            continue

        date_range = pd.date_range(
            row.activity_start_date,
            row.activity_end_date,
            freq="D",
        )

        for activity_date in date_range:
            activity_records.append(
                {
                    "sale_date": activity_date,
                    "product_id": (
                        row.product_id
                    ),
                    "campaign_price": (
                        row.campaign_price
                    ),
                    "activity_tag": getattr(
                        row,
                        "activity_tag",
                        None,
                    ),
                    "activity_gift": getattr(
                        row,
                        "activity_gift",
                        None,
                    ),
                    "bonus_gift_name": getattr(
                        row,
                        "bonus_gift_name",
                        None,
                    ),
                    "activity_source_file": (
                        getattr(
                            row,
                            "source_file",
                            None,
                        )
                    ),
                    "activity_source_row": (
                        getattr(
                            row,
                            "source_row_number",
                            None,
                        )
                    ),
                }
            )

    activity_days = pd.DataFrame(
        activity_records
    )

    if activity_days.empty:
        return activity_days

    activity_days = (
        activity_days.groupby(
            [
                "sale_date",
                "product_id",
            ],
            as_index=False,
        )
        .agg(
            campaign_price=(
                "campaign_price",
                "min",
            ),
            activity_tag=(
                "activity_tag",
                combine_unique_text,
            ),
            activity_gift=(
                "activity_gift",
                combine_unique_text,
            ),
            bonus_gift_name=(
                "bonus_gift_name",
                combine_unique_text,
            ),
            product_activity_count=(
                "product_id",
                "size",
            ),
        )
    )

    activity_days[
        "is_product_activity_day"
    ] = True

    return activity_days


# =========================================================
# 活動日曆整理
# =========================================================

def prepare_calendar_days(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    將平台或品牌活動區間展開成每日活動。
    """

    calendar = dataframe.copy()

    calendar["campaign_start_date"] = (
        pd.to_datetime(
            calendar[
                "campaign_start_date"
            ],
            errors="coerce",
        )
    )

    calendar["campaign_end_date"] = (
        pd.to_datetime(
            calendar[
                "campaign_end_date"
            ],
            errors="coerce",
        )
    )

    calendar = calendar.dropna(
        subset=[
            "campaign_start_date",
            "campaign_end_date",
        ]
    ).copy()

    calendar_records = []

    for row in calendar.itertuples():
        if (
            row.campaign_end_date
            < row.campaign_start_date
        ):
            continue

        date_range = pd.date_range(
            row.campaign_start_date,
            row.campaign_end_date,
            freq="D",
        )

        for campaign_date in date_range:
            calendar_records.append(
                {
                    "sale_date": campaign_date,
                    "campaign_name": getattr(
                        row,
                        "campaign_name",
                        None,
                    ),
                    "campaign_level": getattr(
                        row,
                        "campaign_level",
                        None,
                    ),
                }
            )

    calendar_days = pd.DataFrame(
        calendar_records
    )

    if calendar_days.empty:
        return calendar_days

    calendar_days = (
        calendar_days.groupby(
            "sale_date",
            as_index=False,
        )
        .agg(
            campaign_name=(
                "campaign_name",
                combine_unique_text,
            ),
            campaign_level=(
                "campaign_level",
                combine_unique_text,
            ),
            calendar_activity_count=(
                "campaign_name",
                "size",
            ),
        )
    )

    calendar_days[
        "is_calendar_activity_day"
    ] = True

    return calendar_days


# =========================================================
# 優惠內容整理
# =========================================================

def prepare_benefit_days(
    dataframe: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    將優惠區間展開。

    分成：
    1. 指定商品優惠
    2. 全站或品牌優惠
    """

    benefits = dataframe.copy()

    benefits["product_id"] = normalize_id(
        benefits["product_id"]
    )

    benefits["benefit_start_date"] = (
        pd.to_datetime(
            benefits[
                "benefit_start_date"
            ],
            errors="coerce",
        )
    )

    benefits["benefit_end_date"] = (
        pd.to_datetime(
            benefits[
                "benefit_end_date"
            ],
            errors="coerce",
        )
    )

    benefits = benefits.dropna(
        subset=[
            "benefit_start_date",
            "benefit_end_date",
        ]
    ).copy()

    product_benefit_records = []
    global_benefit_records = []

    for row in benefits.itertuples():
        if (
            row.benefit_end_date
            < row.benefit_start_date
        ):
            continue

        date_range = pd.date_range(
            row.benefit_start_date,
            row.benefit_end_date,
            freq="D",
        )

        for benefit_date in date_range:
            record = {
                "sale_date": benefit_date,
                "benefit_type": getattr(
                    row,
                    "benefit_type",
                    None,
                ),
                "benefit_content": getattr(
                    row,
                    "benefit_content",
                    None,
                ),
                "campaign_name": getattr(
                    row,
                    "campaign_name",
                    None,
                ),
                "threshold_amount": getattr(
                    row,
                    "threshold_amount",
                    None,
                ),
                "reward_percentage": getattr(
                    row,
                    "reward_percentage",
                    None,
                ),
                "reward_amount": getattr(
                    row,
                    "reward_amount",
                    None,
                ),
            }

            if pd.notna(row.product_id):
                record["product_id"] = (
                    row.product_id
                )

                product_benefit_records.append(
                    record
                )

            else:
                global_benefit_records.append(
                    record
                )

    product_benefits = pd.DataFrame(
        product_benefit_records
    )

    global_benefits = pd.DataFrame(
        global_benefit_records
    )

    if not product_benefits.empty:
        product_benefits = (
            product_benefits.groupby(
                [
                    "sale_date",
                    "product_id",
                ],
                as_index=False,
            )
            .agg(
                product_benefit_type=(
                    "benefit_type",
                    combine_unique_text,
                ),
                product_benefit_content=(
                    "benefit_content",
                    combine_unique_text,
                ),
                product_benefit_campaign=(
                    "campaign_name",
                    combine_unique_text,
                ),
                product_benefit_count=(
                    "benefit_type",
                    "size",
                ),
            )
        )

        product_benefits[
            "has_product_benefit"
        ] = True

    if not global_benefits.empty:
        global_benefits = (
            global_benefits.groupby(
                "sale_date",
                as_index=False,
            )
            .agg(
                global_benefit_type=(
                    "benefit_type",
                    combine_unique_text,
                ),
                global_benefit_content=(
                    "benefit_content",
                    combine_unique_text,
                ),
                global_benefit_campaign=(
                    "campaign_name",
                    combine_unique_text,
                ),
                global_benefit_count=(
                    "benefit_type",
                    "size",
                ),
            )
        )

        global_benefits[
            "has_global_benefit"
        ] = True

    return (
        product_benefits,
        global_benefits,
    )


# =========================================================
# 執行整合
# =========================================================

if st.button(
    "建立每日商品活動整合表",
    type="primary",
):
    try:
        with st.spinner(
            "正在展開日期並整合銷量與活動資料……"
        ):
            daily_sales = prepare_daily_sales(
                sales_dataframe
            )

            product_activity_days = (
                prepare_product_activity_days(
                    main_activity_dataframe
                )
            )

            calendar_days = (
                prepare_calendar_days(
                    calendar_dataframe
                )
            )

            (
                product_benefit_days,
                global_benefit_days,
            ) = prepare_benefit_days(
                benefits_dataframe
            )

            integrated = daily_sales.copy()

            if not product_activity_days.empty:
                integrated = integrated.merge(
                    product_activity_days,
                    on=[
                        "sale_date",
                        "product_id",
                    ],
                    how="left",
                )

            if not calendar_days.empty:
                integrated = integrated.merge(
                    calendar_days,
                    on="sale_date",
                    how="left",
                )

            if not product_benefit_days.empty:
                integrated = integrated.merge(
                    product_benefit_days,
                    on=[
                        "sale_date",
                        "product_id",
                    ],
                    how="left",
                )

            if not global_benefit_days.empty:
                integrated = integrated.merge(
                    global_benefit_days,
                    on="sale_date",
                    how="left",
                )

            boolean_columns = [
                "is_product_activity_day",
                "is_calendar_activity_day",
                "has_product_benefit",
                "has_global_benefit",
            ]

            for column in boolean_columns:
                if column not in integrated.columns:
                    integrated[column] = False
                else:
                    integrated[column] = (
                        integrated[column]
                        .fillna(False)
                        .astype(bool)
                    )

            integrated[
                "has_any_activity"
            ] = integrated[
                boolean_columns
            ].any(axis=1)

            integrated[
                "estimated_revenue"
            ] = (
                integrated["quantity"]
                * integrated["campaign_price"]
            )

            integrated = integrated.sort_values(
                by=[
                    "sale_date",
                    "product_id",
                ]
            ).reset_index(drop=True)

            integration_issues = integrated[
                (
                    integrated[
                        "is_product_activity_day"
                    ]
                )
                & (
                    integrated[
                        "campaign_price"
                    ].isna()
                )
            ].copy()

        st.session_state[
            "integrated_sales_activity_dataframe"
        ] = integrated

        st.session_state[
            "integration_issues_dataframe"
        ] = integration_issues

        st.success(
            "每日商品活動整合表建立完成。"
        )

    except Exception as error:
        st.error(
            f"資料整合失敗：{error}"
        )


# =========================================================
# 顯示結果
# =========================================================

integrated_dataframe = st.session_state.get(
    "integrated_sales_activity_dataframe"
)

integration_issues_dataframe = (
    st.session_state.get(
        "integration_issues_dataframe"
    )
)


if integrated_dataframe is None:
    st.info(
        "請按下「建立每日商品活動整合表」。"
    )
    st.stop()


st.divider()

st.subheader("整合結果摘要")


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "每日商品紀錄",
    len(integrated_dataframe),
)

col2.metric(
    "有活動紀錄",
    int(
        integrated_dataframe[
            "has_any_activity"
        ].sum()
    ),
)

col3.metric(
    "商品活動日",
    int(
        integrated_dataframe[
            "is_product_activity_day"
        ].sum()
    ),
)

col4.metric(
    "需確認資料",
    len(
        integration_issues_dataframe
    )
    if integration_issues_dataframe is not None
    else 0,
)


tab1, tab2, tab3 = st.tabs(
    [
        "整合資料",
        "有活動的資料",
        "待確認問題",
    ]
)


with tab1:
    st.dataframe(
        integrated_dataframe,
        use_container_width=True,
        hide_index=True,
    )


with tab2:
    activity_only = integrated_dataframe[
        integrated_dataframe[
            "has_any_activity"
        ]
    ].copy()

    st.dataframe(
        activity_only,
        use_container_width=True,
        hide_index=True,
    )


with tab3:
    if (
        integration_issues_dataframe is None
        or integration_issues_dataframe.empty
    ):
        st.success(
            "目前沒有發現商品活動日缺少活動價格的資料。"
        )

    else:
        st.warning(
            "以下商品在活動期間沒有可用活動價格，"
            "因此無法估算營收。"
        )

        st.dataframe(
            integration_issues_dataframe,
            use_container_width=True,
            hide_index=True,
        )


st.divider()

integrated_csv = (
    integrated_dataframe.to_csv(
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )
    .encode("utf-8-sig")
)


st.download_button(
    "下載每日商品活動整合資料",
    data=integrated_csv,
    file_name=(
        "daily_product_activity_integrated.csv"
    ),
    mime="text/csv",
)