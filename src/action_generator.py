from __future__ import annotations

import pandas as pd
from google.genai import types

from src.ai_advisor import get_gemini_client
from src.unit_recommendation_notes import (
    build_unit_personalized_recommendation_sections,
    format_signed_currency,
)
from src.whatif_simulation import WhatIfScenarioResult


# =========================================================
# 行動生成頁設定
#
# 對應「強化執行規格書」指令 E：下一步行動生成器。
# 產出內容一律只能引用本檔案組出的「證據」文字，
# 不得由 AI 自行捏造商品、活動或數字。
# =========================================================

CHANNEL_OPTIONS = [
    "電話話術",
    "LINE/簡訊",
    "Email",
    "拜訪提綱",
]

TONE_OPTIONS = [
    "專業",
    "關係維護",
    "促成交易",
]

LENGTH_OPTIONS = [
    "簡短",
    "標準",
    "詳細",
]

GEMINI_MODEL_NAME = "gemini-flash-lite-latest"


# =========================================================
# 平台檔期 vs 商品優惠 分類
#
# corresponding_activities_label 到了活動單位分析後段，
# 只留下活動名稱字串，不再帶 campaign_level。這裡改用
# session state 裡保存的原始活動日曆（含 campaign_level）
# 反查每個活動名稱屬於「平台檔期」還是「商品/品牌活動」，
# 讓行動生成內容能誠實區分兩種完全不同方向的優惠，
# 而不是含混地當成同一件事。
# =========================================================

PLATFORM_CAMPAIGN_LEVEL = "平台檔期"


