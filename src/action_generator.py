from __future__ import annotations

import re
from typing import Any

import pandas as pd
from google.genai import types

from src.ai_advisor import get_gemini_client
from src.unit_recommendation_notes import (
    build_unit_personalized_recommendation_sections,
    format_signed_currency,
)
from src.whatif_simulation import WhatIfScenarioResult


CHANNEL_OPTIONS = ["電話話術", "LINE/簡訊", "Email", "拜訪提綱"]
TONE_OPTIONS = ["專業", "關係維護", "促成交易"]
LENGTH_OPTIONS = ["簡短", "標準", "詳細"]
AUDIENCE_OPTIONS = ["B2C 消費者行銷", "B2B 商務溝通"]

GEMINI_MODEL_NAME = "gemini-flash-lite-latest"
PLATFORM_CAMPAIGN_LEVEL = "平台檔期"

INTERNAL_ONLY_TERMS = (
    "預估活動營收",
    "無活動預期營收",
    "淨營收增益",
    "贈品成本",
    "簡化後淨效益",
    "平台抽成",
    "毛利",
    "淨利潤",
    "情境試算結果",
    "試算情境",
    "方案試算",
)

B2B_ONLY_PHRASES = (
    "合作夥伴",
    "感謝夥伴",
    "長期合作",
    "回報主管",
    "通路窗口",
    "合作機會",
)


def build_platform_campaign_name_set(
    activity_calendar_dataframe: pd.DataFrame | None,
) -> set[str]:
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
    label = str(
        unit_row.get("corresponding_activities_label") or ""
    ).strip()

    activity_types = [part for part in label.split("、") if part]

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
        classify_activity_type(activity_type, platform_campaign_names)
        == "平台檔期"
        for activity_type in activity_types
    )
    has_product = any(
        classify_activity_type(activity_type, platform_campaign_names)
        == "商品/品牌活動"
        for activity_type in activity_types
    )

    note = ""
    if has_platform and has_product:
        note = (
            "本檔同時搭配平台檔期與商品/品牌活動，"
            "兩者是不同方向的優惠（平台滿額門檻 vs 廠商贈品/折扣），"
            "下方淨營收效應為兩者疊加後的整體效果。"
        )

    return f"本活動單位對應活動：{composition_text}。{note}".strip()


def build_unit_action_evidence(
    unit_row: pd.Series,
    pairing_rows: pd.DataFrame,
    unit_overview: pd.DataFrame,
    mechanism_text: str,
    strategy_category: str,
    activity_calendar_dataframe: pd.DataFrame | None,
) -> dict[str, object]:
    composition_note = build_unit_activity_composition_note(
        unit_row, activity_calendar_dataframe
    )

    personalized_sections = build_unit_personalized_recommendation_sections(
        unit_row=unit_row,
        pairing_rows=pairing_rows,
        unit_overview=unit_overview,
        mechanism_text=mechanism_text,
        strategy_category=strategy_category,
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

    public_offer = {
        "product_name": str(product_name),
        "original_price": _first_number(
            unit_row,
            ["baseline_price", "quiet_period_price", "original_price"],
        ),
        "activity_price": _first_number(
            unit_row,
            ["activity_price", "unit_price", "campaign_price"],
        ),
        "gift_name": _extract_gift_name(mechanism_text),
        "activity_name": str(
            unit_row.get("corresponding_activities_label") or ""
        ),
        "selling_point": "",
        "activity_period": "",
        "platform_offer": "",
        "cta": "立即查看活動詳情",
    }

    return {
        "source_type": "活動單位分析",
        "source_label": source_label,
        "sections": sections,
        "evidence_text": evidence_text,
        "public_offer": public_offer,
    }


def build_whatif_action_evidence(
    scenario_result: WhatIfScenarioResult,
    product_name: str,
    scenario_input: Any | None = None,
) -> dict[str, object]:
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
        f"淨營收增益 {format_signed_currency(scenario_result.net_revenue_gain)}"
        + (
            f"，贈品成本 {scenario_result.total_gift_cost:,.0f} 元"
            if scenario_result.has_gift
            else "，本方案不含贈品"
        )
        + "，簡化後淨效益 "
        + format_signed_currency(scenario_result.simplified_net_benefit)
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
            "本方案有勾選同時搭配平台活動，但平台活動的疊加貢獻"
            "需要客單價與配對比較才能拆分，本次試算未計入。"
        )

    sections: list[tuple[str, str]] = [
        ("【情境設定】", f"商品「{product_name}」。"),
        ("【試算結果】", scenario_summary),
        ("【資料限制】", "".join(limitation_parts)),
    ]

    activity_price = getattr(scenario_input, "activity_price", None)
    baseline_price = getattr(scenario_input, "baseline_price", None)

    public_offer = {
        "product_name": str(product_name),
        "original_price": baseline_price,
        "activity_price": activity_price,
        "gift_name": "" if not scenario_result.has_gift else "指定贈品",
        "activity_name": str(scenario_result.label),
        "selling_point": "",
        "activity_period": "",
        "platform_offer": "",
        "cta": "立即查看活動詳情",
    }

    source_label = f"{product_name}｜{scenario_result.label}（情境模擬）"
    evidence_text = "\n\n".join(
        f"{label}{text}" for label, text in sections
    )

    return {
        "source_type": "情境模擬",
        "source_label": source_label,
        "sections": sections,
        "evidence_text": evidence_text,
        "public_offer": public_offer,
    }


