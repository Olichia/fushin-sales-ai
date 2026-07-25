from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# =========================================================
# 完整分析設定
# =========================================================

@dataclass(frozen=True)
class AnalysisSettings:
    """完整分析使用的參數設定。"""

    baseline_days: int = 7
    post_days: int = 7
    fill_missing_dates_with_zero: bool = True

    high_uplift_threshold: float = 0.20
    low_uplift_threshold: float = 0.0
    minimum_campaign_sales: float = 1.0
    only_complete_periods: bool = True


# =========================================================
# 完整分析結果
# =========================================================

@dataclass
class AnalysisPipelineResult:
    """執行完整分析後回傳的所有結果。"""

    integrated_dataframe: pd.DataFrame
    integration_issues_dataframe: pd.DataFrame
    performance_dataframe: pd.DataFrame
    strategy_dataframe: pd.DataFrame
    strategy_report_text: str


# =========================================================
# 共用工具
# =========================================================

def normalize_product_id(series: pd.Series) -> pd.Series:
    """將商品編號轉成一致且乾淨的文字格式。"""

    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace("", pd.NA)
    )


def combine_unique_text(values: pd.Series) -> str | None:
    """合併同一群組中不重複且非空白的文字。"""

    results: list[str] = []

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
    """安全計算變化率；基準為零或空值時回傳 None。"""

    if pd.isna(baseline_value):
        return None

    if baseline_value == 0:
        return None

    return (current_value - baseline_value) / baseline_value


def format_percentage(value: object) -> str:
    """將數字格式化為百分比文字。"""

    if pd.isna(value):
        return "無法計算"

    return f"{float(value):.1%}"


def activity_label(row: pd.Series) -> str:
    """建立策略報告使用的商品活動標籤。"""

    product_id = str(row.get("product_id", "未提供編號"))

    product_name = row.get(
        "product_name",
        "未提供名稱",
    )

    if pd.isna(product_name):
        product_name = "未提供名稱"

    start_date = row.get("activity_start_date")
    end_date = row.get("activity_end_date")

    start_text = (
        start_date.strftime("%Y-%m-%d")
        if pd.notna(start_date)
        else "-"
    )

    end_text = (
        end_date.strftime("%Y-%m-%d")
        if pd.notna(end_date)
        else "-"
    )

    return (
        f"{product_id}｜{product_name}"
        f"｜{start_text}～{end_text}"
    )


# =========================================================
# 第一階段：銷量與活動資料整合
# =========================================================

