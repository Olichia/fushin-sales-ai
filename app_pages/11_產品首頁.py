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


from src.chart_theme import apply_chart_theme, get_category_color_map
from src.executive_summary import build_executive_brief_summary
from src.insight_cards import render_ai_insight_card
from src.persistence import load_state
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
CATEGORY_COLOR_MAP = get_category_color_map(dark_mode)


def dataframe_ready(dataframe) -> bool:
    """判斷 DataFrame 是否存在且有資料。"""

    return (
        isinstance(dataframe, pd.DataFrame)
        and not dataframe.empty
    )

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
        整合銷量、品牌活動、活動成效與策略建議，
        協助快速掌握目前資料狀態、重要商業洞察與待確認風險。
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

integrated_dataframe = st.session_state.get(
    "integrated_sales_activity_dataframe"
)

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)

strategy_dataframe = st.session_state.get(
    "strategy_report_dataframe"
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
# 本期摘要（首屏，只在活動單位分析已就緒時顯示；
# 沒有分析結果時頁面行為與改版前完全相同）
# =========================================================

if new_engine_ready:
    brief = build_executive_brief_summary(unit_overview_raw)

    with st.container(border=True):
        st.markdown(
            '<div class="output-card-label">本期摘要</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{brief['headline_text']}**")

    brief_kpi_col1, brief_kpi_col2, brief_kpi_col3, brief_kpi_col4 = (
        st.columns(4)
    )

    brief_kpi_col1.metric(
        "可分析活動數", f"{brief['total_units']:,}"
    )
    brief_kpi_col2.metric(
        "建議延續數", f"{brief['continue_count']:,}"
    )
    brief_kpi_col3.metric(
        "高風險活動數", f"{brief['risk_count']:,}"
    )
    brief_kpi_col4.metric(
        "待確認活動數", f"{brief['unclear_count']:,}"
    )

    render_ai_insight_card(
        finding=brief["insight_finding"],
        reason=brief["insight_reason"],
        action=brief["insight_action"],
        confidence=brief["insight_confidence"],
    )

    st.divider()


# =========================================================
# 資料流程狀態
# =========================================================

st.subheader("分析資料狀態")

sales_ready = (
    sales_dataframe is not None
    and not sales_dataframe.empty
    and bool(
        st.session_state.get(
            "sales_data_confirmed",
            False,
        )
    )
)

activity_ready = (
    activity_dataframe is not None
    and not activity_dataframe.empty
    and bool(
        st.session_state.get(
            "activity_data_confirmed",
            False,
        )
    )
)

analysis_ready = (
    integrated_dataframe is not None
    and performance_dataframe is not None
    and strategy_dataframe is not None
    and bool(
        st.session_state.get(
            "full_analysis_completed",
            False,
        )
    )
)

process_status = [
    {
        "編號": "01",
        "名稱": "銷量資料",
        "狀態": sales_ready,
    },
    {
        "編號": "02",
        "名稱": "活動資料",
        "狀態": activity_ready,
    },
    {
        "編號": "03",
        "名稱": "完整分析",
        "狀態": analysis_ready,
    },
]

status_columns = st.columns(3)

for column, item in zip(
    status_columns,
    process_status,
):
    with column:
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="overview-status-number">
                    STEP {item['編號']}
                </div>
                <div class="overview-status-title">
                    {item['名稱']}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if item["狀態"]:
                st.success("已完成")
            else:
                st.info("尚未完成")

completed_steps = sum(
    int(item["狀態"])
    for item in process_status
)

progress_ratio = (
    completed_steps
    / len(process_status)
)

st.progress(
    progress_ratio,
    text=(
        f"目前完成 {completed_steps}／"
        f"{len(process_status)} 個主要步驟"
    ),
)


# =========================================================
# 尚未完成完整流程時的提醒
# =========================================================

if not sales_ready:
    st.warning(
        "目前尚未完成銷量資料確認，"
        "請先前往「01 銷量資料處理」。"
    )

if not activity_ready:
    st.warning(
        "目前尚未完成活動資料確認，"
        "請先前往「02 活動資料處理」。"
    )

if sales_ready and activity_ready and not analysis_ready:
    st.info(
        "兩份資料都已確認，請前往「03 執行完整分析」"
        "產生整合資料、活動成效與策略報告。"
    )


# =========================================================
# KPI 計算
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

st.divider()

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
    st.caption(
        "目前銷量資料期間："
        f"{sales_date_start:%Y-%m-%d}"
        " 至 "
        f"{sales_date_end:%Y-%m-%d}"
    )


# =========================================================
# 每日銷量趨勢
#
# 「淨增益GMV合計」「風險檔數」原本在此處另有一組補充 KPI，
# 已併入上方「本期摘要」區塊（風險檔數＝高風險活動數），
# 避免同一頁面出現兩組意義重疊的 KPI。
# =========================================================

st.divider()

chart_col1, chart_col2 = st.columns(
    [2, 1]
)


with chart_col1:
    st.subheader("每日銷量趨勢")

    chart_sales_dataframe = sales_dataframe
    using_last_known_sales_data = False

    if chart_sales_dataframe is None or chart_sales_dataframe.empty:
        persisted_sales_dataframe = load_state(
            "standardized_dataframe"
        )

        if (
            isinstance(persisted_sales_dataframe, pd.DataFrame)
            and not persisted_sales_dataframe.empty
        ):
            chart_sales_dataframe = persisted_sales_dataframe
            using_last_known_sales_data = True

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
        if using_last_known_sales_data:
            st.caption(
                "⏳ 顯示上次已確認的銷量資料，"
                "尚未有本次新資料。"
            )

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


# =========================================================
# 活動成效分布
# =========================================================

with chart_col2:
    st.subheader("活動成效分布")

    if new_engine_ready:
        distribution_count = (
            unit_overview["color_category"]
            .value_counts()
            .rename_axis("成效分類")
            .reset_index(name="活動單位數")
        )

        distribution_figure = px.bar(
            distribution_count,
            x="成效分類",
            y="活動單位數",
            color="成效分類",
            color_discrete_map=CATEGORY_COLOR_MAP,
            text_auto=True,
            labels={
                "成效分類": "活動成效分類",
                "活動單位數": "活動單位數",
            },
        )

        distribution_figure.update_layout(
            xaxis_title="活動成效分類",
            yaxis_title="活動單位數",
            showlegend=False,
            margin={
                "l": 10,
                "r": 10,
                "t": 20,
                "b": 10,
            },
        )
        apply_chart_theme(distribution_figure, dark_mode)

        st.plotly_chart(
            distribution_figure,
            use_container_width=True,
        )

        st.caption(
            "分類依據與「活動洞察」「策略中心」一致："
            "可分離正向／不可分離／負增益。"
        )

    elif (
        performance_dataframe is None
        or performance_dataframe.empty
        or "uplift_rate"
        not in performance_dataframe.columns
    ):
        st.info(
            "完成活動成效分析後，"
            "這裡會顯示活動成效分布。"
        )

    else:
        performance_distribution = (
            performance_dataframe.copy()
        )

        performance_distribution[
            "uplift_rate"
        ] = pd.to_numeric(
            performance_distribution[
                "uplift_rate"
            ],
            errors="coerce",
        )

        performance_distribution[
            "成效分類"
        ] = "無法判定"

        performance_distribution.loc[
            performance_distribution[
                "uplift_rate"
            ] >= 0.20,
            "成效分類",
        ] = "高成效"

        performance_distribution.loc[
            (
                performance_distribution[
                    "uplift_rate"
                ] >= 0
            )
            & (
                performance_distribution[
                    "uplift_rate"
                ] < 0.20
            ),
            "成效分類",
        ] = "一般成效"

        performance_distribution.loc[
            performance_distribution[
                "uplift_rate"
            ] < 0,
            "成效分類",
        ] = "低成效"

        distribution_count = (
            performance_distribution[
                "成效分類"
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
            distribution_count,
            x="成效分類",
            y="活動數",
            text_auto=True,
            labels={
                "成效分類": "活動成效",
                "活動數": "活動數量",
            },
        )

        distribution_figure.update_layout(
            xaxis_title="活動成效",
            yaxis_title="活動數量",
            showlegend=False,
            margin={
                "l": 10,
                "r": 10,
                "t": 20,
                "b": 10,
            },
        )
        apply_chart_theme(distribution_figure, dark_mode)

        st.plotly_chart(
            distribution_figure,
            use_container_width=True,
        )


# =========================================================
# 最佳活動與風險提醒
# =========================================================

st.divider()

insight_col1, insight_col2 = st.columns(
    [1, 1]
)


with insight_col1:
    st.subheader("目前最佳活動")

    if new_engine_ready:
        best_unit_candidates = unit_overview.dropna(
            subset=["net_revenue_effect_per_day"]
        )

        if best_unit_candidates.empty:
            st.info("目前沒有可計算淨增益的活動單位。")

        else:
            best_unit = best_unit_candidates.sort_values(
                "net_revenue_effect_per_day",
                ascending=False,
            ).iloc[0]

            unit_product_id = best_unit.get(
                "product_id", "未提供編號"
            )

            unit_product_name = best_unit.get(
                "product_name", "未提供名稱"
            )

            if pd.isna(unit_product_name):
                unit_product_name = "未提供名稱"

            unit_start = pd.to_datetime(
                best_unit.get("start_date"), errors="coerce"
            )

            unit_end = pd.to_datetime(
                best_unit.get("end_date"), errors="coerce"
            )

            st.success(
                f"**{unit_product_id}｜{unit_product_name}**"
                f"（{best_unit.get('corresponding_activities_label', '')}）"
            )

            unit_metric_col1, unit_metric_col2 = st.columns(2)

            unit_metric_col1.metric(
                "淨增益/日",
                f"{best_unit['net_revenue_effect_per_day']:,.0f}",
            )

            unit_metric_col2.metric(
                "涵蓋天數",
                f"{best_unit.get('days', 0):,.0f}",
            )

            if pd.notna(unit_start) and pd.notna(unit_end):
                st.caption(
                    f"活動單位期間："
                    f"{unit_start:%Y-%m-%d}"
                    " 至 "
                    f"{unit_end:%Y-%m-%d}"
                )

            st.write(
                "建議進一步查看此活動單位是否可拆分歸因，"
                "再決定是否擴大執行或延伸至相似商品。"
            )

    elif (
        performance_dataframe is None
        or performance_dataframe.empty
        or "uplift_rate"
        not in performance_dataframe.columns
    ):
        st.info(
            "完成活動成效分析後，"
            "這裡會顯示最佳活動。"
        )

    else:
        best_activity_candidates = (
            performance_dataframe.copy()
        )

        best_activity_candidates[
            "uplift_rate"
        ] = pd.to_numeric(
            best_activity_candidates[
                "uplift_rate"
            ],
            errors="coerce",
        )

        best_activity_candidates = (
            best_activity_candidates.dropna(
                subset=[
                    "uplift_rate"
                ]
            )
        )

        if best_activity_candidates.empty:
            st.info(
                "目前沒有可計算提升率的活動。"
            )

        else:
            best_activity = (
                best_activity_candidates
                .sort_values(
                    "uplift_rate",
                    ascending=False,
                )
                .iloc[0]
            )

            product_id = best_activity.get(
                "product_id",
                "未提供編號",
            )

            product_name = best_activity.get(
                "product_name",
                "未提供名稱",
            )

            if pd.isna(product_name):
                product_name = (
                    "未提供名稱"
                )

            activity_start = (
                best_activity.get(
                    "activity_start_date"
                )
            )

            activity_end = (
                best_activity.get(
                    "activity_end_date"
                )
            )

            activity_start = (
                pd.to_datetime(
                    activity_start,
                    errors="coerce",
                )
            )

            activity_end = (
                pd.to_datetime(
                    activity_end,
                    errors="coerce",
                )
            )

            st.success(
                f"**{product_id}｜{product_name}**"
            )

            metric_col1, metric_col2 = (
                st.columns(2)
            )

            metric_col1.metric(
                "活動提升率",
                (
                    f"{best_activity['uplift_rate']:.1%}"
                ),
            )

            metric_col2.metric(
                "活動總銷量",
                (
                    f"{best_activity.get('campaign_total_sales', 0):,.0f}"
                ),
            )

            if (
                pd.notna(activity_start)
                and pd.notna(activity_end)
            ):
                st.caption(
                    f"活動期間："
                    f"{activity_start:%Y-%m-%d}"
                    " 至 "
                    f"{activity_end:%Y-%m-%d}"
                )

            st.write(
                "建議進一步查看此活動是否有"
                "其他平台活動或優惠重疊，"
                "再決定是否擴大執行。"
            )


with insight_col2:
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
        "📋 **查看策略中心**\n\n"
        "前往「策略中心」，"
        "查看建議延續、優化或檢討的活動。"
    )


with navigation_col3:
    st.info(
        "🤖 **詢問 AI 顧問**\n\n"
        "前往「AI 策略顧問」，"
        "詢問下一期促銷方向與資料限制。"
    )