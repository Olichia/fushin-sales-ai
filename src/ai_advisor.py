from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai


# =========================================================
# 載入本機環境變數
# =========================================================

load_dotenv()


# =========================================================
# Gemini API 設定
# =========================================================

def get_gemini_api_key() -> str:
    """
    取得 Gemini API Key。

    優先順序：
    1. Streamlit Cloud Secrets
    2. 本機 .env 環境變數
    """

    secret_api_key = ""

    try:
        secret_api_key = str(
            st.secrets.get(
                "GEMINI_API_KEY",
                "",
            )
        ).strip()

    except Exception:
        # 本機沒有 secrets.toml 時可能會發生例外，
        # 此時改從 .env 讀取即可。
        secret_api_key = ""

    environment_api_key = str(
        os.getenv(
            "GEMINI_API_KEY",
            "",
        )
    ).strip()

    api_key = (
        secret_api_key
        or environment_api_key
    )

    if not api_key:
        raise ValueError(
            "找不到 GEMINI_API_KEY。"
            "本機請在專案根目錄的 .env 設定；"
            "Streamlit Cloud 請在 App Secrets 設定。"
        )

    return api_key


def get_gemini_client() -> genai.Client:
    """
    建立 Gemini API Client。
    """

    api_key = get_gemini_api_key()

    return genai.Client(
        api_key=api_key
    )


# =========================================================
# DataFrame 文字化
# =========================================================

def dataframe_to_compact_text(
    dataframe: pd.DataFrame | None,
    max_rows: int = 30,
) -> str:
    """
    將 DataFrame 轉成適合放入 Prompt 的精簡文字。
    """

    if dataframe is None:
        return "無資料"

    if dataframe.empty:
        return "無資料"

    display_dataframe = (
        dataframe.head(max_rows).copy()
    )

    for column in display_dataframe.columns:
        if pd.api.types.is_datetime64_any_dtype(
            display_dataframe[column]
        ):
            display_dataframe[column] = (
                display_dataframe[column]
                .dt.strftime("%Y-%m-%d")
            )

    return display_dataframe.to_csv(
        index=False
    )


# =========================================================
# 建立分析背景
# =========================================================

def build_advisor_context(
    strategy_report_text: str | None,
    strategy_dataframe: pd.DataFrame | None,
    performance_dataframe: pd.DataFrame | None,
) -> str:
    """
    建立 AI 顧問可以使用的分析背景。
    """

    report_text = (
        strategy_report_text
        if strategy_report_text
        else "尚無策略文字報告"
    )

    strategy_text = dataframe_to_compact_text(
        strategy_dataframe,
        max_rows=30,
    )

    performance_columns = [
        "product_id",
        "product_name",
        "activity_start_date",
        "activity_end_date",
        "baseline_average_daily_sales",
        "campaign_average_daily_sales",
        "post_average_daily_sales",
        "campaign_total_sales",
        "uplift_rate",
        "post_change_rate",
        "estimated_revenue",
        "overlapping_campaigns",
        "overlapping_benefits",
        "data_confidence",
        "all_periods_complete",
    ]

    if (
        performance_dataframe is not None
        and not performance_dataframe.empty
    ):
        available_columns = [
            column
            for column in performance_columns
            if column in performance_dataframe.columns
        ]

        compact_performance = (
            performance_dataframe[
                available_columns
            ].copy()
        )

    else:
        compact_performance = None

    performance_text = dataframe_to_compact_text(
        compact_performance,
        max_rows=50,
    )

    return f"""
【規則式策略報告】
{report_text}

【策略建議清單】
{strategy_text}

【活動成效分析資料】
{performance_text}
""".strip()


# =========================================================
# 建立完整 Prompt
# =========================================================

def build_conversation_prompt(
    user_question: str,
    advisor_context: str,
    chat_messages: list[dict[str, Any]],
) -> str:
    """
    建立完整對話 Prompt。
    """

    history_lines = []

    for message in chat_messages[-8:]:
        role = message.get(
            "role",
            "user",
        )

        content = str(
            message.get(
                "content",
                "",
            )
        )

        if role == "assistant":
            role_name = "AI 顧問"
        else:
            role_name = "使用者"

        history_lines.append(
            f"{role_name}：{content}"
        )

    history_text = "\n".join(
        history_lines
    )

    return f"""
你是零售促銷與品牌行銷策略顧問。

請只根據提供的分析資料回答，不可捏造不存在的商品、
活動、數值、成本、毛利或因果關係。

回答時必須遵守以下規則：

1. 明確區分「資料觀察」、「推測」與「建議」。
2. 不可將活動期間銷量上升直接說成活動造成。
3. 若觀察期間不完整、基準為零或存在重疊活動，
   必須主動提醒。
4. 推估營收不等於實際營收。
5. 沒有成本或毛利資料時，不可宣稱活動有獲利。
6. 優先提供具體、可執行、可驗證的下一步。
7. 使用繁體中文。
8. 回答以清楚的小標題與簡短段落呈現。
9. 不需要重複所有原始資料，只整理最重要的依據。
10. 若資料不足，直接說明還需要哪些資料。

以下是目前系統分析背景：

{advisor_context}

以下是最近對話：

{history_text}

使用者最新問題：

{user_question}
""".strip()


# =========================================================
# 呼叫 Gemini
# =========================================================

def ask_gemini_advisor(
    user_question: str,
    advisor_context: str,
    chat_messages: list[dict[str, Any]],
) -> str:
    """
    呼叫 Gemini 產生策略顧問回答。
    """

    client = get_gemini_client()

    prompt = build_conversation_prompt(
        user_question=user_question,
        advisor_context=advisor_context,
        chat_messages=chat_messages,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    response_text = getattr(
        response,
        "text",
        None,
    )

    if not response_text:
        raise ValueError(
            "Gemini 沒有回傳可顯示的文字內容。"
        )

    return response_text.strip()