def _first_number(row: pd.Series, keys: list[str]) -> float | None:
    for key in keys:
        value = row.get(key)
        try:
            if pd.notna(value) and str(value).strip() != "":
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _extract_gift_name(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"(?:贈|送|加贈)\s*([^、，；;。]+)", str(text))
    return match.group(1).strip() if match else ""


def build_consumer_offer_text(public_offer: dict[str, Any]) -> str:
    product_name = str(public_offer.get("product_name") or "").strip()
    if not product_name:
        raise ValueError("B2C 模式必須提供商品名稱。")

    lines = [f"商品名稱：{product_name}"]

    original_price = public_offer.get("original_price")
    activity_price = public_offer.get("activity_price")

    if original_price not in (None, "", 0, 0.0):
        lines.append(f"原價：{float(original_price):,.0f} 元")
    if activity_price not in (None, "", 0, 0.0):
        lines.append(f"活動價：{float(activity_price):,.0f} 元")

    activity_name = str(public_offer.get("activity_name") or "").strip()
    gift_name = str(public_offer.get("gift_name") or "").strip()
    selling_point = str(public_offer.get("selling_point") or "").strip()
    activity_period = str(public_offer.get("activity_period") or "").strip()
    platform_offer = str(public_offer.get("platform_offer") or "").strip()
    cta = str(public_offer.get("cta") or "立即查看活動詳情").strip()

    if activity_name:
        lines.append(f"活動名稱／方案：{activity_name}")
    if gift_name:
        lines.append(f"商品贈品：{gift_name}")
    if selling_point:
        lines.append(f"商品賣點：{selling_point}")
    if activity_period:
        lines.append(f"活動期間：{activity_period}")
    if platform_offer:
        lines.append(
            "已確認的平台優惠資訊："
            f"{platform_offer}（只能照實轉述，不得推估效益）"
        )
    if cta:
        lines.append(f"行動呼籲：{cta}")

    return "\n".join(lines)


_B2B_CHANNEL_GUIDE = {
    "電話話術": (
        "產出業務人員可直接照著念的商務電話話術，"
        "採口語化短句，適合向主管、品牌或通路夥伴說明。"
    ),
    "LINE/簡訊": (
        "產出一則精簡的商務 LINE／簡訊，保留關鍵發現與下一步。"
    ),
    "Email": (
        "產出正式商務 Email，包含主旨、稱謂、內文、結尾。"
    ),
    "拜訪提綱": (
        "產出業務拜訪或內部會議提綱，條列 3–5 個討論重點。"
    ),
}

_B2C_CHANNEL_GUIDE = {
    "電話話術": (
        "產出客服或電話行銷人員可直接對消費者使用的促購話術，"
        "包含問候、需求切入、商品利益、已確認優惠與行動呼籲。"
    ),
    "LINE/簡訊": (
        "產出面向消費者的 LINE／簡訊促購文案；簡短、清楚，"
        "包含商品、已確認優惠與一個明確行動呼籲。"
    ),
    "Email": (
        "產出面向消費者的行銷 Email，包含吸引人的主旨、"
        "商品利益、已確認優惠、活動資訊與行動呼籲。"
    ),
    "拜訪提綱": (
        "將拜訪提綱解釋為門市導購提綱，內容包含需求詢問、"
        "商品特色、優惠說明、異議處理與成交引導。"
    ),
}

_TONE_GUIDE_B2B = {
    "專業": "語氣客觀精簡，聚焦數據、限制與下一步。",
    "關係維護": "語氣溫和，重視合作關係與共同確認。",
    "促成交易": "語氣積極，聚焦時效、確認事項與明確下一步。",
}

