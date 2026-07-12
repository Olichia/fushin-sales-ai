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


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.set_page_config(
    page_title="資料管理中心",
    page_icon="🗂️",
    layout="wide",
)

st.title("資料管理中心")

st.write(
    "集中查看銷量資料、活動資料、品質檢查與系統處理狀態，"
    "並依照建議順序完成資料分析流程。"
)

st.caption(
    "本頁只顯示目前狀態，不會修改、刪除或重新計算任何資料。"
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


# =========================================================
# 判斷處理狀態
# =========================================================

sales_uploaded = (
    uploaded_file_name is not None
    and uploaded_dataframe is not None
)

mapping_completed = bool(
    column_mapping
)

sales_standardized = (
    standardized_dataframe is not None
)

activity_uploaded = bool(
    activity_uploaded_files
)

activity_standardized = (
    activity_standardized_dataframe is not None
)

integration_completed = (
    integrated_dataframe is not None
)

performance_completed = (
    performance_dataframe is not None
)

strategy_completed = (
    strategy_dataframe is not None
)


workflow_steps = [
    {
        "編號": 1,
        "名稱": "銷量資料上傳",
        "完成": sales_uploaded,
        "說明": "上傳銷量 Excel 並選擇正確工作表。",
        "頁面": "銷量資料上傳",
    },
    {
        "編號": 2,
        "名稱": "欄位設定",
        "完成": mapping_completed,
        "說明": "將日期、商品編號、商品名稱與銷量對應至系統欄位。",
        "頁面": "欄位設定",
    },
    {
        "編號": 3,
        "名稱": "銷量資料品質",
        "完成": sales_standardized,
        "說明": "執行銷量標準化與資料品質檢查。",
        "頁面": "銷量資料品質",
    },
    {
        "編號": 4,
        "名稱": "活動資料上傳",
        "完成": activity_uploaded,
        "說明": "上傳各月份品牌活動 Excel。",
        "頁面": "活動資料上傳",
    },
    {
        "編號": 5,
        "名稱": "活動資料品質",
        "完成": activity_standardized,
        "說明": "解析活動期間、價格、活動日曆與優惠內容。",
        "頁面": "活動資料品質",
    },
    {
        "編號": 6,
        "名稱": "建立整合資料",
        "完成": integration_completed,
        "說明": "將每日銷量與商品活動、平台活動及優惠整合。",
        "頁面": "建立整合資料",
    },
    {
        "編號": 7,
        "名稱": "執行成效分析",
        "完成": performance_completed,
        "說明": "比較活動前、活動期間與活動後的銷量。",
        "頁面": "執行成效分析",
    },
    {
        "編號": 8,
        "名稱": "產生策略報告",
        "完成": strategy_completed,
        "說明": "產生建議延續、優化與檢討的策略分類。",
        "頁面": "產生策略報告",
    },
]


completed_step_count = sum(
    step["完成"]
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

st.subheader("整體處理進度")

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
    st.progress(
        completion_rate,
        text=(
            f"資料分析流程已完成 "
            f"{completed_step_count} 個步驟"
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
        "所有主要資料處理步驟均已完成。"
        "現在可以前往「分析總覽」、「活動洞察」、"
        "「策略中心」或「AI 策略顧問」。"
    )

else:
    st.info(
        f"**建議下一步："
        f"{next_incomplete_step['名稱']}**\n\n"
        f"{next_incomplete_step['說明']}\n\n"
        f"請從左側導覽進入「"
        f"{next_incomplete_step['頁面']}」。"
    )


# =========================================================
# 流程卡片
# =========================================================

st.divider()

st.subheader("資料處理流程")


for row_start in range(
    0,
    len(workflow_steps),
    4,
):
    row_steps = workflow_steps[
        row_start:row_start + 4
    ]

    columns = st.columns(
        len(row_steps)
    )

    for column, step in zip(
        columns,
        row_steps,
    ):
        with column:
            with st.container(
                border=True
            ):
                if step["完成"]:
                    st.success(
                        f"步驟 {step['編號']}｜已完成"
                    )
                else:
                    st.warning(
                        f"步驟 {step['編號']}｜待處理"
                    )

                st.markdown(
                    f"### {step['名稱']}"
                )

                st.write(
                    step["說明"]
                )

                st.caption(
                    f"導覽位置：{step['頁面']}"
                )


# =========================================================
# 銷量資料狀態
# =========================================================

st.divider()

status_col1, status_col2 = st.columns(2)


with status_col1:
    st.subheader("銷量資料")

    with st.container(border=True):
        if sales_uploaded:
            st.success("銷量檔案已載入")
        else:
            st.warning("尚未載入銷量檔案")

        st.write(
            "**目前檔案：** "
            + (
                str(uploaded_file_name)
                if uploaded_file_name
                else "尚未上傳"
            )
        )

        raw_sales_count = (
            len(uploaded_dataframe)
            if uploaded_dataframe is not None
            else 0
        )

        standardized_sales_count = (
            len(standardized_dataframe)
            if standardized_dataframe is not None
            else 0
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
            column_mapping.values()
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


# =========================================================
# 活動資料狀態
# =========================================================

with status_col2:
    st.subheader("活動資料")

    with st.container(border=True):
        if activity_uploaded:
            st.success("活動檔案已載入")
        else:
            st.warning("尚未載入活動檔案")

        activity_file_count = len(
            activity_uploaded_files
        )

        st.metric(
            "已上傳活動檔案",
            f"{activity_file_count:,}",
        )

        if activity_uploaded_files:
            st.write("**檔案清單：**")

            for file_name in sorted(
                activity_uploaded_files.keys()
            ):
                st.write(
                    f"• {file_name}"
                )

        else:
            st.caption(
                "尚無活動檔案。"
            )

        activity_metric_col1, activity_metric_col2 = (
            st.columns(2)
        )

        activity_metric_col1.metric(
            "商品活動期間",
            (
                f"{len(activity_standardized_dataframe):,}"
                if activity_standardized_dataframe is not None
                else "0"
            ),
        )

        activity_metric_col2.metric(
            "活動日曆",
            (
                f"{len(activity_calendar_dataframe):,}"
                if activity_calendar_dataframe is not None
                else "0"
            ),
        )

        st.metric(
            "優惠內容",
            (
                f"{len(promotion_benefits_dataframe):,}"
                if promotion_benefits_dataframe is not None
                else "0"
            ),
        )


# =========================================================
# 品質與問題狀態
# =========================================================

st.divider()

st.subheader("資料品質與待確認事項")


activity_issue_count = (
    len(activity_issues_dataframe)
    if activity_issues_dataframe is not None
    else 0
)

integration_issue_count = (
    len(integration_issues_dataframe)
    if integration_issues_dataframe is not None
    else 0
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
        "資料中仍有待確認問題。"
        "這些項目不一定代表錯誤，"
        "但在解讀活動成效前應先確認。"
    )


# =========================================================
# 問題明細
# =========================================================

if activity_issue_count > 0:
    with st.expander(
        "查看活動資料問題"
    ):
        st.dataframe(
            activity_issues_dataframe,
            use_container_width=True,
            hide_index=True,
        )


if integration_issue_count > 0:
    with st.expander(
        "查看整合資料問題"
    ):
        st.dataframe(
            integration_issues_dataframe,
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# 分析輸出狀態
# =========================================================

st.divider()

st.subheader("分析輸出狀態")


output_col1, output_col2, output_col3 = (
    st.columns(3)
)


with output_col1:
    with st.container(border=True):
        st.markdown("### 整合分析資料")

        integrated_count = (
            len(integrated_dataframe)
            if integrated_dataframe is not None
            else 0
        )

        st.metric(
            "每日商品紀錄",
            f"{integrated_count:,}",
        )

        if integration_completed:
            st.success("已建立")
        else:
            st.info("尚未建立")


with output_col2:
    with st.container(border=True):
        st.markdown("### 活動成效分析")

        performance_count = (
            len(performance_dataframe)
            if performance_dataframe is not None
            else 0
        )

        st.metric(
            "活動分析筆數",
            f"{performance_count:,}",
        )

        if performance_completed:
            st.success("已完成")
        else:
            st.info("尚未完成")


with output_col3:
    with st.container(border=True):
        st.markdown("### 策略建議")

        strategy_count = (
            len(strategy_dataframe)
            if strategy_dataframe is not None
            else 0
        )

        st.metric(
            "策略建議筆數",
            f"{strategy_count:,}",
        )

        if strategy_completed:
            st.success("已產生")
        else:
            st.info("尚未產生")


# =========================================================
# 使用提醒
# =========================================================

st.divider()

st.info(
    "重新啟動 Streamlit 後，Session State 中的上傳資料可能會清空。"
    "目前 MVP 需要重新依序執行資料流程；"
    "之後可再加入資料庫或檔案暫存功能。"
)