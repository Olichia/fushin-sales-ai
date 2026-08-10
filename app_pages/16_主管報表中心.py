from pathlib import Path
import sys
from datetime import datetime

import pandas as pd
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


from src.column_labels import default_column_config
from src.session_helpers import initialize_session_state


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()


# =========================================================
# 小工具函式
# =========================================================

def dataframe_ready(
    dataframe: object,
) -> bool:
    """判斷物件是否為非空 DataFrame。"""

    return (
        isinstance(dataframe, pd.DataFrame)
        and not dataframe.empty
    )


# =========================================================
# 頁面標題
# =========================================================

st.markdown(
    """
    <div class="step-label">MANAGEMENT REPORT</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>主管報表中心</h1>
    </div>

    <p class="product-page-description">
        將銷量概況、活動成效、策略建議與資料限制，
        整理成可下載的主管 PDF 報告。本頁僅讀取目前分析結果，
        不會重新計算或修改任何資料。
    </p>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 取得 Session State
# =========================================================

sales_dataframe = st.session_state.get(
    "standardized_dataframe"
)

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)

strategy_dataframe = st.session_state.get(
    "strategy_report_dataframe"
)

strategy_report_text = st.session_state.get(
    "strategy_report_text"
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

waterfall_summary_raw = st.session_state.get(
    "activity_waterfall_summary_dataframe"
)

unit_analysis_completed = bool(
    st.session_state.get("unit_analysis_completed", False)
)

new_engine_ready = (
    unit_analysis_completed
    and dataframe_ready(unit_overview_raw)
    and dataframe_ready(waterfall_summary_raw)
)


# =========================================================
# 資料完整性檢查
# =========================================================

missing_sources = []

if not new_engine_ready:
    if not dataframe_ready(
        performance_dataframe
    ):
        missing_sources.append(
            "活動成效分析"
        )

    if not dataframe_ready(
        strategy_dataframe
    ):
        missing_sources.append(
            "策略建議資料"
        )

    if not str(
        strategy_report_text or ""
    ).strip():
        missing_sources.append(
            "策略文字報告"
        )


if missing_sources:
    st.warning(
        "目前尚缺少："
        + "、".join(missing_sources)
        + "。請先完成「03 執行完整分析」。"
    )

    st.stop()


# =========================================================
# 報表內容摘要
# =========================================================

activity_issue_count = (
    len(activity_issues_dataframe)
    if isinstance(
        activity_issues_dataframe,
        pd.DataFrame,
    )
    else 0
)

integration_issue_count = (
    len(integration_issues_dataframe)
    if isinstance(
        integration_issues_dataframe,
        pd.DataFrame,
    )
    else 0
)

with st.container(border=True):
    if new_engine_ready:
        st.markdown(
            """
            <div class="report-content-heading">
                <div class="report-content-icon">📄</div>
                <div>
                    <div class="report-content-title">
                        PDF 報告將包含
                    </div>
                    <div class="report-content-description">
                        分析概況、商品表現排行、活動單位成效重點、
                        折扣率洞察、疊加活動組合分析、風險提醒、
                        資料信心與判讀限制、主管策略摘要，
                        以及情境模擬採用方案。
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        report_item_col1, report_item_col2, report_item_col3 = (
            st.columns(3)
        )

        with report_item_col1:
            st.markdown(
                """
                **分析概況**

                - 總GMV／淨增益GMV合計
                - 活動單位數與風險檔數
                - 商品表現排行
                """
            )

        with report_item_col2:
            st.markdown(
                """
                **活動單位成效重點**

                - 表現最佳／較差活動單位
                - 折扣率×淨增益對照
                - 疊加活動組合排行
                - 毛利侵蝕風險清單
                """
            )

        with report_item_col3:
            st.markdown(
                """
                **策略摘要與資料限制**

                - 主管策略摘要
                - 情境模擬採用方案
                - 資料信心分布與因果判讀限制
                """
            )

    else:
        st.markdown(
            """
            <div class="report-content-heading">
                <div class="report-content-icon">📄</div>
                <div>
                    <div class="report-content-title">
                        PDF 報告將包含
                    </div>
                    <div class="report-content-description">
                        分析概況、最佳與較差活動、三類策略建議、
                        資料品質限制，以及主管策略摘要。
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        report_item_col1, report_item_col2, report_item_col3 = (
            st.columns(3)
        )

        with report_item_col1:
            st.markdown(
                """
                **分析概況**

                - 活動分析數量
                - 高低成效活動
                - 提升率摘要
                """
            )

        with report_item_col2:
            st.markdown(
                """
                **活動成效與策略建議**

                - 表現最佳／較差活動
                - 建議延續／優化／檢討分類
                """
            )

        with report_item_col3:
            st.markdown(
                """
                **資料限制與摘要**

                - 品質問題與重疊活動
                - 因果判讀限制
                - 主管策略摘要
                """
            )


# =========================================================
# 品質問題摘要
# =========================================================

st.divider()
st.subheader("資料品質摘要")

quality_col1, quality_col2, quality_col3 = (
    st.columns(3)
)

quality_col1.metric(
    "活動資料待確認",
    f"{activity_issue_count:,}",
)

quality_col2.metric(
    "整合資料待確認",
    f"{integration_issue_count:,}",
)

quality_col3.metric(
    "待確認問題合計",
    f"{activity_issue_count + integration_issue_count:,}",
)


if (
    activity_issue_count == 0
    and integration_issue_count == 0
):
    st.success(
        "目前沒有偵測到活動或整合資料問題。"
    )

else:
    st.warning(
        "報告將納入目前偵測到的資料問題，"
        "請在提交主管前確認問題內容。"
    )

    if activity_issue_count > 0:
        with st.expander(
            "查看活動資料問題",
            expanded=False,
        ):
            st.dataframe(
                activity_issues_dataframe,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    activity_issues_dataframe
                ),
            )

    if integration_issue_count > 0:
        with st.expander(
            "查看整合資料問題",
            expanded=False,
        ):
            st.dataframe(
                integration_issues_dataframe,
                use_container_width=True,
                hide_index=True,
                column_config=default_column_config(
                    integration_issues_dataframe
                ),
            )


# =========================================================
# 產生主管報告
# =========================================================

st.divider()
st.subheader("產生主管報告")

with st.container(border=True):
    st.markdown(
        """
        <div class="analysis-action-heading">
            <div class="analysis-action-icon">📥</div>
            <div>
                <div class="analysis-action-title">
                    建立主管 PDF 報告
                </div>
                <div class="analysis-action-description">
                    系統將依目前 Session State 中的最新分析結果，
                    建立包含 KPI、活動表現、策略建議與資料限制的 PDF。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    generate_button = st.button(
        "產生主管 PDF 報告",
        type="primary",
        use_container_width=True,
    )


if generate_button:
    try:
        with st.spinner(
            "正在整理活動成效與策略建議……"
        ):
            if new_engine_ready:
                from src.report_generator import (
                    generate_activity_unit_management_pdf,
                )

                pdf_bytes = (
                    generate_activity_unit_management_pdf(
                        unit_overview_dataframe=(
                            unit_overview_raw
                        ),
                        waterfall_summary_dataframe=(
                            waterfall_summary_raw
                        ),
                        adopted_scenarios=(
                            st.session_state.get(
                                "adopted_whatif_scenarios",
                                [],
                            )
                        ),
                    )
                )

            else:
                from src.report_generator import (
                    generate_management_pdf,
                )

                pdf_bytes = generate_management_pdf(
                    sales_dataframe=(
                        sales_dataframe
                    ),
                    performance_dataframe=(
                        performance_dataframe
                    ),
                    strategy_dataframe=(
                        strategy_dataframe
                    ),
                    strategy_report_text=(
                        strategy_report_text
                    ),
                    activity_issues_dataframe=(
                        activity_issues_dataframe
                    ),
                    integration_issues_dataframe=(
                        integration_issues_dataframe
                    ),
                )

        st.session_state[
            "management_report_pdf"
        ] = pdf_bytes

        st.success(
            "主管 PDF 報告產生完成。"
        )

    except Exception as error:
        st.error(
            "PDF 報告產生失敗，"
            "但其他分析功能仍可正常使用。"
        )

        with st.expander(
            "查看技術錯誤",
            expanded=False,
        ):
            st.code(
                str(error)
            )


pdf_bytes = st.session_state.get(
    "management_report_pdf"
)


if pdf_bytes:
    report_date = (
        datetime.now()
        .strftime("%Y%m%d_%H%M")
    )

    with st.container(border=True):
        st.markdown(
            """
            <div class="report-download-ready">
                <div class="report-download-icon">✅</div>
                <div>
                    <div class="report-download-title">
                        報告已準備完成
                    </div>
                    <div class="report-download-description">
                        請下載後確認中文字、表格換頁與內容完整性。
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.download_button(
            "下載主管 PDF 報告",
            data=pdf_bytes,
            file_name=(
                "management_activity_report_"
                f"{report_date}.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )


# =========================================================
# 判讀限制
# =========================================================

st.divider()

with st.expander(
    "報表判讀限制",
    expanded=False,
):
    st.markdown(
        """
- 活動期間銷量上升不代表已證明因果。
- 推估營收不等於實際營收或獲利。
- 報告尚未納入完整成本、毛利、退貨與庫存資料。
- 存在重疊活動時，不能將效果完全歸因於單一促銷。
- 觀察期間不完整的活動應降低判讀信心。
        """
    )