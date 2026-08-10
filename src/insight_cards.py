from __future__ import annotations

import html

import streamlit as st


_CONFIDENCE_BADGE_CLASS = {
    "高": "badge-confidence-high",
    "中": "badge-confidence-mid",
    "低": "badge-confidence-low",
    "較高": "badge-confidence-high",
    "較低": "badge-confidence-low",
}

_SCENARIO_BADGE_CLASS = {
    "neutral": "badge-neutral",
    "good": "badge-confidence-high",
    "risk": "badge-confidence-low",
}

_OUTCOME_ICON = {
    "表現最佳": "🏆",
    "表現較差": "📉",
}


def render_structured_advisor_card(
    finding: str,
    reason: str,
    evidence: str,
    action: str,
    alternative: str,
    confidence: str,
    limitations: str,
    is_fallback: bool = False,
) -> None:
    """
    以固定六欄位呈現 AI 顧問的結構化回覆：
    關鍵發現／判斷原因／資料證據／建議行動／替代方案／資料限制，
    信心程度以徽章呈現。

    is_fallback=True 時代表這是 Gemini 兩次呼叫都失敗後的規則式
    備援內容，卡片會換成明顯不同的標籤與色調，不能跟正常 AI 回覆
    混淆。

    全部組成單行字串再丟給 st.markdown：
    CommonMark 解析器只要在內嵌 HTML 中間看到空白行，
    就可能提早結束原始 HTML 區塊，因此避免多行 HTML 字串。
    """

    confidence_class = _CONFIDENCE_BADGE_CLASS.get(
        confidence,
        "badge-confidence-mid",
    )

    tag_text = "⚙ 規則式備援" if is_fallback else "✨ AI 結構化回覆"
    tag_class = (
        "advisor-tag-fallback"
        if is_fallback
        else "advisor-tag"
    )

    rows = [
        ("關鍵發現", finding),
        ("判斷原因", reason),
        ("資料證據", evidence),
        ("建議行動", action),
        ("替代方案", alternative),
        ("資料限制", limitations),
    ]

    row_html = "".join(
        '<div class="advisor-row">'
        f'<span class="advisor-row-label">{html.escape(label)}</span>'
        f'<span class="advisor-row-text">{html.escape(str(text))}</span>'
        "</div>"
        for label, text in rows
    )

    card_html = (
        '<div class="advisor-card">'
        '<div class="advisor-card-header">'
        f'<span class="{tag_class}">{html.escape(tag_text)}</span>'
        f'<span class="badge {confidence_class}">'
        f"信心：{html.escape(str(confidence))}"
        "</span>"
        "</div>"
        f"{row_html}"
        "</div>"
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )


def render_ai_insight_card(
    finding: str,
    reason: str,
    action: str,
    confidence: str | None = None,
    outcome: str | None = None,
    tag_label: str = "AI 洞察",
    tag_icon: str = "✨",
    action_label: str = "建議",
) -> None:
    """
    以三段格式呈現規則式洞察摘要。

    預設顯示：
    發現／原因／建議

    呼叫端可透過 action_label 修改第三欄名稱。

    例如：
    - 活動洞察頁：
      action_label="資料限制"
    - 其他頁面不傳 action_label：
      預設仍顯示「建議」

    tag_label 與 tag_icon 可修改卡片標籤。
    outcome 給定時，例如「表現最佳」「表現較差」，
    會優先以 outcome 當卡片標籤。

    此函式內容主要來自已經計算完成的規則式結果，
    並非即時 LLM 回覆，因此與
    render_structured_advisor_card() 的 AI 結構化回覆分開呈現。
    """

    rows = [
        ("發現", finding),
        ("原因", reason),
        (action_label, action),
    ]

    row_html = "".join(
        '<div class="advisor-row">'
        f'<span class="advisor-row-label">'
        f"{html.escape(str(label))}"
        "</span>"
        f'<span class="advisor-row-text">'
        f"{html.escape(str(text))}"
        "</span>"
        "</div>"
        for label, text in rows
    )

    if confidence is not None:
        confidence_class = _CONFIDENCE_BADGE_CLASS.get(
            confidence,
            "badge-confidence-mid",
        )

        confidence_badge = (
            f'<span class="badge {confidence_class}">'
            f"資料信心：{html.escape(str(confidence))}"
            "</span>"
        )
    else:
        confidence_badge = ""

    if outcome is not None:
        outcome_icon = _OUTCOME_ICON.get(
            outcome,
            "📊",
        )
        tag_text = f"{outcome_icon} {outcome}"
    else:
        tag_text = f"{tag_icon} {tag_label}".strip()

    card_html = (
        '<div class="advisor-card">'
        '<div class="advisor-card-header">'
        f'<span class="advisor-tag">'
        f"{html.escape(tag_text)}"
        "</span>"
        f"{confidence_badge}"
        "</div>"
        f"{row_html}"
        "</div>"
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )


