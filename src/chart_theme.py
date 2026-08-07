from __future__ import annotations

import plotly.graph_objects as go


# =========================================================
# Plotly 圖表亮／暗模式配色
#
# 圖表背景一律設成透明，讓底下 [data-testid="stPlotlyChart"]
# 卡片本身的底色（已經用 var(--surface) 跟著亮/暗模式走，見
# src/ui_style.py）直接透出來，不需要另外猜一個「深色圖表底」
# 的色碼去對齊卡片色。文字／座標軸／格線顏色沒辦法用 CSS
# 變數控制（Plotly 是獨立渲染的 SVG，不吃頁面的 CSS），
# 所以才需要這支工具在 Python 端依 dark_mode 手動指定顏色。
# =========================================================

_LIGHT_TEXT_COLOR = "#273142"
_LIGHT_MUTED_COLOR = "#667085"
_LIGHT_GRID_COLOR = "#E1E7F0"

_DARK_TEXT_COLOR = "#EDF1F7"
_DARK_MUTED_COLOR = "#AEB9CC"
_DARK_GRID_COLOR = "#2A3448"


def apply_chart_theme(
    figure: go.Figure,
    dark_mode: bool = False,
) -> go.Figure:
    """
    套用跟目前亮／暗模式一致的 Plotly 版面樣式。

    圖表背景設透明；文字、座標軸標題／刻度、格線顏色依
    dark_mode 切換成對應色調。呼叫時機：圖表所有
    update_layout()／update_traces() 都做完，準備丟進
    st.plotly_chart() 之前的最後一步，避免後續呼叫又把
    這裡設的顏色蓋掉。
    """

    text_color = _DARK_TEXT_COLOR if dark_mode else _LIGHT_TEXT_COLOR
    muted_color = _DARK_MUTED_COLOR if dark_mode else _LIGHT_MUTED_COLOR
    grid_color = _DARK_GRID_COLOR if dark_mode else _LIGHT_GRID_COLOR

    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=text_color),
        legend=dict(font=dict(color=text_color)),
        hoverlabel=dict(
            font=dict(color=text_color),
            bgcolor="#1B2338" if dark_mode else "#FFFFFF",
        ),
    )

    figure.update_xaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color,
        linecolor=grid_color,
        tickfont=dict(color=muted_color),
        title_font=dict(color=text_color),
    )

    figure.update_yaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color,
        linecolor=grid_color,
        tickfont=dict(color=muted_color),
        title_font=dict(color=text_color),
    )

    return figure


# =========================================================
# 分類色票（依亮／暗模式調整飽和度／亮度）
#
# src/unit_overview_helpers.py 的 CATEGORY_COLOR_MAP 是亮色
# 模式調的顏色，直接疊在深色底上會偏暗、不夠醒目，這裡提供
# 對應的深色模式版本（同一組分類名稱，顏色調亮）。
# =========================================================

_CATEGORY_COLOR_MAP_DARK = {
    "可分離正向": "#2FE0A8",
    "不可分離": "#FF7A3D",
    "負增益": "#F87171",
}


def get_category_color_map(dark_mode: bool = False) -> dict[str, str]:
    """依亮／暗模式回傳對應的分類色票。"""

    if dark_mode:
        return dict(_CATEGORY_COLOR_MAP_DARK)

    from src.unit_overview_helpers import CATEGORY_COLOR_MAP

    return dict(CATEGORY_COLOR_MAP)
