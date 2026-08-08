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


from src.column_labels import default_column_config
from src.session_helpers import initialize_session_state


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()


# =========================================================
# 小工具函式
# =========================================================

def dataframe_exists(value: object) -> bool:
    """判斷物件是否為非空 DataFrame。"""

    return (
        isinstance(value, pd.DataFrame)
        and not value.empty
    )


def dataframe_row_count(value: object) -> int:
    """安全取得 DataFrame 筆數。"""

    if isinstance(value, pd.DataFrame):
        return len(value)

    return 0


def render_status_badge(
    completed: bool,
    completed_text: str = "已完成",
    pending_text: str = "待處理",
) -> None:
    """顯示流程狀態標籤。"""

    css_class = (
        "workflow-badge workflow-badge-completed"
        if completed
        else "workflow-badge workflow-badge-pending"
    )

    text = (
        completed_text
        if completed
        else pending_text
    )

    st.markdown(
        f'<span class="{css_class}">{text}</span>',
        unsafe_allow_html=True,
    )


# =========================================================
# 頁面標題
# =========================================================

st.markdown(
    """
    <div class="step-label">WORKFLOW CENTER</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>開始使用</h1>
    </div>

    <p class="product-page-description">
        依序完成銷量資料處理、活動資料處理與完整分析，
        系統就會建立可供分析總覽、活動洞察、策略中心、
        主管報表及 AI 策略顧問使用的成果資料。
    </p>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 讀取 Session State
# =========================================================

uploaded_file_name = st.session_state.get(
    "uploaded_file_name"
)

uploaded_dataframe = st.session_state.get(
    "uploaded_dataframe"
)

column_mapping = st.session_state.get(
    "column_mapping",
    {},
)

standardized_dataframe = st.session_state.get(
    "standardized_dataframe"
)

sales_data_confirmed = bool(
    st.session_state.get(
        "sales_data_confirmed",
        False,
    )
)

activity_uploaded_files = st.session_state.get(
    "activity_uploaded_files",
    {},
)

activity_standardized_dataframe = st.session_state.get(
    "activity_standardized_dataframe"
)

activity_calendar_dataframe = st.session_state.get(
    "activity_calendar_dataframe"
)

promotion_benefits_dataframe = st.session_state.get(
    "promotion_benefits_dataframe"
)

activity_issues_dataframe = st.session_state.get(
    "activity_issues_dataframe"
)

activity_data_confirmed = bool(
    st.session_state.get(
        "activity_data_confirmed",
        False,
    )
)

integrated_dataframe = st.session_state.get(
    "integrated_sales_activity_dataframe"
)

integration_issues_dataframe = st.session_state.get(
    "integration_issues_dataframe"
)

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)

strategy_dataframe = st.session_state.get(
    "strategy_report_dataframe"
)

strategy_report_text = str(
    st.session_state.get(
        "strategy_report_text",
        "",
    )
)

full_analysis_completed = bool(
    st.session_state.get(
        "full_analysis_completed",
        False,
    )
)


# =========================================================
# 判斷新版三步驟流程狀態
# =========================================================

sales_uploaded = (
    uploaded_file_name is not None
    and isinstance(
        uploaded_dataframe,
        pd.DataFrame,
    )
)

sales_standardized = dataframe_exists(
    standardized_dataframe
)

sales_ready = (
    sales_data_confirmed
    and sales_standardized
)

activity_uploaded = bool(
    activity_uploaded_files
)

activity_standardized = dataframe_exists(
    activity_standardized_dataframe
)

activity_ready = (
    activity_data_confirmed
    and activity_standardized
)

analysis_outputs_ready = (
    dataframe_exists(integrated_dataframe)
    and dataframe_exists(performance_dataframe)
    and (
        dataframe_exists(strategy_dataframe)
        or bool(strategy_report_text.strip())
    )
)

analysis_ready = (
    sales_ready
    and activity_ready
    and full_analysis_completed
    and analysis_outputs_ready
)

# 銷量／活動資料不會在啟動時從資料庫回填，所以這個頁面的
# 「目前進度」必須反映「這個 session 有沒有真的重新上傳並
# 確認過」；下方的分析輸出／品質問題預覽也只在 analysis_ready
# 成立時才顯示，避免背景保留的舊分析結果讓這個頁面看起來
# 「已經完成」。舊分析結果的瀏覽只在「執行完整分析」與
# 之後的成果頁面提供。
if not analysis_ready:
    integrated_dataframe = pd.DataFrame()
    integration_issues_dataframe = pd.DataFrame()
    performance_dataframe = pd.DataFrame()
    strategy_dataframe = pd.DataFrame()
    strategy_report_text = ""


workflow_steps = [
    {
        "編號": "01",
        "名稱": "銷量資料處理",
        "完成": sales_ready,
        "圖示": "📊",
        "說明": (
            "上傳銷量 Excel、選擇工作表、確認必要欄位，"
            "完成資料標準化與品質檢查。"
        ),
        "頁面": "01 銷量資料處理",
        "狀態說明": (
            "銷量資料已完成確認"
            if sales_ready
            else "尚未完成銷量資料確認"
        ),
    },
    {
        "編號": "02",
        "名稱": "活動資料處理",
        "完成": activity_ready,
        "圖示": "🏷️",
        "說明": (
            "上傳月份活動 Excel，確認月份對應，"
            "建立活動價格、活動日曆、優惠與問題清單。"
        ),
        "頁面": "02 活動資料處理",
        "狀態說明": (
            "活動資料已完成確認"
            if activity_ready
            else "尚未完成活動資料確認"
        ),
    },
    {
        "編號": "03",
        "名稱": "執行完整分析",
        "完成": analysis_ready,
        "圖示": "▶️",
        "說明": (
            "一次完成資料整合、活動成效分析與策略報告產生。"
        ),
        "頁面": "03 執行完整分析",
        "狀態說明": (
            "完整分析已成功完成"
            if analysis_ready
            else "等待執行完整分析"
        ),
    },
]


completed_step_count = sum(
    int(step["完成"])
    for step in workflow_steps
)

total_step_count = len(
    workflow_steps
)

completion_rate = (
    completed_step_count
    / total_step_count
)


# =========================================================
# 整體進度
# =========================================================

st.subheader("目前進度")

progress_col1, progress_col2, progress_col3 = (
    st.columns([1, 1, 2])
)

with progress_col1:
    st.metric(
        "已完成步驟",
        f"{completed_step_count}／{total_step_count}",
    )

with progress_col2:
    st.metric(
        "完成率",
        f"{completion_rate:.0%}",
    )

with progress_col3:
    with st.container(border=True):
        st.markdown(
            '<div class="progress-card-title">完整分析流程</div>',
            unsafe_allow_html=True,
        )

        st.progress(
            completion_rate,
            text=(
                f"已完成 {completed_step_count} 個步驟，"
                f"尚有 {total_step_count - completed_step_count} 個步驟"
            ),
        )


# =========================================================
# 建議下一步
# =========================================================

next_incomplete_step = next(
    (
        step
        for step in workflow_steps
        if not step["完成"]
    ),
    None,
)

if next_incomplete_step is None:
    st.success(
        "三個主要步驟都已完成。現在可以前往成果與決策區，"
        "查看分析總覽、活動洞察、策略中心、主管報表，"
        "或向 AI 策略顧問提問。"
    )

else:
    st.markdown(
        f"""
        <div class="next-step-panel">
            <div class="next-step-eyebrow">建議下一步</div>
            <div class="next-step-title">
                {next_incomplete_step['編號']}｜
                {next_incomplete_step['名稱']}
            </div>
            <div class="next-step-description">
                {next_incomplete_step['說明']}
            </div>
            <div class="next-step-location">
                請從左側導覽進入「{next_incomplete_step['頁面']}」
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 三步驟流程卡片
# =========================================================

st.subheader("操作流程")

step_columns = st.columns(3)

for column, step in zip(
    step_columns,
    workflow_steps,
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
                            STEP {step['編號']}
                        </div>
                        <div class="workflow-step-title">
                            {step['名稱']}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            render_status_badge(
                step["完成"]
            )

            st.write(
                step["說明"]
            )

            st.caption(
                step["狀態說明"]
            )

            st.caption(
                f"導覽位置：{step['頁面']}"
            )


# =========================================================
# 資料準備狀態
# =========================================================

st.divider()
st.subheader("資料準備狀態")

sales_col, activity_col = st.columns(2)

with sales_col:
    with st.container(border=True):
        st.markdown(
            """
            <div class="status-card-heading">
                <div class="status-card-icon">📊</div>
                <div>
                    <div class="status-card-title">銷量資料</div>
                    <div class="status-card-subtitle">
                        Excel、工作表、欄位與標準化結果
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_status_badge(
            sales_ready,
            completed_text="已確認",
            pending_text="尚未確認",
        )

        st.write(
            "**目前檔案：** "
            + (
                str(uploaded_file_name)
                if uploaded_file_name
                else "尚未上傳"
            )
        )

        raw_sales_count = dataframe_row_count(
            uploaded_dataframe
        )

        standardized_sales_count = dataframe_row_count(
            standardized_dataframe
        )

        sales_metric_col1, sales_metric_col2 = (
            st.columns(2)
        )

        sales_metric_col1.metric(
            "原始資料筆數",
            f"{raw_sales_count:,}",
        )

        sales_metric_col2.metric(
            "標準化筆數",
            f"{standardized_sales_count:,}",
        )

        required_mapping_fields = {
            "sale_date",
            "product_id",
            "product_name",
            "quantity",
        }

        mapped_system_fields = set(
            column_mapping.keys()
        ) if column_mapping else set()

        mapping_ready = (
            required_mapping_fields
            .issubset(mapped_system_fields)
        )

        if mapping_ready:
            st.success(
                "四個必要欄位已完成對應。"
            )
        elif column_mapping:
            missing_mapping_fields = (
                required_mapping_fields
                - mapped_system_fields
            )

            st.warning(
                "仍缺少欄位對應："
                + "、".join(
                    sorted(
                        missing_mapping_fields
                    )
                )
            )
        else:
            st.info(
                "尚未儲存欄位對應。"
            )

with activity_col:
    with st.container(border=True):
        st.markdown(
            """
            <div class="status-card-heading">
                <div class="status-card-icon">🏷️</div>
                <div>
                    <div class="status-card-title">活動資料</div>
                    <div class="status-card-subtitle">
                        月份活動、活動日曆、優惠與品質問題
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_status_badge(
            activity_ready,
            completed_text="已確認",
            pending_text="尚未確認",
        )

        st.metric(
            "已上傳活動檔案",
            f"{len(activity_uploaded_files):,}",
        )

        activity_metric_col1, activity_metric_col2 = (
            st.columns(2)
        )

        activity_metric_col1.metric(
            "商品活動期間",
            f"{dataframe_row_count(activity_standardized_dataframe):,}",
        )

        activity_metric_col2.metric(
            "活動日曆",
            f"{dataframe_row_count(activity_calendar_dataframe):,}",
        )

        st.metric(
            "優惠內容",
            f"{dataframe_row_count(promotion_benefits_dataframe):,}",
        )

        if activity_uploaded_files:
            with st.expander(
                "查看已上傳活動檔案",
                expanded=False,
            ):
                for file_name in sorted(
                    activity_uploaded_files.keys()
                ):
                    st.write(
                        f"• {file_name}"
                    )
        else:
            st.info(
                "尚未上傳活動檔案。"
            )


# =========================================================
# 完整分析輸出
# =========================================================

st.divider()
st.subheader("完整分析輸出")

integrated_count = dataframe_row_count(
    integrated_dataframe
)

performance_count = dataframe_row_count(
    performance_dataframe
)

strategy_count = dataframe_row_count(
    strategy_dataframe
)

output_col1, output_col2, output_col3 = (
    st.columns(3)
)

with output_col1:
    with st.container(border=True):
        st.markdown(
            '<div class="output-card-label">資料整合</div>',
            unsafe_allow_html=True,
        )

        st.metric(
            "整合資料筆數",
            f"{integrated_count:,}",
        )

        if dataframe_exists(integrated_dataframe):
            st.success("已建立")
        else:
            st.info("尚未建立")

with output_col2:
    with st.container(border=True):
        st.markdown(
            '<div class="output-card-label">活動成效</div>',
            unsafe_allow_html=True,
        )

        st.metric(
            "成效分析筆數",
            f"{performance_count:,}",
        )

        if dataframe_exists(performance_dataframe):
            st.success("已完成")
        else:
            st.info("尚未完成")

with output_col3:
    with st.container(border=True):
        st.markdown(
            '<div class="output-card-label">策略建議</div>',
            unsafe_allow_html=True,
        )

        st.metric(
            "策略資料筆數",
            f"{strategy_count:,}",
        )

        if (
            dataframe_exists(strategy_dataframe)
            or strategy_report_text.strip()
        ):
            st.success("已產生")
        else:
            st.info("尚未產生")


# =========================================================
# 品質問題
# =========================================================

st.divider()
st.subheader("資料品質與待確認事項")

activity_issue_count = dataframe_row_count(
    activity_issues_dataframe
)

integration_issue_count = dataframe_row_count(
    integration_issues_dataframe
)

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
        "目前系統沒有偵測到待確認的活動或整合問題。"
    )

else:
    st.warning(
        "資料中仍有待確認項目。這些項目不一定代表錯誤，"
        "但在解讀活動成效前應先確認。"
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
# 使用提醒
# =========================================================

st.divider()

st.info(
    "目前 MVP 使用 Session State 保存上傳與分析結果。"
    "重新啟動 Streamlit 後資料可能清空，"
    "屆時需重新依序完成三個步驟。"
)