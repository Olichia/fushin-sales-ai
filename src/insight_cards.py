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

    全部組成單行字串再丟給 st.markdown：CommonMark 解析器只要在
    內嵌 HTML 中間看到空白行，就會提早結束「原始 HTML 區塊」，
    讓後面的標籤變成純文字顯示出來，多行縮排寫法很容易踩到這個雷。
    """

    confidence_class = _CONFIDENCE_BADGE_CLASS.get(
        confidence, "badge-confidence-mid"
    )

    tag_text = "⚙ 規則式備援" if is_fallback else "✨ AI 結構化回覆"
    tag_class = "advisor-tag-fallback" if is_fallback else "advisor-tag"

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
        f'<span class="{tag_class}">{tag_text}</span>'
        f'<span class="badge {confidence_class}">信心：{html.escape(str(confidence))}</span>'
        "</div>"
        f"{row_html}"
        "</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)


def render_ai_insight_card(
    finding: str,
    reason: str,
    action: str,
    confidence: str | None = None,
    outcome: str | None = None,
) -> None:
    """
    以「發現／原因／建議」三段格式呈現規則式的 AI 洞察摘要，
    confidence 給定時在標題列右側加上資料信心徽章。outcome 給定時
    （例如「表現最佳」／「表現較差」）取代預設的「✨ AI 洞察」
    標籤文字，用於明確標示這張卡片在一組最佳／較差配對中的角色。

    跟 render_structured_advisor_card() 的差異：這裡的內容是直接
    從已經算好的數字組句（例如情境模擬結果、既有的策略分類／
    風險判斷），不是即時呼叫 LLM，所以標籤用「✨ AI 洞察」而不是
    「✨ AI 結構化回覆」，讓使用者能分辨哪些內容是即時 AI 判讀、
    哪些是規則式摘要——兩者都有用，但不該混為一談。適合需要
    使用者反覆調整輸入、即時看到結果的場景（LLM 呼叫的延遲不
    適合這種互動節奏），也適合單純重新包裝既有規則式分析結果的
    場景。
    """

    rows = [
        ("發現", finding),
        ("原因", reason),
        ("建議", action),
    ]

    row_html = "".join(
        '<div class="advisor-row">'
        f'<span class="advisor-row-label">{html.escape(label)}</span>'
        f'<span class="advisor-row-text">{html.escape(str(text))}</span>'
        "</div>"
        for label, text in rows
    )

    if confidence is not None:
        confidence_class = _CONFIDENCE_BADGE_CLASS.get(
            confidence, "badge-confidence-mid"
        )
        confidence_badge = (
            f'<span class="badge {confidence_class}">'
            f"資料信心：{html.escape(str(confidence))}</span>"
        )
    else:
        confidence_badge = ""

    if outcome is not None:
        outcome_icon = _OUTCOME_ICON.get(outcome, "🏆")
        tag_text = f"{outcome_icon} {outcome}"
    else:
        tag_text = "✨ AI 洞察"

    card_html = (
        '<div class="advisor-card">'
        '<div class="advisor-card-header">'
        f'<span class="advisor-tag">{html.escape(tag_text)}</span>'
        f"{confidence_badge}"
        "</div>"
        f"{row_html}"
        "</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)


def render_discount_insight_card(rows: list[tuple[str, str]]) -> None:
    """
    沿用與 AI 洞察卡片相同的 .advisor-card／.advisor-row 版面（原本
    的藍底設計），但標籤與列標籤改用 --blue 修飾類別（原始藍色
    var(--ai-accent) / var(--ai-accent-deep)），刻意跟商品／活動
    視角 AI 洞察卡片現在的紫色（表現最佳／較差）做出區隔，取代
    原本逐段 st.markdown() 純文字輸出。

    rows 中每個 (label, text_html) tuple，label 為純文字（例如
    「折扣率」「值得留意」，這裡會做 html.escape()），text_html
    須為呼叫端已組好、內嵌資料已用 html.escape() 處理過的安全
    HTML 字串（可包含 <strong> 等行內標籤），這裡不再對它逃逸。
    """

    row_html = "".join(
        '<div class="advisor-row">'
        '<span class="advisor-row-label advisor-row-label--blue">'
        f"{html.escape(label)}</span>"
        f'<span class="advisor-row-text">{text}</span>'
        "</div>"
        for label, text in rows
    )

    card_html = (
        '<div class="advisor-card">'
        '<div class="advisor-card-header">'
        '<span class="advisor-tag advisor-tag--blue">📊 折扣率洞察</span>'
        "</div>"
        f"{row_html}"
        "</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)


def render_evidence_sections(
    sections: list[tuple[str, str]],
) -> None:
    """
    以 hanging indent 版面呈現一組「標籤／內容」證據段落。

    跟策略中心頁面內的個別化建議排版邏輯相同（標籤後方內容
    靠左對齊，換行時對齊內容起始位置），抽成共用函式，
    讓行動生成頁等其他頁面也能用同一種排版顯示證據鏈。

    全部組成單行字串再丟給 st.markdown：CommonMark 解析器只要
    在內嵌 HTML 中間看到空白行，就會提早結束「原始 HTML 區塊」，
    多行縮排寫法很容易踩到這個雷。
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

    st.markdown("".join(blocks), unsafe_allow_html=True)


def render_scenario_card(
    title: str,
    badge_text: str,
    badge_tone: str,
    rows: list[tuple[str, str]],
    is_best: bool = False,
    is_adopted: bool = False,
) -> None:
    """
    以「標籤＋換行陳列的欄位」呈現單一情境模擬方案卡片，
    取代逐格 st.metric() 的大數字方塊排版：每一列是
    「說明文字（左）－數值（右，粗體）」，字級跟一般內文一致。

    badge_tone 對應方案性質：
    "neutral"（無贈品／基準）、"good"（贈品組合）、
    "risk"（深折扣，提醒沒有實證支持的降價不代表更划算）。
    is_best=True 時卡片外框改用成功色，標出目前簡化後淨效益
    最高的方案。is_adopted=True 時額外標示「📌 已採用」徽章，
    並改用強調色外框，跟使用者在頁面上按下「採用」的方案對應。
    """

    badge_class = _SCENARIO_BADGE_CLASS.get(
        badge_tone, "badge-neutral"
    )

    card_class = "scenario-card"

    if is_adopted:
        card_class += " scenario-card-adopted"
    elif is_best:
        card_class += " scenario-card-best"

    title_text = f"✅ {title}" if is_best else title

    row_html = "".join(
        '<div class="scenario-row">'
        f'<span class="scenario-row-label">{html.escape(label)}</span>'
        f'<span class="scenario-row-value">{html.escape(str(value))}</span>'
        "</div>"
        for label, value in rows
    )

    adopted_badge_html = (
        '<span class="badge badge-adopted">📌 已採用</span>'
        if is_adopted
        else ""
    )

    card_html = (
        f'<div class="{card_class}">'
        '<div class="scenario-card-title-row">'
        f'<span class="scenario-card-title">{html.escape(title_text)}</span>'
        '<span class="scenario-card-badges">'
        f'<span class="badge {badge_class}">{html.escape(badge_text)}</span>'
        f"{adopted_badge_html}"
        "</span>"
        "</div>"
        f"{row_html}"
        "</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)
