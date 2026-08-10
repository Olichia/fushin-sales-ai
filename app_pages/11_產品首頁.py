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
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from src.chart_theme import apply_chart_theme
from src.session_helpers import initialize_session_state
from src.unit_overview_helpers import (
    compute_actual_revenue_total,
    compute_risk_mask,
    prepare_unit_overview_for_display,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

dark_mode = bool(st.session_state.get("dark_mode", False))


def dataframe_ready(dataframe) -> bool:
    """判斷 DataFrame 是否存在且有資料。"""

    return (
        isinstance(dataframe, pd.DataFrame)
        and not dataframe.empty
    )


def calculate_growth_rate(
    current_value: float,
    comparison_value: object,
) -> float | None:
    comparison = pd.to_numeric(
        comparison_value, errors="coerce"
    )

    if pd.isna(comparison) or float(comparison) == 0:
        return None

    return current_value / float(comparison) - 1

# =========================================================
# 頁面標題
# =========================================================

st.markdown(
    """
    <div class="step-label">ANALYTICS OVERVIEW</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>分析總覽</h1>
    </div>

    <p class="product-page-description">
        彙整銷量、品牌活動與活動成效資料，協助快速掌握業務規模、
        趨勢與待確認風險；AI 生成的策略建議請至「AI 策略中心」查看。
    </p>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 取得既有 Session State
# =========================================================

sales_dataframe = st.session_state.get(
    "standardized_dataframe"
)

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)

activity_dataframe = st.session_state.get(
    "activity_standardized_dataframe"
)

calendar_dataframe = st.session_state.get(
    "activity_calendar_dataframe"
)

benefits_dataframe = st.session_state.get(
    "promotion_benefits_dataframe"
)

activity_issues_dataframe = st.session_state.get(
    "activity_issues_dataframe"
)

integration_issues_dataframe = st.session_state.get(
    "integration_issues_dataframe"
)

unit_overview_raw = st.session_state.get(
    "activity_unit_overview_dataframe"
)

unit_analysis_completed = bool(
    st.session_state.get(
        "unit_analysis_completed",
        False,
    )
)

new_engine_ready = (
    unit_analysis_completed
    and dataframe_ready(unit_overview_raw)
)

if new_engine_ready:
    unit_overview = prepare_unit_overview_for_display(
        unit_overview_raw
    )
    unit_risk_mask = compute_risk_mask(unit_overview)
else:
    unit_overview = None
    unit_risk_mask = None


# =========================================================
# KPI 計算
#
# 資料流程狀態（01/02/03 是否完成）已併入「03 執行完整分析」
# 頂部的「目前進度」區塊，這裡不再重複顯示；本頁只負責資料
# 備妥後的業務規模、趨勢與風險呈現。
# =========================================================

total_quantity = 0
product_count = 0
sales_date_start = None
sales_date_end = None

if sales_dataframe is not None:
    sales = sales_dataframe.copy()

    if "quantity" in sales.columns:
        sales["quantity"] = pd.to_numeric(
            sales["quantity"],
            errors="coerce",
        )

        total_quantity = sales[
            "quantity"
        ].sum()

    if "product_id" in sales.columns:
        product_count = sales[
            "product_id"
        ].nunique()

    if "sale_date" in sales.columns:
        sales["sale_date"] = pd.to_datetime(
            sales["sale_date"],
            errors="coerce",
        )

        sales_date_start = sales[
            "sale_date"
        ].min()

        sales_date_end = sales[
            "sale_date"
        ].max()


activity_analysis_count = 0
complete_period_rate = pd.NA

if performance_dataframe is not None:
    performance = (
        performance_dataframe.copy()
    )

    activity_analysis_count = len(
        performance
    )

    if (
        "all_periods_complete"
        in performance.columns
        and len(performance) > 0
    ):
        complete_period_rate = (
            performance[
                "all_periods_complete"
            ]
            .fillna(False)
            .astype(bool)
            .mean()
        )


if new_engine_ready:
    total_gmv = compute_actual_revenue_total(
        unit_overview
    ).sum()
elif (
    performance_dataframe is not None
    and "estimated_revenue" in performance_dataframe.columns
):
    total_gmv = pd.to_numeric(
        performance_dataframe["estimated_revenue"],
        errors="coerce",
    ).sum()
else:
    total_gmv = 0


# =========================================================
# KPI 顯示
# =========================================================

st.subheader("整體概況")

kpi_col0, kpi_col1, kpi_col2, kpi_col3 = (
    st.columns(4)
)


kpi_col0.metric(
    "總GMV合計",
    f"{total_gmv:,.0f}",
)


kpi_col1.metric(
    "總銷量",
    f"{total_quantity:,.0f}",
)


kpi_col2.metric(
    "分析商品數",
    f"{product_count:,}",
)


kpi_col3.metric(
    "活動分析數",
    f"{activity_analysis_count:,}",
)


if (
    sales_date_start is not None
    and sales_date_end is not None
    and pd.notna(sales_date_start)
    and pd.notna(sales_date_end)
):
    with st.container(border=True):
        st.markdown(
            '<div class="output-card-label">資料期間</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f"**{sales_date_start:%Y-%m-%d} 至 {sales_date_end:%Y-%m-%d}**"
        )


# =========================================================
# 銷量趨勢（每日／月度）
# =========================================================

st.divider()

st.subheader("銷量趨勢")

daily_trend_tab, monthly_trend_tab = st.tabs(
    ["每日", "月度"]
)

with daily_trend_tab:
    chart_sales_dataframe = sales_dataframe

    if (
        chart_sales_dataframe is None
        or "sale_date"
        not in chart_sales_dataframe.columns
        or "quantity"
        not in chart_sales_dataframe.columns
    ):
        st.info(
            "完成銷量資料標準化後，"
            "這裡會顯示每日銷量趨勢。"
        )

    else:
        daily_sales = (
            chart_sales_dataframe.copy()
        )

        daily_sales["sale_date"] = (
            pd.to_datetime(
                daily_sales["sale_date"],
                errors="coerce",
            )
        )

        daily_sales["quantity"] = (
            pd.to_numeric(
                daily_sales["quantity"],
                errors="coerce",
            )
        )

        daily_sales = daily_sales.dropna(
            subset=[
                "sale_date",
                "quantity",
            ]
        )

        daily_sales = (
            daily_sales.groupby(
                "sale_date",
                as_index=False,
            )["quantity"]
            .sum()
            .sort_values(
                "sale_date"
            )
        )

        if daily_sales.empty:
            st.info(
                "目前沒有可顯示的銷量資料。"
            )

        else:
            sales_trend_figure = px.line(
                daily_sales,
                x="sale_date",
                y="quantity",
                markers=True,
                labels={
                    "sale_date": "日期",
                    "quantity": "銷量",
                },
            )

            sales_trend_figure.update_layout(
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
            apply_chart_theme(sales_trend_figure, dark_mode)

            st.plotly_chart(
                sales_trend_figure,
                use_container_width=True,
            )

with monthly_trend_tab:
    monthly_sales = pd.DataFrame()

    if (
        dataframe_ready(sales_dataframe)
        and {"sale_date", "quantity"}.issubset(
            sales_dataframe.columns
        )
    ):
        monthly_source = sales_dataframe[
            ["sale_date", "quantity"]
        ].copy()
        monthly_source["sale_date"] = pd.to_datetime(
            monthly_source["sale_date"], errors="coerce"
        )
        monthly_source["quantity"] = pd.to_numeric(
            monthly_source["quantity"], errors="coerce"
        )
        monthly_source = monthly_source.dropna(
            subset=["sale_date", "quantity"]
        )

        if not monthly_source.empty:
            monthly_source["sale_month"] = (
                monthly_source["sale_date"].dt.to_period("M")
            )
            monthly_sales = (
                monthly_source.groupby(
                    "sale_month", as_index=False
                )["quantity"]
                .sum()
                .rename(
                    columns={"quantity": "monthly_quantity"}
                )
                .sort_values("sale_month")
            )
            monthly_sales["month_label"] = (
                monthly_sales["sale_month"].astype(str)
            )

    if monthly_sales.empty:
        st.info(
            "完成銷量資料標準化後，"
            "這裡會顯示月銷量、MoM 與 YoY。"
        )
    else:
        latest_period = monthly_sales["sale_month"].max()
        previous_period = latest_period - 1
        previous_year_period = latest_period - 12
        monthly_lookup = monthly_sales.set_index(
            "sale_month"
        )["monthly_quantity"]
        latest_quantity = float(
            monthly_lookup.get(latest_period, 0)
        )
        previous_quantity = monthly_lookup.get(
            previous_period
        )
        previous_year_quantity = monthly_lookup.get(
            previous_year_period
        )
        mom_rate = calculate_growth_rate(
            latest_quantity, previous_quantity
        )
        yoy_rate = calculate_growth_rate(
            latest_quantity, previous_year_quantity
        )

        latest_column, mom_column, yoy_column = st.columns(3)
        latest_column.metric(
            f"{latest_period} 月銷量",
            f"{latest_quantity:,.0f}",
        )
        mom_column.metric(
            "MoM（月成長率）",
            f"{mom_rate:.1%}" if mom_rate is not None else "-",
        )
        yoy_column.metric(
            "YoY（年成長率）",
            f"{yoy_rate:.1%}" if yoy_rate is not None else "-",
        )

        monthly_figure = px.line(
            monthly_sales,
            x="month_label",
            y="monthly_quantity",
            markers=True,
            labels={
                "month_label": "月份",
                "monthly_quantity": "月銷量",
            },
        )
        monthly_figure.update_traces(
            line={"color": "#4E56A6", "width": 3},
            marker={"size": 9, "color": "#F45B1B"},
        )
        monthly_figure.update_layout(
            margin={"l": 10, "r": 10, "t": 24, "b": 10},
            height=360,
        )
        apply_chart_theme(monthly_figure, dark_mode)
        st.plotly_chart(monthly_figure, width="stretch")


# =========================================================
# 資料風險提醒
#
# 「目前最佳活動」卡已移除：與 AI 策略中心決策佇列的
# 「成長機會」分組重複，逐檔活動建議請至 AI 策略中心查看。
# 「活動成效分布」長條圖已移除：與 AI 策略中心決策佇列的
# 風險優先／成長機會／待補資料計數卡意義重疊。
# =========================================================

st.divider()

st.subheader("資料風險提醒")

risk_messages = []

if activity_issues_dataframe is not None:
    activity_issue_count = len(
        activity_issues_dataframe
    )

    if activity_issue_count > 0:
        risk_messages.append(
            f"活動標準化有 "
            f"{activity_issue_count} 筆待確認問題。"
        )

if integration_issues_dataframe is not None:
    integration_issue_count = len(
        integration_issues_dataframe
    )

    if integration_issue_count > 0:
        risk_messages.append(
            f"資料整合有 "
            f"{integration_issue_count} 筆待確認問題。"
        )

if pd.notna(complete_period_rate):
    if complete_period_rate < 1:
        risk_messages.append(
            "部分活動缺少完整的活動前、"
            "活動中或活動後觀察期間。"
        )

if performance_dataframe is not None:
    if (
        "overlapping_campaigns"
        in performance_dataframe.columns
        or "overlapping_benefits"
        in performance_dataframe.columns
    ):
        overlap_mask = pd.Series(
            False,
            index=performance_dataframe.index,
        )

        if (
            "overlapping_campaigns"
            in performance_dataframe.columns
        ):
            overlap_mask = (
                overlap_mask
                | performance_dataframe[
                    "overlapping_campaigns"
                ].notna()
            )

        if (
            "overlapping_benefits"
            in performance_dataframe.columns
        ):
            overlap_mask = (
                overlap_mask
                | performance_dataframe[
                    "overlapping_benefits"
                ].notna()
            )

        overlap_count = int(
            overlap_mask.sum()
        )

        if overlap_count > 0:
            risk_messages.append(
                f"共有 {overlap_count} 筆活動"
                "與其他活動或優惠重疊。"
            )

if new_engine_ready:
    unit_risk_count = int(unit_risk_mask.sum())

    if unit_risk_count > 0:
        risk_messages.append(
            f"有 {unit_risk_count} 檔活動單位存在"
            "毛利侵蝕風險（降價效應大於量增效應）。"
        )

if not risk_messages:
    st.success(
        "目前沒有偵測到明顯的資料風險。"
    )

else:
    for message in risk_messages:
        st.warning(message)

st.caption(
    "活動期間銷量上升不代表已證明因果；"
    "推估營收也不等於實際營收或獲利。"
)


# =========================================================
# 快速導覽說明
# =========================================================

st.divider()

st.subheader("接下來可以做什麼")

navigation_col1, navigation_col2, navigation_col3 = (
    st.columns(3)
)


with navigation_col1:
    st.info(
        "📈 **查看活動洞察**\n\n"
        "前往「活動洞察」，"
        "比較活動前、中、後的銷量變化。"
    )


with navigation_col2:
    st.info(
        "✨ **查看 AI 策略中心**\n\n"
        "前往「AI 策略中心」，查看首要建議、"
        "Decision Queue 與下一期規劃。"
    )


with navigation_col3:
    st.info(
        "🤖 **與 AI 討論策略**\n\n"
        "在「AI 策略中心」直接使用快捷問題，"
        "追問促銷方向、佐證與資料限制。"
    )