def render_discount_insight_card(
    rows: list[tuple[str, str]],
) -> None:
    """
    沿用 AI 洞察卡片相同的 advisor-card / advisor-row 版面，
    但使用藍色修飾類別，讓折扣率洞察與一般洞察卡有所區隔。

    rows 中：
    - label 為純文字，會執行 html.escape()
    - text_html 為呼叫端已處理完成的安全 HTML
      可包含 <strong> 等行內標籤
    """

    row_html = "".join(
        '<div class="advisor-row">'
        '<span class="advisor-row-label advisor-row-label--blue">'
        f"{html.escape(label)}"
        "</span>"
        f'<span class="advisor-row-text">{text}</span>'
        "</div>"
        for label, text in rows
    )

    card_html = (
        '<div class="advisor-card">'
        '<div class="advisor-card-header">'
        '<span class="advisor-tag advisor-tag--blue">'
        "📊 折扣率洞察"
        "</span>"
        "</div>"
        f"{row_html}"
        "</div>"
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )


def render_evidence_sections(
    sections: list[tuple[str, str]],
) -> None:
    """
    以 hanging indent 版面呈現一組「標籤／內容」證據段落。

    讓策略中心、行動生成等頁面能使用一致的證據鏈排版。
    """

    blocks = []

    for label, text in sections:
        indent = len(label)

        blocks.append(
            '<div style="padding-left:{indent}em;'
            "text-indent:-{indent}em;"
            'margin:0 0 0.85em;line-height:1.7;">'
            "<strong>{label}</strong>{text}</div>".format(
                indent=indent,
                label=html.escape(label),
                text=html.escape(str(text)),
            )
        )

    st.markdown(
        "".join(blocks),
        unsafe_allow_html=True,
    )


def render_scenario_card(
    title: str,
    badge_text: str,
    badge_tone: str,
    rows: list[tuple[str, str]],
    is_best: bool = False,
    is_adopted: bool = False,
) -> None:
    """
    以「標籤＋欄位」呈現單一情境模擬方案卡片。

    badge_tone：
    - neutral：中性／基準方案
    - good：較佳方案
    - risk：風險方案

    is_best=True：
    標示目前簡化淨效益最佳方案。

    is_adopted=True：
    額外顯示「已採用」徽章。
    """

    badge_class = _SCENARIO_BADGE_CLASS.get(
        badge_tone,
        "badge-neutral",
    )

    card_class = "scenario-card"

    if is_adopted:
        card_class += " scenario-card-adopted"
    elif is_best:
        card_class += " scenario-card-best"

    title_text = (
        f"✅ {title}"
        if is_best
        else title
    )

    row_html = "".join(
        '<div class="scenario-row">'
        f'<span class="scenario-row-label">'
        f"{html.escape(label)}"
        "</span>"
        f'<span class="scenario-row-value">'
        f"{html.escape(str(value))}"
        "</span>"
        "</div>"
        for label, value in rows
    )

    adopted_badge_html = (
        '<span class="badge badge-adopted">'
        "📌 已採用"
        "</span>"
        if is_adopted
        else ""
    )

    card_html = (
        f'<div class="{card_class}">'
        '<div class="scenario-card-title-row">'
        f'<span class="scenario-card-title">'
        f"{html.escape(title_text)}"
        "</span>"
        '<span class="scenario-card-badges">'
        f'<span class="badge {badge_class}">'
        f"{html.escape(badge_text)}"
        "</span>"
        f"{adopted_badge_html}"
        "</span>"
        "</div>"
        f"{row_html}"
        "</div>"
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )