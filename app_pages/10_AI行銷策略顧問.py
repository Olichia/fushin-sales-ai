from pathlib import Path
import sys

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


from src.ai_advisor import (
    ask_gemini_advisor,
    build_advisor_context,
)

from src.session_helpers import (
    initialize_session_state,
)


# =========================================================
# 初始化
# =========================================================

initialize_session_state()

st.title("AI 行銷策略顧問")

st.write(
    "根據活動成效分析與規則式策略報告，"
    "協助解讀結果、整理風險並提出下一步建議。"
)

st.warning(
    "AI 回答屬於決策輔助。"
    "請搭配實際成本、毛利、庫存與商業目標判斷。"
)


# =========================================================
# 取得分析資料
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

if strategy_report_text is None:
    missing_sources.append("策略文字報告")

if performance_dataframe is None:
    missing_sources.append("活動成效分析")


if missing_sources:
    st.error(
        "尚缺少："
        + "、".join(missing_sources)
        + "。請先完成「活動成效分析」"
        "與「策略建議報表」。"
    )
    st.stop()


# =========================================================
# 建立 AI 背景
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
# 初始歡迎訊息
# =========================================================

if not st.session_state.ai_chat_messages:
    st.session_state.ai_chat_messages = [
        {
            "role": "assistant",
            "content": (
                "你好，我是 AI 行銷策略顧問。"
                "我可以根據目前的活動成效分析，"
                "協助你找出高成效活動、低效原因、"
                "資料限制與下一期測試方向。"
            ),
        }
    ]


# =========================================================
# 側邊欄快捷問題
# =========================================================

st.sidebar.header("AI 顧問設定")

if st.sidebar.button(
    "清除對話紀錄"
):
    st.session_state.ai_chat_messages = []

    st.rerun()


st.sidebar.caption(
    "清除對話不會刪除分析資料。"
)


st.subheader("建議提問")

question_col1, question_col2 = st.columns(2)

with question_col1:
    ask_best_activity = st.button(
        "哪些活動最值得延續？",
        use_container_width=True,
    )

    ask_low_activity = st.button(
        "為什麼有些活動表現差？",
        use_container_width=True,
    )


with question_col2:
    ask_next_plan = st.button(
        "下一期促銷應如何規劃？",
        use_container_width=True,
    )

    ask_data_risk = st.button(
        "目前資料有哪些限制？",
        use_container_width=True,
    )


shortcut_question = None

if ask_best_activity:
    shortcut_question = (
        "請分析哪些活動最值得延續，"
        "並說明數據依據、限制與下一步測試方式。"
    )

elif ask_low_activity:
    shortcut_question = (
        "請分析低成效活動可能的原因。"
        "請區分資料能確認的事實、合理推測"
        "與仍需補充的資料。"
    )

elif ask_next_plan:
    shortcut_question = (
        "請根據目前結果，提出下一期促銷規劃。"
        "請包含優先商品、活動形式、測試方法"
        "及應追蹤的指標。"
    )

elif ask_data_risk:
    shortcut_question = (
        "請整理目前分析的資料限制、"
        "不能直接下的結論，以及應補充的資料。"
    )


# =========================================================
# 顯示歷史對話
# =========================================================

st.divider()

for message in (
    st.session_state.ai_chat_messages
):
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


# =========================================================
# 接收問題
# =========================================================

typed_question = st.chat_input(
    "輸入你想詢問的行銷策略問題……"
)

user_question = (
    shortcut_question
    if shortcut_question
    else typed_question
)


if user_question:
    st.session_state.ai_chat_messages.append(
        {
            "role": "user",
            "content": user_question,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_question)

    try:
        with st.chat_message("assistant"):
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

            st.markdown(answer)

        st.session_state.ai_chat_messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

    except Exception as error:
        st.error(
            "AI 顧問目前無法完成回答："
            f"{error}"
        )