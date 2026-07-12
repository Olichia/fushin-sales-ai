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

st.set_page_config(
    page_title="策略中心",
    page_icon="📋",
    layout="wide",
)

st.title("策略中心")

st.write(
    "根據活動成效分析與規則式策略報告，"
    "整理建議延續、建議優化與建議檢討的活動。"
)

st.caption(
    "策略分類屬於決策輔助；"
    "實際執行仍應搭配成本、毛利、庫存與商業目標判斷。"
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


if strategy_dataframe is None:
    st.warning(
        "尚未產生策略建議資料。"
        "請先完成「策略建議報表」。"
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
# 三類策略卡片
# =========================================================

st.divider()

st.subheader("策略行動清單")


continue_tab, optimize_tab, review_tab = st.tabs(
    [
        "建議延續",
        "建議優化",
        "建議檢討",
    ]
)


def display_strategy_cards(
    dataframe: pd.DataFrame,
    empty_message: str,
) -> None:
    """
    以卡片形式顯示策略資料。
    """

    if dataframe.empty:
        st.info(empty_message)
        return

    sorted_dataframe = dataframe.sort_values(
        "活動提升率",
        ascending=False,
        na_position="last",
    )

    for _, row in sorted_dataframe.iterrows():
        with st.container(border=True):
            st.markdown(
                f"### {row['商品活動']}"
            )

            metric_col1, metric_col2, metric_col3 = (
                st.columns(3)
            )

            metric_col1.metric(
                "活動提升率",
                (
                    f"{row['活動提升率']:.1%}"
                    if pd.notna(
                        row["活動提升率"]
                    )
                    else "-"
                ),
            )

            metric_col2.metric(
                "活動總銷量",
                (
                    f"{row['活動總銷量']:,.0f}"
                    if pd.notna(
                        row["活動總銷量"]
                    )
                    else "-"
                ),
            )

            metric_col3.metric(
                "推估營收",
                (
                    f"{row['推估營收']:,.0f}"
                    if pd.notna(
                        row["推估營收"]
                    )
                    else "-"
                ),
            )

            st.write(
                f"**資料信心：** "
                f"{row['資料信心']}"
            )

            st.write(
                f"**建議：** "
                f"{row['建議']}"
            )


with continue_tab:
    continue_dataframe = filtered_strategy[
        filtered_strategy[
            "策略分類"
        ] == "建議延續"
    ].copy()

    display_strategy_cards(
        continue_dataframe,
        "目前沒有符合條件的建議延續活動。",
    )


with optimize_tab:
    optimize_dataframe = filtered_strategy[
        filtered_strategy[
            "策略分類"
        ] == "建議優化"
    ].copy()

    display_strategy_cards(
        optimize_dataframe,
        "目前沒有符合條件的建議優化活動。",
    )


with review_tab:
    review_dataframe = filtered_strategy[
        filtered_strategy[
            "策略分類"
        ] == "建議檢討"
    ].copy()

    display_strategy_cards(
        review_dataframe,
        "目前沒有符合條件的建議檢討活動。",
    )


# =========================================================
# 完整策略清單
# =========================================================

st.divider()

with st.expander(
    "查看完整策略建議表"
):
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
    "可前往「AI 行銷策略顧問」進行提問。"
)