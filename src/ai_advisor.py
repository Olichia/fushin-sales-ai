from __future__ import annotations

import os
from typing import Any, Literal

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.column_labels import label_for
from src.executive_summary import build_activity_unit_strategy_text
from src.unit_overview_helpers import (
    compute_confidence_label,
    compute_risk_mask,
    compute_strategy_category,
    prepare_unit_overview_for_display,
)


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


def _rename_to_chinese_labels(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """把欄名轉成中文標籤，讓 LLM 直接看懂欄位意義。"""

    renamed = dataframe.copy()

    renamed.columns = [
        label_for(column) for column in renamed.columns
    ]

    return renamed


# =========================================================
# 建立分析背景（活動單位分析方法論）
# =========================================================

def build_advisor_context(
    unit_overview_dataframe: pd.DataFrame,
    waterfall_summary_dataframe: pd.DataFrame,
    unit_price_dataframe: pd.DataFrame | None = None,
) -> str:
    """
    建立 AI 顧問可以使用的分析背景。

    這是目前系統唯一使用的分析背景來源（活動單位分析方法論：
    同月安靜期基準、量增/降價效應拆解、瀑布法配對），
    不混用舊版活動前後比較數字。
    """

    strategy_text = build_activity_unit_strategy_text(
        unit_overview_dataframe, waterfall_summary_dataframe
    )

    unit_overview = prepare_unit_overview_for_display(
        unit_overview_dataframe
    )
    unit_overview["策略分類"] = compute_strategy_category(
        unit_overview
    )
    unit_overview["資料信心"] = compute_confidence_label(
        unit_overview
    )

    overview_columns = [
        column
        for column in [
            "product_id",
            "product_name",
            "unit_code",
            "month",
            "days",
            "corresponding_activities_label",
            "unit_avg_price",
            "baseline_price",
            "discount_rate",
            "volume_effect_per_day",
            "price_effect_per_day",
            "net_revenue_effect_per_day",
            "net_revenue_effect_total",
            "策略分類",
            "資料信心",
        ]
        if column in unit_overview.columns
    ]

    overview_text = dataframe_to_compact_text(
        _rename_to_chinese_labels(
            unit_overview[overview_columns]
        ),
        max_rows=80,
    )

    combo_text = dataframe_to_compact_text(
        _rename_to_chinese_labels(waterfall_summary_dataframe),
        max_rows=40,
    )

    if (
        unit_price_dataframe is not None
        and not unit_price_dataframe.empty
    ):
        price_columns = [
            column
            for column in [
                "product_id",
                "product_name",
                "unit_code",
                "price",
                "gift",
                "bonus_gift_text",
                "bonus_campaign_text",
            ]
            if column in unit_price_dataframe.columns
        ]

        price_text = dataframe_to_compact_text(
            _rename_to_chinese_labels(
                unit_price_dataframe[price_columns]
            ),
            max_rows=80,
        )

    else:
        price_text = "無資料"

    return f"""
【活動單位分析摘要】
{strategy_text}

【活動單位總覽明細】
{overview_text}

【商品售價與贈品明細】
{price_text}

【疊加活動組合彙總】
{combo_text}
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
你是零售促銷與品牌行銷策略顧問，熟悉「活動單位分析」方法論。

請只根據提供的分析資料回答，不可捏造不存在的商品、
活動、數值、成本、毛利或因果關係。

【活動單位分析方法論】
- 活動單位：依對應活動組合切出的連續期間，是這套方法論的分析顆粒度。
- 同月安靜期基準：同商品同月沒有參與任何活動的期間，作為比較基準。
- 淨營收效應 = 量增效應 + 降價效應：拆解「賣更多」與「賣更便宜」對營收的
  個別貢獻。
- 折扣率：以基準售價（含代理牌價估算）相對活動售價計算。
- 瀑布法配對（可拆分／不可拆分）：可否把疊加的多個活動效果拆開歸因給單一
  活動；不可拆分代表無法判斷組合裡哪個活動機制真正有效，這是這套方法論
  處理「活動疊加」問題的方式。
- 策略分類：淨增益為負一律是「建議檢討」；非負值時達全體活動單位淨增益
  中位數以上為「建議延續」，未達中位數為「持續觀察」。
- 毛利侵蝕風險：降價效應絕對值大於量增效應時判定，代表銷量沒有跟上降價
  幅度。
- 資料信心：依樣本天數、瀑布法配對樣本量與是否用了代理牌價估算判斷。

回答時必須遵守以下規則：

1. 明確區分「資料觀察」、「推測」與「建議」。
2. 不可將活動期間銷量上升直接說成活動造成。
3. 若活動單位資料信心較低（樣本天數少、瀑布法對照組樣本量小，或使用了
   代理牌價估算），或活動組合為「不可拆分」，必須主動提醒。
4. 淨增益已扣除同月安靜期基準，但不等於實際毛利或淨利潤（未納入成本、
   退貨、平台抽成）。
5. 沒有成本或毛利資料時，不可宣稱活動有獲利。
6. 優先提供具體、可執行、可驗證的下一步。
7. 使用繁體中文。
8. 回答以清楚的小標題與簡短段落呈現。
9. 不需要重複所有原始資料，只整理最重要的依據。
10. 若資料不足，直接說明還需要哪些資料。
11. 使用者問到以下類型問題時，優先從背景資料對應段落找依據回答，並在
    找不到足夠依據時明確說明：
    - 折扣策略／折扣率該打多少 → 引用「活動單位分析摘要」裡的折扣深度
      洞察
    - 贈品或加碼送組合設計 → 引用「商品售價與贈品明細」，並參考策略分類
      為「建議延續」的相似案例搭配了哪些贈品
    - 活動方向／要不要疊加多個活動 → 引用「疊加活動組合彙總」的可拆分／
      不可拆分狀態與策略分類
    - 風險提醒 → 引用資料信心較低或有毛利侵蝕風險的活動單位
    - 類似成功案例 → 從「活動單位總覽明細」找商品、折扣率或活動組合
      相近、且策略分類為「建議延續」的過往案例

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
# 結構化回覆（AI 策略中心專用）
#
# 上面的 ask_gemini_advisor() 回傳自由文字，floating_chatbot.py
# 與舊版 10_AI行銷策略顧問.py 仍在使用，不能更動其行為。這裡
# 另外新增一組固定 JSON schema 版本，供「AI 策略中心」使用：
# 關鍵發現／判斷原因／資料證據／建議行動／替代方案／信心程度／
# 資料限制，解析失敗兩次後改用規則式 fallback，不讓對話中斷。
# =========================================================

class AdvisorStructuredResponse(BaseModel):
    """AI 策略顧問固定回覆結構。"""

    finding: str = Field(
        description=(
            "關鍵發現：本次問題最重要的一個觀察，"
            "需引用具體商品、活動或數字。"
        )
    )
    reason: str = Field(
        description="判斷原因：為什麼會有這個發現，說明機制或推論依據。"
    )
    evidence: str = Field(
        description=(
            "資料證據：引用背景資料中具體的商品、活動組合、"
            "淨增益、折扣率等數值。"
        )
    )
    action: str = Field(
        description="建議行動：具體、可在下一檔活動執行的行動。"
    )
    alternative: str = Field(
        description="替代方案：如果不採用建議行動時，另一個可考慮的選項。"
    )
    confidence: Literal["高", "中", "低"] = Field(
        description="信心程度，只能是「高」「中」或「低」三選一。"
    )
    limitations: str = Field(
        description="資料限制：樣本量不足、無法歸因或需要補充的資料。"
    )


def build_structured_conversation_prompt(
    user_question: str,
    advisor_context: str,
    chat_messages: list[dict[str, Any]],
) -> str:
    """
    建立要求固定 JSON 結構輸出的完整 Prompt。

    業務規則跟 build_conversation_prompt() 完全一致（不可捏造、
    需區分觀察/推測/建議、資料信心提醒等），差別只在於這裡改
    要求輸出對應到 AdvisorStructuredResponse 的七個欄位，
    而不是自由格式的散文。
    """

    history_lines = []

    for message in chat_messages[-8:]:
        role = message.get("role", "user")
        content = str(message.get("content", ""))
        role_name = "AI 顧問" if role == "assistant" else "使用者"
        history_lines.append(f"{role_name}：{content}")

    history_text = "\n".join(history_lines)

    return f"""
你是零售促銷與品牌行銷策略顧問，熟悉「活動單位分析」方法論。

請只根據提供的分析資料回答，不可捏造不存在的商品、
活動、數值、成本、毛利或因果關係。

【活動單位分析方法論】
- 活動單位：依對應活動組合切出的連續期間，是這套方法論的分析顆粒度。
- 同月安靜期基準：同商品同月沒有參與任何活動的期間，作為比較基準。
- 淨營收效應 = 量增效應 + 降價效應：拆解「賣更多」與「賣更便宜」對營收的
  個別貢獻。
- 折扣率：以基準售價（含代理牌價估算）相對活動售價計算。
- 瀑布法配對（可拆分／不可拆分）：可否把疊加的多個活動效果拆開歸因給單一
  活動；不可拆分代表無法判斷組合裡哪個活動機制真正有效。
- 策略分類：淨增益為負一律是「建議檢討」；非負值時達全體活動單位淨增益
  中位數以上為「建議延續」，未達中位數為「持續觀察」。
- 毛利侵蝕風險：降價效應絕對值大於量增效應時判定。
- 資料信心：依樣本天數、瀑布法配對樣本量與是否用了代理牌價估算判斷。

回答時必須遵守以下規則：

1. 明確區分「資料觀察」、「推測」與「建議」，分別寫進對應欄位。
2. 不可將活動期間銷量上升直接說成活動造成。
3. 若活動單位資料信心較低（樣本天數少、瀑布法對照組樣本量小，或使用了
   代理牌價估算），或活動組合為「不可拆分」，信心程度須填「低」或「中」，
   並在資料限制欄位說明原因。
4. 淨增益已扣除同月安靜期基準，但不等於實際毛利或淨利潤（未納入成本、
   退貨、平台抽成）。
5. 沒有成本或毛利資料時，不可宣稱活動有獲利。
6. 建議行動與替代方案都必須具體、可執行、可驗證，不可空泛。
7. 資料證據欄位要點名實際商品、活動或數字，不要只重複發現欄位的說法。
8. 若資料不足以回答，在資料限制欄位直接說明還需要哪些資料，並將信心程度
   填「低」。
9. 使用者問到以下類型問題時，優先從背景資料對應段落找依據：
   - 折扣策略／折扣率該打多少 → 引用「活動單位分析摘要」裡的折扣深度洞察
   - 贈品或加碼送組合設計 → 引用「商品售價與贈品明細」
   - 活動方向／要不要疊加多個活動 → 引用「疊加活動組合彙總」
   - 風險提醒 → 引用資料信心較低或有毛利侵蝕風險的活動單位
   - 類似成功案例 → 從「活動單位總覽明細」找相近且策略分類為「建議延續」
     的過往案例
10. 全部使用繁體中文。

以下是目前系統分析背景：

{advisor_context}

以下是最近對話：

{history_text}

使用者最新問題：

{user_question}
""".strip()


def ask_gemini_advisor_structured(
    user_question: str,
    advisor_context: str,
    chat_messages: list[dict[str, Any]],
) -> AdvisorStructuredResponse:
    """
    呼叫 Gemini 並要求回傳符合 AdvisorStructuredResponse 的固定
    JSON 結構（單次嘗試，不含重試）。重試與 fallback 邏輯統一交給
    get_structured_advisor_answer() 處理，這裡只負責單次呼叫。
    """

    client = get_gemini_client()

    prompt = build_structured_conversation_prompt(
        user_question=user_question,
        advisor_context=advisor_context,
        chat_messages=chat_messages,
    )

    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AdvisorStructuredResponse,
            temperature=0.2,
        ),
    )

    parsed = response.parsed

    if not isinstance(parsed, AdvisorStructuredResponse):
        raise ValueError("Gemini 沒有回傳可解析的結構化內容。")

    return parsed


def build_fallback_advisor_response(
    unit_overview_dataframe: pd.DataFrame,
) -> AdvisorStructuredResponse:
    """
    Gemini 連續兩次呼叫都失敗時的規則式備援內容。

    完全複用既有的策略分類／風險判斷邏輯彙總出一句可用的摘要，
    讓對話不中斷；卡片渲染時會額外標示「示範備援」，
    不會偽裝成正常的 AI 即時判讀結果。
    """

    unit_overview = prepare_unit_overview_for_display(
        unit_overview_dataframe
    )

    strategy_category = compute_strategy_category(unit_overview)
    risk_mask = compute_risk_mask(unit_overview)

    total_units = len(unit_overview)
    continue_count = int((strategy_category == "建議延續").sum())
    risk_count = int(risk_mask.sum())

    return AdvisorStructuredResponse(
        finding=(
            f"目前共 {total_units} 個活動單位，其中 {continue_count} 個"
            f"建議延續、{risk_count} 個存在毛利侵蝕風險。"
        ),
        reason=(
            "AI 顧問服務暫時無法回應，以下為系統依既有規則彙總的摘要，"
            "非本次問題的即時判讀。"
        ),
        evidence="彙總自目前活動單位分析的策略分類與風險判斷欄位。",
        action=(
            "請稍後再重新提問，或前往「AI 策略中心」查看完整決策佇列"
            "與個別化建議。"
        ),
        alternative="可先參考「主管報表中心」的文字策略報告。",
        confidence="低",
        limitations=(
            "此為示範備援內容，非 AI 即時判讀結果，"
            "資料細節請以其他頁面的分析結果為準。"
        ),
    )


def get_structured_advisor_answer(
    user_question: str,
    advisor_context: str,
    chat_messages: list[dict[str, Any]],
    unit_overview_dataframe: pd.DataFrame,
) -> tuple[AdvisorStructuredResponse, bool]:
    """
    呼叫結構化 AI 顧問，最多嘗試兩次；兩次都失敗（API 錯誤、逾時，
    或回傳內容無法對應到 AdvisorStructuredResponse）時改用規則式
    fallback，確保對話不中斷。

    回傳 (回覆內容, 是否為 fallback)。
    """

    for _ in range(2):
        try:
            return (
                ask_gemini_advisor_structured(
                    user_question=user_question,
                    advisor_context=advisor_context,
                    chat_messages=chat_messages,
                ),
                False,
            )
        except Exception:
            continue

    return (
        build_fallback_advisor_response(unit_overview_dataframe),
        True,
    )


def condense_structured_response(
    response: AdvisorStructuredResponse,
) -> str:
    """把結構化回覆壓成一行摘要，供對話歷史（Prompt 用）使用。"""

    return f"{response.finding}｜建議：{response.action}"


# =========================================================
# 系統說明模式（尚無成效分析資料時使用）
# =========================================================

SYSTEM_PROFILE_TEXT = """
【系統名稱】
富信新零售銷量與活動分析系統

【系統定位】
以 Streamlit 建立的零售活動分析 MVP，整合銷量資料與促銷活動資料，
完成欄位對應、資料品質檢查、活動單位分析、策略分類、
AI 顧問解讀與主管 PDF 報表匯出。
提供的是觀察性分析與決策輔助，不直接證明活動造成銷量變化，
也不在缺少成本與毛利資料時判定活動是否獲利。

【資料清洗與處理流程】
銷量資料上傳 → 欄位設定（對應至標準欄位）→ 銷量資料品質檢查
→ 活動資料上傳 → 活動資料品質檢查 → 建立整合資料
（依商品編號與日期整合每日銷量與活動資料）
→ 執行活動單位分析 → 查看活動洞察／AI 策略中心／主管報表。

標準欄位包含：
sale_date（銷售日期）、product_id（商品編號）、
product_name（商品名稱）、quantity（銷量）、
activity_start_date（活動開始日期）、activity_end_date（活動結束日期）。

清洗過程會處理：欄位名稱不一致、日期格式混雜、
同日同商品多筆紀錄彙總、缺值與格式錯誤標記、疑似異常資料標記。

【核心運算邏輯（活動單位分析）】
活動單位：依對應活動組合切出的連續期間，是分析的顆粒度。

同月安靜期基準：同商品同月沒有參與任何活動的期間，
作為每個活動單位的比較基準。

淨營收效應 = 量增效應 + 降價效應：
量增效應反映銷量相對基準的變化，降價效應反映售價相對基準
（含代理牌價估算）的變化，兩者相加才是淨營收效應。

折扣率 = 1 －（活動售價 ÷ 基準售價）。

瀑布法配對（可拆分／不可拆分）：同商品同月找到「扣掉某個活動後
組合相同」的對照單位時可以拆分歸因；找不到對照組時歸類為
不可拆分，代表無法判斷組合裡哪個活動機制真正有效。

系統會依規則將活動單位分類為「建議延續、持續觀察、建議檢討」：
淨增益為負一律是建議檢討；非負值時達全體活動單位淨增益中位數
以上為建議延續，未達中位數為持續觀察。

毛利侵蝕風險：降價效應絕對值大於量增效應時判定。

資料信心：依樣本天數、瀑布法配對樣本量與是否用了代理牌價估算判斷。

【分析成效指標】
net_revenue_effect_per_day／net_revenue_effect_total（淨營收效應/日、
合計）、volume_effect_per_day（量增效應/日）、price_effect_per_day
（降價效應/日）、discount_rate（折扣率）、classification（可否拆分）、
策略分類（建議延續／持續觀察／建議檢討）、資料信心（較高／較低）。

【AI 顧問定位】
核心數值一律由 Python 與既定規則計算，
Gemini 僅負責解讀既有分析結果並提出下一步驗證建議，
需區分資料觀察、推測與建議，不可將相關性表述為因果，
需主動提醒資料信心較低或毛利侵蝕風險的活動單位，
缺少成本或毛利資料時不可宣稱活動有獲利。

【目前限制】
資料保存在 st.session_state，重新整理、休眠或重新啟動後可能需要重新上傳；
尚未建立資料庫、登入、權限與永久儲存機制；
活動單位分析屬觀察性分析，不是隨機實驗或因果推論；
疊加多種活動機制的活動單位（不可拆分）無法把效果拆開歸因給單一活動；
缺少成本、毛利、庫存、退貨、廣告支出及客群資料時，
無法完整評估獲利。
""".strip()


def build_system_explainer_prompt(
    user_question: str,
    chat_messages: list[dict[str, Any]],
) -> str:
    """
    建立「系統說明模式」的完整 Prompt。

    使用者尚未完成資料整合或活動單位分析時，
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

目前使用者尚未完成資料整合或活動單位分析，
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
   執行活動單位分析。
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
