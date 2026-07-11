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


from src.ai_advisor import (
    ask_gemini_advisor,
    build_advisor_context,
)

from src.session_helpers import (
    initialize_session_state,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.set_page_config(
    page_title="AI 行銷策略顧問",
    page_icon="🤖",
    layout="wide",
)

st.title("AI 行銷策略顧問")

st.write(
    "根據活動成效、策略分類與資料限制，"
    "協助解讀分析結果並規劃下一期促銷測試。"
)

st.caption(
    "AI 回答屬於決策輔助。"
    "實際執行仍應搭配成本、毛利、庫存與商業目標判斷。"
)


# =========================================================
# 取得既有分析資料
# =========================================================

strategy_report_text = st.session_state.get(
    "strategy_report_text"
)

strategy_dataframe = st.session_state.get(
    "strategy_report_dataframe"
)

performance_dataframe = st.session_state.get(
    "activity_performance_dataframe"
)


missing_sources = []

if performance_dataframe is None:
    missing_sources.append(
        "活動成效分析"
    )

if strategy_report_text is None:
    missing_sources.append(
        "策略文字報告"
    )


if missing_sources:
    st.warning(
        "目前尚缺少："
        + "、".join(missing_sources)
        + "。請先完成「活動成效分析」"
        "與「策略建議報表」。"
    )
    st.stop()


if performance_dataframe.empty:
    st.warning(
        "目前沒有可提供給 AI 顧問的活動成效資料。"
    )
    st.stop()


performance = performance_dataframe.copy()


# =========================================================
# 分析資料型別整理
# =========================================================

numeric_columns = [
    "uplift_rate",
    "post_change_rate",
    "campaign_total_sales",
    "estimated_revenue",
    "baseline_average_daily_sales",
    "campaign_average_daily_sales",
    "post_average_daily_sales",
]

for column in numeric_columns:
    if column in performance.columns:
        performance[column] = pd.to_numeric(
            performance[column],
            errors="coerce",
        )


boolean_columns = [
    "all_periods_complete",
    "baseline_complete",
    "campaign_complete",
    "post_complete",
]

for column in boolean_columns:
    if column in performance.columns:
        performance[column] = (
            performance[column]
            .fillna(False)
            .astype(bool)
        )


# =========================================================
# 建立 AI 分析背景
# =========================================================

advisor_context = build_advisor_context(
    strategy_report_text=(
        strategy_report_text
    ),
    strategy_dataframe=(
        strategy_dataframe
    ),
    performance_dataframe=(
        performance_dataframe
    ),
)

st.session_state[
    "ai_last_context"
] = advisor_context


# =========================================================
# 初始對話
# =========================================================

if not st.session_state.get(
    "ai_chat_messages"
):
    st.session_state[
        "ai_chat_messages"
    ] = [
        {
            "role": "assistant",
            "content": (
                "你好，我是 AI 行銷策略顧問。\n\n"
                "我可以根據目前的活動成效與策略報告，"
                "協助你判讀高低成效活動、整理資料限制，"
                "以及規劃下一期促銷測試。"
            ),
        }
    ]


# =========================================================
# 頁面左右配置
# =========================================================

summary_column, chat_column = st.columns(
    [1, 2.2],
    gap="large",
)


# =========================================================
# 左側：分析背景與快捷提問
# =========================================================

with summary_column:
    st.subheader("目前分析背景")

    activity_count = len(
        performance
    )

    valid_uplift = performance.dropna(
        subset=["uplift_rate"]
    ).copy()

    high_activity_count = int(
        (
            performance[
                "uplift_rate"
            ] >= 0.20
        ).sum()
    )

    low_activity_count = int(
        (
            performance[
                "uplift_rate"
            ] < 0
        ).sum()
    )

    median_uplift = (
        valid_uplift[
            "uplift_rate"
        ].median()
        if not valid_uplift.empty
        else pd.NA
    )

    if (
        "all_periods_complete"
        in performance.columns
        and activity_count > 0
    ):
        complete_rate = (
            performance[
                "all_periods_complete"
            ].mean()
        )

    else:
        complete_rate = pd.NA


    metric_col1, metric_col2 = st.columns(2)

    metric_col1.metric(
        "活動數",
        f"{activity_count:,}",
    )

    metric_col2.metric(
        "高成效活動",
        f"{high_activity_count:,}",
    )


    metric_col3, metric_col4 = st.columns(2)

    metric_col3.metric(
        "低成效活動",
        f"{low_activity_count:,}",
    )

    metric_col4.metric(
        "提升率中位數",
        (
            f"{median_uplift:.1%}"
            if pd.notna(median_uplift)
            else "-"
        ),
    )


    st.metric(
        "完整觀察期間比例",
        (
            f"{complete_rate:.1%}"
            if pd.notna(complete_rate)
            else "-"
        ),
    )


    st.divider()

    st.subheader("快捷問題")

    shortcut_question = None


    if st.button(
        "哪些活動最值得延續？",
        use_container_width=True,
        key="product_ai_best_activity",
    ):
        shortcut_question = (
            "請根據目前分析，找出最值得延續的活動。"
            "請說明數據依據、資料限制，"
            "以及下一步可以如何驗證。"
        )


    if st.button(
        "低成效活動可能有哪些原因？",
        use_container_width=True,
        key="product_ai_low_activity",
    ):
        shortcut_question = (
            "請分析目前低成效活動可能的原因。"
            "請區分資料能確認的觀察、合理推測，"
            "以及仍需要補充的資料。"
        )


    if st.button(
        "下一期促銷應如何規劃？",
        use_container_width=True,
        key="product_ai_next_campaign",
    ):
        shortcut_question = (
            "請根據目前結果提出下一期促銷規劃。"
            "內容請包含優先活動、測試設計、"
            "追蹤指標與風險控制。"
        )


    if st.button(
        "目前分析有哪些限制？",
        use_container_width=True,
        key="product_ai_data_limit",
    ):
        shortcut_question = (
            "請整理目前分析的資料限制、"
            "不能直接下的結論，以及應補充的資料。"
        )


    if st.button(
        "整理成主管摘要",
        use_container_width=True,
        key="product_ai_manager_summary",
    ):
        shortcut_question = (
            "請將目前分析整理成主管可快速閱讀的摘要。"
            "請包含關鍵發現、主要風險、"
            "建議行動與需要補充的資料。"
        )


    st.divider()

    st.subheader("對話設定")

    if st.button(
        "清除對話紀錄",
        use_container_width=True,
        key="product_ai_clear_chat",
    ):
        st.session_state[
            "ai_chat_messages"
        ] = []

        st.rerun()


    st.caption(
        "清除對話不會刪除銷量、活動或分析資料。"
    )


    with st.expander(
        "AI 使用的資料範圍"
    ):
        st.write(
            "AI 顧問目前會讀取："
        )

        st.markdown(
            """
            - 活動前、中、後銷量
            - 活動提升率
            - 活動總銷量
            - 推估營收
            - 策略分類
            - 活動重疊情況
            - 資料完整度與信心
            - 規則式策略報告
            """
        )

        st.warning(
            "目前沒有完整成本與毛利資料，"
            "因此 AI 不應宣稱活動有實際獲利。"
        )


# =========================================================
# 右側：主要 AI 對話
# =========================================================

with chat_column:
    st.subheader("策略顧問對話")

    st.info(
        "可以直接詢問活動成效、低效原因、"
        "促銷規劃或資料限制。"
    )


    chat_container = st.container(
        border=True,
        height=620,
    )


    with chat_container:
        for message in st.session_state[
            "ai_chat_messages"
        ]:
            role = message.get(
                "role",
                "assistant",
            )

            content = message.get(
                "content",
                "",
            )

            with st.chat_message(role):
                st.markdown(content)


    typed_question = st.chat_input(
        "輸入行銷策略問題……",
        key="product_ai_chat_input",
    )


# =========================================================
# 決定本次問題來源
# =========================================================

user_question = (
    shortcut_question
    if shortcut_question
    else typed_question
)


# =========================================================
# 呼叫 AI
# =========================================================

if user_question:
    st.session_state[
        "ai_chat_messages"
    ].append(
        {
            "role": "user",
            "content": user_question,
        }
    )

    try:
        with st.spinner(
            "AI 顧問正在分析資料……"
        ):
            answer = ask_gemini_advisor(
                user_question=user_question,
                advisor_context=advisor_context,
                chat_messages=(
                    st.session_state[
                        "ai_chat_messages"
                    ]
                ),
            )

        st.session_state[
            "ai_chat_messages"
        ].append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        st.rerun()

    except Exception as error:
        st.error(
            "AI 顧問目前無法完成回答："
            f"{error}"
        )


# =========================================================
# 重要使用提醒
# =========================================================

st.divider()

st.caption(
    "AI 顧問的回答應視為分析與討論起點。"
    "活動期間銷量上升不等於已證明因果，"
    "推估營收也不等於實際營收或獲利。"
)