def build_platform_campaign_name_set(
    activity_calendar_dataframe: pd.DataFrame | None,
) -> set[str]:
    """
    從活動日曆抓出所有 campaign_level 為「平台檔期」的活動名稱。

    找不到日曆資料時回傳空集合，呼叫端要能處理
    「無法判斷、如實告知使用者」的情況，不可自行假設。
    """

    if (
        not isinstance(activity_calendar_dataframe, pd.DataFrame)
        or activity_calendar_dataframe.empty
        or "campaign_level" not in activity_calendar_dataframe.columns
        or "campaign_name" not in activity_calendar_dataframe.columns
    ):
        return set()

    platform_rows = activity_calendar_dataframe[
        activity_calendar_dataframe["campaign_level"]
        == PLATFORM_CAMPAIGN_LEVEL
    ]

    return set(
        platform_rows["campaign_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )


def classify_activity_type(
    activity_type: str,
    platform_campaign_names: set[str],
) -> str:
    """
    判斷單一活動名稱屬於「平台檔期」或「商品/品牌活動」。

    活動單位分析的子階段合併會把名稱組成複合字串
    （例如「女王節正式」＝「女王節」＋「正式」），
    因此用「是否包含已知平台檔期名稱」做判斷，
    而不是要求完全相等。
    """

    if not platform_campaign_names:
        return "無法判斷（缺活動日曆資料）"

    for platform_name in platform_campaign_names:
        if platform_name and platform_name in activity_type:
            return "平台檔期"

    return "商品/品牌活動"


def build_unit_activity_composition_note(
    unit_row: pd.Series,
    activity_calendar_dataframe: pd.DataFrame | None,
) -> str:
    """
    整理一個活動單位裡，各個對應活動分別是平台檔期還是商品優惠。

    平台檔期（例如女王節）是通路滿額門檻優惠，
    商品優惠（例如買二送一）是廠商自行提供的贈品／折扣，
    兩者機制、預算來源都不同，行動生成內容必須分開講清楚，
    不能混為一談，也不能假裝其中一種不存在。
    """

    label = str(
        unit_row.get("corresponding_activities_label") or ""
    ).strip()

    activity_types = [
        part for part in label.split("、") if part
    ]

    if not activity_types:
        return "本活動單位對應活動為安靜期（無促銷活動）。"

    platform_campaign_names = build_platform_campaign_name_set(
        activity_calendar_dataframe
    )

    lines = []

    for activity_type in activity_types:
        category = classify_activity_type(
            activity_type, platform_campaign_names
        )
        lines.append(f"「{activity_type}」（{category}）")

    composition_text = "、".join(lines)

    if not platform_campaign_names:
        return (
            f"本活動單位對應活動：{composition_text}。"
            "目前找不到活動日曆資料，"
            "無法判斷各活動屬於平台檔期或商品優惠，"
            "請勿在生成內容中臆測。"
        )

    has_platform = any(
        classify_activity_type(
            activity_type, platform_campaign_names
        )
        == "平台檔期"
        for activity_type in activity_types
    )

    has_product = any(
        classify_activity_type(
            activity_type, platform_campaign_names
        )
        == "商品/品牌活動"
        for activity_type in activity_types
    )

    if has_platform and has_product:
        note = (
            "本檔同時搭配平台檔期與商品/品牌活動，"
            "兩者是不同方向的優惠（平台滿額門檻 vs 廠商贈品/折扣），"
            "下方淨營收效應為兩者疊加後的整體效果，"
            "若瀑布法配對已能拆分，下方會分別列出兩者的獨立貢獻。"
        )
    else:
        note = ""

    return f"本活動單位對應活動：{composition_text}。{note}".strip()


# =========================================================
# 證據組裝：來源① 活動單位分析（已完成活動）
# =========================================================

def build_unit_action_evidence(
    unit_row: pd.Series,
    pairing_rows: pd.DataFrame,
    unit_overview: pd.DataFrame,
    mechanism_text: str,
    strategy_category: str,
    activity_calendar_dataframe: pd.DataFrame | None,
) -> dict[str, object]:
    """
    組成「行動生成」使用的完整證據內容（來源：已完成的活動單位）。

    沿用策略中心既有的四段式個別化建議
    （績效診斷／檔期歸因／建議決策／下一檔執行），
    再加上「活動組成」一段，明確拆出平台檔期與商品優惠，
    確保生成內容不會漏掉其中一種優惠類型。
    """

    composition_note = build_unit_activity_composition_note(
        unit_row, activity_calendar_dataframe
    )

    personalized_sections = (
        build_unit_personalized_recommendation_sections(
            unit_row=unit_row,
            pairing_rows=pairing_rows,
            unit_overview=unit_overview,
            mechanism_text=mechanism_text,
            strategy_category=strategy_category,
        )
    )

    sections: list[tuple[str, str]] = [
        ("【活動組成】", composition_note),
        *personalized_sections,
    ]

    product_name = unit_row.get("product_name") or "此商品"
    unit_code = unit_row.get("unit_code", "")

    source_label = (
        f"{product_name}｜{unit_code}"
        f"（{unit_row.get('corresponding_activities_label') or '安靜期'}）"
    )

    evidence_text = "\n\n".join(
        f"{label}{text}" for label, text in sections
    )

    return {
        "source_type": "活動單位分析",
        "source_label": source_label,
        "sections": sections,
        "evidence_text": evidence_text,
    }


# =========================================================
# 證據組裝：來源② 情境模擬（尚未發生的方案）
# =========================================================

def build_whatif_action_evidence(
    scenario_result: WhatIfScenarioResult,
    product_name: str,
) -> dict[str, object]:
    """
    組成「行動生成」使用的完整證據內容（來源：情境模擬試算）。

    情境模擬本身刻意不計入平台活動效益（缺客單價無法試算），
    這裡把限制原封不動保留進證據內容，確保改寫成 Email／話術後
    警語不會被 AI 悄悄省略掉。
    """

    discount_text = (
        f"{scenario_result.discount_rate:.1%}"
        if scenario_result.discount_rate is not None
        else "無法計算（缺基準價）"
    )

    scenario_summary = (
        f"方案「{scenario_result.label}」：折扣率約 {discount_text}，"
        f"預估活動營收 {scenario_result.estimated_activity_revenue:,.0f} 元，"
        "無活動預期營收 "
        f"{scenario_result.expected_revenue_without_activity:,.0f} 元，"
        f"淨營收增益 "
        f"{format_signed_currency(scenario_result.net_revenue_gain)}"
        + (
            f"，贈品成本 {scenario_result.total_gift_cost:,.0f} 元"
            if scenario_result.has_gift
            else "，本方案不含贈品"
        )
        + "，簡化後淨效益 "
        + format_signed_currency(
            scenario_result.simplified_net_benefit
        )
        + "。"
    )

    limitation_parts = [
        "此為情境試算結果，是根據使用者輸入條件推算的假設情境，"
        "不是已經發生的真實活動成效，不可當作既定事實陳述。",
        "簡化後淨效益未納入實際成本、退貨與平台抽成，"
        "不能直接視為毛利或淨利潤。",
    ]

    if scenario_result.platform_overlap:
        limitation_parts.append(
            "本方案有勾選「同時搭配平台活動」，"
            "但平台活動（例如滿額門檻優惠）的疊加貢獻"
            "需要客單價與瀑布法配對比較才能拆分，"
            "本次試算並未計入這部分效果，"
            "生成內容必須保留這項限制，不可省略。"
        )

    sections: list[tuple[str, str]] = [
        ("【情境設定】", f"商品「{product_name}」。"),
        ("【試算結果】", scenario_summary),
        ("【資料限制】", "".join(limitation_parts)),
    ]

    source_label = f"{product_name}｜{scenario_result.label}（情境模擬）"

    evidence_text = "\n\n".join(
        f"{label}{text}" for label, text in sections
    )

    return {
        "source_type": "情境模擬",
        "source_label": source_label,
        "sections": sections,
        "evidence_text": evidence_text,
    }


# =========================================================
# Prompt 組裝
# =========================================================

_CHANNEL_FORMAT_GUIDE = {
    "電話話術": (
        "產出業務人員可以直接照著念的電話溝通重點，"
        "採條列式的口語化短句（3-5點），"
        "適合業務跟主管或團隊口頭報告這檔活動的狀況與下一步。"
    ),
    "LINE/簡訊": (
        "產出一則精簡的 LINE 或簡訊通知文字（80字以內），"
        "只保留最關鍵的一到兩個重點與一個行動呼籲，不分段。"
    ),
    "Email": (
        "產出一封正式 Email，"
        "包含「主旨：」一行，接著稱謂、內文（可分段）、結尾與署名處，"
        "適合回報主管或跟通路窗口正式溝通。"
    ),
    "拜訪提綱": (
        "產出業務拜訪前的準備重點清單（條列式，5點以內），"
        "每點是一個要跟對方確認或討論的具體事項。"
    ),
}

_TONE_GUIDE = {
    "專業": "語氣客觀精簡，聚焦數據與結論，避免情緒性字眼。",
    "關係維護": "語氣溫和、重視合作關係，可適度表達感謝與長期合作意願。",
    "促成交易": "語氣積極、聚焦時效與下一步行動，適度營造急迫感但不誇大。",
}

_LENGTH_GUIDE = {
    "簡短": "整體控制在 60-100 字以內。",
    "標準": "整體控制在 120-200 字。",
    "詳細": "整體可到 250-350 字，但仍須精簡，不可贅述。",
}


def build_action_generation_prompt(
    evidence_text: str,
    channel: str,
    tone: str,
    length: str,
) -> str:
    """建立行動生成的完整 Prompt。"""

    channel_guide = _CHANNEL_FORMAT_GUIDE.get(
        channel, _CHANNEL_FORMAT_GUIDE["Email"]
    )
    tone_guide = _TONE_GUIDE.get(tone, _TONE_GUIDE["專業"])
    length_guide = _LENGTH_GUIDE.get(length, _LENGTH_GUIDE["標準"])

    return f"""
你是零售業務團隊的溝通內容撰寫助手。

請只根據下方【證據內容】撰寫，不可新增證據內容中沒有出現的
商品、活動名稱、數字、承諾或因果關係。證據內容中出現的任何
限制、警語或「無法拆分／無法判斷」的說明，都必須原封不動地
保留在輸出內容中，不可省略或淡化。

【格式要求】
{channel_guide}

【語氣要求】
{tone_guide}

【長度要求】
{length_guide}

其他規則：
1. 若證據內容同時包含「平台檔期」與「商品/品牌活動」兩種優惠，
   必須在內容中清楚分開描述，不可合併成單一籠統的「活動」，
   也不可只挑其中一種描述。
2. 若證據內容標示為「情境模擬」，內容中必須讓讀者清楚知道
   這是試算情境、尚未實際執行，不可寫成既成事實。
3. 淨營收效應／淨效益不等於實際毛利或淨利潤，若證據內容有此
   提醒，需保留。
4. 使用繁體中文。
5. 只輸出最終要傳送的內容本身，不要加上「以下是」之類的說明文字，
   也不要用 Markdown 標題語法。

【證據內容】
{evidence_text}
""".strip()


# =========================================================
# 呼叫 Gemini
# =========================================================

def ask_gemini_action_content(
    evidence_text: str,
    channel: str,
    tone: str,
    length: str,
) -> str:
    """呼叫 Gemini 產生一次行動內容（單次嘗試，不含重試）。"""

    client = get_gemini_client()

    prompt = build_action_generation_prompt(
        evidence_text=evidence_text,
        channel=channel,
        tone=tone,
        length=length,
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
        ),
    )

    response_text = getattr(response, "text", None)

    if not response_text or not response_text.strip():
        raise ValueError("Gemini 沒有回傳可顯示的文字內容。")

    return response_text.strip()


# =========================================================
# 規則式 fallback
#
# 直接用已經組好的證據段落（不呼叫任何模型），
# 確保 Gemini 失敗兩次時，展示流程仍不中斷。
# =========================================================

def build_fallback_action_content(
    sections: list[tuple[str, str]],
    channel: str,
    tone: str,
) -> str:
    """依證據段落與管道格式，組出規則式備援內容。"""

    body_lines = [
        f"・{label}{text}" for label, text in sections
    ]
    body_text = "\n".join(body_lines)

    tone_opening = {
        "專業": "重點摘要如下：",
        "關係維護": "跟您分享目前活動的重點：",
        "促成交易": "把握時效，重點如下：",
    }.get(tone, "重點摘要如下：")

    if channel == "Email":
        return (
            "主旨：活動成效與下一步建議\n\n"
            "您好，\n\n"
            f"{tone_opening}\n\n"
            f"{body_text}\n\n"
            "（此為系統示範備援內容，AI 服務暫時無法回應，"
            "細節請以其他頁面的分析結果為準。）"
        )

    if channel == "LINE/簡訊":
        first_line = sections[0][1] if sections else ""
        return (
            f"{tone_opening}{first_line}"
            "（示範備援內容，請至系統查看完整分析）"
        )

    if channel == "拜訪提綱":
        return "\n".join(
            [f"{index}. {label}{text}" for index, (label, text) in enumerate(sections, start=1)]
            + ["（此為系統示範備援內容，非即時 AI 生成）"]
        )

    # 電話話術
    return "\n".join(
        [tone_opening, body_text, "（此為系統示範備援內容，非即時 AI 生成）"]
    )


def generate_action_content(
    evidence_text: str,
    sections: list[tuple[str, str]],
    channel: str,
    tone: str,
    length: str,
) -> tuple[str, bool]:
    """
    產生行動內容，最多嘗試兩次 Gemini 呼叫，
    兩次都失敗時改用規則式 fallback，確保展示不中斷。

    回傳 (內容, 是否為 fallback)。
    """

    for _ in range(2):
        try:
            return (
                ask_gemini_action_content(
                    evidence_text=evidence_text,
                    channel=channel,
                    tone=tone,
                    length=length,
                ),
                False,
            )
        except Exception:
            continue

    return (
        build_fallback_action_content(
            sections=sections,
            channel=channel,
            tone=tone,
        ),
        True,
    )
