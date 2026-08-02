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
from src.analysis_pipeline import (
    AnalysisSettings,
    generate_strategy_report,
)


# =========================================================
# 初始化
# =========================================================

initialize_session_state()

st.title("策略建議報表")

st.write(
    "本頁根據活動成效分析結果，"
    "整理高效活動、低效活動、資料風險與下一期建議。"
)

st.warning(
    "目前建議由明確規則產生，"
    "用於決策輔助，不代表因果推論或最終商業決策。"
)


# =========================================================
# 取得資料
# =========================================================

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)

if performance_dataframe is None:
    st.error(
        "尚未產生活動成效分析結果。"
        "請先完成「活動成效分析」。"
    )
    st.stop()


performance = performance_dataframe.copy()

if performance.empty:
    st.warning("目前沒有可產生策略報告的活動資料。")
    st.stop()


# =========================================================
# 型別整理
# =========================================================

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


# =========================================================
# 共用函式
# =========================================================

def format_percentage(value) -> str:
    if pd.isna(value):
        return "無法計算"

    return f"{value:.1%}"


def format_number(value) -> str:
    if pd.isna(value):
        return "-"

    return f"{value:,.0f}"


def activity_label(row: pd.Series) -> str:
    product_id = str(
        row.get("product_id", "未提供編號")
    )

    product_name = row.get(
        "product_name",
        "未提供名稱",
    )

    if pd.isna(product_name):
        product_name = "未提供名稱"

    start_date = row.get(
        "activity_start_date"
    )

    end_date = row.get(
        "activity_end_date"
    )

    if pd.notna(start_date):
        start_text = start_date.strftime(
            "%Y-%m-%d"
        )
    else:
        start_text = "-"

    if pd.notna(end_date):
        end_text = end_date.strftime(
            "%Y-%m-%d"
        )
    else:
        end_text = "-"

    return (
        f"{product_id}｜{product_name}"
        f"｜{start_text}～{end_text}"
    )


# =========================================================
# 分析設定
# =========================================================

st.sidebar.header("策略判斷設定")

high_uplift_threshold = (
    st.sidebar.number_input(
        "高成效門檻",
        min_value=0.0,
        max_value=5.0,
        value=0.20,
        step=0.05,
        help="0.20 代表活動期平均日銷量提升 20%。",
    )
)

low_uplift_threshold = (
    st.sidebar.number_input(
        "低成效門檻",
        min_value=-5.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
        help="低於此數值的活動會列入需檢討活動。",
    )
)

minimum_campaign_sales = (
    st.sidebar.number_input(
        "最低活動總銷量門檻",
        min_value=0.0,
        value=1.0,
        step=1.0,
    )
)

only_complete_periods = (
    st.sidebar.checkbox(
        "主要建議只使用完整觀察期間",
        value=True,
    )
)


# =========================================================
# 建立分析母體
# =========================================================

analysis_base = performance.copy()

if only_complete_periods:
    analysis_base = analysis_base[
        analysis_base[
            "all_periods_complete"
        ]
    ].copy()


valid_uplift = analysis_base.dropna(
    subset=["uplift_rate"]
).copy()


continue_mask = (
    (
        valid_uplift["uplift_rate"]
        >= high_uplift_threshold
    )
    & (
        valid_uplift[
            "campaign_total_sales"
        ]
        >= minimum_campaign_sales
    )
)


review_mask = (
    valid_uplift["uplift_rate"]
    < low_uplift_threshold
)


optimize_mask = ~(
    continue_mask | review_mask
)


high_performance = valid_uplift[
    continue_mask
].copy()


low_performance = valid_uplift[
    review_mask
].copy()


stable_performance = valid_uplift[
    optimize_mask
].copy()


incomplete_periods = performance[
    ~performance[
        "all_periods_complete"
    ]
].copy()


zero_or_missing_baseline = performance[
    (
        performance[
            "baseline_average_daily_sales"
        ].isna()
    )
    | (
        performance[
            "baseline_average_daily_sales"
        ] == 0
    )
].copy()


overlap_risk = performance[
    (
        performance[
            "overlapping_campaigns"
        ].notna()
    )
    | (
        performance[
            "overlapping_benefits"
        ].notna()
    )
].copy()


post_decline = performance[
    performance[
        "post_change_rate"
    ] < -0.20
].copy()


# =========================================================
# 產生策略資料表
# =========================================================

strategy_rows = []


for _, row in high_performance.iterrows():
    strategy_rows.append(
        {
            "策略分類": "建議延續",
            "商品活動": activity_label(row),
            "活動提升率": row["uplift_rate"],
            "活動總銷量": row[
                "campaign_total_sales"
            ],
            "推估營收": row.get(
                "estimated_revenue"
            ),
            "資料信心": row.get(
                "data_confidence"
            ),
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
            "推估營收": row.get(
                "estimated_revenue"
            ),
            "資料信心": row.get(
                "data_confidence"
            ),
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
            "推估營收": row.get(
                "estimated_revenue"
            ),
            "資料信心": row.get(
                "data_confidence"
            ),
            "建議": (
                "活動有一定效果但未達高成效門檻，"
                "可透過優惠門檻、活動文案"
                "或曝光時間進行小幅測試。"
            ),
        }
    )


strategy_dataframe = pd.DataFrame(
    strategy_rows
)


# =========================================================
# 產生文字報告
# =========================================================

total_count = len(performance)

complete_count = int(
    performance[
        "all_periods_complete"
    ].sum()
)