_TONE_GUIDE_B2C = {
    "專業": "資訊清楚可信，不誇大、不製造虛假稀缺。",
    "關係維護": "以會員關懷與生活情境切入，語氣溫和親切。",
    "促成交易": "凸顯限時優惠與行動呼籲，但不得捏造倒數、限量或成效。",
}

_LENGTH_GUIDE = {
    "簡短": "整體控制在 60–100 字內。",
    "標準": "整體控制在 120–220 字。",
    "詳細": "整體可到 250–380 字，但仍須精簡。",
}


def build_action_generation_prompt(
    evidence_text: str,
    channel: str,
    tone: str,
    length: str,
    audience_type: str = "B2B 商務溝通",
    public_offer: dict[str, Any] | None = None,
) -> str:
    length_guide = _LENGTH_GUIDE.get(length, _LENGTH_GUIDE["標準"])

    if audience_type == "B2C 消費者行銷":
        consumer_text = build_consumer_offer_text(public_offer or {})
        channel_guide = _B2C_CHANNEL_GUIDE.get(
            channel, _B2C_CHANNEL_GUIDE["Email"]
        )
        tone_guide = _TONE_GUIDE_B2C.get(
            tone, _TONE_GUIDE_B2C["專業"]
        )
        return f"""
你是零售電商的消費者行銷文案助手。

你的讀者是一般消費者，不是主管、品牌窗口、供應商或合作夥伴。
只能使用下方【消費者可公開資訊】。完整內部分析只用來決定選哪個
方案，不可把內部營收、成本、淨效益、模型限制或試算數字寫進文案。

【格式要求】
{channel_guide}

【語氣要求】
{tone_guide}

【長度要求】
{length_guide}

必須遵守：
1. 不得出現預估活動營收、無活動預期營收、淨營收增益、贈品成本、
   簡化後淨效益、平台抽成、毛利、淨利潤或情境試算公式。
2. 不得出現感謝夥伴、長期合作、回報主管、通路窗口、合作機會等 B2B 語句。
3. 沒有提供的價格、贈品、期間、平台優惠、限量或倒數資訊不得自行補充。
4. 平台優惠若有填寫，只能照實轉述，不能宣稱它帶來多少成效。
5. 情境模擬尚未執行不必對消費者揭露；只將已確認要採用的公開優惠寫成文案。
6. 使用繁體中文，只輸出可直接發送的最終內容。

【消費者可公開資訊】
{consumer_text}
""".strip()

    channel_guide = _B2B_CHANNEL_GUIDE.get(
        channel, _B2B_CHANNEL_GUIDE["Email"]
    )
    tone_guide = _TONE_GUIDE_B2B.get(tone, _TONE_GUIDE_B2B["專業"])

    return f"""
你是零售業務團隊的商務溝通內容撰寫助手。

請只根據下方【完整分析證據】撰寫，不可新增不存在的商品、活動、
數字、承諾或因果關係。限制與警語不得省略或淡化。

【格式要求】
{channel_guide}

【語氣要求】
{tone_guide}

【長度要求】
{length_guide}

必須遵守：
1. 平台檔期與商品／品牌優惠若同時存在，必須分開描述。
2. 情境模擬必須清楚標示為尚未實際執行的試算。
3. 淨營收效應與簡化後淨效益不等於實際毛利或淨利潤。
4. 使用繁體中文，只輸出最終內容。

【完整分析證據】
{evidence_text}
""".strip()


def ask_gemini_action_content(
    evidence_text: str,
    channel: str,
    tone: str,
    length: str,
    audience_type: str = "B2B 商務溝通",
    public_offer: dict[str, Any] | None = None,
) -> str:
    client = get_gemini_client()
    prompt = build_action_generation_prompt(
        evidence_text=evidence_text,
        channel=channel,
        tone=tone,
        length=length,
        audience_type=audience_type,
        public_offer=public_offer,
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )

    response_text = getattr(response, "text", None)
    if not response_text or not response_text.strip():
        raise ValueError("Gemini 沒有回傳可顯示的文字內容。")

    result = response_text.strip()
    if audience_type == "B2C 消費者行銷":
        validate_b2c_output(result)
    return result


def validate_b2c_output(content: str) -> None:
    blocked = [term for term in INTERNAL_ONLY_TERMS + B2B_ONLY_PHRASES if term in content]
    if blocked:
        raise ValueError(
            "B2C 文案包含內部或 B2B 用語：" + "、".join(blocked)
        )


