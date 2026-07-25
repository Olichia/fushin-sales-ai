from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analysis_pipeline import (
    AnalysisSettings,
    run_full_analysis,
)
from src.session_helpers import initialize_session_state


# =========================================================
# 初始化
# =========================================================

initialize_session_state()


# =========================================================
# 頁面標題
# =========================================================

st.title("執行完整分析")

st.caption(
    "系統會依序完成資料整合、活動成效分析與策略報告產生。"
)


# =========================================================
# Session State 工具
# =========================================================

def get_dataframe(
    key: str,
) -> pd.DataFrame:
    """
    安全取得 Session State 中的 DataFrame。

    若不存在或格式錯誤，回傳空 DataFrame。
    """

    value = st.session_state.get(key)

    if isinstance(value, pd.DataFrame):
        return value

    return pd.DataFrame()


def dataframe_ready(
    dataframe: pd.DataFrame,
) -> bool:
    """判斷 DataFrame 是否存在且有資料。"""

    return (
        isinstance(dataframe, pd.DataFrame)
        and not dataframe.empty
    )


# =========================================================
# 讀取前置資料
# =========================================================

sales_dataframe = get_dataframe(
    "standardized_dataframe"
)

activity_dataframe = get_dataframe(
    "activity_standardized_dataframe"
)

calendar_dataframe = get_dataframe(
    "activity_calendar_dataframe"
)

benefits_dataframe = get_dataframe(
    "promotion_benefits_dataframe"
)


sales_confirmed = bool(
    st.session_state.get(
        "sales_data_confirmed",
        False,
    )
)

activity_confirmed = bool(
    st.session_state.get(
        "activity_data_confirmed",
        False,
    )
)


sales_ready = (
    sales_confirmed
    and dataframe_ready(sales_dataframe)
)

activity_ready = (
    activity_confirmed
    and dataframe_ready(activity_dataframe)
)

calendar_ready = dataframe_ready(
    calendar_dataframe
)

benefits_ready = dataframe_ready(
    benefits_dataframe
)

can_run_analysis = (
    sales_ready
    and activity_ready
)


# =========================================================
# 資料準備狀態
# =========================================================

st.subheader("資料準備狀態")

status_col_1, status_col_2 = st.columns(2)

with status_col_1:
    if sales_ready:
        st.success(
            f"銷量資料已完成，共 {len(sales_dataframe):,} 筆。"
        )
    else:
        st.error(
            "銷量資料尚未完成，請先前往「銷量資料處理」。"
        )

with status_col_2:
    if activity_ready:
        st.success(
            f"活動資料已完成，共 {len(activity_dataframe):,} 筆。"
        )
    else:
        st.error(
            "活動資料尚未完成，請先前往「活動資料處理」。"
        )


with st.expander(
    "查看其他活動資料狀態",
    expanded=False,
):
    if calendar_ready:
        st.write(
            f"平台活動日曆：{len(calendar_dataframe):,} 筆"
        )
    else:
        st.write(
            "平台活動日曆：未提供，系統將以空資料處理。"
        )

    if benefits_ready:
        st.write(
            f"優惠資料：{len(benefits_dataframe):,} 筆"
        )
    else:
        st.write(
            "優惠資料：未提供，系統將以空資料處理。"
        )


# =========================================================
# 分析設定
# =========================================================

st.subheader("分析設定")

with st.expander(
    "調整分析參數",
    expanded=False,
):
    baseline_days = st.number_input(
        "活動前觀察天數",
        min_value=1,
        max_value=90,
        value=7,
        step=1,
        help="用於計算活動開始前的平均每日銷量。",
    )

    post_days = st.number_input(
        "活動後觀察天數",
        min_value=1,
        max_value=90,
        value=7,
        step=1,
        help="用於觀察活動結束後的銷量變化。",
    )

    high_uplift_threshold = st.number_input(
        "高成效提升率門檻",
        min_value=-1.0,
        max_value=10.0,
        value=0.20,
        step=0.05,
        format="%.2f",
        help="0.20 代表活動期間平均每日銷量提升 20%。",
    )

    low_uplift_threshold = st.number_input(
        "低成效提升率門檻",
        min_value=-1.0,
        max_value=10.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        help="低於此門檻的活動會被歸類為低成效。",
    )

    minimum_campaign_sales = st.number_input(
        "最低活動總銷量",
        min_value=0.0,
        value=1.0,
        step=1.0,
        help="活動總銷量低於此數值時，不列入高成效活動。",
    )

    fill_missing_dates_with_zero = st.checkbox(
        "缺少銷量紀錄的日期視為 0",
        value=True,
    )

    only_complete_periods = st.checkbox(
        "策略報告只使用觀察期間完整的活動",
        value=True,
    )


settings = AnalysisSettings(
    baseline_days=int(baseline_days),
    post_days=int(post_days),
    fill_missing_dates_with_zero=(
        fill_missing_dates_with_zero
    ),
    high_uplift_threshold=float(
        high_uplift_threshold
    ),
    low_uplift_threshold=float(
        low_uplift_threshold
    ),
    minimum_campaign_sales=float(
        minimum_campaign_sales
    ),
    only_complete_periods=(
        only_complete_periods
    ),
)


# =========================================================
# 目前分析結果狀態
# =========================================================

existing_integrated = get_dataframe(
    "integrated_sales_activity_dataframe"
)

existing_performance = get_dataframe(
    "activity_performance_dataframe"
)

