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
    sys.path.insert(0, str(PROJECT_ROOT))


from src.report_generator import (
    generate_management_pdf,
)

from src.session_helpers import (
    initialize_session_state,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.set_page_config(
    page_title="主管報表中心",
    page_icon="📄",
    layout="wide",
)

st.title("主管報表中心")

st.write(
    "將銷量概況、活動成效、策略建議與資料限制"
    "整理成可下載的主管 PDF 報告。"
)

st.caption(
    "本頁僅讀取現有分析結果，不會重新計算或修改資料。"
)


# =========================================================
# 取得資料
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


missing_sources = []

if performance_dataframe is None:
    missing_sources.append(
        "活動成效分析"
    )

if strategy_dataframe is None:
    missing_sources.append(
        "策略建議資料"
    )

if strategy_report_text is None:
    missing_sources.append(
        "策略文字報告"
    )


if missing_sources:
    st.warning(
        "目前尚缺少："
        + "、".join(missing_sources)
        + "。請先完成「執行成效分析」"
        "與「產生策略報告」。"
    )
    st.stop()


if performance_dataframe.empty:
    st.warning(
        "目前沒有活動成效資料可產生報告。"
    )
    st.stop()


# =========================================================
# 報表內容預覽
# =========================================================

performance = performance_dataframe.copy()

performance["uplift_rate"] = pd.to_numeric(
    performance["uplift_rate"],
    errors="coerce",
)

activity_count = len(performance)

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
    performance["uplift_rate"].median()
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


st.info(
    "PDF 將包含分析概況、最佳與較差活動、"
    "三類策略建議、資料品質限制及主管策略摘要。"
)


# =========================================================
# 最佳與最差活動預覽
# =========================================================

valid_performance = performance.dropna(
    subset=["uplift_rate"]
).copy()


preview_left, preview_right = st.columns(2)


with preview_left:
    st.subheader("表現最佳活動")

    if valid_performance.empty:
        st.info(
            "目前沒有可計算提升率的活動。"
        )

    else:
        best_activity = (
            valid_performance.sort_values(
                "uplift_rate",
                ascending=False,
            )
            .iloc[0]
        )

        with st.container(border=True):
            st.markdown(
                "### "
                + str(
                    best_activity.get(
                        "product_name",
                        "未提供商品名稱",
                    )
                )
            )

            metric_col1, metric_col2 = (
                st.columns(2)
            )

            metric_col1.metric(
                "活動提升率",
                f"{best_activity['uplift_rate']:.1%}",
            )

            metric_col2.metric(
                "活動總銷量",
                (
                    f"{best_activity.get('campaign_total_sales', 0):,.0f}"
                ),
            )

            st.caption(
                "商品編號："
                + str(
                    best_activity.get(
                        "product_id",
                        "-",
                    )
                )
            )


with preview_right:
    st.subheader("表現較差活動")

    if valid_performance.empty:
        st.info(
            "目前沒有可計算提升率的活動。"
        )

    else:
        worst_activity = (
            valid_performance.sort_values(
                "uplift_rate",
                ascending=True,
            )
            .iloc[0]
        )

        with st.container(border=True):
            st.markdown(
                "### "
                + str(
                    worst_activity.get(
                        "product_name",
                        "未提供商品名稱",
                    )
                )
            )

            metric_col1, metric_col2 = (
                st.columns(2)
            )

            metric_col1.metric(
                "活動提升率",
                f"{worst_activity['uplift_rate']:.1%}",
            )

            metric_col2.metric(
                "活動總銷量",
                (
                    f"{worst_activity.get('campaign_total_sales', 0):,.0f}"
                ),
            )

            st.caption(
                "商品編號："
                + str(
                    worst_activity.get(
                        "product_id",
                        "-",
                    )
                )
            )


# =========================================================
# 產生 PDF
# =========================================================

st.divider()

st.subheader("產生主管報告")

st.write(
    "按下按鈕後，系統會依目前 Session State 中的"
    "最新分析結果建立 PDF。"
)


if st.button(
    "產生主管 PDF 報告",
    type="primary",
    use_container_width=True,
):
    try:
        with st.spinner(
            "正在整理活動成效與策略建議……"
        ):
            pdf_bytes = generate_management_pdf(
                sales_dataframe=sales_dataframe,
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
            "PDF 報告產生失敗："
            f"{error}"
        )


# =========================================================
# PDF 下載
# =========================================================

pdf_bytes = st.session_state.get(
    "management_report_pdf"
)


if pdf_bytes:
    report_date = datetime.now().strftime(
        "%Y%m%d_%H%M"
    )

    st.download_button(
        "下載主管 PDF 報告",
        data=pdf_bytes,
        file_name=(
            f"management_activity_report_"
            f"{report_date}.pdf"
        ),
        mime="application/pdf",
        use_container_width=True,
    )

    st.caption(
        "建議下載後確認中文字、表格換頁與內容完整性。"
    )


# =========================================================
# 報表限制
# =========================================================

st.divider()

with st.expander(
    "報表判讀限制"
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