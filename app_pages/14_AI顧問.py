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
    build_advisor_context,
    condense_structured_response,
    get_structured_advisor_answer,
)

from src.insight_cards import render_structured_advisor_card

from src.session_helpers import (
    initialize_session_state,
)

from src.unit_overview_helpers import (
    compute_actual_revenue_total,
    compute_risk_mask,
    compute_strategy_category,
    prepare_unit_overview_for_display,
)


# =========================================================
# 頁面初始化
# =========================================================

initialize_session_state()

st.markdown(
    """
    <div class="step-label">AI STRATEGY ADVISOR</div>

    <div class="product-page-title">
        <div class="product-page-title-bar"></div>
        <h1>AI 策略顧問</h1>
    </div>

    <p class="product-page-description">
        根據活動單位分析（同月安靜期基準、量增/降價效應拆解、
        瀑布法配對）協助解讀分析結果並規劃下一期促銷測試。
        AI 回答屬於決策輔助，實際執行仍應搭配成本、
        毛利、庫存與商業目標判斷。
    </p>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 取得既有分析資料（活動單位分析，唯一資料來源）
# =========================================================

unit_overview_raw = st.session_state.get(
    "activity_unit_overview_dataframe"
)

waterfall_summary_raw = st.session_state.get(
    "activity_waterfall_summary_dataframe"
)

unit_price_dataframe = st.session_state.get(
    "activity_unit_price_dataframe"
)

unit_analysis_completed = bool(
    st.session_state.get(
        "unit_analysis_completed",
        False,
    )
)

new_engine_ready = (
    unit_analysis_completed
    and isinstance(unit_overview_raw, pd.DataFrame)
    and not unit_overview_raw.empty
    and isinstance(waterfall_summary_raw, pd.DataFrame)
    and not waterfall_summary_raw.empty
)


if not new_engine_ready:
    st.warning(
        "目前尚未完成活動單位分析。"
        "請先完成「03 執行完整分析」，"
        "確認活動單位分析（新方法論）成功執行。"
    )
    st.stop()


unit_overview = prepare_unit_overview_for_display(
    unit_overview_raw
)

unit_overview["策略分類"] = compute_strategy_category(
    unit_overview
)

unit_overview["is_risky"] = compute_risk_mask(
    unit_overview
)

unit_overview["total_actual_revenue"] = (
    compute_actual_revenue_total(unit_overview)
)


# =========================================================
# 建立 AI 分析背景
# =========================================================

advisor_context = build_advisor_context(
    unit_overview_dataframe=(
        unit_overview_raw
    ),
    waterfall_summary_dataframe=(
        waterfall_summary_raw
    ),
    unit_price_dataframe=(
        unit_price_dataframe
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
                "你好，我是 AI 策略顧問。\n\n"
                "我可以根據目前的活動單位分析結果，"
                "協助你判讀高低表現活動、解讀折扣率與贈品搭配、"
                "提醒風險，並規劃下一期促銷測試。"
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

    st.markdown(
        """
        <div class="advisor-panel-heading">
            <div class="advisor-panel-icon">📊</div>
            <div>
                <div class="advisor-panel-title">分析摘要</div>
                <div class="advisor-panel-description">
                    AI 將依據目前活動單位分析、策略分類與資料限制回答。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    unit_count = len(unit_overview)

    continue_count = int(
        (
            unit_overview["策略分類"]
            == "建議延續"
        ).sum()
    )

    risk_count = int(
        unit_overview["is_risky"].sum()
    )

    total_gmv = unit_overview[
        "total_actual_revenue"
    ].sum()


    metric_col1, metric_col2 = st.columns(2)

    metric_col1.metric(
        "活動單位數",
        f"{unit_count:,}",
    )

    metric_col2.metric(
        "建議延續數",
        f"{continue_count:,}",
    )


    metric_col3, metric_col4 = st.columns(2)

    metric_col3.metric(
        "風險檔數",
        f"{risk_count:,}",
    )

    metric_col4.metric(
        "總GMV合計",
        f"{total_gmv:,.0f}",
    )


    st.divider()

    st.subheader("快捷問題")

    shortcut_question = None

    st.markdown(
        """
        <div class="advisor-shortcut-note">
            點選常見問題，快速取得活動延續、折扣與贈品搭配、
            下一期促銷與風險提醒的分析。
        </div>
        """,
        unsafe_allow_html=True,
    )


    if st.button(
        "哪些活動最值得延續？",
        use_container_width=True,
        key="product_ai_best_activity",
    ):
        shortcut_question = (
            "請根據目前分析，找出最值得延續的活動單位。"
            "請說明數據依據、資料限制，"
            "以及下一步可以如何驗證。"
        )


    if st.button(
        "低成效活動可能有哪些原因？",
        use_container_width=True,
        key="product_ai_low_activity",
    ):
        shortcut_question = (
            "請分析目前建議檢討的活動單位可能的原因。"
            "請區分資料能確認的觀察、合理推測，"
            "以及仍需要補充的資料。"
        )


    if st.button(
        "折扣率該打在哪個區間？",
        use_container_width=True,
        key="product_ai_discount_bracket",
    ):
        shortcut_question = (
            "請根據折扣深度洞察，說明折扣率打在哪個區間"
            "平均表現最好，並指出是否有折扣不深但淨增益"
            "仍名列前茅的案例。"
        )


    if st.button(
        "贈品或加碼送該怎麼搭配？",
        use_container_width=True,
        key="product_ai_gift_combo",
    ):
        shortcut_question = (
            "請參考策略分類為建議延續的活動單位，"
            "整理這些案例搭配了哪些贈品或加碼送組合，"
            "並提出下一期活動的贈品設計建議。"
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
            "AI 顧問目前會讀取（活動單位分析）："
        )

        st.markdown(
            """
            - 淨營收效應（量增/降價效應拆解）
            - 折扣率
            - 贈品／加碼送／加碼活動組合
            - 毛利侵蝕風險
            - 策略分類（建議延續／持續觀察／建議檢討）
            - 資料信心
            - 疊加活動組合可否拆分歸因
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

    st.markdown(
        """
        <div class="advisor-chat-heading">
            <div class="advisor-chat-icon">🤖</div>
            <div>
                <div class="advisor-chat-title">與 AI 討論策略</div>
                <div class="advisor-chat-description">
                    可直接詢問活動成效、折扣與贈品搭配、促銷規劃或資料限制。
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
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

            structured = message.get("structured")

            with st.chat_message(role):
                if structured:
                    render_structured_advisor_card(
                        **structured,
                        is_fallback=message.get(
                            "is_fallback", False
                        ),
                    )
                else:
                    st.markdown(
                        message.get("content", "")
                    )


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
            structured_answer, is_fallback = (
                get_structured_advisor_answer(
                    user_question=user_question,
                    advisor_context=advisor_context,
                    chat_messages=(
                        st.session_state[
                            "ai_chat_messages"
                        ]
                    ),
                    unit_overview_dataframe=(
                        unit_overview_raw
                    ),
                )
            )

        st.session_state[
            "ai_chat_messages"
        ].append(
            {
                "role": "assistant",
                "content": condense_structured_response(
                    structured_answer
                ),
                "structured": (
                    structured_answer.model_dump()
                ),
                "is_fallback": is_fallback,
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
    "活動單位分析屬觀察性分析，淨增益不等於實際毛利或淨利潤。"
)
