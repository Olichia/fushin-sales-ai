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


def render_readiness_card(
    *,
    icon: str,
    title: str,
    ready: bool,
    ready_text: str,
    pending_text: str,
    count_text: str,
) -> None:
    """顯示分析前置資料狀態卡。"""

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="status-card-heading">
                <div class="status-card-icon">{icon}</div>
                <div>
                    <div class="status-card-title">{title}</div>
                    <div class="status-card-subtitle">{count_text}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if ready:
            st.success(
                ready_text
            )
        else:
            st.error(
                pending_text
            )


# =========================================================
# 頁面標題
# =========================================================

st.markdown(
    """
    <div class="step-label">STEP 03</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>執行完整分析</h1>
    </div>

    <p class="product-page-description">
        一次完成銷量與活動資料整合、活動前中後成效分析，
        以及策略報告產生。分析完成後，結果會同步提供給
        分析總覽、活動洞察、策略中心、主管報表與 AI 策略顧問。
    </p>
    """,
    unsafe_allow_html=True,
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
    render_readiness_card(
        icon="📊",
        title="銷量資料",
        ready=sales_ready,
        ready_text=(
            f"已完成確認，共 {len(sales_dataframe):,} 筆標準化資料。"
        ),
        pending_text=(
            "尚未完成，請先前往「01 銷量資料處理」。"
        ),
        count_text=(
            f"{len(sales_dataframe):,} 筆標準化資料"
            if dataframe_ready(sales_dataframe)
            else "尚無標準化資料"
        ),
    )

with status_col_2:
    render_readiness_card(
        icon="🏷️",
        title="活動資料",
        ready=activity_ready,
        ready_text=(
            f"已完成確認，共 {len(activity_dataframe):,} 筆商品活動資料。"
        ),
        pending_text=(
            "尚未完成，請先前往「02 活動資料處理」。"
        ),
        count_text=(
            f"{len(activity_dataframe):,} 筆商品活動資料"
            if dataframe_ready(activity_dataframe)
            else "尚無標準化資料"
        ),
    )


with st.expander(
    "查看其他活動資料狀態",
    expanded=False,
):
    auxiliary_col1, auxiliary_col2 = st.columns(2)

    with auxiliary_col1:
        st.metric(
            "平台活動日曆",
            f"{len(calendar_dataframe):,} 筆",
        )

        if calendar_ready:
            st.success(
                "活動日曆已備妥。"
            )
        else:
            st.info(
                "未提供活動日曆，系統將以空資料處理。"
            )

    with auxiliary_col2:
        st.metric(
            "優惠資料",
            f"{len(benefits_dataframe):,} 筆",
        )

        if benefits_ready:
            st.success(
                "優惠資料已備妥。"
            )
        else:
            st.info(
                "未提供優惠資料，系統將以空資料處理。"
            )


# =========================================================
# 分析流程說明
# =========================================================

st.subheader("完整分析流程")

pipeline_columns = st.columns(3)

pipeline_steps = [
    {
        "編號": "01",
        "圖示": "🔗",
        "名稱": "建立整合資料",
        "說明": "將銷量、商品活動、平台活動與優惠資料整合。",
    },
    {
        "編號": "02",
        "圖示": "📈",
        "名稱": "執行成效分析",
        "說明": "比較活動前、活動期間與活動後的銷量表現。",
    },
    {
        "編號": "03",
        "圖示": "📋",
        "名稱": "產生策略報告",
        "說明": "整理延續、優化與檢討活動的策略建議。",
    },
]

for column, step in zip(
    pipeline_columns,
    pipeline_steps,
):
    with column:
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="workflow-step-header">
                    <div class="workflow-step-icon">
                        {step['圖示']}
                    </div>
                    <div>
                        <div class="workflow-step-number">
                            PROCESS {step['編號']}
                        </div>
                        <div class="workflow-step-title">
                            {step['名稱']}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write(
                step["說明"]
            )


# =========================================================
# 分析設定
# =========================================================

st.subheader("分析設定")

with st.expander(
    "調整分析參數",
    expanded=False,
):
    setting_col1, setting_col2 = st.columns(2)

    with setting_col1:
        baseline_days = st.number_input(
            "活動前觀察天數",
            min_value=1,
            max_value=90,
            value=7,
            step=1,
            help="用於計算活動開始前的平均每日銷量。",
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

        minimum_campaign_sales = st.number_input(
            "最低活動總銷量",
            min_value=0.0,
            value=1.0,
            step=1.0,
            help="活動總銷量低於此數值時，不列入高成效活動。",
        )

    with setting_col2:
        post_days = st.number_input(
            "活動後觀察天數",
            min_value=1,
            max_value=90,
            value=7,
            step=1,
            help="用於觀察活動結束後的銷量變化。",
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

analysis_completed = bool(
    st.session_state.get(
        "full_analysis_completed",
        False,
    )
)

if analysis_completed:
    st.info(
        "目前 Session 中已有完整分析結果。"
        "重新執行會以目前資料與設定覆蓋原有結果。"
    )


# =========================================================
# 執行完整分析
# =========================================================

st.subheader("開始分析")

with st.container(border=True):
    st.markdown(
        """
        <div class="analysis-action-heading">
            <div class="analysis-action-icon">▶️</div>
            <div>
                <div class="analysis-action-title">
                    一鍵執行完整分析
                </div>
                <div class="analysis-action-description">
                    系統會按照既定順序完成三個處理階段，
                    不需要再逐頁執行整合、成效分析與策略報告。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not can_run_analysis:
        st.warning(
            "必須先完成銷量資料與活動資料的最終確認，"
            "才能執行完整分析。"
        )

    run_button = st.button(
        "執行完整分析",
        type="primary",
        use_container_width=True,
        disabled=not can_run_analysis,
    )


if run_button:
    calendar_for_analysis = (
        calendar_dataframe
        if calendar_ready
        else pd.DataFrame()
    )

    benefits_for_analysis = (
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
                "① 正在建立銷量與活動整合資料……"
            )

            result = run_full_analysis(
                sales_dataframe=sales_dataframe,
                main_activity_dataframe=(
                    activity_dataframe
                ),
                calendar_dataframe=(
                    calendar_for_analysis
                ),
                benefits_dataframe=(
                    benefits_for_analysis
                ),
                settings=settings,
            )

            st.write(
                "② 銷量與活動資料整合完成。"
            )

            st.write(
                "③ 活動成效分析完成。"
            )

            st.write(
                "④ 策略報告產生完成。"
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

analysis_completed = bool(
    st.session_state.get(
        "full_analysis_completed",
        False,
    )
)

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

    result_tab1, result_tab2 = st.tabs(
        [
            "成效分析預覽",
            "策略報告預覽",
        ]
    )

    with result_tab1:
        if dataframe_ready(performance_dataframe):
            st.dataframe(
                performance_dataframe.head(100),
                use_container_width=True,
                hide_index=True,
            )

            if len(performance_dataframe) > 100:
                st.caption(
                    "目前僅預覽前 100 筆資料。"
                )
        else:
            st.info(
                "目前沒有可顯示的成效分析結果。"
            )

    with result_tab2:
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