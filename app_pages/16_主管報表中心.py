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


def safe_numeric(
    value: object,
) -> float | None:
    """安全轉換成數值。"""

    numeric_value = pd.to_numeric(
        value,
        errors="coerce",
    )

    if pd.isna(numeric_value):
        return None

    return float(numeric_value)


def render_activity_preview_card(
    *,
    eyebrow: str,
    title: str,
    activity_row: pd.Series,
    accent_class: str,
) -> None:
    """顯示最佳或較差活動預覽卡片。"""

    product_name = activity_row.get(
        "product_name",
        "未提供商品名稱",
    )

    if pd.isna(product_name):
        product_name = "未提供商品名稱"

    product_id = activity_row.get(
        "product_id",
        "-",
    )

    uplift_rate = safe_numeric(
        activity_row.get(
            "uplift_rate"
        )
    )

    campaign_total_sales = safe_numeric(
        activity_row.get(
            "campaign_total_sales",
            0,
        )
    )

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="management-activity-card {accent_class}">
                <div class="management-activity-eyebrow">
                    {eyebrow}
                </div>
                <div class="management-activity-title">
                    {title}
                </div>
                <div class="management-activity-product">
                    {product_name}
                </div>
                <div class="management-activity-id">
                    商品編號：{product_id}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        metric_col1, metric_col2 = st.columns(2)

        metric_col1.metric(
            "活動提升率",
            (
                f"{uplift_rate:.1%}"
                if uplift_rate is not None
                else "-"
            ),
        )

        metric_col2.metric(
            "活動總銷量",
            (
                f"{campaign_total_sales:,.0f}"
                if campaign_total_sales is not None
                else "-"
            ),
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


# =========================================================
# 資料完整性檢查
# =========================================================

missing_sources = []

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


performance = (
    performance_dataframe.copy()
)

strategy = (
    strategy_dataframe.copy()
)


if "uplift_rate" not in performance.columns:
    st.error(
        "活動成效資料缺少 uplift_rate 欄位，"
        "請重新執行「03 執行完整分析」。"
    )

    st.stop()


performance["uplift_rate"] = pd.to_numeric(
    performance["uplift_rate"],
    errors="coerce",
)


# =========================================================
# 報表內容摘要
# =========================================================

activity_count = len(
    performance
)

high_count = int(
    (
        performance["uplift_rate"]
        >= 0.20
    ).sum()
)

low_count = int(
    (
        performance["uplift_rate"]
        < 0
    ).sum()
)

median_uplift = (
    performance["uplift_rate"]
    .median()
)

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


st.subheader("報表內容預覽")

preview_col1, preview_col2, preview_col3, preview_col4 = (
    st.columns(4)
)

preview_col1.metric(
    "活動分析數",
    f"{activity_count:,}",
)

preview_col2.metric(
    "高成效活動",
    f"{high_count:,}",
)

preview_col3.metric(
    "低成效活動",
    f"{low_count:,}",
)

preview_col4.metric(
    "提升率中位數",
    (
        f"{median_uplift:.1%}"
        if pd.notna(median_uplift)
        else "-"
    ),
)


with st.container(border=True):
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
            **策略建議**

            - 建議延續
            - 建議優化
            - 建議檢討
            """
        )

    with report_item_col3:
        st.markdown(
            """
            **資料限制**

            - 品質問題
            - 重疊活動
            - 因果判讀限制
            """
        )


# =========================================================
# 最佳與較差活動
# =========================================================

st.divider()
st.subheader("重點活動預覽")

valid_performance = (
    performance.dropna(
        subset=["uplift_rate"]
    )
    .copy()
)

preview_left, preview_right = (
    st.columns(2)
)

if valid_performance.empty:
    st.info(
        "目前沒有可計算提升率的活動。"
    )

else:
    best_activity = (
        valid_performance
        .sort_values(
            "uplift_rate",
            ascending=False,
        )
        .iloc[0]
    )

    worst_activity = (
        valid_performance
        .sort_values(
            "uplift_rate",
            ascending=True,
        )
        .iloc[0]
    )

    with preview_left:
        render_activity_preview_card(
            eyebrow="TOP PERFORMER",
            title="表現最佳活動",
            activity_row=best_activity,
            accent_class=(
                "management-activity-best"
            ),
        )

    with preview_right:
        render_activity_preview_card(
            eyebrow="NEEDS REVIEW",
            title="表現較差活動",
            activity_row=worst_activity,
            accent_class=(
                "management-activity-worst"
            ),
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
        from src.report_generator import (
            generate_management_pdf,
        )

        with st.spinner(
            "正在整理活動成效與策略建議……"
        ):
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