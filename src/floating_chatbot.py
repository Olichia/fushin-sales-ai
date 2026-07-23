from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ai_advisor import (
    ask_gemini_advisor,
    ask_gemini_system_explainer,
    build_advisor_context,
)


# =========================================================
# 樣式：固定在右下角的浮動開關鈕
# =========================================================
#
# 面板本身改用 st.popover 承載，由 Streamlit 內建的浮動定位
# 機制處理位置，避免自行用 position:fixed + st.columns
# 造成寬度計算錯亂、面板跑版的問題。這裡只需要把觸發按鈕
# 固定在右下角即可。

def _inject_floating_chat_styles() -> None:
    st.markdown(
        """
        <style>
        /* ---------------------------------------------
           固定在畫面右下角。

           Streamlit 預設會讓這種區塊 width:100%，
           鋪滿整個視窗寬度；一旦寬度等於視窗寬度，
           「right:22px」只是把這個超寬容器的右邊界
           貼齊畫面右緣，容器裡的按鈕仍會靠左對齊，
           視覺上就跑到畫面左側去了。
           這裡強制把容器寬度收縮到剛好包住按鈕，
           並讓內容靠右對齊，才會讓按鈕本身出現在右下角。
        --------------------------------------------- */

        .st-key-floating_chatbot_root {
            position: fixed !important;
            bottom: 22px !important;
            right: 22px !important;
            left: auto !important;
            top: auto !important;
            width: fit-content !important;
            max-width: fit-content !important;
            display: flex !important;
            justify-content: flex-end !important;
            z-index: 2147483647 !important;
        }

        .st-key-floating_chatbot_root [data-testid="stPopoverButton"] {
            border-radius: 50% 50% 4px 50% !important;
            width: 60px !important;
            height: 60px !important;
            padding: 0 !important;
            font-size: 1.6rem !important;
            line-height: 1 !important;
            background: linear-gradient(135deg, #0B57C6, #073F99) !important;
            color: #FFFFFF !important;
            border: none !important;
            box-shadow: 0 6px 18px rgba(7, 63, 153, 0.35);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .st-key-floating_chatbot_root [data-testid="stPopoverButton"]:hover {
            background: linear-gradient(135deg, #1668DE, #0B57C6) !important;
            color: #FFFFFF !important;
            transform: translateY(-2px);
            box-shadow: 0 8px 22px rgba(7, 63, 153, 0.42);
        }

        /* ---------------------------------------------
           彈出面板本身：寬度收窄在畫面右側約 1/3，
           高度貼近整個網頁可視高度。
        --------------------------------------------- */

        [data-testid="stPopoverBody"] {
            width: min(33vw, 460px) !important;
            max-width: 92vw !important;
            min-width: 300px !important;
            height: min(82vh, 760px) !important;
            max-height: 82vh !important;
            display: flex !important;
            flex-direction: column !important;
        }

        /* ---------------------------------------------
           面板標題
        --------------------------------------------- */

        .st-key-floating_chat_title [data-testid="stMarkdownContainer"] p {
            margin: 0 0 0.4rem 0;
            font-size: 1.05rem;
            font-weight: 700;
            color: #172033;
        }

        /* ---------------------------------------------
           對話泡泡：助理靠左、使用者靠右，
           文字過長時自動換行，不會撐破泡泡寬度。
        --------------------------------------------- */

        [class*="st-key-floating_chat_bubble_user_"],
        [class*="st-key-floating_chat_bubble_assistant_"] {
            margin-bottom: 0.6rem;
            animation: floating-chat-fade-in 0.18s ease-out;
        }

        /* 讓「元素外層容器」也收縮成剛好包住泡泡的寬度，
           避免中間還有一層 100% 寬度的包裝把 flex 對齊蓋掉。 */

        [class*="st-key-floating_chat_bubble_user_"] [data-testid="stElementContainer"],
        [class*="st-key-floating_chat_bubble_assistant_"] [data-testid="stElementContainer"] {
            display: flex !important;
            width: 100% !important;
        }

        [class*="st-key-floating_chat_bubble_user_"] [data-testid="stElementContainer"] {
            justify-content: flex-end !important;
        }

        [class*="st-key-floating_chat_bubble_assistant_"] [data-testid="stElementContainer"] {
            justify-content: flex-start !important;
        }

        [class*="st-key-floating_chat_bubble_user_"] [data-testid="stMarkdown"] {
            display: inline-block !important;
            width: fit-content !important;
            background: linear-gradient(135deg, #0B57C6, #073F99);
            color: #FFFFFF;
            padding: 0.55rem 0.85rem !important;
            border-radius: 16px 16px 4px 16px;
            max-width: 300px !important;
            box-shadow: 0 2px 8px rgba(7, 63, 153, 0.25);
            word-wrap: break-word;
            overflow-wrap: anywhere;
        }

        [class*="st-key-floating_chat_bubble_assistant_"] [data-testid="stMarkdown"] {
            display: inline-block !important;
            width: fit-content !important;
            background: #F1F3F6;
            color: #1F2937;
            padding: 0.55rem 0.85rem !important;
            border-radius: 16px 16px 16px 4px;
            max-width: 300px !important;
            box-shadow: 0 1px 4px rgba(18, 38, 63, 0.08);
            word-wrap: break-word;
            overflow-wrap: anywhere;
        }

        [class*="st-key-floating_chat_bubble_user_"] [data-testid="stMarkdownContainer"],
        [class*="st-key-floating_chat_bubble_assistant_"] [data-testid="stMarkdownContainer"] {
            padding: 0 !important;
            margin: 0 !important;
        }

        [class*="st-key-floating_chat_bubble_user_"] [data-testid="stMarkdown"] p,
        [class*="st-key-floating_chat_bubble_assistant_"] [data-testid="stMarkdown"] p {
            margin: 0 !important;
            padding: 0 !important;
            font-size: 0.85rem !important;
            line-height: 1.5 !important;
        }

        [class*="st-key-floating_chat_bubble_user_"] [data-testid="stMarkdown"] p {
            color: #FFFFFF !important;
        }

        [class*="st-key-floating_chat_bubble_user_"] [data-testid="stMarkdown"] p + p,
        [class*="st-key-floating_chat_bubble_assistant_"] [data-testid="stMarkdown"] p + p {
            margin-top: 0.5em !important;
        }

        @keyframes floating-chat-fade-in {
            from {
                opacity: 0;
                transform: translateY(4px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .st-key-floating_chat_panel [data-testid="stChatInput"] {
            border-radius: 999px;
        }

        /* ---------------------------------------------
           對話紀錄區高度：填滿面板剩餘空間，
           並隨網頁可視高度調整。
        --------------------------------------------- */

        .st-key-floating_chat_history {
            height: min(58vh, 560px) !important;
            flex: 1 1 auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 浮動 AI 顧問視窗
# =========================================================

FLOATING_CHAT_GREETING = (
    "你好，我是 AI 策略顧問\n\n"
    "如果活動成效與策略報告已經分析完成，"
    "我可以協助解讀高低成效活動、整理資料限制，"
    "並規劃下一期促銷測試。\n\n"
    "如果還沒上傳或分析資料，也可以先問我"
    "系統定位、資料清洗流程或運算邏輯是什麼。"
)


def render_floating_chatbot() -> None:
    """
    在畫面右下角顯示可彈出的 AI 顧問浮動視窗。

    對話紀錄（ai_chat_messages）與「AI 顧問」分頁共用同一份，
    因此在任一邊輸入的內容，切換到另一邊也看得到。

    當活動成效與策略報告尚未整合完成時，
    不會直接擋住問答，而是改用系統說明模式，
    僅根據系統本身的定位、清洗流程與運算邏輯回答，
    不會捏造任何實際商品或成效數字。
    """

    if not st.session_state.get("ai_chat_messages"):
        st.session_state["ai_chat_messages"] = [
            {
                "role": "assistant",
                "content": FLOATING_CHAT_GREETING,
            }
        ]

    _inject_floating_chat_styles()

    with st.container(key="floating_chatbot_root"):
        with st.popover(
            ":material/chat_bubble:",
            width=380,
            help="開啟 AI 策略顧問",
        ):
            with st.container(key="floating_chat_panel"):
                _render_floating_chat_panel()


def _get_analysis_sources() -> tuple[str | None, pd.DataFrame | None, pd.DataFrame | None, bool]:
    strategy_report_text = st.session_state.get(
        "strategy_report_text"
    )
    strategy_dataframe = st.session_state.get(
        "strategy_report_dataframe"
    )
    performance_dataframe = st.session_state.get(
        "activity_performance_dataframe"
    )

    data_ready = (
        strategy_report_text is not None
        and performance_dataframe is not None
        and isinstance(performance_dataframe, pd.DataFrame)
        and not performance_dataframe.empty
    )

    return (
        strategy_report_text,
        strategy_dataframe,
        performance_dataframe,
        data_ready,
    )


def _render_floating_chat_panel() -> None:
    with st.container(key="floating_chat_title"):
        st.markdown(":material/smart_toy: **AI 策略顧問**")

    (
        strategy_report_text,
        strategy_dataframe,
        performance_dataframe,
        data_ready,
    ) = _get_analysis_sources()

    with st.container(key="floating_chat_history", height=400):
        for index, message in enumerate(
            st.session_state["ai_chat_messages"]
        ):
            role = message.get("role", "assistant")
            content = message.get("content", "")

            bubble_key = f"floating_chat_bubble_{role}_{index}"
            avatar = ":material/person:" if role == "user" else ":material/smart_toy:"

            with st.container(key=bubble_key):
                st.markdown(f"{avatar} {content}")

    if not data_ready:
        st.caption(
            "目前尚未完成活動成效與策略報告分析，"
            "仍可詢問系統定位、資料清洗流程或分析邏輯，"
            "完整數據問答請先完成「活動成效分析」與「策略建議報表」。"
        )

    typed_question = st.chat_input(
        "輸入問題……",
        key="floating_chat_input",
    )

    if st.button(
        "清除對話紀錄",
        key="floating_chat_clear",
        use_container_width=True,
    ):
        st.session_state["ai_chat_messages"] = [
            {
                "role": "assistant",
                "content": FLOATING_CHAT_GREETING,
            }
        ]
        st.rerun()

    if typed_question:
        st.session_state["ai_chat_messages"].append(
            {
                "role": "user",
                "content": typed_question,
            }
        )

        try:
            with st.spinner("AI 顧問正在分析……"):
                if data_ready:
                    advisor_context = build_advisor_context(
                        strategy_report_text=strategy_report_text,
                        strategy_dataframe=strategy_dataframe,
                        performance_dataframe=performance_dataframe,
                    )

                    st.session_state["ai_last_context"] = advisor_context

                    answer = ask_gemini_advisor(
                        user_question=typed_question,
                        advisor_context=advisor_context,
                        chat_messages=st.session_state["ai_chat_messages"],
                    )

                else:
                    answer = ask_gemini_system_explainer(
                        user_question=typed_question,
                        chat_messages=st.session_state["ai_chat_messages"],
                    )

            st.session_state["ai_chat_messages"].append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            st.rerun()

        except Exception as error:
            st.error(f"AI 顧問目前無法完成回答：{error}")
