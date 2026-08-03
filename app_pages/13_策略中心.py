from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 專案路徑
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.executive_summary import build_activity_unit_strategy_text
from src.session_helpers import initialize_session_state
from src.unit_overview_helpers import (
    compute_confidence_label,
    compute_risk_mask,
    compute_strategy_category,
    prepare_unit_overview_for_display,
)


def dataframe_ready(dataframe) -> bool:
    """判斷 DataFrame 是否存在且有資料。"""

    return (
        isinstance(dataframe, pd.DataFrame)
        and not dataframe.empty
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
        整理建議延續、持續觀察／優化與建議檢討的活動。
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
# 新引擎策略清單（活動單位分析）
#
# 有新引擎資料時，策略清單改用活動單位分析的結果重新組出，
# 取代上面舊版 uplift_rate 門檻分類。策略分類規則：淨增益
# 為負一律是建議檢討；非負值時，達全體活動單位中位數以上
# 為建議延續，未達中位數為持續觀察
# （compute_strategy_category()）。
# =========================================================

unit_overview_raw = st.session_state.get(
    "activity_unit_overview_dataframe"
)

waterfall_summary_raw = st.session_state.get(
    "activity_waterfall_summary_dataframe"
)

unit_analysis_completed = bool(
    st.session_state.get("unit_analysis_completed", False)
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
    unit_confidence_label = compute_confidence_label(
        unit_overview
    )

    strategy = unit_overview.copy()

    strategy["策略分類"] = compute_strategy_category(strategy)

    strategy["商品活動"] = (
        strategy["product_name"].astype(str)
        + "｜"
        + strategy["unit_code"].astype(str)
        + "（"
        + strategy["corresponding_activities_label"]
        + "）"
    )

    strategy["活動總銷量(估)"] = (
        strategy["unit_avg_sales"] * strategy["days"]
    )

    strategy["淨增益/日"] = strategy["net_revenue_effect_per_day"]
    strategy["淨增益合計"] = strategy["net_revenue_effect_total"]
    strategy["資料信心"] = unit_confidence_label

    def build_unit_suggestion(color_category: str, is_risky: bool) -> str:
        if color_category == "可分離正向":
            return (
                "此活動單位淨增益為正且效果可獨立歸因，"
                "可考慮延續此折扣／贈品組合，"
                "並測試擴大曝光或延伸至相似商品。"
            )

        if color_category == "不可分離":
            return (
                "此活動單位疊加了多個活動，"
                "效果無法拆分歸因到單一活動，"
                "建議下次測試時錯開檔期，"
                "才能確認真正有效的組合。"
            )

        if is_risky:
            return (
                "此活動單位淨增益為負，"
                "且降價效應大於量增效應，屬於毛利侵蝕風險，"
                "建議下檔縮減折扣或改以贈品吸引轉換。"
            )

        return (
            "此活動單位淨增益為負，"
            "建議檢視商品吸引力、曝光位置或活動設計，"
            "不建議直接延續原方案。"
        )

    strategy["建議"] = [
        build_unit_suggestion(color_category, is_risky)
        for color_category, is_risky in zip(
            strategy["color_category"], unit_risk_mask
        )
    ]

    strategy = strategy[
        [
            "策略分類",
            "商品活動",
            "淨增益/日",
            "活動總銷量(估)",
            "淨增益合計",
            "資料信心",
            "建議",
        ]
    ]

    primary_metric_column = "淨增益/日"
    primary_metric_label = "淨增益/日 中位數"
    primary_metric_is_percent = False
    volume_column = "活動總銷量(估)"
    revenue_column = "淨增益合計"
    revenue_label = "淨增益合計"

else:
    primary_metric_column = "活動提升率"
    primary_metric_label = "提升率中位數"
    primary_metric_is_percent = True
    volume_column = "活動總銷量"
    revenue_column = "推估營收"
    revenue_label = "推估營收合計"


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
            f"最低{volume_column}",
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
        volume_column
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


if new_engine_ready:
    middle_eyebrow = "OBSERVE"
    middle_title = "持續觀察"
    middle_description = (
        "淨增益為正但未達整體中位數，建議持續觀察後續表現。"
    )
else:
    middle_eyebrow = "OPTIMIZE"
    middle_title = "建議優化"
    middle_description = (
        "調整優惠、價格、期間或商品組合後再次測試。"
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
        ] == middle_title
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
    primary_metric_column
].median()

total_estimated_revenue = filtered_strategy[
    revenue_column
].sum(
    min_count=1
)


strategy_card_col1, strategy_card_col2, strategy_card_col3 = (
    st.columns(3)
)

card_specs = [
    (
        strategy_card_col1,
        "CONTINUE",
        "建議延續",
        continue_count,
        "優先保留成效較佳、資料可信度較高的活動。",
    ),
    (
        strategy_card_col2,
        middle_eyebrow,
        middle_title,
        optimize_count,
        middle_description,
    ),
    (
        strategy_card_col3,
        "REVIEW",
        "建議檢討",
        review_count,
        "檢視活動設計、重疊優惠與資料完整性。",
    ),
]

for column, eyebrow, title, count, description in card_specs:
    with column:
        with st.container(border=True):
            st.caption(eyebrow)
            st.metric(title, f"{count:,}")
            st.caption(description)


kpi_col4, kpi_col5 = st.columns(2)

kpi_col4.metric(
    primary_metric_label,
    (
        (
            f"{median_uplift:.1%}"
            if primary_metric_is_percent
            else f"{median_uplift:,.0f}"
        )
        if pd.notna(median_uplift)
        else "-"
    ),
)

kpi_col5.metric(
    revenue_label,
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

    product_mom_source = standardized_dataframe[
        ["sale_date", "product_id", "product_name", "quantity"]
    ].copy()

    product_mom_source["sale_date"] = pd.to_datetime(
        product_mom_source["sale_date"], errors="coerce"
    )

    product_mom_source["quantity"] = pd.to_numeric(
        product_mom_source["quantity"], errors="coerce"
    )

    product_mom_source = product_mom_source.dropna(
        subset=["sale_date", "product_id", "quantity"]
    )

    product_mom_source["sale_month"] = (
        product_mom_source["sale_date"].dt.to_period("M")
    )

    monthly_by_product = (
        product_mom_source.groupby(
            ["product_id", "product_name", "sale_month"],
            as_index=False,
        )["quantity"].sum()
    )

    latest_by_product = monthly_by_product[
        monthly_by_product["sale_month"] == latest_period
    ].set_index("product_id")["quantity"]

    previous_by_product = monthly_by_product[
        monthly_by_product["sale_month"] == previous_period
    ].set_index("product_id")["quantity"]

    product_names = (
        monthly_by_product[["product_id", "product_name"]]
        .drop_duplicates()
        .set_index("product_id")["product_name"]
    )

    product_mom = pd.DataFrame(
        {"product_name": product_names}
    ).reset_index()

    product_mom["latest_quantity"] = product_mom[
        "product_id"
    ].map(latest_by_product)

    product_mom["previous_quantity"] = product_mom[
        "product_id"
    ].map(previous_by_product)

    product_mom["mom_rate"] = product_mom.apply(
        lambda row: calculate_growth_rate(
            row["latest_quantity"], row["previous_quantity"]
        ),
        axis=1,
    )

    product_mom_chart_data = product_mom.dropna(
        subset=["latest_quantity", "mom_rate"]
    ).sort_values("mom_rate")

    if product_mom_chart_data.empty:
        st.info(
            "目前沒有足夠的品項月銷量資料可比較 MoM。"
        )
    else:
        mom_bar_figure = go.Figure(
            go.Bar(
                x=product_mom_chart_data["mom_rate"] * 100,
                y=product_mom_chart_data["product_name"],
                orientation="h",
                marker_color=[
                    "#3BA776" if rate >= 0 else "#D64550"
                    for rate in product_mom_chart_data["mom_rate"]
                ],
                text=[
                    f"銷量 {quantity:,.0f}（{rate:+.1%}）"
                    for quantity, rate in zip(
                        product_mom_chart_data["latest_quantity"],
                        product_mom_chart_data["mom_rate"],
                    )
                ],
                textposition="outside",
            )
        )

        mom_bar_figure.update_layout(
            xaxis_title="MoM 月增率（%）",
            yaxis_title="品項",
            margin={
                "l": 10,
                "r": 10,
                "t": 20,
                "b": 10,
            },
            height=max(280, 60 * len(product_mom_chart_data)),
        )

        st.plotly_chart(
            mom_bar_figure,
            use_container_width=True,
        )

        st.caption(
            f"比較 {previous_period} 與 {latest_period} "
            "各品項銷量計算 MoM。"
        )


# =========================================================
# 活動提升率與總銷量圖
# =========================================================

st.divider()

st.subheader("活動成效與銷量對照")


chart_dataframe = filtered_strategy.dropna(
    subset=[
        primary_metric_column,
        volume_column,
    ]
).copy()


if chart_dataframe.empty:
    st.info(
        "目前沒有足夠資料繪製活動成效圖。"
    )

elif primary_metric_is_percent:
    chart_dataframe[
        "活動提升率百分比"
    ] = (
        chart_dataframe[
            primary_metric_column
        ] * 100
    )

    strategy_scatter_figure = px.scatter(
        chart_dataframe,
        x=volume_column,
        y="活動提升率百分比",
        color="策略分類",
        hover_name="商品活動",
        hover_data={
            revenue_column: ":,.0f",
            "資料信心": True,
            "活動提升率百分比": ":.1f",
        },
        labels={
            volume_column: volume_column,
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

    # 許多活動單位座標完全重疊（例如活動總銷量估計值都是0），
    # 預設不透明的點會互相遮蔽，改成半透明＋外框線，重疊處
    # 會自然顯示成顏色較深/較密的區塊，不更動任何資料本身。
    strategy_scatter_figure.update_traces(
        marker={
            "opacity": 0.65,
            "line": {"width": 1, "color": "rgba(0,0,0,0.35)"},
        }
    )

    strategy_scatter_figure.update_layout(
        xaxis_title=volume_column,
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

else:
    median_metric_value = chart_dataframe[
        primary_metric_column
    ].median()

    strategy_scatter_figure = px.scatter(
        chart_dataframe,
        x=volume_column,
        y=primary_metric_column,
        color="策略分類",
        hover_name="商品活動",
        hover_data={
            revenue_column: ":,.0f",
            "資料信心": True,
            primary_metric_column: ":,.0f",
        },
        labels={
            volume_column: volume_column,
            primary_metric_column: primary_metric_column,
            "策略分類": "策略分類",
        },
    )

    if pd.notna(median_metric_value):
        strategy_scatter_figure.add_hline(
            y=median_metric_value,
            line_dash="dot",
            annotation_text=f"{primary_metric_column} 中位數",
        )

    # 許多活動單位座標完全重疊（例如活動總銷量估計值都是0），
    # 預設不透明的點會互相遮蔽，改成半透明＋外框線，重疊處
    # 會自然顯示成顏色較深/較密的區塊，不更動任何資料本身。
    strategy_scatter_figure.update_traces(
        marker={
            "opacity": 0.65,
            "line": {"width": 1, "color": "rgba(0,0,0,0.35)"},
        }
    )

    strategy_scatter_figure.update_layout(
        xaxis_title=volume_column,
        yaxis_title=primary_metric_column,
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
        "右上方通常代表估算銷量較高且淨增益較高；"
        "淨增益已扣除同月安靜期基準，"
        "但沒有毛利與成本資料時，不能直接解讀為實際獲利。"
    )


# =========================================================
# 活動策略清單
# =========================================================

st.divider()

st.subheader("活動策略清單")

strategy_table_column_config = {
    primary_metric_column: st.column_config.NumberColumn(
        format="percent" if primary_metric_is_percent else "%.0f"
    ),
    volume_column: st.column_config.NumberColumn(format="%.0f"),
    revenue_column: st.column_config.NumberColumn(format="%.0f"),
}

st.dataframe(
    filtered_strategy,
    use_container_width=True,
    hide_index=True,
    column_config=strategy_table_column_config,
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

if new_engine_ready and dataframe_ready(waterfall_summary_raw):
    management_strategy_text = build_activity_unit_strategy_text(
        unit_overview_raw, waterfall_summary_raw
    )

else:
    management_strategy_text = strategy_report_text

    st.caption(
        "新版活動單位分析資料尚未就緒，暫時顯示舊版"
        "活動前後比較方法論產生的文字報告。"
    )

if management_strategy_text:
    with st.expander(
        "展開完整文字報告",
        expanded=False,
    ):
        st.markdown(
            management_strategy_text
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
    if management_strategy_text:
        st.download_button(
            "下載策略文字報告",
            data=management_strategy_text.encode(
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