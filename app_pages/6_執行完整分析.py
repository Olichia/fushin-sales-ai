from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analysis_pipeline import (
    AnalysisSettings,
    run_full_analysis,
)
from src.activity_unit_analysis import run_activity_unit_analysis
from src.column_labels import default_column_config
from src.persistence import save_analysis_snapshot
from src.session_helpers import initialize_session_state
from src.unit_overview_helpers import compute_actual_revenue_total


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
        分析總覽、活動洞察、AI 策略中心與主管報表。
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
# 分析設定（舊版方法論不再是主要依據，固定使用預設參數；
# 舊版流程仍會在背後執行，供「分析完成摘要」KPI 與頁11/13
# 新引擎失敗時的備援路徑使用）
# =========================================================

settings = AnalysisSettings(
    baseline_days=7,
    post_days=7,
    fill_missing_dates_with_zero=True,
    high_uplift_threshold=0.20,
    low_uplift_threshold=0.0,
    minimum_campaign_sales=1.0,
    only_complete_periods=True,
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
    # 執行活動單位分析（新方法論，獨立 try/except，
    # 確保萬一失敗也不影響上面舊 pipeline 的結果）
    # =====================================================

    try:
        unit_analysis_result = run_activity_unit_analysis(
            sales_dataframe=sales_dataframe,
            activity_standardized_dataframe=(
                activity_dataframe
            ),
            activity_calendar_dataframe=(
                calendar_for_analysis
            ),
        )

    except Exception as error:
        unit_analysis_result = None

        st.warning(
            "活動單位分析（新方法論）執行失敗，"
            f"將僅顯示舊版成效分析結果：{error}"
        )

    if unit_analysis_result is not None:
        st.session_state[
            "activity_unit_timeline_dataframe"
        ] = unit_analysis_result.unit_timeline

        st.session_state[
            "activity_unit_timeline_wide_dataframe"
        ] = unit_analysis_result.unit_timeline_wide

        st.session_state[
            "activity_unit_price_dataframe"
        ] = unit_analysis_result.unit_price_table

        st.session_state[
            "activity_unit_overview_dataframe"
        ] = unit_analysis_result.unit_overview

        st.session_state[
            "activity_waterfall_pairing_dataframe"
        ] = unit_analysis_result.waterfall_pairing_table

        st.session_state[
            "activity_waterfall_summary_dataframe"
        ] = unit_analysis_result.waterfall_summary

        st.session_state[
            "activity_bundle_rules_dataframe"
        ] = unit_analysis_result.bundle_rules

        st.session_state[
            "activity_bundle_date_mismatch_dataframe"
        ] = unit_analysis_result.bundle_date_mismatches

        st.session_state["unit_analysis_completed"] = True

    else:
        st.session_state["unit_analysis_completed"] = False


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

    # 分析結果不需要另外比對/選擇，銷量與活動資料在各自的
    # 確認步驟已經做過覆蓋/保留的把關，這裡算出來的結果直接
    # 存檔即可，重新整理瀏覽器時才能連分析結果一起帶回來，
    # 不用逼使用者重新按一次「執行完整分析」。
    save_analysis_snapshot()

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
                column_config=default_column_config(
                    issues_dataframe
                ),
            )
    else:
        st.success(
            "整合過程沒有發現需要另外處理的問題。"
        )

    bundle_date_mismatch_dataframe = get_dataframe(
        "activity_bundle_date_mismatch_dataframe"
    )

    if dataframe_ready(bundle_date_mismatch_dataframe):
        st.warning(
            f"發現 {len(bundle_date_mismatch_dataframe):,} 筆"
            "活動組合名稱相符但日期未完全對齊的提醒，"
            "請展開查看。"
        )

        with st.expander(
            "查看活動組合日期提醒",
            expanded=False,
        ):
            st.caption(
                "以下活動名稱包含同一個母活動的關鍵字，"
                "但日期沒有完全一致，因此未被系統合併成"
                "同一個不可分割活動組合。建議確認來源資料"
                "的日期是否填寫正確。"
            )
            st.dataframe(
                bundle_date_mismatch_dataframe,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    bundle_date_mismatch_dataframe
                ),
            )

    unit_timeline_wide_dataframe = get_dataframe(
        "activity_unit_timeline_wide_dataframe"
    )

    unit_overview_dataframe = get_dataframe(
        "activity_unit_overview_dataframe"
    )

    unit_price_dataframe = get_dataframe(
        "activity_unit_price_dataframe"
    )

    unit_analysis_completed = bool(
        st.session_state.get(
            "unit_analysis_completed",
            False,
        )
    )

    st.divider()

    st.markdown("##### 活動單位分析（新方法論）")
    st.caption(
        "以「活動單位」為顆粒度，比較每個活動單位相對於"
        "同月安靜期基準的淨營收效應，並拆解量增與降價兩種效應"
        "（對應參考報表工作表3-5）。取代舊版單純的活動前後"
        "平均值比較。"
    )

    result_tab3, result_tab4, result_tab5 = st.tabs(
        [
            "活動清單",
            "商品售價表",
            "整合資料總覽",
        ]
    )

    with result_tab3:
        st.caption(
            "對應參考報表工作表3，逐SKU一欄顯示每個單位的對應活動。"
        )

        if unit_analysis_completed and dataframe_ready(
            unit_timeline_wide_dataframe
        ):
            unit_timeline_wide_display = unit_timeline_wide_dataframe.drop(
                columns=[
                    column
                    for column in ["note"]
                    if column in unit_timeline_wide_dataframe.columns
                ]
            )

            st.dataframe(
                unit_timeline_wide_display,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    unit_timeline_wide_display
                ),
            )
        else:
            st.info(
                "目前沒有可顯示的活動清單，"
                "可能是活動單位分析執行失敗或尚未執行。"
            )

    with result_tab4:
        st.caption("對應參考報表工作表4「商品售價表(依單位)」。")

        if unit_analysis_completed and dataframe_ready(
            unit_price_dataframe
        ):
            st.dataframe(
                unit_price_dataframe,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    unit_price_dataframe
                ),
            )
        else:
            st.info(
                "目前沒有可顯示的商品售價表，"
                "可能是活動單位分析執行失敗或尚未執行。"
            )

    with result_tab5:
        if unit_analysis_completed and dataframe_ready(
            unit_overview_dataframe
        ):
            unit_metric_col_1, unit_metric_col_2, unit_metric_col_3 = (
                st.columns(3)
            )

            with unit_metric_col_1:
                st.metric(
                    "活動單位數",
                    f"{unit_overview_dataframe['unit_code'].nunique():,} 個",
                )

            with unit_metric_col_2:
                st.metric(
                    "涉及SKU數",
                    f"{unit_overview_dataframe['product_id'].nunique():,} 個",
                )

            with unit_metric_col_3:
                st.metric(
                    "淨營收效應合計",
                    f"{unit_overview_dataframe['net_revenue_effect_total'].sum():,.0f} 元",
                )

            st.caption(
                "對應參考報表工作表5，"
                "已略去「分類／樣本量提示／代理牌價提示」3個欄位。"
            )

            unit_overview_with_revenue = (
                unit_overview_dataframe.copy()
            )

            unit_overview_with_revenue["total_actual_revenue"] = (
                compute_actual_revenue_total(
                    unit_overview_with_revenue
                )
            )

            unit_overview_display = unit_overview_with_revenue.drop(
                columns=[
                    column
                    for column in [
                        "classification",
                        "sample_size_note",
                        "proxy_price_note",
                    ]
                    if column in unit_overview_with_revenue.columns
                ]
            )

            st.dataframe(
                unit_overview_display,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    unit_overview_display
                ),
            )
        else:
            st.info(
                "目前沒有可顯示的整合資料總覽，"
                "可能是活動單位分析執行失敗或尚未執行。"
            )

    with st.expander(
        "分析方法與欄位說明",
        expanded=False,
    ):
        st.caption(
            "**活動單位（unit_code）**　同一個月份中，"
            "同一組活動組合特徵會被歸為同一個活動單位，"
            "同一單位常對應多個商品；「活動清單」即依此顆粒度"
            "逐SKU列出每個單位對應的活動。"
        )
        st.caption(
            "**量增效應／降價效應／淨營收效應**　以商品所在活動"
            "區間的實際營收，對照同月安靜期基準估算：量增效應"
            "為銷量變動帶來的營收差異，降價效應為售價變動帶來的"
            "營收差異，兩者加總為淨營收效應（見「整合資料總覽」）。"
        )
        st.caption(
            "**分類欄位**　「可分離正向」代表可拆解出正向貢獻的"
            "單一活動；「不可分割活動組合」代表活動疊加無法拆解，"
            "需以整體單位判讀；「負增益」代表該單位淨營收效應為負。"
        )
        st.caption(
            "**樣本天數提示**　樣本天數 <2 天的區間信心較低，"
            "已於「提示」欄位標示，建議僅作輔助參考。"
        )

    st.success(
        "下一步可前往「分析總覽」、「活動洞察」、"
        "「AI 策略中心」或「主管報表」查看成果。"
    )