def _b2c_offer_sentence(public_offer: dict[str, Any]) -> str:
    product = str(public_offer.get("product_name") or "此商品").strip()
    parts = [product]

    activity_price = public_offer.get("activity_price")
    gift_name = str(public_offer.get("gift_name") or "").strip()
    activity_period = str(public_offer.get("activity_period") or "").strip()
    platform_offer = str(public_offer.get("platform_offer") or "").strip()

    if activity_price not in (None, "", 0, 0.0):
        parts.append(f"活動價 {float(activity_price):,.0f} 元")
    if gift_name:
        parts.append(f"購買加贈{gift_name}")
    if activity_period:
        parts.append(f"活動期間 {activity_period}")
    if platform_offer:
        parts.append(platform_offer)

    return "，".join(parts)


def build_b2c_fallback_content(
    public_offer: dict[str, Any],
    channel: str,
    tone: str,
) -> str:
    offer_sentence = _b2c_offer_sentence(public_offer)
    selling_point = str(public_offer.get("selling_point") or "").strip()
    cta = str(public_offer.get("cta") or "立即查看活動詳情").strip()

    if channel == "Email":
        subject_product = str(public_offer.get("product_name") or "精選商品")
        body = f"{offer_sentence}。"
        if selling_point:
            body += f"{selling_point}。"
        body += f"{cta}。"
        return f"主旨：{subject_product}限時優惠\n\n您好，\n\n{body}"

    if channel == "LINE/簡訊":
        extra = f"，{selling_point}" if selling_point else ""
        return f"{offer_sentence}{extra}。{cta}。"

    if channel == "拜訪提綱":
        points = [
            "1. 先詢問消費者目前使用情境與需求",
            f"2. 說明商品：{offer_sentence}",
        ]
        if selling_point:
            points.append(f"3. 強調商品特色：{selling_point}")
        points.append(f"4. 成交引導：{cta}")
        return "\n".join(points)

    opening = {
        "專業": "您好，想向您介紹目前的商品優惠。",
        "關係維護": "您好，想和您分享一個可能適合您的優惠。",
        "促成交易": "您好，現在有一項期間優惠想優先通知您。",
    }.get(tone, "您好，想向您介紹目前的商品優惠。")
    return f"{opening}\n{offer_sentence}。\n{selling_point + '。' if selling_point else ''}{cta}。"


def build_b2b_fallback_content(
    sections: list[tuple[str, str]],
    channel: str,
    tone: str,
) -> str:
    body_lines = [f"・{label}{text}" for label, text in sections]
    body_text = "\n".join(body_lines)
    tone_opening = {
        "專業": "重點摘要如下：",
        "關係維護": "跟您分享目前活動的重點：",
        "促成交易": "把握時效，重點如下：",
    }.get(tone, "重點摘要如下：")

    if channel == "Email":
        return (
            "主旨：活動成效與下一步建議\n\n您好，\n\n"
            f"{tone_opening}\n\n{body_text}\n\n"
            "（此為系統示範備援內容，細節請以分析頁結果為準。）"
        )
    if channel == "LINE/簡訊":
        first_line = sections[0][1] if sections else ""
        return f"{tone_opening}{first_line}（示範備援內容）"
    if channel == "拜訪提綱":
        return "\n".join(
            [
                f"{index}. {label}{text}"
                for index, (label, text) in enumerate(sections, start=1)
            ]
            + ["（此為系統示範備援內容）"]
        )
    return "\n".join([tone_opening, body_text, "（此為系統示範備援內容）"])


def build_fallback_action_content(
    sections: list[tuple[str, str]],
    channel: str,
    tone: str,
    audience_type: str = "B2B 商務溝通",
    public_offer: dict[str, Any] | None = None,
) -> str:
    if audience_type == "B2C 消費者行銷":
        return build_b2c_fallback_content(
            public_offer=public_offer or {},
            channel=channel,
            tone=tone,
        )
    return build_b2b_fallback_content(
        sections=sections,
        channel=channel,
        tone=tone,
    )


def generate_action_content(
    evidence_text: str,
    sections: list[tuple[str, str]],
    channel: str,
    tone: str,
    length: str,
    audience_type: str = "B2B 商務溝通",
    public_offer: dict[str, Any] | None = None,
) -> tuple[str, bool]:
    for _ in range(2):
        try:
            return (
                ask_gemini_action_content(
                    evidence_text=evidence_text,
                    channel=channel,
                    tone=tone,
                    length=length,
                    audience_type=audience_type,
                    public_offer=public_offer,
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
            audience_type=audience_type,
            public_offer=public_offer,
        ),
        True,
    )