existing_strategy = get_dataframe(
    "strategy_report_dataframe"
)


analysis_completed = bool(
    st.session_state.get(
        "full_analysis_completed",
        False,
    )
)

if analysis_completed:
    st.info(
        "目前 Session 中已有完整分析結果。"
        "重新執行將覆蓋原有結果。"
    )


# =========================================================
# 執行完整分析
# =========================================================

st.subheader("開始分析")

st.write(
    "按下按鈕後，系統將依序執行："
)

st.write(
    "1. 建立銷量與活動整合資料"
)

st.write(
    "2. 執行活動前、中、後成效分析"
)

st.write(
    "3. 產生策略資料與文字報告"
)


run_button = st.button(
    "執行完整分析",
    type="primary",
    use_container_width=True,
    disabled=not can_run_analysis,
)


if run_button:
    empty_calendar_dataframe = (
        calendar_dataframe
        if calendar_ready
        else pd.DataFrame()
    )

    empty_benefits_dataframe = (
        benefits_dataframe
        if benefits_ready
        else pd.DataFrame()
    )

    try:
        with st.status(
            "正在執行完整分析……",
            expanded=True,
        ) as analysis_status:
            st.write(
                "正在建立銷量與活動整合資料……"
            )

            result = run_full_analysis(
                sales_dataframe=sales_dataframe,
                main_activity_dataframe=(
                    activity_dataframe
                ),
                calendar_dataframe=(
                    empty_calendar_dataframe
                ),
                benefits_dataframe=(
                    empty_benefits_dataframe
                ),
                settings=settings,
            )

            st.write(
                "銷量與活動資料整合完成。"
            )

            st.write(
                "活動成效分析完成。"
            )

            st.write(
                "策略報告產生完成。"
            )

            analysis_status.update(
                label="完整分析已完成",
                state="complete",
                expanded=True,
            )

    except ValueError as error:
        st.session_state[
            "full_analysis_completed"
        ] = False

        st.error(
            f"分析資料格式不符合要求：{error}"
        )

        st.stop()

    except KeyError as error:
        st.session_state[
            "full_analysis_completed"
        ] = False

        st.error(
            f"分析時找不到必要欄位：{error}"
        )

        st.stop()

    except Exception as error:
        st.session_state[
            "full_analysis_completed"
        ] = False

        st.error(
            f"完整分析執行失敗：{error}"
        )

        st.exception(error)

        st.stop()


    # =====================================================
    # 將結果存回原有 Session State
    # =====================================================

    st.session_state[
        "integrated_sales_activity_dataframe"
    ] = result.integrated_dataframe

    st.session_state[
        "integration_issues_dataframe"
    ] = result.integration_issues_dataframe

    st.session_state[
        "activity_performance_dataframe"
    ] = result.performance_dataframe

    st.session_state[
        "strategy_report_dataframe"
    ] = result.strategy_dataframe

    st.session_state[
        "strategy_report_text"
    ] = result.strategy_report_text

    st.session_state[
        "full_analysis_completed"
    ] = True

    st.session_state[
        "integration_completed"
    ] = True

    st.session_state[
        "performance_analysis_completed"
    ] = True

    st.session_state[
        "strategy_report_completed"
    ] = True

    st.success(
        "完整分析已成功完成，可以前往成果頁面查看結果。"
    )

    st.rerun()


# =========================================================
# 顯示完成後摘要
# =========================================================

if analysis_completed:
    integrated_dataframe = get_dataframe(
        "integrated_sales_activity_dataframe"
    )

    issues_dataframe = get_dataframe(
        "integration_issues_dataframe"
    )

    performance_dataframe = get_dataframe(
        "activity_performance_dataframe"
    )

    strategy_dataframe = get_dataframe(
        "strategy_report_dataframe"
    )

    strategy_report_text = str(
        st.session_state.get(
            "strategy_report_text",
            "",
        )
    )


    st.divider()

    st.subheader("分析完成摘要")

    metric_col_1, metric_col_2, metric_col_3 = (
        st.columns(3)
    )

    with metric_col_1:
        st.metric(
            "整合資料",
            f"{len(integrated_dataframe):,} 筆",
        )

    with metric_col_2:
        st.metric(
            "成效分析",
            f"{len(performance_dataframe):,} 筆",
        )

    with metric_col_3:
        st.metric(
            "策略資料",
            f"{len(strategy_dataframe):,} 筆",
        )


    if dataframe_ready(issues_dataframe):
        st.warning(
            f"整合過程發現 {len(issues_dataframe):,} 筆提醒，"
            "請展開查看。"
        )

        with st.expander(
            "查看整合問題",
            expanded=False,
        ):
            st.dataframe(
                issues_dataframe,
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.success(
            "整合過程沒有發現需要另外處理的問題。"
        )


    with st.expander(
        "預覽成效分析結果",
        expanded=False,
    ):
        if dataframe_ready(performance_dataframe):
            st.dataframe(
                performance_dataframe.head(100),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "目前沒有可顯示的成效分析結果。"
            )


    with st.expander(
        "預覽策略報告",
        expanded=True,
    ):
        if strategy_report_text.strip():
            st.markdown(
                strategy_report_text
            )
        else:
            st.info(
                "目前沒有策略報告文字。"
            )


    st.success(
        "下一步可前往「分析總覽」、「活動洞察」、"
        "「策略中心」或「主管報表」查看成果。"
    )