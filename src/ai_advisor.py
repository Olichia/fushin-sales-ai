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
        model="gemini-flash-lite-latest",
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


# =========================================================
# 系統說明模式（尚無成效分析資料時使用）
# =========================================================

SYSTEM_PROFILE_TEXT = """
【系統名稱】
富信新零售銷量與活動分析系統

【系統定位】
以 Streamlit 建立的零售活動分析 MVP，整合銷量資料與促銷活動資料，
完成欄位對應、資料品質檢查、活動前中後比較、策略分類、
AI 顧問解讀與主管 PDF 報表匯出。
提供的是觀察性分析與決策輔助，不直接證明活動造成銷量變化，
也不在缺少成本與毛利資料時判定活動是否獲利。

【資料清洗與處理流程】
銷量資料上傳 → 欄位設定（對應至標準欄位）→ 銷量資料品質檢查
→ 活動資料上傳 → 活動資料品質檢查 → 建立整合資料
（依商品編號與日期整合每日銷量與活動資料）
→ 執行成效分析 → 產生策略報告 → 查看活動洞察／AI 顧問／主管報表。

標準欄位包含：
sale_date（銷售日期）、product_id（商品編號）、
product_name（商品名稱）、quantity（銷量）、
activity_start_date（活動開始日期）、activity_end_date（活動結束日期）。

清洗過程會處理：欄位名稱不一致、日期格式混雜、
同日同商品多筆紀錄彙總、缺值與格式錯誤標記、疑似異常資料標記。

【核心運算邏輯】
每日商品銷量 = 同日期、同商品所有交易數量加總。

活動提升率 =（活動期間日均銷量－活動前日均銷量）÷ 活動前日均銷量。
當活動前日均銷量為 0 時，不進行一般百分比計算，
視為低基期或無基期情況。

推估營收 = 活動期間銷量 × 可用的活動價格。
推估營收不等於實際營收或獲利，尚未納入折扣碼、退貨、
平台幣、贈品、運費、廣告成本、平台抽成、商品成本與毛利。

系統會依規則將活動分類為「建議延續、建議優化、建議檢討」，
並標記觀察期間不完整、低基期及活動重疊等情況。

【分析成效指標】
uplift_rate（活動提升率）、post_change_rate（活動後變化率）、
campaign_total_sales（活動總銷量）、estimated_revenue（推估營收）、
data_confidence（資料信心）、all_periods_complete（觀察期間完整度）、
overlapping_campaigns / overlapping_benefits（活動與優惠重疊情況）。

【AI 顧問定位】
核心數值一律由 Python 與既定規則計算，
Gemini 僅負責解讀既有分析結果並提出下一步驗證建議，
需區分資料觀察、推測與建議，不可將相關性表述為因果，
需主動提醒期間不完整、低基期與活動重疊，
缺少成本或毛利資料時不可宣稱活動有獲利。

【目前限制】
資料保存在 st.session_state，重新整理、休眠或重新啟動後可能需要重新上傳；
尚未建立資料庫、登入、權限與永久儲存機制；
活動前後比較屬觀察性分析，不是隨機實驗或因果推論；
活動重疊時無法將效果完整歸因於單一活動；
缺少成本、毛利、庫存、退貨、廣告支出及客群資料時，
無法完整評估獲利。
""".strip()


def build_system_explainer_prompt(
    user_question: str,
    chat_messages: list[dict[str, Any]],
) -> str:
    """
    建立「系統說明模式」的完整 Prompt。

    使用者尚未完成資料整合或成效分析時，
    沒有任何實際商品、活動或數值可以引用，
    因此只能根據系統設計本身回答。
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
你是「富信新零售銷量與活動分析系統」的系統說明助手。

目前使用者尚未完成資料整合或活動成效分析，
因此沒有任何實際商品、活動、銷量或營收數字可以引用。

回答時必須遵守以下規則：

1. 只能根據下方【系統說明】回答系統定位、資料清洗流程、
   運算邏輯與分析指標的意義，不可捏造任何實際商品、
   活動名稱、銷量、營收或成效數字。
2. 若使用者詢問的是需要實際資料才能回答的問題
   （例如「哪個商品賣得最好」「這次活動成效如何」），
   必須說明目前沒有可用的分析資料，
   並引導使用者依序完成：
   銷量資料上傳 → 欄位設定 → 銷量資料品質 →
   活動資料上傳 → 活動資料品質 → 建立整合資料 →
   執行成效分析 → 產生策略報告。
3. 使用繁體中文，回答簡潔清楚，可使用小標題或條列。
4. 不需要逐字複誦系統說明全文，只整理與問題相關的重點。

【系統說明】
{SYSTEM_PROFILE_TEXT}

以下是最近對話：

{history_text}

使用者最新問題：

{user_question}
""".strip()


def ask_gemini_system_explainer(
    user_question: str,
    chat_messages: list[dict[str, Any]],
) -> str:
    """
    呼叫 Gemini，於尚無成效分析資料時回答系統相關說明。
    """

    client = get_gemini_client()

    prompt = build_system_explainer_prompt(
        user_question=user_question,
        chat_messages=chat_messages,
    )

    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
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