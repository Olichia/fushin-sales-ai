from __future__ import annotations

import html

import streamlit as st


_ICON_ACCENT_CLASS = {
    "blue": "kpi-card-icon--blue",
    "green": "kpi-card-icon--green",
    "orange": "kpi-card-icon--orange",
    "red": "kpi-card-icon--red",
}


def render_kpi_card(
    icon: str,
    label: str,
    value: str,
    help_text: str,
    accent: str = "blue",
    value_size: str = "normal",
) -> None:
    """
    以「右上角彩色外框 icon 徽章＋標籤在上／大數值在下」格式呈現
    單一 KPI，取代原生 st.metric() 的純白卡片，accent 對應既有
    品牌色（blue／green／orange／red），亮／暗模式皆沿用同一組
    CSS 變數自動換色。help_text 透過瀏覽器原生 title 提示呈現，
    取代 st.metric() 的 help 參數。

    value_size="lg" 時數值字級加大，適合短數字／百分比內容；
    較長的文字內容（例如活動類型組合名稱）維持預設字級，避免
    放大後換行、破壞卡片版面一致性。
    """

    icon_class = _ICON_ACCENT_CLASS.get(accent, "kpi-card-icon--blue")
    value_class = (
        "kpi-card-value kpi-card-value--lg"
        if value_size == "lg"
        else "kpi-card-value"
    )

    card_html = (
        '<div class="kpi-card" title="'
        f'{html.escape(help_text)}">'
        f'<div class="kpi-card-icon {icon_class}">{html.escape(icon)}</div>'
        f'<div class="kpi-card-label">{html.escape(label)}</div>'
        f'<div class="{value_class}">{html.escape(value)}</div>'
        "</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)