def prepare_daily_sales(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """將同日同商品銷量加總成每日商品粒度。"""

    sales = dataframe.copy()

    required_columns = [
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in sales.columns
    ]

    if missing_columns:
        raise ValueError(
            "銷量資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    sales["sale_date"] = pd.to_datetime(
        sales["sale_date"],
        errors="coerce",
    )

    sales["product_id"] = normalize_product_id(
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

    if sales.empty:
        raise ValueError("銷量資料整理後沒有可使用的紀錄。")

    daily_sales = (
        sales.groupby(
            ["sale_date", "product_id"],
            as_index=False,
        )
        .agg(
            product_name=(
                "product_name",
                combine_unique_text,
            ),
            quantity=("quantity", "sum"),
            source_record_count=("quantity", "size"),
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
            if "same_day_product_multiple" in sales.columns
            else (
                "quantity",
                lambda series: False,
            ),
        )
    )

    return daily_sales


def prepare_product_activity_days(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """將商品活動區間展開成每日商品活動資料。"""

    activity = dataframe.copy()

    required_columns = [
        "product_id",
        "activity_start_date",
        "activity_end_date",
        "campaign_price",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in activity.columns
    ]

    if missing_columns:
        raise ValueError(
            "商品活動資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    activity["product_id"] = normalize_product_id(
        activity["product_id"]
    )

    activity["activity_start_date"] = pd.to_datetime(
        activity["activity_start_date"],
        errors="coerce",
    )

    activity["activity_end_date"] = pd.to_datetime(
        activity["activity_end_date"],
        errors="coerce",
    )

    activity["campaign_price"] = pd.to_numeric(
        activity["campaign_price"],
        errors="coerce",
    )

    activity = activity.dropna(
        subset=[
            "product_id",
            "activity_start_date",
            "activity_end_date",
        ]
    ).copy()

    activity_records: list[dict[str, object]] = []

    for row in activity.itertuples():
        if row.activity_end_date < row.activity_start_date:
            continue

        for activity_date in pd.date_range(
            row.activity_start_date,
            row.activity_end_date,
            freq="D",
        ):
            activity_records.append(
                {
                    "sale_date": activity_date,
                    "product_id": row.product_id,
                    "campaign_price": row.campaign_price,
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
                    "activity_source_file": getattr(
                        row,
                        "source_file",
                        None,
                    ),
                    "activity_source_row": getattr(
                        row,
                        "source_row_number",
                        None,
                    ),
                }
            )

    activity_days = pd.DataFrame(activity_records)

    if activity_days.empty:
        return activity_days

    activity_days = (
        activity_days.groupby(
            ["sale_date", "product_id"],
            as_index=False,
        )
        .agg(
            campaign_price=("campaign_price", "min"),
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
            product_activity_count=("product_id", "size"),
        )
    )

    activity_days["is_product_activity_day"] = True

    return activity_days


def prepare_calendar_days(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """將平台或品牌活動區間展開成每日活動。"""

    calendar = dataframe.copy()

    required_columns = [
        "campaign_start_date",
        "campaign_end_date",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in calendar.columns
    ]

    if missing_columns:
        raise ValueError(
            "活動日曆資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    calendar["campaign_start_date"] = pd.to_datetime(
        calendar["campaign_start_date"],
        errors="coerce",
    )

    calendar["campaign_end_date"] = pd.to_datetime(
        calendar["campaign_end_date"],
        errors="coerce",
    )

    calendar = calendar.dropna(
        subset=[
            "campaign_start_date",
            "campaign_end_date",
        ]
    ).copy()

    calendar_records: list[dict[str, object]] = []

    for row in calendar.itertuples():
        if row.campaign_end_date < row.campaign_start_date:
            continue

        for campaign_date in pd.date_range(
            row.campaign_start_date,
            row.campaign_end_date,
            freq="D",
        ):
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

    calendar_days = pd.DataFrame(calendar_records)

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
            calendar_activity_count=("campaign_name", "size"),
        )
    )

    calendar_days["is_calendar_activity_day"] = True

    return calendar_days


def prepare_benefit_days(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """將優惠區間展開為指定商品優惠與全站優惠。"""

    benefits = dataframe.copy()

    required_columns = [
        "product_id",
        "benefit_start_date",
        "benefit_end_date",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in benefits.columns
    ]

    if missing_columns:
        raise ValueError(
            "優惠內容資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    benefits["product_id"] = normalize_product_id(
        benefits["product_id"]
    )

    benefits["benefit_start_date"] = pd.to_datetime(
        benefits["benefit_start_date"],
        errors="coerce",
    )

    benefits["benefit_end_date"] = pd.to_datetime(
        benefits["benefit_end_date"],
        errors="coerce",
    )

    benefits = benefits.dropna(
        subset=[
            "benefit_start_date",
            "benefit_end_date",
        ]
    ).copy()

    product_benefit_records: list[dict[str, object]] = []
    global_benefit_records: list[dict[str, object]] = []

    for row in benefits.itertuples():
        if row.benefit_end_date < row.benefit_start_date:
            continue

        for benefit_date in pd.date_range(
            row.benefit_start_date,
            row.benefit_end_date,
            freq="D",
        ):
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
                record["product_id"] = row.product_id
                product_benefit_records.append(record)
            else:
                global_benefit_records.append(record)

    product_benefits = pd.DataFrame(product_benefit_records)
    global_benefits = pd.DataFrame(global_benefit_records)

    if not product_benefits.empty:
        product_benefits = (
            product_benefits.groupby(
                ["sale_date", "product_id"],
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
                product_benefit_count=("benefit_type", "size"),
            )
        )

        product_benefits["has_product_benefit"] = True

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
                global_benefit_count=("benefit_type", "size"),
            )
        )

        global_benefits["has_global_benefit"] = True

    return product_benefits, global_benefits


def build_integrated_data(
    sales_dataframe: pd.DataFrame,
    main_activity_dataframe: pd.DataFrame,
    calendar_dataframe: pd.DataFrame,
    benefits_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """建立每日商品活動整合資料與整合問題清單。"""

    if sales_dataframe is None:
        raise ValueError("缺少標準化銷量資料。")

    if main_activity_dataframe is None:
        raise ValueError("缺少商品活動價格資料。")

    if calendar_dataframe is None:
        raise ValueError("缺少活動日曆資料。")

    if benefits_dataframe is None:
        raise ValueError("缺少優惠內容資料。")

    daily_sales = prepare_daily_sales(sales_dataframe)

    product_activity_days = prepare_product_activity_days(
        main_activity_dataframe
    )

    calendar_days = prepare_calendar_days(calendar_dataframe)

    (
        product_benefit_days,
        global_benefit_days,
    ) = prepare_benefit_days(benefits_dataframe)

    integrated = daily_sales.copy()

    if not product_activity_days.empty:
        integrated = integrated.merge(
            product_activity_days,
            on=["sale_date", "product_id"],
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
            on=["sale_date", "product_id"],
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

    integrated["has_any_activity"] = integrated[
        boolean_columns
    ].any(axis=1)

    if "campaign_price" not in integrated.columns:
        integrated["campaign_price"] = pd.NA

    integrated["estimated_revenue"] = (
        integrated["quantity"]
        * integrated["campaign_price"]
    )

    integrated = integrated.sort_values(
        by=["sale_date", "product_id"]
    ).reset_index(drop=True)

    integration_issues = integrated[
        integrated["is_product_activity_day"]
        & integrated["campaign_price"].isna()
    ].copy()

    return integrated, integration_issues


# =========================================================
# 第二階段：活動成效分析
# =========================================================

def prepare_daily_performance_sales(
    integrated_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """整理活動成效分析使用的每日商品銷量。"""

    integrated = integrated_dataframe.copy()

    required_columns = [
        "sale_date",
        "product_id",
        "product_name",
        "quantity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in integrated.columns
    ]

    if missing_columns:
        raise ValueError(
            "整合資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    integrated["sale_date"] = pd.to_datetime(
        integrated["sale_date"],
        errors="coerce",
    )

    integrated["product_id"] = normalize_product_id(
        integrated["product_id"]
    )

    integrated["quantity"] = pd.to_numeric(
        integrated["quantity"],
        errors="coerce",
    )

    if "campaign_price" in integrated.columns:
        integrated["campaign_price"] = pd.to_numeric(
            integrated["campaign_price"],
            errors="coerce",
        )

    integrated = integrated.dropna(
        subset=[
            "sale_date",
            "product_id",
            "quantity",
        ]
    ).copy()

    if integrated.empty:
        raise ValueError("整合資料整理後沒有可使用的銷量紀錄。")

    daily_sales = (
        integrated.groupby(
            ["sale_date", "product_id"],
            as_index=False,
        )
        .agg(
            product_name=(
                "product_name",
                combine_unique_text,
            ),
            quantity=("quantity", "sum"),
            campaign_price=("campaign_price", "min")
            if "campaign_price" in integrated.columns
            else ("quantity", lambda _: pd.NA),
            campaign_name=(
                "campaign_name",
                combine_unique_text,
            )
            if "campaign_name" in integrated.columns
            else ("quantity", lambda _: None),
            global_benefit_type=(
                "global_benefit_type",
                combine_unique_text,
            )
            if "global_benefit_type" in integrated.columns
            else ("quantity", lambda _: None),
            product_benefit_type=(
                "product_benefit_type",
                combine_unique_text,
            )
            if "product_benefit_type" in integrated.columns
            else ("quantity", lambda _: None),
        )
    )

    return daily_sales


def prepare_activity_periods(
    activity_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """整理可供成效分析使用的商品活動期間。"""

    activities = activity_dataframe.copy()

    required_columns = [
        "product_id",
        "activity_start_date",
        "activity_end_date",
        "campaign_price",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in activities.columns
    ]

    if missing_columns:
        raise ValueError(
            "商品活動資料缺少必要欄位："
            + "、".join(missing_columns)
        )

    activities["product_id"] = normalize_product_id(
        activities["product_id"]
    )

    activities["activity_start_date"] = pd.to_datetime(
        activities["activity_start_date"],
        errors="coerce",
    )

    activities["activity_end_date"] = pd.to_datetime(
        activities["activity_end_date"],
        errors="coerce",
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
        raise ValueError("目前沒有可用的商品活動期間資料。")

    return activities


def get_period_daily_sales(
    daily_sales: pd.DataFrame,
    product_id: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    fill_zero: bool,
) -> tuple[pd.DataFrame, int, int]:
    """取得指定商品與日期區間的每日銷量。"""

    expected_dates = pd.date_range(
        start_date,
        end_date,
        freq="D",
    )

    required_output_columns = [
        "sale_date",
        "quantity",
        "campaign_price",
        "campaign_name",
        "global_benefit_type",
        "product_benefit_type",
    ]

    period_source = daily_sales.copy()

    for column in required_output_columns:
        if column not in period_source.columns:
            period_source[column] = pd.NA

    product_period_sales = period_source[
        (period_source["product_id"] == product_id)
        & period_source["sale_date"].between(
            start_date,
            end_date,
        )
    ][required_output_columns].copy()

    recorded_day_count = product_period_sales[
        "sale_date"
    ].nunique()

    if fill_zero:
        calendar_dataframe = pd.DataFrame(
            {"sale_date": expected_dates}
        )

        product_period_sales = calendar_dataframe.merge(
            product_period_sales,
            on="sale_date",
            how="left",
        )

        product_period_sales["quantity"] = (
            product_period_sales["quantity"].fillna(0)
        )

    return (
        product_period_sales,
        len(expected_dates),
        int(recorded_day_count),
    )


def calculate_activity_performance(
    activity_row: pd.Series,
    daily_sales: pd.DataFrame,
    data_min_date: pd.Timestamp,
    data_max_date: pd.Timestamp,
    settings: AnalysisSettings,
) -> dict[str, object]:
    """計算單一商品活動前、中、後的成效。"""

    product_id = str(activity_row["product_id"])
    activity_start = activity_row["activity_start_date"]
    activity_end = activity_row["activity_end_date"]

    baseline_start = activity_start - pd.Timedelta(
        days=int(settings.baseline_days)
    )
    baseline_end = activity_start - pd.Timedelta(days=1)

    post_start = activity_end + pd.Timedelta(days=1)
    post_end = activity_end + pd.Timedelta(
        days=int(settings.post_days)
    )

    (
        baseline_sales,
        baseline_expected_days,
        baseline_recorded_days,
    ) = get_period_daily_sales(
        daily_sales,
        product_id,
        baseline_start,
        baseline_end,
        settings.fill_missing_dates_with_zero,
    )

    (
        campaign_sales,
        campaign_expected_days,
        campaign_recorded_days,
    ) = get_period_daily_sales(
        daily_sales,
        product_id,
        activity_start,
        activity_end,
        settings.fill_missing_dates_with_zero,
    )

    (
        post_sales,
        post_expected_days,
        post_recorded_days,
    ) = get_period_daily_sales(
        daily_sales,
        product_id,
        post_start,
        post_end,
        settings.fill_missing_dates_with_zero,
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

    post_change_rate = safe_percentage_change(
        post_average,
        campaign_average,
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
        campaign_sales["campaign_price"].dropna()
        if (
            not campaign_sales.empty
            and "campaign_price" in campaign_sales.columns
        )
        else pd.Series(dtype=float)
    )

    if not campaign_price_values.empty:
        effective_campaign_price = campaign_price_values.min()
    else:
        effective_campaign_price = activity_row.get(
            "campaign_price",
            pd.NA,
        )

    if pd.notna(effective_campaign_price):
        estimated_revenue = (
            campaign_total * effective_campaign_price
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

    overlapping_benefits: list[str] = []

    if not campaign_sales.empty:
        for benefit_column in [
            "global_benefit_type",
            "product_benefit_type",
        ]:
            if benefit_column in campaign_sales.columns:
                values = (
                    campaign_sales[benefit_column]
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
                        overlapping_benefits.append(value)

    if all_periods_complete:
        data_confidence = "較高"
    elif campaign_complete:
        data_confidence = "中等"
    else:
        data_confidence = "較低"

    return {
        "product_id": product_id,
        "product_name": activity_row.get(
            "product_name",
            None,
        ),
        "activity_start_date": activity_start,
        "activity_end_date": activity_end,
        "activity_days": (
            activity_end - activity_start
        ).days
        + 1,
        "campaign_price": effective_campaign_price,
        "activity_tag": activity_row.get(
            "activity_tag",
            None,
        ),
        "activity_gift": activity_row.get(
            "activity_gift",
            None,
        ),
        "baseline_start_date": baseline_start,
        "baseline_end_date": baseline_end,
        "post_start_date": post_start,
        "post_end_date": post_end,
        "baseline_average_daily_sales": baseline_average,
        "campaign_average_daily_sales": campaign_average,
        "post_average_daily_sales": post_average,
        "campaign_total_sales": campaign_total,
        "uplift_rate": uplift_rate,
        "post_change_rate": post_change_rate,
        "estimated_revenue": estimated_revenue,
        "baseline_expected_days": baseline_expected_days,
        "baseline_recorded_days": baseline_recorded_days,
        "campaign_expected_days": campaign_expected_days,
        "campaign_recorded_days": campaign_recorded_days,
        "post_expected_days": post_expected_days,
        "post_recorded_days": post_recorded_days,
        "baseline_complete": baseline_complete,
        "campaign_complete": campaign_complete,
        "post_complete": post_complete,
        "all_periods_complete": all_periods_complete,
        "overlapping_campaigns": (
            "、".join(overlapping_campaigns)
            if overlapping_campaigns
            else None
        ),
        "overlapping_benefits": (
            "、".join(overlapping_benefits)
            if overlapping_benefits
            else None
        ),
        "data_confidence": data_confidence,
    }


def analyze_activity_performance(
    integrated_dataframe: pd.DataFrame,
    activity_dataframe: pd.DataFrame,
    settings: AnalysisSettings | None = None,
) -> pd.DataFrame:
    """計算所有商品活動的前、中、後成效。"""

    settings = settings or AnalysisSettings()

    if settings.baseline_days < 1:
        raise ValueError("活動前基準天數至少需要 1 天。")

    if settings.post_days < 1:
        raise ValueError("活動後觀察天數至少需要 1 天。")

    daily_sales = prepare_daily_performance_sales(
        integrated_dataframe
    )

    activities = prepare_activity_periods(
        activity_dataframe
    )

    data_min_date = daily_sales["sale_date"].min()
    data_max_date = daily_sales["sale_date"].max()

    performance_records = [
        calculate_activity_performance(
            activity_row=activity_row,
            daily_sales=daily_sales,
            data_min_date=data_min_date,
            data_max_date=data_max_date,
            settings=settings,
        )
        for _, activity_row in activities.iterrows()
    ]

    performance_dataframe = pd.DataFrame(
        performance_records
    )

    if performance_dataframe.empty:
        return performance_dataframe

    performance_dataframe = (
        performance_dataframe.sort_values(
            by=[
                "activity_start_date",
                "product_id",
            ]
        ).reset_index(drop=True)
    )

    return performance_dataframe


# =========================================================
# 第三階段：策略建議報告
# =========================================================

def prepare_performance_dataframe(
    performance_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """整理策略報告需要的資料型別。"""

    performance = performance_dataframe.copy()

    date_columns = [
        "activity_start_date",
        "activity_end_date",
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

    return performance


def generate_strategy_report(
    performance_dataframe: pd.DataFrame,
    settings: AnalysisSettings | None = None,
) -> tuple[pd.DataFrame, str]:
    """依照活動成效結果產生策略資料表與文字報告。"""

    settings = settings or AnalysisSettings()

    if performance_dataframe is None:
        raise ValueError("缺少活動成效分析結果。")

    if performance_dataframe.empty:
        raise ValueError("目前沒有可產生策略報告的活動資料。")

    performance = prepare_performance_dataframe(
        performance_dataframe
    )

    required_columns = [
        "all_periods_complete",
        "uplift_rate",
        "campaign_total_sales",
        "baseline_average_daily_sales",
        "post_change_rate",
        "overlapping_campaigns",
        "overlapping_benefits",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in performance.columns
    ]

    if missing_columns:
        raise ValueError(
            "成效分析資料缺少策略報告必要欄位："
            + "、".join(missing_columns)
        )

    analysis_base = performance.copy()

    if settings.only_complete_periods:
        analysis_base = analysis_base[
            analysis_base["all_periods_complete"]
        ].copy()

    valid_uplift = analysis_base.dropna(
        subset=["uplift_rate"]
    ).copy()

    high_performance = valid_uplift[
        (
            valid_uplift["uplift_rate"]
            >= settings.high_uplift_threshold
        )
        & (
            valid_uplift["campaign_total_sales"]
            >= settings.minimum_campaign_sales
        )
    ].copy()

    low_performance = valid_uplift[
        valid_uplift["uplift_rate"]
        < settings.low_uplift_threshold
    ].copy()

    stable_performance = valid_uplift[
        (
            valid_uplift["uplift_rate"]
            >= settings.low_uplift_threshold
        )
        & (
            valid_uplift["uplift_rate"]
            < settings.high_uplift_threshold
        )
    ].copy()

    incomplete_periods = performance[
        ~performance["all_periods_complete"]
    ].copy()

    zero_or_missing_baseline = performance[
        performance[
            "baseline_average_daily_sales"
        ].isna()
        | (
            performance[
                "baseline_average_daily_sales"
            ]
            == 0
        )
    ].copy()

    overlap_risk = performance[
        performance["overlapping_campaigns"].notna()
        | performance["overlapping_benefits"].notna()
    ].copy()

    post_decline = performance[
        performance["post_change_rate"] < -0.20
    ].copy()

    strategy_rows: list[dict[str, object]] = []

    for _, row in high_performance.iterrows():
        strategy_rows.append(
            {
                "策略分類": "建議延續",
                "商品活動": activity_label(row),
                "活動提升率": row["uplift_rate"],
                "活動總銷量": row[
                    "campaign_total_sales"
                ],
                "推估營收": row.get("estimated_revenue"),
                "資料信心": row.get("data_confidence"),
                "建議": (
                    "保留此活動機制，"
                    "並測試擴大曝光、增加庫存"
                    "或延伸至相似商品。"
                ),
            }
        )

    for _, row in low_performance.iterrows():
        strategy_rows.append(
            {
                "策略分類": "建議檢討",
                "商品活動": activity_label(row),
                "活動提升率": row["uplift_rate"],
                "活動總銷量": row[
                    "campaign_total_sales"
                ],
                "推估營收": row.get("estimated_revenue"),
                "資料信心": row.get("data_confidence"),
                "建議": (
                    "檢查活動價格、曝光位置、"
                    "商品吸引力、庫存與重疊優惠，"
                    "不建議直接照原方案延續。"
                ),
            }
        )

    for _, row in stable_performance.iterrows():
        strategy_rows.append(
            {
                "策略分類": "建議優化",
                "商品活動": activity_label(row),
                "活動提升率": row["uplift_rate"],
                "活動總銷量": row[
                    "campaign_total_sales"
                ],
                "推估營收": row.get("estimated_revenue"),
                "資料信心": row.get("data_confidence"),
                "建議": (
                    "活動有一定效果但未達高成效門檻，"
                    "可透過優惠門檻、活動文案"
                    "或曝光時間進行小幅測試。"
                ),
            }
        )

    strategy_dataframe = pd.DataFrame(strategy_rows)

    total_count = len(performance)
    complete_count = int(
        performance["all_periods_complete"].sum()
    )

    high_count = len(high_performance)
    low_count = len(low_performance)
    stable_count = len(stable_performance)

    median_uplift = valid_uplift["uplift_rate"].median()

    report_lines = [
        "# 策略建議報表",
        "",
        "## 一、分析摘要",
        "",
        f"- 共分析 {total_count} 筆商品活動。",
        f"- 完整前、中、後觀察期間：{complete_count} 筆。",
        f"- 高成效活動：{high_count} 筆。",
        f"- 一般成效活動：{stable_count} 筆。",
        f"- 低成效活動：{low_count} 筆。",
        (
            "- 可計算活動的提升率中位數："
            f"{format_percentage(median_uplift)}。"
        ),
        "",
        "## 二、策略建議",
        "",
    ]

    if high_performance.empty:
        report_lines.append(
            "- 目前沒有符合高成效門檻且資料完整的活動。"
        )
    else:
        report_lines.append(
            "- 建議延續高提升率且活動總銷量具規模的活動，"
            "並測試擴大曝光、備貨或套用至相似商品。"
        )

    if low_performance.empty:
        report_lines.append(
            "- 目前沒有低於低成效門檻的完整活動。"
        )
    else:
        report_lines.append(
            "- 低成效活動應優先檢查定價、曝光、庫存、"
            "商品適配與活動重疊，不建議直接複製原方案。"
        )

    if not post_decline.empty:
        report_lines.append(
            "- 部分活動結束後銷量明顯下降，"
            "可能存在需求提前透支，"
            "後續應評估活動頻率與間隔。"
        )

    if not overlap_risk.empty:
        report_lines.append(
            "- 多筆活動與平台檔期或其他優惠重疊，"
            "目前無法將效果完全歸因於單一活動。"
        )

    report_lines.extend(
        [
            "",
            "## 三、資料限制",
            "",
            (
                "- 觀察期間不完整："
                f"{len(incomplete_periods)} 筆。"
            ),
            (
                "- 基準銷量為 0 或缺漏："
                f"{len(zero_or_missing_baseline)} 筆。"
            ),
            (
                "- 存在重疊活動或優惠："
                f"{len(overlap_risk)} 筆。"
            ),
            "- 推估營收未納入實際成交折扣、退貨、平台幣與贈品成本。",
            "- 本報告描述活動期間的銷量變化，不代表已證明因果關係。",
        ]
    )

    strategy_report_text = "\n".join(report_lines)

    return strategy_dataframe, strategy_report_text


# =========================================================
# 完整三階段流程
# =========================================================

def run_full_analysis(
    sales_dataframe: pd.DataFrame,
    main_activity_dataframe: pd.DataFrame,
    calendar_dataframe: pd.DataFrame,
    benefits_dataframe: pd.DataFrame,
    settings: AnalysisSettings | None = None,
) -> AnalysisPipelineResult:
    """依序執行資料整合、成效分析與策略報告。"""

    settings = settings or AnalysisSettings()

    (
        integrated_dataframe,
        integration_issues_dataframe,
    ) = build_integrated_data(
        sales_dataframe=sales_dataframe,
        main_activity_dataframe=main_activity_dataframe,
        calendar_dataframe=calendar_dataframe,
        benefits_dataframe=benefits_dataframe,
    )

    performance_dataframe = analyze_activity_performance(
        integrated_dataframe=integrated_dataframe,
        activity_dataframe=main_activity_dataframe,
        settings=settings,
    )

    (
        strategy_dataframe,
        strategy_report_text,
    ) = generate_strategy_report(
        performance_dataframe=performance_dataframe,
        settings=settings,
    )

    return AnalysisPipelineResult(
        integrated_dataframe=integrated_dataframe,
        integration_issues_dataframe=(
            integration_issues_dataframe
        ),
        performance_dataframe=performance_dataframe,
        strategy_dataframe=strategy_dataframe,
        strategy_report_text=strategy_report_text,
    )