high_count = len(high_performance)
low_count = len(low_performance)
stable_count = len(stable_performance)

median_uplift = valid_uplift[
    "uplift_rate"
].median()


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
        f"- 可計算活動的提升率中位數："
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
            f"- 觀察期間不完整："
            f"{len(incomplete_periods)} 筆。"
        ),
        (
            f"- 基準銷量為 0 或缺漏："
            f"{len(zero_or_missing_baseline)} 筆。"
        ),
        (
            f"- 存在重疊活動或優惠："
            f"{len(overlap_risk)} 筆。"
        ),
        "- 推估營收未納入實際成交折扣、退貨、平台幣與贈品成本。",
        "- 本報告描述活動期間的銷量變化，不代表已證明因果關係。",
    ]
)


strategy_report_text = "\n".join(
    report_lines
)


# 舊版頁面沿用中央策略產生器，避免與策略中心出現不同規則。
strategy_settings = AnalysisSettings(
    high_uplift_threshold=float(
        high_uplift_threshold
    ),
    low_uplift_threshold=float(
        low_uplift_threshold
    ),
    minimum_campaign_sales=float(
        minimum_campaign_sales
    ),
    only_complete_periods=only_complete_periods,
)

strategy_dataframe, strategy_report_text = (
    generate_strategy_report(
        performance_dataframe=performance,
        settings=strategy_settings,
    )
)


st.session_state[
    "strategy_report_dataframe"
] = strategy_dataframe

st.session_state[
    "strategy_report_text"
] = strategy_report_text

st.session_state["analysis_settings"] = {
    "baseline_days": strategy_settings.baseline_days,
    "post_days": strategy_settings.post_days,
    "high_uplift_threshold": (
        strategy_settings.high_uplift_threshold
    ),
    "low_uplift_threshold": (
        strategy_settings.low_uplift_threshold
    ),
    "minimum_campaign_sales": (
        strategy_settings.minimum_campaign_sales
    ),
    "only_complete_periods": (
        strategy_settings.only_complete_periods
    ),
}


# =========================================================
# KPI
# =========================================================

st.subheader("策略摘要")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "高成效活動",
    high_count,
)

col2.metric(
    "一般成效活動",
    stable_count,
)

col3.metric(
    "低成效活動",
    low_count,
)

col4.metric(
    "資料完整率",
    (
        f"{complete_count / total_count:.1%}"
        if total_count > 0
        else "-"
    ),
)


# =========================================================
# 主要洞察
# =========================================================

st.subheader("主要洞察")


if not high_performance.empty:
    best_activity = (
        high_performance.sort_values(
            "uplift_rate",
            ascending=False,
        ).iloc[0]
    )

    st.success(
        "目前表現最佳活動為："
        f"{activity_label(best_activity)}，"
        f"活動提升率為 "
        f"{format_percentage(best_activity['uplift_rate'])}，"
        f"活動總銷量為 "
        f"{format_number(best_activity['campaign_total_sales'])}。"
    )

else:
    st.info(
        "目前沒有符合高成效門檻且觀察期間完整的活動。"
    )


if not low_performance.empty:
    worst_activity = (
        low_performance.sort_values(
            "uplift_rate",
            ascending=True,
        ).iloc[0]
    )

    st.error(
        "目前最需要檢討的活動為："
        f"{activity_label(worst_activity)}，"
        f"活動提升率為 "
        f"{format_percentage(worst_activity['uplift_rate'])}。"
    )


if not overlap_risk.empty:
    st.warning(
        f"共有 {len(overlap_risk)} 筆活動"
        "與其他平台活動或優惠重疊，"
        "判讀時需避免將效果完全歸因於單一活動。"
    )


# =========================================================
# 分頁
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "策略建議",
        "高成效活動",
        "低成效活動",
        "完整報告",
    ]
)


with tab1:
    st.subheader("活動策略清單")

    if strategy_dataframe.empty:
        st.info(
            "目前沒有符合策略分類條件的活動。"
        )

    else:
        st.dataframe(
            strategy_dataframe,
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


with tab2:
    st.subheader("高成效活動")

    if high_performance.empty:
        st.info("目前沒有高成效活動。")

    else:
        high_display = (
            high_performance.sort_values(
                "uplift_rate",
                ascending=False,
            )
        )

        st.dataframe(
            high_display,
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
            },
        )


with tab3:
    st.subheader("低成效活動")

    if low_performance.empty:
        st.success(
            "目前沒有低於門檻的活動。"
        )

    else:
        low_display = (
            low_performance.sort_values(
                "uplift_rate",
                ascending=True,
            )
        )

        st.dataframe(
            low_display,
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
            },
        )


with tab4:
    st.subheader("策略建議文字報告")

    st.markdown(
        strategy_report_text
    )


# =========================================================
# 下載
# =========================================================

st.divider()

download_col1, download_col2 = st.columns(2)


with download_col1:
    strategy_csv = (
        strategy_dataframe.to_csv(
            index=False,
            encoding="utf-8-sig",
        )
        .encode("utf-8-sig")
    )

    st.download_button(
        "下載策略建議清單",
        data=strategy_csv,
        file_name="strategy_recommendations.csv",
        mime="text/csv",
    )


with download_col2:
    st.download_button(
        "下載策略文字報告",
        data=strategy_report_text.encode(
            "utf-8"
        ),
        file_name="strategy_report.md",
        mime="text/markdown",
    )
